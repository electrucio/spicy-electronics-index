"""A preview of the FET and op-amp benches on ngspice: every measurement of docs/fet-characterisation.md
and docs/opamp-characterisation.md, run on one model per part, as numbers (docs/bench-preview-2026-10.md).
Not the pipeline, which is data/bench/measurements.yaml, the decks in docker/sim/bench and the records:
the decks here are the draft of decks_jfet, decks_mos and decks_opamp (docs/bench-roadmap.md), written
in the syntax the three engines share, and the numbers say what each model can and cannot do.

    make bench-preview MODELS=<dir> OUT=<dir>
    python3 docker/sim/preview/bench_preview.py <models dir> <work dir>

The models dir holds one file per part under the names `PARTS` gives (the recipes in data/models/parts/
say where each comes from; the text never enters git). ngspice must be on the PATH; standard library only,
plus docker/sim/bench's `num` and `raw`.
"""
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench import num, raw  # noqa: E402

MODELS = Path(sys.argv[1]).resolve()
WORK = Path(sys.argv[2]).resolve()
WORK.mkdir(parents=True, exist_ok=True)
TWO_PI = 2 * math.pi

# part: (file, name, kind of element, pins)
PARTS = {
    "jfet": {"J201": ("J201_csm.LIB", "J201", "J"), "2N5457": ("2N5457_CSM.LIB", "2N5457", "J"), "2N3819": ("CSM1455.LIB", "2N3819", "J")},
    "mosfet": {"2N7000": ("zetex_2n7000.lib", "2N7000", "X"), "BS170": ("BS170P.spice.txt", "BS170P", "X"), "IRF510": ("irf510.lib", "IRF510", "M")},
    "opamp": {"TL072": ("TL072.301", "TL072", "X"), "NE5532": ("NE553x.lib", "NE5532", "X"), "RC4558": ("RC4558.301", "RC4558", "X")},
}


def prepare_models():
    """The IRF510 card alone out of the 1988 IR collection; the others as they came."""
    src = (MODELS / "pwrmos.lib").read_text(errors="replace")
    m = re.search(r"^\.model IRF510\s.*?(?=^\*\$)", src, re.S | re.M)
    (MODELS / "irf510.lib").write_text(m.group(0) + "\n")


def run(name, lines):
    """Run one deck in ngspice, return its plots (raw.read) and the log."""
    deck = WORK / f"{name}.cir"
    deck.write_text("\n".join(["* " + name, *lines, ".end"]) + "\n")
    rawp = WORK / f"{name}.raw"
    if rawp.exists():
        rawp.unlink()
    env = dict(os.environ, SPICE_ASCIIRAWFILE="1")
    p = subprocess.run(["ngspice", "-b", "-r", rawp.name, deck.name], cwd=WORK, capture_output=True, text=True, env=env, timeout=600)
    log = p.stdout + p.stderr
    (WORK / f"{name}.log").write_text(log)
    plots = raw.read(rawp) if rawp.exists() and rawp.stat().st_size > 0 else []
    return plots, log


def vec(plot, name):
    d = plot["data"]
    for k in (name.lower(), f"v({name.lower()})", f"i({name.lower()})"):
        if k in d:
            return list(d[k])
    raise KeyError(f"{name} not in {sorted(d)[:12]}")


def cur(plot, source):
    """The current through a source, whatever node shares its name."""
    return list(plot["data"][f"i({source.lower()})"])


def pick(plots, kind):
    keys = {"dc": "dc", "ac": "ac", "tran": "tran", "noise": "noise spectral", "op": "operating"}[kind]
    for p in plots:
        if keys in p["name"].lower():
            return p
    return plots[0] if plots else None


def mag(z):
    return abs(z) if isinstance(z, complex) else abs(float(z))


def phase_deg(z):
    return math.degrees(math.atan2(z.imag, z.real)) if isinstance(z, complex) else 0.0


def at(xs, ys, x):
    """ys at x by linear interpolation on sorted xs; the last point stands for an x just past it."""
    if xs and abs(x - xs[-1]) <= 1e-6 * max(1.0, abs(x)) + 1e-9:
        return ys[-1]
    if xs and abs(x - xs[0]) <= 1e-6 * max(1.0, abs(x)) + 1e-9:
        return ys[0]
    for i in range(1, len(xs)):
        if xs[i - 1] <= x <= xs[i] or xs[i] <= x <= xs[i - 1]:
            t = (x - xs[i - 1]) / (xs[i] - xs[i - 1]) if xs[i] != xs[i - 1] else 0
            return ys[i - 1] + t * (ys[i] - ys[i - 1])
    return None


def x_where(xs, ys, level, log_y=False):
    """The first x at which ys crosses `level` (interpolated; on log(ys) when asked)."""
    f = (lambda v: math.log10(v) if v > 0 else -99) if log_y else (lambda v: v)
    lv = f(level)
    for i in range(1, len(xs)):
        a, b = f(ys[i - 1]), f(ys[i])
        if (a - lv) * (b - lv) <= 0 and a != b:
            return xs[i - 1] + (lv - a) / (b - a) * (xs[i] - xs[i - 1])
    return None


def fmt(v, unit=""):
    if v is None:
        return "n/a"
    if isinstance(v, str):
        return v
    return num.si(v, unit) if hasattr(num, "si") else f"{v:.4g}{unit}"


def head(part, kind):
    f, _, _ = PARTS[kind][part]
    return [f'.include "{(MODELS / f).as_posix()}"', ".options reltol=1e-4"]


def dev(part, kind, name, d, g, s):
    _, model, el = PARTS[kind][part]
    if el == "J":
        return f"J{name} {d} {g} {s} {model}"
    if el == "M":
        return f"M{name} {d} {g} {s} {s} {model}"
    return f"X{name} {d} {g} {s} {model}"


def harmonics(tt, v, t0, t1, cycles, hmax=10):
    """Amplitudes of harmonics 1..hmax of a tone with `cycles` periods between t0 and t1."""
    y = num.resample(tt, v, t0, t1, 8192)
    return [abs(num.goertzel(y, cycles * h)) for h in range(1, hmax + 1)]


def thd_of(tt, v, t0, t1, cycles):
    m = harmonics(tt, v, t0, t1, cycles)
    return math.sqrt(sum(x * x for x in m[1:])) / m[0] if m[0] else None


def sine_tran(f, cycles=12):
    """The .tran card for `cycles` periods of a tone at f, 400 points per period."""
    per = 1 / f
    return f".tran {per / 400:.4e} {cycles * per:.4e} 0 {per / 400:.4e}", 4 * per, cycles * per, cycles - 4


def integrate_noise(f, en, f0, f1, weight=None):
    """rms over f0..f1 of a density en(f) (V/√Hz), optionally weighted, trapezoid on a log grid."""
    tot = 0.0
    for i in range(1, len(f)):
        a, b = f[i - 1], f[i]
        if b <= f0 or a >= f1:
            continue
        a2, b2 = max(a, f0), min(b, f1)
        ea, eb = at(f, en, a2), at(f, en, b2)
        wa = weight(a2) if weight else 1.0
        wb = weight(b2) if weight else 1.0
        tot += 0.5 * ((ea * wa) ** 2 + (eb * wb) ** 2) * (b2 - a2)
    return math.sqrt(tot)


def a_weight(f):
    """IEC 61672 A-weighting, linear gain (0 dB at 1 kHz)."""
    f2 = f * f
    ra = (12194 ** 2 * f2 * f2) / ((f2 + 20.6 ** 2) * math.sqrt((f2 + 107.7 ** 2) * (f2 + 737.9 ** 2)) * (f2 + 12194 ** 2))
    return ra / 0.7943


def riaa_weight(f):
    """The RIAA playback curve as a linear gain, 0 dB at 1 kHz: a reproduction amplifier's weighting."""
    w = TWO_PI * f
    t1, t2, t3 = 3180e-6, 318e-6, 75e-6
    g = abs(complex(1, w * t2) / (complex(1, w * t1) * complex(1, w * t3)))
    w1 = TWO_PI * 1000
    g1 = abs(complex(1, w1 * t2) / (complex(1, w1 * t1) * complex(1, w1 * t3)))
    return g / g1


def card_facts(path, name):
    """What the model text says it can do: pins, element counts, family, supply resistor, temperature and noise carriers."""
    text = Path(path).read_text(errors="replace")
    m = re.search(rf"^\s*\.subckt\s+{re.escape(name)}\s+([^\n]*)", text, re.I | re.M)
    body = text
    if m:
        start = m.end()
        end = re.search(r"^\s*\.ends", text[start:], re.I | re.M)
        body = text[start:start + end.start()] if end else text[start:]
    counts = {}
    for line in body.splitlines():
        s = line.strip()
        if not s or s[0] in "*+.":
            continue
        counts[s[0].upper()] = counts.get(s[0].upper(), 0) + 1
    models = re.findall(r"^\s*\.model\s+(\S+)\s+(\w+)", text, re.I | re.M)
    kinds = sorted({k.upper() for _, k in models})
    facts = {"pins": m.group(1).split() if m else ["(model card)"], "elements": counts, "model types": kinds}
    facts["transistors (temperature and shot noise carriers)"] = counts.get("Q", 0) + counts.get("J", 0) + counts.get("M", 0)
    facts["behavioural sources"] = counts.get("B", 0) + counts.get("E", 0) + counts.get("G", 0) + counts.get("F", 0) + counts.get("H", 0)
    rp = re.search(r"^\s*RP\s+\S+\s+\S+\s+(\S+)", body, re.I | re.M)
    facts["supply resistor RP"] = rp.group(1) if rp else "none"
    facts["flicker noise (KF/AF)"] = "present" if re.search(r"\bKF\s*=", text, re.I) else "absent"
    facts["temperature coefficients (TC1/TC2/XTI/EG)"] = "present" if re.search(r"\b(TC1|TC2|XTI|EG)\s*=", text, re.I) else "only the junctions' defaults"
    facts["transit time (TT/TF)"] = "present" if re.search(r"\b(TT|TF)\s*=", text, re.I) else "absent"
    facts["breakdown (BV)"] = "present" if re.search(r"\bBV\s*=", text, re.I) else "absent"
    facts["family"] = ("Boyle macromodel (PSpice PARTS)" if counts.get("Q", 0) == 2 and counts.get("G", 0) + counts.get("E", 0) >= 3 and m
                       else "subcircuit" if m else f"card: {', '.join(kinds)}")
    return facts


# ---------------------------------------------------------------- JFET and MOSFET
def transfer(part, kind, vds_list, vg_from, vg_to, step, temp=25):
    lines = head(part, kind) + [f".temp {temp}", "VG g 0 0"]
    for v in vds_list:
        tag = str(v).replace(".", "p")
        lines += [f"VD{tag} d{tag} 0 {v}", dev(part, kind, tag, f"d{tag}", "g", "0")]
    lines += [f".dc VG {vg_from} {vg_to} {step}"]
    plots, log = run(f"{part}-transfer-{temp}", lines)
    p = pick(plots, "dc")
    if p is None:
        return None, log
    vg = vec(p, "v-sweep") if "v-sweep" in p["data"] else vec(p, "g")
    out = {}
    for v in vds_list:
        tag = str(v).replace(".", "p")
        out[v] = (vg, [-x for x in vec(p, f"vd{tag}")])
    return out, log


def derivative(xs, ys):
    g = []
    for i in range(len(xs)):
        a, b = max(0, i - 1), min(len(xs) - 1, i + 1)
        g.append((ys[b] - ys[a]) / (xs[b] - xs[a]) if xs[b] != xs[a] else 0)
    return g


def jfet_bench(part):
    kind, r = "jfet", {}
    tr, log = transfer(part, kind, [5, 10, 15], -8, 0.6, 0.005)
    if tr is None:
        return {"runs": "failed: " + log[-300:]}
    r["runs"] = "ok"
    for v in (5, 10, 15):
        vg, idv = tr[v]
        r[f"idss@{v}V"] = at(vg, idv, 0.0)
        r[f"vgsoff@1uA,{v}V"] = x_where(vg, idv, 1e-6, log_y=True)
    vg, id10 = tr[10]
    r["vgsoff@10nA,10V"] = x_where(vg, id10, 1e-8, log_y=True)
    gm = derivative(vg, id10)
    r["gfs@0V,10V"] = at(vg, gm, 0.0)
    for i_ref in (1e-4, 1e-3, 5e-3):
        x = x_where(vg, id10, i_ref)
        r[f"gm@{num.si(i_ref,'A')},10V"] = at(vg, gm, x) if x is not None else None
        r[f"vgs@{num.si(i_ref,'A')},10V"] = x
    # the stage current for noise, gm(f) and distortion: 1 mA, or half IDSS for a card that never reaches 1 mA
    i_noise = 1e-3 if r.get("vgs@1mA,10V") is not None else (r["idss@10V"] or 0) / 2
    vq = r.get("vgs@1mA,10V") if i_noise == 1e-3 else x_where(vg, id10, i_noise)
    r["noise_id"] = i_noise
    # tracer at VGS = 0, and at fractions of VGS(off)
    voff = r["vgsoff@1uA,10V"] or -2.0
    steps = [0.0] + [round(voff * k / 5, 3) for k in (1, 2, 3, 4)]
    lines = head(part, kind) + ["VD d 0 0"]
    for i, vgs in enumerate(steps):
        lines += [f"VG{i} g{i} 0 {vgs}", f"VA{i} d a{i} 0", dev(part, kind, f"T{i}", f"a{i}", f"g{i}", "0")]
    lines += [".dc VD 0 15 0.05"]
    plots, log = run(f"{part}-tracer", lines)
    p = pick(plots, "dc")
    if p is not None:
        vd = vec(p, "v-sweep")
        idt = vec(p, "va0")
        r["id@10V,vgs=0"] = at(vd, idt, 10.0)
        r["knee90%@vgs=0"] = x_where(vd, idt, 0.9 * (at(vd, idt, 15.0) or 0))
        slope = (at(vd, idt, 11.0) - at(vd, idt, 9.0)) / 2.0
        r["ro@10V,vgs=0"] = 1 / slope if slope > 0 else "absent (LAMBDA=0)"
        r["tracer_steps"] = steps
        r["tracer_id@10V"] = [at(vd, vec(p, f"va{i}"), 10.0) for i in range(len(steps))]
    else:
        r["tracer"] = "failed"
    # capacitances at 1 MHz, VDS = 15 V, VGS ladder; and the gate diode
    vgs_ladder = [0, -0.5, -1, -2, -3, -5]
    lines = head(part, kind)
    for i, vgs in enumerate(vgs_ladder):
        lines += [f"VG{i} g{i} 0 DC {vgs} AC 1", f"VD{i} d{i} 0 15", dev(part, kind, f"C{i}", f"d{i}", f"g{i}", "0")]
    lines += [".ac lin 1 1meg 1meg"]
    plots, log = run(f"{part}-cap", lines)
    p = pick(plots, "ac")
    if p is not None:
        w = TWO_PI * 1e6
        r["ciss_vs_vgs@15V"] = [(v, abs(vec(p, f"vg{i}")[0].imag) / w) for i, v in enumerate(vgs_ladder)]
        r["crss_vs_vgs@15V"] = [(v, abs(vec(p, f"vd{i}")[0].imag) / w) for i, v in enumerate(vgs_ladder)]
    lines = head(part, kind) + ["VG g 0 0", "VD d 0 0", dev(part, kind, "G", "d", "g", "0"), ".dc VG -20 1.5 0.01"]
    plots, log = run(f"{part}-gate", lines)
    p = pick(plots, "dc")
    if p is not None:
        vg = vec(p, "v-sweep")
        ig = [-x for x in vec(p, "vg")]
        r["igss@-15V"] = at(vg, ig, -15.0)
        r["vgs(fwd)@1mA"] = x_where(vg, ig, 1e-3)
    # noise: common source, ID = 1 mA at VDS = 10 V through RD = 1 kΩ
    if vq is not None:
        lines = head(part, kind) + [f"VG g 0 DC {vq} AC 1", "VDD vdd 0 15", f"RD vdd d {5 / i_noise:.4g}", dev(part, kind, "N", "d", "g", "0"),
                                    ".noise v(d) VG dec 10 1 1meg"]
        plots, log = run(f"{part}-noise", lines)
        p = pick(plots, "noise")
        if p is not None:
            f = vec(p, "frequency")
            en = vec(p, "inoise_spectrum")
            r["en@10Hz"], r["en@1kHz"], r["en@10kHz"] = (at(f, en, x) for x in (10, 1e3, 1e4))
            flat = r["en@10kHz"]
            corner = x_where(f, en, flat * math.sqrt(2)) if flat else None
            r["1/f corner"] = corner if corner and corner < 1e5 else "absent (no KF)"
        else:
            r["noise"] = "failed"
    # ohmic region: rDS(on) at VDS = 0 per VGS step, and its linearity over ±100 mV
    lines = head(part, kind) + ["VD d 0 0"]
    for i, vgs in enumerate(steps):
        lines += [f"VG{i} g{i} 0 {vgs}", f"VA{i} d a{i} 0", dev(part, kind, f"O{i}", f"a{i}", f"g{i}", "0")]
    lines += [".dc VD -0.1 0.1 0.002"]
    plots, log = run(f"{part}-ohmic", lines)
    p = pick(plots, "dc")
    if p is not None:
        vd = vec(p, "v-sweep")
        rows = []
        for i, vgs in enumerate(steps):
            idv = vec(p, f"va{i}")
            g0 = (at(vd, idv, 0.01) - at(vd, idv, -0.01)) / 0.02
            gp = (at(vd, idv, 0.1) - at(vd, idv, 0.08)) / 0.02
            gn = (at(vd, idv, -0.08) - at(vd, idv, -0.1)) / 0.02
            rows.append((vgs, 1 / g0 if g0 > 0 else None, (gp / gn) if gn else None))
        r["rds_on_vs_vgs"] = rows
        r["rds_on@vgs=0"] = rows[0][1]
    # gm against frequency at the noise stage's current; the frequency where the drain's AC current equals the gate's
    if vq is not None:
        lines = head(part, kind) + [f"VG g 0 DC {vq} AC 1", "VD d 0 10", dev(part, kind, "F", "d", "g", "0"), ".ac dec 20 1k 10g"]
        plots, log = run(f"{part}-freq", lines)
        p = pick(plots, "ac")
        if p is not None:
            f = [abs(x) for x in vec(p, "frequency")]
            gd = [mag(x) for x in cur(p, "vd")]
            gg = [mag(x) for x in cur(p, "vg")]
            r["gm@1kHz"] = at(f, gd, 1e3)
            r["f(|id/ig|=1)"] = x_where(f, [a / b if b else 1e9 for a, b in zip(gd, gg)], 1.0, log_y=True)
    # analogue switch: 1 V signal through the channel into 10 kΩ ‖ 100 pF, gate from 2·VGS(off) to 0 and back
    lines = head(part, kind) + ["VS s 0 1", f"VG g 0 PULSE({2 * voff} 0 1u 10n 10n 20u 40u)", dev(part, kind, "SW", "d", "g", "s"),
                                "RL d 0 10k", "CL d 0 100p", ".tran 5n 40u"]
    plots, log = run(f"{part}-switch", lines)
    p = pick(plots, "tran")
    if p is not None:
        tt = vec(p, "time")
        v = vec(p, "d")
        vmax = at(tt, v, 20e-6)
        on1 = [(a, b) for a, b in zip(tt, v) if 1e-6 <= a <= 21e-6]
        off1 = [(a, b) for a, b in zip(tt, v) if 21e-6 <= a <= 40e-6]
        t10 = x_where([a for a, _ in on1], [b for _, b in on1], 0.1 * vmax)
        t90 = x_where([a for a, _ in on1], [b for _, b in on1], 0.9 * vmax)
        f90 = x_where([a for a, _ in off1], [b for _, b in off1], 0.9 * vmax)
        f10 = x_where([a for a, _ in off1], [b for _, b in off1], 0.1 * vmax)
        r["t_on(10-90)"] = (t90 - t10) if t10 and t90 else None
        r["t_off(90-10)"] = (f10 - f90) if f90 and f10 else None
        r["v_on (1 V through 10 kΩ)"] = at(tt, v, 20e-6)
    # a reference common-source stage: 100 mVpk at 1 kHz, RD for VDS = 10 V at the noise current, harmonics 2..10
    if vq is not None:
        lines = head(part, kind) + [f"VG g 0 SIN({vq} 0.1 1k)", "VDD vdd 0 15", f"RD vdd d {5 / i_noise:.4g}", dev(part, kind, "D", "d", "g", "0"),
                                    ".tran 0.5u 12m 0 0.5u"]
        plots, log = run(f"{part}-thd", lines)
        p = pick(plots, "tran")
        if p is not None:
            tt, v = vec(p, "time"), vec(p, "d")
            y = num.resample(tt, v, 4e-3, 12e-3, 8192)
            mags = [abs(num.goertzel(y, 8 * h)) for h in range(1, 11)]
            r["thd(cs stage, 100mVpk)"] = math.sqrt(sum(m * m for m in mags[1:])) / mags[0]
            r["stage gain"] = mags[0] / 0.1
    # breakdown: the channel off (VGS = VGS(off) − 1 V), VDS to 60 V
    lines = head(part, kind) + [f"VG g 0 {voff - 1}", "VD d 0 0", dev(part, kind, "BV", "d", "g", "0"), ".dc VD 0 60 0.5"]
    plots, log = run(f"{part}-breakdown", lines)
    p = pick(plots, "dc")
    if p is not None:
        vd = vec(p, "v-sweep")
        idv = [-x for x in cur(p, "vd")]
        r["id(off)@30V"], r["id(off)@60V"] = at(vd, idv, 30.0), at(vd, idv, 60.0)
        r["breakdown"] = "absent (leakage flat to 60 V)" if (r["id(off)@60V"] or 0) < 10 * max(r["id(off)@30V"] or 1e-15, 1e-15) else "present"
    # the two junction capacitances: Cgs = Ciss − Crss per VGS (above), and Cgd against VDG at VGS = 0
    vdg_ladder = [0, 1, 2, 5, 10, 15, 20, 25]
    lines = head(part, kind)
    for i, v in enumerate(vdg_ladder):
        lines += [f"VG{i} g{i} 0 DC 0 AC 1", f"VD{i} d{i} 0 {v}", dev(part, kind, f"K{i}", f"d{i}", f"g{i}", "0")]
    lines += [".ac lin 1 1meg 1meg"]
    plots, log = run(f"{part}-cgd", lines)
    p = pick(plots, "ac")
    if p is not None:
        w = TWO_PI * 1e6
        r["cgd_vs_vdg@vgs=0"] = [(v, abs(cur(p, f"vd{i}")[0].imag) / w) for i, v in enumerate(vdg_ladder)]
    if "ciss_vs_vgs@15V" in r and "crss_vs_vgs@15V" in r:
        r["cgs_vs_vgs@15V"] = [(v, c - x) for (v, c), (_, x) in zip(r["ciss_vs_vgs@15V"], r["crss_vs_vgs@15V"])]
    # the gate's reverse leakage and the drain's share of it, at VGS = −10 and −15 V with the drain at 0 and at 10 V
    rows = []
    for vgs in (-10, -15):
        for vds in (0, 10):
            lines = head(part, kind) + [f"VG g 0 {vgs}", f"VD d 0 {vds}", "VSS s 0 0", dev(part, kind, "L", "d", "g", "s"), ".op"]
            plots, log = run(f"{part}-leak-{abs(vgs)}-{vds}", lines)
            p = pick(plots, "op")
            if p is not None:
                rows.append((vgs, vds, -cur(p, "vg")[0], -cur(p, "vd")[0], -cur(p, "vss")[0]))
    r["gate leakage (VGS, VDS, IG, ID share, IS share)"] = rows
    # charge injection of the switch: the step a 1 nF hold capacitor takes at turn-off
    lines = head(part, kind) + ["VS s 0 1", f"VG g 0 PULSE(0 {2 * voff} 20u 10n 10n 20u 100u)", dev(part, kind, "CI", "d", "g", "s"), "CH d 0 1n",
                                "RLK d 0 1G", ".tran 5n 40u"]
    plots, log = run(f"{part}-inject", lines)
    p = pick(plots, "tran")
    if p is not None:
        tt, v = vec(p, "time"), vec(p, "d")
        r["charge injection (1 nF hold)"] = 1e-9 * (at(tt, v, 30e-6) - at(tt, v, 19.9e-6))
    # a source follower too: 1 Vpk in, RS for the stage current, THD
    if vq is not None:
        rs_ = 5 / i_noise
        lines = head(part, kind) + [f"VG g 0 SIN({vq + 5} 1 1k)", "VDD vdd 0 15", f"RS s 0 {rs_:.4g}", dev(part, kind, "SF", "vdd", "g", "s"), sine_tran(1e3)[0]]
        plots, log = run(f"{part}-follower", lines)
        p = pick(plots, "tran")
        if p is not None:
            _, t0, t1, cyc = sine_tran(1e3)
            r["thd(source follower, 1 Vpk)"] = thd_of(vec(p, "time"), vec(p, "s"), t0, t1, cyc)
    # temperature: IDSS and VGS(off) at −55, 100, 125, 150 °C, and the zero-temperature-coefficient point
    curves = {25: tr[10]}
    for t in (-55, 100, 125, 150):
        trt, log = transfer(part, kind, [10], -8, 0.6, 0.005, temp=t)
        if trt:
            vg, idv = trt[10]
            curves[t] = trt[10]
            r[f"idss@10V,{t}C"] = at(vg, idv, 0.0)
            r[f"vgsoff@1uA,10V,{t}C"] = x_where(vg, idv, 1e-6, log_y=True)
            r[f"vgs@100uA,10V,{t}C"] = x_where(vg, idv, 1e-4)
    if 125 in curves:
        vg25, i25 = curves[25]
        vg125, i125 = curves[125]
        diff = [a - b for a, b in zip(i25, i125)]
        ztc = None
        for i in range(1, len(vg25)):
            if diff[i - 1] * diff[i] < 0 and i25[i] > 1e-6:
                ztc = (vg25[i], i25[i])
                break
        r["zero-TC point (VGS, ID)"] = ztc if ztc else "absent (no crossing above 1 µA)"
    r["card"] = card_facts(MODELS / PARTS[kind][part][0], PARTS[kind][part][1])
    r["agreement"] = "n/a (ngspice only here)"
    return r


def mos_bench(part):
    kind, r = "mosfet", {}
    tr, log = transfer(part, kind, [5, 10], 0, 10, 0.01)
    if tr is None:
        return {"runs": "failed: " + log[-300:]}
    r["runs"] = "ok"
    vg, id5 = tr[5]
    r["vth@250uA,5V"] = x_where(vg, id5, 250e-6)
    r["vth@1mA,5V"] = x_where(vg, id5, 1e-3)
    for v in (3, 4.5, 5, 10):
        r[f"id@vgs={v}V,5V"] = at(vg, id5, float(v))
    gm = derivative(vg, id5)
    for i_ref in (1e-2, 1e-1, 1.0):
        x = x_where(vg, id5, i_ref)
        r[f"gfs@{num.si(i_ref,'A')},5V"] = at(vg, gm, x) if x is not None else None
    # tracer and RDS(on) at VDS = 0.1 V
    steps = [2, 2.5, 3, 3.5, 4, 4.5, 5, 6, 8, 10]
    lines = head(part, kind) + ["VD d 0 0"]
    for i, vgs in enumerate(steps):
        lines += [f"VG{i} g{i} 0 {vgs}", f"VA{i} d a{i} 0", dev(part, kind, f"T{i}", f"a{i}", f"g{i}", "0")]
    lines += [".dc VD 0 10 0.02"]
    plots, log = run(f"{part}-tracer", lines)
    p = pick(plots, "dc")
    if p is not None:
        vd = vec(p, "v-sweep")
        r["tracer_id@10V"] = [(s, at(vd, vec(p, f"va{i}"), 10.0)) for i, s in enumerate(steps)]
        for vgs in (4.5, 10):
            i = steps.index(vgs)
            idv = at(vd, vec(p, f"va{i}"), 0.1)
            r[f"rdson@vgs={vgs}V,0.1V"] = 0.1 / idv if idv and idv > 0 else None
    # capacitances vs VDS at VGS = 0, 1 MHz: gate-driven (Ciss, Crss) and drain-driven (Coss)
    vds_ladder = [0, 1, 2, 5, 10, 15, 20, 25]
    lines = head(part, kind)
    for i, v in enumerate(vds_ladder):
        lines += [f"VG{i} g{i} 0 DC 0 AC 1", f"VD{i} d{i} 0 {v}", dev(part, kind, f"C{i}", f"d{i}", f"g{i}", "0")]
    lines += [".ac lin 1 1meg 1meg"]
    plots, log = run(f"{part}-cap-g", lines)
    p = pick(plots, "ac")
    w = TWO_PI * 1e6
    if p is not None:
        r["ciss_vs_vds"] = [(v, abs(vec(p, f"vg{i}")[0].imag) / w) for i, v in enumerate(vds_ladder)]
        r["crss_vs_vds"] = [(v, abs(vec(p, f"vd{i}")[0].imag) / w) for i, v in enumerate(vds_ladder)]
    lines = head(part, kind)
    for i, v in enumerate(vds_ladder):
        lines += [f"VG{i} g{i} 0 0", f"VD{i} d{i} 0 DC {v} AC 1", dev(part, kind, f"C{i}", f"d{i}", f"g{i}", "0")]
    lines += [".ac lin 1 1meg 1meg"]
    plots, log = run(f"{part}-cap-d", lines)
    p = pick(plots, "ac")
    if p is not None:
        r["coss_vs_vds"] = [(v, abs(vec(p, f"vd{i}")[0].imag) / w) for i, v in enumerate(vds_ladder)]
    # body diode: source positive, gate tied to source
    lines = head(part, kind) + ["VS s 0 0", "VDM d 0 0", dev(part, kind, "B", "d", "s", "s"), ".dc VS 0 1.5 0.005"]
    plots, log = run(f"{part}-body", lines)
    p = pick(plots, "dc")
    if p is not None:
        vs = vec(p, "v-sweep")
        isd = vec(p, "vdm")      # current into the drain source: forward body-diode current
        r["vsd@100mA"] = x_where(vs, isd, 0.1)
        r["vsd@1A"] = x_where(vs, isd, 1.0)
        r["isd@1.5V"] = at(vs, isd, 1.5)
    big = part == "IRF510"
    i_sw, vdd = (1.0, 25.0) if big else (0.2, 10.0)
    rl = vdd / i_sw
    # gate charge: IG = 100 µA into the gate, drain through RL to VDD; VGS(t) → Qg at 10 V, the plateau
    lines = head(part, kind) + ["IG 0 g PULSE(0 100u 1u 1n 1n 10m 20m)", "RGS g 0 1G", f"VDD vdd 0 {vdd}", f"RL vdd d {rl}", dev(part, kind, "Q", "d", "g", "0"),
                                ".tran 20n 2m"]
    plots, log = run(f"{part}-qg", lines)
    p = pick(plots, "tran")
    if p is not None:
        tt, vgs_t, vds_t = vec(p, "time"), vec(p, "g"), vec(p, "d")
        t10 = x_where(tt, vgs_t, 10.0)
        r["qg@10V"] = 100e-6 * (t10 - 1e-6) if t10 else None
        after = [(a, b) for a, b in zip(tt, vds_t) if a >= 1e-6]
        ta_, tb_ = [a for a, _ in after], [b for _, b in after]
        tp0 = x_where(ta_, tb_, 0.9 * vdd)
        tp1 = x_where(ta_, tb_, 0.1 * vdd)
        r["qgs (to plateau)"] = 100e-6 * (tp0 - 1e-6) if tp0 else None
        r["qgd (plateau)"] = 100e-6 * (tp1 - tp0) if tp0 and tp1 else None
        r["v_plateau"] = at(tt, vgs_t, (tp0 + tp1) / 2) if tp0 and tp1 else None
    # resistive-load switching: 0 → 10 V gate pulse through RG = 25 Ω
    lines = head(part, kind) + ["VGP gp 0 PULSE(0 10 1u 5n 5n 20u 40u)", "RG gp g 25", f"VDD vdd 0 {vdd}", f"RL vdd d {rl}", dev(part, kind, "S", "d", "g", "0"),
                                ".tran 2n 40u"]
    plots, log = run(f"{part}-switch", lines)
    p = pick(plots, "tran")
    if p is not None:
        tt, vds_t = vec(p, "time"), vec(p, "d")
        on = [(a, b) for a, b in zip(tt, vds_t) if 1e-6 <= a <= 21e-6]
        off = [(a, b) for a, b in zip(tt, vds_t) if 21e-6 <= a <= 40e-6]
        ta, tb = [a for a, _ in on], [b for _, b in on]
        fa, fb = [a for a, _ in off], [b for _, b in off]
        t90, t10 = x_where(ta, tb, 0.9 * vdd), x_where(ta, tb, 0.1 * vdd)
        r["td(on)"] = (t90 - 1e-6) if t90 else None
        r["tr"] = (t10 - t90) if t90 and t10 else None
        f10, f90 = x_where(fa, fb, 0.1 * vdd), x_where(fa, fb, 0.9 * vdd)
        r["td(off)"] = (f10 - 21e-6) if f10 else None
        r["tf"] = (f90 - f10) if f10 and f90 else None
        r["switch conditions"] = f"VDD {vdd} V, RL {rl:g} Ω, RG 25 Ω"
    # reverse recovery of the body diode: IF then −IF with 100 A/µs (big) or 10 A/µs
    didt = 100e6 if big else 10e6
    tr_ = 2 * i_sw / didt
    lines = head(part, kind) + [f"IF 0 s PULSE({i_sw} {-i_sw} 2u {tr_:.3e} 1 1 2)", "VDM d 0 0", "RS s 0 1e6", dev(part, kind, "RR", "d", "s", "s"), "DCLP 0 s DCL", ".model DCL D(IS=1e-14)",
                                f".tran {tr_ / 50:.3e} {2e-6 + tr_ + 2e-6:.3e}"]
    plots, log = run(f"{part}-trr", lines)
    p = pick(plots, "tran")
    if p is not None:
        tt, idio = vec(p, "time"), cur(p, "vdm")
        seg = [(a, b) for a, b in zip(tt, idio) if a >= 2e-6]
        ta, tb = [a for a, _ in seg], [b for _, b in seg]
        irm = min(tb) if tb else 0
        t0 = x_where(ta, tb, 0.0)
        tend = None
        if t0 and irm < 0:
            after = [(a, b) for a, b in seg if a > t0]
            tend = x_where([a for a, _ in after], [b for _, b in after], 0.1 * irm)
        r["irm"], r["trr"] = irm, ((tend - t0) if t0 and tend else None)
        r["reverse recovery"] = "present" if (r["trr"] or 0) > 2e-9 and abs(irm) > 0.05 * i_sw else "absent (no transit time: a capacitive spike only)"
    # noise of a common-source stage at ID = 10 mA, VDS = 10 V
    vg10 = x_where(vg, id5, 1e-2)
    if vg10:
        lines = head(part, kind) + [f"VG g 0 DC {vg10} AC 1", "VDD vdd 0 20", "RD vdd d 1k", dev(part, kind, "N", "d", "g", "0"), ".noise v(d) VG dec 10 1 1meg"]
        plots, log = run(f"{part}-noise", lines)
        p = pick(plots, "noise")
        if p is not None:
            f, en = vec(p, "frequency"), vec(p, "inoise_spectrum")
            r["en@10Hz"], r["en@1kHz"] = at(f, en, 10), at(f, en, 1e3)
            r["1/f"] = "absent (no KF)" if r["en@10Hz"] and r["en@1kHz"] and r["en@10Hz"] < 1.5 * r["en@1kHz"] else "present"
        # distortion of the same stage, 100 mVpk at 1 kHz
        lines = head(part, kind) + [f"VG g 0 SIN({vg10} 0.1 1k)", "VDD vdd 0 20", "RD vdd d 1k", dev(part, kind, "D", "d", "g", "0"), ".tran 0.5u 12m 0 0.5u"]
        plots, log = run(f"{part}-thd", lines)
        p = pick(plots, "tran")
        if p is not None:
            tt, v = vec(p, "time"), vec(p, "d")
            y = num.resample(tt, v, 4e-3, 12e-3, 8192)
            mags = [abs(num.goertzel(y, 8 * h)) for h in range(1, 11)]
            r["thd(cs stage, 100mVpk)"] = math.sqrt(sum(m * m for m in mags[1:])) / mags[0]
    # breakdown: VGS = 0, VDS to 100 V
    lines = head(part, kind) + ["VG g 0 0", "VD d 0 0", dev(part, kind, "BV", "d", "g", "0"), ".dc VD 0 100 0.5"]
    plots, log = run(f"{part}-breakdown", lines)
    p = pick(plots, "dc")
    if p is not None:
        vd = vec(p, "v-sweep")
        idv = [-x for x in cur(p, "vd")]
        r["idss@60V"], r["idss@100V"] = at(vd, idv, 60.0), at(vd, idv, 100.0)
        r["breakdown"] = "absent (leakage flat to 100 V)" if (r["idss@100V"] or 0) < 10 * max(r["idss@60V"] or 1e-15, 1e-15) else "present"
    # RDS(on) against drain current at VGS = 10 V and 4.5 V: the drain current forced, a clamp at 5 V
    imax = 4.0 if big else 1.0
    for vgs in (4.5, 10):
        lines = head(part, kind) + [f"VG g 0 {vgs}", "ID 0 d 0", "DCL d cl DCLMP", "VCL cl 0 5", ".model DCLMP D(IS=1e-14)", dev(part, kind, "R", "d", "g", "0"),
                                    f".dc ID 0.001 {imax} {imax / 1000}"]
        plots, log = run(f"{part}-rdson-id-{vgs}", lines)
        p = pick(plots, "dc")
        if p is not None:
            i_sw_ = vec(p, "v-sweep") if "v(v-sweep)" in p["data"] else vec(p, "i-sweep")
            vd = vec(p, "d")
            pts = []
            for i_ref in (0.01, 0.1, 0.5, 1.0, 2.0, 4.0):
                if i_ref <= imax:
                    v_ = at(i_sw_, vd, i_ref)
                    pts.append((i_ref, v_ / i_ref if v_ is not None and v_ < 4.5 else None))
            r[f"rdson_vs_id@vgs={vgs}V"] = pts
    # RDS(on) against VGS at ID = i_sw/2 (the drive floor: the lowest VGS within twice the 10 V value)
    lines = head(part, kind) + ["VG g 0 0", f"ID 0 d {i_sw / 2}", "DCL d cl DCLMP", "VCL cl 0 5", ".model DCLMP D(IS=1e-14)", dev(part, kind, "V", "d", "g", "0"), ".dc VG 1 15 0.05"]
    plots, log = run(f"{part}-rdson-vgs", lines)
    p = pick(plots, "dc")
    if p is not None:
        vg_ = vec(p, "v-sweep")
        vd = vec(p, "d")
        ron = [(v, d / (i_sw / 2) if d < 4.5 else None) for v, d in zip(vg_, vd)]
        r["rdson_vs_vgs@id=" + num.si(i_sw / 2, "A")] = [(v, x) for v, x in ron if v in (2, 2.5, 3, 3.5, 4, 4.5, 5, 6, 8, 10, 15)]
        r10 = at(vg_, [x if x is not None else 1e9 for _, x in ron], 10.0)
        floor = next((v for v, x in ron if x is not None and x < 2 * r10), None)
        r["drive floor (RDS(on) < 2× its 10 V value)"] = floor
    # third quadrant with the channel on: VGS = 10 V, source positive
    lines = head(part, kind) + ["VS s 0 0", "VDM d 0 0", "VG g s 10", dev(part, kind, "T3", "d", "g", "s"), ".dc VS 0 1.5 0.005"]
    plots, log = run(f"{part}-third", lines)
    p = pick(plots, "dc")
    if p is not None:
        vs = vec(p, "v-sweep")
        isd = cur(p, "vdm")
        r["vsd@100mA,vgs=10V (channel on)"] = x_where(vs, isd, 0.1)
        r["vsd@1A,vgs=10V (channel on)"] = x_where(vs, isd, 1.0)
    # Ciss against VGS at VDS = 0
    vgs_l = [0, 2, 4, 6, 8, 10]
    lines = head(part, kind)
    for i, v in enumerate(vgs_l):
        lines += [f"VG{i} g{i} 0 DC {v} AC 1", f"VD{i} d{i} 0 0", dev(part, kind, f"G{i}", f"d{i}", f"g{i}", "0")]
    lines += [".ac lin 1 1meg 1meg"]
    plots, log = run(f"{part}-ciss-vgs", lines)
    p = pick(plots, "ac")
    if p is not None:
        r["ciss_vs_vgs@vds=0"] = [(v, abs(cur(p, f"vg{i}")[0].imag) / (TWO_PI * 1e6)) for i, v in enumerate(vgs_l)]
    # clamped-inductive switching: Eon and Eoff at I = i_sw, VDD, L = 100 µH with a freewheel diode
    L = 100e-6
    ton = L * i_sw / vdd
    # the inductor as the current source it is during the edges, with a freewheel diode to VDD (the clamped-inductive fixture)
    ton = 5e-6
    lines = head(part, kind) + [f"VGP gp 0 PULSE(0 10 1u 20n 20n {ton:.3e} {2 * ton + 5e-6:.3e})", "RG gp g 25", f"VDD vdd 0 {vdd}", f"IL vdd dl {i_sw}",
                                "DFW dl dfw DFW", "RFW dfw vdd 0.02", ".model DFW D(IS=1e-12 N=1.1 CJO=100p)", "VIDM dl d 0",
                                "RSN d sn 10", "CSN sn 0 1n", dev(part, kind, "CI", "d", "g", "0"), ".options method=gear", f".tran 1n {3 * ton + 12e-6:.3e}"]
    plots, log = run(f"{part}-inductive", lines)
    p = pick(plots, "tran")
    if p is not None:
        tt, vds_t, id_t = vec(p, "time"), vec(p, "d"), cur(p, "vidm")
        t2 = 1e-6 + 2 * ton + 5e-6          # the second pulse's turn-on, with the current already flowing
        def energy(t0, t1):
            e = 0.0
            for i in range(1, len(tt)):
                if t0 <= tt[i] <= t1:
                    e += 0.5 * (vds_t[i] * id_t[i] + vds_t[i - 1] * id_t[i - 1]) * (tt[i] - tt[i - 1])
            return e
        r["eon (2nd pulse, 300 ns window)"] = energy(t2 - 20e-9, t2 + 300e-9)
        toff = t2 + ton
        r["eoff (300 ns window)"] = energy(toff - 20e-9, toff + 300e-9)
        r["inductive conditions"] = f"VDD {vdd} V, I {i_sw} A (current source + freewheel diode), RG 25 Ω"
    # a source follower too (mosfet-distortion's second stage): 1 Vpk in at ID = 10 mA
    if vg10:
        lines = head(part, kind) + [f"VG g 0 SIN({vg10 + 5} 1 1k)", "VDD vdd 0 20", "RS s 0 500", dev(part, kind, "SF", "vdd", "g", "s"), sine_tran(1e3)[0]]
        plots, log = run(f"{part}-follower", lines)
        p = pick(plots, "tran")
        if p is not None:
            _, t0, t1, cyc = sine_tran(1e3)
            r["thd(source follower, 1 Vpk)"] = thd_of(vec(p, "time"), vec(p, "s"), t0, t1, cyc)
    # temperature: Vth, RDS(on) at 10 V, gfs and the body diode at −55, 100, 125, 150, 175 °C; the zero-TC point
    curves = {25: tr[5]}
    for t_ in (-55, 100, 125, 150, 175):
        trt, log = transfer(part, kind, [5, 0.1], 0, 10, 0.01, temp=t_)
        if trt:
            vg, idv = trt[5]
            curves[t_] = trt[5]
            r[f"vth@1mA,5V,{t_}C"] = x_where(vg, idv, 1e-3)
            x = x_where(vg, idv, 0.1)
            r[f"gfs@100mA,{t_}C"] = at(vg, derivative(vg, idv), x) if x else None
            vg_, id01 = trt[0.1]
            r[f"rdson@vgs=10V,{t_}C"] = 0.1 / at(vg_, id01, 10.0) if at(vg_, id01, 10.0) else None
        lines = head(part, kind) + [f".temp {t_}", "VS s 0 0", "VDM d 0 0", dev(part, kind, "B", "d", "s", "s"), ".dc VS 0 1.5 0.005"]
        plots, log = run(f"{part}-body-{t_}", lines)
        p = pick(plots, "dc")
        if p is not None:
            r[f"vsd@100mA,{t_}C"] = x_where(vec(p, "v-sweep"), cur(p, "vdm"), 0.1)
    if 125 in curves:
        vg25, i25 = curves[25]
        _, i125 = curves[125]
        diff = [a - b for a, b in zip(i25, i125)]
        ztc = next(((vg25[i], i25[i]) for i in range(1, len(vg25)) if diff[i - 1] * diff[i] < 0 and i25[i] > 1e-4), None)
        r["zero-TC point (VGS, ID)"] = ztc if ztc else "absent (no crossing above 100 µA)"
    r["card"] = card_facts(MODELS / PARTS[kind][part][0], PARTS[kind][part][1])
    r["agreement"] = "n/a (ngspice only here)"
    return r


# ---------------------------------------------------------------- op-amps
def oa(part, name, inp, inn, vp, vn, out):
    return f"X{name} {inp} {inn} {vp} {vn} {out} {PARTS['opamp'][part][1]}"


def supplies(vp, vn, sfx=""):
    return [f"VP{sfx} vp{sfx} 0 {vp}", f"VN{sfx} vn{sfx} 0 {vn}"]


def opamp_bench(part):
    kind, r = "opamp", {}
    # runs: follower at four supplies; IQ and VOS
    lines = head(part, kind)
    for i, vs in enumerate((5, 9, 15, 18)):
        lines += supplies(vs, -vs, str(i)) + [f"VI{i} in{i} 0 0", oa(part, f"R{i}", f"in{i}", f"o{i}", f"vp{i}", f"vn{i}", f"o{i}"), f"RL{i} o{i} 0 2k"]
    lines += [".op"]
    plots, log = run(f"{part}-runs", lines)
    p = pick(plots, "op")
    if p is None:
        return {"runs": "failed: " + log[-400:]}
    r["runs"] = "ok"
    for i, vs in enumerate((5, 9, 15, 18)):
        r[f"iq@±{vs}V"] = -cur(p, f"vp{i}")[0]
        r[f"vos@±{vs}V"] = vec(p, f"o{i}")[0]
    # bias currents at ±15 V
    lines = head(part, kind) + supplies(15, -15) + ["VIP in inp 0", "VI in 0 0", "VNN out inn 0", oa(part, "B", "inp", "inn", "vp", "vn", "out"), "RL out 0 2k", ".op"]
    plots, log = run(f"{part}-bias", lines)
    p = pick(plots, "op")
    if p is not None:
        ibp, ibn = cur(p, "vip")[0], cur(p, "vnn")[0]
        r["ib+"], r["ib-"], r["ios"] = ibp, ibn, ibp - ibn
    # open-loop gain and phase by the inductor/capacitor trick
    lines = head(part, kind) + supplies(15, -15) + ["VIN inp 0 DC 0 AC 1", "L1 out inn 1G", "C1 inn 0 1G", oa(part, "A", "inp", "inn", "vp", "vn", "out"),
                                                   "RL out 0 2k", "CL out 0 100p", ".ac dec 20 1 100meg"]
    plots, log = run(f"{part}-aol", lines)
    p = pick(plots, "ac")
    if p is not None:
        f = [abs(x) for x in vec(p, "frequency")]
        a = vec(p, "out")
        g = [mag(x) for x in a]
        ph = [phase_deg(x) for x in a]
        r["aol_dc"] = 20 * math.log10(g[0])
        r["gbw@10kHz"] = (at(f, g, 1e4) or 0) * 1e4
        r["gbw@100kHz"] = (at(f, g, 1e5) or 0) * 1e5
        fu = x_where(f, g, 1.0, log_y=True)
        r["f_unity"] = fu
        r["phase_margin"] = (180 + at(f, ph, fu)) if fu else None
        r["f_p1"] = x_where(f, g, g[0] / math.sqrt(2))
    # offset against common mode (follower, ±15 V)
    lines = head(part, kind) + supplies(15, -15) + ["VIN in 0 0", oa(part, "V", "in", "out", "vp", "vn", "out"), "RL out 0 10k", ".dc VIN -16 16 0.02"]
    plots, log = run(f"{part}-vcm", lines)
    p = pick(plots, "dc")
    if p is not None:
        vin = vec(p, "v-sweep")
        vout = vec(p, "out")
        vos = [o - i for o, i in zip(vout, vin)]
        v0 = at(vin, vos, 0.0)
        ok = [i for i, e in zip(vin, vos) if abs(e - v0) < 1e-3]
        r["vicr-"], r["vicr+"] = (min(ok), max(ok)) if ok else (None, None)
        r["cmrr_dc"] = None
        if ok:
            lo, hi = max(min(ok), -10), min(max(ok), 10)
            dv = at(vin, vos, hi) - at(vin, vos, lo)
            r["cmrr_dc"] = 20 * math.log10((hi - lo) / abs(dv)) if dv else "absent (no VCM term)"
        r["reversal_within_rails"] = any(o < -1 for i, o in zip(vin, vout) if 13 < i <= 15) or any(o > 1 for i, o in zip(vin, vout) if -15 <= i < -13)
        r["reversal_1V_beyond_rails"] = any(o < -1 for i, o in zip(vin, vout) if i > 15) or any(o > 1 for i, o in zip(vin, vout) if i < -15)
    # CMRR and PSRR against frequency
    lines = head(part, kind) + supplies(15, -15) + ["VCM vcm 0 DC 0 AC 1", "R1 vcm inn 10k", "R2 inn out 10k", "R3 vcm inp 10k", "R4 inp 0 10k",
                                                   oa(part, "C", "inp", "inn", "vp", "vn", "out"), "RL out 0 2k", ".ac dec 20 1 10meg"]
    plots, log = run(f"{part}-cmrr", lines)
    p = pick(plots, "ac")
    if p is not None:
        f = [abs(x) for x in vec(p, "frequency")]
        g = [mag(x) for x in vec(p, "out")]
        r["cmrr@100Hz"], r["cmrr@1kHz"], r["cmrr@100kHz"] = (-20 * math.log10(at(f, g, x)) if at(f, g, x) else None for x in (100, 1e3, 1e5))
    for rail, (vpl, vnl) in {"+": ("DC 15 AC 1", "DC -15"), "-": ("DC 15", "DC -15 AC 1")}.items():
        lines = head(part, kind) + [f"VP vp 0 {vpl}", f"VN vn 0 {vnl}", "VIN in 0 0", oa(part, "P", "in", "out", "vp", "vn", "out"), "RL out 0 2k", ".ac dec 20 1 10meg"]
        plots, log = run(f"{part}-psrr{'p' if rail == '+' else 'n'}", lines)
        p = pick(plots, "ac")
        if p is not None:
            f = [abs(x) for x in vec(p, "frequency")]
            g = [mag(x) for x in vec(p, "out")]
            r[f"psrr{rail}@100Hz"], r[f"psrr{rail}@10kHz"] = (-20 * math.log10(at(f, g, x)) if at(f, g, x) else None for x in (100, 1e4))
    # swing against load, and short-circuit current: open loop, saturated
    lines = head(part, kind) + supplies(15, -15)
    loads = [600, 2000, 10000]
    for i, rl in enumerate(loads):
        lines += [f"VIp{i} ip{i} 0 1", oa(part, f"Sp{i}", f"ip{i}", "0", "vp", "vn", f"op{i}"), f"RLp{i} op{i} 0 {rl}",
                  f"VIn{i} in{i} 0 -1", oa(part, f"Sn{i}", f"in{i}", "0", "vp", "vn", f"on{i}"), f"RLn{i} on{i} 0 {rl}"]
    lines += ["VIsp isp 0 1", oa(part, "Ip", "isp", "0", "vp", "vn", "osp"), "VSCp osp 0 0",
              "VIsn isn 0 -1", oa(part, "In", "isn", "0", "vp", "vn", "osn"), "VSCn osn 0 0", ".op"]
    plots, log = run(f"{part}-swing", lines)
    p = pick(plots, "op")
    if p is not None:
        for i, rl in enumerate(loads):
            r[f"vom+@{num.si(rl,'Ω')}"] = vec(p, f"op{i}")[0]
            r[f"vom-@{num.si(rl,'Ω')}"] = vec(p, f"on{i}")[0]
        r["isc+"], r["isc-"] = cur(p, "vscp")[0], cur(p, "vscn")[0]
    # output impedance, closed loop (follower) and open loop
    lines = head(part, kind) + supplies(15, -15) + ["VIN in 0 0", oa(part, "Z", "in", "out", "vp", "vn", "out"), "IINJ 0 out AC 1", ".ac dec 20 10 100meg"]
    plots, log = run(f"{part}-zout-cl", lines)
    p = pick(plots, "ac")
    if p is not None:
        f = [abs(x) for x in vec(p, "frequency")]
        z = [mag(x) for x in vec(p, "out")]
        r["zo_cl@1kHz"], r["zo_cl@100kHz"], r["zo_cl@1MHz"] = (at(f, z, x) for x in (1e3, 1e5, 1e6))
    lines = head(part, kind) + supplies(15, -15) + ["VIN inp 0 0", "L1 out inn 1G", "C1 inn 0 1G", oa(part, "ZO", "inp", "inn", "vp", "vn", "out"), "IINJ 0 out AC 1", ".ac dec 20 10 100meg"]
    plots, log = run(f"{part}-zout-ol", lines)
    p = pick(plots, "ac")
    if p is not None:
        f = [abs(x) for x in vec(p, "frequency")]
        z = [mag(x) for x in vec(p, "out")]
        r["zo_ol@1kHz"], r["zo_ol@1MHz"] = (at(f, z, x) for x in (1e3, 1e6))
    # slew: follower, 10 V step, RL 2k, CL 100 pF
    lines = head(part, kind) + supplies(15, -15) + ["VIN in 0 PULSE(-5 5 1u 10n 10n 40u 80u)", oa(part, "S", "in", "out", "vp", "vn", "out"),
                                                   "RL out 0 2k", "CL out 0 100p", ".tran 5n 80u"]
    plots, log = run(f"{part}-slew", lines)
    p = pick(plots, "tran")
    if p is not None:
        t = vec(p, "time")
        v = vec(p, "out")
        def slope(t0, t1, rising):
            seg = [(ti, vi) for ti, vi in zip(t, v) if t0 <= ti <= t1]
            ts, vs = [s[0] for s in seg], [s[1] for s in seg]
            lo, hi = (-4, 4) if rising else (4, -4)
            a, b = x_where(ts, vs, lo), x_where(ts, vs, hi)
            return abs(8 / (b - a)) if a and b and b != a else None
        r["sr+"] = slope(1e-6, 41e-6, True)
        r["sr-"] = slope(41e-6, 80e-6, False)
    # small-signal step: 10 mV, CL 100 pF
    lines = head(part, kind) + supplies(15, -15) + ["VIN in 0 PULSE(0 0.01 100n 1n 1n 20u 40u)", oa(part, "T", "in", "out", "vp", "vn", "out"),
                                                   "RL out 0 2k", "CL out 0 100p", ".tran 1n 20u"]
    plots, log = run(f"{part}-step", lines)
    p = pick(plots, "tran")
    if p is not None:
        t = vec(p, "time")
        v = vec(p, "out")
        a, b = x_where(t, v, 0.001), x_where(t, v, 0.009)
        r["tr(10-90)@100pF"] = (b - a) if a and b else None
        r["overshoot@100pF"] = (max(v) - 0.01) / 0.01 * 100
    # noise: follower, RS = 0, input-referred
    lines = head(part, kind) + supplies(15, -15) + ["VIN in 0 DC 0 AC 1", oa(part, "N", "in", "out", "vp", "vn", "out"), "RL out 0 2k",
                                                   ".noise v(out) VIN dec 10 1 1meg"]
    plots, log = run(f"{part}-noise", lines)
    p = pick(plots, "noise")
    if p is not None:
        f = vec(p, "frequency")
        en = vec(p, "inoise_spectrum")
        r["en@10Hz"], r["en@1kHz"], r["en@10kHz"] = (at(f, en, x) for x in (10, 1e3, 1e4))
        if (r["en@1kHz"] or 0) < 1e-10:
            r["noise"] = "absent (no noise sources)"
    # THD: follower, 1 kHz, 3 Vrms into 2 kΩ, harmonics 2..10 over the last 8 cycles
    lines = head(part, kind) + supplies(15, -15) + ["VIN in 0 SIN(0 4.2426 1k)", oa(part, "D", "in", "out", "vp", "vn", "out"), "RL out 0 2k",
                                                   ".tran 0.5u 12m 0 0.5u"]
    plots, log = run(f"{part}-thd", lines)
    p = pick(plots, "tran")
    if p is not None:
        t = vec(p, "time")
        v = vec(p, "out")
        nsamp = 8192
        y = num.resample(t, v, 4e-3, 12e-3, nsamp) if hasattr(num, "resample") else None
        if y:
            mags = [abs(num.goertzel(y, 8 * h)) for h in range(1, 11)]
            r["thd@1kHz,3Vrms,2k"] = math.sqrt(sum(m * m for m in mags[1:])) / mags[0]
            r["h2/h1"], r["h3/h1"] = mags[1] / mags[0], mags[2] / mags[0]
    # THD against level at 1 kHz, G = 1, 2 kΩ
    for vrms in (0.1, 1.0, 6.0, 10.0):
        lines = head(part, kind) + supplies(15, -15) + [f"VIN in 0 SIN(0 {vrms * math.sqrt(2):.4f} 1k)", oa(part, "D", "in", "out", "vp", "vn", "out"), "RL out 0 2k",
                                                       ".tran 0.5u 12m 0 0.5u"]
        plots, log = run(f"{part}-thd-{vrms}", lines)
        p = pick(plots, "tran")
        if p is not None:
            y = num.resample(vec(p, "time"), vec(p, "out"), 4e-3, 12e-3, 8192)
            mags = [abs(num.goertzel(y, 8 * h)) for h in range(1, 11)]
            r[f"thd@1kHz,{vrms:g}Vrms"] = math.sqrt(sum(m * m for m in mags[1:])) / mags[0]
    # max VO against frequency: 10 Vpk at 20, 50, 100 kHz (THD by Goertzel over the last 8 cycles)
    for fk in (20e3, 50e3, 100e3):
        per = 1 / fk
        lines = head(part, kind) + supplies(15, -15) + [f"VIN in 0 SIN(0 10 {fk:g})", oa(part, "F", "in", "out", "vp", "vn", "out"), "RL out 0 2k",
                                                       f".tran {per / 200:.3e} {12 * per:.3e} 0 {per / 200:.3e}"]
        plots, log = run(f"{part}-vof-{int(fk)}", lines)
        p = pick(plots, "tran")
        if p is not None:
            y = num.resample(vec(p, "time"), vec(p, "out"), 4 * per, 12 * per, 8192)
            mags = [abs(num.goertzel(y, 8 * h)) for h in range(1, 11)]
            r[f"thd@10Vpk,{num.si(fk, 'Hz')}"] = math.sqrt(sum(m * m for m in mags[1:])) / mags[0]
            r[f"vopk@{num.si(fk, 'Hz')}"] = mags[0]
    if r.get("sr+") and r.get("vom+@2kΩ"):
        r["fpbw (SR/2πVOM)"] = r["sr+"] / (TWO_PI * r["vom+@2kΩ"])
    # settling to 0.1 % and 0.01 % of a 2 V and a 10 V step, G = 1, 100 pF
    for vstep in (2.0, 10.0):
        lines = head(part, kind) + supplies(15, -15) + [f"VIN in 0 PULSE({-vstep / 2} {vstep / 2} 1u 10n 10n 40u 80u)", oa(part, "S", "in", "out", "vp", "vn", "out"),
                                                       "RL out 0 2k", "CL out 0 100p", ".tran 2n 41u"]
        plots, log = run(f"{part}-settle-{int(vstep)}", lines)
        p = pick(plots, "tran")
        if p is not None:
            tt, v = vec(p, "time"), vec(p, "out")
            final = v[-1]
            for pct in (1e-3, 1e-4):
                band = pct * vstep
                outside = [a for a, b in zip(tt, v) if a >= 1e-6 and abs(b - final) > band]
                r[f"ts@{pct * 100:g}%,{vstep:g}V"] = (outside[-1] - 1e-6) if outside else 0.0
    # overload recovery: inverter G = −10, input 1.2·VS/10 beyond, time back to within 1 % of the linear output
    lines = head(part, kind) + supplies(15, -15) + ["VIN in 0 PULSE(0 1.8 1u 10n 10n 20u 40u)", "R1 in inn 1k", "R2 inn out 10k",
                                                   oa(part, "O", "0", "inn", "vp", "vn", "out"), "RL out 0 2k", ".tran 2n 40u"]
    plots, log = run(f"{part}-overload", lines)
    p = pick(plots, "tran")
    if p is not None:
        tt, v = vec(p, "time"), vec(p, "out")
        back = [a for a, b in zip(tt, v) if a >= 21.01e-6 and abs(b) > 0.1]
        r["trec(−)"] = (back[-1] - 21.01e-6) if back else 0.0
        r["vout(overloaded)"] = min(v)
    # closed-loop bandwidth at G = 10, 100, 1000 and −1
    for g, net in {10: ["R1 inn 0 1k", "R2 out inn 9k"], 100: ["R1 inn 0 1k", "R2 out inn 99k"], 1000: ["R1 inn 0 100", "R2 out inn 99.9k"]}.items():
        lines = head(part, kind) + supplies(15, -15) + ["VIN in 0 DC 0 AC 1"] + net + [oa(part, "G", "in", "inn", "vp", "vn", "out"), "RL out 0 2k", "CL out 0 100p", ".ac dec 20 10 100meg"]
        plots, log = run(f"{part}-cl-{g}", lines)
        p = pick(plots, "ac")
        if p is not None:
            f = [abs(x) for x in vec(p, "frequency")]
            m = [mag(x) for x in vec(p, "out")]
            r[f"bw@G={g}"] = x_where(f, m, m[0] / math.sqrt(2))
            r[f"peak@G={g}"] = 20 * math.log10(max(m) / m[0])
    lines = head(part, kind) + supplies(15, -15) + ["VIN in 0 DC 0 AC 1", "R1 in inn 10k", "R2 out inn 10k", oa(part, "G", "0", "inn", "vp", "vn", "out"), "RL out 0 2k", "CL out 0 100p", ".ac dec 20 10 100meg"]
    plots, log = run(f"{part}-cl-inv", lines)
    p = pick(plots, "ac")
    if p is not None:
        f = [abs(x) for x in vec(p, "frequency")]
        m = [mag(x) for x in vec(p, "out")]
        r["bw@G=-1"] = x_where(f, m, m[0] / math.sqrt(2))
    # phase margin against capacitive load (open-loop deck) and overshoot of a 100 mV step
    for cl in ("10p", "100p", "1n", "10n"):
        lines = head(part, kind) + supplies(15, -15) + ["VIN inp 0 DC 0 AC 1", "L1 out inn 1G", "C1 inn 0 1G", oa(part, "A", "inp", "inn", "vp", "vn", "out"),
                                                       "RL out 0 2k", f"CL out 0 {cl}", ".ac dec 20 1 100meg"]
        plots, log = run(f"{part}-pm-{cl}", lines)
        p = pick(plots, "ac")
        if p is not None:
            f = [abs(x) for x in vec(p, "frequency")]
            a_ = vec(p, "out")
            g_ = [mag(x) for x in a_]
            fu = x_where(f, g_, 1.0, log_y=True)
            r[f"pm@{cl}F"] = (180 + at(f, [phase_deg(x) for x in a_], fu)) if fu else None
    for cl in ("100p", "1n"):
        lines = head(part, kind) + supplies(15, -15) + ["VIN in 0 PULSE(0 0.1 100n 1n 1n 20u 40u)", oa(part, "T", "in", "out", "vp", "vn", "out"),
                                                       "RL out 0 2k", f"CL out 0 {cl}", ".tran 1n 20u"]
        plots, log = run(f"{part}-ovs-{cl}", lines)
        p = pick(plots, "tran")
        if p is not None:
            r[f"overshoot(100mV)@{cl}F"] = (max(vec(p, "out")) - 0.1) / 0.1 * 100
    # AOL against output swing: open loop, the input swept finely around VOS
    vos = r.get("vos@±15V", 0.0)
    lines = head(part, kind) + supplies(15, -15) + ["VIN inp 0 0", oa(part, "L", "inp", "0", "vp", "vn", "out"), "RL out 0 2k",
                                                   f".dc VIN {vos - 300e-6:.6e} {vos + 300e-6:.6e} 0.25e-6"]
    plots, log = run(f"{part}-aol-swing", lines)
    p = pick(plots, "dc")
    if p is not None:
        vin = vec(p, "v-sweep")
        vout = vec(p, "out")
        def aol_between(lo, hi):
            a_, b_ = x_where(vin, vout, lo), x_where(vin, vout, hi)
            return (hi - lo) / (b_ - a_) if a_ and b_ and b_ != a_ else None
        r["aol@±10V,2k"] = aol_between(-10, 10)
        r["aol@±13V,2k"] = aol_between(-13, 13)
        r["vout range (open loop)"] = (min(vout), max(vout))
    # noise against source resistance: total input-referred at 1 kHz with RS in the follower's input
    tot = {}
    for rs in (1e3, 1e4, 1e5, 1e6):
        lines = head(part, kind) + supplies(15, -15) + ["VIN in 0 DC 0 AC 1", f"RS in inr {rs:g}", oa(part, "N", "inr", "out", "vp", "vn", "out"), "RL out 0 2k",
                                                       ".noise v(out) VIN dec 2 1k 1k"]
        plots, log = run(f"{part}-noise-rs-{int(rs)}", lines)
        p = pick(plots, "noise")
        if p is not None:
            tot[rs] = vec(p, "onoise_spectrum")[0]
            r[f"vt@1kHz,rs={num.si(rs, 'Ω')}"] = tot[rs]
    if 1e5 in tot and r.get("en@1kHz") is not None:
        kt4r = 4 * 1.380649e-23 * 300 * 1e5
        rest = tot[1e5] ** 2 - r["en@1kHz"] ** 2 - kt4r
        r["in@1kHz (from RS=100k)"] = math.sqrt(rest) / 1e5 if rest > 0 else "absent (no current noise)"
    # EMIRR: 100 mVpk at 100 MHz on the follower's input, the DC shift of the output
    lines = head(part, kind) + supplies(15, -15) + ["VIN in 0 SIN(0 0.1 100meg)", oa(part, "E", "in", "out", "vp", "vn", "out"), "RL out 0 2k", ".tran 0.05n 2u"]
    plots, log = run(f"{part}-emirr", lines)
    p = pick(plots, "tran")
    if p is not None:
        tt, v = vec(p, "time"), vec(p, "out")
        y = num.resample(tt, v, 1e-6, 2e-6, 4000)
        shift = sum(y) / len(y) - vos
        r["emirr@100MHz"] = (20 * math.log10(0.1 / abs(shift))) if abs(shift) > 2e-5 else "absent (no RF rectification in the model)"
        r["vos shift@100MHz"] = shift
    r["channel separation"] = "absent (the subcircuit is one amplifier)"
    # ---- the variants every sheet draws
    # turn-on: both rails ramped at 0.3 V/µs to ±15 V, the follower's output settling within 10 mV
    lines = head(part, kind) + ["VP vp 0 PWL(0 3 40u 15 1 15)", "VN vn 0 PWL(0 -3 40u -15 1 -15)", "VIN in 0 0", oa(part, "U", "in", "out", "vp", "vn", "out"),
                                "RL out 0 2k", ".tran 50n 200u"]
    plots, log = run(f"{part}-turnon", lines)
    p = pick(plots, "tran")
    if p is not None:
        tt, v = vec(p, "time"), vec(p, "out")
        late = [a for a, b in zip(tt, v) if abs(b - vos) > 0.01]
        r["turn-on (settled 10 mV after a ±3→±15 V ramp at 0.3 V/µs)"] = late[-1] if late else 0.0
    # VOS, IB and IQ against temperature; AOL and swing too
    for t_ in (-55, 125):
        lines = head(part, kind) + [f".temp {t_}"] + supplies(15, -15) + ["VIP in inp 0", "VI in 0 0", "VNN out inn 0", oa(part, "B", "inp", "inn", "vp", "vn", "out"), "RL out 0 2k", ".op"]
        plots, log = run(f"{part}-bias-{t_}", lines)
        p = pick(plots, "op")
        if p is not None:
            r[f"vos@{t_}C"], r[f"ib+@{t_}C"], r[f"iq@{t_}C"] = vec(p, "out")[0], cur(p, "vip")[0], -cur(p, "vp")[0]
    if r.get("vos@125C") is not None and r.get("vos@-55C") is not None:
        r["dvos/dt (−55..125)"] = (r["vos@125C"] - r["vos@-55C"]) / 180
        r["offset drift"] = r["dvos/dt (−55..125)"] if abs(r["dvos/dt (−55..125)"]) > 1e-9 else "absent (VOS does not move with temperature)"
    # IB against common mode
    for vcm in (-13, 13):
        lines = head(part, kind) + supplies(15, -15) + ["VIP in inp 0", f"VI in 0 {vcm}", "VNN out inn 0", oa(part, "B", "inp", "inn", "vp", "vn", "out"), "RL out 0 2k", ".op"]
        plots, log = run(f"{part}-bias-vcm{vcm}", lines)
        p = pick(plots, "op")
        if p is not None:
            r[f"ib+@vcm={vcm}V"] = cur(p, "vip")[0]
    # input impedance: common-mode (both inputs driven) and differential (one input, the other grounded), at 1 kHz and 1 MHz
    lines = head(part, kind) + supplies(15, -15) + ["VCM cm 0 DC 0 AC 1", "VA cm inp 0", "VB cm inn 0", oa(part, "I", "inp", "inn", "vp", "vn", "out"), "RL out 0 2k", ".ac dec 10 1k 1meg"]
    plots, log = run(f"{part}-zicm", lines)
    p = pick(plots, "ac")
    if p is not None:
        f = [abs(x) for x in vec(p, "frequency")]
        i_ = [mag(a + b) for a, b in zip(cur(p, "va"), cur(p, "vb"))]
        r["zicm@1kHz"], r["zicm@1MHz"] = (1 / at(f, i_, x) if at(f, i_, x) else None for x in (1e3, 1e6))
        r["cicm (from 1 MHz)"] = at(f, i_, 1e6) / (TWO_PI * 1e6) if at(f, i_, 1e6) else None
    lines = head(part, kind) + supplies(15, -15) + ["VD inp 0 DC 0 AC 1", "L1 out inn 1G", "C1 inn 0 1G", oa(part, "I", "inp", "inn", "vp", "vn", "out"), "RL out 0 2k", ".ac dec 10 1k 1meg"]
    plots, log = run(f"{part}-zid", lines)
    p = pick(plots, "ac")
    if p is not None:
        f = [abs(x) for x in vec(p, "frequency")]
        i_ = [mag(x) for x in cur(p, "vd")]
        r["zid@1kHz"], r["zid@1MHz"] = (1 / at(f, i_, x) if at(f, i_, x) else None for x in (1e3, 1e6))
    # CMRR at the edges of the common-mode range (1 kHz)
    for vcm in (-13, 13):
        lines = head(part, kind) + supplies(15, -15) + [f"VCM vcm 0 DC {vcm} AC 1", "R1 vcm inn 10k", "R2 inn out 10k", "R3 vcm inp 10k", "R4 inp 0 10k",
                                                       oa(part, "C", "inp", "inn", "vp", "vn", "out"), "RL out 0 2k", ".ac dec 10 1k 1k"]
        plots, log = run(f"{part}-cmrr-vcm{vcm}", lines)
        p = pick(plots, "ac")
        if p is not None:
            g = mag(vec(p, "out")[0])
            r[f"cmrr@1kHz,vcm={vcm}V"] = -20 * math.log10(g) if g else None
    # PSRR with both rails modulated together (onsemi's way)
    lines = head(part, kind) + ["VP vp 0 DC 15 AC 1", "VN vn 0 DC -15 AC -1", "VIN in 0 0", oa(part, "P", "in", "out", "vp", "vn", "out"), "RL out 0 2k", ".ac dec 20 1 10meg"]
    plots, log = run(f"{part}-psrr-both", lines)
    p = pick(plots, "ac")
    if p is not None:
        f = [abs(x) for x in vec(p, "frequency")]
        g = [mag(x) for x in vec(p, "out")]
        r["psrr(both)@100Hz"], r["psrr(both)@10kHz"] = (-20 * math.log10(at(f, g, x)) if at(f, g, x) else None for x in (100, 1e4))
    # EMIRR at more carriers
    for fc, step, span in ((10e6, 0.5e-9, 4e-6), (400e6, 0.02e-9, 400e-9), (1e9, 0.01e-9, 200e-9)):
        lines = head(part, kind) + supplies(15, -15) + [f"VIN in 0 SIN(0 0.1 {fc:g})", oa(part, "E", "in", "out", "vp", "vn", "out"), "RL out 0 2k", f".tran {step:g} {span:g}"]
        plots, log = run(f"{part}-emirr-{int(fc / 1e6)}", lines)
        p = pick(plots, "tran")
        if p is not None:
            tt, v = vec(p, "time"), vec(p, "out")
            y = num.resample(tt, v, span / 2, span, 4000)
            shift = sum(y) / len(y) - vos
            r[f"emirr@{num.si(fc, 'Hz')}"] = (20 * math.log10(0.1 / abs(shift))) if abs(shift) > 2e-5 else "absent"
    # open-loop gain at other loads, supplies and temperatures
    for tag, extra, rl, sup, temp in (("600Ω", [], "600", (15, -15), 25), ("10kΩ", [], "10k", (15, -15), 25), ("±5V", [], "2k", (5, -5), 25),
                                      ("±9V", [], "2k", (9, -9), 25), ("-55C", [".temp -55"], "2k", (15, -15), -55), ("125C", [".temp 125"], "2k", (15, -15), 125)):
        lines = head(part, kind) + extra + supplies(*sup) + ["VIN inp 0 DC 0 AC 1", "L1 out inn 1G", "C1 inn 0 1G", oa(part, "A", "inp", "inn", "vp", "vn", "out"),
                                                            f"RL out 0 {rl}", "CL out 0 100p", ".ac dec 20 1 100meg"]
        plots, log = run(f"{part}-aol-{tag}", lines)
        p = pick(plots, "ac")
        if p is not None:
            f = [abs(x) for x in vec(p, "frequency")]
            a_ = vec(p, "out")
            g = [mag(x) for x in a_]
            fu = x_where(f, g, 1.0, log_y=True)
            r[f"aol_dc@{tag}"] = 20 * math.log10(g[0])
            r[f"gbw@100kHz,{tag}"] = (at(f, g, 1e5) or 0) * 1e5
            r[f"pm@{tag}"] = (180 + at(f, [phase_deg(x) for x in a_], fu)) if fu else None
    # swing and short circuit against supply and temperature
    for tag, extra, sup in (("±5V", [], (5, -5)), ("±9V", [], (9, -9)), ("-55C", [".temp -55"], (15, -15)), ("125C", [".temp 125"], (15, -15))):
        lines = head(part, kind) + extra + supplies(*sup) + ["VIp ip 0 1", oa(part, "Sp", "ip", "0", "vp", "vn", "op"), "RLp op 0 2k",
                                                            "VIn inn 0 -1", oa(part, "Sn", "inn", "0", "vp", "vn", "on"), "RLn on 0 2k",
                                                            "VIsp isp 0 1", oa(part, "Ip", "isp", "0", "vp", "vn", "osp"), "VSCp osp 0 0", ".op"]
        plots, log = run(f"{part}-swing-{tag}", lines)
        p = pick(plots, "op")
        if p is not None:
            r[f"vom+@2kΩ,{tag}"], r[f"vom-@2kΩ,{tag}"], r[f"isc+@{tag}"] = vec(p, "op")[0], vec(p, "on")[0], cur(p, "vscp")[0]
    # output voltage against output current (sourcing), from the saturated amplifier into a swept load current
    lines = head(part, kind) + supplies(15, -15) + ["VIp ip 0 1", oa(part, "Sp", "ip", "0", "vp", "vn", "op"), "IL op 0 0", ".dc IL 0 0.08 0.0005"]
    plots, log = run(f"{part}-vo-io", lines)
    p = pick(plots, "dc")
    if p is not None:
        il = vec(p, "v-sweep") if "v(v-sweep)" in p["data"] else vec(p, "i-sweep")
        vo = vec(p, "op")
        r["vo_vs_io (sourcing)"] = [(i_, at(il, vo, i_)) for i_ in (0.001, 0.005, 0.01, 0.02, 0.04, 0.08)]
    # closed-loop output impedance at G = 10, 100, 1000
    for g, net in {10: ["R1 inn 0 1k", "R2 out inn 9k"], 100: ["R1 inn 0 1k", "R2 out inn 99k"], 1000: ["R1 inn 0 100", "R2 out inn 99.9k"]}.items():
        lines = head(part, kind) + supplies(15, -15) + ["VIN in 0 0"] + net + [oa(part, "Z", "in", "inn", "vp", "vn", "out"), "IINJ 0 out AC 1", ".ac dec 10 10 10meg"]
        plots, log = run(f"{part}-zo-g{g}", lines)
        p = pick(plots, "ac")
        if p is not None:
            f = [abs(x) for x in vec(p, "frequency")]
            z = [mag(x) for x in vec(p, "out")]
            r[f"zo@1kHz,G={g}"], r[f"zo@100kHz,G={g}"] = at(f, z, 1e3), at(f, z, 1e5)
    # stability against the differential source resistance at G = +100 (onsemi): peaking and bandwidth per RT
    for rt in (100, 1000, 10000, 100000):
        r1 = rt / 100
        lines = head(part, kind) + supplies(15, -15) + ["VIN in 0 DC 0 AC 1", f"R1 inn 0 {r1:g}", f"R2 out inn {rt - r1:g}", oa(part, "G", "in", "inn", "vp", "vn", "out"),
                                                       "RL out 0 2k", "CL out 0 100p", ".ac dec 20 10 100meg"]
        plots, log = run(f"{part}-rt-{rt}", lines)
        p = pick(plots, "ac")
        if p is not None:
            f = [abs(x) for x in vec(p, "frequency")]
            m = [mag(x) for x in vec(p, "out")]
            r[f"peak@G=100,rt={num.si(rt, 'Ω')}"] = 20 * math.log10(max(m) / m[0])
    # slew: G = −1, CL = 20 pF, 2 V and 20 V steps, ±5 V, 125 °C
    def slew_deck(tag, src, net, follower, cl, sup, extra):
        lines = head(part, kind) + extra + supplies(*sup) + [src] + net + [oa(part, "S", *follower), "RL out 0 2k", f"CL out 0 {cl}", ".tran 5n 80u"]
        plots, log = run(f"{part}-slew-{tag}", lines)
        p = pick(plots, "tran")
        if p is None:
            return
        tt, v = vec(p, "time"), vec(p, "out")
        lo, hi = min(v), max(v)
        seg = [(a, b) for a, b in zip(tt, v) if 1e-6 <= a <= 41e-6]
        ta, tb = [a for a, _ in seg], [b for _, b in seg]
        a_, b_ = x_where(ta, tb, lo + 0.1 * (hi - lo)), x_where(ta, tb, lo + 0.9 * (hi - lo))
        r[f"sr@{tag}"] = abs(0.8 * (hi - lo) / (b_ - a_)) if a_ and b_ and b_ != a_ else None
    slew_deck("G=-1,100pF", "VIN in 0 PULSE(5 -5 1u 10n 10n 40u 80u)", ["R1 in inn 10k", "R2 out inn 10k"], ("0", "inn", "vp", "vn", "out"), "100p", (15, -15), [])
    slew_deck("G=1,20pF", "VIN in 0 PULSE(-5 5 1u 10n 10n 40u 80u)", [], ("in", "out", "vp", "vn", "out"), "20p", (15, -15), [])
    slew_deck("2V,G=1", "VIN in 0 PULSE(-1 1 1u 10n 10n 40u 80u)", [], ("in", "out", "vp", "vn", "out"), "100p", (15, -15), [])
    slew_deck("20V,G=1", "VIN in 0 PULSE(-10 10 1u 10n 10n 40u 80u)", [], ("in", "out", "vp", "vn", "out"), "100p", (15, -15), [])
    slew_deck("±5V,G=1", "VIN in 0 PULSE(-2 2 1u 10n 10n 40u 80u)", [], ("in", "out", "vp", "vn", "out"), "100p", (5, -5), [])
    slew_deck("125C,G=1", "VIN in 0 PULSE(-5 5 1u 10n 10n 40u 80u)", [], ("in", "out", "vp", "vn", "out"), "100p", (15, -15), [".temp 125"])
    # settling at G = −1, 10 V
    lines = head(part, kind) + supplies(15, -15) + ["VIN in 0 PULSE(5 -5 1u 10n 10n 40u 80u)", "R1 in inn 10k", "R2 out inn 10k", oa(part, "S", "0", "inn", "vp", "vn", "out"),
                                                   "RL out 0 2k", "CL out 0 100p", ".tran 2n 41u"]
    plots, log = run(f"{part}-settle-inv", lines)
    p = pick(plots, "tran")
    if p is not None:
        tt, v = vec(p, "time"), vec(p, "out")
        final = v[-1]
        for pct in (1e-3, 1e-4):
            outside = [a for a, b in zip(tt, v) if a >= 1e-6 and abs(b - final) > pct * 10]
            r[f"ts@{pct * 100:g}%,10V,G=-1"] = (outside[-1] - 1e-6) if outside else 0.0
    # positive overload recovery
    lines = head(part, kind) + supplies(15, -15) + ["VIN in 0 PULSE(0 -1.8 1u 10n 10n 20u 40u)", "R1 in inn 1k", "R2 inn out 10k",
                                                   oa(part, "O", "0", "inn", "vp", "vn", "out"), "RL out 0 2k", ".tran 2n 40u"]
    plots, log = run(f"{part}-overload-p", lines)
    p = pick(plots, "tran")
    if p is not None:
        tt, v = vec(p, "time"), vec(p, "out")
        back = [a for a, b in zip(tt, v) if a >= 21.01e-6 and abs(b) > 0.1]
        r["trec(+)"] = (back[-1] - 21.01e-6) if back else 0.0
    # the input's current when driven beyond the rails
    lines = head(part, kind) + supplies(15, -15) + ["VIN in 0 0", "VIM in inp 0", oa(part, "V", "inp", "out", "vp", "vn", "out"), "RL out 0 10k", ".dc VIN -17 17 0.1"]
    plots, log = run(f"{part}-iin", lines)
    p = pick(plots, "dc")
    if p is not None:
        vin = vec(p, "v-sweep")
        iin = cur(p, "vim")
        r["iin@+16V"], r["iin@-16V"], r["iin@+14V"] = at(vin, iin, 16.0), at(vin, iin, -16.0), at(vin, iin, 14.0)
    # noise: the 0.1–10 Hz band by integration, 20 Hz–20 kHz rms, en at ±5 V; weighted figures at RS = 300 Ω and 2.2 kΩ
    lines = head(part, kind) + supplies(15, -15) + ["VIN in 0 DC 0 AC 1", oa(part, "N", "in", "out", "vp", "vn", "out"), "RL out 0 2k", ".noise v(out) VIN dec 20 0.1 1meg"]
    plots, log = run(f"{part}-noise-wide", lines)
    p = pick(plots, "noise")
    if p is not None:
        f, en = vec(p, "frequency"), vec(p, "inoise_spectrum")
        rms = integrate_noise(f, en, 0.1, 10)
        r["en rms 0.1-10Hz"], r["en p-p 0.1-10Hz (6.6×rms)"] = rms, 6.6 * rms
        r["en rms 20Hz-20kHz"] = integrate_noise(f, en, 20, 20e3)
        r["en rms 10Hz-10kHz"] = integrate_noise(f, en, 10, 10e3)
    lines = head(part, kind) + supplies(5, -5) + ["VIN in 0 DC 0 AC 1", oa(part, "N", "in", "out", "vp", "vn", "out"), "RL out 0 2k", ".noise v(out) VIN dec 2 1k 1k"]
    plots, log = run(f"{part}-noise-5v", lines)
    p = pick(plots, "noise")
    if p is not None:
        r["en@1kHz,±5V"] = vec(p, "inoise_spectrum")[0]
    for rs in (300, 2200):
        lines = head(part, kind) + supplies(15, -15) + ["VIN in 0 DC 0 AC 1", f"RS in inr {rs}", oa(part, "N", "inr", "out", "vp", "vn", "out"), "RL out 0 2k", ".noise v(out) VIN dec 20 10 100k"]
        plots, log = run(f"{part}-noise-w{rs}", lines)
        p = pick(plots, "noise")
        if p is not None:
            f, en = vec(p, "frequency"), vec(p, "inoise_spectrum")
            r[f"en rms flat 20Hz-20kHz, rs={rs}Ω"] = integrate_noise(f, en, 20, 20e3)
            r[f"en rms A-weighted, rs={rs}Ω"] = integrate_noise(f, en, 20, 20e3, a_weight)
            r[f"en rms RIAA-weighted (30 kHz), rs={rs}Ω"] = integrate_noise(f, en, 20, 30e3, riaa_weight)
    # THD against frequency at 1 and 3 Vrms, G = +1 and +10 (9k/1k), 2 kΩ; and against load at 3 Vrms, 1 kHz
    for gtag, net, follower in (("G=1", [], ("in", "out", "vp", "vn", "out")), ("G=10", ["R1 inn 0 1k", "R2 out inn 9k"], ("in", "inn", "vp", "vn", "out"))):
        for vrms in (1.0, 3.0):
            for fk in (20, 100, 1e3, 10e3, 20e3):
                card, t0, t1, cyc = sine_tran(fk, 12)
                amp = vrms * math.sqrt(2) / (10 if gtag == "G=10" else 1)
                lines = head(part, kind) + supplies(15, -15) + [f"VIN in 0 SIN(0 {amp:.5f} {fk:g})"] + net + [oa(part, "D", *follower), "RL out 0 2k", card]
                plots, log = run(f"{part}-thdf-{gtag}-{vrms:g}-{int(fk)}", lines)
                p = pick(plots, "tran")
                if p is not None:
                    r[f"thd@{num.si(fk, 'Hz')},{vrms:g}Vrms,{gtag}"] = thd_of(vec(p, "time"), vec(p, "out"), t0, t1, cyc)
    for rl in (100, 300, 600, 10000):
        card, t0, t1, cyc = sine_tran(1e3)
        lines = head(part, kind) + supplies(15, -15) + ["VIN in 0 SIN(0 4.2426 1k)", oa(part, "D", "in", "out", "vp", "vn", "out"), f"RL out 0 {rl}", card]
        plots, log = run(f"{part}-thd-rl{rl}", lines)
        p = pick(plots, "tran")
        if p is not None:
            r[f"thd@1kHz,3Vrms,rl={num.si(rl, 'Ω')}"] = thd_of(vec(p, "time"), vec(p, "out"), t0, t1, cyc)
            r[f"vout@3Vrms in,rl={num.si(rl, 'Ω')}"] = harmonics(vec(p, "time"), vec(p, "out"), t0, t1, cyc)[0]
    # IMD: SMPTE 60 Hz + 7 kHz 4:1 and CCIF 19 + 20 kHz 1:1, 3 Vrms in all, 2 kΩ
    a60 = 3 * math.sqrt(2) * 4 / 5
    a7k = 3 * math.sqrt(2) / 5
    lines = head(part, kind) + supplies(15, -15) + [f"VIN in mid SIN(0 {a60:.4f} 60)", f"VIN2 mid 0 SIN(0 {a7k:.4f} 7k)", oa(part, "D", "in", "out", "vp", "vn", "out"), "RL out 0 2k",
                                                   ".tran 1u 150m 0 1u"]
    plots, log = run(f"{part}-imd-smpte", lines)
    p = pick(plots, "tran")
    if p is not None:
        y = num.resample(vec(p, "time"), vec(p, "out"), 100e-3, 150e-3, 16384)     # 50 ms: 3 cycles of 60 Hz, 350 of 7 kHz
        carrier = abs(num.goertzel(y, 350))
        side = math.sqrt(sum(abs(num.goertzel(y, 350 + k)) ** 2 + abs(num.goertzel(y, 350 - k)) ** 2 for k in (3, 6)))
        r["imd SMPTE (60 Hz + 7 kHz 4:1, 3 Vrms)"] = side / carrier if carrier else None
    a19 = 3 * math.sqrt(2) / 2
    lines = head(part, kind) + supplies(15, -15) + [f"VIN in mid SIN(0 {a19:.4f} 19k)", f"VIN2 mid 0 SIN(0 {a19:.4f} 20k)", oa(part, "D", "in", "out", "vp", "vn", "out"), "RL out 0 2k",
                                                   ".tran 0.1u 14m 0 0.1u"]
    plots, log = run(f"{part}-imd-ccif", lines)
    p = pick(plots, "tran")
    if p is not None:
        y = num.resample(vec(p, "time"), vec(p, "out"), 4e-3, 14e-3, 32768)       # 10 ms: 190 and 200 cycles
        tones = abs(num.goertzel(y, 190)) + abs(num.goertzel(y, 200))
        prods = abs(num.goertzel(y, 10)) + abs(num.goertzel(y, 180)) + abs(num.goertzel(y, 210))
        r["imd CCIF (19 + 20 kHz, 3 Vrms)"] = prods / tones if tones else None
    r["card"] = card_facts(MODELS / PARTS[kind][part][0], PARTS[kind][part][1])
    r["agreement"] = "n/a (ngspice only here)"
    return r


def calibrate_noise():
    """What ngspice's inoise_spectrum means: a 1 kΩ resistor gives 4.07 nV/√Hz at 300 K."""
    lines = ["VIN in 0 DC 0 AC 1", "R1 in out 1k", "R2 out 0 1e12", ".noise v(out) VIN dec 2 1k 1k"]
    plots, log = run("calib-noise", lines)
    p = pick(plots, "noise")
    if p is not None:
        return vec(p, "inoise_spectrum")[0]
    return None


def main():
    prepare_models()
    results = {"ngspice_inoise_1k": calibrate_noise()}
    for kind, parts in PARTS.items():
        for part in parts:
            bench = {"jfet": jfet_bench, "mosfet": mos_bench, "opamp": opamp_bench}[kind]
            try:
                results[f"{kind}/{part}"] = bench(part)
            except Exception as e:      # a deck that could not be read: say so and go on
                results[f"{kind}/{part}"] = {"error": f"{type(e).__name__}: {e}"}
            print(kind, part, "done", flush=True)
    (WORK / "results.json").write_text(json.dumps(results, indent=1, default=str))


if __name__ == "__main__":
    main()
