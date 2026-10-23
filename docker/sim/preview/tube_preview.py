"""A preview of the tube bench on ngspice: the measurements of docs/tube-characterisation.md run on the
models of a few parts, as numbers beside the sheets' own (that page's "What the preview says").
Not the pipeline: the catalogue entries and the decks in docker/sim/bench come after; the decks here are
their draft, written in the syntax the three engines share where the models allow it.

    python3 docker/sim/preview/tube_preview.py <models dir> <survey dir> <work dir> [part ...]

The models dir is the curated tube tree (private_web_spice_models/models/tube: one folder per part, with
`part.json` naming each candidate's file, subcircuit and pins; the text never enters git); the survey dir is
data/datasheets/survey/tube, whose rows and graphs are the sheet layer's conditions. Results go to
<work dir>/results/<part>__<model>.json. ngspice must be on the PATH; standard library only, plus
docker/sim/bench's `num` and `raw`. JOBS sets the number of models run at once (6).
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

TWO_PI = 2 * math.pi

# The pin names the authors use, by role. A name not here (a heater pin, a number with no comment) means
# the model is not run: the bench never guesses a pin.
ROLES = {
    "a": {"A", "P", "PL", "PLATE", "ANODE"},
    "g1": {"G", "G1", "GRID"},
    "g2": {"G2", "S", "SG", "SCREEN"},
    "g3": {"G3", "SUP"},
    "k": {"K", "C", "CATH", "CATHODE"},
    "a1": {"A1", "P1"},
    "a2": {"A2", "P2"},
}

# Dialects in the order they are tried: ngspice as it comes, then its PSpice and LTspice compatibilities.
MODES = ["none", "psa", "lta", "ltpsa"]


# ---------------------------------------------------------------- models
def role_of(pin):
    p = pin.upper()
    for role, names in ROLES.items():
        if p in names:
            return role
    return None


def kind_of(roles):
    rs = set(roles)
    if {"a", "g2", "g1", "k"} <= rs:
        return "pentode"
    if {"a", "g1", "k"} <= rs and len(rs) == 3:
        return "triode"
    if rs in ({"a", "k"}, {"a1", "a2", "k"}):
        return "diode"
    return None


def shim_params(text):
    """Declare on each .SUBCKT line the parameters its callers pass and it does not declare.

    LTspice and PSpice let a caller hand a subcircuit any parameter; ngspice wants every one declared.
    The value given (0) is never used, since every caller passes its own; nothing else changes."""
    lines = text.splitlines()
    joined, owner = [], []
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("+") and joined:
            joined[-1] += " " + ln.lstrip()[1:]
        else:
            joined.append(ln)
            owner.append(i)
    passed = {}
    for ln in joined:
        s = ln.split(";")[0].strip()
        if not s or s[0] not in "xX":
            continue
        toks = s.replace("=", " = ").split()
        names = [toks[j - 1].upper() for j in range(1, len(toks)) if toks[j] == "="]
        first_kv = next((j - 1 for j in range(1, len(toks)) if toks[j] == "="), len(toks))
        sub = toks[first_kv - 1].upper() if first_kv > 1 else None
        if sub and names:
            passed.setdefault(sub, set()).update(n for n in names if n != "PARAMS:")
    out = list(lines)
    for j, ln in enumerate(joined):
        m = re.match(r"^\s*\.subckt\s+(\S+)", ln, re.I)
        if not m or m.group(1).upper() not in passed:
            continue
        if re.search(r"\bparams\s*:", ln, re.I):
            continue
        i = owner[j]
        body = out[i].split(";")[0].rstrip()
        out[i] = body + " params: " + " ".join(f"{p}=0" for p in sorted(passed[m.group(1).upper()]))
    return "\n".join(out) + "\n"


def candidates(models_dir, part):
    pj = Path(models_dir) / part / "part.json"
    if not pj.exists():
        return []
    d = json.loads(pj.read_text())
    out = []
    for c in d["candidates"]:
        pins = c.get("pins") or []
        roles = [role_of(p) for p in pins]
        stem = Path(c["file"]).stem
        out.append({"part": part, "id": f"{part}/{stem}", "file": Path(models_dir) / part / c["file"], "name": c["name"],
                    "source": c["source"], "pins": pins, "roles": roles,
                    "kind": kind_of(roles) if pins and None not in roles else None})
    return out


# ---------------------------------------------------------------- running
RAW_CAP = 200 * 2 ** 20


def _cap_files():
    """No file ngspice writes may pass RAW_CAP: a deck whose solver collapses its step stops there."""
    import resource
    resource.setrlimit(resource.RLIMIT_FSIZE, (RAW_CAP, RAW_CAP))


class Model:
    def __init__(self, cand, work):
        self.c = cand
        self.dir = Path(work) / cand["id"].replace("/", "__")
        self.dir.mkdir(parents=True, exist_ok=True)
        self.lib = self.dir / "model.lib"
        self.lib.write_text(Path(cand["file"]).read_text(errors="replace"))
        self.mode = None
        self.shimmed = False

    def x(self, tag, **nodes):
        """The tube as a subcircuit call; a role the caller leaves out of a pentode (g3) goes to the cathode."""
        pins = []
        for role in self.c["roles"]:
            pins.append(nodes.get(role) or nodes.get("k" if role == "g3" else role) or "0")
        return f"X{tag} {' '.join(pins)} {self.c['name']}"

    def run(self, name, lines, save=None):
        deck = self.dir / f"{name}.cir"
        body = ["* " + name, f'.include "{self.lib.name}"', ".options reltol=1e-4"]
        if save:
            body.append(".save " + " ".join(save))
        deck.write_text("\n".join(body + lines + [".end"]) + "\n")
        rawp = self.dir / f"{name}.raw"
        if rawp.exists():
            rawp.unlink()
        init = self.dir / ".spiceinit"
        init.write_text("" if self.mode in (None, "none") else f"set ngbehavior={self.mode}\n")
        try:
            p = subprocess.run(["ngspice", "-b", "-r", rawp.name, deck.name], cwd=self.dir, capture_output=True,
                               text=True, timeout=900, preexec_fn=_cap_files)
            log = p.stdout + p.stderr
        except subprocess.TimeoutExpired:
            return [], "timeout"
        (self.dir / f"{name}.log").write_text(log[-20000:])
        plots = raw.read(rawp) if rawp.exists() and rawp.stat().st_size > 0 else []
        if rawp.exists():
            rawp.unlink()       # the waveforms are read once; a preview of hundreds of models must not fill the disk
        return plots, log


def vec(plot, name):
    d = plot["data"]
    for k in (name.lower(), f"v({name.lower()})", f"i({name.lower()})"):
        if k in d:
            return list(d[k])
    raise KeyError(f"{name} not in {sorted(d)[:12]}")


def pick(plots, kind):
    keys = {"dc": "dc", "ac": "ac", "tran": "tran", "noise": "noise spectral", "op": "operating"}[kind]
    for p in plots:
        if keys in p["name"].lower():
            return p
    return None


def at(xs, ys, x):
    """ys at x by linear interpolation on xs (either direction); None outside."""
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


def harmonics(tt, v, t0, t1, cycles, hmax=10):
    """Amplitudes of harmonics 1..hmax of a tone with `cycles` periods between t0 and t1, and the mean."""
    y = num.resample(tt, v, t0, t1, 8192)
    return [num.goertzel(y, cycles * h) for h in range(1, hmax + 1)], sum(y) / len(y)


def tag(v):
    return str(v).replace("-", "m").replace(".", "p")


# ---------------------------------------------------------------- does it load (tube-runs)
def op_points(kind):
    """The operating points the load check reads: one each at the low end, the middle and full emission."""
    if kind == "triode":
        return [{"a": 100, "g1": 0}, {"a": 250, "g1": 0}, {"a": 250, "g1": -2}, {"a": 250, "g1": -10}]
    if kind == "pentode":
        return [{"a": 250, "g2": 250, "g1": 0}, {"a": 250, "g2": 250, "g1": -10}, {"a": 100, "g2": 250, "g1": 0}]
    return [{"a": 10}, {"a": 50}]


def op_deck(m):
    lines, save = [], []
    for i, pt in enumerate(op_points(m.c["kind"])):
        nodes = {}
        for role, v in pt.items():
            lines.append(f"V{role.upper()}{i} {role}{i} 0 {v}")
            nodes[role] = f"{role}{i}"
            save.append(f"i(v{role}{i})")
        if m.c["kind"] == "diode" and "a1" in m.c["roles"]:
            nodes = {"a1": f"a{i}", "a2": "0", "k": "0"}
        else:
            nodes["k"] = "0"
        lines.append(m.x(f"T{i}", **nodes))
    return lines + [".op"], save


def runs(m):
    """Find the dialect ngspice reads the model in, declaring undeclared parameters if it has to."""
    tried = []
    for shim in (False, True):
        if shim:
            m.lib.write_text(shim_params(Path(m.c["file"]).read_text(errors="replace")))
            m.shimmed = True
        for mode in MODES:
            m.mode = mode
            lines, save = op_deck(m)
            plots, log = m.run("runs", lines, save)
            p = pick(plots, "op")
            if p is not None and all(math.isfinite(float(v[0])) for v in p["data"].values()):
                r = {"runs": True, "mode": mode, "shim": shim}
                for i, pt in enumerate(op_points(m.c["kind"])):
                    cond = ",".join(f"{k}={v}" for k, v in pt.items())
                    for role in pt:
                        r[f"i_{role}@{cond}"] = -float(p["data"][f"i(v{role}{i})"][0])
                return r
            err = next((ln.strip() for ln in log.splitlines() if re.search(r"error|mismatch|undefined|no such", ln, re.I)), log[-120:])
            tried.append(f"{mode}{'+shim' if shim else ''}: {err}")
    m.mode = None
    return {"runs": False, "why": tried[-4:]}


# ---------------------------------------------------------------- the static surface
def grid_ladder(neg_to=-300):
    """Grid voltages for the copies of the anode sweep: fine near zero, coarser towards cut-off."""
    out, v = [], 0.0
    for step, until in ((0.25, -5), (0.5, -10), (1, -30), (2, -60), (5, -150), (10, -300)):
        while v - step >= max(until, neg_to) - 1e-9:
            v = round(v - step, 3)
            out.append(v)
    return [0.0] + out


def anode_family(m, va_max, vgs, extra=None, step=1.0):
    """Ia (and Ig1, Ig2) against Va for each grid voltage in `vgs`, the other electrodes held as `extra` says."""
    extra = extra or {}
    lines, save = ["VSW sw 0 0"], []
    for i, vg in enumerate(vgs):
        lines += [f"VA{i} sw a{i} 0", f"VG{i} g{i} 0 {vg}"]
        save += [f"i(va{i})", f"i(vg{i})"]
        nodes = {"a": f"a{i}", "g1": f"g{i}", "k": "0"}
        if "g2" in extra:
            g2 = extra["g2"]
            if g2 == "a":          # triode connection: the screen strapped to the anode
                nodes["g2"] = f"a{i}"
            elif isinstance(g2, tuple):   # ultralinear: the screen at a tap x of the way from B+ to the anode
                _, vb, x = g2
                lines += [f"BS{i} s{i} 0 V={vb}+{x}*(V(a{i})-{vb})"]
                nodes["g2"] = f"s{i}"
            else:
                lines.append(f"VS{i} s{i} 0 {g2}")
                nodes["g2"] = f"s{i}"
                save.append(f"i(vs{i})")
        lines.append(m.x(f"T{i}", **nodes))
    lines.append(f".dc VSW 0 {va_max} {step}")
    plots, log = m.run(f"anode-{tag(extra.get('g2', 'x')) if not isinstance(extra.get('g2'), tuple) else 'ul' + tag(extra['g2'][2])}-{len(vgs)}", lines, save)
    p = pick(plots, "dc")
    if p is None:
        return None
    va = vec(p, "v-sweep")
    fam = {}
    for i, vg in enumerate(vgs):
        fam[vg] = {"ia": vec(p, f"va{i}"), "ig1": [-x for x in vec(p, f"vg{i}")]}
        if f"i(vs{i})" in p["data"]:
            fam[vg]["ig2"] = [-x for x in vec(p, f"vs{i}")]
    return va, fam


def transfer(m, vas, vg_from, vg_to, step, g2=None):
    """Ia, Ig1 (and Ig2) against Vg1 for each anode voltage in `vas`."""
    lines, save = ["VG g 0 0"], ["i(vg)"]
    for i, va in enumerate(vas):
        lines.append(f"VA{i} a{i} 0 {va}")
        save += [f"i(va{i})", f"i(vgk{i})"]
        nodes = {"a": f"a{i}", "g1": f"gk{i}", "k": "0"}
        lines.append(f"VGK{i} g gk{i} 0")
        if g2 is not None:
            if g2 == "a":
                nodes["g2"] = f"a{i}"
            else:
                lines.append(f"VS{i} s{i} 0 {g2}")
                nodes["g2"] = f"s{i}"
                save.append(f"i(vs{i})")
        lines.append(m.x(f"T{i}", **nodes))
    lines.append(f".dc VG {vg_from} {vg_to} {step}")
    plots, log = m.run(f"transfer-{tag(g2 if g2 is not None else 'x')}-{tag(vg_from)}", lines, save)
    p = pick(plots, "dc")
    if p is None:
        return None
    vg = vec(p, "v-sweep")
    out = {}
    for i, va in enumerate(vas):
        out[va] = {"ia": [-x for x in vec(p, f"va{i}")], "ig1": vec(p, f"vgk{i}")}
        if f"i(vs{i})" in p["data"]:
            out[va]["ig2"] = [-x for x in vec(p, f"vs{i}")]
    return vg, out


def transfer_reach(m, vas, lo, hi, step, g2=None):
    """The transfer sweep from `lo`, or from the deepest of a few shorter starts the model can be evaluated at:
    an equation that takes the logarithm of a quantity negative past cut-off fails the whole deck. Returns the
    sweep and the start it reached."""
    for start in (lo, -100, -40, -15, -5):
        if start < lo:
            continue
        r = transfer(m, vas, start, hi, step, g2)
        if r:
            return r, start
    return None, None


def small_signal(m, points, g2=None):
    """gm, ra and mu at each (Va, Vg1) point, from two AC copies per point at 1 kHz."""
    lines, save = [], []
    sides = ("g", "a", "s") if g2 is not None and g2 != "a" else ("g", "a")
    for i, (va, vg) in enumerate(points):
        for side in sides:
            n = f"{side}{i}"
            ac_g, ac_a, ac_s = ("AC 1" if side == "g" else ""), ("AC 1" if side == "a" else ""), ("AC 1" if side == "s" else "")
            lines += [f"VA{n} a{n} 0 DC {va} {ac_a}", f"VG{n} g{n} 0 DC {vg} {ac_g}"]
            nodes = {"a": f"a{n}", "g1": f"g{n}", "k": "0"}
            if g2 is not None:
                if g2 == "a":
                    nodes["g2"] = f"a{n}"
                else:
                    lines.append(f"VS{n} s{n} 0 DC {g2} {ac_s}")
                    nodes["g2"] = f"s{n}"
            lines.append(m.x(f"T{n}", **nodes))
            save.append(f"i(va{n})")
    lines.append(".ac lin 1 1k 1k")
    plots, log = m.run(f"params-{tag(g2 if g2 is not None else 'x')}", lines, save)
    p = pick(plots, "ac")
    if p is None:
        return None
    out = []
    for i, _ in enumerate(points):
        gm = abs(complex(p["data"][f"i(vag{i})"][0]))
        ga = abs(complex(p["data"][f"i(vaa{i})"][0]))
        ra = 1 / ga if ga > 0 else None
        row = {"gm": gm, "ra": ra, "mu": gm * ra if ra else None}
        if f"i(vas{i})" in p["data"]:
            gs = abs(complex(p["data"][f"i(vas{i})"][0]))
            row["gm_g2"] = gs
            row["mu_g1g2"] = gm / gs if gs > 0 else None
        out.append(row)
    return out


# ---------------------------------------------------------------- circuits
def thd_row(h, mean=None):
    """THD and the first harmonics, in percent of the fundamental."""
    f = h[0]
    tiny = f < 1e-6
    row = {"v1": f, "thd": None if tiny else 100 * math.sqrt(sum(x * x for x in h[1:])) / f}
    for k in range(2, 6):
        row[f"h{k}"] = None if tiny else 100 * h[k - 1] / f
    if mean is not None:
        row["mean"] = mean
    return row


def rc_stage(m, ebb, rl, rk, rg, ck=None, cc=0.1e-6, rs=0.0, rgl=1e6, cl=0.0, rg2=None, cg2=None, drives=(), f=1000.0,
             cycles=None, name="rc"):
    """A resistance-coupled stage: Ebb through RL to the anode, Rk (bypassed by Ck or not) in the cathode, the
    output through Cc into the next grid's Rg (and CL); for a pentode the screen through Rg2 bypassed by Cg2.

    AC: gain and response from 1 Hz to 10 MHz. Transient: one copy per peak drive in `drives`; harmonics of the
    output, the mean anode current and the peak grid current over the last ten cycles."""
    def copy(i, ac, drive):
        ln = [f"VIN{i} in{i} 0 DC 0 {ac}" if drive is None else f"VIN{i} in{i} 0 DC 0 SIN(0 {drive} {f})",
              f"RS{i} in{i} gs{i} {max(rs, 1e-3)}", f"RGL{i} gs{i} 0 {rgl}", f"VGM{i} gs{i} g{i} 0",
              f"VBB{i} bb{i} 0 {ebb}", f"RL{i} bb{i} am{i} {rl}", f"VAM{i} am{i} a{i} 0",
              f"RK{i} k{i} 0 {rk}"]
        if ck:
            ln.append(f"CK{i} k{i} 0 {ck}")
        ln += [f"CC{i} am{i} o{i} {cc}", f"RG{i} o{i} 0 {rg}"]
        if cl:
            ln.append(f"CL{i} o{i} 0 {cl}")
        nodes = {"a": f"a{i}", "g1": f"g{i}", "k": f"k{i}"}
        if rg2 is not None:
            ln.append(f"RG2{i} bb{i} s{i} {rg2}")
            if cg2:
                ln.append(f"CG2{i} s{i} k{i} {cg2}")
            nodes["g2"] = f"s{i}"
        ln.append(m.x(f"T{i}", **nodes))
        return ln

    out = {}
    lines = copy(0, "AC 1", None) + [".ac dec 20 1 10meg"]
    plots, log = m.run(f"{name}-ac", lines, ["v(o0)", "v(a0)", "v(k0)", "i(vam0)", "i(vgm0)"])
    p = pick(plots, "ac")
    if p is None:
        return None
    fr = [float(x.real) if isinstance(x, complex) else float(x) for x in vec(p, "frequency")]
    gain = [abs(complex(x)) for x in vec(p, "o0")]
    out["f"], out["gain"] = fr, gain
    g1k = at(fr, gain, 1000.0)
    out["gain@1kHz"] = g1k
    out["f_low"] = x_where(fr, gain, g1k / math.sqrt(2))
    hi = [(x, g) for x, g in zip(fr, gain) if x > 1000]
    out["f_high"] = x_where([x for x, _ in hi], [g for _, g in hi], g1k / math.sqrt(2))
    if drives:
        cyc = cycles or 30
        per = 1 / f
        lines = []
        for i, d in enumerate(drives):
            lines += copy(i, "", d)
        lines.append(f".tran {per / 200:.4e} {cyc * per:.4e} 0 {per / 200:.4e}")
        save = [f"v(o{i})" for i in range(len(drives))] + [f"i(vam{i})" for i in range(len(drives))] + \
               [f"i(vgm{i})" for i in range(len(drives))] + [f"v(k{i})" for i in range(len(drives))]
        plots, log = m.run(f"{name}-tran", lines, save)
        p = pick(plots, "tran")
        if p is None:
            out["tran"] = "failed"
            return out
        tt = vec(p, "time")
        t0, t1 = (cyc - 10) * per, cyc * per
        rows = []
        for i, d in enumerate(drives):
            h, _ = harmonics(tt, vec(p, f"o{i}"), t0, t1, 10)
            ia = vec(p, f"vam{i}")
            ig = vec(p, f"vgm{i}")
            seg = [k for k, t in enumerate(tt) if t >= t0]
            row = thd_row(h)
            row.update({"drive_pk": d, "vout_rms": h[0] / math.sqrt(2), "ia_mean": sum(ia[k] for k in seg) / len(seg),
                        "ig_peak": max(ig[k] for k in seg), "vk_mean": sum(vec(p, f"k{i}")[k] for k in seg) / len(seg)})
            rows.append(row)
        out["levels"] = rows
    return out


def bias_point(m, ebb, rl, rk, rg2=None):
    """The quiescent anode current, anode and cathode voltages of a stage, from one operating point."""
    lines = [f"VBB bb 0 {ebb}", f"RL bb am {rl}", "VAM am a 0", f"RK k 0 {rk}", "VG g 0 0"]
    nodes = {"a": "a", "g1": "g", "k": "k"}
    if rg2 is not None:
        lines.append(f"RG2 bb s {rg2}")
        nodes["g2"] = "s"
    lines += [m.x("T", **nodes), ".op"]
    plots, log = m.run(f"bias-{tag(ebb)}-{tag(rl)}-{tag(rk)}", lines)
    p = pick(plots, "op")
    if p is None:
        return None
    d = p["data"]
    return {"ia": float(d["i(vam)"][0]), "va": float(d["v(a)"][0]), "vk": float(d["v(k)"][0]),
            "vs": float(d["v(s)"][0]) if "v(s)" in d else None}


def power_stage(m, va, loads, drives, vg=None, rk=None, ck=100e-6, vg2=None, rg2=None, pp=False, ul=None,
                triode=False, f=1000.0, cycles=60, name="pwr"):
    """Single-ended or push-pull output stage into an ideal transformer, one copy per (load, drive).

    Single-ended: B+ through the primary inductance (100 times the load's reactance at f) to the anode, the
    load coupled by a large capacitor, so the anode current is free to shift with the signal as a
    transformer lets it. Push-pull: an ideal centre-tapped primary, each half at v = Raa/4 · (i1 − i2), the
    screens of an ultralinear stage tapped at `ul` of each half. Fixed bias (vg) or cathode bias (rk, ck)."""
    lines, save, combos = [], [], []
    per = 1 / f
    for li, rload in enumerate(loads):
        for di, drive in enumerate(drives):
            i = f"{li}_{di}"
            combos.append((rload, drive, i))
            lines += [f"VB{i} b{i} 0 {va}"]
            if rk:
                lines += [f"RK{i} k{i} 0 {rk}", f"CK{i} k{i} 0 {ck}"]
                gdc = 0
            else:
                lines.append(f"VKK{i} k{i} 0 0")
                gdc = vg
            # the transient takes its offset from SIN(), not from DC: both carry the bias
            src = f" SIN({gdc} {drive} {f})" if drive else ""
            if not pp:
                lines += [f"VIN{i} g{i} 0 DC {gdc}{src}", f"VGM{i} g{i} gt{i} 0",
                          f"LP{i} b{i} am{i} {100 * rload / (TWO_PI * f):.6g}", f"VAM{i} am{i} a{i} 0",
                          f"CO{i} am{i} o{i} 1", f"RO{i} o{i} 0 {rload}"]
                nodes = {"a": f"a{i}", "g1": f"gt{i}", "k": f"k{i}"}
                if triode:
                    nodes["g2"] = f"a{i}"
                elif vg2 is not None:
                    lines.append(f"VS{i} sv{i} 0 {vg2}")
                    lines.append(f"RS{i} sv{i} s{i} {rg2 or 1e-3}")
                    nodes["g2"] = f"s{i}"
                    save.append(f"i(vs{i})")
                lines.append(m.x(f"T{i}", **nodes))
                save += [f"v(o{i})", f"i(vam{i})", f"i(vgm{i})", f"v(k{i})"]
            else:
                q = rload / 4
                lines += [f"VIN{i} gd{i} 0 " + (f"SIN(0 {drive} {f})" if drive else "0"),
                          f"BP{i} gp{i} 0 V={gdc}+V(gd{i})", f"BN{i} gn{i} 0 V={gdc}-V(gd{i})",
                          f"VGM{i} gp{i} gtp{i} 0", f"VGN{i} gn{i} gtn{i} 0",
                          f"VMP{i} ap{i} tap{i} 0", f"VMN{i} an{i} tan{i} 0"]
                isp = isn = "0"
                if ul is not None:
                    lines += [f"VSP{i} sp{i} tsp{i} 0", f"VSN{i} sn{i} tsn{i} 0"]
                    isp, isn = f"i(VSP{i})", f"i(VSN{i})"
                diff = f"(i(VMP{i})+{ul or 0}*{isp})-(i(VMN{i})+{ul or 0}*{isn})"
                lines += [f"BHP{i} ap{i} b{i} V=-{q}*({diff})", f"BHN{i} an{i} b{i} V={q}*({diff})"]
                if ul is not None:
                    lines += [f"BUP{i} sp{i} b{i} V=-{ul}*{q}*({diff})", f"BUN{i} sn{i} b{i} V={ul}*{q}*({diff})"]
                np_ = {"a": f"tap{i}", "g1": f"gtp{i}", "k": f"k{i}"}
                nn_ = {"a": f"tan{i}", "g1": f"gtn{i}", "k": f"k{i}"}
                if triode:
                    np_["g2"], nn_["g2"] = f"tap{i}", f"tan{i}"
                elif ul is not None:
                    np_["g2"], nn_["g2"] = f"tsp{i}", f"tsn{i}"
                    save += [f"i(vsp{i})", f"i(vsn{i})"]
                elif vg2 is not None:
                    lines += [f"VS{i} sv{i} 0 {vg2}", f"RS{i} sv{i} s{i} {rg2 or 1e-3}"]
                    np_["g2"] = nn_["g2"] = f"s{i}"
                    save.append(f"i(vs{i})")
                lines += [m.x(f"TP{i}", **np_), m.x(f"TN{i}", **nn_)]
                save += [f"v(ap{i})", f"v(b{i})", f"i(vmp{i})", f"i(vmn{i})", f"i(vgm{i})", f"v(k{i})"]
    lines.append(f".tran {per / 100:.4e} {cycles * per:.4e} 0 {per / 100:.4e}")
    plots, log = m.run(name, lines, save)
    p = pick(plots, "tran")
    if p is None:
        return None
    tt = vec(p, "time")
    t0, t1 = (cycles - 10) * per, cycles * per
    seg = [k for k, t in enumerate(tt) if t >= t0]
    rows = []
    for rload, drive, i in combos:
        if not pp:
            vo = vec(p, f"o{i}")
            h, _ = harmonics(tt, vo, t0, t1, 10)
            pout = (h[0] / math.sqrt(2)) ** 2 / rload
            ia = vec(p, f"vam{i}")
            row = thd_row(h)
            row.update({"load": rload, "drive_pk": drive, "pout": pout, "ia_mean": sum(ia[k] for k in seg) / len(seg)})
            if f"i(vs{i})" in p["data"]:
                is2 = [-x for x in vec(p, f"vs{i}")]
                row["ig2_mean"] = sum(is2[k] for k in seg) / len(seg)
        else:
            v = [a - b for a, b in zip(vec(p, f"ap{i}"), vec(p, f"b{i}"))]
            h, _ = harmonics(tt, v, t0, t1, 10)
            pout = (h[0] / math.sqrt(2)) ** 2 / (rload / 4)
            ip, ineg = vec(p, f"vmp{i}"), vec(p, f"vmn{i}")
            row = thd_row(h)
            row.update({"load": rload, "drive_pk": drive, "pout": pout,
                        "ia_mean": sum(ip[k] + ineg[k] for k in seg) / len(seg)})
            if f"i(vs{i})" in p["data"]:
                is2 = [-x for x in vec(p, f"vs{i}")]
                row["ig2_mean"] = sum(is2[k] for k in seg) / len(seg)
        ig = vec(p, f"vgm{i}")
        row["ig1_peak"] = max(ig[k] for k in seg)
        row["vk_mean"] = sum(vec(p, f"k{i}")[k] for k in seg) / len(seg)
        rows.append(row)
    return rows


def rectifier(m, vac_list, loads, filt="C", c1=40e-6, l1=10.0, rl_choke=0.0, c2=40e-6, rs=0.0, f=60.0, cycles=40,
              name="rect"):
    """Full-wave rectifier, one copy per (AC volts per plate, DC load current): two windings of `vac` rms per
    plate, each with `rs` of supply impedance, into a capacitor-input (C) or choke-input (L) filter, the load a
    constant current. A single-plate model rectifies half-wave."""
    lines, save, combos, loads_r = [], [], [], {}
    per = 1 / f
    twin = "a1" in m.c["roles"]
    for vi, vac in enumerate(vac_list):
        for li, idc in enumerate(loads):
            i = f"{vi}_{li}"
            combos.append((vac, idc, i))
            pk = vac * math.sqrt(2)
            lines += [f"VP{i} p{i} 0 SIN(0 {pk:.6g} {f})", f"RSP{i} p{i} pa{i} {max(rs, 1e-3)}", f"VMA{i} pa{i} ta{i} 0"]
            if twin:
                lines += [f"VN{i} n{i} 0 SIN(0 {-pk:.6g} {f})", f"RSN{i} n{i} na{i} {max(rs, 1e-3)}", f"VMB{i} na{i} tb{i} 0",
                          m.x(f"T{i}", a1=f"ta{i}", a2=f"tb{i}", k=f"c{i}")]
            else:
                lines.append(m.x(f"T{i}", a=f"ta{i}", k=f"c{i}"))
            # the load is a resistor sized for the target current at the output's expected level, as a bench
            # loads a rectifier; the current published is the one that flowed
            rload = (0.9 * pk if filt == "C" else 0.9 * vac) / idc
            loads_r[i] = rload
            if filt == "C":
                lines += [f"C1{i} c{i} 0 {c1}", f"RLD{i} c{i} 0 {rload:.6g}"]
                outn = f"c{i}"
            else:
                lines += [f"L1{i} c{i} lm{i} {l1}", f"RLC{i} lm{i} o{i} {max(rl_choke, 1e-3)}", f"C2{i} o{i} 0 {c2}",
                          f"RLD{i} o{i} 0 {rload:.6g}"]
                outn = f"o{i}"
            save += [f"v({outn})", f"i(vma{i})"]
    # Gear integration: the trapezoidal rule rings on a choke input switching at every half-cycle and stalls
    lines += [".options method=gear", f".tran {per / 400:.4e} {cycles * per:.4e} 0 {per / 400:.4e} uic"]
    plots, log = m.run(f"{name}-{filt}", lines, save)
    p = pick(plots, "tran")
    if p is None:
        return None
    tt = vec(p, "time")
    if not tt or tt[-1] < cycles * per * 0.999:
        return None           # the solver stopped short: the deck is `failed', not a curve
    t0 = (cycles - 5) * per
    seg = [k for k, t in enumerate(tt) if t >= t0]
    first = [k for k, t in enumerate(tt) if t <= 2 * per]
    rows = []
    for vac, idc, i in combos:
        outn = f"c{i}" if filt == "C" else f"o{i}"
        vo = vec(p, outn)
        ia = vec(p, f"vma{i}")
        vs = [vo[k] for k in seg]
        vdc = sum(vs) / len(vs)
        rows.append({"vac": vac, "idc": vdc / loads_r[i], "idc_target": idc, "vdc": vdc, "ripple_pp": max(vs) - min(vs),
                     "ia_peak": max(ia[k] for k in seg), "surge_peak": max(ia[k] for k in first)})
    return rows


def stage_noise(m, ebb, rl, rk, rs=1e3, rg2=None, cg2=10e-6):
    """Input-referred noise of a grounded-cathode stage (cathode bypassed), and the share of the output noise
    that comes from inside the model: zero when its anode current is a noiseless behavioural source."""
    lines = ["VIN in 0 DC 0 AC 1", f"RSN in g {rs}", f"VBB bb 0 {ebb}", f"RL bb a {rl}", f"RK k 0 {rk}", "CK k 0 1"]
    nodes = {"a": "a", "g1": "g", "k": "k"}
    if rg2 is not None:
        lines += [f"RG2 bb s {rg2}", f"CG2 s k {cg2}"]
        nodes["g2"] = "s"
    lines += [m.x("N", **nodes), ".noise v(a) VIN dec 10 1 100k 1"]
    plots, log = m.run(f"noise-{tag(ebb)}-{tag(rl)}", lines)
    p = pick(plots, "noise")
    if p is None:
        return None
    f = [float(x) for x in vec(p, "frequency")]
    en = [float(x) for x in vec(p, "inoise_spectrum")]
    out = {"en@10Hz": at(f, en, 10.0), "en@1kHz": at(f, en, 1e3), "en@10kHz": at(f, en, 1e4)}
    k = min(range(len(f)), key=lambda j: abs(f[j] - 1e3))
    tot = float(p["data"]["v(onoise_spectrum)"][k]) ** 2
    inside = sum(float(v[k]) ** 2 for name, v in p["data"].items()
                 if name.startswith("v(onoise_") and ".xn." in name and not name.endswith(("_thermal)", "_1overf)", "_rs)", "_id)")))
    out["inside_share@1kHz"] = inside / tot if tot else None
    out["rs"] = rs
    out["req@1kHz"] = max(0.0, (out["en@1kHz"] ** 2 / (4 * num.K_B * num.T_K)) - rs) if out["en@1kHz"] else None
    return out


def capacitances(m, op, f=1e6):
    """Direct interelectrode capacitances at f, the tube biased at `op` (a dict of electrode voltages): each
    electrode driven in turn, the currents into the others (all held at AC ground) read through their sources."""
    roles = [r for r in ("a", "g1", "g2", "k") if r in m.c["roles"]]
    lines, save = [], []
    for drv in roles:
        for r in roles:
            dc = op.get(r, 0)
            ac = " AC 1" if r == drv else ""
            lines.append(f"V{r.upper()}{drv} {r}{drv} 0 DC {dc}{ac}")
            save.append(f"i(v{r}{drv})")
        lines.append(m.x(f"C{drv}", **{r: f"{r}{drv}" for r in roles}))
    lines.append(f".ac lin 1 {f} {f}")
    plots, log = m.run("caps", lines, save)
    p = pick(plots, "ac")
    if p is None:
        return None
    w = TWO_PI * f
    out = {}
    for drv in roles:
        for r in roles:
            if r == drv:
                continue
            c = abs(complex(p["data"][f"i(v{r}{drv})"][0]).imag) / w
            key = "c_" + "".join(sorted([drv, r]))
            out[key] = max(out.get(key, 0.0), c)
    return out


def diode_drop(m, v_from=-5.0, v_to=300.0, step=0.05):
    """Anode current against anode voltage, each plate alone (the other at the cathode), from below zero,
    where a real diode still passes its initial-velocity current, to well past any rated current."""
    first = "a1" if "a1" in m.c["roles"] else "a"
    nodes = {first: "a", "k": "0"}
    if first == "a1":
        nodes["a2"] = "0"
    lines = ["VA a 0 0", m.x("D", **nodes), f".dc VA {v_from} {v_to} {step}"]
    plots, log = m.run("drop", lines, ["i(va)"])
    p = pick(plots, "dc")
    if p is None:
        return None
    return vec(p, "v-sweep"), [-x for x in vec(p, "va")]


# ---------------------------------------------------------------- the sheet layer: a surveyed graph, redrawn
SYM = {  # the sheets' spellings, by electrode
    "a": r"(?:V_?a|U_?a|E_?b|E_?p|plate volts|plate voltage|anode voltage|Va)",
    "g2": r"(?:V_?g2|U_?g2|E_?c2|E_?g2|grid[- ]?(?:no\.?\s*)?(?:#\s*)?2 volts|screen volts|screen voltage)",
    "g1": r"(?:V_?g1?|U_?g1?|E_?c1?|E_?g1?|grid[- ]?(?:no\.?\s*)?(?:#\s*)?1 volts|grid volts|grid voltage|grid bias)",
}


def fixed_value(text, role):
    m = re.search(SYM[role] + r"\s*[=:]\s*([-+−]?\d[\d.,]*)", text or "", re.I)
    return float(m.group(1).replace("−", "-").replace(",", ".")) if m else None


def family_numbers(values):
    """The stepped values of a family as printed, up to the first second-quantity label (Ic2, Ig, dashed)."""
    head = re.split(r"(?:I[cg]2?\b|dashed|\bIc\b|\bIg\b)", values or "", maxsplit=1)[0]
    out = []
    for tok in re.findall(r"[-+−]?\d+(?:[.,]\d+)?", head):
        v = float(tok.replace("−", "-").replace(",", "."))
        if v not in out:
            out.append(v)
    return out


def family_role(fam):
    f = (fam or "").lower()
    if re.search(r"c2|g2|screen", f):
        return "g2"
    if re.search(r"\beb\b|\bea\b|\bva\b|\bua\b|plate|anode", f):
        return "a"
    if re.search(r"c1|g1|\bec\b|\bug\b|\bvg\b|grid", f):
        return "g1"
    return None


def ul_tap(fixed):
    m = re.search(r"=\s*(\d+)\s*\+\s*(0?\.\d+)\s*Δ?E", fixed or "")
    return (float(m.group(1)), float(m.group(2))) if m else None


def replay_static(m, fig):
    """Redraw a static graph from its survey row: the x span, the stepped family and the fixed electrodes.
    Returns (x, {family value: y}) or the reason it cannot be redrawn from the row alone."""
    test, fixed, conn = fig["test"], fig.get("fixed", ""), (fig.get("connection") or "").lower()
    fam_role = family_role(fig.get("family"))
    vals = family_numbers(fig.get("family_values"))
    def lead(v):    # "−60 (grid to ≈−68)": the labelled end of the axis, before any note
        m = re.match(r"\s*([-+−]?\d+(?:[.,]\d+)?)", (v or "").replace("−", "-"))
        return float(m.group(1).replace(",", ".")) if m else None
    x0, x1 = lead(fig["x_from"]), lead(fig["x_to"])
    if x0 is None or x1 is None:
        return "axis not read"
    if not vals or fam_role is None:
        return "family not read"
    pentode = m.c["kind"] == "pentode"
    g2 = None
    if pentode:
        if test == "triode-connected" or "triode" in conn:
            g2 = "a"
        elif test == "ultralinear":
            tap = ul_tap(fixed)
            if not tap:
                return "ultralinear tap not read"
            g2 = ("ul", tap[0], tap[1])
        else:
            g2 = fixed_value(fixed, "g2")
    if test in ("anode-characteristics", "anode-characteristics-positive-grid", "triode-connected", "ultralinear",
                "screen-current", "rectifier-drop", "diode-characteristic"):
        if fam_role == "g1":
            if pentode and g2 is None:
                return "screen voltage not read"
            r = anode_family(m, max(x1, 1.0), vals, {"g2": g2} if pentode else {})
            if r is None:
                return "failed"
            va, fam = r
            key = "ig2" if test == "screen-current" else "ia"
            return va, {v: fam[v].get(key) for v in vals}
        if fam_role == "g2" and pentode:
            vg = fixed_value(fixed, "g1")
            if vg is None:
                return "grid voltage not read"
            curves = {}
            for v2 in vals:
                r = anode_family(m, max(x1, 1.0), [vg], {"g2": v2})
                if r is None:
                    return "failed"
                va, fam = r
                curves[v2] = fam[vg]["ia"]
            return va, curves
    if test in ("transfer", "cutoff", "remote-cutoff"):
        if fam_role == "a":
            r = transfer(m, vals, min(x0, x1), max(x0, x1), 0.01, g2 if pentode else None)
            if r is None:
                return "failed"
            vg, tr = r
            return vg, {v: tr[v]["ia"] for v in vals}
        if fam_role == "g2" and pentode:
            va = fixed_value(fixed, "a")
            if va is None:
                return "anode voltage not read"
            curves = {}
            for v2 in vals:
                r = transfer(m, [va], min(x0, x1), max(x0, x1), 0.01, v2)
                if r is None:
                    return "failed"
                vg, tr = r
                curves[v2] = tr[va]["ia"]
            return vg, curves
    return "not a static graph"


def rc_cell(m, ebb, rp, rs, rg1, rk, rg2=None, thd_target=5.0, vout_gain=2.0, f=1000.0, cycles=30, name="cell"):
    """One cell of a resistance-coupled amplifier chart, as GE and RCA define it: the cathode resistor
    "adequately by-passed" (an ideal bypass: the cathode held at Rk times the stage's mean current under
    signal, found by iteration), the gain read at `vout_gain` V rms out, Eo the largest rms output at
    `thd_target` % total harmonic distortion. For a pentode the screen is fed through Rg2, also ideally
    bypassed."""
    def deck(drives, vks, vss):
        lines, save = [], []
        for i, d in enumerate(drives):
            lines += [f"VIN{i} in{i} 0 DC 0 SIN(0 {d} {f})", f"RG1{i} in{i} 0 {rg1}", f"VGM{i} in{i} g{i} 0",
                      f"VBB{i} bb{i} 0 {ebb}", f"RP{i} bb{i} am{i} {rp}", f"VAM{i} am{i} a{i} 0", f"VK{i} k{i} 0 {vks[i]}",
                      f"CC{i} am{i} o{i} 10u", f"RS{i} o{i} 0 {rs}"]
            nodes = {"a": f"a{i}", "g1": f"g{i}", "k": f"k{i}"}
            if rg2 is not None:
                lines += [f"VSS{i} s{i} 0 {vss[i]}", f"VSM{i} s{i} st{i} 0"]
                nodes["g2"] = f"st{i}"
                save.append(f"i(vsm{i})")
            lines.append(m.x(f"T{i}", **nodes))
            save += [f"v(o{i})", f"i(vam{i})", f"i(vgm{i})"]
        per = 1 / f
        lines.append(f".tran {per / 200:.4e} {cycles * per:.4e} 0 {per / 200:.4e}")
        return lines, save

    # the quiescent point with a resistor in the cathode (and the screen through its resistor)
    lines = [f"VBB bb 0 {ebb}", f"RP bb am {rp}", "VAM am a 0", f"RK k 0 {rk}", "VG g 0 0"]
    nodes = {"a": "a", "g1": "g", "k": "k"}
    if rg2 is not None:
        lines += [f"RG2 bb s {rg2}", "VSM s st 0"]
        nodes["g2"] = "st"
    lines += [m.x("T", **nodes), ".op"]
    plots, _ = m.run(f"{name}-op", lines)
    p = pick(plots, "op")
    if p is None:
        return None
    d = p["data"]
    ia0, vk0 = float(d["i(vam)"][0]), float(d["v(k)"][0])
    is0 = float(d["i(vsm)"][0]) if rg2 is not None else 0.0
    out = {"ia0": ia0, "vk0": vk0, "va0": float(d["v(a)"][0])}
    # the small-signal gain into the next grid, to place the drive ladder
    lines = ["VIN in 0 DC 0 AC 1", f"RG1 in 0 {rg1}", f"VBB bb 0 {ebb}", f"RP bb a {rp}", f"VK k 0 {vk0}",
             "CC a o 1", f"RS o 0 {rs}"]
    nodes = {"a": "a", "g1": "in", "k": "k"}
    if rg2 is not None:
        lines += [f"VSS s 0 {ebb - is0 * rg2}"]
        nodes["g2"] = "s"
    lines += [m.x("T", **nodes), ".ac lin 1 1k 1k"]
    plots, _ = m.run(f"{name}-ac", lines)
    p = pick(plots, "ac")
    g_ac = abs(complex(p["data"]["v(o)"][0])) if p else None
    out["gain_ac"] = g_ac
    if not g_ac:
        return out
    d_gain = vout_gain * math.sqrt(2) / g_ac
    drives = [d_gain] + [d_gain * 2 ** (k / 2) for k in range(1, 15)]
    vks = [vk0] * len(drives)
    vss = [ebb - is0 * rg2] * len(drives) if rg2 is not None else [0] * len(drives)
    for it in range(4):
        lines, save = deck(drives, vks, vss)
        plots, _ = m.run(f"{name}-tran{it}", lines, save)
        p = pick(plots, "tran")
        if p is None:
            out["tran"] = "failed"
            return out
        tt = vec(p, "time")
        per = 1 / f
        t0 = (cycles - 10) * per
        seg = [k for k, t in enumerate(tt) if t >= t0]
        if not seg or tt[-1] < cycles * per * 0.999:
            out["tran"] = "failed"
            return out
        means = [sum(vec(p, f"vam{i}")[k] for k in seg) / len(seg) for i in range(len(drives))]
        new_vk = [mi * rk for mi in means]
        moved = max(abs(a - b) / max(abs(b), 1e-9) for a, b in zip(new_vk, vks))
        if rg2 is not None:
            smean = [sum(vec(p, f"vsm{i}")[k] for k in seg) / len(seg) for i in range(len(drives))]
            vss = [ebb - s * rg2 for s in smean]
        vks = new_vk
        if moved < 0.005:
            break
    rows = []
    for i, dr in enumerate(drives):
        h, _ = harmonics(tt, vec(p, f"o{i}"), t0, cycles * per, 10)
        r = thd_row(h)
        r.update({"drive_pk": dr, "vout_rms": h[0] / math.sqrt(2), "ia_mean": means[i], "vk": vks[i],
                  "ig_peak": max(vec(p, f"vgm{i}")[k] for k in seg)})
        rows.append(r)
    out["levels"] = rows
    out["gain@2Vrms"] = rows[0]["vout_rms"] / (drives[0] / math.sqrt(2))
    th = [r["thd"] for r in rows]
    vo = [r["vout_rms"] for r in rows]
    out["eo@5%"] = None
    for i in range(1, len(rows)):
        if th[i - 1] is not None and th[i] is not None and th[i - 1] < thd_target <= th[i]:
            w = (math.log(thd_target) - math.log(th[i - 1])) / (math.log(th[i]) - math.log(th[i - 1]))
            out["eo@5%"] = math.exp(math.log(vo[i - 1]) + w * (math.log(vo[i]) - math.log(vo[i - 1])))
            break
    gi = next((r["drive_pk"] for r in rows if r["ig_peak"] > 1e-6), None)
    out["drive_at_grid_current"] = gi
    return out


def power_case(m, vb, loads, drives, pp=False, conn="pentode", vg=None, rk=None, rk_common=True, vg2=None, rg2=None,
               rg2_common=False, ul=None, f=1000.0, cycles=6, name="pc"):
    """An output stage at steady state, one copy per (load, peak drive per grid).

    Everything a test set makes ideal is ideal, and solved for rather than waited for: the output
    transformer (single-ended: Va = Vb − RL·(ia − Ī), an infinite primary inductance; push-pull: each half
    at v = Raa/4 · ((ia1 + x·ig2,1) − (ia2 + x·ig2,2)), x the ultralinear tap), the cathode bypass (the cathode
    held at Rk times the mean cathode current under signal, per valve or common), the screen decoupling
    (Vg2 supply less Rg2 times the mean screen current). Each of those is an unknown per copy, started at
    the zero-signal operating point and found by the secant method on its own residual; the drive goes
    straight to the grids, so nothing else in the circuit has memory."""
    combos = [(rl, d) for rl in loads for d in drives]
    halves = (0, 1) if pp else (0,)
    pent = m.c["kind"] == "pentode"
    per = 1 / f
    # the zero-signal point, with the real resistors: the start of every unknown
    lines = [f"VB b 0 {vb}"]
    for h in halves:
        nodes = {"a": "b", "g1": f"g{h}", "k": "kc" if (rk is not None and pp and rk_common) else f"k{h}"}
        lines.append(f"VG{h} g{h} 0 {vg if rk is None else 0}")
        if pent:
            if conn == "triode":
                nodes["a"] = f"a{h}"
                lines += [f"VA{h} b a{h} 0"]
                nodes["g2"] = f"a{h}"
            else:
                sup = "b" if conn == "ul" else "s"
                if conn != "ul":
                    lines.append(f"VSUP{h} s{h}x 0 {vg2}")
                    sup = f"s{h}x"
                rr = rg2 * (2 if (pp and rg2_common and conn != "ul") else 1) if rg2 else 1e-3
                lines += [f"RG2{h} {sup} sg{h} {rr}", f"VSM{h} sg{h} sgt{h} 0"]
                nodes["g2"] = f"sgt{h}"
        if rk is not None and not (pp and rk_common):
            lines.append(f"RK{h} k{h} 0 {rk}")
        elif rk is None:
            lines.append(f"VKZ{h} k{h} 0 0")
        lines.append(m.x(f"Q{h}", **nodes))
    if rk is not None and pp and rk_common:
        lines.append(f"RKC kc 0 {rk}")
    lines.append(".op")
    plots, _ = m.run(f"{name}-op", lines)
    p = pick(plots, "op")
    if p is None:
        return None
    d0 = p["data"]
    vk0 = [float(d0["v(kc)" if (rk is not None and pp and rk_common) else f"v(k{h})"][0]) if rk is not None else 0.0 for h in halves]
    vs0 = [float(d0[f"v(sgt{h})"][0]) if (pent and conn == "pentode") else 0.0 for h in halves]
    ia0 = -sum(float(d0["i(vb)"][0]) for _ in (0,)) / len(halves)
    unknowns = {}
    for c in range(len(combos)):
        for h in halves:
            if rk is not None:
                unknowns[(c, "vk", h)] = [vk0[h]]
            if pent and conn == "pentode" and rg2:
                unknowns[(c, "vs", h)] = [vs0[h]]
        if not pp:
            unknowns[(c, "im", 0)] = [ia0]
    resid = {k: [] for k in unknowns}

    def cur(key):
        if key in unknowns:
            return unknowns[key][-1]
        c, what, h = key
        return {"vk": 0.0, "vs": vg2 if vg2 is not None else 0.0, "im": 0.0}[what]

    rows = None
    for it in range(12):
        lines, save = [f"VB b 0 {vb}"], []
        for c, (rl, dr) in enumerate(combos):
            q = rl / 4
            for h in halves:
                t = f"{c}_{h}"
                sign = 1 if h == 0 else -1
                gdc = vg if rk is None else 0.0
                lines += [f"VG{t} g{t} 0 DC {gdc} SIN({gdc} {sign * dr} {f})" if dr else f"VG{t} g{t} 0 {gdc}",
                          f"VA{t} an{t} at{t} 0", f"VK{t} k{t} 0 {cur((c, 'vk', h)) if rk is not None else 0}"]
                nodes = {"a": f"at{t}", "g1": f"g{t}", "k": f"k{t}"}
                if pent:
                    if conn == "triode":
                        nodes["g2"] = f"at{t}"
                    elif conn == "ul":
                        lines += [f"VS{t} sn{t} st{t} 0", f"RG2{t} st{t} sg{t} {rg2 or 1e-3}"]
                        nodes["g2"] = f"sg{t}"
                    else:
                        lines += [f"VSS{t} sn{t} 0 {cur((c, 'vs', h))}", f"VS{t} sn{t} sg{t} 0"]
                        nodes["g2"] = f"sg{t}"
                    if conn != "triode":
                        save.append(f"i(vs{t})")
                lines.append(m.x(f"T{t}", **nodes))
                save += [f"i(va{t})", f"i(vg{t})"]
            x = ul if conn == "ul" else 0
            ia = [f"(i(VA{c}_{h})+{x}*i(VS{c}_{h}))" if conn == "ul" else f"i(VA{c}_{h})" for h in halves]
            if pp:
                diff = f"({ia[0]}-{ia[1]})"
                lines += [f"BH{c}_0 an{c}_0 b V=-{q}*{diff}", f"BH{c}_1 an{c}_1 b V={q}*{diff}"]
                if conn == "ul":
                    lines += [f"BU{c}_0 sn{c}_0 b V=-{x}*{q}*{diff}", f"BU{c}_1 sn{c}_1 b V={x}*{q}*{diff}"]
            else:
                lines += [f"BH{c}_0 an{c}_0 b V=-{rl}*({ia[0]}-{cur((c, 'im', 0))})"]
                if conn == "ul":
                    lines += [f"BU{c}_0 sn{c}_0 b V=-{x}*{rl}*({ia[0]}-{cur((c, 'im', 0))})"]
            save.append(f"v(an{c}_0)")
        lines.append(f".tran {per / 200:.4e} {cycles * per:.4e} 0 {per / 200:.4e}")
        plots, log = m.run(f"{name}-{it}", lines, save)
        p = pick(plots, "tran")
        if p is None or vec(p, "time")[-1] < cycles * per * 0.999:
            return rows
        tt = vec(p, "time")
        t0 = (cycles - 4) * per
        seg = [k for k, t in enumerate(tt) if t >= t0]

        def mean(nm):
            v = vec(p, nm)
            return sum(v[k] for k in seg) / len(seg)

        rows, worst = [], 0.0
        for c, (rl, dr) in enumerate(combos):
            ia_m = [mean(f"va{c}_{h}") for h in halves]
            is_m = [mean(f"vs{c}_{h}") if f"i(vs{c}_{h})" in p["data"] else 0.0 for h in halves]
            ig_pk = max(max(vec(p, f"vg{c}_{h}")[k] for k in seg) for h in halves)
            ik = [ia_m[h] + is_m[h] for h in halves]
            target = {}
            for h in halves:
                if rk is not None:
                    target[(c, "vk", h)] = rk * (sum(ik) if (pp and rk_common) else ik[h])
                if (c, "vs", h) in unknowns:
                    target[(c, "vs", h)] = vg2 - rg2 * (sum(is_m) if (pp and rg2_common) else is_m[h])
            if not pp:
                target[(c, "im", 0)] = ia_m[0] + (x * is_m[0] if conn == "ul" else 0)
            for key, tv in target.items():
                xs, rs = unknowns[key], resid[key]
                rs.append(tv - xs[-1])
                scale = max(abs(tv), 1e-3 if key[1] == "im" else 0.05)
                worst = max(worst, abs(rs[-1]) / scale)
                if len(xs) >= 2 and rs[-1] != rs[-2]:
                    nxt = xs[-1] - rs[-1] * (xs[-1] - xs[-2]) / (rs[-1] - rs[-2])
                else:
                    nxt = xs[-1] + 0.5 * rs[-1]
                xs.append(nxt)
            v = [a - vb for a in vec(p, f"an{c}_0")]
            hm, _ = harmonics(tt, v, t0, cycles * per, 4)
            row = thd_row(hm)
            vrms = hm[0] / math.sqrt(2)
            row.update({"load": rl, "drive_pk": dr, "pout": vrms ** 2 / (rl / 4 if pp else rl),
                        "ia_per_valve": sum(ia_m) / len(halves), "ig2_per_valve": sum(is_m) / len(halves),
                        "ig1_peak": ig_pk, "vk": unknowns[(c, "vk", 0)][-2] if rk is not None else 0.0,
                        "vg2": unknowns[(c, "vs", 0)][-2] if (c, "vs", 0) in unknowns else vg2})
            rows.append(row)
        if worst < 0.002:
            break
    return rows


# ---------------------------------------------------------------- the sheet layer: the survey's rows as conditions
UNIT = {"v": 1, "volts": 1, "volt": 1, "veff": 1, "v rms": 1, "volts rms": 1, "kv": 1e3, "mv": 1e-3,
        "a": 1, "amperes": 1, "ma": 1e-3, "milliamperes": 1e-3, "µa": 1e-6, "ua": 1e-6, "microamperes": 1e-6,
        "ω": 1, "ohm": 1, "ohms": 1, "kω": 1e3, "kohm": 1e3, "mω": 1e6, "meg": 1e6, "megohm": 1e6, "megohms": 1e6,
        "w": 1, "watts": 1, "watt": 1, "mw": 1e-3, "µmhos": 1e-6, "micromhos": 1e-6, "µmho": 1e-6, "mmhos": 1e-3,
        "ma/v": 1e-3, "µs": 1e-6, "ms": 1e-3, "%": 1, "percent": 1, "per cent": 1, "milliampere": 1e-3, "amp": 1,
        "k": 1e3, "microfarads": 1e-6, "µf": 1e-6, "henrys": 1, "henries": 1, "": 1}
PAIR = re.compile(r"([A-Za-zµ][\wµ\-\(\)'/\.]*?)\s*=\s*([-+−–]?\s*\d[\d.,]*)\s*([a-zA-ZΩµω%]*)")
CANON = [("vb", r"^(E_?bb|V_?b|V_?bb)$"), ("va", r"^(E_?b|E_?a|U_?a|V_?a|E_?p)$"), ("vg2", r"^(E_?c2|E_?g2|V_?g2|U_?g2)$"),
         ("vg1", r"^(E_?c1?|V_?g1?|U_?g1?|E_?g1?)$"), ("rk", r"^R_?k$"), ("rl", r"^(R_?L|R_?a|R_?p|R_?a-a|R_?aa)$"),
         ("rnext", r"^(R_?s|R_?gf|R_?g1'|R_?g')$"), ("rg1", r"^R_?g1?$"), ("rg2", r"^(R_?g2|R_?sg)$")]


def number(text):
    """The first number of a printed value: '2×55' → 55 (and per valve), '27,5' → 27.5, '40±14' → 40."""
    t = (text or "").replace("−", "-").replace("–", "-")
    per_valve = bool(re.match(r"\s*2\s*[×x]", t))
    t = re.sub(r"^\s*2\s*[×x]\s*", "", t)
    t = re.sub(r"(\d),(\d{3})(?!\d)", r"\1\2", t)      # 11,000 µmhos: an American thousands separator
    t = re.sub(r"(\d)[ \u00a0\u2009](\d{3})(?!\d)", r"\1\2", t)   # 6 100 µMHOS, 30 000 OHMS: Tung-Sol's
    m = re.match(r"\s*([-+]?\d+(?:[.,]\d+)?)", t)
    if not m:
        return None, per_valve
    return float(m.group(1).replace(",", ".")), per_valve


def scaled(value, unit):
    v, pv = number(value)
    if v is None:
        return None, pv
    u = re.sub(r"[.\s]+$", "", (unit or "").strip().lower()).replace("micromhos", "µmhos").replace("μ", "µ")
    return v * UNIT.get(u, UNIT.get(u.split()[0] if u else "", 1)), pv


def conditions(text):
    out = {}
    for sym, val, unit in PAIR.findall(text or ""):
        key = next((k for k, rx in CANON if re.match(rx, sym.strip(), re.I)), None)
        if key is None or key in out:
            continue
        v, _ = scaled(val, unit)
        if v is None:
            continue
        if key in ("rl", "rnext", "rg1", "rg2") and not unit and v < 100:
            v *= 1e6          # GE's resistance-coupled charts give megohms without a unit
        out[key] = v
    t = (text or "").lower()
    for word, key in (("plate voltage", "va"), ("grid voltage", "vg1"), ("anode voltage", "va")):
        m = re.search(word + r"\s*=\s*([-+−]?\d[\d.,]*)", t)
        if m and key not in out:
            out[key] = float(m.group(1).replace("−", "-").replace(",", "."))
    return out


def cases(rows, tests):
    """Rows grouped into the cases a sheet's column defines: (page, section, conditions) → {quantity: row}."""
    out = {}
    for r in rows:
        if r["test"] not in tests:
            continue
        out.setdefault((r["page"], r["section"], r["conditions"]), []).append(r)
    return out


QUANT = [("ia", r"^(plate|anode) current|^I_?[ab]\b|zero.signal (plate|anode) current|anode current zero"),
         ("gm", r"transconductance|mutual conductance|slope|^S\b|^g_?m"),
         ("ra", r"(plate|anode|internal).*resistance|^r_?[ap]\b|^R_?i\b"),
         ("mu", r"amplification factor|^µ|^mu\b"), ("ig2", r"(screen|grid.no.?\s*2|g2).*current")]


def strapped_only(m, pentode_sheet, text):
    """A pentode part modelled strapped as a triode (Ayumi's …T) answers only its sheet's triode-connected rows."""
    return pentode_sheet and m.c["kind"] == "triode" and "triode" not in text.lower()


def static_points(m, rows, pentode_sheet=False):
    """Every characteristic the sheets give at a stated operating point, from the model at the same point:
    at the sheet's grid voltage, and again at the sheet's anode current (the two disagree when the model's
    bias is off but its slopes are right)."""
    out = []
    for (page, section, cond), rs in cases(rows, ("typical-operation", "small-signal-params", "triode-connected")).items():
        c = conditions(cond)
        triode = "triode" in (cond + section).lower() and m.c["kind"] == "pentode"
        if strapped_only(m, pentode_sheet, cond + section):
            continue
        if "va" not in c or ("power" in section.lower() or "push" in section.lower()):
            continue
        want = {}
        for r in rs:
            key = next((k for k, rx in QUANT if re.search(rx, r["quantity"], re.I)), None)
            if key and key not in want:
                v, _ = scaled(r["value"], r["unit"])
                if v is not None:
                    want[key] = (v, r)
        if not want:
            continue
        g2 = "a" if triode else (c.get("vg2") if m.c["kind"] == "pentode" else None)
        if m.c["kind"] == "pentode" and g2 is None:
            continue
        got = {}
        if "vg1" in c:
            ss = small_signal(m, [(c["va"], c["vg1"])], g2)
            r_op = transfer(m, [c["va"]], c["vg1"] - 0.5, c["vg1"] + 0.5, 0.5, g2)
            if r_op:
                vg, tr = r_op
                got["ia"] = at(vg, tr[c["va"]]["ia"], c["vg1"])
                if "ig2" in tr[c["va"]]:
                    got["ig2"] = at(vg, tr[c["va"]]["ig2"], c["vg1"])
            if ss:
                got.update(ss[0])
        at_i = {}
        if "ia" in want:
            r_tr, _ = transfer_reach(m, [c["va"]], -300, 5, 0.02, g2)
            if r_tr:
                vg, tr = r_tr
                vq = x_where(vg, tr[c["va"]]["ia"], want["ia"][0])
                if vq is not None:
                    ss = small_signal(m, [(c["va"], vq)], g2)
                    if ss:
                        at_i = dict(ss[0], vg1=vq)
        if m.c["kind"] == "pentode" and not triode:
            for d in (got, at_i):
                if "mu_g1g2" in d:
                    d["mu"] = d["mu_g1g2"]
        for k, (v, r) in want.items():
            out.append({"doc": r["doc"], "page": page, "section": section, "conditions": cond, "quantity": k,
                        "sheet": v, "model@vg": got.get(k), "model@ia": at_i.get(k) if k != "ia" else None,
                        "vg1@ia": at_i.get("vg1")})
    return out


def rc_points(m, rows, kind, most=12):
    """The cells of the sheets' resistance-coupled amplifier charts, run as `rc_cell` defines it: in the preview
    at most `most` of them, spread evenly over the chart (the pipeline runs every one)."""
    out = []
    every = list(cases(rows, ("rc-amplifier",)).items())
    step = max(1, len(every) // most)
    for (page, section, cond), rs in every[::step][:most]:
        c = conditions(cond)
        vb = c.get("vb") or c.get("va")
        rp, rs_next = c.get("rl"), c.get("rnext")
        if not (vb and rp and rs_next):
            continue
        q = {}
        for r in rs:
            ql = r["quantity"].lower()
            v, _ = scaled(r["value"], r["unit"])
            if "cathode resistor" in ql:
                q["rk"] = v
            elif "screen resistor" in ql and v is not None:
                q["rg2"] = v * (1e6 if v < 100 else 1)
            elif "gain" in ql:
                q["gain"] = v
            elif "output" in ql:
                q.setdefault("eo", v)
        triode_conn = "triode" in cond.lower()
        if not q.get("rk") or "eo" not in q:
            continue
        if kind == "pentode" and not triode_conn and "rg2" not in q and "rg2" not in c:
            continue
        rg2 = q.get("rg2") or c.get("rg2")
        if kind == "pentode" and triode_conn:
            continue          # the triode-connected tables of a pentode need the strapped screen: not in rc_cell yet
        r = rc_cell(m, vb, rp, rs_next, c.get("rg1", 1e6), q["rk"], rg2=rg2 if kind == "pentode" else None,
                    name=f"rc-{tag(vb)}-{tag(rp)}-{tag(rs_next)}")
        if r is None:
            continue
        out.append({"doc": rs[0]["doc"], "page": page, "ebb": vb, "rp": rp, "rs": rs_next, "rk": q["rk"], "rg2": rg2,
                    "sheet_gain": q.get("gain"), "model_gain": r.get("gain@2Vrms"), "model_gain_ac": r.get("gain_ac"),
                    "sheet_eo": q.get("eo"), "model_eo": r.get("eo@5%"), "ia0": r.get("ia0"),
                    "drive_at_grid_current": r.get("drive_at_grid_current")})
    return out


POUT = [("vg3", r"suppressor|^V_?g3"), ("vin_50mw", r"for p_?out|p_?out\s*=|sensitivity"),
        ("pout", r"power output|output power|^P_?o(ut)?\b"), ("thd", r"distortion|^D_?tot|THD"),
        ("ia0", r"zero.signal (plate|anode) current|^I_?a\(o\)|anode current zero|^I_?b\(o\)"),
        ("iamax", r"max.*signal (plate|anode) current|^I_?a\(max|anode current at max"),
        ("ig20", r"zero.signal (grid.no.?\s*2|screen).*current|^I_?g2\(o\)|screen current zero"),
        ("ig2max", r"max.*signal (grid.no.?\s*2|screen).*current|^I_?g2\(max|screen current at max"),
        ("rl", r"load resist|anode load|^R_?a\b|^R_?a-a|plate.to.plate|effective load|^R_?L"),
        ("rk", r"cathode resistor|^R_?k"), ("vg1", r"grid.no.?\s*1.*voltage|control.grid voltage|^V_?g1\b|^E_?c1\b|grid voltage|grid bias"),
        ("vg2", r"(grid.no.?\s*2|screen).*voltage|^V_?g2|^E_?c2"), ("va", r"^(plate|anode) voltage|^V_?a\b|^E_?b\b"),
        ("vb", r"supply voltage|^V_?b\b|^E_?bb"), ("rg2", r"screen.*resistor|^R_?g2"),
        ("drive", r"peak af grid|grid.to.grid|input voltage|^V_?in|^E_?sig|signal voltage")]


def power_points(m, rows, pentode_sheet=False):
    """Every column of the sheets' output-stage tables, run as `power_case` defines it, at zero and at the
    sheet's drive."""
    out = []
    for (page, section, cond), rs in cases(rows, ("power-output", "ultralinear", "triode-connected")).items():
        text = (section + " " + cond).lower()
        if strapped_only(m, pentode_sheet, text):
            continue
        if not re.search(r"amplifier|operating|typical|push|single|class a", text) or "characteristics" in section.lower() and "operating" not in text:
            continue
        q = {}
        for r in rs:
            key = next((k for k, rx in POUT if re.search(rx, r["quantity"], re.I) or re.search(rx, r.get("symbol") or "", re.I)), None)
            if key and key not in q:
                v, pv = scaled(r["value"], r["unit"])
                if v is not None:
                    q[key] = (v, pv, r)
        c = conditions(cond)
        for k in ("va", "vb", "vg1", "vg2", "rk", "rl", "rg2"):
            if k in c and k not in q:
                q[k] = (c[k], False, None)
        pp = bool(re.search(r"push.pull|two valves|2 tubes|two tubes|grid.to.grid|plate.to.plate|a-a", text))
        conn = "triode" if "triode" in text else "ul" if re.search(r"ultra|tap|distributed load", text) else "pentode"
        tapm = re.search(r"(\d+)\s*%", text) if conn == "ul" else None
        ul = float(tapm.group(1)) / 100 if tapm else (0.43 if conn == "ul" else None)
        vb = (q.get("vb") or q.get("va") or (None,))[0]
        rl = (q.get("rl") or (None,))[0]
        if not vb or not rl or "pout" not in q or "drive" not in q:
            continue
        dr_v, _, dr_row = q["drive"]
        dq = (dr_row["quantity"] + " " + (dr_row.get("symbol") or "")).lower() if dr_row else ""
        peak = "peak" in dq or "crest" in dq
        g2g = bool(re.search(r"grid.to.grid|g1-g1", dq))
        drive_pk = dr_v * (1 if peak else math.sqrt(2)) / (2 if (pp and g2g) else 1)
        rk = q.get("rk", (None,))[0]
        vg = q.get("vg1", (None,))[0] if rk is None else None
        if vg is not None:
            vg = -abs(vg)      # "negative grid voltage 34 V": an output stage's fixed bias is always below zero
        if rk is None and vg is None:
            continue
        kw = dict(pp=pp, conn=conn if m.c["kind"] == "pentode" else "triode", vg=vg, rk=rk,
                  rk_common=not re.search(r"per valve|separate cathode", text), vg2=(q.get("vg2") or (vb,))[0],
                  rg2=(q.get("rg2") or (None,))[0], rg2_common=bool(re.search(r"common", text)), ul=ul)
        try:
            res = power_case(m, vb, [rl], [0.0, drive_pk], name=f"pw-{page}-{abs(hash(cond)) % 10**6}", **kw)
        except Exception:  # a model that cannot be driven past its own cut-off
            res = None
        row = {"doc": rs[0]["doc"], "page": page, "section": section, "pp": pp, "conn": kw["conn"], "vb": vb, "rl": rl,
               "drive_pk": drive_pk, "bias": f"Rk={rk}" if rk else f"Vg1={vg}"}
        for k in ("pout", "thd", "ia0", "iamax", "ig20", "ig2max"):
            if k in q:
                v, pv, r = q[k]
                if pp and k.startswith(("ia", "ig2")) and not pv and r is not None and not re.search(r"per valve|each", (r["quantity"] + r["notes"]).lower()):
                    v = v / 2      # an American push-pull column gives both valves together
                row[f"sheet_{k}"] = v
        if res:
            z, s = res[0], res[-1]
            row.update({"model_pout": s["pout"], "model_thd": s["thd"], "model_ia0": z["ia_per_valve"],
                        "model_iamax": s["ia_per_valve"], "model_ig20": z["ig2_per_valve"], "model_ig2max": s["ig2_per_valve"],
                        "model_ig1_peak": s["ig1_peak"]})
        else:
            row["model"] = "failed"
        out.append(row)
    return out


# ---------------------------------------------------------------- the universal layer
IA_LADDER = [1e-5, 2e-5, 5e-5, 1e-4, 2e-4, 5e-4, 1e-3, 2e-3, 5e-3, 1e-2, 2e-2, 5e-2, 0.1, 0.2, 0.5]
VA_LADDER = [12, 25, 50, 90, 100, 150, 180, 200, 250, 300, 350, 400, 450, 500]
VG2_LADDER = [100, 150, 200, 250, 300, 400]


def universal_triode(m, g2=None, tagname="triode"):
    """The triode battery (a pentode strapped as a triode when g2 is 'a'): what every model gets."""
    r = {}
    vg_list = grid_ladder(-150) + [0.5, 1, 2, 5, 10, 20]
    fam = anode_family(m, 600, vg_list, {"g2": g2} if g2 else {})
    if fam:
        va, f = fam
        for v in (100, 250, 400):
            for g in (0, -1, -2, -4, -8, -16, -32, -64):
                if g in f:
                    r[f"ia@{v}V,{g}V"] = at(va, f[g]["ia"], v)
            for g in (1, 5, 10, 20):
                r[f"ia@{v}V,+{g}V"] = at(va, f[g]["ia"], v)
                r[f"ig@{v}V,+{g}V"] = at(va, f[g]["ig1"], v)
    tr, reach = transfer_reach(m, VA_LADDER, -300, 5, 0.02, g2)
    r["sweep_reach"] = reach
    if tr:
        vg, t = tr
        for v in VA_LADDER:
            r[f"vg_cutoff@{v}V"] = x_where(vg, t[v]["ia"], 1e-5, log_y=True)
        ig = t[250]["ig1"]
        r["ig@0V,250V"] = at(vg, ig, 0.0)
        r["vg@ig=0.3uA"] = x_where(vg, ig, 3e-7, log_y=True)
        r["ig@+1V,250V"] = at(vg, ig, 1.0)
        r["ig@+5V,250V"] = at(vg, ig, 5.0)
        pts = []
        for v in (100, 250, 400):
            for i in IA_LADDER:
                x = x_where(vg, t[v]["ia"], i)
                if x is not None and x <= 0.0:
                    pts.append((v, x, i))
        ss = small_signal(m, [(v, x) for v, x, _ in pts], g2)
        if ss:
            for (v, x, i), s in zip(pts, ss):
                for k in ("gm", "ra", "mu"):
                    r[f"{k}@{num.si(i, 'A')},{v}V"] = s[k]
            mus = [s["mu"] for (v, x, i), s in zip(pts, ss) if v == 250 and s["mu"]]
            if len(mus) >= 3:
                r["mu_low/mu_high@250V"] = mus[0] / max(mus)
    caps = capacitances(m, {"a": 250, "g1": r.get("vg_cutoff@250V", -5) or -5, **({"g2": 250} if g2 not in (None, "a") else {})})
    if caps:
        r.update({k: v for k, v in caps.items()})
    return r


def universal_pentode(m):
    r = {}
    vgs = [0, -1, -2, -3, -4, -5, -6, -8, -10, -12, -15, -20, -25, -30, -40, -50, -60, -80, -100]
    for v2 in VG2_LADDER:
        fam = anode_family(m, 600, vgs, {"g2": v2})
        if not fam:
            r[f"anode@{v2}V"] = "failed"
            continue
        va, f = fam
        ia0 = f[0]["ia"]
        top = at(va, ia0, v2)
        r[f"ia@{v2}V,{v2}V,0V"] = top
        r[f"knee@{v2}V"] = x_where(va, ia0, 0.9 * top) if top else None
        g2 = f[0].get("ig2")
        if g2:
            hi, lo = at(va, g2, v2), at(va, g2, 50.0)
            r[f"ig2@{v2}V,{v2}V,0V"] = hi
            r[f"ig2_rise@50V/{v2}V"] = lo / hi if hi else None
            slope = (at(va, ia0, 400.0) - at(va, ia0, 300.0)) / 100 if v2 <= 300 else None
            r[f"ra@350V,{v2}V,0V"] = 1 / slope if slope else "absent (flat)"
    tr, reach = transfer_reach(m, [250], -150, 5, 0.02, 250)
    r["sweep_reach"] = reach
    if tr:
        vg, t = tr
        ia = t[250]["ia"]
        r["vg_cutoff@250V,250V"] = x_where(vg, ia, 1e-5, log_y=True)
        ig = t[250]["ig1"]
        r["vg@ig=0.3uA"] = x_where(vg, ig, 3e-7, log_y=True)
        r["ig@0V"] = at(vg, ig, 0.0)
        gm = [(ia[i + 1] - ia[i - 1]) / (vg[i + 1] - vg[i - 1]) if 0 < i < len(vg) - 1 else 0 for i in range(len(vg))]
        for g in (2e-6, 1e-5, 4e-5, 1e-4):
            r[f"vg1@gm={g * 1e6:g}umho"] = x_where(vg, gm, g, log_y=True)
        pts = [(250, x_where(vg, ia, i), i) for i in IA_LADDER]
        pts = [(v, x, i) for v, x, i in pts if x is not None and x <= 0]
        ss = small_signal(m, [(v, x) for v, x, _ in pts], 250)
        if ss:
            for (v, x, i), s in zip(pts, ss):
                for k in ("gm", "ra", "mu_g1g2"):
                    r[f"{k}@{num.si(i, 'A')},250V,250V"] = s.get(k)
    tri = universal_triode(m, "a")
    r.update({f"triode:{k}": v for k, v in tri.items() if not k.startswith("c_")})
    ulf = anode_family(m, 600, [0, -10, -20, -30], {"g2": ("ul", 400, 0.43)})
    if ulf:
        va, f = ulf
        for g in (0, -10, -20, -30):
            r[f"ul43%@400V:ia@300V,{g}V"] = at(va, f[g]["ia"], 300.0)
    caps = capacitances(m, {"a": 250, "g2": 250, "g1": -50})
    if caps:
        r.update(caps)
    return r


def universal_diode(m):
    r = {}
    d = diode_drop(m)
    if d:
        v, i = d
        r["ia@0V"] = at(v, i, 0.0)
        r["ia@-1V"] = at(v, i, -1.0)
        for ia in (1e-3, 1e-2, 0.1, 0.25, 0.5):
            r[f"va@{num.si(ia, 'A')}"] = x_where(v, i, ia)
        pts = [(math.log(a), math.log(b)) for a, b in zip(v, i) if 10 <= a <= 100 and b > 0]
        if len(pts) > 2:
            n_, c_ = num.linfit([p[0] for p in pts], [p[1] for p in pts])
            r["exponent(10-100V)"], r["perveance"] = n_, math.exp(c_)
    if "a1" in m.c["roles"] or m.c["part"] in ("5Y3GT", "5AR4", "5U4GB", "6X4", "GZ34", "5Y3"):
        for filt in ("C", "L"):
            rows = rectifier(m, [300, 400], [0.025, 0.05, 0.1, 0.15, 0.2, 0.25], filt=filt, c1=40e-6, c2=40e-6, l1=10.0, rs=50, f=60)
            if rows is None:
                r[f"{filt}:regulation"] = "failed"
            for row in rows or []:
                k = f"{row['vac']}Vrms,{row['idc_target'] * 1e3:g}mA"
                r[f"{filt}:vdc@{k}"], r[f"{filt}:idc@{k}"] = row["vdc"], row["idc"]
                r[f"{filt}:ia_peak@{k}"] = row["ia_peak"]
                if filt == "C":
                    r[f"C:surge@{k}"] = row["surge_peak"]
    return r


def regulation_points(m, figs):
    """The sheets' rectifier operation curves, redrawn: DC volts against DC current per AC volts per plate."""
    out = []
    for f in figs:
        if f["test"] != "rectifier-regulation":
            continue
        fx = f.get("fixed") or ""
        filt = "L" if "choke" in (f["title"] + fx).lower() else "C"
        cm = re.search(r"C\s*=\s*(\d+(?:\.\d+)?)\s*[µu]", fx)
        rsm = re.findall(r"R_?s\s*=\s*(\d+)", fx)
        lm = re.search(r"L\s*=\s*(\d+)\s*H", fx)
        vals = family_numbers(re.sub(r"\(\d\)", "", f.get("family_values") or ""))
        if not vals:
            continue
        c1 = float(cm.group(1)) * 1e-6 if cm else 40e-6
        rs = float(rsm[0]) if rsm else 50.0
        hz = 50 if "50" in fx and "Mullard" in f["doc"] else 60
        rows = rectifier(m, vals, [0.01, 0.05, 0.1, 0.15, 0.2], filt=filt, c1=c1, c2=10e-6 if filt == "L" else c1,
                         l1=float(lm.group(1)) if lm else 10.0, rs=rs, f=hz, name=f"reg-{f['page']}-{f['fig']}")
        out.append({"doc": f["doc"], "page": f["page"], "fig": f["fig"], "filter": filt, "c1": c1, "rs": rs,
                    "rows": [{k: row[k] for k in ("vac", "idc", "idc_target", "vdc", "ripple_pp", "ia_peak", "surge_peak")} for row in rows or []]})
    return out


# ---------------------------------------------------------------- main
def characterise(args):
    cand, survey, work = args
    m = Model(cand, work)
    res = {"id": cand["id"], "source": cand["source"], "name": cand["name"], "kind": cand["kind"], "pins": cand["pins"]}
    r = runs(m)
    res["runs"] = r
    if not r.get("runs"):
        return res
    docs = survey["docs"].get(cand["part"], [])
    pentode_sheet = any(survey["types"].get(d, "") in ("pentode", "remote-cutoff-pentode", "power-pentode", "beam-tetrode") for d in docs)
    rows = [x for x in survey["tables"] if x["doc"] in docs]
    figs = [x for x in survey["figures"] if x["doc"] in docs]
    try:
        if cand["kind"] == "triode":
            res["universal"] = universal_triode(m)
            res["static_points"] = static_points(m, rows, pentode_sheet)
            res["rc_points"] = rc_points(m, [x for x in rows if not pentode_sheet], "triode")
            res["power_points"] = power_points(m, rows, pentode_sheet)
            res["noise"] = stage_noise(m, 250, 100e3, 1500)
        elif cand["kind"] == "pentode":
            res["universal"] = universal_pentode(m)
            res["static_points"] = static_points(m, rows, pentode_sheet)
            res["rc_points"] = rc_points(m, rows, "pentode")
            res["power_points"] = power_points(m, rows, pentode_sheet)
            res["noise"] = stage_noise(m, 250, 100e3, 1500, rg2=390e3)
        else:
            res["universal"] = universal_diode(m)
            res["regulation_points"] = regulation_points(m, figs)
        replays = []
        for f in figs:
            if f["test"] in ("anode-characteristics", "anode-characteristics-positive-grid", "triode-connected", "ultralinear",
                             "screen-current", "transfer", "cutoff", "remote-cutoff"):
                strapped = strapped_only(m, pentode_sheet, f["test"] + " " + (f.get("connection") or "") + " " + f["title"])
                rr = "model strapped as a triode" if strapped else replay_static(m, f)
                replays.append({"doc": f["doc"], "page": f["page"], "fig": f["fig"], "test": f["test"],
                                "result": rr if isinstance(rr, str) else "ok"})
        res["figure_replays"] = replays
    except Exception as e:  # one model's failure is that model's result, never the run's
        res["error"] = f"{type(e).__name__}: {e}"
    return res


def main(argv):
    import csv
    from multiprocessing import Pool
    models_dir, survey_dir, work = Path(argv[1]), Path(argv[2]), Path(argv[3])
    parts = argv[4:]
    sheets = list(csv.DictReader(open(survey_dir / "sheets.csv", encoding="utf-8")))
    docs = {}
    for s in sheets:
        for name in re.findall(r"[0-9A-Z][0-9A-Z\-]+", f"{s['tube']} {s.get('equivalent') or ''}".upper()):
            n = name.replace("-", "")
            for key in {n, re.sub(r"(GT[AB]?|[AB])$", "", n)}:     # 6SN7-GTB is a 6SN7, 12AU7-A a 12AU7
                docs.setdefault(key, []).append(s["doc"])
    tables = []
    for f in sorted(survey_dir.glob("tables*.csv")):      # data/datasheets/survey/tube splits them by kind
        tables += list(csv.DictReader(open(f, encoding="utf-8")))
    survey = {"tables": tables, "figures": list(csv.DictReader(open(survey_dir / "figures.csv", encoding="utf-8"))),
              "types": {s["doc"]: s["type"] for s in sheets}}
    jobs = []
    for part in parts:
        survey_p = dict(survey, docs={part: sorted(set(docs.get(part.upper().replace("-", ""), [])))})
        for c in candidates(models_dir, part):
            if c["kind"]:
                jobs.append((c, survey_p, str(work)))
    out = work / "results"
    out.mkdir(parents=True, exist_ok=True)
    with Pool(int(os.environ.get("JOBS", "6"))) as pool:
        for res in pool.imap_unordered(characterise, jobs):
            (out / (res["id"].replace("/", "__") + ".json")).write_text(json.dumps(res, indent=1, default=str))
            print(res["id"], "ok" if res.get("runs", {}).get("runs") else "not run", res.get("error", ""), flush=True)


if __name__ == "__main__":
    main(sys.argv)
