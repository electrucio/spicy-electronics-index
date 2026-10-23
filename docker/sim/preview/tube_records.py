"""The characterisation records of one tube part, made with the preview's decks, in the shape the site reads.

    uv run python docker/sim/preview/tube_records.py <models dir> <survey dir> <work dir> <out dir> <part>
    (JOBS=6 models at once; ONLY=<text> runs the candidates whose id holds it)

Until `decks_tube.py` runs in the simulator images, a tube part's records are made here, on this machine's
ngspice, for the tube entries of the catalogue (`data/bench/measurements.yaml`, kind `tube`), and written as a
machine that cannot release writes them: one record per curated model in <out dir>/<hash>.json, the hash
being that of the recipe's model the curated file is (`data/models/parts/tube/<PART>.yaml`, matched by
source, name and the file's sha256), so that `data/verification/models/supplement/` puts them on the part's
page and the next `sei bench character-release` packs them. Numbers only: no model text leaves the private
tree. The grids below are the catalogue's (a change to one is a change to the entry), and a model that gives
nothing for a measurement gets the code `failed` with the reason, as the bench's own records do.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from datetime import date
from multiprocessing import Pool
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tube_preview as tp  # noqa: E402

CATALOGUE = "m-13"
ANODE_X = [5.0 * i for i in range(121)]                                      # 0 to 600 V
TRANSFER_X = sorted({round(v, 3) for v in
                     [-300 + 5 * i for i in range(41)] + [-100 + i for i in range(71)]
                     + [-30 + 0.25 * i for i in range(81)] + [-10 + 0.05 * i for i in range(221)]})
GRID_X = [round(-5 + 0.05 * i, 3) for i in range(201)]                        # −5 to +5 V
IA_X = [m * 10.0 ** e for e in range(-5, 0) for m in (1, 2, 5)] + [1.0]      # 10 µA to 1 A
VOUT_X = [0.1, 0.2, 0.3, 0.5, 0.7, 1, 1.5, 2, 3, 5, 7, 10, 15, 20, 30, 50, 70, 100, 150]
TRANSFER_VA = [100, 150, 200, 250, 300, 400]
PARAMS_VA = [100, 250, 400]
GRID_VA = [100, 250, 400]
TRACES = 9                                                                   # Vg1 = 0 down to −8 steps
SERIES = [1, 2, 2.5, 5]
MIDDLE_CELL = (300.0, 240e3, 510e3)                                          # the RC chart's cell drawn as THD curves
CHANGES = {
    "caret_power": "'^' written '**' (LTspice reads '^' as XOR; ngspice reads both as a power)",
    "shim": "the parameters a caller passes declared on the .SUBCKT line (ngspice refuses an undeclared one)",
    "psa": "read in ngspice's PSpice compatibility mode (ngbehavior=psa)",
    "lta": "read in ngspice's LTspice compatibility mode (ngbehavior=lta)",
    "ltpsa": "read in ngspice's LTspice and PSpice compatibility mode (ngbehavior=ltpsa)",
}


def si_tag(v: float, unit: str) -> str:
    """A ladder value as the output keys write it: 240kΩ, 1MΩ, 300V."""
    for f, p in ((1e6, "M"), (1e3, "k"), (1, ""), (1e-3, "m"), (1e-6, "µ")):
        if abs(v) >= f * 0.999:
            x = v / f
            return f"{x:g}{p}{unit}"
    return f"{v:g}{unit}"


def on_grid(xs, ys, grid, keep=lambda y: True):
    """A curve on the catalogue's grid: interpolated, None outside the swept span or where `keep` says no."""
    out = []
    for g in grid:
        if g < min(xs) - 1e-9 or g > max(xs) + 1e-9:
            out.append(None)
            continue
        y = tp.at(xs, ys, g)
        out.append(None if y is None or not math.isfinite(y) or not keep(y) else float(f"{y:.4g}"))
    return out


def loglog(xs, ys, grid):
    """THD-like curves: interpolated in log-log between the drive ladder's points, None outside them."""
    pts = sorted((x, y) for x, y in zip(xs, ys) if x and y and x > 0 and y > 0)
    out = []
    for g in grid:
        if not pts or g < pts[0][0] or g > pts[-1][0]:
            out.append(None)
            continue
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if x0 <= g <= x1:
                w = (math.log(g) - math.log(x0)) / (math.log(x1) - math.log(x0)) if x1 > x0 else 0
                out.append(float(f"{math.exp(math.log(y0) + w * (math.log(y1) - math.log(y0))):.4g}"))
                break
        else:
            out.append(float(f"{pts[-1][1]:.4g}"))
    return out


def sig(v):
    return None if v is None or not isinstance(v, (int, float)) or not math.isfinite(v) else float(f"{v:.4g}")


def auto_step(cutoff: float | None) -> float | None:
    """The anode family's grid step: the model's cut-off at 250 V over eight, the nearest value of the
    1-2-2.5-5 series (in log)."""
    if not cutoff or cutoff >= 0:
        return None
    raw = abs(cutoff) / 8
    cands = [s * 10.0 ** e for e in range(-3, 4) for s in SERIES]
    return min(cands, key=lambda c: abs(math.log(c / raw)))


def family_of(text: str) -> str:
    body = "\n".join(ln for ln in text.upper().splitlines() if not ln.lstrip().startswith("*"))
    if re.search(r"TRIODEK|BTETRODED|PENTHODED|DIODEK", body):
        return "derk-reefman"
    if re.search(r"\bBM1\b", body) and "URAMP" in body:
        return "ayumi"
    if "LOG(1+EXP(" in body.replace(" ", "") and "KG1" in body:
        return "koren"
    if re.search(r"PWR\(|\*\*\s*1\.5|PWRS\(", body):
        return "3/2 law"
    return "other"


def rc_cells(rows):
    """The cells of the part's resistance-coupled chart: (ebb, rp, rs, rg1, rk)."""
    out = []
    for (_, _, cond), rs in tp.cases(rows, ("rc-amplifier",)).items():
        c = tp.conditions(cond)
        vb, rp, rnext, rg1 = c.get("vb") or c.get("va"), c.get("rl"), c.get("rnext"), c.get("rg1", 1e6)
        rk = next((tp.scaled(r["value"], r["unit"])[0] for r in rs if "cathode resistor" in r["quantity"].lower()), None)
        if vb and rp and rnext and rk is not None:
            out.append((vb, rp, rnext, rg1, rk))
    return out


def cell_key(ebb, rp, rs, rg1) -> str:
    return f"{ebb:g}V,{si_tag(rp, 'Ω')},{si_tag(rs, 'Ω')}" + (",grid-leak" if rg1 >= 5e6 else "")


def measure(m, rows) -> tuple[dict, dict, dict, dict]:
    """values, curves, codes and errors per measurement id, for one triode model."""
    vals: dict = {}
    curves: dict = {}
    codes: dict = {}
    errors: dict = {}

    # tube-runs
    r = m.runs_result
    v = {"runs": True, "mode": r["mode"], "params_declared": r["shim"]}
    for k, x in r.items():
        mm = re.match(r"i_(a|g1)@a=(\d+),g1=(-?\d+)", k)
        if mm:
            v[f"{'ia' if mm.group(1) == 'a' else 'ig'}@{mm.group(2)}V,{mm.group(3)}V"] = sig(x)
    vals["tube-runs"], codes["tube-runs"] = v, "ok"

    # the transfer sweep: cut-off, the anode family's step, the bias points of the AC copies, the grid current
    tr, reach = tp.transfer_reach(m, TRANSFER_VA, -300, 5, 0.02)
    if not tr:
        for mid in ("triode-transfer", "triode-grid-current", "triode-params", "triode-anode"):
            codes[mid], errors[mid] = "failed", {"ngspice": "the transfer sweep returned no waveform"}
        return vals, curves, codes, errors
    vg, t = tr
    v, cv = {"sweep_from": reach}, {}
    for va in TRANSFER_VA:
        ia = t[va]["ia"]
        v[f"vg_cutoff@{va}V"] = sig(tp.x_where(vg, ia, 1e-5, log_y=True))
        v[f"ia@{va}V,0V"] = sig(tp.at(vg, ia, 0.0))
        # drawn from a quarter beyond where the current falls to a thousandth of its zero-bias value (the foot,
        # whatever leakage a model carries below it) up to +1 V
        foot = tp.x_where(vg, ia, max(1e-6, 1e-3 * (tp.at(vg, ia, 0.0) or 0)), log_y=True)
        lo = 1.25 * foot if foot is not None and foot < 0 else min(vg)
        cv[f"Ia, Va={va}V"] = [y if lo <= x <= 1.0 else None for x, y in zip(TRANSFER_X, on_grid(vg, ia, TRANSFER_X))]
    vals["triode-transfer"], curves["triode-transfer"], codes["triode-transfer"] = v, cv, "ok"
    cutoff = v.get("vg_cutoff@250V")

    # grid current, from the same sweep's grid ammeters
    v, cv = {}, {}
    for va in GRID_VA:
        ig = t[va]["ig1"]
        cv[f"Ig, Va={va}V"] = on_grid(vg, ig, GRID_X)
    ig = t[250]["ig1"]
    v["vg@ig=0.3uA"] = sig(tp.x_where(vg, ig, 3e-7, log_y=True))
    v["vg@ig=1uA"] = sig(tp.x_where(vg, ig, 1e-6, log_y=True))
    for g in (0.0, 1.0, 5.0):
        v[f"ig@{g:+g}V".replace("+0V", "0V")] = sig(tp.at(vg, ig, min(g, max(vg))))
    i1, i2 = tp.at(vg, ig, 0.95), tp.at(vg, ig, 1.05)
    v["rin@+1V"] = sig(0.1 / (i2 - i1)) if i1 is not None and i2 is not None and i2 > i1 else None
    below = tp.at(vg, ig, -0.5)
    v["ig@-0.5V"] = sig(below)
    vals["triode-grid-current"], curves["triode-grid-current"] = v, cv
    codes["triode-grid-current"] = "absent" if not (tp.at(vg, ig, 1.0) or 0) > 1e-9 else "ok"

    # the anode family, its step the model's own
    step = auto_step(cutoff)
    if step:
        vgs = [round(-k * step, 6) for k in range(TRACES)]
        fam = tp.anode_family(m, 600, vgs)
        if fam:
            va, f = fam
            v = {"vg1_step": step}
            for x in (0, 5, 12, 25, 50, 250):
                v[f"ia@{x}V,0V"] = sig(tp.at(va, f[0.0]["ia"], float(x)))
            vals["triode-anode"] = v
            # each trace stops where Va × Ia passes the power at the model's own I0 point (250 V × I0), as a sheet
            # dashes its traces past the dissipation limit
            p0 = 250 * (v["ia@250V,0V"] or 0)
            curves["triode-anode"] = {
                f"Ia, Vg1={-k}·step": [y if y is None or not p0 or x * y <= p0 else None
                                       for x, y in zip(ANODE_X, on_grid(va, f[vgs[k]]["ia"], ANODE_X))]
                for k in range(TRACES)}
            v["p_limit"] = sig(p0)
            codes["triode-anode"] = "ok"
    if "triode-anode" not in codes:
        codes["triode-anode"], errors["triode-anode"] = "failed", {"ngspice": "no cut-off at 250 V, or the anode sweep failed"}

    # µ, gm and ra against anode current
    pts = []
    for va in PARAMS_VA:
        for i in IA_X:
            x = tp.x_where(vg, t[va]["ia"], i)
            if x is not None and x <= 0.0:
                pts.append((va, x, i))
    ss = tp.small_signal(m, [(a, x) for a, x, _ in pts]) if pts else None
    if ss:
        cv = {}
        for va in PARAMS_VA:
            got = {i: s for (a, x, i), s in zip(pts, ss) if a == va}
            for q, name in (("mu", "µ"), ("gm", "gm"), ("ra", "ra")):
                cv[f"{name}, Va={va}V"] = [sig(got[i][q]) if i in got else None for i in IA_X]
        mus = [ss[k]["mu"] for k, (a, x, i) in enumerate(pts) if a == 250 and ss[k]["mu"]]
        v = {"mu_ratio@250V": sig(mus[0] / max(mus)) if len(mus) >= 3 else None}
        for a, x, i in pts:
            if abs(i - 1e-3) < 1e-9:
                s = ss[pts.index((a, x, i))]
                v.update({f"mu@1mA,{a}V": sig(s["mu"]), f"gm@1mA,{a}V": sig(s["gm"]), f"ra@1mA,{a}V": sig(s["ra"])})
        vals["triode-params"], curves["triode-params"], codes["triode-params"] = v, cv, "ok"
    else:
        codes["triode-params"], errors["triode-params"] = "failed", {"ngspice": "no AC solution at the bias points"}

    # the interelectrode capacitances, cold (at cut-off) and hot (at a quarter of I0)
    i0 = vals["tube-runs"].get("ia@250V,0V")
    v = {}
    for label, g in (("", cutoff or -5.0), ("@hot", tp.x_where(vg, t[250]["ia"], (i0 or 0) / 4) if i0 else None)):
        if g is None:
            continue
        caps = tp.capacitances(m, {"a": 250, "g1": g})
        if caps:
            v[f"c_g1k{label}"] = sig(caps.get("c_g1k"))
            v[f"c_g1a{label}"] = sig(caps.get("c_ag1"))
            v[f"c_ak{label}"] = sig(caps.get("c_ak"))
    vals["tube-capacitance"] = v
    codes["tube-capacitance"] = "absent" if v and max(x or 0 for x in v.values()) < 1e-15 else ("ok" if v else "failed")

    # the resistance-coupled chart, every cell of the part's sheet
    v, cv = {}, {}
    for ebb, rp, rs, rg1, rk in rc_cells(rows):
        res = tp.rc_cell(m, ebb, rp, rs, rg1, rk, name=f"rc-{tp.tag(ebb)}-{tp.tag(rp)}-{tp.tag(rs)}-{tp.tag(rg1)}")
        k = cell_key(ebb, rp, rs, rg1)
        if not res:
            continue
        v[f"gain@{k}"] = sig(res.get("gain@2Vrms"))
        v[f"eo@{k}"] = sig(res.get("eo@5%"))
        v[f"ia0@{k}"] = sig(res.get("ia0"))
        v[f"vk@{k}"] = sig(res.get("vk0"))
        v[f"grid_onset@{k}"] = sig(res.get("drive_at_grid_current"))
        if (ebb, rp, rs) == MIDDLE_CELL and rg1 < 5e6 and res.get("levels"):
            lv = res["levels"]
            xs = [x["vout_rms"] for x in lv]
            for q in ("thd", "h2", "h3"):
                cv[q.upper()] = loglog(xs, [x[q] for x in lv], VOUT_X)
    if v:
        vals["triode-rc-amplifier"], curves["triode-rc-amplifier"], codes["triode-rc-amplifier"] = v, cv, "ok"
    else:
        codes["triode-rc-amplifier"], errors["triode-rc-amplifier"] = "failed", {"ngspice": "no cell ran"}

    # noise, and how much of it comes from inside the model
    nz = tp.stage_noise(m, 250, 100e3, 1500, rs=1e3)
    if nz:
        vals["triode-noise"] = {k: sig(nz.get(k)) for k in ("en@10Hz", "en@1kHz", "en@10kHz", "inside_share@1kHz", "req@1kHz")}
        codes["triode-noise"] = "absent" if not (nz.get("inside_share@1kHz") or 0) > 1e-3 else "ok"
    else:
        codes["triode-noise"], errors["triode-noise"] = "failed", {"ngspice": "the noise analysis returned nothing"}
    return vals, curves, codes, errors


DECK_IDS = {"runs": ["tube-runs"], "transfer": ["triode-transfer", "triode-grid-current"], "anode": ["triode-anode"],
            "params": ["triode-params"], "caps": ["tube-capacitance"], "rc": ["triode-rc-amplifier"], "noise": ["triode-noise"]}
ANALYSIS = {"runs": "op", "transfer": "dc", "anode": "dc", "params": "ac", "caps": "ac", "rc": "tran", "noise": "noise"}


def decks_of(m) -> dict:
    out = {}
    for p in sorted(m.dir.glob("*.cir")):
        head = p.stem.split("-")[0]
        if head not in DECK_IDS:
            continue
        dig = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
        out[p.stem] = {"analysis": ANALYSIS[head], "ids": DECK_IDS[head], "ngspice": {"digest": dig, "pack": 1}}
    return out


def recipe_hashes(part: str, root: Path) -> dict:
    """(source, name, file sha256) of every model of the recipe and of its copies, to the model's hash."""
    rec = yaml.safe_load((root / "data/models/parts/tube" / f"{part}.yaml").read_text(encoding="utf-8"))
    out = {}
    for m in rec.get("models") or []:
        for c in [m] + list(m.get("copies") or []):
            out.setdefault((c["source"], c["name"], (c.get("get") or {}).get("sha256")), m["hash"])
    return out


def main(argv) -> int:
    models_dir, survey_dir, work, out_dir = (Path(a) for a in argv[:4])
    part = argv[4]
    root = Path(__file__).resolve().parents[3]
    hashes = recipe_hashes(part, root)
    rows = []
    for f in sorted(survey_dir.glob("tables*.csv")):
        rows += list(csv.DictReader(open(f, encoding="utf-8")))
    sheets = list(csv.DictReader(open(survey_dir / "sheets.csv", encoding="utf-8")))
    docs = {s["doc"] for s in sheets if re.sub(r"[^0-9A-Z]", "", s["tube"].upper()).startswith(part.upper())}
    rows = [r for r in rows if r["doc"] in docs]
    version = subprocess.run(["ngspice", "--version"], capture_output=True, text=True).stdout
    version = next((ln.strip("* ").strip() for ln in version.splitlines() if "ngspice-" in ln), "ngspice")
    commit = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    out_dir.mkdir(parents=True, exist_ok=True)
    prov = json.loads((models_dir / part / "part.json").read_text())["candidates"]
    jobs = []
    for cand in tp.candidates(str(models_dir), part):
        if os.environ.get("ONLY") and os.environ["ONLY"] not in cand["id"]:
            continue
        meta = next(c for c in prov if c["file"] == Path(cand["file"]).name)
        h = hashes.get((meta["provenance"]["source"], meta["name"], meta["provenance"].get("file_sha256")))
        if not h or cand["kind"] != "triode":
            print(f"{cand['id']}: {'not a triode' if h else 'no recipe model'}: skipped")
            continue
        jobs.append((cand, meta, h, str(work), str(out_dir), part, rows, version, commit))
    with Pool(int(os.environ.get("JOBS", "6"))) as pool:
        for line in pool.imap_unordered(one, jobs):
            print(line, flush=True)
    return 0


def one(job) -> str:
    """One curated model: measured, and its record written."""
    cand, meta, h, work, out_dir, part, rows, version, commit = job
    m = tp.Model(cand, work)
    t0 = time.time()
    r = tp.runs(m)
    if r.get("runs"):
        m.runs_result = r
        vals, curves, codes, errors = measure(m, rows)
        runs = "ok"
    else:                                                    # a model that does not load is a result too
        why = (r.get("why") or ["?"])[-1]
        cls = "params" if re.search(r"parameter", why, re.I) else "subckt" if re.search(r"subckt", why, re.I) \
            else "domain" if re.search(r"range|domain", why, re.I) else "syntax"
        vals = {"tube-runs": {"runs": False, "error_class": cls}}
        curves, codes, errors = {}, {"tube-runs": "failed"}, {"tube-runs": {"ngspice": why}}
        r = {"mode": None, "shim": False}                  # tried every way; nothing it ran with to report
        runs = "failed"
    changes = [CHANGES[c["id"]] for c in meta.get("changes") or [] if c["id"] in CHANGES]
    if r["shim"]:
        changes.append(CHANGES["shim"])
    if r["mode"] in CHANGES:
        changes.append(CHANGES[r["mode"]])
    text = Path(cand["file"]).read_text(errors="replace")
    rec = {
        "schema": 1, "hash": h, "kind": "tube", "class": None, "family": family_of(text), "parts": [f"tube/{part}"],
        "pins": meta["pins"], "polarity": None, "catalogue": CATALOGUE, "primary": "ngspice", "secondary": "",
        "runs": {"ngspice": runs}, "codes": codes, "values": {k: {"ngspice": v} for k, v in vals.items()},
        "derived": {}, "curves": curves, "other_curves": {}, "agree": {}, "decks": decks_of(m),
        "changes": {"ngspice": changes}, "errors": errors,
        "engines": {"ngspice": {"image": f"host:{version}", "version": version, "on": date.today().isoformat(),
                                "cpu_s": round(time.time() - t0, 1),
                                "bench": {"commit": commit, "clean": False, "script": "docker/sim/preview/tube_records.py"}}},
    }
    (Path(out_dir) / f"{h}.json").write_text(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return f"{cand['id']} -> {h}: " + ", ".join(f"{k} {c}" for k, c in sorted(codes.items())) + f" ({time.time() - t0:.0f} s)"

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
