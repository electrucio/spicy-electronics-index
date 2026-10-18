"""The measurement catalogue: what the bench measures of every transistor model, how, and what each
number tells — read from `data/bench/measurements.yaml`, checked, and rendered for the method page.

    sei bench methods              # counts per kind and group, and anything wrong with the catalogue
    sei bench methods --markdown   # the catalogue as the docs print it
    sei bench methods --write      # rewrite the generated section of docs/model-characterisation.md

One entry per measurement id. The decks inside the simulator images read their conditions from the
entry, the site's method page shows its text, and every published number carries the id and the
catalogue's version: the method described, the method run and the method a reader is pointed at are
one thing. `problems()` is what the tests run; `markdown()` and `site()` are the two renderings.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from functools import lru_cache
from pathlib import Path

import yaml

from spicy_electronics_index.core.config import bench_measurements, docs_dir
from spicy_electronics_index.models import behaviours

KINDS = ("bjt", "jfet", "mosfet", "opamp")
ENGINES = ("qspice", "ngspice", "ltspice")
ANALYSES = ("op", "dc", "ac", "tran", "noise", "derived")
CODES = ("ok", "absent", "n/a", "failed", "suspect")
REQUIRED = ("id", "kind", "group", "name", "symbols", "what", "circuit", "drawing", "analysis", "conditions",
            "extraction", "outputs", "parameters", "reads_high", "reads_low", "cannot_tell", "standard", "pack",
            "engines")
RX_ID = re.compile(r"^(bjt|jfet|mosfet|opamp)-[a-z0-9]+(-[a-z0-9]+)*$")
RX_VERSION = re.compile(r"^m-\d+$")
RX_KEY = re.compile(r"^[a-z][a-z0-9_]*(@[^\s@]+)?$")
RX_PARAM = re.compile(r"^[A-Z][A-Z0-9_]*$")
CURVE_KEYS = {"name", "x", "y", "scale", "unit", "x_unit", "at", "grid", "k"}
# what a chart may compute for the point under the cursor: [term, op, term] over the point (x, y), the local
# slope (dx, dy, from the neighbouring points), the trace's base current (ib) and the curve's conditions (at.<selector>)
HOVER_TERMS = {"x", "y", "dx", "dy", "ib"}
HOVER_OPS = {"*", "/"}
# YAML 1.1 reads 1.0e5 as text (the exponent needs a sign); a condition that is text breaks every deck
RX_NUMBER_TEXT = re.compile(r"^[-+]?[0-9.]+e[-+]?[0-9]+$", re.I)
# A model card's text never belongs in the catalogue (CLAUDE.md rule 1; scripts/licence_guard.py).
RX_MODEL_TEXT = re.compile(r"^\s*\.(model|subckt)\b", re.I | re.M)
MARK_START, MARK_END = "<!-- measurements:start -->", "<!-- measurements:end -->"
DOC = "model-characterisation.md"
# the document each kind's entries are printed in; the first one also carries the codes and the uses
DOCS = {"bjt": DOC, "jfet": "fet-characterisation.md", "mosfet": "fet-characterisation.md", "opamp": "opamp-characterisation.md"}
KIND_NAMES = {"bjt": "Bipolar transistors", "jfet": "JFETs", "mosfet": "MOSFETs", "opamp": "Op-amps"}


@lru_cache(maxsize=4)
def _read(path: str) -> tuple[str, dict]:
    text = Path(path).read_text(encoding="utf-8")
    return text, yaml.safe_load(text)


def load(path: Path | None = None) -> dict:
    return _read(str(path or bench_measurements()))[1]


def text(path: Path | None = None) -> str:
    return _read(str(path or bench_measurements()))[0]


def digest(path: Path | None = None) -> str:
    """The sha256 of the catalogue file: part of every run's input fingerprint, so a changed catalogue
    reruns what it describes."""
    return hashlib.sha256(text(path).encode("utf-8")).hexdigest()


BENCH_KEYS = ("id", "kind", "analysis", "conditions", "grid", "curves", "pack", "engines")


def bench_digest(doc: dict | None = None) -> str:
    """The sha256 of what the decks read — conditions, grids, output keys, curves, engines — and nothing
    of the text: the prose can be improved without rerunning a simulation."""
    doc = doc or load()
    slim = {"version": doc["version"], "measurements": [
        {**{k: m.get(k) for k in BENCH_KEYS}, "outputs": [o["key"] for o in m["outputs"]]} for m in doc["measurements"]]}
    return hashlib.sha256(json.dumps(slim, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def version(doc: dict | None = None) -> str:
    return (doc or load())["version"]


def measurements(kind: str | None = None, doc: dict | None = None) -> list[dict]:
    ms = (doc or load())["measurements"]
    return [m for m in ms if kind is None or m["kind"] == kind]


def ids(kind: str | None = None, doc: dict | None = None) -> list[str]:
    return [m["id"] for m in measurements(kind, doc)]


def by_id(doc: dict | None = None) -> dict[str, dict]:
    return {m["id"]: m for m in measurements(None, doc)}


def problems(doc: dict | None = None, raw: str | None = None) -> list[str]:
    """Everything wrong with the catalogue, as messages; empty when it is sound."""
    doc = doc or load()
    raw = text() if raw is None else raw
    out: list[str] = []
    if not RX_VERSION.match(str(doc.get("version", ""))):
        out.append(f"version must be m-<n>, not {doc.get('version')!r}")
    if tuple(doc.get("codes", {})) != CODES:
        out.append(f"codes must be exactly {CODES}")
    if RX_MODEL_TEXT.search(raw):
        out.append("a line starts with .model or .subckt: no card text in the catalogue")
    for name, sel in (doc.get("selectors") or {}).items():
        if not isinstance(sel, dict) or "unit" not in sel or not sel.get("what"):
            out.append(f"selector {name!r} needs a unit and a what")
    for u in doc.get("uses", []):
        bad = set(u.get("groups", [])) - set(behaviours.BEHAVIOURS)
        if bad or not u.get("use") or not u.get("look_at"):
            out.append(f"use {u.get('use')!r}: unknown groups {sorted(bad)} or missing text")
    seen: set[str] = set()
    for m in doc.get("measurements", []):
        mid = m.get("id", "?")
        missing = [k for k in REQUIRED if k not in m]
        if missing:
            out.append(f"{mid}: missing {missing}")
            continue
        if not RX_ID.match(mid) or not mid.startswith(m["kind"] + "-"):
            out.append(f"{mid}: id must be <kind>-<words>, kind {m['kind']}")
        if mid in seen:
            out.append(f"{mid}: duplicate id")
        seen.add(mid)
        if m["kind"] not in KINDS:
            out.append(f"{mid}: kind {m['kind']!r} not in {KINDS}")
        if m["group"] not in behaviours.BEHAVIOURS:
            out.append(f"{mid}: group {m['group']!r} is not a behaviour")
        if m["analysis"] not in ANALYSES:
            out.append(f"{mid}: analysis {m['analysis']!r} not in {ANALYSES}")
        if not m["engines"] or set(m["engines"]) - set(ENGINES):
            out.append(f"{mid}: engines {m['engines']!r}")
        if not isinstance(m["pack"], bool) or not isinstance(m["conditions"], dict):
            out.append(f"{mid}: pack must be a boolean and conditions a mapping")
        keys: set[str] = set()
        for o in m["outputs"]:
            if not isinstance(o, dict) or not {"key", "unit", "what"} <= set(o) <= {"key", "unit", "what", "plotted"} \
                    or not RX_KEY.match(o["key"]):
                out.append(f"{mid}: output {o!r} needs key, unit and what")
                continue
            if o["key"] in keys:
                out.append(f"{mid}: output {o['key']} twice")
            keys.add(o["key"])
        if not keys:
            out.append(f"{mid}: no outputs")
        selectors = doc.get("selectors") or {}
        seen_at: dict[str, list] = {}
        for c in m.get("curves", []):
            if not isinstance(c, dict) or not {"name", "x", "y", "scale"} <= set(c) <= CURVE_KEYS or c["scale"] not in ("log", "lin"):
                out.append(f"{mid}: curve {c!r} needs name, x, y and a scale of log or lin ({', '.join(sorted(CURVE_KEYS - {'name', 'x', 'y', 'scale'}))} optional)")
                continue
            at = c.get("at") or {}
            if not isinstance(at, dict) or any(k not in selectors for k in at):
                out.append(f"{mid}: curve {c['name']!r} is taken at {at!r}: every key must be a selector")
            for k, v in (at.items() if isinstance(at, dict) else []):
                seen_at.setdefault(k, []).append(v)
            if "grid" in c and not (isinstance(c["grid"], dict) and c["grid"].get("x") == c["x"]):
                out.append(f"{mid}: curve {c['name']!r} has a grid whose x is not the curve's")
        for k, v in (m.get("select") or {}).items():
            if k not in seen_at or not (v == "all" or any(_same(v, w) for w in seen_at[k])):
                out.append(f"{mid}: select {k}: {v!r} is not a value any curve is taken at (nor 'all')")
        ys = {c.get("y") for c in m.get("curves") or [] if isinstance(c, dict)}
        for h in m.get("hover") or []:
            of = h.get("of") if isinstance(h, dict) else None
            terms = [of[0], of[2]] if isinstance(of, list) and len(of) == 3 else []
            good_terms = all(t in HOVER_TERMS or (isinstance(t, str) and t.startswith("at.") and t[3:] in selectors) for t in terms)
            if not (isinstance(h, dict) and {"y", "label", "unit", "of"} <= set(h) <= {"y", "label", "unit", "of", "what"}
                    and h["y"] in ys and terms and of[1] in HOVER_OPS and good_terms
                    and (("dx" in terms) == ("dy" in terms))):
                out.append(f"{mid}: hover {h!r} needs y (a curve's y), label, unit and of: [term, * or /, term] "
                           f"over {sorted(HOVER_TERMS)} or at.<selector>, dx with dy")
        ids = {x.get("id") for x in doc.get("measurements", [])}
        for nz in m.get("normalise") or []:
            by = nz.get("by") if isinstance(nz, dict) else None
            if not (isinstance(nz, dict) and set(nz) == {"y", "by", "label"} and nz["y"] in ys and isinstance(by, dict)
                    and by.get("id") in ids and isinstance(by.get("key"), str) and by["key"]):
                out.append(f"{mid}: normalise {nz!r} needs y (a curve's y), a label and by: {{id: a measurement, key: one of its values}}")
        for c in m.get("curves") or []:
            if isinstance(c, dict) and "k" in c and not (isinstance(c["k"], int) and c["k"] > 0 and m.get("family")):
                out.append(f"{mid}: curve {c.get('name')!r}: k is a family trace's multiple of the step, a positive integer")
        fam = m.get("family")
        if fam is not None and not (isinstance(fam, dict) and isinstance(fam.get("note"), str) and fam["note"].strip()
                                    and (fam.get("key") is None or fam["key"] in {o["key"] for o in m["outputs"]})):
            out.append(f"{mid}: family needs a note and, if a key, one of the outputs")
        why = (fam or {}).get("because")
        if why is not None and not (isinstance(why, dict) and {"id", "key", "label"} <= set(why) and "{value}" in str(why["label"])
                                    and why["id"] in {x.get("id") for x in doc.get("measurements", [])}):
            out.append(f"{mid}: family.because needs the id of a measurement, a key and a label with {{value}}")
        if any("grid" not in c for c in m.get("curves") or []) and not m.get("grid") and m["analysis"] not in ("tran", "noise"):
            out.append(f"{mid}: curves without a grid")
        d = m["drawing"]
        if set(d) != {"file", "elements", "differs_from_netlist"} or not all(isinstance(e, str) for e in d["elements"]):
            out.append(f"{mid}: drawing needs file, elements (texts: quote one with a comma) and differs_from_netlist")
        elif d["file"] and (not d["file"].startswith("bench/drawings/") or d["file"] != f"bench/drawings/{mid}.svg"):
            out.append(f"{mid}: drawing file must be bench/drawings/{mid}.svg")
        for where in ("conditions", "grid"):
            for path, val in _walk(m.get(where) or {}, where):
                if isinstance(val, str) and RX_NUMBER_TEXT.match(val):
                    out.append(f"{mid}: {path} is the text {val!r}, not a number: write the exponent with a sign (1.0e+5)")
        bad = [p for p in m["parameters"] if not RX_PARAM.match(p)]
        if bad:
            out.append(f"{mid}: parameters are upper-case names, not {bad}")
        if m["analysis"] != "derived" and not m["circuit"].strip():
            out.append(f"{mid}: a simulated measurement describes its circuit")
        lines = m.get("directives", [])
        if not isinstance(lines, list) or any(not isinstance(x, str) or not x.strip() for x in lines):
            out.append(f"{mid}: directives are a list of non-empty lines")
        elif any(RX_MODEL_TEXT.match(x) for x in lines):
            out.append(f"{mid}: a directive line is card text")
    return out


def _same(a, b) -> bool:
    """Two selector values are the same: numbers within a millionth, texts exactly."""
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        return abs(a - b) <= 1e-6 * max(abs(a), abs(b), 1e-300)
    return a == b


def _walk(obj, path):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk(v, f"{path}[{i}]")
    else:
        yield path, obj


# ------------------------------------------------------------------------------------------ renderings
def _scalar(v) -> str:
    if isinstance(v, float):
        return f"{v:.6g}"
    if isinstance(v, dict):
        return "{" + ", ".join(f"{k}: {_scalar(x)}" for k, x in v.items()) + "}"
    if isinstance(v, list):
        return "[" + ", ".join(_scalar(x) for x in v) + "]"
    return str(v)


def _para(s: str) -> str:
    return " ".join(str(s).split())


def markdown(doc: dict | None = None, kinds: tuple[str, ...] | None = None, head: bool = True) -> str:
    """The catalogue as the docs print it: one subsection per measurement, under one heading per kind; with
    `head`, the codes and the uses table first."""
    doc = doc or load()
    out = []
    if head:
        out += [f"Catalogue version `{doc['version']}`. Codes a number can be replaced by:", ""]
        out += [f"- `{k}` — {v}" for k, v in doc["codes"].items()]
        out += ["", "Which groups of measurements matter for which use:", "", "| use | groups | look at |", "|---|---|---|"]
        out += [f"| {u['use']} | {', '.join(u['groups'])} | {_para(u['look_at'])} |" for u in doc["uses"]]
    else:
        out += [f"Catalogue version `{doc['version']}`; the codes and the uses table are in [model-characterisation.md](model-characterisation.md)."]
    for kind in kinds or KINDS:
        ms = measurements(kind, doc)
        if not ms:
            continue
        out += ["", f"### {KIND_NAMES[kind]}", ""]
        for m in ms:
            out += [f"#### {m['name']} (`{m['id']}`)", ""]
            head = f"Group `{m['group']}` · analysis `{m['analysis']}` · engines {', '.join(m['engines'])}"
            if m["symbols"]:
                head += " · symbols " + ", ".join(m["symbols"])
            out += [head + ".", ""]
            out += [_para(m["what"]), ""]
            if m["circuit"].strip():
                out += ["**Circuit.** " + _para(m["circuit"]), ""]
                d = m["drawing"]
                if d.get("elements"):
                    line = "Drawing: " + "; ".join(d["elements"])
                    if d.get("differs_from_netlist") and d["differs_from_netlist"] != "nothing":
                        line += f". Differs from the netlist: {_para(d['differs_from_netlist'])}"
                    out += [line + ".", ""]
            out += ["**Conditions.** " + _scalar(m["conditions"]), ""]
            if m.get("directives"):
                out += ["**The deck (QSPICE), line by line.**", ""]
                says: list[str] = []
                for line in m["directives"]:
                    if line.startswith("*"):
                        says.append(line.lstrip("* "))
                    else:
                        out.append(f"- `{line}` — {' '.join(says)}" if says else f"- `{line}`")
                        says = []
                if says:
                    out.append("- " + " ".join(says))
                out.append("")
            out += ["**Extraction.** " + _para(m["extraction"]), ""]
            out += ["**Outputs.**", ""]
            out += [f"- `{o['key']}`" + (f" ({o['unit']})" if o["unit"] else "") + f": {_para(o['what'])}" for o in m["outputs"]]
            out += [""]
            if m.get("curves"):
                out += ["Curves: " + "; ".join(f"{c['name']} ({c['y']} against {c['x']}, {c['scale']}"
                                                + (", at " + ", ".join(f"{k} = {_scalar(v)}" for k, v in c["at"].items()) if c.get("at") else "") + ")"
                                                for c in m["curves"])
                        + (f". Drawn together, as a family: {m['family']['note']}" if m.get("family") else "")
                        + (". Shown first: " + ", ".join(f"{k} = {_scalar(v)}" for k, v in m["select"].items()) if m.get("select") else "") + ".", ""]
            if m.get("hover"):
                out += ["Beside the point under the cursor: " + "; ".join(
                    f"{h['label']}" + (f" ({h['unit']})" if h["unit"] else "") + f", {h.get('what') or ' '.join(map(str, h['of']))}"
                    for h in m["hover"]) + ".", ""]
            if m["parameters"]:
                out += ["**Card parameters that drive it:** " + ", ".join(m["parameters"]) + ".", ""]
            for label, key in (("A high value", "reads_high"), ("A low value", "reads_low"), ("What it cannot tell", "cannot_tell")):
                if str(m[key]).strip():
                    out += [f"**{label}.** " + _para(m[key]), ""]
            out += [f"**Standard.** {_para(m['standard'])}", ""]
    return "\n".join(out).rstrip() + "\n"


def site(doc: dict | None = None) -> dict:
    """What the method page needs: the whole catalogue, with the drawing file names it should look for."""
    doc = doc or load()
    return {"version": doc["version"], "codes": doc["codes"], "uses": doc["uses"], "selectors": doc.get("selectors") or {},
            "measurements": [{k: v for k, v in m.items()} for m in doc["measurements"]]}


def doc_files() -> dict[str, tuple[str, ...]]:
    """Each document and the kinds it prints, in the catalogue's order."""
    out: dict[str, tuple[str, ...]] = {}
    for kind in KINDS:
        out[DOCS[kind]] = out.get(DOCS[kind], ()) + (kind,)
    return out


def markdown_for(name: str, doc: dict | None = None) -> str:
    """What one document's generated section holds: its kinds, with the head in the first document only."""
    return markdown(doc, kinds=doc_files()[name], head=(name == DOC))


def write_doc(path: Path | None = None) -> bool:
    """Rewrite the generated section of each specification between its markers (a document without markers is
    left alone); True when any changed. With `path`, that one document."""
    changed = False
    for name in ([path.name] if path else doc_files()):
        p = path or docs_dir() / name
        old = p.read_text(encoding="utf-8")
        if MARK_START not in old:
            continue
        a, b = old.index(MARK_START) + len(MARK_START), old.index(MARK_END)
        new = old[:a] + "\n" + markdown_for(name) + old[b:]
        if new != old:
            p.write_text(new, encoding="utf-8")
            changed = True
    return changed


def generated_section(path: Path | None = None) -> str:
    path = path or docs_dir() / DOC
    s = path.read_text(encoding="utf-8")
    return s[s.index(MARK_START) + len(MARK_START):s.index(MARK_END)].strip("\n") + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--markdown", action="store_true", help="print the catalogue as the docs print it")
    ap.add_argument("--write", action="store_true", help=f"rewrite the generated section of docs/{DOC}")
    a = ap.parse_args(argv)
    bad = problems()
    for p in bad:
        print("problem: " + p, file=sys.stderr)
    if bad:
        return 1
    if a.markdown:
        print(markdown(), end="")
        return 0
    if a.write:
        print(", ".join(f"docs/{name}" for name in doc_files()) + ": " + ("rewritten" if write_doc() else "unchanged"))
        return 0
    doc = load()
    for kind in KINDS:
        ms = measurements(kind, doc)
        if ms:
            groups = sorted({m["group"] for m in ms})
            print(f"{kind}: {len(ms)} measurements, {sum(len(m['outputs']) for m in ms)} outputs; groups {', '.join(groups)}")
    print(f"version {doc['version']}, sha256 {digest()[:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
