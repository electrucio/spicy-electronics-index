"""How the models of a part are related to each other, and to models of other parts, by their cards.

    sei models kinship

Two cards can be the same model (identical code, which `models found` already merges under one hash),
the same physics with a different fit (the same parameter names, other values), a copy with a couple of
numbers changed, or two cards that share one block of values. The last is the interesting one: libraries
written from a template carry the same dynamic parameters (CJE, CJC, TF, TR and their grading) across
dozens of unrelated parts, and a model whose capacitances are a template's says nothing about its part's
capacitances however good its DC fit. So, per model: a fingerprint of its parameter names, which other
models of the part share it, which other models of the part it differs from by at most two values, and
whether its dynamic block is a template seen under other parts, with how many.

Only fingerprints, hashes and counts are published, never a parameter's value (CLAUDE.md rule 2).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict

from spicy_electronics_index.bench import record
from spicy_electronics_index.core.config import require, spice_models_root, spice_recipe_locations
from spicy_electronics_index.models import behaviours
from spicy_electronics_index.models import cards as C
from spicy_electronics_index.models import found as F

VERSION = "kin-1"
# The dynamic block a template shows in: a card with at least three of these, all equal to another
# part's card, was written from the same template (or from the same measurement, which no library says).
DYNAMIC = ("CJE", "CJC", "TF", "TR", "VJE", "VJC", "MJE", "MJC", "CGS", "CGD", "CGDMAX", "CGDMIN", "CJO", "TT")
NEAR = 2            # a card that differs from another in at most this many values is "derived"
TEMPLATE_MIN = 3    # dynamic parameters a block needs before it counts as a template


def signature(params: dict[str, str]) -> tuple[str, frozenset, str | None]:
    """(names fingerprint, the (name, value) pairs, the dynamic block's fingerprint or None)."""
    pairs = frozenset((k, F.value(C.AMPERE_UNIT.sub("", v))) for k, v in params.items() if k not in C.CATALOGUE)
    names = hashlib.sha1(" ".join(sorted(k for k, _ in pairs)).encode()).hexdigest()[:8]
    dyn = sorted((k, v) for k, v in pairs if k in DYNAMIC)
    block = hashlib.sha1(json.dumps(dyn).encode()).hexdigest()[:6] if len(dyn) >= TEMPLATE_MIN else None
    return names, pairs, block


def compute(cards: dict[str, dict[str, dict[str, str]]]) -> dict[str, dict[str, dict]]:
    """`{part key: {hash: params}}` → `{part key: {hash: kin}}`. Pure, so it is tested on invented cards."""
    sigs = {key: {h: signature(p) for h, p in hs.items()} for key, hs in cards.items()}
    parts_of_block: dict[str, set[str]] = defaultdict(set)
    for key, hs in sigs.items():
        for _, _, block in hs.values():
            if block:
                parts_of_block[block].add(key)
    out: dict[str, dict[str, dict]] = {}
    for key, hs in sigs.items():
        out[key] = {}
        for h, (names, pairs, block) in hs.items():
            kin: dict = {"params": names}
            same = sorted(o for o, (n2, _, _) in hs.items() if o != h and n2 == names)
            if same:
                kin["same_parameters"] = same
            derived = sorted(o for o, (_, p2, _) in hs.items()
                             if o != h and len(pairs ^ p2) <= 2 * NEAR and len(pairs ^ p2) > 0
                             and {k for k, _ in pairs} == {k for k, _ in p2})
            if derived:
                kin["derived_from_or_to"] = derived
            others = parts_of_block.get(block, set()) - {key} if block else set()
            if others:
                kin["template"] = f"t-{block}"
                kin["template_parts"] = len(others)
            out[key][h] = kin
    return out


def run(only_kind: str | None = None) -> Counter:
    locations = json.loads(require(spice_recipe_locations(), "reading the recipes' cards").read_text(encoding="utf-8"))
    files = F.Files(spice_models_root())
    cards: dict[str, dict[str, dict[str, str]]] = {}
    c: Counter = Counter()
    for key, models in sorted(locations.items()):
        kind = key.split("/", 1)[0]
        if behaviours.group(kind) not in ("bjt", "jfet", "diode", "mosfet") or (only_kind and kind != only_kind):
            continue
        for m in models:
            if not m["hash"] or not m["file"].startswith("sources/"):
                continue
            try:
                chain = F.closure(files.get(m["file"])[0], m["name"])
            except OSError:
                continue
            if not chain or chain[-1][0] != "model":
                continue
            parsed = C.card_params(chain[-1][2])
            if parsed and not parsed[1]:
                cards.setdefault(key, {})[m["hash"]] = parsed[2]
    kin = compute(cards)
    everything = record.digest(sorted((k, sorted(hs)) for k, hs in cards.items()))
    led = record.ledger()
    for key, by_hash in sorted(kin.items()):
        kind, part = key.split("/", 1)
        dig = record.digest([sorted(by_hash), everything])
        if led.fresh(key, "kin", VERSION, dig):
            c["fresh"] += 1
            continue
        published = {h: k for h, k in by_hash.items() if len(k) > 1}      # a bare fingerprint says nothing
        c["written" if record.write_section(kind, part, "kin", published) else "unchanged"] += 1
        c["templates"] += sum(1 for k in by_hash.values() if "template" in k)
        c["derived"] += sum(1 for k in by_hash.values() if "derived_from_or_to" in k)
        c["same parameters"] += sum(1 for k in by_hash.values() if "same_parameters" in k)
        led.stamp(key, "kin", version=VERSION, kin_in=dig)
    led.save()
    c["models"] = sum(len(hs) for hs in cards.values())
    return c


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--kind", help="only one kind")
    a = ap.parse_args(argv)
    c = run(a.kind)
    print(f"{c['models']:,} cards read; {c['written']:,} parts written, {c['unchanged']:,} unchanged, "
          f"{c['fresh']:,} already done")
    print(f"models whose dynamic block is a template seen under other parts: {c['templates']:,}; "
          f"with the same parameter names as another model of the part: {c['same parameters']:,}; "
          f"differing from another by at most {NEAR} values: {c['derived']:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
