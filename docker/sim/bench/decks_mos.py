"""The MOSFET decks of the characterisation bench: one class per netlist, serving the `mosfet-*` measurements
of data/bench/measurements.yaml whose conditions it reads (docs/fet-characterisation.md).

Same shape as the bipolar and JFET decks. A deck writes a MOSFET as `M<name> d g s DUT` with three nodes;
the image ties the bulk of a four-terminal `.model` card to the source and maps a subcircuit's pins
(`character.as_device`). Where the drain current is forced (on-resistance, the body diode) the bipolar
bench's behavioural dial is used, ID = 10^V(x), with a clamp diode to a rail. The sign `s` is +1 for an
N-channel and −1 for a P-channel. Standard library only.
"""

import math

from bench import num
from bench.decks_bjt import Deck, curve_grid, freq, listed, mag, signed, tlabel, vec, whole
from bench.decks_jfet import a_weight, dc_line, integrate_noise, lin_points, nz, parallel_c
from bench.num import K_B, LN10, T_K, n, si

CLAMP = 30.0        # V: the rail a forced drain current is caught at when the transistor cannot pass it
DIODE_CLAMP = 5.0   # V: the same for a forced source current, for a card without a body diode
VTH_FLOOR = 1e-3    # A: the drain current the threshold is read at for the decks that need one
OPEN = 1e9          # Ω: a copy the clamp caught


def dial(name, node, s, scale=1.0):
    """A current of 10^V(x) (times a scale) pushed into `node`, the bipolar bench's dial; negative for a P-channel."""
    sg = "-" if s < 0 else ""
    k = f"{n(scale)}*" if scale != 1.0 else ""
    return f"{name} 0 {node} I={sg}{k}exp({LN10}*V(x))"


def dial_tail(sw):
    lo, hi = math.log10(float(sw["from"])), math.log10(float(sw["to"]))
    return ["VX x 0 0", "RX x 0 1", f".dc VX {n(lo)} {n(hi)} {n(1 / int(sw['per_decade']))}"]


def dial_points(sw):
    lo, hi = math.log10(float(sw["from"])), math.log10(float(sw["to"]))
    return int(round((hi - lo) * int(sw["per_decade"]))) + 1


def clamp_lines(tag, node, s, rail):
    """A diode from the node to a rail: what the transistor cannot pass goes there."""
    d = f"DCL{tag} {node} cl{tag} DCLMP" if s > 0 else f"DCL{tag} cl{tag} {node} DCLMP"
    return [d, f"VCL{tag} cl{tag} 0 {n(s * rail)}"]


def ladder_points(ladder, derived):
    return [(i, derived.get(f"_vgs@{si(i, 'A')}")) for i in ladder]


def gate_or_off(vgs):
    """A ladder current the model never reached keeps its copy with the gate at 0 V: closed, not read."""
    return vgs if vgs is not None else 0.0


# ----------------------------------------------------------------------------------- the transfer sweep
class Transfer(Deck):
    """One gate sweep: copies at four drain voltages and one diode-connected, for the thresholds, the
    power law, the subthreshold slope and the model's own gate voltages the later decks bias at."""
    name = "transfer"
    ids = ("mosfet-runs", "mosfet-transfer")

    def __init__(self, cat):
        super().__init__(cat)
        c = self.cond("mosfet-transfer")
        self.vds = [float(v) for v in c["vds"]]
        self.sw = c["vgs_sweep"]
        self.vth_at = [float(i) for i in c["vth_currents"]]
        self.ladder = [float(i) for i in c["id_ladder"]]
        self.read = [float(v) for v in c["vgs_read"]]
        self.v_main = float(c["vds_main"])
        r = self.cond("mosfet-runs")
        self.v_runs, self.vgs_runs = float(r["vds"]), [float(v) for v in r["vgs"]]

    def body(self, m, s, x, derived):
        out = []
        for i, v in enumerate(self.vds):
            out += [f"VT{i}{x} dt{i}{x} 0 {n(s * v)}", f"MT{i}{x} dt{i}{x} g 0 {m}"]
        return out + [f"VTD{x} dtd{x} g 0", f"MTD{x} dtd{x} g 0 {m}"]

    def saves(self, x):
        return ["V(g)"] + [f"I(VT{i}{x})" for i in range(len(self.vds))] + [f"I(VTD{x})"]

    def tail(self, s):
        return ["VGS g 0 0", dc_line("VGS", self.sw, s)]

    def measure(self, d, s, x, derived):
        vg = [s * v for v in whole(d, "V(g)", lin_points(self.sw))]
        ids = {v: signed(d, f"I(VT{i}{x})", -s) for i, v in enumerate(self.vds)}
        idd = signed(d, f"I(VTD{x})", -s)      # the diode-connected copy: its drain fed from the gate node through VTD (+ at the drain)
        vals, cur, der = {}, {}, {}
        vm = self.v_main
        main = ids[vm]
        # runs: the on-state currents at the low drain voltage
        low = ids[self.v_runs]
        runs = {"runs": True, "error_class": ""}
        for v in self.vgs_runs:
            runs[f"id_on@{si(v, 'V')}"] = num.interp(vg, low, v)
        i_on = runs.get(f"id_on@{si(self.vgs_runs[0], 'V')}")
        codes = {"mosfet-runs": "ok" if i_on and i_on > 0 else "suspect"}
        # thresholds
        # the diode-connected copy carries the body diode's current while the gate (and so the drain) is below the
        # source: the threshold is read from 0 V up
        for i_t in self.vth_at:
            vals[f"vth@{si(i_t, 'A')},diode"] = num.crossing(vg, idd, i_t, 0.0, True)
            vals[f"vth@{si(i_t, 'A')},{si(vm, 'V')}"] = num.crossing(vg, main, i_t, vg[0] - 1, True)
        vth = vals.get(f"vth@{si(VTH_FLOOR, 'A')},diode") or vals.get(f"vth@{si(VTH_FLOOR, 'A')},{si(vm, 'V')}")
        # the extrapolated threshold: √ID against VGS between 10 and 100 mA
        pts = [(a, math.sqrt(b)) for a, b in zip(vg, main) if 1e-2 <= b <= 1e-1]
        if len(pts) >= 4:
            slope, icpt = num.linfit([p[0] for p in pts], [p[1] for p in pts])
            if slope:
                vals["vth_extrapolated"] = -icpt / slope
        # the subthreshold slope, volts per decade over the window below the square law; a slope outside what a
        # junction can do (40 mV to 500 mV per decade) is not a subthreshold region but a leakage resistor or the
        # square law's foot, and reads absent
        lo, hi = [float(q) for q in self.cond("mosfet-transfer")["sub_window"]]
        pts = [(a, math.log10(b)) for a, b in zip(vg, main) if lo <= b <= hi]
        vals["sub_slope"] = None
        if len(pts) >= 4:
            slope, _ = num.linfit([p[1] for p in pts], [p[0] for p in pts])
            if slope is not None and 0.04 <= slope <= 0.5:
                vals["sub_slope"] = slope
        # the exponent above threshold, 100 mA to the top
        if vth is not None:
            pts = [(math.log(a - vth), math.log(b)) for a, b in zip(vg, main) if a - vth > 0 and b >= 1e-1]
            if len(pts) >= 4:
                slope, _ = num.linfit([p[0] for p in pts], [p[1] for p in pts])
                vals["n_fit"] = slope
        g = self.grid("mosfet-transfer")
        for v in self.vds:
            for r in self.read:
                vals[f"id@{si(r, 'V')},{si(v, 'V')}"] = num.interp(vg, ids[v], r)
            for i_t in self.ladder:
                vals[f"vgs@{si(i_t, 'A')},{si(v, 'V')}"] = num.crossing(vg, ids[v], i_t, vg[0] - 1, True)
            cur[f"ID, VDS={si(v, 'V')}"] = num.on_grid(vg, ids[v], g, log_x=False)
            cur[f"ID log, VDS={si(v, 'V')}"] = num.on_grid(vg, ids[v], g, log_x=False, log_y=True)
        cur["ID diode-connected"] = num.on_grid(vg, idd, g, log_x=False, log_y=True)
        a, b = vals.get(f"vgs@1A,{si(self.vds[-1], 'V')}"), None
        if a is not None:
            b = num.interp(vg, ids[self.vds[1]], a)
            vals["id_25v_over_6v@1A"] = (1.0 / b) if b else None
        for i_t in self.ladder:
            w = vals.get(f"vgs@{si(i_t, 'A')},{si(vm, 'V')}")
            if w is not None:
                der[f"_vgs@{si(i_t, 'A')}"] = w
        der["_vth"] = vth
        codes["mosfet-transfer"] = "ok" if vth is not None else "n/a"
        return ({"mosfet-runs": runs, "mosfet-transfer": vals}, {"mosfet-transfer": cur}, codes, der)


# ------------------------------------------------------------------------------------ the curve tracer
class Tracer(Deck):
    """ID against VDS: one trace per universal gate voltage (copies VGU/VU/MU) and five auto traces at the
    gate voltages that gave the catalogue's currents in the transfer sweep (VGK/VK/MK)."""
    name = "tracer"
    ids = ("mosfet-tracer",)
    pack_limit = 3

    def __init__(self, cat):
        super().__init__(cat)
        c = self.cond("mosfet-tracer")
        self.ladder = [float(v) for v in c["vgs_ladder"]]
        self.auto = [float(i) for i in c["auto"]["id"]]
        self.sw = c["vds_sweep"]
        self.read_at = float(c["rds_chord_vds"])

    def steps(self, derived):
        return [derived.get(f"_vgs@{si(i, 'A')}") for i in self.auto]

    def ready(self, derived):
        return any(v is not None for v in self.steps(derived))

    def body(self, m, s, x, derived):
        out = []
        for k, v in enumerate(self.steps(derived), 1):
            out += [f"VGK{k}{x} gk{k}{x} 0 {nz(s * gate_or_off(v))}", f"VK{k}{x} sw dk{k}{x} 0", f"MK{k}{x} dk{k}{x} gk{k}{x} 0 {m}"]
        for j, v in enumerate(self.ladder, 1):
            out += [f"VGU{j}{x} gu{j}{x} 0 {n(s * v)}", f"VU{j}{x} sw du{j}{x} 0", f"MU{j}{x} du{j}{x} gu{j}{x} 0 {m}"]
        return out

    def saves(self, x):
        return ["V(sw)"] + [f"I(VK{k}{x})" for k in range(1, len(self.auto) + 1)] + [f"I(VU{j}{x})" for j in range(1, len(self.ladder) + 1)]

    def tail(self, s):
        return ["VSW sw 0 0", dc_line("VSW", self.sw, s)]

    def measure(self, d, s, x, derived):
        whole(d, "V(sw)", lin_points(self.sw))
        v = signed(d, "V(sw)", s)
        g = self.grid("mosfet-tracer")
        top = float(self.sw["to"])
        vals, cur = {}, {}
        for k, vgs in enumerate(self.steps(derived), 1):
            if vgs is None:
                continue
            vs, idv = num.monotone(v, signed(d, f"I(VK{k}{x})", s))
            cur[f"ID, auto {k}"] = num.on_grid(vs, idv, g, log_x=False)
            vals[f"vgs_auto@{k}"] = vgs
            i_top = num.interp(vs, idv, min(top, vs[-1]))
            vals[f"vds_knee@auto{k}"] = num.crossing(vs, idv, 0.9 * i_top, -1.0, True) if i_top else None
            a, b = num.interp(vs, idv, 5.0), num.interp(vs, idv, min(top, vs[-1]))
            vals[f"gos_flat@auto{k}"] = (b - a) / (min(top, vs[-1]) - 5.0) if a is not None and b is not None and top > 5 else None
        for j, vgs in enumerate(self.ladder, 1):
            vs, idv = num.monotone(v, signed(d, f"I(VU{j}{x})", s))
            cur[f"ID, VGS={si(vgs, 'V')}"] = num.on_grid(vs, idv, g, log_x=False)
            i_r = num.interp(vs, idv, self.read_at)
            vals[f"rds_chord@{si(self.read_at, 'V')},{si(vgs, 'V')}"] = (self.read_at / i_r) if i_r and i_r > 1e-9 else None
        return {"mosfet-tracer": vals}, {"mosfet-tracer": cur}, {"mosfet-tracer": "ok" if cur else "n/a"}, {}


# ------------------------------------------------------------------------------------- on-resistance
class Rdson(Deck):
    """The drain current forced by the dial at each gate voltage of the ladder, a clamp to 30 V, VDS read."""
    name = "rdson"
    ids = ("mosfet-rdson",)

    def __init__(self, cat):
        super().__init__(cat)
        c = self.cond("mosfet-rdson")
        self.vgs = [float(v) for v in c["vgs_ladder"]]
        self.sw = c["id_sweep"]
        self.ladder = [float(i) for i in c["id_ladder"]]
        self.clamp = float(c["clamp_v"])
        self.lin_fraction = float(c["linear_fraction"])

    def body(self, m, s, x, derived):
        out = []
        for i, v in enumerate(self.vgs):
            out += [dial(f"BR{i}{x}", f"dr{i}{x}", s), *clamp_lines(f"{i}{x}", f"dr{i}{x}", s, self.clamp),
                    f"VGR{i}{x} gr{i}{x} 0 {n(s * v)}", f"MR{i}{x} dr{i}{x} gr{i}{x} 0 {m}"]
        return out

    def saves(self, x):
        return ["V(x)"] + [f"V(dr{i}{x})" for i in range(len(self.vgs))]

    def tail(self, s):
        return [".model DCLMP D(Is=1e-14)"] + dial_tail(self.sw)

    def measure(self, d, s, x, derived):
        xs = whole(d, "v(x)", dial_points(self.sw))
        i_d = [10 ** q for q in xs]
        vth = derived.get("_vth") or 0.0
        vals, cur = {}, {}
        g = self.grid("mosfet-rdson")
        for i, vgs in enumerate(self.vgs):
            vds = signed(d, f"V(dr{i}{x})", s)
            # the linear region: below the clamp and well below the saturation voltage VGS − Vth
            ok = [(a, b / a) for a, b in zip(i_d, vds) if b < self.clamp - 1 and b < self.lin_fraction * max(vgs - vth, 0.05)]
            k = si(vgs, "V")
            if len(ok) >= 2:
                xs_ok, r_ok = [p[0] for p in ok], [p[1] for p in ok]
                for i_t in self.ladder:
                    vals[f"rdson@{si(i_t, 'A')},{k}"] = num.log_interp(xs_ok, r_ok, i_t) if xs_ok[0] <= i_t <= xs_ok[-1] else None
                cur[f"RDS(on), VGS={k}"] = num.on_grid(xs_ok, r_ok, g, log_y=True)
        f10 = vals.get("rdson@1mA,10V")
        vals["rdson_floor@10V"] = f10
        top = [i_t for i_t in self.ladder if vals.get(f"rdson@{si(i_t, 'A')},10V") is not None]
        if f10 and top:
            vals["rdson_slope@10V"] = vals[f"rdson@{si(top[-1], 'A')},10V"] / f10
            vals["id_top_conducting@10V"] = top[-1]
        a, b = vals.get("rdson@1A,4.5V"), vals.get("rdson@1A,10V")
        if a and b:
            vals["rdson_4v5_over_10v@1A"] = a / b
        return {"mosfet-rdson": vals}, {"mosfet-rdson": cur}, {"mosfet-rdson": "ok" if f10 else "n/a"}, {}


class RdsonVgs(Deck):
    """The drain current held at each of three values, the gate swept: RDS(on) against VGS and the drive floor."""
    name = "rdson-vgs"
    ids = ("mosfet-rdson",)

    def __init__(self, cat):
        super().__init__(cat)
        c = self.cond("mosfet-rdson")
        self.ids_held = [float(i) for i in c["vgs_sweep_at_id"]]
        self.sw = c["vgs_sweep"]
        self.clamp = float(c["clamp_v"])

    def body(self, m, s, x, derived):
        out = []
        for i, i_t in enumerate(self.ids_held):
            out += [f"IH{i}{x} 0 dh{i}{x} {n(s * i_t)}", *clamp_lines(f"h{i}{x}", f"dh{i}{x}", s, self.clamp), f"MH{i}{x} dh{i}{x} gsw 0 {m}"]
        return out

    def saves(self, x):
        return ["V(gsw)"] + [f"V(dh{i}{x})" for i in range(len(self.ids_held))]

    def tail(self, s):
        return [".model DCLMP D(Is=1e-14)", "VGSW gsw 0 0", dc_line("VGSW", self.sw, s)]

    def measure(self, d, s, x, derived):
        vg = [s * q for q in whole(d, "V(gsw)", lin_points(self.sw))]
        vals, cur = {}, {}
        g = curve_grid(self.cat, "mosfet-rdson", "RDS(on) vs VGS, ID=1A")
        for i, i_t in enumerate(self.ids_held):
            vds = signed(d, f"V(dh{i}{x})", s)
            # a copy caught by the clamp (the gate too low for the current) reads an open: a huge resistance, left out
            r = [(b / i_t) if b < self.clamp - 1 else OPEN for b in vds]
            k = si(i_t, "A")
            cur[f"RDS(on) vs VGS, ID={k}"] = [q if q is not None and q < OPEN / 10 else None for q in num.on_grid(vg, r, g, log_x=False)]
            r15 = num.interp(vg, r, float(self.sw["to"]))
            if r15 and r15 < OPEN / 10:
                vals[f"vgs_rdson_110pct@{k}"] = num.crossing(vg, r, 1.1 * r15, vg[0] - 1, False)
        return {"mosfet-rdson": vals}, {"mosfet-rdson": cur}, {}, {}


# ----------------------------------------------------------------------------- gfs and gos at 1 kHz
class Gm(Deck):
    name = "gm"
    ids = ("mosfet-gm",)
    analysis = "ac"

    def __init__(self, cat):
        super().__init__(cat)
        c = self.cond("mosfet-gm")
        self.vds = float(c["vds"])
        self.ladder = [float(i) for i in c["id_ladder"]]
        self.f = float(c["f"])

    def ready(self, derived):
        return any(v is not None for _, v in ladder_points(self.ladder, derived))

    def body(self, m, s, x, derived):
        out = []
        for i, (_, vgs) in enumerate(ladder_points(self.ladder, derived)):
            out += [f"VD{i}{x} d{i}{x} 0 {n(s * self.vds)}", f"VG{i}{x} g{i}{x} 0 DC {nz(s * gate_or_off(vgs))} AC 1", f"MG{i}{x} d{i}{x} g{i}{x} 0 {m}",
                    f"VDO{i}{x} do{i}{x} 0 DC {n(s * self.vds)} AC 1", f"VGO{i}{x} go{i}{x} 0 {nz(s * gate_or_off(vgs))}", f"MO{i}{x} do{i}{x} go{i}{x} 0 {m}"]
        return out

    def saves(self, x):
        return [f"I(VD{i}{x})" for i in range(len(self.ladder))] + [f"I(VDO{i}{x})" for i in range(len(self.ladder))]

    def tail(self, s):
        return [f".ac dec 10 {n(self.f / 10)} {n(self.f * 10)}"]

    def measure(self, d, s, x, derived):
        fr = freq(d)
        vals, der, gfs_pts, gos_pts = {}, {}, [], []
        for i, (i_t, vgs) in enumerate(ladder_points(self.ladder, derived)):
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
            if i_t == 0.1:
                vals["av_intrinsic@100mA"] = (gfs / gos) if gos > 1e-15 else None
                vals["va_equiv@100mA"] = (i_t / gos - self.vds) if gos > 1e-15 and i_t / gos - self.vds < 1e4 else None
        g = self.grid("mosfet-gm")
        cur = {f"gfs, VDS={si(self.vds, 'V')}": num.on_grid([p[0] for p in gfs_pts], [p[1] for p in gfs_pts], g, log_y=True),
               f"gos, VDS={si(self.vds, 'V')}": num.on_grid([p[0] for p in gos_pts], [p[1] for p in gos_pts], g, log_y=True)}
        if gos_pts and max(p[1] for p in gos_pts) <= 1e-15:
            vals["gos_note"] = "absent"
        return {"mosfet-gm": vals}, {"mosfet-gm": cur}, {"mosfet-gm": "ok" if gfs_pts else "n/a"}, der


# ---------------------------------------------------------------------------------------- capacitance
class Cap(Deck):
    """Per drain voltage: Ciss and Crss from a copy with the gate driven at VGS = 0 and the drain held; Coss
    from a copy with the drain driven and the gate grounded."""
    name = "cap"
    ids = ("mosfet-capacitance",)
    analysis = "ac"

    def __init__(self, cat):
        super().__init__(cat)
        c = self.cond("mosfet-capacitance")
        self.vs = [float(v) for v in c["vds_ladder"]]
        self.f = float(c["f"])
        self.q_at = [float(v) for v in c["qoss_at"]]

    def body(self, m, s, x, derived):
        out = []
        for i, v in enumerate(self.vs):
            out += [f"VDI{i}{x} di{i}{x} 0 {n(s * v)}", f"VGI{i}{x} gi{i}{x} 0 DC 0 AC 1", f"MI{i}{x} di{i}{x} gi{i}{x} 0 {m}",
                    f"VDO{i}{x} do{i}{x} 0 DC {n(s * v)} AC 1", f"MO{i}{x} do{i}{x} 0 0 {m}"]
        return out

    def saves(self, x):
        out = []
        for i in range(len(self.vs)):
            out += [f"I(VGI{i}{x})", f"I(VDI{i}{x})", f"I(VDO{i}{x})"]
        return out

    def tail(self, s):
        return [f".ac dec 10 {n(self.f / 10)} {n(self.f * 10)}"]

    def measure(self, d, s, x, derived):
        fr = freq(d)
        vals, cur = {}, {"Ciss": [], "Coss": [], "Crss": []}
        for i, v in enumerate(self.vs):
            k = si(v, "V")
            got = {"ciss": parallel_c(fr, vec(d, f"I(VGI{i}{x})"), self.f), "crss": parallel_c(fr, vec(d, f"I(VDI{i}{x})"), self.f),
                   "coss": parallel_c(fr, vec(d, f"I(VDO{i}{x})"), self.f)}
            for q, c in got.items():
                vals[f"{q}@{k}"] = c
            cur["Ciss"].append(got["ciss"])
            cur["Coss"].append(got["coss"])
            cur["Crss"].append(got["crss"])
        for q in ("crss", "coss"):
            a, b = vals.get(f"{q}@1V"), vals.get(f"{q}@25V")
            if a and b and b > 1e-16:
                vals[f"{q}_1v_over_25v"] = a / b
        a, b = vals.get("crss@25V"), vals.get("ciss@25V")
        if a is not None and b:
            vals["miller_ratio@25V"] = a / b
        # Qoss and Eoss: Coss integrated over voltage, trapezoids on the ladder from 0 (Coss(0) taken as Coss(0.1 V))
        pts = [(0.0, cur["Coss"][0])] + list(zip(self.vs, cur["Coss"]))
        eoss_curve = []
        for v_to in self.vs:
            q = e = 0.0
            for (v0, c0), (v1, c1) in zip(pts, pts[1:]):
                if v1 > v_to:
                    break
                q += (c0 + c1) / 2 * (v1 - v0)
                e += (c0 * v0 + c1 * v1) / 2 * (v1 - v0)
            eoss_curve.append(e)
            if v_to in self.q_at:
                vals[f"qoss@{si(v_to, 'V')}"], vals[f"eoss@{si(v_to, 'V')}"] = q, e
        cur["Eoss"] = eoss_curve
        code = "ok" if max(cur["Ciss"]) > 1e-16 else "absent"
        return {"mosfet-capacitance": vals}, {"mosfet-capacitance": cur}, {"mosfet-capacitance": code}, {}


class CapVgs(Deck):
    """Ciss and Crss against the gate voltage at VDS = 0: the oxide takes over as the channel forms."""
    name = "cap-vgs"
    ids = ("mosfet-capacitance",)
    analysis = "ac"

    def __init__(self, cat):
        super().__init__(cat)
        c = self.cond("mosfet-capacitance")
        self.vgs = [float(v) for v in c["vgs_ladder_at_vds0"]]
        self.f = float(c["f"])

    def body(self, m, s, x, derived):
        out = []
        for i, v in enumerate(self.vgs):
            out += [f"VDG{i}{x} dg{i}{x} 0 0", f"VGG{i}{x} gg{i}{x} 0 DC {nz(s * v)} AC 1", f"MG{i}{x} dg{i}{x} gg{i}{x} 0 {m}"]
        return out

    def saves(self, x):
        out = []
        for i in range(len(self.vgs)):
            out += [f"I(VGG{i}{x})", f"I(VDG{i}{x})"]
        return out

    def tail(self, s):
        return [f".ac dec 10 {n(self.f / 10)} {n(self.f * 10)}"]

    def measure(self, d, s, x, derived):
        fr = freq(d)
        ciss = [parallel_c(fr, vec(d, f"I(VGG{i}{x})"), self.f) for i in range(len(self.vgs))]
        crss = [parallel_c(fr, vec(d, f"I(VDG{i}{x})"), self.f) for i in range(len(self.vgs))]
        vals = {}
        if ciss[0] > 1e-16:
            vals["ciss_10v_over_0v@vds0"] = ciss[-1] / ciss[0]
        return {"mosfet-capacitance": vals}, {"mosfet-capacitance": {"Ciss vs VGS": ciss, "Crss vs VGS": crss}}, {}, {}


# ---------------------------------------------------------------------------------------- gate charge
class GateCharge(Deck):
    """A constant current into the gate, the drain fed the load current from a source clamped to the supply:
    the gate voltage against time is the charge curve. The gate is caught at 15 V by a diode."""
    ids = ("mosfet-gate-charge",)
    analysis = "tran"
    pack = False

    def __init__(self, cat, i_d, vdd, ig):
        super().__init__(cat)
        self.c = self.cond("mosfet-gate-charge")
        self.i_d, self.vdd, self.ig = float(i_d), float(vdd), float(ig)
        self.name = f"qg{si(self.i_d, 'A')}-{si(self.vdd, 'V')}"
        self.key = f"{si(self.i_d, 'A')},{si(self.vdd, 'V')}"

    def ready(self, derived):
        return derived.get("_vth") is not None

    def body(self, m, s, x, derived):
        c = self.c
        t0 = float(c["t_start_s"])
        # the gate's 1 GΩ to ground gives the operating point a path: without it the floating gate starts at the clamp
        return [f"IG 0 g PULSE(0 {n(s * self.ig)} {n(t0)} 1e-09 1e-09 1 2)", "RGL g 0 1e9", f"IL vdd d {n(s * self.i_d)}", *clamp_lines("", "d", s, self.vdd), f"VDD vdd 0 {n(s * self.vdd)}",
                *clamp_lines("G", "g", s, float(c["vgs_clamp"])), f"M1 d g 0 {m}"]

    def saves(self, x):
        return ["V(g)", "V(d)"]

    def tail(self, s):
        c = self.c
        return [".model DCLMP D(Is=1e-14)", f".tran {n(float(c['max_step_s']))} {n(float(c['t_end_s']))} 0 {n(float(c['max_step_s']))}"]

    def measure(self, d, s, x, derived):
        c = self.c
        t, vg, vd = vec(d, "time"), signed(d, "V(g)", s), signed(d, "V(d)", s)
        t0 = float(c["t_start_s"])
        q = [self.ig * max(a - t0, 0.0) for a in t]
        vth = derived["_vth"]
        vals = {}
        key = self.key
        t_th = num.crossing(t, vg, vth, 0, True)
        # the plateau: the drain falls from the clamp; its start and end are where VDS passes 90 % and 10 % of VDD
        t_p0 = num.crossing(t, vd, 0.9 * self.vdd, 0, False)
        t_p1 = num.crossing(t, vd, 0.1 * self.vdd, 0, False)
        if t_th is None or t_p0 is None or t_p1 is None:
            return {"mosfet-gate-charge": {f"qg@{si(float(c['vgs_read'][1]), 'V')},{key}": None}}, {}, {"mosfet-gate-charge": "n/a"}, {}
        vals[f"qgs_th@{key}"] = self.ig * (t_th - t0)
        vals[f"qgs@{key}"] = self.ig * (t_p0 - t0)
        vals[f"qgd@{key}"] = self.ig * (t_p1 - t_p0)
        vals[f"vplateau@{key}"] = num.interp(t, vg, (t_p0 + t_p1) / 2)
        for v_read in c["vgs_read"]:
            t_r = num.crossing(t, vg, float(v_read), 0, True)
            vals[f"qg@{si(float(v_read), 'V')},{key}"] = self.ig * (t_r - t0) if t_r is not None else None
        vals[f"qsw@{key}"] = vals[f"qgs@{key}"] - vals[f"qgs_th@{key}"] + vals[f"qgd@{key}"]
        if vals[f"qgs_th@{key}"] > 0:
            vals[f"qgd_over_qgsth@{key}"] = vals[f"qgd@{key}"] / vals[f"qgs_th@{key}"]
        # the curve up to the read voltage, as [charge, VGS] pairs
        t_end = num.crossing(t, vg, float(c["vgs_read"][-1]) + 1.0, 0, True) or t[-1]
        pts = [(a, b) for a, b, c_ in zip(q, vg, t) if t0 <= c_ <= t_end]
        cur = {f"VGS vs Qg, ID={si(self.i_d, 'A')}, VDD={si(self.vdd, 'V')}": num.thin([p[0] for p in pts], [p[1] for p in pts], int(c["curve_points"]))}
        return {"mosfet-gate-charge": vals}, {"mosfet-gate-charge": cur}, {"mosfet-gate-charge": "ok"}, {}


# ------------------------------------------------------------------------------------------ switching
class Switching(Deck):
    """The resistive-load switch: VDD through RL = VDD/ID, the gate pulsed through RG."""
    ids = ("mosfet-switching",)
    analysis = "tran"
    pack = False

    def __init__(self, cat, i_d, rg, von):
        super().__init__(cat)
        self.c = self.cond("mosfet-switching")
        self.i_d, self.rg, self.von = float(i_d), float(rg), float(von)
        self.vdd = float(self.c["vdd"])
        first = self.rg == listed(self.c["rg"])[0] and self.von == listed(self.c["v_on"])[0]
        self.name = f"sw{si(self.i_d, 'A')}" + ("" if first else f"-{si(self.rg, 'Ω')}-{si(self.von, 'V')}")
        self.key = f"{si(self.i_d, 'A')},{si(self.vdd, 'V')},{si(self.rg, 'Ω')},{si(self.von, 'V')}"

    def body(self, m, s, x, derived):
        c = self.c
        t0, e, t_on = float(c["t_start_s"]), float(c["edge_s"]), float(c["t_on_s"])
        return [f"VDD vdd 0 {n(s * self.vdd)}", f"RL vdd dl {n(self.vdd / self.i_d)}", "VS dl d 0",
                f"VIN in 0 PULSE(0 {n(s * self.von)} {n(t0)} {n(e)} {n(e)} {n(t_on)} 1)", f"RG in g {n(self.rg)}", f"M1 d g 0 {m}"]

    def saves(self, x):
        return ["V(in)", "V(d)", "I(VS)"]

    def tail(self, s):
        c = self.c
        end = float(c["t_start_s"]) + 2 * float(c["edge_s"]) + float(c["t_on_s"]) + float(c["t_after_s"])
        return [f".tran {n(float(c['max_step_s']))} {n(end)} 0 {n(float(c['max_step_s']))}"]

    def measure(self, d, s, x, derived):
        c = self.c
        t = vec(d, "time")
        vin, vd, i_d = signed(d, "V(in)", s), signed(d, "V(d)", s), signed(d, "I(VS)", s)
        t0, e, t_on = float(c["t_start_s"]), float(c["edge_s"]), float(c["t_on_s"])
        t1 = t0 + e + t_on
        key = self.key
        on_pts = [b for a, b in zip(t, vd) if t1 - 0.2 * t_on <= a <= t1]
        v_on = sum(on_pts) / len(on_pts) if on_pts else self.vdd
        vals = {f"on@{key}": 1 - v_on / self.vdd}
        cur = {f"VDS(t), ID={si(self.i_d, 'A')}, VDD={si(self.vdd, 'V')}, RG={si(self.rg, 'Ω')}, VON={si(self.von, 'V')}": num.thin(t, vd, int(c["curve_points"]))}
        if v_on > 0.1 * self.vdd:
            return {"mosfet-switching": vals}, {"mosfet-switching": cur}, {"mosfet-switching": "n/a"}, {}
        i_on = self.i_d * (1 - v_on / self.vdd)
        # the first nanoseconds carry the simulator's settling of the model's charges from the operating point
        # (a spurious drain current that decays before the pulse): the edges are read from half-way to the pulse
        settle = 0.5 * t0
        g10 = num.crossing(t, vin, 0.1 * self.von, settle, True)
        t10, t90 = num.crossing(t, i_d, 0.1 * i_on, settle, True), num.crossing(t, i_d, 0.9 * i_on, settle, True)
        g90f = num.crossing(t, vin, 0.9 * self.von, t1 - e, False)
        f90, f10 = num.crossing(t, i_d, 0.9 * i_on, t1, False), num.crossing(t, i_d, 0.1 * i_on, t1, False)
        if g10 is not None and t10 is not None:
            vals[f"td_on@{key}"] = t10 - g10
        if t10 is not None and t90 is not None:
            vals[f"tr@{key}"] = t90 - t10
        if g90f is not None and f90 is not None:
            vals[f"td_off@{key}"] = f90 - g90f
        if f90 is not None and f10 is not None:
            vals[f"tf@{key}"] = f10 - f90
        return {"mosfet-switching": vals}, {"mosfet-switching": cur}, {"mosfet-switching": "ok"}, {}


class Inductive(Deck):
    """The clamped-inductive fixture: the load current from an ideal source with a freewheeling diode to
    the supply, a small snubber on the drain, two gate pulses; the switching energies read on the second."""
    ids = ("mosfet-switching",)
    analysis = "tran"
    pack = False

    def __init__(self, cat, i_d):
        super().__init__(cat)
        self.c = self.cond("mosfet-switching")
        self.ind = self.c["inductive"]
        self.i_d = float(i_d)
        self.vdd, self.rg = float(self.ind["vdd"]), float(self.ind["rg"])
        self.name = f"ind{si(self.i_d, 'A')}"
        self.key = f"{si(self.i_d, 'A')},{si(self.rg, 'Ω')}"

    def body(self, m, s, x, derived):
        c, ind = self.c, self.ind
        t_on, e = float(ind["t_on_s"]), float(ind["edge_s"])
        period = 2 * t_on + float(ind["gap_s"])
        return [f"VIN in 0 PULSE(0 {n(s * float(c['v_on'][0]))} {n(float(c['t_start_s']))} {n(e)} {n(e)} {n(t_on)} {n(period)})", f"RG in g {n(self.rg)}",
                f"VDD vdd 0 {n(s * self.vdd)}", f"IL vdd dl {n(s * self.i_d)}",
                ("DFW dl dfw DFW" if s > 0 else "DFW dfw dl DFW"), f"RFW dfw vdd {n(float(ind['r_fw']))}", "VIDM dl d 0",
                f"RSN d sn {n(float(ind['r_snub']))}", f"CSN sn 0 {n(float(ind['c_snub']))}", f"M1 d g 0 {m}"]

    def saves(self, x):
        return ["V(d)", "I(VIDM)"]

    def tail(self, s):
        c, ind = self.c, self.ind
        t_on = float(ind["t_on_s"])
        end = float(c["t_start_s"]) + 3 * t_on + 2 * float(ind["gap_s"])
        return [".model DFW D(Is=1e-12 N=1.1 Cjo=100p)", ".options method=gear", f".tran {n(float(ind['max_step_s']))} {n(end)} 0 {n(float(ind['max_step_s']))}"]

    def measure(self, d, s, x, derived):
        c, ind = self.c, self.ind
        t, vd, i_d = vec(d, "time"), signed(d, "V(d)", s), signed(d, "I(VIDM)", s)
        t_on = float(ind["t_on_s"])
        t2 = float(c["t_start_s"]) + 2 * t_on + float(ind["gap_s"])      # the second pulse's turn-on (one period on), the current flowing
        w = float(ind["window_s"])

        def energy(t0, t1):
            e = 0.0
            for i in range(1, len(t)):
                if t0 <= t[i] <= t1:
                    e += 0.5 * (vd[i] * i_d[i] + vd[i - 1] * i_d[i - 1]) * (t[i] - t[i - 1])
            return e
        vals = {f"eon@{self.key}": energy(t2 - 0.1 * w, t2 + w), f"eoff@{self.key}": energy(t2 + t_on - 0.1 * w, t2 + t_on + w)}
        return {"mosfet-switching": vals}, {}, {}, {}


# ----------------------------------------------------------------------------------------- body diode
class BodyDiode(Deck):
    """The source current forced by the dial with the drain grounded, at three gate voltages; a clamp at 5 V
    for a card without a diode."""
    name = "body"
    ids = ("mosfet-body-diode",)

    def __init__(self, cat):
        super().__init__(cat)
        c = self.cond("mosfet-body-diode")
        self.vgs = [float(v) for v in c["vgs"]]
        self.sw = c["is_sweep"]
        self.ladder = [float(i) for i in c["is_ladder"]]

    def body(self, m, s, x, derived):
        out = []
        for i, v in enumerate(self.vgs):
            out += [dial(f"BS{i}{x}", f"s{i}{x}", s), *clamp_lines(f"s{i}{x}", f"s{i}{x}", s, DIODE_CLAMP),
                    f"VG{i}{x} g{i}{x} s{i}{x} {nz(s * v)}", f"MD{i}{x} 0 g{i}{x} s{i}{x} {m}"]
        return out

    def saves(self, x):
        return ["V(x)"] + [f"V(s{i}{x})" for i in range(len(self.vgs))]

    def tail(self, s):
        return [".model DCLMP D(Is=1e-14)"] + dial_tail(self.sw)

    def measure(self, d, s, x, derived):
        xs = whole(d, "v(x)", dial_points(self.sw))
        i_s = [10 ** q for q in xs]
        vals, cur = {}, {}
        g = self.grid("mosfet-body-diode")
        for i, vgs in enumerate(self.vgs):
            vsd = signed(d, f"V(s{i}{x})", s)
            ok = [(a, b) for a, b in zip(i_s, vsd) if b < DIODE_CLAMP - 1]
            k = si(vgs, "V")
            if len(ok) >= 2:
                xs_ok, v_ok = [p[0] for p in ok], [p[1] for p in ok]
                for i_t in self.ladder:
                    vals[f"vsd@{si(i_t, 'A')},{k}"] = num.log_interp(xs_ok, v_ok, i_t) if xs_ok[0] <= i_t <= xs_ok[-1] else None
                cur[f"IS vs VSD, VGS={k}"] = num.on_grid(v_ok, xs_ok, g, log_x=False, log_y=True)
                if vgs == 0.0:
                    pts = [(b, math.log(a)) for a, b in ok if 1e-3 <= a <= 1e-1]
                    if len(pts) >= 4:
                        slope, icpt = num.linfit([p[0] for p in pts], [p[1] for p in pts])
                        if slope and slope > 0:
                            vals["n_diode"] = 1 / (slope * num.VT_25)
                            vals["is_diode"] = math.exp(icpt)
        has = vals.get("vsd@100mA,0V") is not None
        runs = {"is_diode@1V": None}
        v0 = cur.get("IS vs VSD, VGS=0V")
        if v0:
            gp = num.grid_points(g)
            k1 = min(range(len(gp)), key=lambda j: abs(gp[j] - 1.0))
            runs["is_diode@1V"] = v0[k1]
        return ({"mosfet-body-diode": vals, "mosfet-runs": runs}, {"mosfet-body-diode": cur},
                {"mosfet-body-diode": "ok" if has else "absent"}, {})


class Recovery(Deck):
    """Reverse recovery: the diode carrying IF, the current reversed at di/dt to −IF, the drain current
    through its ammeter; a clamp diode to ground takes the current once the body diode has recovered."""
    ids = ("mosfet-body-diode",)
    analysis = "tran"
    pack = False

    def __init__(self, cat, i_f, didt):
        super().__init__(cat)
        self.c = self.cond("mosfet-body-diode")["recovery"]
        self.i_f, self.didt = float(i_f), float(didt) * 1e6
        self.name = f"trr{si(self.i_f, 'A')}-{int(float(didt))}"
        self.key = f"{si(self.i_f, 'A')},{int(float(didt))}A/µs"
        self.t_rev = 2 * self.i_f / self.didt
        self.t0 = float(self.c["t_forward_s"])

    def body(self, m, s, x, derived):
        return [f"IF 0 s PULSE({n(s * self.i_f)} {n(-s * self.i_f)} {n(self.t0)} {n(self.t_rev)} 1 1 2)", "VDM d 0 0", "RS s 0 1e6",
                f"MR d s s {m}", ("DCLP 0 s DCLMP" if s > 0 else "DCLP s 0 DCLMP")]

    def saves(self, x):
        return ["I(VDM)"]

    def tail(self, s):
        return [".model DCLMP D(Is=1e-14)", f".tran {n(self.t_rev / 50)} {n(self.t0 + self.t_rev + float(self.c['t_after_s']))} 0 {n(self.t_rev / 50)}"]

    def measure(self, d, s, x, derived):
        t = vec(d, "time")
        i_d = signed(d, "I(VDM)", s)          # the diode's forward current flows out of the drain into VDM: positive while conducting
        seg = [(a, b) for a, b in zip(t, i_d) if a >= self.t0]
        ta, tb = [p[0] for p in seg], [p[1] for p in seg]
        irm = min(tb) if tb else 0.0
        t_zero = num.crossing(ta, tb, 0.0, self.t0, False)
        vals = {f"irrm@{self.key}": -irm if irm < 0 else 0.0, f"trr@{self.key}": None, f"qrr@{self.key}": None}
        present = irm < 0 and -irm > float(self.c["present_fraction"]) * self.i_f
        if t_zero is not None and present:
            after = [(a, b) for a, b in seg if a > t_zero]
            k_min = min(range(len(after)), key=lambda j: after[j][1])
            tail = after[k_min:]
            t_end = num.crossing([p[0] for p in tail], [p[1] for p in tail], 0.1 * irm, tail[0][0] - 1, True)
            if t_end is not None and t_end - t_zero < float(self.c["present_trr_s"]):
                present = False                       # a capacitive spike, not stored charge
            if t_end is not None and present:
                vals[f"trr@{self.key}"] = t_end - t_zero
                q = 0.0
                for (a0, b0), (a1, b1) in zip(after, after[1:]):
                    if a1 > t_end:
                        break
                    q += -(b0 + b1) / 2 * (a1 - a0)
                vals[f"qrr@{self.key}"] = q
                t_a = after[k_min][0] - t_zero
                vals[f"softness@{self.key}"] = (t_end - after[k_min][0]) / t_a if t_a > 0 else None
        cur = {f"I(t) recovery, IF={si(self.i_f, 'A')}, di/dt={int(self.didt / 1e6)}A/µs": num.thin(ta, tb, 80)}
        vals[f"recovery@{self.key}"] = "present" if present else "absent"
        return {"mosfet-body-diode": vals}, {"mosfet-body-diode": cur}, {}, {}


# ----------------------------------------------------------------------------------------- temperature
class Temp(Deck):
    """The transfer copies at another temperature: 15 V, diode-connected, and a 0.1 V copy for RDS(on)."""
    ids = ("mosfet-temperature",)

    def __init__(self, cat, temp):
        super().__init__(cat)
        self.temp = float(temp)
        self.name = f"temp{int(temp)}"
        c = self.cond("mosfet-temperature")
        self.vds, self.v_lin = float(c["vds"]), float(c["vds_linear"])
        self.sw = c["vgs_sweep"]

    def body(self, m, s, x, derived):
        return [f"VT{x} dt{x} 0 {n(s * self.vds)}", f"MT{x} dt{x} g 0 {m}", f"VTD{x} dtd{x} g 0", f"MTD{x} dtd{x} g 0 {m}",
                f"VL{x} dl{x} 0 {n(s * self.v_lin)}", f"ML{x} dl{x} g 0 {m}"]

    def saves(self, x):
        return ["V(g)", f"I(VT{x})", f"I(VTD{x})", f"I(VL{x})"]

    def tail(self, s):
        return ["VGS g 0 0", dc_line("VGS", self.sw, s)]

    def measure(self, d, s, x, derived):
        c = self.cond("mosfet-temperature")
        vg = [s * v for v in whole(d, "V(g)", lin_points(self.sw))]
        ids = signed(d, f"I(VT{x})", -s)
        idd = signed(d, f"I(VTD{x})", -s)
        idl = signed(d, f"I(VL{x})", -s)
        t = int(self.temp)
        der = {f"_vth{t}": num.crossing(vg, idd, VTH_FLOOR, 0.0, True)}
        for v in c["rdson_vgs"]:
            i_l = num.interp(vg, idl, float(v))
            der[f"_rdson{t}@{si(float(v), 'V')}"] = (self.v_lin / i_l) if i_l and i_l > 1e-9 else None
        i_g = float(c["gfs_id"])
        v_g = num.crossing(vg, ids, i_g, vg[0] - 1, True)
        if v_g is not None:
            a, b = num.interp(vg, ids, v_g - 0.02), num.interp(vg, ids, v_g + 0.02)
            der[f"_gfs{t}@{si(i_g, 'A')}"] = (b - a) / 0.04 if a is not None and b is not None else None
        g = self.grid("mosfet-temperature")
        return {}, {"mosfet-temperature": {f"ID, {tlabel(self.temp)}": num.on_grid(vg, ids, g, log_x=False)}}, {}, der


# ----------------------------------------------------------------------------------------------- noise
class Noise(Deck):
    ids = ("mosfet-noise",)
    analysis = "noise"
    pack = False

    def __init__(self, cat, i_d, rg):
        super().__init__(cat)
        self.i_d, self.rg = float(i_d), float(rg)
        self.name = f"noise{si(i_d, 'A')}-{si(rg, 'Ω') if rg else '0'}"
        c = self.cond("mosfet-noise")
        self.vds = float(c["vds"])
        self.sw = c["noise_sweep"]

    def ready(self, derived):
        return derived.get(f"_vgs@{si(self.i_d, 'A')}") is not None

    def body(self, m, s, x, derived):
        vgs = derived[f"_vgs@{si(self.i_d, 'A')}"]
        return ["VSENSE d dd 0", f"VD dd 0 {n(s * self.vds)}", f"VIN in 0 DC {n(s * vgs)} AC 1", f"RG in g {n(self.rg) if self.rg else '0.001'}",
                f"M1 d g 0 {m}", "H1 out 0 VSENSE 1000", "RLOAD out 0 1meg"]

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


# ------------------------------------------------------------------------------------------- breakdown
class Breakdown(Deck):
    ids = ("mosfet-breakdown",)

    def __init__(self, cat, which):
        super().__init__(cat)
        self.which = which
        self.name = f"bv{which}"
        c = self.cond("mosfet-breakdown")
        self.sw = c["vds_sweep"] if which == "dss" else c["vgs_sweep"]
        self.i_br = float(c["breakdown_current"])
        self.leak = c["leakage_points"]

    def body(self, m, s, x, derived):
        if self.which == "dss":
            return [f"VA{x} sw da{x} 0", f"MA{x} da{x} 0 0 {m}"]
        return [f"VB{x} sw gb{x} 0", f"MB{x} 0 gb{x} 0 {m}"]

    def saves(self, x):
        return ["V(sw)", f"I(V{'A' if self.which == 'dss' else 'B'}{x})"]

    def tail(self, s):
        return ["VSW sw 0 0", dc_line("VSW", self.sw, s)]

    def measure(self, d, s, x, derived):
        whole(d, "V(sw)", lin_points(self.sw))
        v = signed(d, "V(sw)", s)
        vals = {}
        if self.which == "dss":
            i_abs = [abs(q) for q in signed(d, f"I(VA{x})", s)]
            vals["vbr_dss"] = num.crossing(v, i_abs, self.i_br, -1.0, True)
            for p in self.leak["idss"]:
                vals[f"idss@{si(float(p), 'V')}"] = num.interp(v, i_abs, float(p))
            return {"mosfet-breakdown": vals}, {}, {"mosfet-breakdown": "ok" if vals["vbr_dss"] is not None else "absent"}, {}
        i_g = [abs(q) for q in signed(d, f"I(VB{x})", s)]
        vs, ig = num.monotone(v, i_g)
        p = float(self.leak["igss"])
        vals["igss@20V"], vals["igss@-20V"] = num.interp(vs, ig, p), num.interp(vs, ig, -p)
        return {"mosfet-breakdown": vals}, {}, {}, {}


# ------------------------------------------------------------------------------------------ distortion
class ThdProbe(Deck):
    """A short run at a small amplitude, to learn the stage's gain for the model."""
    ids = ("mosfet-distortion",)
    analysis = "tran"
    pack = False
    AMP = 0.02

    def __init__(self, cat, stage="cs", rs_in=None, f=None):
        super().__init__(cat)
        self.c = self.cond("mosfet-distortion")
        self.stage = stage
        st = self.c[stage]
        self.rs_in = float(rs_in if rs_in is not None else listed(st["rs_in"])[0])
        self.f = float(f if f is not None else listed(st["f"])[0])
        self.name = f"thd-probe-{stage}"

    def amplitude(self, derived):
        return self.AMP

    def cycles(self):
        return 3

    def body(self, m, s, x, derived):
        st = self.c[self.stage]
        out = [f"VSS vss 0 {n(-s * float(st['vss']))}", f"VDD vdd 0 {n(s * float(st['vdd']))}", f"RIN in g {n(self.rs_in)}",
               f"VIN in 0 SIN(0 {n(self.amplitude(derived))} {n(self.f)})"]
        if self.stage == "cs":
            out += [f"RL vdd d {n(float(st['rl']))}", f"RS s sx {n(float(st['rs']))}", "CS sx 0 1000u", f"IS sx vss {n(s * float(st['id']))}", f"M1 d g s {m}"]
        else:
            out += [f"IS s vss {n(s * float(st['id']))}", "CL s l 1000u", f"RL l 0 {n(float(st['rl']))}", f"M1 vdd g s {m}"]
        return out

    def out_node(self):
        return "d" if self.stage == "cs" else "l"

    def saves(self, x):
        return [f"V({self.out_node()})"]

    def tail(self, s):
        step = 1 / self.f / int(self.c["steps_per_cycle"])
        return [".options method=gear", f".tran {n(step)} {n(self.cycles() / self.f)} 0 {n(step)}"]

    def window(self, d):
        t, vo = vec(d, "time"), vec(d, f"V({self.out_node()})")
        k = min(int(self.c["analysed_cycles"]), self.cycles() - 1)
        t1 = t[-1]
        return k, num.resample(t, vo, t1 - k / self.f, t1, k * int(self.c["steps_per_cycle"]))

    def measure(self, d, s, x, derived):
        k, samples = self.window(d)
        fund = num.goertzel(samples, k)
        return {}, {}, {}, {f"thd_gain_{self.stage}": fund / self.AMP if fund else None}


class Thd(ThdProbe):
    def __init__(self, cat, stage, rs_in=None, f=None):
        super().__init__(cat, stage, rs_in, f)
        self.level = float(self.c["vout_peak"])
        self.name = f"thd-{stage}" + ("" if stage == "cs" else f"-{si(self.rs_in, 'Ω')}-{si(self.f, 'Hz')}")
        self.tag = "_cs" if stage == "cs" else f"_sf@{si(self.rs_in, 'Ω')},{si(self.f, 'Hz')}"

    def ready(self, derived):
        return bool(derived.get(f"thd_gain_{self.stage}"))

    def amplitude(self, derived):
        return min(self.level / derived[f"thd_gain_{self.stage}"], 2.0)

    def cycles(self):
        return int(self.c["cycles"])

    def measure(self, d, s, x, derived):
        k, samples = self.window(d)
        amps = [num.goertzel(samples, k * h) for h in range(1, 11)]
        h1 = amps[0]
        if not h1:
            return {"mosfet-distortion": {}}, {}, {"mosfet-distortion": "n/a"}, {}
        thd = math.sqrt(sum(a * a for a in amps[1:])) / h1
        vals = {f"thd{self.tag}": thd, f"hd2{self.tag}": amps[1] / h1, f"hd3{self.tag}": amps[2] / h1, f"gain_{self.stage}": derived[f"thd_gain_{self.stage}"]}
        return {"mosfet-distortion": vals}, {}, {"mosfet-distortion": "ok"}, {}


# ------------------------------------------------------------------------------------------------ plan
def plan(cat, engine):
    """Every MOSFET deck in the order their dependencies need, for the measurements this engine runs."""
    decks = [Transfer(cat), Tracer(cat), Rdson(cat), RdsonVgs(cat), Gm(cat), Cap(cat), CapVgs(cat)]
    qg = cat["mosfet-gate-charge"]["conditions"]
    decks += [GateCharge(cat, p["id"], p["vdd"], p["ig"]) for p in qg["points"]]
    sw = cat["mosfet-switching"]["conditions"]
    rg0, von0 = listed(sw["rg"])[0], listed(sw["v_on"])[0]
    decks += [Switching(cat, i, rg0, von0) for i in sw["id_ladder"]]
    decks += [Switching(cat, sw["variants_id"], rg, von0) for rg in listed(sw["rg"])[1:]]
    decks += [Switching(cat, sw["variants_id"], rg0, von) for von in listed(sw["v_on"])[1:]]
    decks += [Inductive(cat, i) for i in sw["inductive"]["id"]]
    bd = cat["mosfet-body-diode"]["conditions"]
    decks += [BodyDiode(cat)] + [Recovery(cat, i_f, didt) for i_f in bd["recovery"]["if"] for didt in bd["recovery"]["didt_a_per_us"]]
    decks += [Temp(cat, t) for t in cat["mosfet-temperature"]["conditions"]["temps_c"]]
    nz = cat["mosfet-noise"]["conditions"]
    decks += [Noise(cat, i, 0) for i in nz["id_ladder"]] + [Noise(cat, nz["nf"]["id"], nz["nf"]["rg"])]
    decks += [Breakdown(cat, "dss"), Breakdown(cat, "gss")]
    dc = cat["mosfet-distortion"]["conditions"]
    decks += [ThdProbe(cat, "cs"), Thd(cat, "cs"), ThdProbe(cat, "sf")]
    decks += [Thd(cat, "sf", rs, f) for rs in listed(dc["sf"]["rs_in"]) for f in listed(dc["sf"]["f"]) if not (rs != listed(dc["sf"]["rs_in"])[0] and f == listed(dc["sf"]["f"])[0])]
    return [dk for dk in decks if all(engine in cat[i]["engines"] for i in dk.ids)]


def finalize(cat, values, curves, derived):
    """What needs several decks: the temperature ratios and the zero-TC point, the noise spectra, the
    distortion ratio of the follower's two drives."""
    c = cat["mosfet-temperature"]["conditions"]
    temps = sorted(float(t) for t in c["temps_c"])
    hot, cold = int(max(temps)), int(min(temps))
    out = {}
    for t in temps:
        k = int(t)
        if derived.get(f"_vth{k}") is not None:
            out[f"vth@1mA,{tlabel(t)}"] = derived[f"_vth{k}"]
        for v in c["rdson_vgs"]:
            kk = si(float(v), "V")
            r25, rt = derived.get(f"_rdson25@{kk}"), derived.get(f"_rdson{k}@{kk}")
            if r25 and rt and k != 25:
                out[f"rdson_{'m' if t < 0 else ''}{abs(k)}_over_25@{kk}"] = rt / r25
        g25, gt = derived.get(f"_gfs25@{si(float(c['gfs_id']), 'A')}"), derived.get(f"_gfs{k}@{si(float(c['gfs_id']), 'A')}")
        if g25 and gt and k != 25:
            out[f"gfs_{'m' if t < 0 else ''}{abs(k)}_over_25@{si(float(c['gfs_id']), 'A')}"] = gt / g25
    a, b = derived.get(f"_vth{hot}"), derived.get(f"_vth{cold}")
    if a is not None and b is not None:
        out["dvth_dt"] = (a - b) / (hot - cold)
    # the exponent of RDS(on) against absolute temperature, at the first gate voltage
    kk = si(float(c["rdson_vgs"][0]), "V")
    pts = [(math.log(t + 273.15), math.log(derived[f"_rdson{int(t)}@{kk}"])) for t in temps if derived.get(f"_rdson{int(t)}@{kk}")]
    if len(pts) >= 3:
        slope, _ = num.linfit([p[0] for p in pts], [p[1] for p in pts])
        out["rdson_t_exponent"] = slope
    tc = curves.get("mosfet-temperature") or {}
    g = num.grid_points(cat["mosfet-temperature"]["grid"])
    c25, chot = tc.get(f"ID, {tlabel(25)}"), tc.get(f"ID, {tlabel(float(c['ztc_hot']))}")
    ztc = None
    if c25 and chot:
        diff = [(p - q) if p is not None and q is not None else None for p, q in zip(c25, chot)]
        for j in range(1, len(g)):
            if diff[j - 1] is not None and diff[j] is not None and diff[j - 1] * diff[j] < 0 and c25[j] > float(c["ztc_min_id"]):
                w = diff[j - 1] / (diff[j - 1] - diff[j])
                ztc = (g[j - 1] + w * (g[j] - g[j - 1]), c25[j - 1] + w * (c25[j] - c25[j - 1]))
                break
    out["vgs_0tc"], out["id_0tc"] = (ztc[0], ztc[1]) if ztc else (None, None)
    if out:
        ratios = [v for k, v in out.items() if k.startswith("rdson_") and "_over_25" in k]
        values["mosfet-temperature"] = {**out, "_code": "absent" if ratios and all(abs(r - 1) < 1e-3 for r in ratios) else "ok"}
        tc["Vth"] = [derived.get(f"_vth{int(t)}") for t in temps]
        tc["RDS(on) normalised"] = [((derived.get(f"_rdson{int(t)}@{kk}") or 0) / derived[f"_rdson25@{kk}"]) if derived.get(f"_rdson25@{kk}") and derived.get(f"_rdson{int(t)}@{kk}") else None for t in temps]
    # noise
    nz = cat["mosfet-noise"]["conditions"]
    vals, spectra = {}, {}
    for i_d in nz["id_ladder"]:
        k = si(float(i_d), "A")
        en = derived.get(f"_noise@{k}@0")
        if not en:
            continue
        f, e = en
        for fp in nz["f_points"]:
            vals[f"en@{si(float(fp), 'Hz')},{k}"] = num.at_x(f, e, float(fp))
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
        spectra[k] = (f, e)
    nfc = nz["nf"]
    k_nf = si(float(nfc["id"]), "A")
    tot = derived.get(f"_noise@{k_nf}@{si(float(nfc['rg']), 'Ω')}")
    if tot:
        f, t2 = tot
        v = num.at_x(f, t2, float(nfc["f"]))
        vals[f"nf@{si(float(nfc['f']), 'Hz')},{k_nf},{si(float(nfc['rg']), 'Ω')}"] = 10 * math.log10(v * v / (4 * K_B * T_K * float(nfc["rg"])))
    if vals:
        g = cat["mosfet-noise"].get("grid")
        cur = {f"en, {k}": num.on_grid(f, e, g, log_y=True) for k, (f, e) in spectra.items()}
        ks = [si(float(i), "A") for i in nz["id_ladder"]]
        for fp in nz["f_points"]:
            fk = si(float(fp), "Hz")
            pts = [vals.get(f"en@{fk},{k}") for k in ks]
            if any(v is not None for v in pts):
                cur[f"en at {fk}"] = pts
        curves["mosfet-noise"] = cur
        flat = all(v is None for k, v in vals.items() if k.startswith("en_corner@"))
        values["mosfet-noise"] = {**vals, "one_over_f": "absent" if flat else "present", "_code": "ok"}
    # the follower's Crss figure: THD at 20 kHz from 1 kΩ over THD from 100 Ω
    dv = values.get("mosfet-distortion") or {}
    dc = cat["mosfet-distortion"]["conditions"]["sf"]
    rs = listed(dc["rs_in"])
    fh = listed(dc["f"])[-1]
    a, b = dv.get(f"thd_sf@{si(rs[-1], 'Ω')},{si(fh, 'Hz')}"), dv.get(f"thd_sf@{si(rs[0], 'Ω')},{si(fh, 'Hz')}")
    if a and b:
        dv["crss_distortion_ratio"] = a / b
