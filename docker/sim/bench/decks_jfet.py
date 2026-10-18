"""The JFET decks of the characterisation bench: one class per netlist, serving the `jfet-*` measurements of
data/bench/measurements.yaml whose conditions it reads (docs/fet-characterisation.md).

Same shape as the bipolar decks (`decks_bjt`): `body` gives one copy's element lines, `saves` its vectors,
`tail` the shared sweep and analysis, `measure` the values, curves, codes and derived points of the ids the
deck serves, and `finalize` what needs several decks. The gate is driven from a voltage source (no junction
to force a current into); the sign `s` is +1 for an N-channel and −1 for a P-channel, every source is
multiplied by it and every reading divided by it, so a P-channel publishes the numbers an N-channel would.
Standard library only.
"""

import math

from bench import num
from bench.decks_bjt import Deck, curve_grid, freq, listed, mag, signed, step_points, tlabel, vec, whole
from bench.num import K_B, T_K, n, si

VGS_OFF_FLOOR = 1e-8      # A: the drain current VGS(off) is read at when the model's ladder gives nothing else
GMIN_FLOOR = 1e-10        # A: below this a gate current is the simulators' gmin conductance, not the card
RDS_ABSENT = 1e9          # Ω: a channel the sweep never opened


def lin_points(sw):
    return step_points(sw)


def nz(x):
    """A number as the netlists write it, with a negative zero written as 0 (a P-channel copy at VGS = 0)."""
    return n(x + 0.0)


def dc_line(name, sw, s):
    """A linear sweep of a voltage source, reversed for a P-channel."""
    return f".dc {name} {n(s * float(sw['from']))} {n(s * float(sw['to']))} {n(s * float(sw['step']))}"


def parallel_c(fr, current, f):
    """The capacitance at f from the AC current of a 1 V drive: the quadrature part over ω. The in-phase part
    is a conductance (the transconductance, when the drain is read with the channel open) and is left out,
    which is what a guarded meter does; a level-1 card has no series gate resistance to pull the reading
    down, so the series-equivalent form the bipolar bench needs is not needed here."""
    y = num.at_x(fr, current, f)
    return abs(y.imag) / (2 * math.pi * f)


def cubic_fit(xs, ys):
    """Least-squares a1, a2, a3 of y = a0 + a1 x + a2 x² + a3 x³ (normal equations, 4 × 4)."""
    m = len(xs)
    if m < 8:
        return None
    rows = [[sum(x ** (i + j) for x in xs) for j in range(4)] for i in range(4)]
    rhs = [sum(y * x ** i for x, y in zip(xs, ys)) for i in range(4)]
    a = [r + [b] for r, b in zip(rows, rhs)]
    for c in range(4):
        p = max(range(c, 4), key=lambda r: abs(a[r][c]))
        a[c], a[p] = a[p], a[c]
        if abs(a[c][c]) < 1e-300:
            return None
        for r in range(4):
            if r != c:
                k = a[r][c] / a[c][c]
                a[r] = [u - k * v for u, v in zip(a[r], a[c])]
    return [a[i][4] / a[i][i] for i in range(4)]


def ladder_points(ladder, derived):
    """(current, gate voltage) per ladder current: the voltage the transfer sweep found, or None where the model
    never reached the current. Every current keeps its copy so that the deck's vectors are the same for every
    model; an unreached copy's gate sits at twice VGS(off), the channel closed, and is not read."""
    return [(i, derived.get(f"_vgs@{si(i, 'A')}")) for i in ladder]


def gate_or_off(vgs, derived):
    return vgs if vgs is not None else 2 * (derived.get("_vgs_off") or -10.0)


# ----------------------------------------------------------------------------------- the transfer sweep
class Transfer(Deck):
    """One gate sweep, one copy per drain voltage: IDSS, VGS(off), the square law, and the gate current along
    the way; the 25 °C leg of the temperature measurement; and the model's own points the later decks need."""
    name = "transfer"
    ids = ("jfet-runs", "jfet-transfer")

    def __init__(self, cat):
        super().__init__(cat)
        c = self.cond("jfet-transfer")
        self.vds = [float(v) for v in c["vds"]]
        self.sw = c["vgs_sweep"]
        self.off_at = [float(i) for i in c["vgs_off_currents"]]
        self.ladder = [float(i) for i in c["id_ladder"]]
        self.window = [float(w) for w in c["fit_window"]]
        self.v_main = float(self.cond("jfet-runs")["vds"])

    def body(self, m, s, x, derived):
        out = []
        for i, v in enumerate(self.vds):
            out += [f"VT{i}{x} dt{i}{x} 0 {n(s * v)}", f"VIG{i}{x} g gi{i}{x} 0", f"JT{i}{x} dt{i}{x} gi{i}{x} 0 {m}"]
        return out

    def saves(self, x):
        return ["V(g)"] + [f"I(VT{i}{x})" for i in range(len(self.vds))] + [f"I(VIG{i}{x})" for i in range(len(self.vds))]

    def tail(self, s):
        return ["VGS g 0 0", dc_line("VGS", self.sw, s)]

    def measure(self, d, s, x, derived):
        vg = whole(d, "V(g)", lin_points(self.sw))
        vg = [s * v for v in vg]
        k_main = self.vds.index(self.v_main) if self.v_main in self.vds else 0
        ids = {v: signed(d, f"I(VT{i}{x})", -s) for i, v in enumerate(self.vds)}
        igs = {v: signed(d, f"I(VIG{i}{x})", s) for i, v in enumerate(self.vds)}
        vals, cur, der = {}, {}, {}
        vm = self.vds[k_main]
        idss = num.interp(vg, ids[vm], 0.0)
        runs = {"runs": True, "error_class": "", "idss_op": idss, "ig_op": num.interp(vg, igs[vm], 0.0)}
        codes = {"jfet-runs": "ok" if idss and idss > 0 else "suspect"}
        g = self.grid("jfet-transfer")
        for v in self.vds:
            cur_id = ids[v]
            vals[f"idss@{si(v, 'V')}"] = num.interp(vg, cur_id, 0.0)
            # VGS(off): the gate voltage where the current has fallen to each defining current, read from the
            # low side so that a current that rises again below pinch-off (a card's leakage) is not taken
            for i_off in self.off_at:
                vals[f"vgs_off@{si(i_off, 'A')},{si(v, 'V')}"] = self.off_voltage(vg, cur_id, i_off)
            for i_t in self.ladder:
                vals[f"vgs@{si(i_t, 'A')},{si(v, 'V')}"] = self.vgs_at(vg, cur_id, i_t)
            cur[f"ID, VDS={si(v, 'V')}"] = num.on_grid(vg, cur_id, g, log_x=False)
            cur[f"ID log, VDS={si(v, 'V')}"] = num.on_grid(vg, cur_id, g, log_x=False, log_y=True)
        # the square law on the main curve
        main = ids[vm]
        vp = vals.get(f"vgs_off@{si(VGS_OFF_FLOOR, 'A')},{si(vm, 'V')}") or vals.get(f"vgs_off@1µA,{si(vm, 'V')}")
        if idss and idss > 0 and vp is not None and vp < 0:
            pts = [(math.log(-vp + a), math.log(b)) for a, b in zip(vg, main)
                   if -vp + a > 0 and self.window[0] * idss <= b <= self.window[1] * idss]
            slope, _ = num.linfit([p[0] for p in pts], [p[1] for p in pts]) if len(pts) >= 4 else (None, None)
            vals["n_fit"] = slope
            gfs0 = self.slope_at(vg, main, 0.0)
            vals["gfs_vp_over_idss"] = (gfs0 * -vp / idss) if gfs0 else None
            der["_vgs_off"] = vp
            der["_idss"] = idss
            der["_vgs_third"] = self.vgs_at(vg, main, idss / 3)
            der["_id_third"] = idss / 3
        a, b = vals.get(f"idss@{si(self.vds[-1], 'V')}"), vals.get(f"idss@{si(self.vds[0], 'V')}")
        if a and b:
            vals[f"idss_{si(self.vds[-1], 'V').lower()}_over_{si(self.vds[0], 'V').lower()}"] = a / b
        for i_t in self.ladder:
            w = vals.get(f"vgs@{si(i_t, 'A')},{si(vm, 'V')}")
            if w is not None:
                der[f"_vgs@{si(i_t, 'A')}"] = w
        # the stage used by the frequency, noise and distortion decks: ID = IDSS/3 at VDS = 9 V from 18 V
        st = (self.cat.get("jfet-distortion") or {}).get("conditions") or {}
        if der.get("_vgs_third") is not None and der["_id_third"] > 0 and st:
            vdd, vds = float(st["vdd"]), float(st["vds"])
            rs = -der["_vgs_third"] / der["_id_third"]
            der["_rs_stage"] = rs
            der["_rd_stage"] = max((vdd - vds - (-der["_vgs_third"])) / der["_id_third"], 1.0)
        code = "ok" if any(k.startswith("vgs_off@") and v is not None for k, v in vals.items()) else "n/a"
        codes["jfet-transfer"] = code
        tcur = {"jfet-temperature": {"ID, 25°C": cur[f"ID, VDS={si(vm, 'V')}"]}}
        der["_idss25"] = idss
        der["_vgsoff25"] = vp
        return ({"jfet-runs": runs, "jfet-transfer": vals}, {"jfet-transfer": cur, **tcur}, codes, der)

    @staticmethod
    def off_voltage(vg, cur, level):
        """The first gate voltage, from the negative end, at which the current reaches `level`."""
        return num.crossing(vg, cur, level, vg[0] - 1, True)

    @staticmethod
    def vgs_at(vg, cur, level):
        keep = [(a, b) for a, b in zip(vg, cur) if a <= 0]
        if not keep:
            return None
        return num.crossing([p[0] for p in keep], [p[1] for p in keep], level, keep[0][0] - 1, True)

    @staticmethod
    def slope_at(vg, cur, v0, h=0.02):
        a, b = num.interp(vg, cur, v0 - h), num.interp(vg, cur, v0 + h)
        return (b - a) / (2 * h) if a is not None and b is not None else None


# ------------------------------------------------------------------------------------ the curve tracer
class Tracer(Deck):
    """ID against VDS at equal steps of gate voltage: one family per universal step (copies VGU/VU/JU) and the
    auto family (VGK/VK/JK) whose step is a fifth of the model's own VGS(off). Trace k sits at
    VGS = −(steps − k) × step, so the top trace (k = steps) is VGS = 0."""
    name = "tracer"
    ids = ("jfet-tracer",)
    pack_limit = 3

    def __init__(self, cat):
        super().__init__(cat)
        c = self.cond("jfet-tracer")
        self.n_steps = int(c["steps"])
        self.steps = [float(v) for v in c["vgs_steps"]]
        self.divisor = float(c["auto"]["divisor"])
        self.sw = c["vds_sweep"]

    def step(self, derived):
        vp = derived.get("_vgs_off")
        return -vp / self.divisor if vp else None

    def ready(self, derived):
        return self.step(derived) is not None

    def body(self, m, s, x, derived):
        st = self.step(derived)
        out = []
        for k in range(1, self.n_steps + 1):
            out += [f"VGK{k}{x} gk{k}{x} 0 {nz(-s * st * (self.n_steps - k))}", f"VK{k}{x} sw dk{k}{x} 0", f"JK{k}{x} dk{k}{x} gk{k}{x} 0 {m}"]
        for j, step in enumerate(self.steps, 1):
            for k in range(1, self.n_steps + 1):
                out += [f"VGU{j}{k}{x} gu{j}{k}{x} 0 {nz(-s * step * (self.n_steps - k))}", f"VU{j}{k}{x} sw du{j}{k}{x} 0",
                        f"JU{j}{k}{x} du{j}{k}{x} gu{j}{k}{x} 0 {m}"]
        return out

    def saves(self, x):
        return ["V(sw)"] + [f"I(VK{k}{x})" for k in range(1, self.n_steps + 1)] \
            + [f"I(VU{j}{k}{x})" for j in range(1, len(self.steps) + 1) for k in range(1, self.n_steps + 1)]

    def tail(self, s):
        return ["VSW sw 0 0", dc_line("VSW", self.sw, s)]

    def measure(self, d, s, x, derived):
        whole(d, "V(sw)", lin_points(self.sw))
        v = signed(d, "V(sw)", s)
        g = self.grid("jfet-tracer")
        top = float(self.sw["to"])
        st = self.step(derived)
        cur, vals = {}, {"vgs_step": st}
        families = [("auto", "VK", "")] + [(f"VGS step={si(step, 'V')}", "VU", str(j)) for j, step in enumerate(self.steps, 1)]
        for label, elem, j in families:
            for k in range(1, self.n_steps + 1):
                ids = signed(d, f"I({elem}{j}{k}{x})", s)
                vs, idv = num.monotone(v, ids)
                cur[f"ID, step {k}, {label}"] = num.on_grid(vs, idv, g, log_x=False)
                if label == "auto" and k == self.n_steps:
                    vals[f"id@{si(top, 'V')},step{k}"] = num.interp(vs, idv, min(top, vs[-1])) if vs else None
                    i10 = num.interp(vs, idv, 10.0)
                    i9, i11 = num.interp(vs, idv, 9.0), num.interp(vs, idv, 11.0)
                    if i9 is not None and i11 is not None and i10:
                        gos = (i11 - i9) / 2.0
                        vals["ro@10V,step5"] = (1 / gos) if gos > 1e-15 else None
                        vals["knee@step5"] = num.crossing(vs, idv, 0.9 * i10, -1.0, True)
        return {"jfet-tracer": vals}, {"jfet-tracer": cur}, {"jfet-tracer": "ok"}, {}


# ----------------------------------------------------------------------------- gfs and gos at 1 kHz
class Gm(Deck):
    """One copy per ladder current the transfer sweep reached, biased by the gate voltage it found, with 1 V
    of AC on the gate (gfs) or on the drain (gos)."""
    name = "gm"
    ids = ("jfet-gm",)
    analysis = "ac"

    def __init__(self, cat):
        super().__init__(cat)
        c = self.cond("jfet-gm")
        self.vds = float(c["vds"])
        self.ladder = [float(i) for i in c["id_ladder"]]
        self.f = float(c["f"])

    def points(self, derived):
        return ladder_points(self.ladder, derived)

    def ready(self, derived):
        return any(v is not None for _, v in self.points(derived))

    def body(self, m, s, x, derived):
        out = []
        for i, (_, vgs) in enumerate(self.points(derived)):
            out += [f"VD{i}{x} d{i}{x} 0 {n(s * self.vds)}", f"VG{i}{x} g{i}{x} 0 DC {n(s * gate_or_off(vgs, derived))} AC 1", f"JM{i}{x} d{i}{x} g{i}{x} 0 {m}",
                    f"VDO{i}{x} do{i}{x} 0 DC {n(s * self.vds)} AC 1", f"VGO{i}{x} go{i}{x} 0 {n(s * gate_or_off(vgs, derived))}", f"JO{i}{x} do{i}{x} go{i}{x} 0 {m}"]
        return out

    def saves(self, x):
        return [f"I(VD{i}{x})" for i in range(len(self.ladder))] + [f"I(VDO{i}{x})" for i in range(len(self.ladder))]

    def tail(self, s):
        return [f".ac dec 10 {n(self.f / 10)} {n(self.f * 10)}"]

    def measure(self, d, s, x, derived):
        fr = freq(d)
        vals, der = {}, {}
        gfs_pts, gos_pts = [], []
        for i, (i_t, vgs) in enumerate(self.points(derived)):
            if vgs is None:
                continue
            gfs = abs(num.at_x(fr, vec(d, f"I(VD{i}{x})"), self.f))
            gos = abs(num.at_x(fr, vec(d, f"I(VDO{i}{x})"), self.f))
            k = si(i_t, "A")
            vals[f"gfs@{k},{si(self.vds, 'V')}"] = gfs
            vals[f"gos@{k},{si(self.vds, 'V')}"] = gos
            vals[f"gfs_over_sqrt_id@{k}"] = gfs / math.sqrt(i_t)
            der[f"_gfs@{k}"] = gfs
            gfs_pts.append((i_t, gfs))
            gos_pts.append((i_t, gos))
            if i_t == 1e-3:
                vals["av_intrinsic@1mA"] = (gfs / gos) if gos > 1e-15 else None
                vals["va_equiv@1mA"] = (i_t / gos - self.vds) if gos > 1e-15 and i_t / gos - self.vds < 1e4 else None
        g = self.grid("jfet-gm")
        cur = {f"gfs, VDS={si(self.vds, 'V')}": num.on_grid([p[0] for p in gfs_pts], [p[1] for p in gfs_pts], g, log_y=True),
               f"gos, VDS={si(self.vds, 'V')}": num.on_grid([p[0] for p in gos_pts], [p[1] for p in gos_pts], g, log_y=True)}
        code = "ok" if gfs_pts else "n/a"
        if gos_pts and max(p[1] for p in gos_pts) <= 1e-15:
            vals["gos_note"] = "absent"
        return {"jfet-gm": vals}, {"jfet-gm": cur}, {"jfet-gm": code}, der


# ------------------------------------------------------------------------------------ the ohmic region
class Ohmic(Deck):
    """The drain swept through zero at four gate voltages (fractions of the model's VGS(off)), the gate held
    (copies VGR/VR/JR) and the gate fed VGS + VDS/2 through two 1 MΩ resistors (VGB/RF1/RF2/VF/JF)."""
    name = "ohmic"
    ids = ("jfet-ohmic",)

    def __init__(self, cat):
        super().__init__(cat)
        c = self.cond("jfet-ohmic")
        self.fractions = [float(f) for f in c["lin_vgs_fractions"]]
        self.sw = c["lin_vds_sweep"]
        self.small = float(c["vds_small"])

    def ready(self, derived):
        return derived.get("_vgs_off") is not None

    def body(self, m, s, x, derived):
        vp = derived["_vgs_off"]
        out = []
        for i, fr in enumerate(self.fractions):
            out += [f"VGR{i}{x} gr{i}{x} 0 {nz(s * fr * vp)}", f"VR{i}{x} sw dr{i}{x} 0", f"JR{i}{x} dr{i}{x} gr{i}{x} 0 {m}",
                    f"VGB{i}{x} gb{i}{x} 0 {nz(2 * s * fr * vp)}", f"RFD{i}{x} df{i}{x} gf{i}{x} 1e6", f"RFB{i}{x} gb{i}{x} gf{i}{x} 1e6",
                    f"VF{i}{x} sw df{i}{x} 0", f"JF{i}{x} df{i}{x} gf{i}{x} 0 {m}"]
        return out

    def saves(self, x):
        return ["V(sw)"] + [f"I(VR{i}{x})" for i in range(len(self.fractions))] + [f"I(VF{i}{x})" for i in range(len(self.fractions))]

    def tail(self, s):
        return ["VSW sw 0 0", dc_line("VSW", self.sw, s)]

    def measure(self, d, s, x, derived):
        whole(d, "V(sw)", lin_points(self.sw))
        v = signed(d, "V(sw)", s)
        vals, cur = {}, {}
        g = self.grid("jfet-ohmic")
        for i, fr in enumerate(self.fractions):
            tag = f"{fr:g}"
            for which, elem in (("", "VR"), ("_fb", "VF")):
                ids = signed(d, f"I({elem}{i}{x})", s)
                vs, idv = num.monotone(v, ids)
                ip, im = num.interp(vs, idv, self.small), num.interp(vs, idv, -self.small)
                if which == "":
                    rds = (2 * self.small / (ip - im)) if ip is not None and im is not None and ip - im > 0 else None
                    vals[f"rds@{tag}" if fr else "rds_on@0V"] = rds
                    cur[f"ID vs VDS ohmic, VGS={tag}"] = num.on_grid(vs, idv, g, log_x=False)
                    vmax = float(self.sw["to"])
                    i_hi, i_lo = num.interp(vs, idv, vmax), num.interp(vs, idv, -vmax)
                    if i_hi and i_lo and i_hi > 0 and i_lo < 0:
                        vals[f"rds_asym@{tag}"] = (vmax / i_hi) / (vmax / -i_lo)
                fit = cubic_fit(vs, idv)
                if fit and fit[1]:
                    vals[f"rds_hd2{which}@{tag}"] = fit[2] / fit[1]
                    if which == "":
                        vals[f"rds_hd3@{tag}"] = fit[3] / fit[1]
                if which == "_fb":
                    cur[f"ID vs VDS with feedback, VGS={tag}"] = num.on_grid(vs, idv, g, log_x=False)
        code = "ok" if vals.get("rds_on@0V") else "n/a"
        return {"jfet-ohmic": vals}, {"jfet-ohmic": cur}, {"jfet-ohmic": code}, {}


class OhmicVgs(Deck):
    """rDS at 50 mV across the drain as the gate goes from 0 to past VGS(off)."""
    name = "ohmic-vgs"
    ids = ("jfet-ohmic",)

    def __init__(self, cat):
        super().__init__(cat)
        c = self.cond("jfet-ohmic")
        self.small = float(c["vds_small"])
        self.points = int(c["vgs_points"])

    def ready(self, derived):
        return derived.get("_vgs_off") is not None

    def body(self, m, s, x, derived):
        # the gate at VGS(off) times the swept number: the sweep runs in units of the model's own pinch-off
        return [f"VDR{x} dr{x} 0 {n(s * self.small)}", f"BGR{x} gr{x} 0 V={n(s * derived['_vgs_off'])}*V(gsw)", f"JR{x} dr{x} gr{x} 0 {m}"]

    def saves(self, x):
        return ["V(gsw)", f"I(VDR{x})"]

    def tail(self, s):
        return ["VGSW gsw 0 0", f".dc VGSW 0 1.2 {n(1.2 / self.points)}"]

    def measure(self, d, s, x, derived):
        vp = derived["_vgs_off"]
        fr = list(vec(d, "V(gsw)"))                        # the gate, in units of VGS(off)
        ids = signed(d, f"I(VDR{x})", -s)
        rds = [(self.small / i) if i and i > 0 else None for i in ids]
        pts = [(a, b) for a, b in zip(fr, rds) if a is not None and b is not None]
        grid_fr = curve_grid(self.cat, "jfet-ohmic", "rDS vs VGS/VGS(off)")
        cur = {"rDS vs VGS/VGS(off)": num.on_grid([p[0] for p in pts], [p[1] for p in pts], grid_fr, log_x=False, log_y=True)}
        vals = {}
        r0 = pts[0][1] if pts else None
        if r0:
            x2 = num.crossing([p[0] for p in pts], [p[1] for p in pts], 2 * r0, -1, True)
            x10 = num.crossing([p[0] for p in pts], [p[1] for p in pts], 10 * r0, -1, True)
            vals["vgs_rds_x2"] = x2 * vp if x2 is not None else None
            vals["vgs_rds_x10"] = x10 * vp if x10 is not None else None
        return {"jfet-ohmic": vals}, {"jfet-ohmic": cur}, {}, {}


# ------------------------------------------------------------------------------------------ the gate
class GateForward(Deck):
    name = "gate-fwd"
    ids = ("jfet-gate",)

    def __init__(self, cat):
        super().__init__(cat)
        self.sw = self.cond("jfet-gate")["vg_forward"]

    def body(self, m, s, x, derived):
        return [f"VGF{x} gf{x} gsw 0", f"JF{x} 0 gf{x} 0 {m}"]

    def saves(self, x):
        return ["V(gsw)", f"I(VGF{x})"]

    def tail(self, s):
        return ["VGSW gsw 0 0", dc_line("VGSW", self.sw, s)]

    def measure(self, d, s, x, derived):
        v = [s * q for q in whole(d, "V(gsw)", lin_points(self.sw))]
        ig = signed(d, f"I(VGF{x})", -s)         # the source feeds the gate from its − node: I(VGF) is −IG
        vals = {"vg_fwd@10µA": num.crossing(v, ig, 1e-5, -1, True), "vg_fwd@1mA": num.crossing(v, ig, 1e-3, -1, True)}
        pts = [(a, math.log(b)) for a, b in zip(v, ig) if 1e-6 <= b <= 1e-4]
        if len(pts) >= 4:
            slope, icpt = num.linfit([p[0] for p in pts], [p[1] for p in pts])
            if slope and slope > 0:
                vals["n_gate"] = 1 / (slope * num.VT_25)
                vals["is_gate"] = math.exp(icpt)
        g = curve_grid(self.cat, "jfet-gate", "IG forward")
        cur = {"IG forward": num.on_grid(v, ig, g, log_x=False, log_y=True)}
        code = "ok" if vals["vg_fwd@10µA"] is not None else "absent"
        return {"jfet-gate": vals}, {"jfet-gate": cur}, {"jfet-gate": code}, {}


class GateReverse(Deck):
    name = "gate-rev"
    ids = ("jfet-gate",)

    def __init__(self, cat):
        super().__init__(cat)
        c = self.cond("jfet-gate")
        self.sw = c["vg_reverse"]
        self.points = [float(p) for p in c["igss_points"]]

    def body(self, m, s, x, derived):
        return [f"VGR{x} gr{x} gsw 0", f"JR{x} 0 gr{x} 0 {m}"]

    def saves(self, x):
        return ["V(gsw)", f"I(VGR{x})"]

    def tail(self, s):
        return ["VGSW gsw 0 0", dc_line("VGSW", self.sw, s)]

    def measure(self, d, s, x, derived):
        v = [-s * q for q in whole(d, "V(gsw)", lin_points(self.sw))]      # the reverse voltage, positive
        ig = [abs(q) for q in signed(d, f"I(VGR{x})", s)]
        vs, igs = num.monotone(v, ig)
        vals = {f"igss@{si(p, 'V')}": num.interp(vs, igs, p) for p in self.points}
        g = curve_grid(self.cat, "jfet-gate", "IG reverse")
        return {"jfet-gate": vals}, {"jfet-gate": {"IG reverse": num.on_grid(vs, igs, g, log_x=False, log_y=True)}}, {}, {}


class GateField(Deck):
    """The gate current as the drain rises, at fixed drain currents: impact ionisation, where a card has it."""
    name = "gate-field"
    ids = ("jfet-gate",)

    def __init__(self, cat):
        super().__init__(cat)
        c = self.cond("jfet-gate")
        self.sw = c["vdg_sweep"]
        self.ladder = [float(i) for i in c["field_id"]]
        self.at = [float(v) for v in c["field_points"]]

    def points(self, derived):
        return ladder_points(self.ladder, derived)

    def ready(self, derived):
        return any(v is not None for _, v in self.points(derived))

    def body(self, m, s, x, derived):
        out = []
        for i, (_, vgs) in enumerate(self.points(derived)):
            out += [f"VF{i}{x} sw df{i}{x} 0", f"VGB{i}{x} gb{i}{x} 0 {n(s * gate_or_off(vgs, derived))}", f"JD{i}{x} df{i}{x} gb{i}{x} 0 {m}"]
        return out

    def saves(self, x):
        return ["V(sw)"] + [f"I(VGB{i}{x})" for i in range(len(self.ladder))]

    def tail(self, s):
        return ["VSW sw 0 0", dc_line("VSW", self.sw, s)]

    def measure(self, d, s, x, derived):
        whole(d, "V(sw)", lin_points(self.sw))
        v = signed(d, "V(sw)", s)
        vals, cur = {}, {}
        g = curve_grid(self.cat, "jfet-gate", "IG vs VDS, ID=1mA")
        for i, (i_t, vgs) in enumerate(self.points(derived)):
            if vgs is None:
                continue
            ig = [abs(q) for q in signed(d, f"I(VGB{i}{x})", s)]
            k = si(i_t, "A")
            for p in self.at:
                vals[f"ig@{si(p, 'V')},{k}"] = num.interp(v, ig, p)
            cur[f"IG vs VDS, ID={k}"] = num.on_grid(v, ig, g, log_x=False, log_y=True)
            if i_t == 1e-3:
                a, b = vals.get(f"ig@20V,{k}"), vals.get(f"ig@5V,{k}")
                vals["ig_field_ratio@1mA"] = (a / b) if a and b and a > GMIN_FLOOR and a / b > 1.05 else None
        return {"jfet-gate": vals}, {"jfet-gate": cur}, {}, {}


# ---------------------------------------------------------------------------------------- capacitance
class Cap(Deck):
    """Per ladder voltage: Ciss and Crss from one copy at VDS = v, VGS = 0 with 1 V of AC on the gate; Cgs
    alone with the drain open; Cgd alone with the source open."""
    name = "cap"
    ids = ("jfet-capacitance",)
    analysis = "ac"

    def __init__(self, cat):
        super().__init__(cat)
        c = self.cond("jfet-capacitance")
        self.vs = [float(v) for v in c["v_ladder"]]
        self.f = float(c["f"])

    def body(self, m, s, x, derived):
        out = []
        for i, v in enumerate(self.vs):
            out += [f"VDX{i}{x} dx{i}{x} 0 {n(s * v)}", f"VGX{i}{x} gx{i}{x} 0 DC 0 AC 1", f"JX{i}{x} dx{i}{x} gx{i}{x} 0 {m}",
                    f"VGS{i}{x} gs{i}{x} 0 DC {n(-s * v)} AC 1", f"RDS{i}{x} ds{i}{x} 0 1e9", f"JS{i}{x} ds{i}{x} gs{i}{x} 0 {m}",
                    f"VDG{i}{x} dg{i}{x} 0 {n(s * v)}", f"VGG{i}{x} gg{i}{x} 0 DC 0 AC 1", f"RSG{i}{x} sg{i}{x} 0 1e9", f"JG{i}{x} dg{i}{x} gg{i}{x} sg{i}{x} {m}"]
        return out

    def saves(self, x):
        out = []
        for i in range(len(self.vs)):
            out += [f"I(VGX{i}{x})", f"I(VDX{i}{x})", f"I(VGS{i}{x})", f"I(VGG{i}{x})"]
        return out

    def tail(self, s):
        return [f".ac dec 10 {n(self.f / 10)} {n(self.f * 10)}"]

    def measure(self, d, s, x, derived):
        fr = freq(d)
        vals, cur, der = {}, {"Ciss": [], "Crss": [], "Cgs": [], "Cgd": []}, {}
        for i, v in enumerate(self.vs):
            k = si(v, "V")
            got = {"ciss": parallel_c(fr, vec(d, f"I(VGX{i}{x})"), self.f), "crss": parallel_c(fr, vec(d, f"I(VDX{i}{x})"), self.f),
                   "cgs": parallel_c(fr, vec(d, f"I(VGS{i}{x})"), self.f), "cgd": parallel_c(fr, vec(d, f"I(VGG{i}{x})"), self.f)}
            for q, c in got.items():
                vals[f"{q}@{k}"] = c
            cur["Ciss"].append(got["ciss"])
            cur["Crss"].append(got["crss"])
            cur["Cgs"].append(got["cgs"])
            cur["Cgd"].append(got["cgd"])
            if v == 10.0:
                der["_cgs@10V"], der["_cgd@10V"] = got["cgs"], got["cgd"]
        c1, c10 = vals.get("crss@1V"), vals.get("crss@10V")
        if c1 and c10 and c10 > 1e-16:
            vals["crss_m"] = math.log(c1 / c10) / math.log(11.0 / 2.0)
        a, b = vals.get("ciss@1V"), vals.get("ciss@10V")
        if a and b and b > 1e-16:
            vals["ciss_1v_over_10v"] = a / b
        code = "ok" if max(cur["Ciss"]) > 1e-16 else "absent"
        return {"jfet-capacitance": vals}, {"jfet-capacitance": cur}, {"jfet-capacitance": code}, der


# ------------------------------------------------------------------------------------------ frequency
class Yfs(Deck):
    """|yfs| against frequency at the ladder currents: the gfs copies swept to 1 GHz."""
    name = "yfs"
    ids = ("jfet-frequency",)
    analysis = "ac"

    def __init__(self, cat):
        super().__init__(cat)
        c = self.cond("jfet-frequency")
        self.vds = float(c["vds"])
        self.ladder = [float(i) for i in c["id_ladder"]]
        self.sw = c["ac_sweep"]

    def points(self, derived):
        return ladder_points(self.ladder, derived)

    def ready(self, derived):
        return any(v is not None for _, v in self.points(derived))

    def body(self, m, s, x, derived):
        out = []
        for i, (_, vgs) in enumerate(self.points(derived)):
            out += [f"VD{i}{x} d{i}{x} 0 {n(s * self.vds)}", f"VG{i}{x} g{i}{x} 0 DC {n(s * gate_or_off(vgs, derived))} AC 1", f"JY{i}{x} d{i}{x} g{i}{x} 0 {m}"]
        return out

    def saves(self, x):
        return [f"I(VD{i}{x})" for i in range(len(self.ladder))]

    def tail(self, s):
        return [f".ac dec {int(self.sw['per_decade'])} {n(float(self.sw['from']))} {n(float(self.sw['to']))}"]

    def measure(self, d, s, x, derived):
        fr = freq(d)
        vals, cur = {}, {}
        g = self.grid("jfet-frequency")
        for i, (i_t, vgs) in enumerate(self.points(derived)):
            if vgs is None:
                continue
            y = mag(d, f"I(VD{i}{x})")
            k = si(i_t, "A")
            y0 = y[0]
            # a voltage-driven gate has no series resistance in a level-1 card, so |yfs| does not fall; what it
            # does near the top is rise, as Cgd feeds the gate drive straight through: the first 3 dB departure
            # either way is reported
            f3 = num.crossing(fr, y, y0 / math.sqrt(2), 0, False)
            up = num.crossing(fr, y, y0 * math.sqrt(2), 0, True)
            vals[f"yfs_3db@{k}"] = min(v for v in (f3, up) if v is not None) if f3 is not None or up is not None else None
            cur[f"|yfs|, ID={k}"] = num.on_grid(fr, y, g, log_y=True)
            cgs, cgd = derived.get("_cgs@10V"), derived.get("_cgd@10V")
            if cgs is not None and cgd is not None and cgs + cgd > 1e-16:
                vals[f"ft_equiv@{k}"] = y0 / (2 * math.pi * (cgs + cgd))
        return {"jfet-frequency": vals}, {"jfet-frequency": cur}, {"jfet-frequency": "ok" if vals else "n/a"}, {}


class Stage(Deck):
    """The reference common-source stage, self-biased at IDSS/3, swept for its gain and bandwidth."""
    name = "stage"
    ids = ("jfet-frequency",)
    analysis = "ac"

    def __init__(self, cat):
        super().__init__(cat)
        self.c = self.cond("jfet-frequency")["stage"]
        self.st = self.cond("jfet-distortion")

    def ready(self, derived):
        return derived.get("_rs_stage") is not None and derived.get("_rd_stage") is not None

    def body(self, m, s, x, derived):
        c = self.c
        return [f"VDD{x} vdd{x} 0 {n(s * float(self.st['vdd']))}", f"RD{x} vdd{x} dc{x} {n(derived['_rd_stage'])}", f"RS{x} s{x} 0 {n(derived['_rs_stage'])}",
                f"CS{x} s{x} 0 1000u", f"RIN{x} in{x} g{x} {n(float(c['rs_in']))}", f"VIN{x} in{x} 0 AC 1", f"JS{x} dc{x} g{x} s{x} {m}"]

    def saves(self, x):
        return [f"V(dc{x})", f"I(VIN{x})"]

    def tail(self, s):
        sw = self.c["sweep"]
        return [f".ac dec {int(sw['per_decade'])} {n(float(sw['from']))} {n(float(sw['to']))}"]

    def measure(self, d, s, x, derived):
        fr = freq(d)
        av = mag(d, f"V(dc{x})")
        a1k = num.at_x(fr, av, 1e3)
        vals = {"stage_gain@1kHz": a1k, "stage_f3db": num.crossing(fr, av, a1k / math.sqrt(2), 1e3, False) if a1k else None}
        iin = num.at_x(fr, vec(d, f"I(VIN{x})"), 1e3)
        # the gate's admittance at 1 kHz is the drive current over the gate voltage, 1 V less the drop across RIN
        rin = float(self.c["rs_in"])
        vg = 1 + iin * rin if isinstance(iin, complex) else None
        vals["stage_cin@1kHz"] = abs((-iin / vg).imag) / (2 * math.pi * 1e3) if vg and abs(vg) > 1e-9 else None
        g = curve_grid(self.cat, "jfet-frequency", "stage gain")
        return {"jfet-frequency": vals}, {"jfet-frequency": {"stage gain": num.on_grid(fr, av, g, log_y=True)}}, {}, {}


# ----------------------------------------------------------------------------------------------- noise
class Noise(Deck):
    ids = ("jfet-noise",)
    analysis = "noise"
    pack = False

    def __init__(self, cat, i_d, rg):
        super().__init__(cat)
        self.i_d, self.rg = float(i_d), float(rg)
        self.name = f"noise{si(i_d, 'A')}-{si(rg, 'Ω') if rg else '0'}"
        c = self.cond("jfet-noise")
        self.vds = float(c["vds"])
        self.sw = c["noise_sweep"]

    def ready(self, derived):
        return derived.get(f"_vgs@{si(self.i_d, 'A')}") is not None

    def body(self, m, s, x, derived):
        vgs = derived[f"_vgs@{si(self.i_d, 'A')}"]
        return ["VSENSE d dd 0", f"VD dd 0 {n(s * self.vds)}", f"VIN in 0 DC {n(s * vgs)} AC 1", f"RG in g {n(self.rg) if self.rg else '0.001'}",
                f"J1 d g 0 {m}", "H1 out 0 VSENSE 1000", "RLOAD out 0 1meg"]

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
        return {}, {}, {}, {f"_noise@{si(self.i_d, 'A')}@{si(self.rg, 'Ω') if self.rg else '0'}": [f, inn]}


# ----------------------------------------------------------------------------------------- temperature
class Temp(Deck):
    ids = ("jfet-temperature",)

    def __init__(self, cat, temp):
        super().__init__(cat)
        self.temp = float(temp)
        self.name = f"temp{int(temp)}"
        c = self.cond("jfet-temperature")
        self.vds = float(c["vds"])
        self.sw = c["vgs_sweep"]

    def body(self, m, s, x, derived):
        return [f"VT{x} dt{x} 0 {n(s * self.vds)}", f"JT{x} dt{x} g 0 {m}"]

    def saves(self, x):
        return ["V(g)", f"I(VT{x})"]

    def tail(self, s):
        return ["VGS g 0 0", dc_line("VGS", self.sw, s)]

    def measure(self, d, s, x, derived):
        vg = [s * v for v in whole(d, "V(g)", lin_points(self.sw))]
        ids = signed(d, f"I(VT{x})", -s)
        t = int(self.temp)
        der = {f"_idss{t}": num.interp(vg, ids, 0.0), f"_vgsoff{t}": Transfer.off_voltage(vg, ids, VGS_OFF_FLOOR)}
        g = self.grid("jfet-temperature")
        return {}, {"jfet-temperature": {f"ID, {tlabel(self.temp)}": num.on_grid(vg, ids, g, log_x=False)}}, {}, der


# -------------------------------------------------------------------------------------------- switching
class Switch(Deck):
    """The analogue switch: a 1 V signal through the channel into RL, the gate pulsed from V(off) to 0 and
    back through 1 kΩ."""
    ids = ("jfet-switch",)
    analysis = "tran"
    pack = False

    def __init__(self, cat, rl, voff):
        super().__init__(cat)
        self.c = self.cond("jfet-switch")
        self.rl = float(rl)
        self.voff = voff            # a number, or "auto" for twice the model's VGS(off)
        self.name = f"switch{si(self.rl, 'Ω')}-{'auto' if voff == 'auto' else si(float(voff), 'V')}"

    def off(self, derived):
        if self.voff == "auto":
            vp = derived.get("_vgs_off")
            return 2 * vp if vp else None
        return float(self.voff)

    def ready(self, derived):
        return self.off(derived) is not None

    def body(self, m, s, x, derived):
        c = self.c
        off = s * self.off(derived)
        e, t_on = float(c["edge_s"]), float(c["t_on_s"])
        t0 = float(c["t_start_s"])
        pwl = f"0 {n(off)} {n(t0)} {n(off)} {n(t0 + e)} 0 {n(t0 + e + t_on)} 0 {n(t0 + 2 * e + t_on)} {n(off)}"
        return [f"VS s 0 {n(s * float(c['v_signal']))}", f"JW l g s {m}", f"RL l 0 {n(self.rl)}", f"RG in g {n(float(c['rg']))}", f"VIN in 0 PWL({pwl})"]

    def saves(self, x):
        return ["V(l)"]

    def tail(self, s):
        c = self.c
        end = float(c["t_start_s"]) + 2 * float(c["edge_s"]) + float(c["t_on_s"]) + float(c["t_after_s"])
        return [f".tran {n(float(c['max_step_s']))} {n(end)} 0 {n(float(c['max_step_s']))}"]

    def measure(self, d, s, x, derived):
        c = self.c
        t = vec(d, "time")
        v = signed(d, "V(l)", s)
        t0, e, t_on = float(c["t_start_s"]), float(c["edge_s"]), float(c["t_on_s"])
        t_off = t0 + e + t_on
        on = num.interp(t, v, t_off - 0.05 * t_on)
        key = f"{si(self.rl, 'Ω')},{'auto' if self.voff == 'auto' else si(float(self.voff), 'V')}"
        vals = {}
        if not on or on < 0.05:
            return {"jfet-switch": {f"ton@{key}": None, f"toff@{key}": None}}, {}, {"jfet-switch": "n/a"}, {}
        t10, t90 = num.crossing(t, v, 0.1 * on, t0, True), num.crossing(t, v, 0.9 * on, t0, True)
        f90, f10 = num.crossing(t, v, 0.9 * on, t_off, False), num.crossing(t, v, 0.1 * on, t_off, False)
        vals[f"ton@{key}"] = (t90 - t0) if t90 is not None else None
        vals[f"toff@{key}"] = (f10 - t_off) if f10 is not None else None
        vsig = float(c["v_signal"])
        if self.voff == "auto" and self.rl == listed(c["rl"])[0] and on < vsig:
            vals["rds_on_switch"] = self.rl * (vsig - on) / on
        _ = (t10, f90)
        cur = {"jfet-switch": {f"Vload(t), RL={si(self.rl, 'Ω')}, Voff={'auto' if self.voff == 'auto' else si(float(self.voff), 'V')}": num.thin(t, v, int(c["curve_points"]))}}
        return {"jfet-switch": vals}, cur, {"jfet-switch": "ok"}, {}


class Inject(Deck):
    """Charge injection: the step a 1 nF hold capacitor takes when the gate switches off."""
    ids = ("jfet-switch",)
    analysis = "tran"
    pack = False

    def __init__(self, cat, voff):
        super().__init__(cat)
        self.c = self.cond("jfet-switch")
        self.voff = voff
        self.name = f"inject-{'auto' if voff == 'auto' else si(float(voff), 'V')}"

    def off(self, derived):
        return Switch.off(self, derived)

    def ready(self, derived):
        return self.off(derived) is not None

    def body(self, m, s, x, derived):
        c = self.c
        off = s * self.off(derived)
        e, t0 = float(c["edge_s"]), float(c["t_on_s"])
        pwl = f"0 0 {n(t0)} 0 {n(t0 + e)} {n(off)} {n(2 * t0)} {n(off)}"
        return ["VS s 0 0", f"JW l g s {m}", f"CH l 0 {n(float(c['c_hold']))}", "RLK l 0 1G", f"RG in g {n(float(c['rg']))}", f"VIN in 0 PWL({pwl})"]

    def saves(self, x):
        return ["V(l)"]

    def tail(self, s):
        c = self.c
        return [f".tran {n(float(c['max_step_s']))} {n(2 * float(c['t_on_s']))} 0 {n(float(c['max_step_s']))}"]

    def measure(self, d, s, x, derived):
        c = self.c
        t, v = vec(d, "time"), signed(d, "V(l)", s)
        t0 = float(c["t_on_s"])
        before, after = num.interp(t, v, 0.9 * t0), num.interp(t, v, 1.9 * t0)
        key = "auto" if self.voff == "auto" else si(float(self.voff), "V")
        q = float(c["c_hold"]) * (after - before) if before is not None and after is not None else None
        return {"jfet-switch": {f"q_inj@{key}": q}}, {}, {}, {}


# ------------------------------------------------------------------------------------------ distortion
class ThdProbe(Deck):
    """A short run at a small amplitude, to learn the stage's gain for the model."""
    ids = ("jfet-distortion",)
    analysis = "tran"
    pack = False
    AMP = 0.02

    def __init__(self, cat, stage="cs"):
        super().__init__(cat)
        self.c = self.cond("jfet-distortion")
        self.stage = stage
        self.name = f"thd-probe-{stage}"

    def ready(self, derived):
        return derived.get("_rs_stage") is not None and derived.get("_rd_stage") is not None

    def amplitude(self, derived):
        return self.AMP

    def cycles(self):
        return 3

    def body(self, m, s, x, derived):
        c = self.c
        out = [f"VDD vdd 0 {n(s * float(c['vdd']))}", f"RS s 0 {n(derived['_rs_stage'])}", f"RIN in g {n(float(c['rs_in']))}",
               f"VIN in 0 SIN(0 {n(self.amplitude(derived))} {n(float(c['f']))})"]
        if self.stage == "cs":
            out += [f"RD vdd d {n(derived['_rd_stage'])}", f"J1 d g s {m}"]
        else:
            out += [f"J1 vdd g s {m}"]
        return out

    def out_node(self):
        return "d" if self.stage == "cs" else "s"

    def saves(self, x):
        return [f"V({self.out_node()})"]

    def tail(self, s):
        c = self.c
        period = 1 / float(c["f"])
        step = period / int(c["steps_per_cycle"])
        return [f".tran {n(step)} {n(period * self.cycles())} 0 {n(step)}"]

    def window(self, d):
        c = self.c
        t, vo = vec(d, "time"), vec(d, f"V({self.out_node()})")
        period = 1 / float(c["f"])
        k = min(int(c["analysed_cycles"]), self.cycles() - 1)
        t1 = t[-1]
        return k, num.resample(t, vo, t1 - k * period, t1, k * int(c["steps_per_cycle"]))

    def measure(self, d, s, x, derived):
        k, samples = self.window(d)
        fund = num.goertzel(samples, k)
        return {}, {}, {}, {f"thd_gain_{self.stage}": fund / self.AMP if fund else None}


class Thd(ThdProbe):
    def __init__(self, cat, stage, level):
        super().__init__(cat, stage)
        self.level = float(level)
        self.name = f"thd-{stage}-{si(self.level, 'V')}" if stage == "cs" else "thd-sf"

    def ready(self, derived):
        return bool(derived.get(f"thd_gain_{self.stage}"))

    def target(self, derived):
        """The output level: the catalogue's, or for the follower half the quiescent drop across RS when that
        is less (a stage biased at IDSS/3 cannot swing a volt across a small RS)."""
        if self.stage == "sf":
            return min(self.level, 0.5 * derived["_rs_stage"] * derived["_id_third"])
        return self.level

    def amplitude(self, derived):
        return min(self.target(derived) / derived[f"thd_gain_{self.stage}"], 1.0)

    def cycles(self):
        return int(self.c["cycles"])

    def measure(self, d, s, x, derived):
        k, samples = self.window(d)
        amps = [num.goertzel(samples, k * h) for h in range(1, 11)]
        h1 = amps[0]
        if not h1:
            return {"jfet-distortion": {}}, {}, {"jfet-distortion": "n/a"}, {}
        tag = f"_{self.stage}@{si(self.level, 'V')}" if self.stage == "cs" else "_sf"
        thd = math.sqrt(sum(a * a for a in amps[1:])) / h1
        vals = {f"thd{tag}": thd, f"hd2{tag}": amps[1] / h1, f"hd3{tag}": amps[2] / h1, f"gain_{self.stage}": derived[f"thd_gain_{self.stage}"]}
        if self.stage == "sf":
            vals["vout_sf"] = h1
        return {"jfet-distortion": vals}, {}, {"jfet-distortion": "ok"}, {}


# ------------------------------------------------------------------------------------------- breakdown
ELEM = {"gss": "A", "dgo": "B", "dss": "C"}


class Breakdown(Deck):
    ids = ("jfet-breakdown",)

    def __init__(self, cat, which):
        super().__init__(cat)
        self.which = which
        self.name = f"bv{which}"
        c = self.cond("jfet-breakdown")
        self.sw = c[{"gss": "vgs_sweep", "dgo": "vdg_sweep", "dss": "vds_off_sweep"}[which]]
        self.i_br = float(c["breakdown_current"])
        self.leak = c["leakage_points"]

    def ready(self, derived):
        return self.which != "dss" or derived.get("_vgs_off") is not None

    def body(self, m, s, x, derived):
        if self.which == "gss":
            return [f"VA{x} sw ga{x} 0", f"RDA{x} da{x} 0 1e9", f"JA{x} da{x} ga{x} 0 {m}"]
        if self.which == "dgo":
            return [f"VB{x} sw db{x} 0", f"RSB{x} sb{x} 0 1e9", f"JB{x} db{x} 0 sb{x} {m}"]
        return [f"VC{x} sw dc{x} 0", f"VGC{x} gc{x} 0 {n(2 * s * derived['_vgs_off'])}", f"JC{x} dc{x} gc{x} 0 {m}"]

    def saves(self, x):
        return ["V(sw)", f"I(V{ELEM[self.which]}{x})"]

    def tail(self, s):
        return ["VSW sw 0 0", dc_line("VSW", self.sw, s)]

    def measure(self, d, s, x, derived):
        whole(d, "V(sw)", lin_points(self.sw))
        elem = ELEM[self.which]
        v = [abs(q) for q in signed(d, "V(sw)", s)]
        i = [abs(q) for q in signed(d, f"I(V{elem}{x})", s)]
        vs, i_abs = num.monotone(v, i)
        vbr = num.crossing(vs, i_abs, self.i_br, -1.0, True)
        vals = {f"vbr_{self.which}": vbr}
        leak = {"gss": ("igss@20V", float(self.leak["igss"])), "dgo": ("idgo@20V", float(self.leak["igss"])),
                "dss": ("id_off@15V", float(self.leak["id_off"]))}[self.which]
        vals[leak[0]] = num.interp(vs, i_abs, leak[1])
        return {"jfet-breakdown": vals}, {}, {"jfet-breakdown": "ok" if vbr is not None else "absent"}, {}


# ------------------------------------------------------------------------------------------------ plan
def plan(cat, engine):
    """Every JFET deck in the order their dependencies need, for the measurements this engine runs."""
    decks = [Transfer(cat), Tracer(cat), Gm(cat), Ohmic(cat), OhmicVgs(cat), GateForward(cat), GateReverse(cat), GateField(cat),
             Cap(cat), Yfs(cat), Stage(cat)]
    nz = cat["jfet-noise"]["conditions"]
    decks += [Noise(cat, i, rg) for i in nz["id_ladder"] for rg in nz["rg"]]
    decks += [Noise(cat, nz["nf"]["id"], nz["nf"]["rg"])]
    decks += [Temp(cat, t) for t in cat["jfet-temperature"]["conditions"]["temps_c"] if float(t) != 25.0]
    sw = cat["jfet-switch"]["conditions"]
    decks += [Switch(cat, rl, voff) for rl in listed(sw["rl"]) for voff in sw["v_off"]]
    decks += [Inject(cat, voff) for voff in sw["v_off"]]
    dc = cat["jfet-distortion"]["conditions"]
    decks += [ThdProbe(cat, "cs")] + [Thd(cat, "cs", lv) for lv in listed(dc["vout_peak"])] + [ThdProbe(cat, "sf"), Thd(cat, "sf", listed(dc["vout_peak"])[0])]
    decks += [Breakdown(cat, w) for w in ("gss", "dgo", "dss")]
    return [dk for dk in decks if all(engine in cat[i]["engines"] for i in dk.ids)]


A_WEIGHT_POLES = (20.598997, 107.65265, 737.86223, 12194.217)


def a_weight(f):
    """IEC 61672 A-weighting as a linear gain (1 at 1 kHz)."""
    p1, p2, p3, p4 = A_WEIGHT_POLES
    f2 = f * f
    ra = (p4 ** 2 * f2 * f2) / ((f2 + p1 ** 2) * math.sqrt((f2 + p2 ** 2) * (f2 + p3 ** 2)) * (f2 + p4 ** 2))
    return ra / 0.7943  # 1.0 at 1 kHz (−2 dB offset undone)


def integrate_noise(f, en, lo, hi, weight=None):
    """Volts rms over a band from a density on a log sweep: trapezoids on the sweep's own points."""
    pts = [(a, (b * (weight(a) if weight else 1.0)) ** 2) for a, b in zip(f, en) if lo <= a <= hi and b is not None]
    if len(pts) < 2:
        return None
    return math.sqrt(sum((pts[j + 1][0] - pts[j][0]) * (pts[j][1] + pts[j + 1][1]) / 2 for j in range(len(pts) - 1)))


def finalize(cat, values, curves, derived):
    """What needs several decks: the temperature drifts and the zero-TC point, the noise spectra into en,
    in, the corner, NF and the audio-band figures."""
    c = cat["jfet-temperature"]["conditions"]
    temps = sorted(float(t) for t in c["temps_c"])
    hot, cold = int(max(temps)), int(min(temps))
    out = {}
    for t in temps:
        k = int(t)
        if derived.get(f"_idss{k}") is not None:
            out[f"idss@{tlabel(t)}"] = derived[f"_idss{k}"]
        if derived.get(f"_vgsoff{k}") is not None:
            out[f"vgs_off@{tlabel(t)}"] = derived[f"_vgsoff{k}"]
    a, b = derived.get(f"_vgsoff{hot}"), derived.get(f"_vgsoff{cold}")
    if a is not None and b is not None:
        out["dvgsoff_dt"] = (a - b) / (hot - cold)
    i125, i25 = derived.get("_idss125"), derived.get("_idss25")
    if i125 and i25:
        out["idss_125_over_25"] = i125 / i25
    tc = curves.get("jfet-temperature") or {}
    c25, c125 = tc.get("ID, 25°C"), tc.get("ID, 125°C")
    g = num.grid_points(cat["jfet-temperature"]["grid"])
    ztc = None
    if c25 and c125:
        diff = [(p - q) if p is not None and q is not None else None for p, q in zip(c25, c125)]
        for j in range(1, len(g)):
            if diff[j - 1] is not None and diff[j] is not None and diff[j - 1] * diff[j] < 0 and c25[j] > 1e-6:
                w = diff[j - 1] / (diff[j - 1] - diff[j])
                ztc = (g[j - 1] + w * (g[j] - g[j - 1]), c25[j - 1] + w * (c25[j] - c25[j - 1]))
                break
    out["vgs_0tc"], out["id_0tc"] = (ztc[0], ztc[1]) if ztc else (None, None)
    if out:
        values["jfet-temperature"] = {**out, "_code": "ok" if ztc or ("idss_125_over_25" in out and abs(out["idss_125_over_25"] - 1) > 1e-3) else "absent"}
        # ID against temperature at VGS = 0 and at fractions of VGS(off), from the curves on the grid
        vp = derived.get("_vgs_off")
        if vp:
            for fr in c["vgs_points_fraction"]:
                v_at = float(fr) * vp
                pts = []
                for t in temps:
                    cv = tc.get(f"ID, {tlabel(t)}")
                    pts.append(num.interp(g, [q if q is not None else 0.0 for q in cv], v_at) if cv else None)
                tc[f"ID vs T, VGS={float(fr):g}"] = pts
    # noise
    nz = cat["jfet-noise"]["conditions"]
    rg0, rg1 = [float(r) for r in nz["rg"]][:2]
    vals, spectra = {}, {}
    _ = rg0
    for i_d in nz["id_ladder"]:
        k = si(float(i_d), "A")
        en = derived.get(f"_noise@{k}@0")
        tot = derived.get(f"_noise@{k}@{si(rg1, 'Ω')}")
        if not en:
            continue
        f, e = en
        inn = None
        if tot:
            _, t2 = tot
            inn = [math.sqrt(max(b * b - a * a - 4 * K_B * T_K * rg1, 0.0)) / rg1 for a, b in zip(e, t2)]
        for fp in nz["f_points"]:
            vals[f"en@{si(float(fp), 'Hz')},{k}"] = num.at_x(f, e, float(fp))
            if inn:
                vals[f"in@{si(float(fp), 'Hz')},{k}"] = num.at_x(f, inn, float(fp))
        e10k = num.at_x(f, e, 1e4)
        corner = None
        if e10k:
            for a, b in sorted(zip(f, e), reverse=True):
                if a <= 1e4 and b >= math.sqrt(2) * e10k:
                    corner = a
                    break
        vals[f"en_corner@{k}"] = corner
        band = nz["audio_band"]
        vals[f"vn_20_20k@{k}"] = integrate_noise(f, e, float(band[0]), float(band[1]))
        vals[f"vn_a_weighted@{k}"] = integrate_noise(f, e, float(band[0]), float(band[1]), a_weight)
        spectra[k] = (f, e, inn)
    nfc = nz["nf"]
    k_nf = si(float(nfc["id"]), "A")
    tot = derived.get(f"_noise@{k_nf}@{si(float(nfc['rg']), 'Ω')}")
    if tot:
        f, t2 = tot
        v = num.at_x(f, t2, float(nfc["f"]))
        vals[f"nf@{si(float(nfc['f']), 'Hz')},{k_nf},{si(float(nfc['rg']), 'Ω')}"] = 10 * math.log10(v * v / (4 * K_B * T_K * float(nfc["rg"])))
    ks = [si(float(i), "A") for i in nz["id_ladder"]]
    a, b = vals.get(f"en@10kHz,{ks[-1]}"), vals.get(f"en@10kHz,{ks[0]}")
    if a and b:
        vals["en_ratio_top_over_bottom"] = a / b
    if vals:
        values["jfet-noise"] = vals
        g = cat["jfet-noise"].get("grid")
        cur = {}
        for k, (f, e, inn) in spectra.items():
            cur[f"en, {k}"] = num.on_grid(f, e, g, log_y=True)
            if inn:
                cur[f"in, {k}"] = num.on_grid(f, inn, g, log_y=True)
        for fp in nz["f_points"]:
            fk = si(float(fp), "Hz")
            for q in ("en", "in"):
                pts = [vals.get(f"{q}@{fk},{k}") for k in ks]
                if any(v is not None for v in pts):
                    cur[f"{q} at {fk}"] = pts
        f_nf = float(nfc["f"])
        for k, (f, e, inn) in spectra.items():
            if not inn:
                continue
            en1, in1 = num.at_x(f, e, f_nf), num.at_x(f, inn, f_nf)
            if not en1 or in1 is None:
                continue
            rs = num.grid_points(curve_grid(cat, "jfet-noise", f"NF, {k}"))
            vt = [math.sqrt(en1 * en1 + in1 * in1 * r * r + 4 * K_B * T_K * r) for r in rs]
            cur[f"VT, {k}"] = vt
            cur[f"NF, {k}"] = [10 * math.log10(v * v / (4 * K_B * T_K * r)) for v, r in zip(vt, rs)]
        curves["jfet-noise"] = cur
        flat = all(v is None for k, v in vals.items() if k.startswith("en_corner@"))
        values["jfet-noise"]["_code"] = "ok"
        values["jfet-noise"]["one_over_f"] = "absent" if flat else "present"
