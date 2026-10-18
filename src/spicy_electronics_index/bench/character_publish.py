"""Publish what the characterisation measured, one file per model hash, with everything a reader needs
to repeat any number and nothing of the card.

    sei bench character-publish

The latest run of each engine is read; a model gets one record (`config.character(hash)`) holding, per
measurement, the values of every engine at four significant figures, the code where a number cannot
stand, the primary engine's curves on the catalogue's grid, the agreement between engines, and the
digest of each deck as it is written for the model alone. The ledger is stamped per hash with the
engines published, so that `sei bench character` skips them next time.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path

from spicy_electronics_index.bench import catalogue
from spicy_electronics_index.bench.character import (
    ENGINES,
    PLANNED_KINDS,
    PRIMARY,
    VERSION,
    input_digest,
    ledger,
)
from spicy_electronics_index.bench.jobs import CHANGES
from spicy_electronics_index.core.config import character, character_runs
from spicy_electronics_index.core.ledger import today

SCHEMA = 1
TOLERANCES = (0.01, 0.05)
# below these, two engines' values count as equal: a capacitance or a time no part has, and the leakage
# currents, which every engine sets at its own minimum conductance (10 to 20 pA at 10 V)
FLOORS = {"F": 1e-16, "s": 1e-12}
KEY_FLOORS = {"icbo": 1e-10, "iceo": 1e-10, "iebo": 1e-10, "igss": 1e-10, "idss": 1e-10, "ig_operating": 1e-10,
              "hre": 1e-7}      # a card without VAF gives hre as a numerical zero, different in every engine
ERROR_CHARS = 160
DIGEST_CHARS = 16     # of the sha256: what a reader compares; the whole digest is in the private run
CURVE_FIGURES = 4     # a curve is read on hover, slopes included: three figures flattened the Early slope to zero
CURVE_X_FIGURES = 5   # a waveform's own x: the turn-off edge lives at 3 µs and lasts nanoseconds


def sig(x):
    """Four significant figures, through lists and dicts; anything that is not a float passes."""
    if isinstance(x, bool) or x is None:
        return x
    if isinstance(x, float):
        return float(f"{x:.4g}")
    if isinstance(x, list):
        return [sig(v) for v in x]
    if isinstance(x, dict):
        return {k: sig(v) for k, v in x.items()}
    return x


def sig_curve(x):
    if isinstance(x, float):
        return float(f"{x:.{CURVE_FIGURES}g}")
    if isinstance(x, list):
        return [sig_curve(v) for v in x]
    if isinstance(x, dict):
        return {k: sig_curve(v) for k, v in x.items()}
    return x


def round_curves(curves):
    """A curve on the catalogue's grid carries y alone, at four figures. A waveform carries [x, y] pairs,
    and its x keeps five, so that a fall at 3.1123 µs does not collapse onto 3.11 µs."""
    out = {}
    for mid, by_name in curves.items():
        out[mid] = {}
        for name, pts in by_name.items():
            if pts and all(isinstance(p, list) and len(p) == 2 for p in pts):
                out[mid][name] = [[float(f"{p[0]:.{CURVE_X_FIGURES}g}") if isinstance(p[0], float) else p[0], sig_curve(p[1])] for p in pts]
            else:
                out[mid][name] = sig_curve(pts)
    return out


def differs(a, b, tol=TOLERANCES[0]) -> bool:
    """Whether a secondary engine's value is worth publishing beside the primary's."""
    if isinstance(a, bool) or isinstance(b, bool) or not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        return a != b
    m = (abs(a) + abs(b)) / 2
    return m > 0 and abs(a - b) / m > tol


def curve_differs(a: list, b: list, floor: float = 0.0, tol: float = TOLERANCES[0]) -> bool:
    """Whether a secondary engine's curve on the grid is worth publishing beside the primary's: a point both
    engines reached that they place more than the tolerance apart. Reaching one grid point more or less is
    not a difference worth a curve."""
    for x, y in zip(a, b):
        if x is None or y is None or (abs(x) < floor and abs(y) < floor):
            continue
        m = (abs(x) + abs(y)) / 2
        if m > 0 and abs(x - y) / m > tol:
            return True
    return False


def waveform_differs(mine: dict, theirs: dict, tol: float = TOLERANCES[1]) -> bool:
    """A transient differs by about 1 % between engines by nature; its waveform is worth publishing when a
    time it gave differs from the primary's by more than the wider tolerance."""
    return any(differs(v, theirs.get(k), tol) for k, v in mine.items() if isinstance(v, (int, float)) and not isinstance(v, bool))


# what a record carries of its curves, so that two thousand models fit the site: a curve tracer family whose
# top trace never leaves the noise floor or runs past any rating carries nothing a reader can use
TRACER_RANGE = (2e-5, 20.0)        # A: the top trace's highest collector current, for a universal family kept
SECONDARY_CURVE_TOL = TOLERANCES[1]  # a secondary engine's grid curve is published where it differs by more than 5 %


def trim_curves(curves: dict) -> dict:
    """The curves a record publishes: the tracer's universal families within range (the auto family always),
    and the switching waveforms from the first supply only (the times at both are in the values)."""
    out = dict(curves)
    tr = out.get("bjt-tracer")
    if tr:
        top = {}
        for name, pts in tr.items():
            parts = name.split(", ")
            if len(parts) == 3 and parts[1] == "step 5":
                vals = [abs(v) for v in pts if isinstance(v, (int, float))]
                top[parts[2]] = max(vals) if vals else 0.0
        keep = {fam for fam, v in top.items() if fam == "auto" or TRACER_RANGE[0] <= v <= TRACER_RANGE[1]}
        out["bjt-tracer"] = {n: p for n, p in tr.items() if n.split(", ")[-1] in keep}
    sw = out.get("bjt-switching")
    if sw:
        out["bjt-switching"] = {n: p for n, p in sw.items() if not (n.startswith("IC(t)") and "VCC=" in n)}
    return out


def curve_units(doc: dict) -> dict[tuple[str, str], str]:
    return {(m["id"], c["name"]): c.get("unit", "") for m in doc["measurements"] for c in m.get("curves") or []}


def run_order(d: Path) -> tuple[str, int]:
    """A run directory's place in time: its date, then its number that day (2026-10-06-10 after -9, which the
    alphabet puts before -2)."""
    name = d.name
    day, _, k = name[:10], name[10:11], name[11:]
    return day, int(k) if k.isdigit() else 1


def runs_of(engine: str) -> list[Path]:
    """An engine's finished runs, newest first."""
    base = character_runs(engine)
    if not base.exists():
        return []
    return sorted((d for d in base.iterdir() if d.is_dir() and (d / "run.json").exists()), key=run_order, reverse=True)


def latest_run(engine: str) -> Path | None:
    runs = runs_of(engine)
    return runs[0] if runs else None


def load_run(run_dir: Path) -> tuple[dict, dict[str, dict], dict[str, dict]]:
    info = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    results = {}
    for p in sorted(run_dir.glob("results-*.jsonl")):
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                results[r["id"]] = r
    jobs = {}
    for line in (run_dir / "jobs.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            j = json.loads(line)
            jobs[j["id"]] = {k: v for k, v in j.items() if k != "card"}
    return info, results, jobs


def units_of(doc: dict) -> dict[str, str]:
    """The unit of each output key, by its name before the '@'."""
    out = {}
    for m in doc["measurements"]:
        for o in m["outputs"]:
            out[(m["id"], o["key"].split("@")[0])] = o["unit"]
    return out


def agree(by_engine: dict[str, dict], units: dict[str, str] | None = None, mid: str = "") -> list | None:
    """[largest spread, class, engines compared, odd engine] over the outputs two or more engines gave."""
    units = units or {}
    engines = sorted(e for e, vals in by_engine.items() if vals)
    if len(engines) < 2:
        return None
    worst, odd = 0.0, Counter()
    keys = {k for e in engines for k, v in by_engine[e].items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
    for k in keys:
        got = {e: by_engine[e][k] for e in engines if isinstance(by_engine[e].get(k), (int, float))
               and not isinstance(by_engine[e].get(k), bool)}
        if len(got) < 2:
            continue
        base = k.split("@")[0]
        floor = max(FLOORS.get(units.get((mid, base), ""), 0.0), KEY_FLOORS.get(base, 0.0))
        vals = {e: (0.0 if abs(v) < floor else v) for e, v in got.items()}
        mean = sum(abs(v) for v in vals.values()) / len(vals)
        spread = 0.0 if mean == 0 else (max(vals.values()) - min(vals.values())) / mean
        worst = max(worst, spread)
        if spread > TOLERANCES[1] and len(vals) >= 3:
            med = sorted(vals.values())[len(vals) // 2]
            odd[max(vals, key=lambda e: abs(vals[e] - med))] += 1
    cls = "1%" if worst <= TOLERANCES[0] else ("5%" if worst <= TOLERANCES[1] else ">5%")
    return [sig(worst), cls, engines, odd.most_common(1)[0][0] if odd else None]


def build_record(h: str, per_engine: dict[str, tuple[dict, dict, dict]], doc: dict) -> dict:
    """One model's record from (run info, result, job) per engine."""
    engines = [e for e in ENGINES if e in per_engine]
    primary = PRIMARY if PRIMARY in engines else engines[0]
    _, r0, j0 = per_engine[primary]
    units = units_of(doc)
    rec: dict = {"schema": SCHEMA, "hash": h, "kind": j0["kind"], "family": j0["family"], "polarity": j0["polarity"],
                 "catalogue": doc["version"], "class": None, "parts": sorted(j0.get("parts", [])), "primary": primary,
                 "secondary": f"only the outputs that differ from {primary}'s by more than {TOLERANCES[0]:.0%}, and its curves for those measurements",
                 "engines": {}, "runs": {}, "values": {}, "codes": {}, "errors": {}, "derived": {}, "curves": {},
                 "agree": {}, "decks": {}, "changes": {}}
    if j0.get("pins"):
        rec["pins"] = j0["pins"]                     # a subcircuit, measured through its pins in this order
    for e in engines:
        info, r, j = per_engine[e]
        rec["engines"][e] = {"version": r.get("version") or info.get("version"), "image": info["image"], "bench": info["bench"],
                             "on": info["on"], "cpu_s": sig(sum(d.get("cpu_s", 0) for d in r.get("decks", {}).values()))}
        rec["runs"][e] = "failed" if r.get("error") or not r.get("values") else "ok"
        rec["changes"][e] = j.get("changes", [])
        for mid, vals in r.get("values", {}).items():
            rec["values"].setdefault(mid, {})[e] = sig(vals)
        for mid, text in (r.get("errors") or {}).items():
            rec["errors"].setdefault(mid, {})[e] = text[:ERROR_CHARS]
        for name, d in (r.get("decks") or {}).items():
            slot = rec["decks"].setdefault(name, {"ids": d["ids"], "analysis": d["analysis"]})
            slot[e] = {"digest": d["digest"][:DIGEST_CHARS], "pack": d["pack"]}
    rec["codes"] = dict(r0.get("codes") or {})
    rec["derived"] = sig(r0.get("derived") or {})
    rec["curves"] = round_curves(trim_curves(r0.get("curves") or {}))
    # a secondary engine's curve goes out where it differs from the primary's: a grid curve by its points, a
    # waveform (its own x) when the times read from it differ by more than 5 %
    rec["other_curves"] = {}
    cunits = curve_units(doc)
    for e in engines:
        if e == primary:
            continue
        own: dict = {}
        for mid, cs in trim_curves(per_engine[e][1].get("curves") or {}).items():
            prim = (r0.get("curves") or {}).get(mid) or {}
            for name, pts in cs.items():
                pairs = bool(pts) and isinstance(pts[0], list)
                mine, theirs = per_engine[e][1].get("values", {}).get(mid) or {}, r0.get("values", {}).get(mid) or {}
                if pairs and waveform_differs(mine, theirs) or not pairs and curve_differs(pts, prim.get(name) or [], FLOORS.get(cunits.get((mid, name), ""), 0.0), SECONDARY_CURVE_TOL):
                    own.setdefault(mid, {})[name] = pts
        if own:
            rec["other_curves"][e] = round_curves(own)
    for mid, by_engine in rec["values"].items():
        a = agree(by_engine, units, mid)
        if a:
            rec["agree"][mid] = a
    # the agreement is computed on every number; the secondary engines then keep only what differs
    for mid, by_engine in rec["values"].items():
        prim = by_engine.get(primary, {})
        for e in list(by_engine):
            if e != primary and prim:
                by_engine[e] = {k: v for k, v in by_engine[e].items() if differs(v, prim.get(k))}
    # the agreement entry is the catalogue's: an amplifier job's measurements are the `opamp` kind's
    kind = PLANNED_KINDS.get(j0["kind"], (j0["kind"],))[0]
    if rec["agree"]:
        n_all = len(rec["agree"])
        within1 = sum(1 for a in rec["agree"].values() if a[1] == "1%")
        within5 = sum(1 for a in rec["agree"].values() if a[1] in ("1%", "5%"))
        odd = Counter(a[3] for a in rec["agree"].values() if a[3])
        rec["values"][f"{kind}-agreement"] = {"all": {
            "agree_1pct": sig(within1 / n_all), "agree_5pct": sig(within5 / n_all),
            "odd_engine": odd.most_common(1)[0][0] if odd else None,
            "disagreeing": sorted(m for m, a in rec["agree"].items() if a[1] == ">5%")}}
        rec["codes"][f"{kind}-agreement"] = "ok"
    else:
        rec["codes"][f"{kind}-agreement"] = "n/a"
    return rec


def write(h: str, rec: dict) -> bool:
    p = character(h)
    text = json.dumps(rec, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    if p.exists() and p.read_text(encoding="utf-8") == text:
        return False
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=f".{p.name}.")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, p)
    return True


def publish() -> Counter:
    doc = catalogue.load()
    per_hash: dict[str, dict[str, tuple[dict, dict, dict]]] = {}
    c: Counter = Counter()
    for e in ENGINES:
        # every run of this catalogue version, newest first: a model takes its newest result, so that a rerun
        # of the models a run missed completes it instead of replacing it
        got = 0
        for d in runs_of(e):
            info, results, jobs = load_run(d)
            if info.get("catalogue", {}).get("version") != doc["version"]:
                continue
            for h, r in results.items():
                if h in jobs and e not in per_hash.get(h, {}):
                    per_hash.setdefault(h, {})[e] = (info, r, jobs[h])
                    got += 1
        if got:
            c[f"{e} results"] += got
        else:
            c[f"{e}: no run of this catalogue version"] += 1
    led = ledger()
    dig = input_digest()
    for h, per_engine in sorted(per_hash.items()):
        rec = build_record(h, per_engine, doc)
        c["written" if write(h, rec) else "unchanged"] += 1
        c["models"] += 1
        led.stamp(h, "character", version=VERSION, when=today(), character_in=dig, engines=",".join(sorted(per_engine)))
    led.save()
    return c


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.parse_args(argv)
    c = publish()
    print(f"{c['models']:,} models published ({c['written']:,} written, {c['unchanged']:,} unchanged); "
          + ", ".join(f"{k}: {v:,}" for k, v in c.items() if k.endswith("results") or "not published" in k))
    print(f"changes a card may carry: {', '.join(CHANGES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
