"""The page number printed on a scanned page, where the scan's own number would mislead.

    sei schematics printed-pages [--source books] [--dry]

A page link opens the scan at its leaf, and the site labelled it with the leaf's number. In a book that
is not the page a reader cites: The Art of Electronics' leaf 656 is printed page 623, its 33 pages of
front matter in between — a reader checking the index against the book found exactly that offset
(2026-11-02). The link was right; the label was not.

Internet Archive reads the number printed on every leaf of an item it serves as a book and publishes it
beside the scan, as `<file>_page_numbers.json`: per leaf, the number it read and how sure it is. That is
a source anyone can open, so it is the one used here, for every document of a source served from
archive.org whose page links name a leaf (`/page/n655`). A leaf it read no number on takes one only when
the leaves read on either side agree on the offset — the run is unbroken, so the page between belongs to
it. Anything else stays unnumbered and keeps the scan's label. A link that is a search (`?q=`, the
borrowable books) names no leaf and is left alone.

Written to `data/schematics/printed_pages.csv`, one row per published page: the number, how it was had
(`read` off the leaf, or `between` two that were), and where the numbers are. A document already in the
file is not asked again unless it has pages the file lacks, or `VERSION` changes.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from urllib.parse import quote

from spicy_electronics_index.core import http
from spicy_electronics_index.core.config import (
    schematics_documents,
    schematics_pages,
    schematics_printed_pages,
)

VERSION = "ia-page-numbers-1"
FIELDS = ("source", "key", "page", "printed", "how", "numbers", "version")
ITEM = re.compile(r"^https?://archive\.org/details/([^/?#]+)")
LEAF = re.compile(r"/page/n(\d+)")
ARABIC = re.compile(r"^\d+$")
MIN_CONFIDENCE = 50          # Internet Archive's own score for an item's numbering; below it, nothing is taken
DELAY = 2.0                  # seconds between two requests to archive.org


def numbered(pages: list[dict]) -> dict[int, tuple[str, str]]:
    """leaf -> (printed number, how) from an item's `pages` list. Numbers read off the leaf as they are;
    an unread leaf takes the arabic number its neighbours imply when both agree on the offset."""
    read = {int(p["leafNum"]): str(p.get("pageNumber") or "").strip() for p in pages}
    out = {leaf: (n, "read") for leaf, n in read.items() if n}
    arabic = sorted(leaf for leaf, n in read.items() if ARABIC.match(n))
    for a, b in zip(arabic, arabic[1:]):
        if b - a > 1 and int(read[b]) - int(read[a]) == b - a:
            for leaf in range(a + 1, b):
                out.setdefault(leaf, (str(int(read[a]) + leaf - a), "between"))
    return out


def leaves(source: str) -> dict[str, dict[str, int]]:
    """Per archive.org item of the source: its document key -> {published page: leaf}."""
    docs = {r["id"]: r for r in csv.DictReader(open(schematics_documents(source), encoding="utf-8"))}
    out: dict[str, dict[str, int]] = {}
    for r in csv.DictReader(open(schematics_pages(source), encoding="utf-8")):
        d = docs.get(r["doc"])
        m = LEAF.search(r.get("url", ""))
        if d and m and ITEM.match(d.get("url", "")):
            out.setdefault(d["key"], {})[r["page"]] = int(m.group(1))
    return out


def ask(item: str) -> tuple[str, dict] | None:
    """(the address of the item's page numbers, the numbers) or None when it has none worth taking."""
    r = http.get(f"https://archive.org/metadata/{item}", delay=DELAY)
    if not r.ok:
        return None
    files = [f["name"] for f in json.loads(r.body).get("files", [])]
    name = next((f for f in files if f.endswith("_page_numbers.json")), None)
    if not name:
        return None
    url = f"https://archive.org/download/{item}/{quote(name)}"
    r = http.get(url, delay=DELAY)
    if not r.ok:
        return None
    data = json.loads(r.body)
    return (url, data) if (data.get("confidence") or 0) >= MIN_CONFIDENCE else None


def load() -> list[dict]:
    f = schematics_printed_pages()
    return list(csv.DictReader(open(f, encoding="utf-8"))) if f.exists() else []


def run(source: str, dry: bool = False) -> dict:
    """Number the source's leaf-linked pages. Every page asked about gets a row, an empty `printed` when
    no number was had, so that a run asks archive.org only about what the file has not seen."""
    have = load()
    rows = [r for r in have if r["source"] != source]
    kept: dict[str, list[dict]] = {}
    for r in have:
        if r["source"] == source:
            kept.setdefault(r["key"], []).append(r)
    counts = {"documents": 0, "asked": 0, "pages": 0, "numbered": 0, "none": 0}
    for key, pages in sorted(leaves(source).items()):
        counts["documents"] += 1
        counts["pages"] += len(pages)
        old = kept.get(key, [])
        if old and all(r["version"] == VERSION for r in old) and set(pages) <= {r["page"] for r in old}:
            rows += old
            counts["numbered"] += sum(1 for r in old if r["printed"])
            continue
        counts["asked"] += 1
        got = ask(ITEM.match(key).group(1))
        url, nums = (got[0], numbered(got[1].get("pages") or [])) if got else ("", {})
        counts["none"] += not nums
        for page, leaf in sorted(pages.items(), key=lambda kv: int(kv[0])):
            printed, how = nums.get(leaf, ("", "unread" if nums else "no numbers"))
            rows.append({"source": source, "key": key, "page": page, "printed": printed, "how": how,
                         "numbers": url, "version": VERSION})
            counts["numbered"] += bool(printed)
    if not dry:
        rows.sort(key=lambda r: (r["source"], r["key"], int(r["page"])))
        with open(schematics_printed_pages(), "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows)
    return counts


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--source", action="append", help="only these sources (default: books)")
    ap.add_argument("--dry", action="store_true", help="ask and count, write nothing")
    args = ap.parse_args(argv)
    for source in args.source or ["books"]:
        c = run(source, args.dry)
        print(f"{source}: {c['numbered']:,} of {c['pages']:,} leaf-linked pages numbered, in {c['documents']} documents"
              f" ({c['asked']} asked, {c['none']} without numbers)" + (" — dry run, nothing written" if args.dry else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
