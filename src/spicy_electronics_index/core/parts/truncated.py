"""Part numbers the OCR cut short: 2N390 for 2N3904, 1N414 for 1N4148, 2SC181 for 2SC1815.

    sei parts truncations [--dry]

A strict numbering scheme makes every number inside it look real. 2N390 is as well-formed a JEDEC number
as 2N3904, so the extractor took it at full confidence, and a Bose L1 power supply was published with a
2N390 for its Q50 — a reader found it in a first look at the site (2026-11-02). Measured on that export,
2N390 was on 28 documents and the four-digit numbers it is the start of on 4,509; 1N414 on 152 beside
1N4148 on 13,242; 1N400 on 169 beside the 1N4001 to 1N4007 on 16,933. The summariser had already said
"OCR error for 2N3904" on a third of 2N390's pages, which hid those pages and left the rest.

The page alone cannot tell: a Q50 labelled 2N390 is a well-formed label. The corpus can. A number that no
list of real parts holds, and whose one-digit-longer numbers are printed at least `RATIO` times as often,
is read here as cut short, and the extractor drops it — rule 4: a doubtful read is dropped, never guessed
into one of the longer ones. Real short numbers keep theirs: 2N404, 1N34, 2SK30 and 2SB56 are in the
dictionary or the census, 1N91 has a curated model, a repair shop's stock list in `wanted.csv` sells 2N555
as a germanium TO-3, and 2N107 or 2N1302 are not twenty times rarer than anything one digit longer.

Judged once, with the evidence, and committed in `data/parts/truncated.csv`: what is measured is the
export the list was made from, and a number once listed stays listed, since the next export will not
hold it. Adding the number to the dictionary (`known_parts.csv`) is how a listed one comes back.
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import date

from spicy_electronics_index.core.config import models_dir, schematics_parts, truncated_parts, wanted_parts

FIELDS = ("name", "documents", "longer", "longer_documents", "measured")
RATIO = 20            # how many times as often the longer numbers must be printed
LONGER_SHOWN = 3      # the longer numbers named as evidence, the most printed first


def load() -> dict[str, dict]:
    """The committed list, by name. Empty when there is none."""
    f = truncated_parts()
    if not f.exists():
        return {}
    return {r["name"]: r for r in csv.DictReader(open(f, encoding="utf-8"))}


def vouched() -> set[str]:
    """The numbers a list beside the extractor's own holds: a curated model recipe, or a wanted list that
    names its source."""
    held = {p.stem for p in (models_dir() / "parts").glob("*/*.yaml")}
    if wanted_parts().exists():
        held |= {r["part"] for r in csv.DictReader(open(wanted_parts(), encoding="utf-8"))}
    return held


def measure(documents: dict[str, int], listed, scheme, ratio: int = RATIO, today: str | None = None) -> list[dict]:
    """The numbers in `documents` (part -> documents printing it) that read as cut short.

    `listed(part)`: a list of real parts holds it. `scheme(part)`: it is a number of a strict scheme,
    where a shorter number is as well-formed as a longer one."""
    today = today or date.today().isoformat()
    out = []
    for part, n in documents.items():
        if not part[-1:].isdigit() or not scheme(part) or listed(part):
            continue
        longer = sorted(((part + d, documents[part + d]) for d in "0123456789" if part + d in documents),
                        key=lambda kv: (-kv[1], kv[0]))
        total = sum(k for _, k in longer)
        if longer and total >= ratio * n:
            out.append({"name": part, "documents": n, "longer": " ".join(p for p, _ in longer[:LONGER_SHOWN]),
                        "longer_documents": total, "measured": today})
    return out


def merged(old: dict[str, dict], new: list[dict]) -> list[dict]:
    """The list as committed, with the newly measured names added; an old entry is never re-measured."""
    rows = dict(old)
    for r in new:
        rows.setdefault(r["name"], r)
    return sorted(rows.values(), key=lambda r: r["name"])


def main(argv=None) -> int:
    from spicy_electronics_index.core.parts import extractor as x

    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dry", action="store_true", help="say what would be added and write nothing")
    args = ap.parse_args(argv)
    documents = {r["part"]: int(r["documents"]) for r in csv.DictReader(open(schematics_parts(), encoding="utf-8"))}
    old = load()
    held = vouched()
    new = measure(documents, lambda p: p in held or x._listed(p) or x._listed(x.base_part(p)),
                  lambda p: bool((f := x.family_of(p)) and f[2]))
    added = [r for r in new if r["name"] not in old]
    for r in sorted(added, key=lambda r: -int(r["documents"]))[:20]:
        print(f"  {r['name']:<10} {r['documents']:>5} documents; {r['longer']} on {r['longer_documents']:,}")
    print(f"{len(added)} added to the {len(old)} already listed"
          f" ({sum(int(r['documents']) for r in added):,} documents)" + (" — dry run, nothing written" if args.dry else ""))
    if not args.dry:
        rows = merged(old, new)
        with open(truncated_parts(), "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
