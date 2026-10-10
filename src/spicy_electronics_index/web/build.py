"""Build the website's data from `data/`, and from nothing else.

    sei web build

This is the architectural contract of the project: everything the site shows is committed, so anyone who
clones the repository can rebuild it — no corpus, no GPU, no credentials. `tests/web/test_build.py` proves
it by making the private data root raise and running this anyway.

What it emits grows as the exports land. Today: the source registries with their coverage, the search
index, and one file per part holding everything its page shows — where the part is used, which models
exist for it and how good each one is. Datasheets follow.

A part page is one request, because the site is static and has nobody to ask. `web/parts.py` does the
joining, grouping and capping that a browser would otherwise have to be sent the raw rows to do.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import shutil
import tempfile
from datetime import date
from pathlib import Path

from spicy_electronics_index import status
from spicy_electronics_index.core.config import datasheets_table, model_part, schematics_parts, web_data
from spicy_electronics_index.core.partfile import part_file
from spicy_electronics_index.web import character as character_web
from spicy_electronics_index.web import parts as part_pages

SCHEMA = 1


def write_json_gz(out: Path, name: str, payload) -> int:
    """Write one file gzipped, compact, atomically; the site decompresses it in the browser. Returns its size.
    The gzip header carries no time, so the same payload gives the same bytes."""
    target = out / name
    target.parent.mkdir(parents=True, exist_ok=True)
    data = gzip.compress(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8"), 9, mtime=0)
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=target.name, suffix=".tmp")
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    os.replace(tmp, target)
    return len(data)


def write_json(out: Path, name: str, payload) -> int:
    """Write one file atomically, compact. Returns its size in bytes.

    `name` may carry a slash. 267 published parts do — ADC121C027CIMK/NOPB is TI's ordering suffix,
    APT1608LSECK/J3-PRV is Kingbright's — and the site asks for `part/<encodeURIComponent(part)>.json`,
    which a static server decodes back to a path with a directory in it. So the directory is made here,
    for the file, and not once for the root: the first build after the CAD sources arrived died on
    part/A10/A20.json with the directory A10 not there.
    """
    target = out / name
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=target.name, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    os.replace(tmp, target)
    return target.stat().st_size


def sources_payload() -> dict:
    """Both registries with their coverage, straight from the committed ledgers."""
    return {
        "schematics": [
            {k: r[k] for k in ("source", "kind", "status", "items", "download", "ocr", "index",
                               "linkcheck", "skipped", "last", "next")}
            for r in status.schematics_rows()
        ],
        "models": [
            {k: r[k] for k in ("source", "status", "fetch", "files", "scanned", "with_defs", "defs",
                               "unavailable", "not_tried", "licence", "last", "next")}
            for r in status.model_rows()
        ],
    }


def totals(payload: dict) -> dict:
    s, m = payload["schematics"], payload["models"]
    return {
        "sources": len(s),
        "items": sum(r["items"] for r in s),
        "indexed": sum(r["index"] for r in s),
        "ocr": sum(r["ocr"] for r in s),
        "modelSources": len(m),
        "modelFiles": sum(r["files"] for r in m),
        "definitions": sum(r["defs"] for r in m),
    }


def build(out: Path | None = None) -> dict:
    """Write every data file the site needs. Returns the manifest."""
    out = Path(out) if out else web_data()
    payload = sources_payload()
    sizes = {"sources.json": write_json(out, "sources.json", payload)}

    idx = part_pages.index()
    recipes, clashes = part_pages.model_recipes()
    # the bench's order: the page's numbers and colours, and the character file, follow it
    recipes = {k: character_web.ranked(v) for k, v in recipes.items()}
    # Every number the project knows, for the naming schemes that must not read an American revision
    # letter as a Soviet envelope: 1X2A is the 1X2, revised, because 1X2 is a part of its own. Known before
    # the search index is written, because a part's family there can come from its name.
    idx["known"] = part_pages.known_kinds(idx, recipes, part_pages.all_names(idx, recipes))
    search, kind_names = part_pages.search_index(idx, recipes)
    names = [r[0] for r in search]
    idx["variants"] = part_pages.variant_groups(names, part_pages.vouched(idx, recipes, search))
    # A part page names its sources by position in parts.json, and the two are cached apart (Pages sends
    # max-age=600 for each). A browser holding the last build's parts.json read the new part pages
    # through the old list and put audiocircuit's manuals under AMB. Both carry this stamp of the list;
    # a page whose stamp differs from the index it was given asks for the index again.
    kinds_list = [idx["kinds"].get(s, "") for s in idx["sources"]]
    stamp = hashlib.sha1("\n".join(idx["sources"] + ["--"] + kinds_list).encode("utf-8")).hexdigest()[:10]
    if search:
        # The part pages first: each one counts its data sheets, and the index carries that count so the
        # list can be sorted by it without opening fifty thousand files.
        total = 0
        written_models: set[str] = set()
        for row in search:
            page = part_pages.part_payload(row[0], idx, recipes.get(row[0]))
            about = page.get("about") or {}
            row.append(len(about.get("sheets") or []) + len(about.get("books") or []))
            total += write_json(out / "part", f"{part_file(row[0])}.json", {**page, "ss": stamp})
            ch = character_web.part_payload(recipes[row[0]]) if row[0] in recipes else None
            if ch:
                sizes["character/"] = sizes.get("character/", 0) + write_json(out / "character", f"{part_file(row[0])}.json", ch)
                # each model's record once, gzipped, whatever the parts that list it
                for mo in ch["models"].values():
                    h = mo["hash"]
                    if h not in written_models:
                        written_models.add(h)
                        sizes["character/"] += write_json_gz(out / "character" / "m", f"{h}.json.gz",
                                                             character_web.model_payload(character_web.record_of(h)))
                page["models"]["char"] = character_web.summary(ch)
                total += write_json(out / "part", f"{part_file(row[0])}.json", {**page, "ss": stamp})
        sizes["part/"] = total
        sizes["parts.json"] = write_json(out, "parts.json", {
            "schema": SCHEMA, "sources": idx["sources"], "sourcesStamp": stamp,
            # what each source is, so a part page can group its uses by the kind of thing they are
            "kinds": kinds_list,
            # the vocabulary of device kinds; a part row names one by position
            "deviceKinds": kind_names,
            # the families, in the order a part row names one by position
            "families": list(part_pages.catalogue.families()),
            "parts": search})
        sizes["catalogue.json"] = write_json(out, "catalogue.json", part_pages.catalogue_payload(idx))

    # The method page: the measurement catalogue as published, and the circuit drawings that exist.
    sizes["bench/methods.json"] = write_json(out / "bench", "methods.json", character_web.methods_payload())
    for f in character_web.drawing_files():
        (out / "bench" / "drawings").mkdir(parents=True, exist_ok=True)
        shutil.copy(f, out / "bench" / "drawings" / f.name)

    # Each of these lands with its exporter; the site renders what is present and says what is not.
    manifest = {
        "schema": SCHEMA,
        "built": date.today().isoformat(),
        "totals": totals(payload),
        "have": {
            "sources": True,
            "index": schematics_parts().exists(),
            "parts": bool(search),
            "models": model_part("bjt", "any").parent.parent.is_dir(),
            "datasheets": datasheets_table().exists(),
            "character": "character/" in sizes,
        },
        "parts": len(search),
        "partsFiledTwice": sorted(set(clashes)),
        "sizes": sizes,
    }
    write_json(out, "manifest.json", manifest)
    return manifest
