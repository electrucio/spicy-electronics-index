"""The bipolar decks of the characterisation bench: one class per netlist, serving the measurement ids of
data/bench/measurements.yaml whose conditions it reads (docs/model-characterisation.md).

A deck gives, for one copy of the transistor, the element lines (`body`), the vectors to keep (`saves`)
and the shared tail (`tail`: sweep source, clamp model, analysis card); `character.py` assembles one
netlist from several copies when the deck packs, runs it, and hands each copy's vectors back to
`measure`, which returns the values and curves of the measurement ids it serves, their codes, and what
later decks need (`derived`: the base currents of the ladder, the gain at 25 °C). `finalize` computes
what needs several decks (the temperature ratios, the current noise). Standard library only.

The base is always driven from a behavioural source IB = 10^V(x) while VX sweeps x: a current into a
junction converges where forcing the collector current does not, and a DC sweep starts each point from
the last one. The sign `s` is +1 for an NPN and −1 for a PNP, and every source is multiplied by it.
"""

import math

from bench import num
from bench.num import K_B, LN10, T_K, n, si

CLAMP = 30.0        # V: a transistor too weak to sink its forced collector current has it caught here
SUSPECT_HFE = 1e4   # a gain no transistor has: the behavioural drive settled on a wrong point (QSPICE, RB≈0)
VBE_RANGE = (0.05, 1.6)   # a VBE outside this at any current is that wrong point too (germanium sits near 0.1-0.3 V)


def ibsrc(name, node, s, scale=1.0):
    sg = "-" if s < 0 else ""
    k = f"{n(scale)}*" if scale != 1.0 else ""
    return f"{name} 0 {node} I={sg}{k}exp({LN10}*V(x))"


def sweep_tail(sw):
    """The log sweep of the base current: decades from `from` to `to`, `per_decade` points each."""
    lo, hi = math.log10(float(sw["from"])), math.log10(float(sw["to"]))
    return ["VX x 0 0", "RX x 0 1", f".dc VX {n(lo)} {n(hi)} {n(1 / int(sw['per_decade']))}"]


def listed(v):
    """A condition that is one value or a list of them, as a list of floats."""
    return [float(x) for x in (v if isinstance(v, (list, tuple)) else [v])]


def sat_names(ratio, first):
    """The element and node suffix of a forced-ratio saturation copy: the first ratio keeps the bare names the
    catalogue quotes, the others carry the ratio."""
    return "" if first else str(int(ratio))


def sat_body(m, s, x, ratio, clamp, first):
    """The forced-ratio saturation circuit: a base drive, a collector drive of `ratio` times it, a clamp."""
    r = sat_names(ratio, first)
    return [ibsrc(f"BSB{r}{x}", f"bs{r}{x}", s), ibsrc(f"BSC{r}{x}", f"cs{r}{x}", s, ratio),
            (f"DCL{r}{x} cs{r}{x} cl{r}{x} DCLMP" if s > 0 else f"DCL{r}{x} cl{r}{x} cs{r}{x} DCLMP"),
            f"VCL{r}{x} cl{r}{x} 0 {n(s * clamp)}", f"QS{r}{x} cs{r}{x} bs{r}{x} 0 {m}"]


def saturation(cat, ib, vcs, vbs, ratio, clamp, summary=True):
    """VCE(sat) and VBE(sat) along a forced-ratio sweep: at each ladder current where the transistor was
    saturated (below the clamp, collector below base), and the two curves on the catalogue's grid."""
    c = cat["bjt-saturation"]["conditions"]
    ics = [ratio * b for b in ib]
    ok = [(i, v, w) for i, v, w in zip(ics, vcs, vbs) if v < clamp - 1 and v < w]
    if len(ok) < 3:
        return {}, {}, "n/a"
    xs = [p[0] for p in ok]
    vce = [p[1] for p in ok]
    vbe = [p[2] for p in ok]
    vals, got = {}, {}
    tag = f",{int(ratio)}"
    for i_t in c["ic_ladder"]:
        v = num.log_interp(xs, vce, i_t)
        if v is None:
            continue
        got[i_t] = v
        vals[f"vcesat@{si(i_t, 'A')}{tag}"] = v
        vals[f"vbesat@{si(i_t, 'A')}{tag}"] = num.log_interp(xs, vbe, i_t)
    if summary:
        vals["vce_sat_floor"] = got.get(1e-4)
        hi = sorted(got)
        if 0.1 in got and 1.0 in got:
            vals["rce_sat"] = (got[1.0] - got[0.1]) / 0.9
        elif len(hi) >= 2:
            vals["rce_sat"] = (got[hi[-1]] - got[hi[-2]]) / (hi[-1] - hi[-2])
    g = cat["bjt-saturation"]["grid"]
    cur = {f"VCE(sat), IC/IB={int(ratio)}": num.on_grid(xs, vce, g, log_y=True), f"VBE(sat), IC/IB={int(ratio)}": num.on_grid(xs, vbe, g)}
    return vals, cur, "ok"


def tlabel(t):
    """A temperature as the curve names spell it: −55°C, 25°C, 125°C."""
    return f"{'−' if t < 0 else ''}{abs(int(t))}°C"


def curve_grid(cat, mid, name):
    """The grid a named curve of a measurement is published on: its own, else the measurement's."""
    for c in cat[mid].get("curves") or []:
        if c["name"] == name:
            return c.get("grid") or cat[mid].get("grid")
    return cat[mid].get("grid")


def vec(d, name):
    v = d.get(name.lower())
    if v is None:
        raise KeyError(f"{name} not in {sorted(d)[:12]}")
    return list(v)


def sweep_points(sw):
    """How many points a log sweep of the base current has: decades times points per decade, plus one."""
    lo, hi = math.log10(float(sw["from"])), math.log10(float(sw["to"]))
    return int(round((hi - lo) * int(sw["per_decade"]))) + 1


def step_points(sw):
    """How many points a linear voltage sweep has."""
    return int(round((float(sw["to"]) - float(sw["from"])) / float(sw["step"]))) + 1


def whole(d, name, expected):
    """The sweep vector, or an error when the simulator stopped the sweep early: a copy that will not converge
    spoils every copy of its pack, and the simulator may still exit 0 with a few points, so the measurement
    refuses them and the pack is run one model at a time (one point short at the end is a rounding)."""
    v = vec(d, name)
    if len(v) < expected - 1:
        raise RuntimeError(f"sweep stopped at {len(v)} of {expected} points")
    return v


def signed(d, name, s):
    return [s * x for x in vec(d, name)]


def mag(d, name):
    return [abs(x) for x in vec(d, name)]


def freq(d):
    return [abs(x) for x in vec(d, "frequency")]


class Deck:
    name = ""
    ids = ()
    analysis = "dc"
    pack = True
    temp = 25.0

    def __init__(self, cat):
        self.cat = cat

    def cond(self, mid):
        return self.cat[mid]["conditions"]

    def grid(self, mid):
        return self.cat[mid].get("grid")

    def ready(self, derived):
        return True

    def body(self, m, s, sfx, derived):
        raise NotImplementedError

    def saves(self, sfx):
        return []

    def tail(self, s):
        return []

    def measure(self, d, s, sfx, derived):
        """→ (values {id: {key: value}}, curves {id: {name: points}}, codes {id: code}, derived updates)."""
        raise NotImplementedError


# ------------------------------------------------------------------------------------- the DC sweep
class DcMain(Deck):
    """One sweep, five circuits: the Gummel plot, hFE at three VCE, forced-β saturation, the reverse gain."""
    name = "dc"
    ids = ("bjt-runs", "bjt-gummel", "bjt-hfe-ic", "bjt-saturation", "bjt-reverse")

    def __init__(self, cat):
        super().__init__(cat)
        self.vces = [float(v) for v in self.cond("bjt-hfe-ic")["vce"]]
        self.ratios = listed(self.cond("bjt-saturation")["forced_hfe"])
        self.clamp = float(self.cond("bjt-saturation").get("clamp_v", CLAMP))
        self.vec_r = float(self.cond("bjt-reverse")["vec"])
        self.sw = self.cond("bjt-hfe-ic")["ib_sweep"]

    def body(self, m, s, x, derived):
        out = [ibsrc(f"BG{x}", f"bg{x}", s), f"VG{x} cg{x} bg{x} 0", f"QG{x} cg{x} bg{x} 0 {m}"]
        for i, vce in enumerate(self.vces):
            out += [f"VH{i}{x} ch{i}{x} 0 {n(s * vce)}", ibsrc(f"BH{i}{x}", f"bh{i}{x}", s),
                    f"QH{i}{x} ch{i}{x} bh{i}{x} 0 {m}"]
        for j, ratio in enumerate(self.ratios):
            out += sat_body(m, s, x, ratio, self.clamp, j == 0)
        out += [f"VR{x} er{x} 0 {n(s * self.vec_r)}", ibsrc(f"BR{x}", f"br{x}", s), f"QR{x} 0 br{x} er{x} {m}"]
        return out

    def saves(self, x):
        out = ["V(x)", f"I(VG{x})", f"V(bg{x})"]
        for i in range(len(self.vces)):
            out += [f"I(VH{i}{x})", f"V(bh{i}{x})"]
        for j, ratio in enumerate(self.ratios):
            r = sat_names(ratio, j == 0)
            out += [f"V(cs{r}{x})", f"V(bs{r}{x})"]
        return out + [f"I(VR{x})", f"V(br{x})"]

    def tail(self, s):
        return [".model DCLMP D(Is=1e-14)"] + sweep_tail(self.sw)

    def measure(self, d, s, x, derived):
        values, curves, codes, der = {}, {}, {}, {}
        xs = whole(d, "v(x)", sweep_points(self.sw))
        ib = [10 ** v for v in xs]
        i5 = self.vces.index(5.0) if 5.0 in self.vces else 0
        ic_h = {vce: signed(d, f"I(VH{i}{x})", -s) for i, vce in enumerate(self.vces)}
        vb_h = {vce: signed(d, f"V(bh{i}{x})", s) for i, vce in enumerate(self.vces)}
        # runs: the operating point at IB = 10 µA, VCE = 5 V (or the first VCE)
        v5 = self.vces[i5]
        k = min(range(len(xs)), key=lambda j: abs(xs[j] + 5))
        values["bjt-runs"] = {"runs": True, "error_class": "", "ic_op": ic_h[v5][k], "vbe_op": vb_h[v5][k]}
        sane = VBE_RANGE[0] < vb_h[v5][k] < VBE_RANGE[1] and ic_h[v5][k] > ib[k]
        codes["bjt-runs"] = "ok" if sane else "suspect"
        # the Gummel plot
        values["bjt-gummel"], curves["bjt-gummel"], codes["bjt-gummel"] = self.gummel(
            ib, signed(d, f"I(VG{x})", -s), signed(d, f"V(bg{x})", s))
        # hFE and VBE against IC at each VCE
        v, c, code, more = self.hfe(ib, ic_h, vb_h, v5)
        values["bjt-hfe-ic"], curves["bjt-hfe-ic"], codes["bjt-hfe-ic"] = v, c, code
        der.update(more)
        # the 25 °C leg of the temperature measurement: hFE and VBE at 5 V, and the saturation voltages at IC/IB = 10
        curves["bjt-temperature"] = {"hFE, 25°C": c.get(f"hFE, VCE={si(v5, 'V')}", []), "VBE, 25°C": c.get(f"VBE, VCE={si(v5, 'V')}", []),
                                     "IC, 25°C": c.get(f"IC, VCE={si(v5, 'V')}", [])}
        for ic_t in self.cond("bjt-temperature")["ic_points"]:
            der[f"_hfe25@{si(ic_t, 'A')}"] = v.get(f"hfe@{si(ic_t, 'A')},{si(v5, 'V')}")
            der[f"_vbe25@{si(ic_t, 'A')}"] = v.get(f"vbe@{si(ic_t, 'A')},{si(v5, 'V')}")
        # saturation, at each forced ratio; the first ratio's curves are also the 25 °C leg of the temperature measurement
        sv, sc, scode = {}, {}, "n/a"
        for j, ratio in enumerate(self.ratios):
            r = sat_names(ratio, j == 0)
            v1, c1, code1 = saturation(self.cat, ib, signed(d, f"V(cs{r}{x})", s), signed(d, f"V(bs{r}{x})", s), ratio, self.clamp, summary=(j == 0))
            sv.update(v1)
            sc.update(c1)
            if code1 == "ok":
                scode = "ok"
            if j == 0 and c1:
                curves["bjt-temperature"]["VCE(sat), 25°C"] = c1[f"VCE(sat), IC/IB={int(ratio)}"]
                curves["bjt-temperature"]["VBE(sat), 25°C"] = c1[f"VBE(sat), IC/IB={int(ratio)}"]
        values["bjt-saturation"], curves["bjt-saturation"], codes["bjt-saturation"] = sv, sc, scode
        # reverse
        icr = signed(d, f"I(VR{x})", -s)
        ibr = num.loglog_interp(*num.monotone(icr, ib), 1e-3)
        values["bjt-reverse"] = {"hfe_reverse@1mA": (1e-3 / ibr) if ibr else None}
        codes["bjt-reverse"] = "ok" if ibr else "n/a"
        return values, curves, codes, der

    def gummel(self, isrc, ic, vb):
        # the source feeds the base node, and the collector draws from that node through VG: the base
        # current is what the source gives less what the collector takes; a collector current that peaks and
        # falls as the drive rises (NK > 1) is cut at its peak, the falling branch being the card's artefact
        keep = num.until_peak(ic)
        pts = [(c, b - c, v) for c, b, v in zip(ic[:keep], isrc[:keep], vb[:keep]) if c > 0 and b - c > 0]
        if len(pts) < 5:
            return {}, {}, "n/a"
        xs = [math.log10(c) for c, _, _ in pts if 1e-5 <= c <= 1e-3]
        ys = [v for c, _, v in pts if 1e-5 <= c <= 1e-3]
        if len(xs) < 5:
            xs = [math.log10(c) for c, _, _ in pts]
            ys = [v for _, _, v in pts]
        slope, icpt = num.linfit(xs, ys)
        vals = {}
        if slope and slope > 0:
            vals["n_fit"] = slope / num.DECADE_MV_25
            vals["is_fit"] = 10 ** (-icpt / slope)
            vals["fit_window"] = [10 ** min(xs), 10 ** max(xs)]
        hfe = [c / b for c, b, _ in pts]
        kp = max(range(len(hfe)), key=lambda j: hfe[j])
        peak = hfe[kp]
        vals["hfe_peak"], vals["ic_at_hfe_peak"] = peak, pts[kp][0]
        ics = [p[0] for p in pts]
        low = num.loglog_interp(*num.monotone(ics, hfe), 1e-6)
        vals["hfe_low_ratio"] = low / peak if low else None
        knee = None
        for j in range(kp + 1, len(hfe)):
            if hfe[j] <= peak / 2:
                knee = num.loglog_interp([hfe[j], hfe[j - 1]], [ics[j], ics[j - 1]], peak / 2) or ics[j]
                break
        vals["ikf_knee"] = knee
        # the classic plot: both currents against VBE, on the catalogue's linear VBE grid
        g = self.grid("bjt-gummel")
        vbes = [p[2] for p in pts]
        cur = {"IC": num.on_grid(vbes, ics, g, log_x=False, log_y=True),
               "IB": num.on_grid(vbes, [p[1] for p in pts], g, log_x=False, log_y=True)}
        return vals, cur, "ok"

    def hfe(self, ib, ic_h, vb_h, v5):
        c = self.cond("bjt-hfe-ic")
        vals, cur, der = {}, {}, {}
        suspect = 0
        per_vce = {}
        peaks = {}
        for vce, ic in ic_h.items():
            # a collector current that peaks and falls as the drive rises is cut at its peak (the falling branch
            # would give two base currents for one collector current)
            keep = num.until_peak(ic)
            if keep < len(ic) and vb_h[vce][keep - 1] < vce:
                peaks[vce] = ic[keep - 1]
            xs, ibs = num.monotone(ic[:keep], ib[:keep])
            _, vbs = num.monotone(ic[:keep], vb_h[vce][:keep])
            hfes = [a / b for a, b in zip(xs, ibs)]
            per_vce[vce] = (xs, ibs, vbs, hfes)
            for i_t in c["ic_ladder"]:
                ibx = num.loglog_interp(xs, ibs, i_t)
                vbe = num.log_interp(xs, vbs, i_t)
                if ibx is None:
                    continue
                h = i_t / ibx
                if h > SUSPECT_HFE or vbe is None or not VBE_RANGE[0] < vbe < VBE_RANGE[1]:
                    suspect += 1
                    continue
                vals[f"hfe@{si(i_t, 'A')},{si(vce, 'V')}"] = h
                vals[f"vbe@{si(i_t, 'A')},{si(vce, 'V')}"] = vbe
                if vce == v5:
                    der[f"ib@{si(i_t, 'A')}"] = ibx
                    der[f"vbe@{si(i_t, 'A')}"] = vbe
            g = self.grid("bjt-hfe-ic")
            cur[f"hFE, VCE={si(vce, 'V')}"] = num.on_grid(xs, hfes, g, log_y=True)
            cur[f"VBE, VCE={si(vce, 'V')}"] = num.on_grid(xs, vbs, g)
            # the same sweep the other way round: IC against VBE, on a VBE grid
            name = f"IC, VCE={si(vce, 'V')}"
            cur[name] = num.on_grid(vbs, xs, curve_grid(self.cat, "bjt-hfe-ic", name), log_x=False, log_y=True)
        # the card's own ceiling (NK > 1) peaks at the same current whatever the collector voltage; a peak that
        # moves with VCE, or shows at one voltage only, is the transistor saturated through its own resistances
        # by an absurd drive, which is physics and not published
        others = [v for v in ic_h if v > v5]
        if v5 in peaks and others and all(v in peaks and abs(peaks[v] - peaks[v5]) <= 0.1 * peaks[v5] for v in others):
            vals["ic_peak"] = peaks[v5]
        xs, ibs, vbs, hfes = per_vce[v5]
        # the base current and VBE at the noise bench's currents too, which the hFE ladder may not hold
        for i_t in (self.cat.get("bjt-noise") or {}).get("conditions", {}).get("ic_ladder", []):
            k = si(float(i_t), "A")
            if f"ib@{k}" not in der:
                ibx, vbe = num.loglog_interp(xs, ibs, float(i_t)), num.log_interp(xs, vbs, float(i_t))
                if ibx and vbe is not None and float(i_t) / ibx <= SUSPECT_HFE and VBE_RANGE[0] < vbe < VBE_RANGE[1]:
                    der[f"ib@{k}"], der[f"vbe@{k}"] = ibx, vbe
        sane = [j for j, (h, vb) in enumerate(zip(hfes, vbs)) if h <= SUSPECT_HFE and VBE_RANGE[0] < vb < VBE_RANGE[1]]
        if sane:
            kp = max(sane, key=lambda j: hfes[j])
            if True:
                vals["hfe_peak"], vals["ic_at_hfe_peak"] = hfes[kp], xs[kp]
                der["ic_at_hfe_peak"] = xs[kp]
            der["ic_max_converged"] = xs[-1]
            band = [h for a, h in zip(xs, hfes) if 1e-4 <= a <= 1e-2 and h <= SUSPECT_HFE]
            if band:
                vals["hfe_flatness"] = max(band) / min(band)
        a, b = vals.get("hfe@1mA,10V"), vals.get("hfe@1mA,1V")
        if a and b:
            vals["hfe_10v_over_1v"] = a / b
        code = "ok" if any(k.startswith("hfe@") for k in vals) else ("suspect" if suspect else "n/a")
        return vals, cur, code, der


# ------------------------------------------------------------------------- the saturation region
class VceIb(Deck):
    """VCE against base current at fixed collector currents: one copy per ladder current, its collector
    pulled by a constant current source through a clamp to 30 V, its base on the log sweep."""
    name = "vceib"
    ids = ("bjt-vce-ib",)

    def __init__(self, cat):
        super().__init__(cat)
        c = self.cond("bjt-vce-ib")
        self.ladder = [float(i) for i in c["ic_ladder"]]
        self.sw = c["ib_sweep"]
        self.clamp = float(c.get("clamp_v", CLAMP))
        self.edge = float(c.get("edge_v", 1.0))

    def body(self, m, s, x, derived):
        out = []
        for k, ic in enumerate(self.ladder):
            out += [f"IV{k}{x} 0 cv{k}{x} {n(s * ic)}",
                    (f"DCV{k}{x} cv{k}{x} cl{k}{x} DCLMP" if s > 0 else f"DCV{k}{x} cl{k}{x} cv{k}{x} DCLMP"),
                    f"VCV{k}{x} cl{k}{x} 0 {n(s * self.clamp)}", ibsrc(f"BV{k}{x}", f"bv{k}{x}", s), f"QV{k}{x} cv{k}{x} bv{k}{x} 0 {m}"]
        return out

    def saves(self, x):
        return ["V(x)"] + [f"V(cv{k}{x})" for k in range(len(self.ladder))]

    def tail(self, s):
        return [".model DCLMP D(Is=1e-14)"] + sweep_tail(self.sw)

    def measure(self, d, s, x, derived):
        ib = [10 ** v for v in whole(d, "v(x)", sweep_points(self.sw))]
        g = self.grid("bjt-vce-ib")
        vals, cur = {}, {}
        for k, ic in enumerate(self.ladder):
            vce = signed(d, f"V(cv{k}{x})", s)
            key = si(ic, "A")
            on = [(b, v) for b, v in zip(ib, vce) if v < self.clamp - 1]
            if len(on) < 3:
                vals[f"ib_edge@{key}"] = None
                continue
            xs, ys = num.monotone([p[0] for p in on], [p[1] for p in on])
            cur[f"VCE, IC={key}"] = num.on_grid(xs, ys, g)
            # the edge of saturation: the first base current at which the collector has come down to the edge voltage
            vals[f"ib_edge@{key}"] = num.crossing(xs, ys, self.edge, 0.0, False)
        code = "ok" if cur else "n/a"
        return {"bjt-vce-ib": vals}, {"bjt-vce-ib": cur}, {"bjt-vce-ib": code}, {}


# ------------------------------------------------------------------------ output characteristics
class Tracer(Deck):
    """The curve tracer's families: IC against VCE at equal steps of base current. One family per universal
    step (copies IU/VU/QU, one for any model), and the auto family (copies IK/VK/QK) whose top step is the
    current that gave the catalogue's top IC at its VCE in the hFE sweep."""
    name = "tracer"
    ids = ("bjt-tracer",)
    pack_limit = 2      # 85 copies a model: ten models would be 850 transistors in one deck

    def __init__(self, cat):
        super().__init__(cat)
        c = self.cond("bjt-tracer")
        self.n_steps = int(c["steps"])
        self.top = c["top"]
        self.steps = [float(v) for v in c.get("ib_steps") or []]
        self.sw = c["vce_sweep"]

    def step(self, derived):
        ib = derived.get(f"ib@{si(float(self.top['ic']), 'A')}")
        return ib / self.n_steps if ib else None

    def ready(self, derived):
        return bool(self.steps) or self.step(derived) is not None

    def body(self, m, s, x, derived):
        st = self.step(derived)
        out = []
        for k in range(1, self.n_steps + 1 if st else 1):
            out += [f"IK{k}{x} 0 bk{k}{x} {n(s * st * k)}", f"VK{k}{x} sw ck{k}{x} 0", f"QK{k}{x} ck{k}{x} bk{k}{x} 0 {m}"]
        for j, step in enumerate(self.steps, 1):
            for k in range(1, self.n_steps + 1):
                out += [f"IU{j}{k}{x} 0 bu{j}{k}{x} {n(s * step * k)}", f"VU{j}{k}{x} sw cu{j}{k}{x} 0", f"QU{j}{k}{x} cu{j}{k}{x} bu{j}{k}{x} 0 {m}"]
        return out

    def saves(self, x):
        return ["V(sw)"] + [f"I(VK{k}{x})" for k in range(1, self.n_steps + 1)] \
            + [f"I(VU{j}{k}{x})" for j in range(1, len(self.steps) + 1) for k in range(1, self.n_steps + 1)]

    def tail(self, s):
        return ["VSW sw 0 0", f".dc VSW {n(float(self.sw['from']))} {n(s * float(self.sw['to']))} {n(s * float(self.sw['step']))}"]

    def measure(self, d, s, x, derived):
        st = self.step(derived)
        whole(d, "V(sw)", step_points(self.sw))
        v = signed(d, "V(sw)", s)
        g = self.grid("bjt-tracer")
        top = float(self.sw["to"])
        cur, vals = {}, {"ib_step": st}
        families = [("auto", "VK", "")] + [(f"IB step={si(step, 'A')}", "VU", str(j)) for j, step in enumerate(self.steps, 1)]
        for label, elem, j in families:
            for k in range(1, self.n_steps + 1):
                try:
                    ic = signed(d, f"I({elem}{j}{k}{x})", s)
                except KeyError:
                    continue
                vs, ics = num.monotone(v, ic)
                cur[f"IC, step {k}, {label}"] = num.on_grid(vs, ics, g, log_x=False)
                if label == "auto" and k == self.n_steps:
                    # a sweep's last point may fall a rounding short of its end: read the top trace where it ends
                    vals[f"ic@{si(top, 'V')},step{k}"] = num.interp(vs, ics, min(top, vs[-1])) if vs else None
        if not cur:
            return {"bjt-tracer": vals}, {}, {"bjt-tracer": "n/a"}, {}
        return {"bjt-tracer": vals}, {"bjt-tracer": cur}, {"bjt-tracer": "ok"}, {}


class Early(Deck):
    name = "early"
    ids = ("bjt-early",)

    def __init__(self, cat):
        super().__init__(cat)
        c = self.cond("bjt-early")
        self.targets = [float(t) for t in c["ic_targets"]]
        self.sw = c["vce_sweep"]

    def steps(self, derived):
        return [(i, t, derived.get(f"ib@{si(t, 'A')}")) for i, t in enumerate(self.targets)
                if derived.get(f"ib@{si(t, 'A')}")]

    def ready(self, derived):
        return bool(self.steps(derived))

    def body(self, m, s, x, derived):
        out = []
        for i, _, ib in self.steps(derived):
            out += [f"IE{i}{x} 0 be{i}{x} {n(s * ib)}", f"VE{i}{x} sw ce{i}{x} 0", f"QE{i}{x} ce{i}{x} be{i}{x} 0 {m}"]
        return out

    def saves(self, x):
        return ["V(sw)"] + [f"I(VE{i}{x})" for i in range(len(self.targets))]

    def tail(self, s):
        return ["VSW sw 0 0", f".dc VSW {n(float(self.sw['from']))} {n(s * float(self.sw['to']))} {n(s * float(self.sw['step']))}"]

    def measure(self, d, s, x, derived):
        whole(d, "V(sw)", step_points(self.sw))
        v = signed(d, "V(sw)", s)
        vals, cur = {}, {}
        g = self.grid("bjt-early")
        absent = 0
        for i, t, _ in self.steps(derived):
            try:
                ic = signed(d, f"I(VE{i}{x})", s)
            except KeyError:
                continue
            vs, ics = num.monotone(v, ic)
            ic5, ic10 = num.interp(vs, ics, 5.0), num.interp(vs, ics, 10.0)
            key = si(t, "A")
            if ic5 and ic10:
                slope = (ic10 - ic5) / 5.0
                if slope > 0 and ic5 / slope - 5.0 < 1e4:
                    vals[f"va@{key}"] = ic5 / slope - 5.0
                else:
                    vals[f"va@{key}"] = None
                    absent += 1
                if t == 1e-3:
                    vals["hoe@1mA,5V"] = slope if slope > 0 else None
                knee = next((a for a, b in zip(vs, ics) if b >= 0.9 * ic5), None)
                vals[f"vce_knee@{key}"] = knee
            cur[f"IC, {key}"] = num.on_grid(vs, ics, g, log_x=False)
        code = "ok" if any(v is not None for k, v in vals.items() if k.startswith("va@")) else ("absent" if absent else "n/a")
        return {"bjt-early": vals}, {"bjt-early": cur}, {"bjt-early": code}, {}


class HParams(Deck):
    name = "hparams"
    ids = ("bjt-early",)
    analysis = "ac"

    def __init__(self, cat):
        super().__init__(cat)
        c = self.cond("bjt-early")["h_parameters"]
        self.ic, self.vce, self.f = float(c["ic"]), float(c["vce"]), float(c["f"])

    def ready(self, derived):
        return bool(derived.get(f"ib@{si(self.ic, 'A')}"))

    def body(self, m, s, x, derived):
        ib = derived[f"ib@{si(self.ic, 'A')}"]
        return [f"VCA{x} ca{x} 0 {n(s * self.vce)}", f"IBA{x} 0 ba{x} DC {n(s * ib)} AC 1", f"QA{x} ca{x} ba{x} 0 {m}",
                f"VCB{x} cb{x} 0 DC {n(s * self.vce)} AC 1", f"IBB{x} 0 bb{x} DC {n(s * ib)}", f"QB{x} cb{x} bb{x} 0 {m}"]

    def saves(self, x):
        return [f"V(ba{x})", f"V(bb{x})", f"I(VCA{x})", f"I(VCB{x})"]

    def tail(self, s):
        return [f".ac dec 10 {n(self.f / 10)} {n(self.f * 10)}"]

    def measure(self, d, s, x, derived):
        fr = freq(d)
        pick = lambda name: num.at_x(fr, mag(d, name), self.f)  # noqa: E731
        key = si(self.ic, "A")
        vals = {f"hie@{key}": pick(f"V(ba{x})"),
                f"hre@{key}": pick(f"V(bb{x})"), f"hoe_ac@{key}": pick(f"I(VCB{x})")}
        return {"bjt-early": vals}, {}, {}, {}


# -------------------------------------------------------------------------------- capacitances
class Cap(Deck):
    name = "cap"
    ids = ("bjt-capacitance",)
    analysis = "ac"

    def __init__(self, cat):
        super().__init__(cat)
        c = self.cond("bjt-capacitance")
        self.vs = [float(v) for v in c["v_ladder"]]
        self.vo = self.vs + [float(v) for v in c.get("cob_extra") or []]    # Cob alone goes on to high voltage
        self.f = float(c["f"])

    def body(self, m, s, x, derived):
        out = []
        for i, v in enumerate(self.vo):
            out += [f"VO{i}{x} ao{i}{x} 0 DC {n(s * v)} AC 1", f"VBO{i}{x} bo{i}{x} 0 0", f"REO{i}{x} eo{i}{x} 0 1e9",
                    f"QO{i}{x} ao{i}{x} bo{i}{x} eo{i}{x} {m}"]
            if i < len(self.vs):
                out += [f"VI{i}{x} ai{i}{x} 0 DC {n(s * v)} AC 1", f"VBI{i}{x} bi{i}{x} 0 0", f"RCI{i}{x} ci{i}{x} 0 1e9",
                        f"QI{i}{x} ci{i}{x} bi{i}{x} ai{i}{x} {m}"]
        return out

    def saves(self, x):
        return [f"I(VO{i}{x})" for i in range(len(self.vo))] + [f"I(VI{i}{x})" for i in range(len(self.vs))]

    def tail(self, s):
        return [f".ac dec 10 {n(self.f / 10)} {n(self.f * 10)}"]

    def series_c(self, fr, current):
        """The capacitance at the test frequency as a capacitance meter reads a junction: the series-equivalent
        capacitance of the impedance the 1 V source sees, Cs = |I|² / (ω |Im I|). For a junction of picofarads
        it equals the parallel reading |Im I| / ω to a part in a million; for the nanofarads of a power
        transistor's emitter junction it is the only reading the card's base resistance in series does not
        pull down (Cp = Cs / (1 + (ωRC)²)). A card with no capacitance reads zero, not the infinite series
        capacitance of a pure conductance."""
        y = num.at_x(fr, current, self.f)
        w = 2 * math.pi * self.f
        cp = abs(y.imag) / w
        return cp if cp <= 1e-16 else abs(y) ** 2 / (w * abs(y.imag))

    def measure(self, d, s, x, derived):
        fr = freq(d)
        vals, cob, cib = {}, [], []
        for i, v in enumerate(self.vo):
            co = self.series_c(fr, vec(d, f"I(VO{i}{x})"))
            vals[f"cob@{si(v, 'V')}"] = co
            cob.append(co)
            if i < len(self.vs):
                ci = self.series_c(fr, vec(d, f"I(VI{i}{x})"))
                vals[f"cib@{si(v, 'V')}"] = ci
                cib.append(ci)
        c1, c10 = vals.get("cob@1V"), vals.get("cob@10V")
        if c1 and c10 and c10 > 0:
            vals["cob_1v_over_10v"] = c1 / c10
            vals["cob_m"] = math.log(c1 / c10) / math.log(10.7 / 1.7)
        code = "ok" if max(cob) > 1e-16 else "absent"
        return {"bjt-capacitance": vals}, {"bjt-capacitance": {"Cob": cob, "Cib": cib}}, {"bjt-capacitance": code}, {}


# ----------------------------------------------------------------------------------- fT against IC
class Ft(Deck):
    """One copy per ladder current and collector voltage with 1 A of AC on the base: |h21| against frequency
    gives fT, and at 1 kHz it is the small-signal gain hfe. The first voltage's copies keep the bare names
    the catalogue quotes (VCT, IBT, QT); the next ones are lettered U, W."""
    name = "ft"
    ids = ("bjt-ft", "bjt-hfe-ac")
    analysis = "ac"
    TAGS = "TUW"

    def __init__(self, cat):
        super().__init__(cat)
        c = self.cond("bjt-ft")
        self.vces = listed(c["vce"])
        self.ladder = [float(i) for i in c["ic_ladder"]]
        self.sw = c["ac_sweep"]
        self.f_ac = float(self.cond("bjt-hfe-ac")["f"])
        self.read_at = [float(f) for f in c.get("read_at") or []]

    def steps(self, derived):
        return [(i, t, derived.get(f"ib@{si(t, 'A')}")) for i, t in enumerate(self.ladder) if derived.get(f"ib@{si(t, 'A')}")]

    def ready(self, derived):
        return bool(self.steps(derived))

    def body(self, m, s, x, derived):
        out = []
        for j, vce in enumerate(self.vces):
            tg = self.TAGS[j]
            for i, _, ib in self.steps(derived):
                out += [f"VC{tg}{i}{x} c{tg.lower()}{i}{x} 0 {n(s * vce)}", f"IB{tg}{i}{x} 0 b{tg.lower()}{i}{x} DC {n(s * ib)} AC 1",
                        f"Q{tg}{i}{x} c{tg.lower()}{i}{x} b{tg.lower()}{i}{x} 0 {m}"]
        return out

    def saves(self, x):
        return [f"I(VC{self.TAGS[j]}{i}{x})" for j in range(len(self.vces)) for i in range(len(self.ladder))]

    def tail(self, s):
        return [f".ac dec {int(self.sw['per_decade'])} {n(float(self.sw['from']))} {n(float(self.sw['to']))}"]

    def measure(self, d, s, x, derived):
        fr = freq(d)
        vals, hcur, ac, ftcur, accur = {}, {}, {}, {}, {}
        code = "absent"
        grid = num.grid_points(self.grid("bjt-ft"))
        g_ac = num.grid_points(self.grid("bjt-hfe-ac"))
        for j, vce in enumerate(self.vces):
            tg, vk = self.TAGS[j], si(vce, "V")
            fts, by_ic, ac_by_ic = [], {}, {}
            at_f = {f: {} for f in self.read_at}
            for i, t, ib in self.steps(derived):
                try:
                    h = mag(d, f"I(VC{tg}{i}{x})")
                except KeyError:
                    fts.append(None)
                    continue
                key = f"{si(t, 'A')},{vk}"
                # the small-signal gain: |h21| at the catalogue's audio frequency
                hfe = num.log_interp(fr, h, self.f_ac)
                if hfe:
                    ac[f"hfe_ac@{key}"], ac_by_ic[t] = hfe, hfe
                    if j == 0 and t == 1e-3 and ib:
                        ac["hfe_ac_over_hfe@1mA"] = hfe / (t / ib)
                    # the beta cut-off: where |hfe| has fallen to 1/√2 of its low-frequency value
                    level = hfe / math.sqrt(2)
                    fb = None
                    for k in range(1, len(h)):
                        if h[k - 1] >= level > h[k]:
                            fb = math.exp(num.interp([math.log(h[k]), math.log(h[k - 1])], [math.log(fr[k]), math.log(fr[k - 1])], math.log(level)))
                            break
                    vals[f"f_beta@{key}"] = fb
                name = f"|hfe|, {si(t, 'A')}, VCE={vk}"
                hcur[name] = num.on_grid(fr, h, curve_grid(self.cat, "bjt-ft", name), log_y=True)
                unity = None
                for k in range(1, len(h)):
                    if h[k - 1] >= 1 > h[k]:
                        unity = math.exp(num.interp([math.log(h[k]), math.log(h[k - 1])], [math.log(fr[k]), math.log(fr[k - 1])], 0.0))
                        break
                band = [(abs(math.log(hh / 5)), hh * f) for hh, f in zip(h, fr) if 2 <= hh <= 10]
                ft = min(band)[1] if band else unity
                vals[f"ft@{key}"], vals[f"ft_unity@{key}"] = ft, unity
                # fT the way most sheets measure it: |hfe| at a fixed frequency, times that frequency; only where
                # that frequency is above the beta cut-off (below it the product underestimates) and |hfe| is 1.5 or
                # more (near unity the base-collector capacitance feeds the drive through and the product is noise)
                fb = vals.get(f"f_beta@{key}")
                for f_read in self.read_at:
                    hf = num.loglog_interp(fr, h, f_read)
                    ok = hf is not None and hf >= 1.5 and fb is not None and f_read >= fb
                    vals[f"ft_at@{key},{si(f_read, 'Hz')}"] = hf * f_read if ok else None
                    if ok:
                        at_f[f_read][t] = hf * f_read
                fts.append(ft)
                by_ic[t] = ft
            good = [(f, t) for f, (_, t, _) in zip(fts, self.steps(derived)) if f]
            if j == 0 and good:
                peak, at = max(good)
                vals["ft_peak"], vals["ic_at_ft_peak"] = peak, at
                vals["ft_rolloff"] = good[-1][0] / peak
            if good:
                code = "ok"
            ftcur[f"fT, VCE={vk}"] = [by_ic.get(g) for g in grid]
            for f_read, got in at_f.items():
                ftcur[f"fT at {si(f_read, 'Hz')}, VCE={vk}"] = [got.get(g) for g in grid]
            accur[f"hfe at 1 kHz, VCE={vk}"] = [ac_by_ic.get(g) for g in g_ac]
        return ({"bjt-ft": vals, "bjt-hfe-ac": ac}, {"bjt-ft": {**ftcur, **hcur}, "bjt-hfe-ac": accur},
                {"bjt-ft": code, "bjt-hfe-ac": "ok" if ac else "n/a"}, {})


# ----------------------------------------------------------------------------------- temperature
class Temp(Deck):
    ids = ("bjt-temperature",)

    def __init__(self, cat, temp):
        super().__init__(cat)
        self.temp = float(temp)
        self.name = f"temp{int(temp)}"
        c = self.cond("bjt-temperature")
        self.vce = float(c["vce"])
        self.sw = c["ib_sweep"]
        self.points = [float(i) for i in c["ic_points"]]
        sat = self.cond("bjt-saturation")
        self.ratio = listed(sat["forced_hfe"])[0]
        self.clamp = float(sat.get("clamp_v", CLAMP))

    def body(self, m, s, x, derived):
        return [f"VT{x} ct{x} 0 {n(s * self.vce)}", ibsrc(f"BT{x}", f"bt{x}", s), f"QT{x} ct{x} bt{x} 0 {m}"] \
            + sat_body(m, s, x, self.ratio, self.clamp, True)

    def saves(self, x):
        return ["V(x)", f"I(VT{x})", f"V(bt{x})", f"V(cs{x})", f"V(bs{x})"]

    def tail(self, s):
        return [".model DCLMP D(Is=1e-14)"] + sweep_tail(self.sw)

    def measure(self, d, s, x, derived):
        ib = [10 ** v for v in whole(d, "v(x)", sweep_points(self.sw))]
        ic = signed(d, f"I(VT{x})", -s)
        keep = num.until_peak(ic)
        xs, ibs = num.monotone(ic[:keep], ib[:keep])
        _, vbs = num.monotone(ic[:keep], signed(d, f"V(bt{x})", s)[:keep])
        der = {}
        for i_t in self.points:
            ibx = num.loglog_interp(xs, ibs, i_t)
            der[f"_hfe{int(self.temp)}@{si(i_t, 'A')}"] = (i_t / ibx) if ibx and i_t / ibx <= SUSPECT_HFE else None
            der[f"_vbe{int(self.temp)}@{si(i_t, 'A')}"] = num.log_interp(xs, vbs, i_t)
        hfes = [a / b for a, b in zip(xs, ibs)]
        g = self.grid("bjt-temperature")
        t = tlabel(self.temp)
        cur = {f"hFE, {t}": num.on_grid(xs, hfes, g, log_y=True), f"VBE, {t}": num.on_grid(xs, vbs, g),
               f"IC, {t}": num.on_grid(vbs, xs, curve_grid(self.cat, "bjt-temperature", f"IC, {t}"), log_x=False, log_y=True)}
        _, sc, _ = saturation(self.cat, ib, signed(d, f"V(cs{x})", s), signed(d, f"V(bs{x})", s), self.ratio, self.clamp, summary=False)
        for q in ("VCE(sat)", "VBE(sat)"):
            if f"{q}, IC/IB={int(self.ratio)}" in sc:
                cur[f"{q}, {t}"] = sc[f"{q}, IC/IB={int(self.ratio)}"]
        return {}, {"bjt-temperature": cur}, {}, der


# ------------------------------------------------------------------------- breakdown and leakage
class Breakdown(Deck):
    ids = ("bjt-breakdown",)

    def __init__(self, cat, which):
        super().__init__(cat)
        self.which = which
        self.name = f"bv{which}"
        c = self.cond("bjt-breakdown")
        self.sw = c[{"ceo": "vce_sweep", "cbo": "vcb_sweep", "ebo": "veb_sweep"}[which]]
        self.i_br = float(c["breakdown_current"])
        self.leak = c["leakage_points"]

    def body(self, m, s, x, derived):
        if self.which == "ceo":
            return [f"VA{x} sw ca{x} 0", f"RBA{x} ba{x} 0 1e6", f"QA{x} ca{x} ba{x} 0 {m}"]
        if self.which == "cbo":
            return [f"VA{x} sw ca{x} 0", f"REA{x} ea{x} 0 1e9", f"QA{x} ca{x} 0 ea{x} {m}"]
        return [f"VA{x} sw ea{x} 0", f"RCA{x} ca{x} 0 1e9", f"QA{x} ca{x} 0 ea{x} {m}"]

    def saves(self, x):
        return ["V(sw)", f"I(VA{x})"]

    def tail(self, s):
        return ["VSW sw 0 0", f".dc VSW {n(float(self.sw['from']))} {n(s * float(self.sw['to']))} {n(s * float(self.sw['step']))}"]

    def measure(self, d, s, x, derived):
        whole(d, "V(sw)", step_points(self.sw))
        v, i = num.monotone(signed(d, "V(sw)", s), signed(d, f"I(VA{x})", s))
        i_abs = [abs(z) for z in i]
        vbr = num.crossing(v, i_abs, self.i_br, -1.0, True)
        vals = {f"vbr_{self.which}": vbr}
        leak = {"ceo": ("iceo@10V", float(self.leak["iceo"])), "cbo": ("icbo@10V", float(self.leak["icbo"])),
                "ebo": ("iebo@5V", float(self.leak["iebo"]))}[self.which]
        vals[leak[0]] = num.interp(v, i_abs, leak[1])
        return {"bjt-breakdown": vals}, {}, {}, {}


# ------------------------------------------------------------------------------------- switching
class Switching(Deck):
    ids = ("bjt-switching",)
    analysis = "tran"
    pack = False

    def __init__(self, cat, ic, vcc=None, pulse=None):
        super().__init__(cat)
        self.c = self.cond("bjt-switching")
        vccs = listed(self.c["vcc"])
        pulses = self.c["pulses"]
        self.ic = float(ic)
        self.vcc = float(vcc) if vcc is not None else vccs[0]
        # the pulse: its on time, the time watched after it and the largest step, scaled together so that a
        # long pulse costs a deck about what a short one does
        self.p = pulse if pulse is not None else pulses[0]
        self.t_on = float(self.p["t_on_s"])
        first_pulse = self.t_on == float(pulses[0]["t_on_s"])
        # the first supply and the first pulse keep the deck names the catalogue quotes
        self.name = (f"sw{si(ic, 'A')}" + ("" if self.vcc == vccs[0] else f"-{si(self.vcc, 'V')}")
                     + ("" if first_pulse else f"-{si(self.t_on, 's')}"))
        self.wave = [float(w) for w in self.c.get("waveforms") or [self.ic]]
        self.label = ("" if self.vcc == vccs[0] else f", VCC={si(self.vcc, 'V')}") + ("" if first_pulse else f", {si(self.t_on, 's')}")

    def body(self, m, s, x, derived):
        c = self.c
        rl, rb = self.vcc / self.ic, float(c["rb_times_ic"]) / self.ic
        t0, e, t_on = float(c["t_start_s"]), float(c["edge_s"]), self.t_on
        lo, hi = s * float(c["v_off"]), s * float(c["v_on"])
        t1 = t0 + e + t_on
        pwl = f"0 {n(lo)} {n(t0)} {n(lo)} {n(t0 + e)} {n(hi)} {n(t1)} {n(hi)} {n(t1 + e)} {n(lo)}"
        return [f"VCC vcc 0 {n(s * self.vcc)}", f"RL vcc cs {n(rl)}", "VS cs c 0", f"VIN in 0 PWL({pwl})",
                f"RB in b {n(rb)}", f"Q1 c b 0 {m}"]

    def saves(self, x):
        return ["V(in)", "I(VS)"]

    def tail(self, s):
        c = self.c
        step = float(self.p["max_step_s"])
        end = float(c["t_start_s"]) + 2 * float(c["edge_s"]) + self.t_on + float(self.p["t_after_s"])
        return [f".tran {n(step)} {n(end)} 0 {n(step)}"]

    def measure(self, d, s, x, derived):
        c = self.c
        t = vec(d, "time")
        ic = signed(d, "I(VS)", s)
        vin = signed(d, "V(in)", s)
        t0, e, t_on = float(c["t_start_s"]), float(c["edge_s"]), self.t_on
        t1 = t0 + e + t_on
        lo, hi = float(c["v_off"]), float(c["v_on"])
        on_pts = [b for a, b in zip(t, ic) if t1 - 0.2 * t_on <= a <= t1]
        key = f"{si(self.ic, 'A')},{si(self.vcc, 'V')},{si(self.t_on, 's')}"
        vals = {f"{k}@{key}": None for k in ("td", "tr", "ts", "tf", "qs")}
        published = any(abs(w - self.ic) <= 1e-9 * w for w in self.wave)
        curves = {"bjt-switching": {f"IC(t), {si(self.ic, 'A')}{self.label}": num.thin(t, ic, int(c["curve_points"]))}} if published else {}
        on = sum(on_pts) / len(on_pts) if on_pts else 0.0
        # how far the collector current got by the end of the pulse: below 0.9 the step did not switch, and
        # the number says how far it was from it
        vals[f"on@{key}"] = on / self.ic
        if on < 0.9 * self.ic:
            return {"bjt-switching": vals}, curves, {"bjt-switching": "n/a"}, {}
        t_in_rise = num.crossing(t, vin, lo + 0.1 * (hi - lo), 0, True)
        t10 = num.crossing(t, ic, 0.1 * on, 0, True)
        t90 = num.crossing(t, ic, 0.9 * on, 0, True)
        t_in_fall = num.crossing(t, vin, hi - 0.1 * (hi - lo), t1 - e, False)
        f90 = num.crossing(t, ic, 0.9 * on, t1, False)
        f10 = num.crossing(t, ic, 0.1 * on, t1, False)
        if t_in_rise is not None and t10 is not None:
            vals[f"td@{key}"] = t10 - t_in_rise
        if t10 is not None and t90 is not None:
            vals[f"tr@{key}"] = t90 - t10
        if t_in_fall is not None and f90 is not None:
            vals[f"ts@{key}"] = f90 - t_in_fall
            vals[f"qs@{key}"] = (f90 - t_in_fall) * self.ic / float(c["forced_hfe"])
        if f90 is not None and f10 is not None:
            vals[f"tf@{key}"] = f10 - f90
        return {"bjt-switching": vals}, curves, {"bjt-switching": "ok"}, {}


# ----------------------------------------------------------------------------------------- noise
class Noise(Deck):
    ids = ("bjt-noise",)
    analysis = "noise"
    pack = False

    def __init__(self, cat, ic, rg):
        super().__init__(cat)
        self.ic, self.rg = float(ic), float(rg)
        self.name = f"noise{si(ic, 'A')}-{si(rg, 'Ω') if rg else '0'}"
        c = self.cond("bjt-noise")
        self.vce = float(c["vce"])
        self.sw = c["noise_sweep"]

    def ready(self, derived):
        return bool(derived.get(f"ib@{si(self.ic, 'A')}")) and derived.get(f"vbe@{si(self.ic, 'A')}") is not None

    def body(self, m, s, x, derived):
        ib, vbe = derived[f"ib@{si(self.ic, 'A')}"], derived[f"vbe@{si(self.ic, 'A')}"]
        return ["VSENSE c cc 0", f"VC cc 0 {n(s * self.vce)}", f"IB 0 b DC {n(s * ib)}", f"VIN in 0 DC {n(s * vbe)} AC 1",
                f"RG in b {n(self.rg) if self.rg else '0.001'}", f"Q1 c b 0 {m}", "H1 out 0 VSENSE 1000", "RLOAD out 0 1meg"]

    def tail(self, s):
        return [f".noise V(out) VIN dec {int(self.sw['per_decade'])} {n(float(self.sw['from']))} {n(float(self.sw['to']))}"]

    def measure(self, d, s, x, derived):
        f = freq(d)
        name = derived.get("_plot_name", "")
        on = mag(d, "v(onoise_spectrum)") if "v(onoise_spectrum)" in d else mag(d, "v(onoise)")
        if "v(inoise_spectrum)" in d or "v(inoise)" in d:
            inn = mag(d, "v(inoise_spectrum)") if "v(inoise_spectrum)" in d else mag(d, "v(inoise)")
        else:
            g = mag(d, "v(gain)") if "v(gain)" in d else mag(d, "gain")
            inn = [o / gg for o, gg in zip(on, g)]
        if "^2" in name:
            inn = [math.sqrt(v) for v in inn]
        key = f"_noise@{si(self.ic, 'A')}@{si(self.rg, 'Ω') if self.rg else '0'}"
        return {}, {}, {}, {key: [f, inn]}


# ------------------------------------------------------------------------------------ distortion
class ThdProbe(Deck):
    """A short run at a small amplitude, to learn the stage's gain for the model."""
    name = "thd-probe"
    ids = ("bjt-distortion",)
    analysis = "tran"
    pack = False
    AMP = 0.02

    def __init__(self, cat):
        super().__init__(cat)
        self.c = self.cond("bjt-distortion")

    def amplitude(self, derived):
        return self.AMP

    def cycles(self):
        return 3

    def body(self, m, s, x, derived):
        c = self.c
        return [f"VCC vcc 0 {n(s * float(c['vcc']))}", f"RL vcc c {n(float(c['rl']))}",
                f"VIN in 0 SIN(0 {n(self.amplitude(derived))} {n(float(c['f']))})", f"RS in b {n(float(c['rs']))}",
                f"RE e x {n(float(c['re']))}", "CX x 0 1", f"IE x vee {n(s * float(c['ie']))}", f"VEE vee 0 {n(-s * 5)}",
                f"Q1 c b e {m}"]

    def saves(self, x):
        return ["V(c)"]

    def tail(self, s):
        c = self.c
        period = 1 / float(c["f"])
        step = period / int(c["steps_per_cycle"])
        return [f".tran {n(step)} {n(period * self.cycles())} 0 {n(step)}"]

    def window(self, d):
        c = self.c
        t, vc = vec(d, "time"), vec(d, "v(c)")
        period = 1 / float(c["f"])
        k = min(int(c["analysed_cycles"]), self.cycles() - 1)
        t1 = t[-1]
        t0 = t1 - k * period
        samples = num.resample(t, vc, t0, t1, k * int(c["steps_per_cycle"]))
        return k, samples

    def measure(self, d, s, x, derived):
        k, samples = self.window(d)
        fund = num.goertzel(samples, k)
        return {}, {}, {}, {"thd_gain": fund / self.AMP if fund else None}


class Thd(ThdProbe):
    name = "thd"

    def ready(self, derived):
        return bool(derived.get("thd_gain"))

    def amplitude(self, derived):
        return min(float(self.c["vout_peak"]) / derived["thd_gain"], 0.5)

    def cycles(self):
        return int(self.c["cycles"])

    def measure(self, d, s, x, derived):
        k, samples = self.window(d)
        amps = [num.goertzel(samples, k * h) for h in range(1, 11)]
        h1 = amps[0]
        if not h1:
            return {"bjt-distortion": {}}, {}, {"bjt-distortion": "n/a"}, {}
        thd = math.sqrt(sum(a * a for a in amps[1:])) / h1
        vals = {"thd": thd, "hd2": amps[1] / h1, "hd3": amps[2] / h1, "vout_peak": h1}
        return {"bjt-distortion": vals}, {}, {"bjt-distortion": "ok"}, {}


# ------------------------------------------------------------------------------------------ plan
def plan(cat, engine):
    """Every bipolar deck in the order their dependencies need, for the measurements this engine runs."""
    decks = [DcMain(cat), VceIb(cat), Tracer(cat), Early(cat), HParams(cat), Cap(cat), Ft(cat)]
    decks += [Temp(cat, t) for t in cat["bjt-temperature"]["conditions"]["temps_c"] if float(t) != 25.0]
    decks += [Breakdown(cat, w) for w in ("ceo", "cbo", "ebo")]
    swc = cat["bjt-switching"]["conditions"]
    decks += [Switching(cat, ic, vcc, p) for p in swc["pulses"] for vcc in listed(swc["vcc"]) for ic in swc["ic_ladder"]]
    nz = cat["bjt-noise"]["conditions"]
    decks += [Noise(cat, ic, rg) for ic in nz["ic_ladder"] for rg in nz["rg"]]
    decks += [Noise(cat, nz["nf"]["ic"], nz["nf"]["rg"])]
    decks += [ThdProbe(cat), Thd(cat)]
    return [dk for dk in decks if all(engine in cat[i]["engines"] for i in dk.ids)]


def finalize(cat, values, curves, derived):
    """What needs several decks: the temperature ratios and slopes, the noise spectra into en, in, NF."""
    # temperature
    c = cat["bjt-temperature"]["conditions"]
    temps = sorted(float(t) for t in c["temps_c"])
    hot, cold = int(max(temps)), int(min(temps))
    out = {}
    for i_t in c["ic_points"]:
        k = si(i_t, "A")
        h25 = derived.get(f"_hfe25@{k}")
        for t in temps:
            ht = derived.get(f"_hfe{int(t)}@{k}")
            if t != 25 and h25 and ht:
                out[f"hfe_{'m' if t < 0 else ''}{abs(int(t))}_over_25@{k}"] = ht / h25
    v_hot, v_cold = derived.get(f"_vbe{hot}@1mA"), derived.get(f"_vbe{cold}@1mA")
    if v_hot is not None and v_cold is not None:
        out["dvbe_dt@1mA"] = (v_hot - v_cold) / (hot - cold)
    if out:
        values.setdefault("bjt-temperature", {}).update(out)
        ratios = [v for k, v in out.items() if k.startswith("hfe_")]
        values.setdefault("bjt-temperature", {})
        code = "absent" if ratios and all(abs(r - 1) < 1e-3 for r in ratios) else "ok"
        values["bjt-temperature"]["_code"] = code
    # the slope of VBE with temperature against IC, over each span of the three temperatures
    tc = curves.get("bjt-temperature") or {}
    for a, b in zip([int(t) for t in temps], [int(t) for t in temps[1:]]):
        va, vb_ = tc.get(f"VBE, {tlabel(a)}"), tc.get(f"VBE, {tlabel(b)}")
        if va and vb_:
            tc[f"dVBE/dT, {tlabel(a)[:-2]} to {tlabel(b)}"] = [((q - p) / (b - a)) if p is not None and q is not None else None
                                                             for p, q in zip(va, vb_)]
    # the on voltages: VBE(on) at 5 V, VBE(sat) and VCE(sat) at the first forced ratio, on one grid
    ov = cat.get("bjt-on-voltages")
    hc, sc = curves.get("bjt-hfe-ic") or {}, curves.get("bjt-saturation") or {}
    if ov:
        ratio = int(listed(cat["bjt-saturation"]["conditions"]["forced_hfe"])[0])
        vk = si(float(ov["conditions"]["vce"]), "V")
        g_ov = num.grid_points(ov["grid"])
        g_h = num.grid_points(cat["bjt-hfe-ic"]["grid"])
        g_s = num.grid_points(cat["bjt-saturation"]["grid"])

        def onto(src, g_src):
            """a curve on another grid, read at this one's points (they are a subset of the same decades)"""
            if not src:
                return None
            out = []
            for xg in g_ov:
                k = min(range(len(g_src)), key=lambda j: abs(math.log(g_src[j] / xg)))
                out.append(src[k] if abs(math.log(g_src[k] / xg)) < 1e-6 and k < len(src) else None)
            return out
        got = {"VBE(sat), IC/IB=10": onto(sc.get(f"VBE(sat), IC/IB={ratio}"), g_s),
               f"VBE(on), VCE={vk}": onto(hc.get(f"VBE, VCE={vk}"), g_h),
               "VCE(sat), IC/IB=10": onto(sc.get(f"VCE(sat), IC/IB={ratio}"), g_s)}
        got = {k: v for k, v in got.items() if v and any(p is not None for p in v)}
        if got:
            curves["bjt-on-voltages"] = got
            a = (values.get("bjt-saturation") or {}).get(f"vbesat@1mA,{ratio}")
            b = (values.get("bjt-hfe-ic") or {}).get(f"vbe@1mA,{vk}")
            values["bjt-on-voltages"] = {"vbe_sat_rise@1mA": (a - b) if a is not None and b is not None else None, "_code": "ok"}
    # the switching times against the switched current
    sw = cat["bjt-switching"]["conditions"]
    sv = values.get("bjt-switching") or {}
    if sv:
        cur = curves.setdefault("bjt-switching", {})
        vccs = listed(sw["vcc"])
        t_ons = [float(p["t_on_s"]) for p in sw["pulses"]]
        for t_on in t_ons:
            pk = si(t_on, "s")
            for vcc in vccs:
                vk = si(vcc, "V")
                for k in ("td", "tr", "ts", "tf"):
                    pts = [sv.get(f"{k}@{si(float(ic), 'A')},{vk},{pk}") for ic in sw["ic_ladder"]]
                    if any(p is not None for p in pts):
                        cur[k + ("" if vcc == vccs[0] else f", VCC={vk}") + ("" if t_on == t_ons[0] else f", {pk}")] = pts
    # noise
    nz = cat["bjt-noise"]["conditions"]
    rg0, rg1 = [float(r) for r in nz["rg"]][:2]
    vals = {}
    spectra = {}
    for ic in nz["ic_ladder"]:
        k = si(ic, "A")
        en = derived.get(f"_noise@{k}@0")
        tot = derived.get(f"_noise@{k}@{si(rg1, 'Ω')}")
        if not en:
            continue
        f, e = en
        inn = None
        if tot:
            f2, t2 = tot
            inn = [math.sqrt(max(b * b - a * a - 4 * K_B * T_K * rg1, 0.0)) / rg1 for a, b in zip(e, t2)]
        for fp in nz["f_points"]:
            vals[f"en@{si(fp, 'Hz')},{k}"] = num.at_x(f, e, float(fp))
            if inn:
                vals[f"in@{si(fp, 'Hz')},{k}"] = num.at_x(f, inn, float(fp))
        e10k = num.at_x(f, e, 1e4)
        corner = None
        if e10k:
            for a, b in sorted(zip(f, e), reverse=True):
                if a <= 1e4 and b >= math.sqrt(2) * e10k:
                    corner = a
                    break
        vals[f"en_corner@{k}"] = corner
        spectra[k] = (f, e, inn)
    nfc = nz["nf"]
    k_nf = si(nfc["ic"], "A")
    tot = derived.get(f"_noise@{k_nf}@{si(float(nfc['rg']), 'Ω')}")
    if tot:
        f, t2 = tot
        v = num.at_x(f, t2, float(nfc["f"]))
        vals[f"nf@{si(nfc['f'], 'Hz')},{k_nf},{si(float(nfc['rg']), 'Ω')}"] = 10 * math.log10(v * v / (4 * K_B * T_K * float(nfc["rg"])))
    a, b = vals.get("en@10kHz,10mA"), vals.get("en@10kHz,100µA")
    if a and b:
        vals["en_floor_ratio"] = a / b
    if vals:
        values["bjt-noise"] = vals
        g = cat["bjt-noise"].get("grid")
        cur = {}
        # the spectra at every current
        for k, (f, e, inn) in spectra.items():
            cur[f"en, {k}"] = num.on_grid(f, e, g, log_y=True)
            if inn:
                cur[f"in, {k}"] = num.on_grid(f, inn, g, log_y=True)
        # en and in against current, one curve per frequency point
        ics = [si(float(ic), "A") for ic in nz["ic_ladder"]]
        for fp in nz["f_points"]:
            fk = si(float(fp), "Hz")
            for q in ("en", "in"):
                pts = [vals.get(f"{q}@{fk},{k}") for k in ics]
                if any(v is not None for v in pts):
                    cur[f"{q} at {fk}"] = pts
        # the total input noise and the noise figure against source resistance, from en and in at the
        # sheets' frequency, their correlation neglected as the sheets neglect it
        f_nf = float(nz["nf"]["f"])
        for k, (f, e, inn) in spectra.items():
            if not inn:
                continue
            en1, in1 = num.at_x(f, e, f_nf), num.at_x(f, inn, f_nf)
            if not en1 or in1 is None:
                continue
            rs = num.grid_points(curve_grid(cat, "bjt-noise", f"NF, {k}"))
            vt = [math.sqrt(en1 * en1 + in1 * in1 * r * r + 4 * K_B * T_K * r) for r in rs]
            cur[f"VT, {k}"] = vt
            cur[f"NF, {k}"] = [10 * math.log10(v * v / (4 * K_B * T_K * r)) for v, r in zip(vt, rs)]
            # wideband: the densities integrated over the band, trapezoids on the sweep's own points
            band = nz.get("band")
            if band:
                lo, hi = float(band[0]), float(band[1])
                pts = [(a, e2, i2) for a, e2, i2 in zip(f, e, inn) if lo <= a <= hi and e2 is not None and i2 is not None]
                if len(pts) >= 2:
                    def integral(g):
                        return sum((pts[j + 1][0] - pts[j][0]) * (g(pts[j]) + g(pts[j + 1])) / 2 for j in range(len(pts) - 1))
                    e_int, i_int = integral(lambda p: p[1] ** 2), integral(lambda p: p[2] ** 2)
                    width = pts[-1][0] - pts[0][0]
                    tot = [e_int + i_int * r * r + 4 * K_B * T_K * r * width for r in rs]
                    cur[f"VT wideband, {k}"] = [math.sqrt(t) for t in tot]
                    cur[f"NF wideband, {k}"] = [10 * math.log10(t / (4 * K_B * T_K * r * width)) for t, r in zip(tot, rs)]
                    if k == si(float(nz["nf"]["ic"]), "A"):
                        r0 = float(nz["nf"]["rg"])
                        vals[f"nf_wide@1mA,{si(r0, 'Ω')[:-1]}"] = 10 * math.log10((e_int + i_int * r0 * r0 + 4 * K_B * T_K * r0 * width) / (4 * K_B * T_K * r0 * width))
        curves["bjt-noise"] = cur
        values["bjt-noise"]["_code"] = "ok"
