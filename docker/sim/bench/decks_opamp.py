"""The op-amp decks of the characterisation bench: one class per netlist, serving the `opamp-*` measurements
of data/bench/measurements.yaml whose conditions it reads (docs/opamp-characterisation.md).

Same shape as the transistor decks. An op-amp is a subcircuit measured through its five pins: a deck writes
it as `X<name> in+ in- v+ v- out DUT` and the image puts the model's own pin order in (`character.as_device`,
with the roles bench.jobs read from the author's header). No deck packs: a macromodel's decks are cheap and
its nodes are named without suffixes. The sign `s` is always +1 (an op-amp has no polarity); every source
is written as it is. Standard library only.
"""

import math

from bench import num
from bench.decks_bjt import Deck, curve_grid, freq, mag, vec
from bench.decks_jfet import a_weight, integrate_noise
from bench.num import K_B, T_K, n, si

SHIFT_FLOOR = 5e-5      # V: an RF-induced offset shift below this is the simulator's noise, not rectification
VICR_TOL = 1e-3         # V: the offset's excursion that marks the edge of the common-mode range


def oa(name, inp, inn, vp, vn, out, m):
    return f"X{name} {inp} {inn} {vp} {vn} {out} {m}"


def rails(vp, vn, tag=""):
    return [f"VP{tag} vp{tag} 0 {n(vp)}", f"VN{tag} vn{tag} 0 {n(vn)}"]


def phase_deg(z):
    return math.degrees(math.atan2(z.imag, z.real))


def unwrap(ph):
    out = [ph[0]]
    for p in ph[1:]:
        d = p - out[-1]
        while d > 180:
            d -= 360
        while d < -180:
            d += 360
        out.append(out[-1] + d)
    return out


def db(x):
    return 20 * math.log10(x) if x and x > 0 else None


def supply_tag(vs):
    """A supply of the ladder as the keys spell it: ±15V for a split supply, 36V for a single one."""
    vp, vn = vs
    return f"±{si(float(vp), 'V')}" if float(vn) < 0 else si(float(vp), "V")


def riaa_weight(f):
    """The RIAA playback curve as a linear gain, 1 at 1 kHz, through a 30 kHz low-pass."""
    w = 2 * math.pi * f
    t1, t2, t3 = 3180e-6, 318e-6, 75e-6
    g = abs(complex(1, w * t2) / (complex(1, w * t1) * complex(1, w * t3)))
    g0 = abs(complex(1, 2 * math.pi * 1e3 * t2) / (complex(1, 2 * math.pi * 1e3 * t1) * complex(1, 2 * math.pi * 1e3 * t3)))
    return g / g0 / abs(complex(1, f / 30e3))


# ---------------------------------------------------------------------------------------------- supply
class Runs(Deck):
    """A follower at each supply of the ladder, its input at the reference: the operating point, the supply
    current, the uncorrected offset."""
    name = "runs"
    ids = ("opamp-runs",)
    analysis = "op"
    pack = False

    def __init__(self, cat):
        super().__init__(cat)
        c = self.cond("opamp-runs")
        self.supplies = [(float(a), float(b)) for a, b in c["supplies"]]
        self.rl = float(c["rl"])

    def body(self, m, s, x, derived):
        out = []
        for i, (vp, vn) in enumerate(self.supplies):
            ref = (vp + vn) / 2
            out += rails(vp, vn, str(i)) + [f"VI{i} in{i} 0 {n(ref)}", oa(f"R{i}", f"in{i}", f"o{i}", f"vp{i}", f"vn{i}", f"o{i}", m), f"RL{i} o{i} 0 {n(self.rl)}"]
        return out

    def saves(self, x):
        return [v for i in range(len(self.supplies)) for v in (f"V(o{i})", f"I(VP{i})")]

    def tail(self, s):
        return [".op"]

    def measure(self, d, s, x, derived):
        vals, der = {"runs": True, "error_class": ""}, {}
        lowest = None
        for i, (vp, vn) in enumerate(self.supplies):
            tag = supply_tag((vp, vn))
            ref = (vp + vn) / 2
            vo = vec(d, f"V(o{i})")[0]
            iq = -vec(d, f"I(VP{i})")[0]
            vals[f"iq@{tag}"] = iq
            vals[f"vos@{tag}"] = vo - ref
            ok = abs(vo - ref) < 0.1
            vals[f"runs@{tag}"] = ok
            if ok and (lowest is None or vp - vn < lowest):
                lowest = vp - vn
            if i == 0:
                der["_vos"] = vo - ref
                der["_iq"] = iq
        vals["vs_min"] = lowest
        code = "ok" if vals.get(f"runs@{supply_tag(self.supplies[0])}") else "suspect"
        return {"opamp-runs": vals}, {}, {"opamp-runs": code}, der


class IqSweep(Deck):
    """The follower with no load as the supply sweeps from 4 to 40 V total, the negative rail mirroring the
    positive: IQ and VOS against the supply."""
    name = "iq-sweep"
    ids = ("opamp-iq", "opamp-offset")
    pack = False

    def __init__(self, cat):
        super().__init__(cat)
        self.c = self.cond("opamp-iq")
        self.sw = self.c["vs_sweep"]

    def body(self, m, s, x, derived):
        return ["VP vp 0 0", "EN vn 0 vp 0 -1", "VIN in 0 0", oa("Q", "in", "out", "vp", "vn", "out", m)]

    def saves(self, x):
        return ["V(vp)", "I(VP)", "V(out)"]

    def tail(self, s):
        sw = self.sw
        return [f".dc VP {n(float(sw['from']) / 2)} {n(float(sw['to']) / 2)} {n(float(sw['step']) / 2)}"]

    def measure(self, d, s, x, derived):
        vp = list(vec(d, "V(vp)"))
        vs = [2 * v for v in vp]
        iq = [-i for i in vec(d, "I(VP)")]
        vo = list(vec(d, "V(out)"))
        vals, ovals = {}, {}
        for p in self.c["vs_points"]:
            vals[f"iq@{si(float(p), 'V')}"] = num.interp(vs, iq, float(p))
            ovals[f"vos@{si(float(p), 'V')}"] = num.interp(vs, vo, float(p))
        a, b = num.interp(vs, iq, 10.0), num.interp(vs, iq, 36.0)
        vals["iq_slope"] = (b - a) / 26.0 if a is not None and b is not None else None
        g = self.grid("opamp-iq")
        cur = {"IQ vs VS": num.on_grid(vs, iq, g, log_x=False)}
        go = curve_grid(self.cat, "opamp-offset", "VOS vs VS")
        ocur = {"VOS vs VS": num.on_grid(vs, vo, go, log_x=False)}
        return {"opamp-iq": vals, "opamp-offset": ovals}, {"opamp-iq": cur, "opamp-offset": ocur}, {"opamp-iq": "ok"}, {}


class TurnOn(Deck):
    """Both rails ramped from ±3 V to ±15 V at 0.3 V/µs: the follower's output settling at the reference."""
    name = "turn-on"
    ids = ("opamp-iq",)
    analysis = "tran"
    pack = False

    def __init__(self, cat):
        super().__init__(cat)
        self.c = self.cond("opamp-iq")["turn_on"]

    def body(self, m, s, x, derived):
        c = self.c
        v0, v1, t1 = float(c["v_start"]), float(c["v_end"]), float(c["ramp_s"])
        return [f"VP vp 0 PWL(0 {n(v0)} {n(t1)} {n(v1)} 1 {n(v1)})", f"VN vn 0 PWL(0 {n(-v0)} {n(t1)} {n(-v1)} 1 {n(-v1)})", "VIN in 0 0",
                oa("U", "in", "out", "vp", "vn", "out", m), f"RL out 0 {n(float(c['rl']))}"]

    def saves(self, x):
        return ["V(out)"]

    def tail(self, s):
        c = self.c
        return [f".tran {n(float(c['max_step_s']))} {n(float(c['t_end_s']))} 0 {n(float(c['max_step_s']))}"]

    def measure(self, d, s, x, derived):
        t, v = vec(d, "time"), vec(d, "V(out)")
        vos = derived.get("_vos") or 0.0
        late = [a for a, b in zip(t, v) if abs(b - vos) > float(self.c["settle_v"])]
        key = f"turn_on@{si(float(self.c['v_end']), 'V')}"
        cur = {"turn-on": num.thin(t, v, 80)}
        return {"opamp-iq": {key: late[-1] if late else 0.0}}, {"opamp-iq": cur}, {}, {}


# ----------------------------------------------------------------------------------------------- input
class Bias(Deck):
    """The two input currents and the offset, with the inputs at the reference, at a common-mode voltage, or
    through a source resistance; at 25 °C and at the temperatures of the ladder."""
    ids = ("opamp-bias", "opamp-offset", "opamp-iq")
    analysis = "op"
    pack = False

    def __init__(self, cat, temp=25.0, vcm=0.0, rs=0.0):
        super().__init__(cat)
        self.c = self.cond("opamp-bias")
        self.temp, self.vcm, self.rs = float(temp), float(vcm), float(rs)
        self.vp, self.vn = [float(v) for v in self.c["supply"]]
        self.name = "bias" + ("" if self.temp == 25 else f"{int(self.temp)}") + ("" if not self.vcm else f"-vcm{si(self.vcm, 'V')}") + ("" if not self.rs else f"-rs{si(self.rs, 'Ω')}")

    def body(self, m, s, x, derived):
        out = rails(self.vp, self.vn) + [f"VI in 0 {n(self.vcm)}"]
        if self.rs:
            out += [f"RS in inr {n(self.rs)}", "VIP inr inp 0"]
        else:
            out += ["VIP in inp 0"]
        return out + ["VNN out inn 0", oa("B", "inp", "inn", "vp", "vn", "out", m), f"RL out 0 {n(float(self.c['rl']))}"]

    def saves(self, x):
        return ["I(VIP)", "I(VNN)", "V(out)", "I(VP)"]

    def tail(self, s):
        return [".op"]

    def measure(self, d, s, x, derived):
        ibp, ibn, vo, iq = vec(d, "I(VIP)")[0], vec(d, "I(VNN)")[0], vec(d, "V(out)")[0], -vec(d, "I(VP)")[0]
        t = int(self.temp)
        vals, ovals, ivals, der = {}, {}, {}, {}
        if self.rs:
            ovals[f"vos@rs={si(self.rs, 'Ω')}"] = vo - self.vcm
        elif self.vcm:
            vals[f"ib@vcm={si(self.vcm, 'V')}"] = (ibp + ibn) / 2
            ovals[f"vos@vcm={si(self.vcm, 'V')}"] = vo - self.vcm
        else:
            tag = f"{t}°C" if t != 25 else "25°C"
            vals[f"ib@{tag}"] = (ibp + ibn) / 2
            vals[f"ibp@{tag}"], vals[f"ibn@{tag}"] = ibp, ibn
            vals[f"ios@{tag}"] = ibp - ibn
            ovals[f"vos@{tag}"] = vo
            ivals[f"iq@{tag}"] = iq
            der[f"_ib{t}"], der[f"_vos{t}"], der[f"_iq{t}"] = (ibp + ibn) / 2, vo, iq
        return {"opamp-bias": vals, "opamp-offset": ovals, "opamp-iq": ivals}, {}, {"opamp-bias": "ok"} if not self.vcm and not self.rs and t == 25 else {}, der


class InputZ(Deck):
    """The common-mode input impedance (both inputs driven together) and the differential one (one input
    driven, the other held by the servo), 1 kHz to 1 MHz."""
    ids = ("opamp-bias",)
    analysis = "ac"
    pack = False

    def __init__(self, cat, which):
        super().__init__(cat)
        self.c = self.cond("opamp-bias")
        self.which = which
        self.name = f"zin-{which}"
        self.vp, self.vn = [float(v) for v in self.c["supply"]]

    def body(self, m, s, x, derived):
        out = rails(self.vp, self.vn)
        if self.which == "cm":
            out += ["VCM cm 0 DC 0 AC 1", "VA cm inp 0", "VB cm inn 0"]
        else:
            out += ["VD inp 0 DC 0 AC 1", "L1 out inn 1G", "C1 inn 0 1G"]
        return out + [oa("I", "inp", "inn", "vp", "vn", "out", m), f"RL out 0 {n(float(self.c['rl']))}"]

    def saves(self, x):
        return ["I(VA)", "I(VB)"] if self.which == "cm" else ["I(VD)"]

    def tail(self, s):
        sw = self.c["zin_sweep"]
        return [f".ac dec {int(sw['per_decade'])} {n(float(sw['from']))} {n(float(sw['to']))}"]

    def measure(self, d, s, x, derived):
        f = freq(d)
        if self.which == "cm":
            i = [a + b for a, b in zip(vec(d, "I(VA)"), vec(d, "I(VB)"))]
            tag = "icm"
        else:
            i = list(vec(d, "I(VD)"))
            tag = "id"
        y1k, y1m = num.at_x(f, i, 1e3), num.at_x(f, i, 1e6)
        vals = {}
        if y1k is not None:
            vals[f"r{tag}"] = (1 / y1k.real) if abs(y1k.real) > 1e-15 else None
        if y1m is not None:
            vals[f"c{tag}"] = abs(y1m.imag) / (2 * math.pi * 1e6)
        return {"opamp-bias": vals}, {}, {}, {}


class Vcm(Deck):
    """The follower with its input swept 1 V beyond each rail: the offset against the common-mode voltage,
    the DC CMRR as its slope, the input range, and whether the output reverses."""
    name = "vcm"
    ids = ("opamp-offset", "opamp-phase-reversal")
    pack = False

    def __init__(self, cat):
        super().__init__(cat)
        self.c = self.cond("opamp-offset")
        self.vp, self.vn = [float(v) for v in self.c["supply"]]
        self.beyond = float(self.c["vcm_beyond"])

    def body(self, m, s, x, derived):
        return rails(self.vp, self.vn) + ["VIN in 0 0", oa("V", "in", "out", "vp", "vn", "out", m), f"RL out 0 {n(float(self.c['rl']))}"]

    def saves(self, x):
        return ["V(in)", "V(out)"]

    def tail(self, s):
        return [f".dc VIN {n(self.vn - self.beyond)} {n(self.vp + self.beyond)} {n(float(self.c['vcm_step']))}"]

    def measure(self, d, s, x, derived):
        vin, vout = list(vec(d, "V(in)")), list(vec(d, "V(out)"))
        vos = [o - i for o, i in zip(vout, vin)]
        v0 = num.interp(vin, vos, 0.0)
        vals = {}
        ok = [i for i, e in zip(vin, vos) if v0 is not None and abs(e - v0) < VICR_TOL]
        if ok:
            vals["vicr_low"], vals["vicr_high"] = min(ok) - self.vn, self.vp - max(ok)
            lo, hi = max(min(ok), self.vn + 2), min(max(ok), self.vp - 2)
            a, b = num.interp(vin, vos, lo), num.interp(vin, vos, hi)
            dv = (b - a) if a is not None and b is not None else None
            vals["cmrr_dc"] = db((hi - lo) / abs(dv)) if dv else None
            vals["cmrr_dc_note"] = "absent" if not dv else "ok"
        rev_in = any(o < -1 for i, o in zip(vin, vout) if self.vp - 2 < i <= self.vp) or any(o > 1 for i, o in zip(vin, vout) if self.vn <= i < self.vn + 2)
        rev_out = any(o < -1 for i, o in zip(vin, vout) if i > self.vp) or any(o > 1 for i, o in zip(vin, vout) if i < self.vn)
        pr = {"reversal_within_rails": rev_in, "reversal_beyond_rails": rev_out}
        g = self.grid("opamp-offset")
        cur = {"VOS vs VCM": num.on_grid(vin, vos, g, log_x=False)}
        gp = curve_grid(self.cat, "opamp-phase-reversal", "VOUT vs VIN")
        pcur = {"VOUT vs VIN": num.on_grid(vin, vout, gp, log_x=False)}
        return {"opamp-offset": vals, "opamp-phase-reversal": pr}, {"opamp-offset": cur, "opamp-phase-reversal": pcur}, {"opamp-offset": "ok", "opamp-phase-reversal": "ok"}, {}


class Iin(Deck):
    """The input current as the input is driven 2 V beyond each rail."""
    name = "iin"
    ids = ("opamp-phase-reversal",)
    pack = False

    def __init__(self, cat):
        super().__init__(cat)
        self.c = self.cond("opamp-phase-reversal")
        self.vp, self.vn = [float(v) for v in self.c["supply"]]

    def body(self, m, s, x, derived):
        return rails(self.vp, self.vn) + ["VIN in 0 0", "VIM in inp 0", oa("V", "inp", "out", "vp", "vn", "out", m), f"RL out 0 {n(float(self.c['rl']))}"]

    def saves(self, x):
        return ["V(in)", "I(VIM)"]

    def tail(self, s):
        c = self.c
        return [f".dc VIN {n(self.vn - float(c['beyond']))} {n(self.vp + float(c['beyond']))} {n(float(c['step']))}"]

    def measure(self, d, s, x, derived):
        vin, iin = list(vec(d, "V(in)")), list(vec(d, "I(VIM)"))
        vals = {}
        for p in self.c["iin_points"]:
            v = float(p)
            vals[f"iin@{'+' if v > 0 else ''}{si(v, 'V')}"] = num.interp(vin, iin, v)
        a, b = vals.get(f"iin@+{si(self.vp + 1, 'V')}"), vals.get(f"iin@{si(self.vn - 1, 'V')}")
        vals["input_protection"] = "present" if any(q is not None and abs(q) > 1e-6 for q in (a, b)) else "absent"
        g = curve_grid(self.cat, "opamp-phase-reversal", "IIN vs VIN")
        return {"opamp-phase-reversal": vals}, {"opamp-phase-reversal": {"IIN vs VIN": num.on_grid(vin, iin, g, log_x=False)}}, {}, {}


# ------------------------------------------------------------------------------------ rejection
class Cmrr(Deck):
    """The G = 1 difference amplifier, the common mode driven: three copies at VCM = 0 and near each rail."""
    name = "cmrr"
    ids = ("opamp-cmrr-f",)
    analysis = "ac"
    pack = False

    def __init__(self, cat):
        super().__init__(cat)
        self.c = self.cond("opamp-cmrr-f")
        self.vp, self.vn = [float(v) for v in self.c["supply"]]
        self.vcms = [float(v) for v in self.c["vcm"]]
        self.r = float(self.c["r"])

    def body(self, m, s, x, derived):
        out = rails(self.vp, self.vn)
        for i, v in enumerate(self.vcms):
            out += [f"VCM{i} vcm{i} 0 DC {n(v)} AC 1", f"R1_{i} vcm{i} inn{i} {n(self.r)}", f"R2_{i} inn{i} out{i} {n(self.r)}", f"R3_{i} vcm{i} inp{i} {n(self.r)}",
                    f"R4_{i} inp{i} 0 {n(self.r)}", oa(f"C{i}", f"inp{i}", f"inn{i}", "vp", "vn", f"out{i}", m), f"RL{i} out{i} 0 {n(float(self.c['rl']))}"]
        return out

    def saves(self, x):
        return [f"V(out{i})" for i in range(len(self.vcms))]

    def tail(self, s):
        sw = self.c["sweep"]
        return [f".ac dec {int(sw['per_decade'])} {n(float(sw['from']))} {n(float(sw['to']))}"]

    def measure(self, d, s, x, derived):
        f = freq(d)
        vals, cur = {}, {}
        g = self.grid("opamp-cmrr-f")
        for i, v in enumerate(self.vcms):
            gm = mag(d, f"V(out{i})")
            cm = [(-db(q) if q and q > 1e-12 else None) for q in gm]
            tag = f"vcm={si(v, 'V')}"
            for p in self.c["f_points"]:
                q = num.at_x(f, gm, float(p))
                vals[f"cmrr@{si(float(p), 'Hz')},{tag}"] = -db(q) if q and q > 1e-12 else None
            cur[f"CMRR, VCM={si(v, 'V')}"] = num.on_grid(f, [c if c is not None else 400.0 for c in cm], g)
            if i == 0:
                c0 = cm[0]
                vals["cmrr_corner"] = num.crossing(f, [c if c is not None else 400.0 for c in cm], c0 - 3, 0, False) if c0 is not None else None
                vals["cmrr_note"] = "absent" if c0 is None or c0 > 200 else "ok"
        return {"opamp-cmrr-f": vals}, {"opamp-cmrr-f": cur}, {"opamp-cmrr-f": "ok"}, {}


class Psrr(Deck):
    """The follower with 1 V of AC on the positive rail, the negative, or both in antiphase."""
    ids = ("opamp-psrr-f",)
    analysis = "ac"
    pack = False

    def __init__(self, cat, which):
        super().__init__(cat)
        self.c = self.cond("opamp-psrr-f")
        self.which = which
        self.name = f"psrr-{which}"
        self.vp, self.vn = [float(v) for v in self.c["supply"]]

    def body(self, m, s, x, derived):
        acp = " AC 1" if self.which in ("pos", "both") else ""
        acn = " AC -1" if self.which == "both" else (" AC 1" if self.which == "neg" else "")
        return [f"VP vp 0 DC {n(self.vp)}{acp}", f"VN vn 0 DC {n(self.vn)}{acn}", "VIN in 0 0", oa("P", "in", "out", "vp", "vn", "out", m), f"RL out 0 {n(float(self.c['rl']))}"]

    def saves(self, x):
        return ["V(out)"]

    def tail(self, s):
        sw = self.c["sweep"]
        return [f".ac dec {int(sw['per_decade'])} {n(float(sw['from']))} {n(float(sw['to']))}"]

    def measure(self, d, s, x, derived):
        f = freq(d)
        gm = mag(d, "V(out)")
        tag = self.which
        vals = {}
        for p in self.c["f_points"]:
            q = num.at_x(f, gm, float(p))
            vals[f"psrr_{tag}@{si(float(p), 'Hz')}"] = -db(q) if q and q > 1e-12 else None
        ps = [(-db(q) if q and q > 1e-12 else 400.0) for q in gm]
        if self.which == "pos":
            vals["psrr_corner"] = num.crossing(f, ps, ps[0] - 3, 0, False)
        vals[f"psrr_{tag}_note"] = "absent" if ps[0] > 200 else "ok"
        g = self.grid("opamp-psrr-f")
        return {"opamp-psrr-f": vals}, {"opamp-psrr-f": {f"PSRR {tag}": num.on_grid(f, ps, g)}}, {"opamp-psrr-f": "ok"} if self.which == "pos" else {}, {}


class Emirr(Deck):
    """A 100 mV carrier on the follower's input: the DC shift of the output, after it settles."""
    ids = ("opamp-emirr",)
    analysis = "tran"
    pack = False

    def __init__(self, cat, fc):
        super().__init__(cat)
        self.c = self.cond("opamp-emirr")
        self.fc = float(fc)
        self.name = f"emirr{si(self.fc, 'Hz')}"
        self.vp, self.vn = [float(v) for v in self.c["supply"]]
        self.span = float(self.c["cycles"]) / self.fc
        self.step = 1 / self.fc / int(self.c["steps_per_cycle"])

    def body(self, m, s, x, derived):
        return rails(self.vp, self.vn) + [f"VIN in 0 SIN(0 {n(float(self.c['amplitude']))} {n(self.fc)})", oa("E", "in", "out", "vp", "vn", "out", m), f"RL out 0 {n(float(self.c['rl']))}"]

    def saves(self, x):
        return ["V(out)"]

    def tail(self, s):
        return [f".tran {n(self.step)} {n(self.span)} 0 {n(self.step)}"]

    def measure(self, d, s, x, derived):
        t, v = vec(d, "time"), vec(d, "V(out)")
        y = num.resample(t, v, self.span / 2, self.span, 4000)
        shift = sum(y) / len(y) - (derived.get("_vos") or 0.0)
        k = si(self.fc, "Hz")
        amp = float(self.c["amplitude"])
        vals = {f"emirr@{k}": db(amp / abs(shift)) if abs(shift) > SHIFT_FLOOR else None, f"vos_shift@{k}": shift}
        return {"opamp-emirr": vals}, {}, {}, {}


# ------------------------------------------------------------------------------- gain and frequency
class Aol(Deck):
    """The open loop by the inductor/capacitor trick: 1 GH in the feedback and 1 GF to ground hold the DC
    point and open the loop above a microhertz. The main deck at the first load, supply and temperature;
    variants per load, supply, temperature and capacitive load."""
    ids = ("opamp-aol", "opamp-stability", "opamp-zout")
    analysis = "ac"
    pack = False

    def __init__(self, cat, tag="", rl=None, cl=None, supply=None, temp=25.0):
        super().__init__(cat)
        self.c = self.cond("opamp-aol")
        self.tag = tag
        self.name = "aol" + (f"-{tag}" if tag else "")
        self.rl = float(rl if rl is not None else self.c["rl"])
        self.cl = float(cl if cl is not None else self.c["cl"])
        self.vp, self.vn = [float(v) for v in (supply or self.c["supply"])]
        self.temp = float(temp)

    def body(self, m, s, x, derived):
        return rails(self.vp, self.vn) + ["VIN inp 0 DC 0 AC 1", "L1 out inn 1G", "C1 inn 0 1G", oa("A", "inp", "inn", "vp", "vn", "out", m),
                                          f"RL out 0 {n(self.rl)}", f"CL out 0 {n(self.cl)}"]

    def saves(self, x):
        return ["V(out)"]

    def tail(self, s):
        sw = self.c["sweep"]
        return [f".ac dec {int(sw['per_decade'])} {n(float(sw['from']))} {n(float(sw['to']))}"]

    def measure(self, d, s, x, derived):
        f = freq(d)
        a = list(vec(d, "V(out)"))
        g = [abs(q) for q in a]
        ph = unwrap([phase_deg(q) for q in a])
        ph = [p - ph[0] for p in ph]           # the DC phase as 0°
        fu = num.crossing(f, g, 1.0, 0, False)
        pm = (180 + num.interp(f, ph, fu)) if fu is not None else None
        vals, cur, der = {}, {}, {}
        if not self.tag:
            vals["aol_dc"] = db(g[0])
            vals["gbw@10kHz"] = (num.at_x(f, g, 1e4) or 0) * 1e4
            vals["gbw@100kHz"] = (num.at_x(f, g, 1e5) or 0) * 1e5
            vals["f_unity"] = fu
            vals["pm"] = pm
            f180 = num.crossing(f, ph, -180.0, 0, False)
            vals["gain_margin"] = -db(num.interp(f, g, f180)) if f180 is not None and num.interp(f, g, f180) else None
            vals["f_p1"] = num.crossing(f, g, g[0] / math.sqrt(2), 0, False)
            vals["f_p2"] = num.crossing(f, ph, -135.0, 0, False)
            vals["f_p2_note"] = "absent" if vals["f_p2"] is None else "ok"
            grid = self.grid("opamp-aol")
            cur["gain"] = num.on_grid(f, g, grid, log_y=True)
            cur["phase"] = num.on_grid(f, ph, grid)
            der["_aol25"], der["_gbw25"] = g[0], vals["gbw@100kHz"]
            stab = {f"pm@{si(self.cl, 'F')}": pm}
            out = {"opamp-aol": vals, "opamp-stability": stab}
            codes = {"opamp-aol": "ok" if fu else "n/a"}
            return out, {"opamp-aol": cur}, codes, der
        if self.tag.startswith("cl"):
            return {"opamp-stability": {f"pm@{si(self.cl, 'F')}": pm}}, {}, {}, {}
        vals[f"aol_dc@{self.tag}"] = db(g[0])
        vals[f"gbw@100kHz,{self.tag}"] = (num.at_x(f, g, 1e5) or 0) * 1e5
        vals[f"pm@{self.tag}"] = pm
        if self.temp != 25:
            der[f"_aol{int(self.temp)}"], der[f"_gbw{int(self.temp)}"] = g[0], vals[f"gbw@100kHz,{self.tag}"]
        cur[f"gain, {self.tag}"] = num.on_grid(f, g, self.grid("opamp-aol"), log_y=True)
        return {"opamp-aol": vals}, {"opamp-aol": cur}, {}, der


class AolSwing(Deck):
    """The open loop in DC: the input swept finely around the offset, the output read into three loads."""
    name = "aol-swing"
    ids = ("opamp-aol-swing",)
    pack = False

    def __init__(self, cat):
        super().__init__(cat)
        self.c = self.cond("opamp-aol-swing")
        self.vp, self.vn = [float(v) for v in self.c["supply"]]
        self.rls = [float(r) for r in self.c["rl"]]
        self.span, self.step = float(self.c["vin_span"]), float(self.c["vin_step"])

    def ready(self, derived):
        return derived.get("_vos") is not None

    def body(self, m, s, x, derived):
        # the sweep rides on the model's own offset, so that the output passes through the whole swing
        out = rails(self.vp, self.vn) + ["VIN inb 0 0", f"VOFF inp inb {n(derived['_vos'])}"]
        for i, rl in enumerate(self.rls):
            out += [oa(f"L{i}", "inp", "0", "vp", "vn", f"out{i}", m), f"RL{i} out{i} 0 {n(rl)}"]
        return out

    def saves(self, x):
        return ["V(inb)"] + [f"V(out{i})" for i in range(len(self.rls))]

    def tail(self, s):
        return [f".dc VIN {n(-self.span)} {n(self.span)} {n(self.step)}"]

    def measure(self, d, s, x, derived):
        vin = list(vec(d, "V(inb)"))
        vals, cur = {}, {}
        g = self.grid("opamp-aol-swing")
        for i, rl in enumerate(self.rls):
            vo = list(vec(d, f"V(out{i})"))
            k = si(rl, "Ω")

            def between(lo, hi):
                a, b = num.crossing(vin, vo, lo, vin[0] - 1, True), num.crossing(vin, vo, hi, vin[0] - 1, True)
                return (hi - lo) / (b - a) if a is not None and b is not None and b != a else None
            for sw in self.c["swings"]:
                v = float(sw)
                vals[f"aol@±{si(v, 'V')},{k}"] = between(-v, v)
            vals[f"vout_min@{k}"], vals[f"vout_max@{k}"] = min(vo), max(vo)
            cur[f"VOUT vs VIN, RL={k}"] = num.on_grid(vin, vo, g, log_x=False)
        a = vals.get(f"aol@±10V,{si(self.rls[0], 'Ω')}")
        vals["aol_db@±10V"] = db(a) if a else None
        return {"opamp-aol-swing": vals}, {"opamp-aol-swing": cur}, {"opamp-aol-swing": "ok" if a else "n/a"}, {}


class ClosedLoop(Deck):
    """The non-inverting amplifier at the ladder's gains and the inverter at −1, copies in one deck sharing
    the AC source, each with its feedback network, 2 kΩ and the capacitive load."""
    name = "closed-loop"
    ids = ("opamp-closed-loop",)
    analysis = "ac"
    pack = False

    def __init__(self, cat):
        super().__init__(cat)
        self.c = self.cond("opamp-closed-loop")
        self.vp, self.vn = [float(v) for v in self.c["supply"]]
        self.gains = [float(g) for g in self.c["gains"]]

    def network(self, i, gain):
        r1 = float(self.c["r1"])
        if gain == 1:
            return [oa(f"G{i}", "in", f"out{i}", "vp", "vn", f"out{i}", "DUT")]
        if gain < 0:
            rf = -gain * float(self.c["r_inv"])
            return [f"R1_{i} in inn{i} {n(float(self.c['r_inv']))}", f"R2_{i} out{i} inn{i} {n(rf)}", oa(f"G{i}", "0", f"inn{i}", "vp", "vn", f"out{i}", "DUT")]
        return [f"R1_{i} inn{i} 0 {n(r1)}", f"R2_{i} out{i} inn{i} {n(r1 * (gain - 1))}", oa(f"G{i}", "in", f"inn{i}", "vp", "vn", f"out{i}", "DUT")]

    def body(self, m, s, x, derived):
        out = rails(self.vp, self.vn) + ["VIN in 0 DC 0 AC 1"]
        for i, gain in enumerate(self.gains):
            out += [line.replace(" DUT", f" {m}") if line.startswith("X") else line for line in self.network(i, gain)]
            out += [f"RL{i} out{i} 0 {n(float(self.c['rl']))}", f"CL{i} out{i} 0 {n(float(self.c['cl']))}"]
        return out

    def saves(self, x):
        return [f"V(out{i})" for i in range(len(self.gains))]

    def tail(self, s):
        sw = self.c["sweep"]
        return [f".ac dec {int(sw['per_decade'])} {n(float(sw['from']))} {n(float(sw['to']))}"]

    def measure(self, d, s, x, derived):
        f = freq(d)
        vals, cur = {}, {}
        g = self.grid("opamp-closed-loop")
        for i, gain in enumerate(self.gains):
            mm = mag(d, f"V(out{i})")
            k = f"G={gain:g}"
            vals[f"bw@{k}"] = num.crossing(f, mm, mm[0] / math.sqrt(2), 0, False)
            vals[f"peak@{k}"] = db(max(mm) / mm[0]) if mm[0] else None
            cur[f"gain, {k}"] = num.on_grid(f, [q / mm[0] if mm[0] else 0 for q in mm], g, log_y=True)
        return {"opamp-closed-loop": vals}, {"opamp-closed-loop": cur}, {"opamp-closed-loop": "ok"}, {}


class SourceR(Deck):
    """G = +100 with the feedback network's total resistance stepped: peaking against RT (onsemi's figure)."""
    name = "rt"
    ids = ("opamp-stability",)
    analysis = "ac"
    pack = False

    def __init__(self, cat):
        super().__init__(cat)
        self.c = self.cond("opamp-stability")
        self.vp, self.vn = [float(v) for v in self.c["supply"]]
        self.rts = [float(r) for r in self.c["rt"]]
        self.gain = float(self.c["rt_gain"])

    def body(self, m, s, x, derived):
        out = rails(self.vp, self.vn) + ["VIN in 0 DC 0 AC 1"]
        for i, rt in enumerate(self.rts):
            r1 = rt / self.gain
            out += [f"R1_{i} inn{i} 0 {n(r1)}", f"R2_{i} out{i} inn{i} {n(rt - r1)}", oa(f"T{i}", "in", f"inn{i}", "vp", "vn", f"out{i}", m),
                    f"RL{i} out{i} 0 {n(float(self.c['rl']))}", f"CL{i} out{i} 0 {n(float(self.c['cl_rt']))}"]
        return out

    def saves(self, x):
        return [f"V(out{i})" for i in range(len(self.rts))]

    def tail(self, s):
        sw = self.c["sweep"]
        return [f".ac dec {int(sw['per_decade'])} {n(float(sw['from']))} {n(float(sw['to']))}"]

    def measure(self, d, s, x, derived):
        vals = {}
        pts = []
        for i, rt in enumerate(self.rts):
            mm = mag(d, f"V(out{i})")
            pk = db(max(mm) / mm[0]) if mm[0] else None
            vals[f"peak@G={self.gain:g},rt={si(rt, 'Ω')}"] = pk
            pts.append(pk)
        cur = {f"peaking vs RT, G={self.gain:g}": pts}
        return {"opamp-stability": vals}, {"opamp-stability": cur}, {"opamp-stability": "ok"}, {}


# ----------------------------------------------------------------------------------------------- output
class Swing(Deck):
    """Open-loop amplifiers driven 1 V into saturation each way into each load, and two shorted to the
    reference: the swing and the short-circuit current; variants per supply and temperature."""
    ids = ("opamp-swing", "opamp-isc")
    analysis = "op"
    pack = False

    def __init__(self, cat, tag="", supply=None, temp=25.0):
        super().__init__(cat)
        self.c = self.cond("opamp-swing")
        self.tag = tag
        self.name = "swing" + (f"-{tag}" if tag else "")
        self.vp, self.vn = [float(v) for v in (supply or self.c["supply"])]
        self.temp = float(temp)
        self.rls = [float(r) for r in self.c["rl"]] if not tag else [float(self.c["rl"][0])]

    def body(self, m, s, x, derived):
        vd = float(self.c["drive_v"])
        out = rails(self.vp, self.vn)
        for i, rl in enumerate(self.rls):
            out += [f"VIp{i} ip{i} 0 {n(vd)}", oa(f"Sp{i}", f"ip{i}", "0", "vp", "vn", f"op{i}", m), f"RLp{i} op{i} 0 {n(rl)}",
                    f"VIn{i} in{i} 0 {n(-vd)}", oa(f"Sn{i}", f"in{i}", "0", "vp", "vn", f"on{i}", m), f"RLn{i} on{i} 0 {n(rl)}"]
        out += [f"VIsp isp 0 {n(vd)}", oa("Ip", "isp", "0", "vp", "vn", "osp", m), "VSCp osp 0 0",
                f"VIsn isn 0 {n(-vd)}", oa("In", "isn", "0", "vp", "vn", "osn", m), "VSCn osn 0 0"]
        return out

    def saves(self, x):
        return [v for i in range(len(self.rls)) for v in (f"V(op{i})", f"V(on{i})")] + ["I(VSCp)", "I(VSCn)"]

    def tail(self, s):
        return [".op"]

    def measure(self, d, s, x, derived):
        vals, ivals, der = {}, {}, {}
        sfx = f",{self.tag}" if self.tag else ""
        for i, rl in enumerate(self.rls):
            k = si(rl, "Ω")
            vp, vn = vec(d, f"V(op{i})")[0], vec(d, f"V(on{i})")[0]
            vals[f"vom_hi@{k}{sfx}"], vals[f"vom_lo@{k}{sfx}"] = vp, vn
            vals[f"headroom_hi@{k}{sfx}"], vals[f"headroom_lo@{k}{sfx}"] = self.vp - vp, vn - self.vn
        isp, isn = vec(d, "I(VSCp)")[0], vec(d, "I(VSCn)")[0]
        ivals[f"isc_pos{'@' + self.tag if self.tag else ''}"], ivals[f"isc_neg{'@' + self.tag if self.tag else ''}"] = isp, isn
        if self.temp != 25:
            der[f"_isc{int(self.temp)}"] = isp
        else:
            der["_isc25"] = isp
        codes = {"opamp-swing": "ok", "opamp-isc": "ok"} if not self.tag else {}
        return {"opamp-swing": vals, "opamp-isc": ivals}, {}, codes, der


class VoIo(Deck):
    """The saturated amplifier into a swept load current, sourcing (or sinking): VOUT against IOUT."""
    ids = ("opamp-swing",)
    pack = False

    def __init__(self, cat, which):
        super().__init__(cat)
        self.c = self.cond("opamp-swing")
        self.which = which
        self.name = f"vo-io-{which}"
        self.vp, self.vn = [float(v) for v in self.c["supply"]]

    def body(self, m, s, x, derived):
        vd = float(self.c["drive_v"])
        if self.which == "source":
            return rails(self.vp, self.vn) + [f"VIp ip 0 {n(vd)}", oa("Sp", "ip", "0", "vp", "vn", "op", m), "IL op 0 0"]
        return rails(self.vp, self.vn) + [f"VIn in 0 {n(-vd)}", oa("Sn", "in", "0", "vp", "vn", "op", m), "IL 0 op 0"]

    def saves(self, x):
        return ["V(op)"]

    def tail(self, s):
        sw = self.c["io_sweep"]
        return [f".dc IL 0 {n(float(sw['to']))} {n(float(sw['step']))}"]

    def measure(self, d, s, x, derived):
        sw = self.c["io_sweep"]
        vo = list(vec(d, "V(op)"))
        il = [float(sw["step"]) * j for j in range(len(vo))]
        name = f"VOUT vs IOUT, {'sourcing' if self.which == 'source' else 'sinking'}"
        g = curve_grid(self.cat, "opamp-swing", name)
        cur = {name: num.on_grid(il, vo, g, log_x=False)}
        vals = {}
        if self.which != "source":
            return {"opamp-swing": {}}, {"opamp-swing": cur}, {}, {}
        for p in self.c["io_points"]:
            vals[f"vout_hi@io={si(float(p), 'A')}"] = num.interp(il, vo, float(p))
        return {"opamp-swing": vals}, {"opamp-swing": cur}, {}, {}


class Zout(Deck):
    """Current injected into the output, the voltage read: open loop (the servo) and closed loop at the gains."""
    ids = ("opamp-zout",)
    analysis = "ac"
    pack = False

    def __init__(self, cat, which):
        super().__init__(cat)
        self.c = self.cond("opamp-zout")
        self.which = which
        self.name = f"zout-{which}"
        self.vp, self.vn = [float(v) for v in self.c["supply"]]
        self.gains = [float(g) for g in self.c["gains"]]

    def body(self, m, s, x, derived):
        out = rails(self.vp, self.vn)
        if self.which == "ol":
            return out + ["VIN inp 0 0", "L1 out inn 1G", "C1 inn 0 1G", oa("ZO", "inp", "inn", "vp", "vn", "out", m), "IINJ 0 out AC 1"]
        r1 = float(self.c["r1"])
        for i, gain in enumerate(self.gains):
            if gain == 1:
                out += ["VIN in 0 0", oa(f"Z{i}", "in", f"out{i}", "vp", "vn", f"out{i}", m)]
            else:
                out += [f"R1_{i} inn{i} 0 {n(r1)}", f"R2_{i} out{i} inn{i} {n(r1 * (gain - 1))}", oa(f"Z{i}", "in", f"inn{i}", "vp", "vn", f"out{i}", m)]
            out += [f"IINJ{i} 0 out{i} AC 1"]
        return out

    def saves(self, x):
        return ["V(out)"] if self.which == "ol" else [f"V(out{i})" for i in range(len(self.gains))]

    def tail(self, s):
        sw = self.c["sweep"]
        return [f".ac dec {int(sw['per_decade'])} {n(float(sw['from']))} {n(float(sw['to']))}"]

    def measure(self, d, s, x, derived):
        f = freq(d)
        vals, cur = {}, {}
        g = self.grid("opamp-zout")
        if self.which == "ol":
            z = mag(d, "V(out)")
            for p in self.c["f_points"]:
                vals[f"zo_ol@{si(float(p), 'Hz')}"] = num.at_x(f, z, float(p))
            cur["ZO open loop"] = num.on_grid(f, z, g, log_y=True)
            return {"opamp-zout": vals}, {"opamp-zout": cur}, {"opamp-zout": "ok"}, {}
        for i, gain in enumerate(self.gains):
            z = mag(d, f"V(out{i})")
            for p in self.c["f_points_cl"]:
                vals[f"zo_cl@{si(float(p), 'Hz')},G={gain:g}"] = num.at_x(f, z, float(p))
            cur[f"ZO, G={gain:g}"] = num.on_grid(f, z, g, log_y=True)
        return {"opamp-zout": vals}, {"opamp-zout": cur}, {}, {}


# ------------------------------------------------------------------------------------ transients
class Sine(Deck):
    """One sine through a stage, the last cycles analysed by Goertzel: the base of every distortion deck."""
    analysis = "tran"
    pack = False

    def __init__(self, cat, mid, f, amp, gain=1.0, rl=None, tag="", supply=None):
        super().__init__(cat)
        self.mid = mid
        self.c = self.cond(mid)
        self.f, self.amp, self.gain, self.tag = float(f), float(amp), float(gain), tag
        self.rl = float(rl if rl is not None else self.c["rl"])
        self.vp, self.vn = [float(v) for v in (supply or self.c["supply"])]
        self.cycles = int(self.c["cycles"])
        self.analysed = int(self.c["analysed_cycles"])
        self.steps = int(self.c["steps_per_cycle"])

    def stage(self, m):
        if self.gain == 1:
            return [oa("D", "in", "out", "vp", "vn", "out", m)]
        if self.gain < 0:
            r = float(self.c["r_inv"])
            return [f"R1 in inn {n(r)}", f"R2 out inn {n(-self.gain * r)}", oa("D", "0", "inn", "vp", "vn", "out", m)]
        r1 = float(self.c["r1"])
        return [f"R1 inn 0 {n(r1)}", f"R2 out inn {n(r1 * (self.gain - 1))}", oa("D", "in", "inn", "vp", "vn", "out", m)]

    def body(self, m, s, x, derived):
        return rails(self.vp, self.vn) + [f"VIN in 0 SIN(0 {n(self.amp / abs(self.gain))} {n(self.f)})"] + self.stage(m) + [f"RL out 0 {n(self.rl)}"]

    def saves(self, x):
        return ["V(out)"]

    def tail(self, s):
        step = 1 / self.f / self.steps
        return [f".tran {n(step)} {n(self.cycles / self.f)} 0 {n(step)}"]

    def harmonics(self, d):
        t, v = vec(d, "time"), vec(d, "V(out)")
        t1 = t[-1]
        y = num.resample(t, v, t1 - self.analysed / self.f, t1, self.analysed * self.steps)
        return [num.goertzel(y, self.analysed * h) for h in range(1, 11)]

    def thd(self, d):
        amps = self.harmonics(d)
        h1 = amps[0]
        return (math.sqrt(sum(a * a for a in amps[1:])) / h1 if h1 else None), amps


class ThdF(Sine):
    """THD at the frequency ladder, at a level and gain."""
    ids = ("opamp-thd-f",)

    def __init__(self, cat, f, vrms, gain):
        super().__init__(cat, "opamp-thd-f", f, float(vrms) * math.sqrt(2), gain)
        self.vrms = float(vrms)
        self.name = f"thd-{si(self.f, 'Hz')}-{vrms:g}Vrms-G{gain:g}"
        self.key = f"{si(self.f, 'Hz')},{vrms:g}Vrms,G={gain:g}"

    def measure(self, d, s, x, derived):
        thd, amps = self.thd(d)
        vals = {f"thd@{self.key}": thd}
        if self.f == 1e3 and self.gain == 1 and self.vrms == 3:
            vals["hd2@1kHz,3Vrms,G=1"], vals["hd3@1kHz,3Vrms,G=1"] = (amps[1] / amps[0], amps[2] / amps[0]) if amps[0] else (None, None)
        return {"opamp-thd-f": vals}, {}, {"opamp-thd-f": "ok"}, {}


class ThdLevel(Sine):
    ids = ("opamp-thd-level",)

    def __init__(self, cat, vrms):
        super().__init__(cat, "opamp-thd-level", cat["opamp-thd-level"]["conditions"]["f"], float(vrms) * math.sqrt(2))
        self.vrms = float(vrms)
        self.name = f"thd-level-{vrms:g}Vrms"

    def measure(self, d, s, x, derived):
        thd, amps = self.thd(d)
        return {"opamp-thd-level": {f"thd@{si(self.f, 'Hz')},{self.vrms:g}Vrms": thd, f"vout@{self.vrms:g}Vrms": amps[0]}}, {}, {}, {}


class ThdLoad(Sine):
    ids = ("opamp-thd-load",)

    def __init__(self, cat, rl):
        c = cat["opamp-thd-load"]["conditions"]
        super().__init__(cat, "opamp-thd-load", c["f"], float(c["vrms"]) * math.sqrt(2), rl=rl)
        self.name = f"thd-load-{si(self.rl, 'Ω')}"

    def measure(self, d, s, x, derived):
        thd, amps = self.thd(d)
        k = si(self.rl, "Ω")
        return {"opamp-thd-load": {f"thd@{k}": thd, f"vout@{k}": amps[0]}}, {}, {"opamp-thd-load": "ok"}, {}


class MaxVo(Sine):
    """A 10 V peak sine at 20, 50 and 100 kHz: the output's peak and distortion, where the slew limit bites."""
    ids = ("opamp-max-vo-f",)

    def __init__(self, cat, f):
        c = cat["opamp-max-vo-f"]["conditions"]
        super().__init__(cat, "opamp-max-vo-f", f, float(c["amplitude"]))
        self.name = f"maxvo-{si(self.f, 'Hz')}"

    def measure(self, d, s, x, derived):
        thd, amps = self.thd(d)
        k = si(self.f, "Hz")
        return {"opamp-max-vo-f": {f"thd@{k}": thd, f"vopk@{k}": amps[0]}}, {}, {}, {}


class Imd(Deck):
    """Two tones: SMPTE (60 Hz + 7 kHz, 4:1) or CCIF (19 + 20 kHz, 1:1), 3 Vrms in all."""
    ids = ("opamp-imd",)
    analysis = "tran"
    pack = False

    def __init__(self, cat, which):
        super().__init__(cat)
        self.c = self.cond("opamp-imd")
        self.which = which
        self.name = f"imd-{which}"
        self.vp, self.vn = [float(v) for v in self.c["supply"]]
        self.t = self.c[which]

    def body(self, m, s, x, derived):
        t = self.t
        return rails(self.vp, self.vn) + [f"VIN in mid SIN(0 {n(float(t['a1']))} {n(float(t['f1']))})", f"VIN2 mid 0 SIN(0 {n(float(t['a2']))} {n(float(t['f2']))})",
                                          oa("D", "in", "out", "vp", "vn", "out", m), f"RL out 0 {n(float(self.c['rl']))}"]

    def saves(self, x):
        return ["V(out)"]

    def tail(self, s):
        t = self.t
        return [f".tran {n(float(t['step_s']))} {n(float(t['t_end_s']))} 0 {n(float(t['step_s']))}"]

    def measure(self, d, s, x, derived):
        t = self.t
        tt, v = vec(d, "time"), vec(d, "V(out)")
        t0, t1, count = float(t["t_from_s"]), float(t["t_end_s"]), int(t["samples"])
        y = num.resample(tt, v, t0, t1, count)
        span = t1 - t0
        k = lambda f: int(round(f * span))  # noqa: E731
        if self.which == "smpte":
            carrier = num.goertzel(y, k(float(t["f2"])))
            side = math.sqrt(sum(num.goertzel(y, k(float(t["f2"]) + j * float(t["f1"]))) ** 2 + num.goertzel(y, k(float(t["f2"]) - j * float(t["f1"]))) ** 2 for j in (1, 2)))
            val = side / carrier if carrier else None
        else:
            tones = num.goertzel(y, k(float(t["f1"]))) + num.goertzel(y, k(float(t["f2"])))
            prods = num.goertzel(y, k(float(t["f2"]) - float(t["f1"]))) + num.goertzel(y, k(2 * float(t["f1"]) - float(t["f2"]))) + num.goertzel(y, k(2 * float(t["f2"]) - float(t["f1"])))
            val = prods / tones if tones else None
        return {"opamp-imd": {f"imd_{self.which}": val}}, {}, {"opamp-imd": "ok"} if self.which == "smpte" else {}, {}


class Step(Deck):
    """A step through a follower (or the inverter): the slew between 10 % and 90 %, the settling, the
    small-signal rise and overshoot, the overload recovery; one deck per fixture."""
    analysis = "tran"
    pack = False

    def __init__(self, cat, mid, name, v0, v1, gain=1.0, cl=100e-12, supply=None, temp=25.0, key=""):
        super().__init__(cat)
        self.mid = mid
        self.c = self.cond(mid)
        self.name = name
        self.v0, self.v1, self.gain, self.cl = float(v0), float(v1), float(gain), float(cl)
        self.vp, self.vn = [float(v) for v in (supply or self.c["supply"])]
        self.temp = float(temp)
        self.key = key
        self.t0, self.edge, self.width = float(self.c["t_start_s"]), float(self.c["edge_s"]), float(self.c["width_s"])

    def body(self, m, s, x, derived):
        g = self.gain
        src = f"VIN in 0 PULSE({n(self.v0 / abs(g))} {n(self.v1 / abs(g))} {n(self.t0)} {n(self.edge)} {n(self.edge)} {n(self.width)} {n(2 * self.width)})"
        if g == 1:
            st = [oa("S", "in", "out", "vp", "vn", "out", m)]
        elif g < 0:
            r = float(self.c["r_inv"])
            st = [f"R1 in inn {n(r)}", f"R2 out inn {n(-g * r)}", oa("S", "0", "inn", "vp", "vn", "out", m)]
        else:
            r1 = float(self.c["r1"])
            st = [f"R1 inn 0 {n(r1)}", f"R2 out inn {n(r1 * (g - 1))}", oa("S", "in", "inn", "vp", "vn", "out", m)]
        return rails(self.vp, self.vn) + [src] + st + [f"RL out 0 {n(float(self.c['rl']))}", f"CL out 0 {n(self.cl)}"]

    def saves(self, x):
        return ["V(out)"]

    def tail(self, s):
        return [f".tran {n(float(self.c['max_step_s']))} {n(float(self.c['t_end_s']))} 0 {n(float(self.c['max_step_s']))}"]

    def wave(self, d):
        return vec(d, "time"), vec(d, "V(out)")


class Slew(Step):
    ids = ("opamp-slew",)

    def measure(self, d, s, x, derived):
        t, v = self.wave(d)
        t1 = self.t0 + self.edge + self.width
        seg = [(a, b) for a, b in zip(t, v) if self.t0 <= a <= t1]
        ta, tb = [p[0] for p in seg], [p[1] for p in seg]
        lo, hi = min(tb), max(tb)
        up = self.gain > 0
        a, b = (num.crossing(ta, tb, lo + 0.1 * (hi - lo), 0, True), num.crossing(ta, tb, lo + 0.9 * (hi - lo), 0, True)) if up else \
               (num.crossing(ta, tb, hi - 0.1 * (hi - lo), 0, False), num.crossing(ta, tb, hi - 0.9 * (hi - lo), 0, False))
        sr = abs(0.8 * (hi - lo) / (b - a)) if a is not None and b is not None and b != a else None
        vals = {f"sr_pos@{self.key}": sr}
        der = {}
        if self.key == self.c["main"]:
            seg2 = [(a_, b_) for a_, b_ in zip(t, v) if a_ >= t1]
            ta2, tb2 = [p[0] for p in seg2], [p[1] for p in seg2]
            f90, f10 = num.crossing(ta2, tb2, hi - 0.1 * (hi - lo), t1, False), num.crossing(ta2, tb2, hi - 0.9 * (hi - lo), t1, False)
            vals[f"sr_neg@{self.key}"] = abs(0.8 * (hi - lo) / (f10 - f90)) if f90 is not None and f10 is not None and f10 != f90 else None
            der["_sr25"] = sr
            cur = {"opamp-slew": {f"step, {self.key}": num.thin(t, v, int(self.c["curve_points"]))}}
            return {"opamp-slew": vals}, cur, {"opamp-slew": "ok" if sr else "n/a"}, der
        if self.temp != 25:
            der[f"_sr{int(self.temp)}"] = sr
        return {"opamp-slew": vals}, {}, {}, der


class Settling(Step):
    ids = ("opamp-settling",)

    def measure(self, d, s, x, derived):
        t, v = self.wave(d)
        t1 = self.t0 + self.edge + self.width
        seg = [(a, b) for a, b in zip(t, v) if self.t0 <= a <= t1]
        final = seg[-1][1]
        step = abs(self.v1 - self.v0)
        vals = {}
        for pct in self.c["bands"]:
            band = float(pct) * step
            outside = [a for a, b in seg if abs(b - final) > band]
            vals[f"ts@{float(pct) * 100:g}%,{self.key}"] = (outside[-1] - self.t0) if outside else 0.0
        err = [(a - self.t0, (b - final) / step) for a, b in seg]
        cur = {f"error, {self.key}": num.thin([p[0] for p in err], [p[1] for p in err], int(self.c["curve_points"]))}
        return {"opamp-settling": vals}, {"opamp-settling": cur}, {"opamp-settling": "ok"}, {}


class Overload(Step):
    ids = ("opamp-overload",)

    def measure(self, d, s, x, derived):
        t, v = self.wave(d)
        t1 = self.t0 + self.edge + self.width          # the drive returns to zero here
        back = [a for a, b in zip(t, v) if a >= t1 + float(self.c["after_s"]) and abs(b) > float(self.c["recovered_v"])]
        sign = "pos" if self.v1 < 0 else "neg"        # the inverter: a negative drive overloads positive
        vals = {f"trec_{sign}": (back[-1] - t1) if back else 0.0, f"vout_overloaded_{sign}": max(v) if sign == "pos" else min(v)}
        cur = {f"recovery {sign}": num.thin(t, v, int(self.c["curve_points"]))}
        return {"opamp-overload": vals}, {"opamp-overload": cur}, {"opamp-overload": "ok"} if sign == "neg" else {}, {}


class SmallStep(Step):
    ids = ("opamp-step", "opamp-stability")

    def measure(self, d, s, x, derived):
        t, v = self.wave(d)
        step = self.v1 - self.v0
        seg = [(a, b) for a, b in zip(t, v) if a >= self.t0]
        ta, tb = [p[0] for p in seg], [p[1] for p in seg]
        a, b = num.crossing(ta, tb, 0.1 * step, 0, True), num.crossing(ta, tb, 0.9 * step, 0, True)
        over = (max(tb) - step) / step * 100
        vals = {f"tr@{self.key}": (b - a) if a is not None and b is not None else None, f"overshoot@{self.key}": over}
        cur = {f"step, {self.key}": num.thin(t, v, int(self.c["curve_points"]))}
        if self.mid == "opamp-step":
            return {"opamp-step": vals}, {"opamp-step": cur}, {"opamp-step": "ok"}, {}
        return {"opamp-stability": {f"overshoot@{self.key}": over}}, {"opamp-stability": cur}, {}, {}


# ----------------------------------------------------------------------------------------------- noise
class Noise(Deck):
    """The follower's input-referred noise with a source resistance, by .noise."""
    ids = ("opamp-noise", "opamp-noise-rs")
    analysis = "noise"
    pack = False

    def __init__(self, cat, rs, tag, supply=None, sweep=None):
        super().__init__(cat)
        self.c = self.cond("opamp-noise")
        self.rs, self.tag = float(rs), tag
        self.name = f"noise-{tag}"
        self.vp, self.vn = [float(v) for v in (supply or self.c["supply"])]
        self.sw = sweep or self.c["sweep"]

    def body(self, m, s, x, derived):
        out = rails(self.vp, self.vn) + ["VIN in 0 DC 0 AC 1"]
        if self.rs:
            out += [f"RS in inr {n(self.rs)}", oa("N", "inr", "out", "vp", "vn", "out", m)]
        else:
            out += [oa("N", "in", "out", "vp", "vn", "out", m)]
        return out + [f"RL out 0 {n(float(self.c['rl']))}"]

    def tail(self, s):
        sw = self.sw
        return [f".noise V(out) VIN dec {int(sw['per_decade'])} {n(float(sw['from']))} {n(float(sw['to']))}"]

    def measure(self, d, s, x, derived):
        f = freq(d)
        name = derived.get("_plot_name", "")
        inn = mag(d, "v(inoise_spectrum)") if "v(inoise_spectrum)" in d else mag(d, "v(inoise)")
        if "^2" in name:
            inn = [math.sqrt(v) for v in inn]
        return {}, {}, {}, {f"_noise@{self.tag}": [f, inn]}


# ------------------------------------------------------------------------------------------------ plan
def plan(cat, engine):
    """Every op-amp deck in the order their dependencies need, for the measurements this engine runs."""
    decks = [Runs(cat), IqSweep(cat), TurnOn(cat)]
    bc = cat["opamp-bias"]["conditions"]
    decks += [Bias(cat)] + [Bias(cat, temp=t) for t in bc["temps_c"] if float(t) != 25.0] + [Bias(cat, vcm=v) for v in bc["vcm"]] + [Bias(cat, rs=bc["rs"])]
    decks += [InputZ(cat, "cm"), InputZ(cat, "diff"), Vcm(cat), Iin(cat), Cmrr(cat), Psrr(cat, "pos"), Psrr(cat, "neg"), Psrr(cat, "both")]
    decks += [Emirr(cat, f) for f in cat["opamp-emirr"]["conditions"]["carriers"]]
    ac = cat["opamp-aol"]["conditions"]
    decks += [Aol(cat)]
    decks += [Aol(cat, tag=si(float(r), "Ω"), rl=r) for r in ac["rl_variants"]]
    decks += [Aol(cat, tag=supply_tag(sp), supply=sp) for sp in ac["supply_variants"]]
    decks += [Aol(cat, tag=f"{int(float(t))}°C", temp=t) for t in ac["temps_c"]]
    decks += [Aol(cat, tag=f"cl{si(float(c), 'F')}", cl=c) for c in cat["opamp-stability"]["conditions"]["cl"] if float(c) != float(ac["cl"])]
    decks += [AolSwing(cat), ClosedLoop(cat), SourceR(cat)]
    sc = cat["opamp-swing"]["conditions"]
    decks += [Swing(cat)] + [Swing(cat, tag=supply_tag(sp), supply=sp) for sp in sc["supply_variants"]] + [Swing(cat, tag=f"{int(float(t))}°C", temp=t) for t in sc["temps_c"]]
    decks += [VoIo(cat, "source"), VoIo(cat, "sink"), Zout(cat, "ol"), Zout(cat, "cl")]
    decks += [MaxVo(cat, f) for f in cat["opamp-max-vo-f"]["conditions"]["f"]]
    sl = cat["opamp-slew"]["conditions"]
    for fx in sl["fixtures"]:
        decks.append(Slew(cat, "opamp-slew", f"slew-{fx['key']}".replace(",", "-").replace("=", ""), -fx["step"] / 2, fx["step"] / 2, fx.get("gain", 1), fx.get("cl", sl["cl"]),
                          fx.get("supply"), fx.get("temp", 25), fx["key"]))
    st = cat["opamp-settling"]["conditions"]
    for fx in st["fixtures"]:
        decks.append(Settling(cat, "opamp-settling", f"settle-{fx['key']}".replace(",", "-").replace("=", ""), -fx["step"] / 2, fx["step"] / 2, fx.get("gain", 1), st["cl"], key=fx["key"]))
    ov = cat["opamp-overload"]["conditions"]
    vo = float(ov["drive_v"]) * abs(float(ov["gain"]))          # the steps are given at the output: the drive times the gain
    decks += [Overload(cat, "opamp-overload", "overload-neg", 0, vo, ov["gain"], ov["cl"], key="-"),
              Overload(cat, "opamp-overload", "overload-pos", 0, -vo, ov["gain"], ov["cl"], key="+")]
    ss = cat["opamp-step"]["conditions"]
    decks += [SmallStep(cat, "opamp-step", f"step-{si(float(c), 'F')}", 0, ss["step_v"], 1, c, key=f"{si(float(c), 'F')},G=1") for c in ss["cl"]]
    sb = cat["opamp-stability"]["conditions"]
    decks += [SmallStep(cat, "opamp-stability", f"ovs-{si(float(c), 'F')}", 0, sb["step_v"], 1, c, key=f"{si(float(c), 'F')},G=1") for c in sb["cl_overshoot"]]
    nz = cat["opamp-noise"]["conditions"]
    decks += [Noise(cat, 0, "rs0"), Noise(cat, nz["rs_in"], f"rs{si(float(nz['rs_in']), 'Ω')}"), Noise(cat, 0, supply_tag(nz["supply_variant"]), supply=nz["supply_variant"], sweep=nz["spot_sweep"])]
    nr = cat["opamp-noise-rs"]["conditions"]
    decks += [Noise(cat, r, f"vt{si(float(r), 'Ω')}", sweep=nr["spot_sweep"]) for r in nr["rs_ladder"]]
    decks += [Noise(cat, r, f"w{si(float(r), 'Ω')}", sweep=nr["weighted_sweep"]) for r in nr["rs_weighted"]]
    tf = cat["opamp-thd-f"]["conditions"]
    decks += [ThdF(cat, f, v, g) for g, levels in ((1, tf["vrms"]), (tf["gain2"], tf["vrms"][-1:])) for v in levels for f in tf["f"]]
    decks += [ThdLevel(cat, v) for v in cat["opamp-thd-level"]["conditions"]["vrms"]]
    decks += [Imd(cat, "smpte"), Imd(cat, "ccif")]
    decks += [ThdLoad(cat, r) for r in cat["opamp-thd-load"]["conditions"]["rl"]]
    return [dk for dk in decks if all(engine in cat[i]["engines"] for i in dk.ids)]


def finalize(cat, values, curves, derived):
    """What needs several decks: the temperature ratios, the noise spectra into numbers and curves, the
    full-power bandwidth, the clipping level, the largest capacitive load, the separation of one amplifier."""
    bc = cat["opamp-bias"]["conditions"]
    temps = sorted(float(t) for t in bc["temps_c"])
    hot, cold = int(max(temps)), int(min(temps))
    ov = values.setdefault("opamp-offset", {})
    a, b = derived.get(f"_vos{hot}"), derived.get(f"_vos{cold}")
    if a is not None and b is not None:
        ov["dvos_dt"] = (a - b) / (hot - cold)
        ov["drift_note"] = "absent" if abs(ov["dvos_dt"]) < 1e-9 else "ok"
    bv = values.setdefault("opamp-bias", {})
    a, b = derived.get(f"_ib{hot}"), derived.get("_ib25")
    if a is not None and b:
        bv[f"ib_ratio@{hot}°C/25°C"] = a / b
    iv = values.setdefault("opamp-iq", {})
    a, b = derived.get(f"_iq{hot}"), derived.get("_iq25")
    if a is not None and b:
        iv[f"iq_ratio@{hot}°C/25°C"] = a / b
        iv["iq_temperature_note"] = "absent" if abs(a / b - 1) < 1e-3 else "ok"
    av = values.setdefault("opamp-aol", {})
    ac = cat["opamp-aol"]["conditions"]
    th = int(float(max(ac["temps_c"])))
    a, b = derived.get(f"_aol{th}"), derived.get("_aol25")
    if a and b:
        av[f"aol_ratio@{th}°C/25°C"] = a / b
    a, b = derived.get(f"_gbw{th}"), derived.get("_gbw25")
    if a and b:
        av[f"gbw_ratio@{th}°C/25°C"] = a / b
    isv = values.setdefault("opamp-isc", {})
    sth = int(float(max(cat["opamp-swing"]["conditions"]["temps_c"])))
    a, b = derived.get(f"_isc{sth}"), derived.get("_isc25")
    if a and b:
        isv[f"isc_ratio@{sth}°C/25°C"] = a / b
    slv = values.setdefault("opamp-slew", {})
    sl = cat["opamp-slew"]["conditions"]
    hot_sl = max([int(float(fx["temp"])) for fx in sl["fixtures"] if "temp" in fx] or [25])
    a, b = derived.get(f"_sr{hot_sl}"), derived.get("_sr25")
    if a and b:
        slv[f"sr_ratio@{hot_sl}°C/25°C"] = a / b
    # the full-power bandwidth from the slew rate and the swing
    mv = values.setdefault("opamp-max-vo-f", {})
    sw = values.get("opamp-swing") or {}
    vom = sw.get(f"vom+@{si(float(cat['opamp-swing']['conditions']['rl'][0]), 'Ω')}")
    if b and vom:
        mv["fpbw"] = b / (2 * math.pi * vom)
    pts = [(float(f), mv.get(f"vopk@{si(float(f), 'Hz')}")) for f in cat["opamp-max-vo-f"]["conditions"]["f"]]
    curves.setdefault("opamp-max-vo-f", {})["VO peak vs f"] = [p[1] for p in pts]
    # the clipping level: where THD against level passes 1 %
    tl = values.get("opamp-thd-level") or {}
    tc = cat["opamp-thd-level"]["conditions"]
    levels = [float(v) for v in tc["vrms"]]
    thds = [tl.get(f"thd@{si(float(tc['f']), 'Hz')},{v:g}Vrms") for v in levels]
    pairs = [(v, q) for v, q in zip(levels, thds) if q is not None]
    if pairs:
        tl["v_clip@1%"] = num.crossing([p[0] for p in pairs], [p[1] for p in pairs], 0.01, 0, True)
        curves.setdefault("opamp-thd-level", {})["THD vs level"] = [q for _, q in pairs]
    tf = values.get("opamp-thd-f") or {}
    tfc = cat["opamp-thd-f"]["conditions"]
    fs = [float(f) for f in tfc["f"]]
    for g, levels in ((1, tfc["vrms"]), (tfc["gain2"], tfc["vrms"][-1:])):
        for v in levels:
            pts = [tf.get(f"thd@{si(f, 'Hz')},{float(v):g}Vrms,G={float(g):g}") for f in fs]
            if any(p is not None for p in pts):
                curves.setdefault("opamp-thd-f", {})[f"THD vs f, {float(v):g}Vrms, G={float(g):g}"] = pts
    tld = values.get("opamp-thd-load") or {}
    rls = [float(r) for r in cat["opamp-thd-load"]["conditions"]["rl"]]
    curves.setdefault("opamp-thd-load", {})["THD vs RL"] = [tld.get(f"thd@{si(r, 'Ω')}") for r in rls]
    # stability: the largest capacitive load with 45° of margin, from the margins against CL
    sb = values.get("opamp-stability") or {}
    cls = sorted(float(c) for c in cat["opamp-stability"]["conditions"]["cl"] + [cat["opamp-aol"]["conditions"]["cl"]])
    pms = [sb.get(f"pm@{si(c, 'F')}") for c in cls]
    good = [(c, p) for c, p in zip(cls, pms) if p is not None]
    if good:
        curves.setdefault("opamp-stability", {})["PM vs CL"] = [p for _, p in good]
        below = [c for c, p in good if p < 45]
        sb["cl_max@45deg"] = (min(below) if below else max(c for c, _ in good))
    # noise
    nz = cat["opamp-noise"]["conditions"]
    nv = values.setdefault("opamp-noise", {})
    en = derived.get("_noise@rs0")
    if en:
        f, e = en
        for p in nz["f_points"]:
            nv[f"en@{si(float(p), 'Hz')}"] = num.at_x(f, e, float(p))
        e10k = num.at_x(f, e, 1e4)
        corner = None
        if e10k:
            for a_, b_ in sorted(zip(f, e), reverse=True):
                if a_ <= 1e4 and b_ >= math.sqrt(2) * e10k:
                    corner = a_
                    break
        nv["f_corner_en"] = corner
        for lo, hi in nz["bands"]:
            nv[f"en_rms@{si(float(lo), 'Hz')}-{si(float(hi), 'Hz')}"] = integrate_noise(f, e, float(lo), float(hi))
        rms = nv.get("en_rms@100mHz-10Hz")
        nv["en_pp@0.1-10Hz"] = 6.6 * rms if rms else None
        g = cat["opamp-noise"].get("grid")
        cur = {"en": num.on_grid(f, e, g, log_y=True)}
        tot = derived.get(f"_noise@rs{si(float(nz['rs_in']), 'Ω')}")
        if tot:
            rs = float(nz["rs_in"])
            inn = [math.sqrt(max(b_ * b_ - a_ * a_ - 4 * K_B * T_K * rs, 0.0)) / rs for a_, b_ in zip(e, tot[1])]
            nv["in@1kHz"] = num.at_x(f, inn, 1e3)
            nv["in_note"] = "absent" if (nv["in@1kHz"] or 0) < 1e-16 else "ok"
            cur["in"] = num.on_grid(f, inn, g, log_y=True)
        sv = derived.get(f"_noise@{supply_tag(nz['supply_variant'])}")
        if sv:
            nv[f"en@1kHz,{supply_tag(nz['supply_variant'])}"] = num.at_x(sv[0], sv[1], 1e3)
        nv["noise_sources"] = "absent" if (nv.get("en@1kHz") or 0) < 1e-10 else "present"
        curves["opamp-noise"] = cur
        nv["_code"] = "ok"
    nr = cat["opamp-noise-rs"]["conditions"]
    nrv = values.setdefault("opamp-noise-rs", {})
    vt = []
    for r in nr["rs_ladder"]:
        sp = derived.get(f"_noise@vt{si(float(r), 'Ω')}")
        v = num.at_x(sp[0], sp[1], 1e3) if sp else None
        vt.append(v)
        nrv[f"vt@1kHz,rs={si(float(r), 'Ω')}"] = v
        if v:
            nrv[f"nf@rs={si(float(r), 'Ω')}"] = 10 * math.log10(v * v / (4 * K_B * T_K * float(r)))
    curves.setdefault("opamp-noise-rs", {})["VT vs RS"] = vt
    for r in nr["rs_weighted"]:
        sp = derived.get(f"_noise@w{si(float(r), 'Ω')}")
        if sp:
            f, e = sp
            k = si(float(r), "Ω")
            nrv[f"en_flat@rs={k}"] = integrate_noise(f, e, 20, 20e3)
            nrv[f"en_a@rs={k}"] = integrate_noise(f, e, 20, 20e3, a_weight)
            nrv[f"en_riaa@rs={k}"] = integrate_noise(f, e, 20, 30e3, riaa_weight)
    if nrv:
        nrv["_code"] = "ok"
    # one amplifier in the subcircuit: nothing to separate
    values["opamp-separation"] = {"separation": "absent", "_code": "absent"}
