"""The Projects tab's data: every document the site shows, as a unit holding its parts.

    find/units.json.gz   what a query reads: each unit's parts, the kinds of use, facets, role and date
    find/docs.json.gz    what a result shows: title, link, source and the other copies
    find/w/<xx>.json.gz  which units each word of the summaries is on, split by the word's first letters

A part page answers "where is this part used". The Projects tab asks it the other way round — which
documents use these parts together, and none of those — so it needs each document's parts in one place, and
they have to be the documents the part pages show. Everything comes from `idx["uses"]`, which has already
left out what was withdrawn, what `summarise` read as not a part at all, the sources the site does not show
and the repositories that are gone.

What a unit is. A document, with the copies of one file in several archives as one unit, the way a part page
shows them. A magazine issue or a book is a unit per page, because one issue prints a dozen projects and two
parts in one issue are not two parts in one circuit. A figure a page of the same site holds is a unit with
that page. A design on GitHub is a unit per file, an Eagle board and its schematic of the same name one unit:
a folder can hold twenty unrelated modules (GroundGrown/eurorack-modules), so a folder is not a design.

Parts are positions in `parts.json`, as in `usages.json`, and both files carry the stamps of the lists they
name: a browser holding one build's index and another's finder asks again rather than misread them.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
from collections import defaultdict

import yaml

from spicy_electronics_index.core.config import schematics_registry
from spicy_electronics_index.core.parts import catalogue
from spicy_electronics_index.core.words import shard_of, words
from spicy_electronics_index.web.parts import (
    REPO_HOST,
    facet_of,
    issue_date,
    kin_names,
    kin_names_steps,
)

SCHEMA = 1
# Roles whose documents are a unit per page.
PAGED = frozenset(("issue", "book"))
# The roles a unit can have, in the order the site's "type of document" filter offers them.
ROLES = ("schematic", "project_page", "article", "figure", "service_manual", "issue", "book")
# The kinds of use `summarise` reads, as bits of a unit's mask; the next bit is a use not summarised yet.
KINDS = ("project", "technique", "reference", "mention", "advert")
NOT_SUMMARISED = 1 << len(KINDS)
# A use that names the part without using it: an alternative in the text, an advert.
NAMED_ONLY = frozenset(("mention", "advert"))
# The families a reader may leave out. A family is offered only when what files parts under it can be
# trusted to say no: logic and the BBD family are not, because the shape of a number files CD4013BE under
# processing and CD4013 under logic, and a reader who left out one would still get the other.
NEGATIVE = ("opamp", "comparator", "jfet", "mosfet", "fet", "bjt", "transistor", "tube", "diode")
# What a kin step is called, as the browser reads it (`kin_names`): the ones that are the same part.
SAME_PART = frozenset(("maker's name", "envelope"))
# Flags of a unit.
SCHEMATIC = 1        # a page of it is a circuit drawing
AFTER = 2            # it is the page after the unit before it, in the same document
# A word on more than this share of the units ("amplifier", "stage") finds nothing worth finding: it is left out
# of the word index, and the page says so when a reader types it.
COMMON = 0.25
# A split of the word index bigger than this, gzipped, is split again by the word's first three letters.
SHARD_BYTES = 150_000


def eras() -> dict[str, str]:
    """Each source's era (vintage, modern, mixed) as the registry gives it."""
    reg = schematics_registry()
    entries = (yaml.safe_load(reg.read_text(encoding="utf-8")) or {}) if reg.exists() else {}
    return {k: (v or {}).get("era", "") for k, v in entries.items()}


def design_of(url: str) -> str:
    """`owner/repo/path/name` of a file on GitHub, without its extension: what makes a board and its
    schematic one design."""
    p = url.split("/")
    return os.path.splitext("/".join(p[3:5] + p[7:]))[0].lower() if len(p) > 7 else url.lower()


def unit_key(si: int, doc_id: str, page: str, docs: dict) -> tuple[tuple, str, int]:
    """The unit a use belongs to: (key, the document that stands for it, its page or 0 for all of it)."""
    d = docs.get(doc_id) or {}
    if d.get("role") in PAGED:
        base = ("sha", d["sha"]) if d.get("sha") else ("doc", si, doc_id)
        return base + (int(page),), doc_id, int(page)
    if d.get("url", "").startswith(REPO_HOST):
        return ("design", design_of(d["url"])), doc_id, 0
    parent = d.get("parent", "")
    if d.get("role") == "figure" and parent in docs and docs[parent].get("role") not in PAGED:
        doc_id, d = parent, docs[parent]
    return (("sha", d["sha"]) if d.get("sha") else ("doc", si, doc_id)), doc_id, 0


def units(idx: dict) -> list[dict]:
    """Every unit, in a stable order: its copies, page, parts (with times and whether only named), kinds."""
    by_key: dict[tuple, dict] = {}
    for part, us in idx["uses"].items():
        for si, u in us:
            source = idx["sources"][si]
            key, doc_id, page_no = unit_key(si, u["doc"], u["page"], idx["documents"][source])
            unit = by_key.get(key)
            if unit is None:
                unit = by_key[key] = {"key": key, "page": page_no, "copies": defaultdict(lambda: [0, 0]),
                                      "parts": {}, "kinds": 0, "lines": []}
            copy = unit["copies"][(si, doc_id)]
            copy[1] += 1
            page = idx["pages"][source].get((u["doc"], u["page"])) or {}
            if int(page.get("schematic") or 0):
                copy[0] = 1
            line = idx["lines"].get(source, {}).get((u["doc"], u["page"], part))
            kind = line[0] if line else ""
            if line:
                unit["lines"].append(line[1])
            unit["kinds"] |= (1 << KINDS.index(kind)) if kind in KINDS else NOT_SUMMARISED
            times, named = unit["parts"].get(part, (0, True))
            unit["parts"][part] = (times + int(u.get("times") or 1), named and kind in NAMED_ONLY)
    out = []
    for unit in by_key.values():
        # The copy that stands for the unit: one with a circuit drawing, then the one the parts are read on
        # most, then the source first in the list — the order a part page keeps one copy by. A page of an
        # issue takes the issue's first copy, so the pages of one issue stay one run and can be read together.
        if unit["page"]:
            si, doc_id = min(unit["copies"])
        else:
            (si, doc_id), _ = min(unit["copies"].items(), key=lambda c: (-c[1][0], -c[1][1], c[0]))
        unit.update(si=si, doc=doc_id, schematic=max(s for s, _ in unit["copies"].values()))
        out.append(unit)
    out.sort(key=lambda x: (x["si"], int(x["doc"], 36), x["page"]))
    return out


def facet_key(source: str, label: str) -> str:
    """A facet's key in the usage filter's menu (`usage_facets`)."""
    return f"{source}/{label}" if label else source


def stamp_of(*parts: str) -> str:
    return hashlib.sha1("\n".join(parts).encode("utf-8")).hexdigest()[:10]


def deltas(ids: list[int]) -> list[int]:
    """Sorted ids as the first and then the steps between them: what gzip packs best."""
    out, prev = [], 0
    for i in ids:
        out.append(i - prev)
        prev = i
    return out


def word_index(all_units: list[dict]) -> tuple[dict[str, dict[str, list[int]]], list[str]]:
    """Which units each word of the summaries is on, as splits of the index by the word's first two letters
    (three, where two make a split too big), and the words left out for being on too many units."""
    postings: dict[str, list[int]] = defaultdict(list)
    for n, unit in enumerate(all_units):
        seen: set[str] = set()
        for line in unit["lines"]:
            for w in words(line):
                if w not in seen:
                    seen.add(w)
                    postings[w].append(n)
    limit = COMMON * len(all_units)
    common = sorted(w for w, us in postings.items() if len(us) > limit)
    shards: dict[str, dict[str, list[int]]] = defaultdict(dict)
    for w, us in postings.items():
        if len(us) <= limit:
            shards[shard_of(w)][w] = deltas(us)
    for key in [k for k, ws in shards.items() if gz_size(ws) > SHARD_BYTES]:
        for w, steps in shards.pop(key).items():
            shards[w[:3]][w] = steps
    return dict(shards), common


def gz_size(payload) -> int:
    return len(gzip.compress(json.dumps(payload, separators=(",", ":")).encode("utf-8"), 6))


def payloads(idx: dict, names: list[str], facets: list[dict], sources_stamp: str, parts_stamp: str
             ) -> tuple[dict, dict, dict[str, dict]]:
    """(units.json, docs.json, the word index's splits by key) for the Projects tab. `names` are the parts in
    `parts.json` order and `facets` the usage filter's menu, whose order the units name their facets by."""
    at = {p: i for i, p in enumerate(names)}
    facet_at = {f["key"]: i for i, f in enumerate(facets)}
    all_units = units(idx)
    era = eras()
    col: dict[str, list] = {k: [] for k in ("role", "flags", "kinds", "year", "page", "facet",
                                            "used", "usedIds", "named", "namedIds")}
    more_facets: dict[str, list[int]] = {}
    docs: dict[str, list] = {k: [] for k in ("title", "url", "source", "date")}
    also: dict[str, list[str]] = {}
    aka: dict[str, list[str]] = {}
    sheets: dict[str, int] = {}
    in_facet = [0] * len(facets)
    needed: set[str] = set()
    # A design on GitHub shares its folder with the other sheets of the project, or with other projects: the
    # result says how many, because one sheet of a design may not hold all of its parts.
    folders: dict[str, int] = defaultdict(int)
    for unit in all_units:
        if unit["key"][0] == "design":
            folders[unit["key"][1].rsplit("/", 1)[0]] += 1
    prev = None
    for n, unit in enumerate(all_units):
        source = idx["sources"][unit["si"]]
        doc = idx["documents"][source][unit["doc"]]
        fs = []
        for si, doc_id in sorted(unit["copies"], key=lambda c: (c != (unit["si"], unit["doc"]), c)):
            s = idx["sources"][si]
            i = facet_at.get(facet_key(*facet_of(s, idx["kinds"].get(s, ""), idx["documents"][s].get(doc_id, {}))))
            if i is not None and i not in fs:
                fs.append(i)
        for i in fs:
            in_facet[i] += 1
        col["facet"].append(fs[0] if fs else -1)
        if len(fs) > 1:
            more_facets[str(n)] = fs[1:]
        role = doc.get("role", "")
        col["role"].append(ROLES.index(role) if role in ROLES else -1)
        here = (unit["si"], unit["doc"], unit["page"])
        after = bool(unit["page"]) and prev is not None and prev[:2] == here[:2] and prev[2] == here[2] - 1
        col["flags"].append((SCHEMATIC if unit["schematic"] else 0) | (AFTER if after else 0))
        prev = here
        col["kinds"].append(unit["kinds"])
        year = doc.get("year", "")
        col["year"].append(int(year[:4]) if year[:4].isdigit() else 0)
        col["page"].append(unit["page"])
        used = sorted(at[p] for p, (_, named) in unit["parts"].items() if not named and p in at)
        named = sorted(at[p] for p, (_, only) in unit["parts"].items() if only and p in at)
        needed.update(unit["parts"])
        col["used"].append(len(used))
        col["usedIds"] += deltas(used)
        col["named"].append(len(named))
        col["namedIds"] += deltas(named)

        url = doc.get("url", "")
        if unit["page"]:
            page = idx["pages"][source].get((unit["doc"], str(unit["page"]))) or {}
            url = page.get("url") or url
        docs["title"].append(doc.get("title", ""))
        docs["url"].append(url)
        docs["source"].append(unit["si"])
        docs["date"].append(issue_date(doc))
        others = sorted({idx["sources"][si] for si, _ in unit["copies"]} - {source})
        if others:
            also[str(n)] = others
        titles = sorted({idx["documents"][idx["sources"][si]].get(d, {}).get("title", "")
                         for si, d in unit["copies"]} - {doc.get("title", ""), ""})
        if titles:
            aka[str(n)] = titles
        if unit["key"][0] == "design" and folders[unit["key"][1].rsplit("/", 1)[0]] > 1:
            sheets[str(n)] = folders[unit["key"][1].rsplit("/", 1)[0]]

    # The names each part is the same part as, for "what I have": the type a grade, package or packing is
    # of (BC547BTA -> BC547B -> BC547), and the makers' names of a bare number (7812 -> L7812, MC7812).
    up: dict[str, list[str]] = {}
    alias: dict[str, list[str]] = {}
    for p in sorted(needed):
        steps = [t for _, t in kin_names_steps(p)]
        if steps:
            up[p] = steps
        same = sorted({t for why, t in kin_names(p) if why in SAME_PART})
        if same:
            alias[p] = same

    keys = [repr(u["key"]) for u in all_units]
    find_stamp = stamp_of(parts_stamp, sources_stamp, *keys)
    shards, common = word_index(all_units)
    menu = [{**f, "n": in_facet[i]} for i, f in enumerate(facets)]
    units_payload = {
        "schema": SCHEMA, "findStamp": find_stamp, "partsStamp": parts_stamp, "sourcesStamp": sources_stamp,
        "roles": list(ROLES), "kinds": list(KINDS), "negative": list(NEGATIVE),
        "facets": menu, "moreFacets": more_facets,
        "eras": [era.get(s, "") for s in idx["sources"]],
        "units": col, "up": up, "alias": alias,
        # What a document says one part is to another, by name — a part the reader has may be in no document
        # here (TL072H) and still do for one that is — and what each relation is worth (catalogue.COVERAGE).
        "relations": [[r["part"], r["relation"], r["other"], r["refs"].split(), r["note"], r["status"]]
                      for r in catalogue.relations()],
        "coverage": {k: list(v) for k, v in catalogue.COVERAGE.items()},
        "shards": sorted(shards), "common": common,
    }
    docs_payload = {"schema": SCHEMA, "findStamp": find_stamp, **docs, "also": also, "aka": aka, "sheets": sheets}
    return units_payload, docs_payload, {k: {"findStamp": find_stamp, "words": ws} for k, ws in shards.items()}
