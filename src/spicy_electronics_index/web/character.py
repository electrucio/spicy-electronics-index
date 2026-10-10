"""The characterisation on the site: the method page's data, and each part's models' records joined to
the page's list of models.

The method page (`?bench=`) is the catalogue itself (`data/bench/measurements.yaml`) plus which circuit
drawings exist. A part's file (`character/<PART>.json`, fetched when the fold is opened) holds, by the
model's place in the page's list, the published record of its hash: values per measurement and engine,
codes, the primary engine's curves, the agreement between engines, the deck digests. Nothing is judged
here; the page shows numbers and the reader compares.
"""
from __future__ import annotations

import json
from pathlib import Path

from spicy_electronics_index.bench import catalogue, record
from spicy_electronics_index.bench.catalogue import ENGINES
from spicy_electronics_index.core.config import bench_drawings, character
from spicy_electronics_index.models import cards as C

KEEP = ("hash", "polarity", "runs", "codes", "values", "derived", "curves", "other_curves", "agree", "decks", "changes", "errors")
FACTS = ("family", "absent", "why", "default", "extensions", "geometry", "thermal_pin", "dialect", "ratings")


def facts(card: dict | None, claims: dict | None) -> dict:
    """What the page lists for a model before any simulation: what its card lacks or leaves at a default,
    the extensions it carries, how the simulators read it, what its author declares."""
    out: dict = {}
    if card:
        out.update({k: card[k] for k in FACTS if card.get(k)})
    if claims:
        out["claims"] = {k: claims[k] for k in ("yes", "no", "limits", "simulator", "lines", "scope") if k in claims}
    return out


def attach_facts(recipe: dict, trimmed: dict) -> None:
    """Give each model of the page its card facts (`chk`), from the part's verification record."""
    rec = record.load(recipe.get("kind", ""), recipe.get("part", ""))
    cards, claims = rec.get("cards", {}), rec.get("claims", {})
    for m, t in zip(recipe.get("models") or [], trimmed.get("models") or []):
        h = m.get("hash")
        f = facts(cards.get(h), claims.get(h)) if h else {}
        if f:
            t["chk"] = f


# what a checked card parameter stands for, as the models table names the physics a card lacks
PHYSICS = {"VAF": "Early", "IKF": "high current", "ISE": "low current", "RB": "RB", "RE": "RE", "RC": "RC",
           "CJE": "CJE", "CJC": "CJC", "TF": "fT", "XTF": "fT roll-off", "TR": "storage", "XTB": "hFE(T)",
           "KF": "1/f noise", "LAMBDA": "output conductance", "CGS": "CGS", "CGD": "CGD", "TT": "recovery",
           "BV": "breakdown", "VTOTC": "VTO(T)", "BETATCE": "BETA(T)"}
# a dialect flag that is an artefact, not a dialect: the model does something no transistor does
ARTEFACTS = {"nk-above-1": "IC ceiling (NK > 1)", "nr-above-nf": "negative VCE(sat) (NR > NF)"}


def bench_summary(rec: dict | None, card: dict | None) -> dict | None:
    """What the bench and the card say of a model before any data sheet is looked at: what each engine made
    of it, how much of its family's physics the card carries, how far the engines agree, what went wrong,
    what it costs. Facts a reader can weigh; no score.

    `sims` answers "will it work in mine?" per simulator tried, in the bench's order: `ok`, `failed`, or
    `differs` for the one whose results stand apart from the other two by more than 5 % — which takes three
    to say. A simulator the model was never run in is left out."""
    if not rec and not card:
        return None
    out: dict = {}
    flags: list[str] = []
    if card:
        checked = C.CHECKED.get(card.get("family", ""), ())
        absent = [p for p in card.get("absent") or [] if p in checked]
        out["covers"] = [len(checked) - len(absent), len(checked)]
        out["missing"] = [PHYSICS.get(p, p) for p in absent]
        if card.get("default"):
            out["defaults"] = list(card["default"])          # there, but left at the simulator's own value
        if card.get("extensions"):
            out["extensions"] = list(card["extensions"])    # physics beyond the family's own
        out["artefacts"] = [ARTEFACTS[d] for d in card.get("dialect") or [] if d in ARTEFACTS]
        flags += out["artefacts"]
    if rec:
        runs = rec.get("runs") or {}
        primary = rec.get("primary")
        odd = None
        for mid, by in (rec.get("values") or {}).items():
            if mid.endswith("-agreement") and isinstance(by.get("all"), dict) and by["all"].get("agree_1pct") is not None:
                out["agree"] = by["all"]["agree_1pct"]
                odd = by["all"].get("odd_engine")
                if by["all"].get("disagreeing"):
                    out["differs_on"] = len(by["all"]["disagreeing"])
        out["sims"] = {e: ("failed" if runs[e] != "ok" else "differs" if e == odd else "ok")
                       for e in (*ENGINES, *sorted(set(runs) - set(ENGINES))) if e in runs}
        codes = rec.get("codes") or {}
        for code in ("suspect", "failed"):
            n = sum(1 for c in codes.values() if c == code)
            if n:
                flags.append(f"{code} ×{n}")
        for mid, by in (rec.get("errors") or {}).items():
            for e, txt in by.items():
                if "timeout" in txt:
                    flags.append(f"{e}: timeout in {mid.split('-', 1)[-1]}")
        cpu = ((rec.get("engines") or {}).get(primary) or {}).get("cpu_s")
        if cpu is not None:
            out["cpu_s"] = cpu
    out["flags"] = flags
    return out


def rank_key(b: dict | None, i: int) -> tuple:
    """Best first by what the card can model: more of the family's physics with effect, fewer parameters left
    at the simulator's default, more extensions beyond the family, no artefact of the model itself (a
    collector current with a ceiling); the recipe's own order (most original first) among equals. What a
    particular simulator made of it — runs, agreement, timeouts, cost — is shown, not ranked."""
    if not b or "covers" not in b:
        return (1, 0, 0, 0, 0, i)
    return (0, -b["covers"][0], len(b.get("defaults") or []), -len(b.get("extensions") or []), len(b.get("artefacts") or []), i)


def ranked(recipe: dict) -> dict:
    """The recipe with its models in the bench's order (rank_key) and a `bench` block on each: what the
    part page's models table shows, and the order its numbers and colours follow."""
    models = list(recipe.get("models") or [])
    if not models:
        return recipe
    cards = record.load(recipe.get("kind", ""), recipe.get("part", "")).get("cards", {})
    keyed = []
    for i, m in enumerate(models):
        h = m.get("hash")
        b = bench_summary(record_of(h), cards.get(h)) if h else None
        keyed.append((rank_key(b, i), dict(m), b))
    keyed.sort(key=lambda t: t[0])
    out = []
    for r, (_, m, b) in enumerate(keyed, 1):
        m["bench"] = {**(b or {}), "rank": r}
        out.append(m)
    return {**recipe, "models": out}


def methods_payload() -> dict:
    """The catalogue for the method page and the part page's dialog, with the drawings that exist (an id, and
    `<id>-pnp` for its PNP twin) and each entry's deck lines as the PNP deck writes them."""
    # imported here: it imports the image's decks from the checkout
    from spicy_electronics_index.bench.deck import pnp_directives  # noqa: PLC0415

    doc = catalogue.site()
    doc["drawings"] = [p.stem for p in drawing_files()]
    for m in doc["measurements"]:
        if m.get("directives") and m["kind"] == "bjt":
            m["directives_pnp"] = pnp_directives(m)
    return doc


def drawing_files() -> list[Path]:
    d = bench_drawings()
    return sorted(d.glob("*.svg")) if d.exists() else []


def record_of(model_hash: str | None) -> dict | None:
    if not model_hash:
        return None
    p = character(model_hash)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def model_payload(rec: dict) -> dict:
    """One model's characterisation as the site serves it, once per model whatever the parts that list it
    (`character/m/<hash>.json.gz`): a model listed under sixty parts would otherwise be copied sixty times."""
    return {k: rec[k] for k in KEEP if k in rec}


def part_payload(recipe: dict) -> dict | None:
    """The part's index of characterised models, by their place in the page's list: each model's hash and
    polarity; the records themselves are fetched one file per model."""
    models: dict[str, dict] = {}
    engines: dict[str, dict] = {}
    primary, version = None, None
    for i, m in enumerate(recipe.get("models") or []):
        rec = record_of(m.get("hash"))
        if not rec:
            continue
        models[str(i)] = {"hash": rec["hash"], "polarity": rec.get("polarity")}
        for e, info in rec.get("engines", {}).items():
            engines.setdefault(e, info)
        primary = primary or rec.get("primary")
        version = version or rec.get("catalogue")
    if not models:
        return None
    return {"catalogue": version, "primary": primary, "engines": engines, "models": models}


def summary(payload: dict | None) -> dict | None:
    """What the fold's summary says before the file is fetched: how many models, how many measurements."""
    if not payload:
        return None
    mids = {mid for mo in payload["models"].values() for mid in ((record_of(mo.get("hash")) or {}).get("codes") or {})}
    return {"n": len(payload["models"]), "m": len(mids)}
