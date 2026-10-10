"""Turn the curated model directories into the public recipe for each part.

    sei models promote

The curated tree — `config.spice_curated()`, one directory per part holding its `part.json` — is where
the judgement lives: every model found for a part and where each came from. That judgement is the most
valuable thing the project holds and the only part of it that cannot be downloaded again, so it belongs
in git rather than in a private tree. (The old scores against a data sheet and the "preferred" model of
the first iteration are not carried any more: every model is characterised on its own instead.)

What crosses the line is metadata, never model text. For each candidate this writes the source, the name
and shape of the definition, and a `get:` block saying exactly how to obtain it — URL, the member inside
the archive when there is one, the checksums and the line range. A reader ends up with the same bytes we
have, from the vendor, which is what rule 2 asks for: forbidding redistribution does not forbid indexing.

Everything naming the private tree is dropped, by allow-list rather than by blocking: local paths, the
manifest, the licence file and the downloaded datasheet PDF. The licence itself is **not** copied in — it
lives once in the source's registry entry, and a copy here would go stale the day a source is reviewed.
The part file names the source, and the reader joins.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from functools import lru_cache
from pathlib import Path

import yaml

from spicy_electronics_index.core.config import (
    model_changes,
    model_part,
    model_sources,
    require,
    spice_curated,
    spice_found,
    spice_models_root,
    spice_recipe_locations,
    spice_source,
)
from spicy_electronics_index.models import found as F
from spicy_electronics_index.models import symbols as S
from spicy_electronics_index.models.fetch import archive_for, members, source_files


class Flow(list):
    """A list YAML writes inline. A line range reads as `[250, 250]`, not as three lines."""


yaml.SafeDumper.add_representer(
    Flow, lambda d, data: d.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=True))

VERSION = "promote_models-4"   # 4: no preferred model and no old scores; 3: every model carries its identity, `hash`
# A note is prose the maintainer wrote for themselves, and a judgement is sometimes signed. The date is
# worth keeping and the name is not: the public side of this project carries no personal names.
SIGNED = re.compile(r"\(\s*[A-Z][\w'-]*(?:\s+[A-Z][\w'-]*)?\s*,\s*(\d{4}-\d{2}-\d{2})\s*\)")


def unsigned(text: str) -> str:
    """Prose with any `(Name, date)` attribution reduced to `(maintainer, date)`."""
    return SIGNED.sub(lambda m: f"(maintainer, {m.group(1)})", text or "")


def parts(root: Path) -> list[Path]:
    """Every curated part, in a stable order so a rerun produces the same files."""
    return sorted(root.glob("*/*/part.json"))


def installed_from(prov: dict) -> tuple[str, str] | None:
    """For a model that ships inside a simulator, which product it is and where in its library.

    Some definitions have no URL at all: LTspice installs its own library, and the way to obtain those
    models is to install LTspice. The recipe has to say that instead of publishing an empty link. The
    path is recorded against a variable, `$LTSPICE_LIB/cmp/standard.dio`, and only the part below the
    library is a fact about the product — the rest is wherever that machine happened to put it.
    """
    if prov.get("url"):
        return None
    origin = (prov.get("origin") or "").split(";")[0].strip()
    file = prov.get("installed_file") or prov.get("file") or ""
    m = re.match(r"\$[A-Z_]+/(.*)", file)
    return (origin, m.group(1)) if origin and m else None


def from_archive(prov: dict) -> dict | None:
    """The archive a definition was unpacked from, when the curation did not record its URL.

    Curation copied the provenance of the file it read, and for a file that came out of an archive that
    is a path under `extracted/`, with no link in it. The link was never lost — it is in the manifest,
    against the archive — so the recipe is completed by the same join that recovery makes. Without it
    seventy-one models would say where they were verified and not where to get them.
    """
    parts = (prov.get("file") or "").split("/")
    if prov.get("url") or len(parts) < 4 or parts[0] != "sources" or parts[2] != "extracted":
        return None
    files = source_files(parts[1])
    hit, inferred = archive_for(files, parts[3], strict=True), False
    if not hit:
        # The folder does not name any archive, so fall back to the source's only one. That is an
        # inference, not a record, and the recipe says so: a reader can tell a link we followed from a
        # link we worked out, which rule 4 asks for whenever a wrong link would be worse than none.
        hit, inferred = archive_for(files, parts[3]), True
    if not hit:
        return None
    member = prov.get("member") or member_of(parts[1], hit, parts[3:])
    out = {"url": hit["url"], "member": member, "archive_sha256": hit.get("sha256", "")}
    if inferred:
        out["archive_inferred"] = True
    return out


@lru_cache(maxsize=None)
def archive_members(source: str, rel: str) -> frozenset[str]:
    """The files an archive the source keeps holds, or none when it is not here to look into."""
    try:
        return frozenset(members(spice_source(source) / rel))
    except (OSError, zipfile.BadZipFile):
        return frozenset()


def member_of(source: str, hit: dict, tail: list[str]) -> str:
    """The file inside the archive, as the archive names it.

    `tail` is the path under `extracted/`, starting with the folder that names the archive. Usually that
    folder is where the archive was unpacked, so it is not part of the member. But an archive that carries
    its own top folder and was unpacked straight into `extracted/` (Bordodynov's lib.zip holds `lib/...`)
    puts that folder there itself, and then it is: the archive is asked which of the two it holds.
    """
    inner, whole = "/".join(tail[1:]), "/".join(tail)
    held = archive_members(source, hit["path"]) if hit.get("path") else frozenset()
    return whole if whole in held and inner not in held else inner


def get_block(prov: dict) -> dict:
    """How to obtain this definition, with nothing in it that names the private tree.

    A definition found inside an archive needs three facts, not one: the URL serves the archive, the
    member says which file inside it holds the definition, and the two checksums answer different
    questions — whether the download is the one we saw, and whether the file inside it is.
    """
    installed = installed_from(prov)
    if installed:
        out = {"installed_with": installed[0], "file": installed[1]}
        if prov.get("file_sha256"):
            out["sha256"] = prov["file_sha256"]
        if prov.get("lines"):
            out["lines"] = {k: Flow(v) for k, v in sorted(prov["lines"].items())}
        return out
    recovered = from_archive(prov)
    if recovered:
        out = {k: v for k, v in recovered.items() if v not in ("", None)}
    else:
        out = {"url": prov.get("url") or ""}
        if prov.get("member"):
            out["member"] = prov["member"]
            archive = prov.get("archive") or {}
            if archive.get("sha256"):
                out["archive_sha256"] = archive["sha256"]
        if not out["url"]:
            # Honest about the gap: the model was read and scored, but nothing recorded where it came
            # from. Saying so is better than publishing an empty link.
            out.pop("url")
            out["how"] = "unknown"
    if prov.get("file_sha256"):
        out["sha256"] = prov["file_sha256"]
    if prov.get("lines"):
        # {definition: [first, last]}, 1-based and inclusive, as the extractor recorded them.
        out["lines"] = {k: Flow(v) for k, v in sorted(prov["lines"].items())}
    if prov.get("fetched"):
        out["fetched"] = prov["fetched"]
    return out


def candidate(c: dict) -> dict:
    """One model offered for this part: what it is, how to get it, how well it did."""
    prov = c.get("provenance") or {}
    changes = c.get("changes") or []
    out: dict = {
        "source": c.get("source") or prov.get("source", ""),
        "name": c.get("name", ""),
        "def": c.get("def", ""),
    }
    if c.get("type"):
        out["type"] = c["type"]
    if c.get("pins"):
        out["pins"] = list(c["pins"])
    if c.get("deps"):
        # Other top-level definitions this one references; they must travel with it.
        out["deps"] = list(c["deps"])
    out["verbatim"] = not changes
    if changes:
        # Our own fixups, named. What changed is our work and is worth publishing; the text is not.
        out["changes"] = [x["id"] if isinstance(x, dict) else str(x) for x in changes]
    out["get"] = get_block(prov)
    if prov.get("note"):
        out["get"]["note"] = unsigned(prov["note"])
    if c.get("note"):
        out["note"] = unsigned(c["note"])
    return out


def datasheet_block(d: dict | None) -> dict | None:
    """The data sheet the recipe names: the link and what it is, never the downloaded copy."""
    if not d or not d.get("url"):
        return None
    return {k: d[k] for k in ("url", "maker", "doc", "date") if d.get(k)}


def recipe(data: dict) -> dict:
    """The public record for one part."""
    cands = [candidate(c) for c in data.get("candidates") or []]
    out: dict = {"part": data.get("part", ""), "kind": data.get("kind", "")}
    if data.get("priority"):
        out["priority"] = data["priority"]
    if data.get("group"):
        out["group"] = data["group"]
    out["models"] = cands
    ds = datasheet_block(data.get("datasheet"))
    if ds:
        out["datasheet"] = ds
    return out


def change_kinds(root: Path) -> dict[str, str]:
    """Every fixup the curation names, with the reason recorded once instead of at each use.

    The reason is the valuable half and it is our own writing: that LTspice reads `^` as Boolean XOR,
    so an author's `2^3` silently evaluates to zero, is the kind of thing this project exists to record.
    The patch itself stays private — a diff carries the vendor's surrounding lines, which is model text.
    """
    out: dict[str, str] = {}
    for p in parts(root):
        for c in json.loads(p.read_text(encoding="utf-8")).get("candidates") or []:
            for ch in c.get("changes") or []:
                if isinstance(ch, dict) and ch.get("id"):
                    out.setdefault(ch["id"], unsigned(ch.get("why", "")))
    return out


def write(path: Path, doc: dict) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100)
    path.write_text(text, encoding="utf-8")
    return len(text.encode("utf-8"))


# --- what the catalogue holds beyond the curation ------------------------------------------------------
# The old curation's own sentence for what `copies` now lists with a link each.
SAME_CODE = re.compile(r";?\s*same code also in: [^;]*")


def found_models() -> dict:
    """`sei models found`: every distinct model per part, with its copies. Empty when it has not run."""
    p = spice_found()
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def curated_hash(c: dict, files: F.Files) -> str | None:
    """The identity `sei models found` gives this curated model, read from the file it was taken from."""
    file = (c.get("provenance") or {}).get("file") or ""
    if not file.startswith("sources/"):
        return None
    try:
        chain = F.closure(files.get(file)[0], c.get("name", ""))
    except OSError:
        return None
    return F.code_hash(chain) if chain else None


# A copy is a pointer to the same bytes elsewhere: where to get them and the checksum that proves it is
# them. The line ranges and fetch dates are on the model itself; repeated for every copy they made the
# recipes four times larger for nothing a reader follows.
COPY_GET = ("url", "member", "installed_with", "file", "how", "sha256")


def copy_entry(x: dict) -> dict:
    """Another source holding the same model: who, under which name, and how to get it from there."""
    get = get_block(x.get("provenance") or {})
    return {"source": x["source"], "name": x["name"], "get": {k: get[k] for k in COPY_GET if get.get(k)}}


def match_note(part: str, how: str) -> str:
    """What the part page must say about a model found under a name other than the part's own."""
    if how.startswith("stand-in:"):
        return (f"STAND-IN: model of {how[9:].split('/')[0]}, not of {part}; the equivalence is declared "
                f"in data/models/wanted.yaml")
    if how.startswith("alias:"):
        return f"found under the alias {how[6:].split('/')[0]}"
    return ""


def with_hash(model: dict, h: str) -> dict:
    """The model with its identity right after its name and shape, where a reader of the YAML looks."""
    out: dict = {}
    for k, v in model.items():
        if k != "hash":
            out[k] = v
        if k == "def":
            out["hash"] = h
    return out


def uncurated(part: str, m: dict) -> dict:
    """A model the catalogue holds for this part and the curation never judged."""
    out: dict = {"source": m["source"], "name": m["name"], "def": m["def"], "hash": m["hash"]}
    if m.get("type"):
        out["type"] = m["type"]
    if m.get("deps"):
        out["deps"] = list(m["deps"])
    out["verbatim"] = True
    out["get"] = get_block(m.get("provenance") or {})
    if (m.get("provenance") or {}).get("embedded_in_symbol"):
        out["get"]["note"] = "the model is inside the QSPICE symbol, in its «library file» field"
    if (m.get("provenance") or {}).get("url_is_source_page"):
        # The manifest does not list this file, so the link is the source's own and a reader must be
        # told it will not land on the file. Manifest notes themselves are working notes and stay private.
        out["get"]["note"] = "the URL is where the source publishes its files, not this file"
    note = match_note(part, m.get("match", ""))
    if note:
        out["note"] = note
    if m.get("copies"):
        out["copies"] = [copy_entry(x) for x in m["copies"]]
    return out


def join_found(doc: dict, data: dict, entry: dict, files: F.Files, where: list[str] | None = None) -> int:
    """Add to a recipe what the catalogue holds beyond its curated models. Returns how many were added.

    `where`, when given, receives the file each of the recipe's models was read from, in the recipe's
    order: the private side of the same list (`spice_recipe_locations`).

    A curated model the catalogue also holds elsewhere gains those copies, each with its own link — the
    file a collection copied is often the vendor's original, and it is the one a reader should be sent to.
    A model no curated one matches is appended, unjudged: the page shows it as not measured.
    """
    hashes = {}
    where = [] if where is None else where
    for i, c in enumerate(data.get("candidates") or []):
        h = curated_hash(c, files)
        where.append((c.get("provenance") or {}).get("file") or "")
        if h:
            hashes.setdefault(h, i)
            doc["models"][i] = with_hash(doc["models"][i], h)
    added = 0
    for m in entry.get("models") or []:
        i = hashes.get(m["hash"])
        if i is None:
            doc["models"].append(uncurated(doc["part"], m))
            where.append(m["provenance"].get("file") or "")
            added += 1
            continue
        cand = data["candidates"][i]
        own = (cand.get("provenance") or {}).get("file")
        others = [dict(m, file=m["provenance"].get("file"))] + list(m.get("copies") or [])
        model = doc["models"][i]
        best = others[0]
        if best["file"] != own and F.rank(best["source"], best["file"]) < F.rank(model["source"], own or ""):
            # the catalogue holds the same model somewhere more original than the curated file (the vendor's
            # own, say, where the curation read a collection's copy): that is the copy the recipe links
            others = [x for x in others if x["file"] != best["file"]]
            if not any(x.get("file") == own for x in others):
                others.append({"source": model["source"], "name": model["name"], "file": own, "provenance": cand.get("provenance") or {}})
            model.update(source=best["source"], name=best["name"], get=get_block(best["provenance"]))
            where[i] = best["file"]
        copies = [copy_entry(x) for x in others if x.get("file") != where[i]]
        if copies:
            model["copies"] = copies
            if model.get("note"):
                model["note"] = SAME_CODE.sub("", model["note"]).strip("; ")
                if not model["note"]:
                    del model["note"]
    return added


def order_models(doc: dict, where: list[str]) -> None:
    """Most original first (the class of the file each model is linked to, models/origin.py), the
    curation's order among equals; `where` (the private file list) follows."""
    idx = sorted(range(len(doc["models"])), key=lambda i: (F.rank(doc["models"][i]["source"], where[i]), i))
    doc["models"] = [doc["models"][i] for i in idx]
    where[:] = [where[i] for i in idx]


def known_sources() -> set[str]:
    return {p.stem for p in model_sources().glob("*.yaml")}


def promote(only: str | None = None, dry: bool = False) -> dict:
    root = require(spice_curated(), "promoting the curated models")
    known = known_sources()
    found = found_models()
    files = F.Files(spice_models_root())
    counts = {"parts": 0, "models": 0, "verified": 0, "with_datasheet": 0, "bytes": 0,
              "unknown_sources": 0, "uncurated_parts": 0,
              "uncurated_models": 0, "with_copies": 0, "published_symbols": 0}
    by_model = S.load()
    unknown: set[str] = set()
    locations: dict[str, list[dict]] = {}

    def publish(doc: dict, where: list[str], entry: dict | None = None) -> None:
        # the symbol published with the model: beside the copy the recipe links, or else beside another copy
        # of the same code, linked like the model either way (models/symbols.py). The pins are the
        # definition's, which a recipe of an unjudged model does not repeat.
        held = {r["hash"]: (r.get("pins") or [], [(r.get("provenance") or {}).get("file") or "",
                                                  *(c.get("file") or "" for c in r.get("copies") or [])])
                for r in (entry or {}).get("models") or []}
        for m, f in zip(doc["models"], where):
            pins, files = held.get(m.get("hash"), ([], []))
            n = len(m.get("pins") or pins)
            s = next((x for x in (S.symbol_for(m["name"], n, g, by_model) for g in dict.fromkeys([f, *files]) if g)
                      if x), None)
            if s:
                prov = F.provenance(spice_models_root(), s["file"], s["source"], s["sha256"])
                m.setdefault("get", {})["symbol"] = {k: v for k, v in get_block(prov).items()
                                                     if k in ("url", "member", "archive_sha256", "sha256", "how")}
                counts["published_symbols"] += 1
        # Where each model was read from goes to the private side: the file names the private tree.
        locations[f"{doc['kind']}/{doc['part']}"] = [
            {"hash": m.get("hash", ""), "file": f, "name": m["name"]} for m, f in zip(doc["models"], where)]
        counts["parts"] += 1
        counts["models"] += len(doc["models"])
        counts["with_copies"] += sum(1 for m in doc["models"] if m.get("copies"))
        counts["with_datasheet"] += 1 if doc.get("datasheet") else 0
        for m in doc["models"]:
            if m["source"] not in known:
                unknown.add(m["source"])
        if not dry:
            counts["bytes"] += write(model_part(doc["kind"], doc["part"]), doc)

    curated: set[str] = set()
    for p in parts(root):
        data = json.loads(p.read_text(encoding="utf-8"))
        if only and data.get("kind") != only:
            continue
        # a curated model read from a file no link leads to goes, as such a file's definitions never become
        # candidates (found.UNPUBLISHED)
        data["candidates"] = [c for c in data.get("candidates") or []
                              if not F.unpublished((c.get("provenance") or {}).get("file") or "")]
        doc = recipe(data)
        if not doc["part"] or not doc["kind"]:
            continue
        curated.add(doc["part"].upper())
        where: list[str] = []
        counts["uncurated_models"] += join_found(doc, data, found.get(doc["part"]) or {}, files, where)
        order_models(doc, where)
        publish(doc, where, found.get(doc["part"]))
    # Parts the curation never reached, with every model the catalogue holds for them. Found entries are
    # keyed by the name the wanted list gives, which the curation may have spelt in another case.
    for part, entry in sorted(found.items()):
        if part.upper() in curated or not entry.get("models") or (only and entry["kind"] != only):
            continue
        doc = {"part": part, "kind": entry["kind"]}
        if entry.get("priority"):
            doc["priority"] = entry["priority"]
        if entry.get("group"):
            doc["group"] = entry["group"]
        doc["models"] = [uncurated(part, m) for m in entry["models"]]
        where = [m["provenance"].get("file") or "" for m in entry["models"]]
        order_models(doc, where)
        counts["uncurated_parts"] += 1
        counts["uncurated_models"] += len(doc["models"])
        publish(doc, where, entry)
    if not dry and not only:
        spice_recipe_locations().write_text(json.dumps(locations, indent=0, sort_keys=True) + "\n",
                                            encoding="utf-8")
    kinds = change_kinds(root)
    counts["change_kinds"] = len(kinds)
    if kinds and not dry:
        model_changes().parent.mkdir(parents=True, exist_ok=True)
        model_changes().write_text(yaml.safe_dump(
            {"changes": [{"id": k, "why": kinds[k]} for k in sorted(kinds)]},
            sort_keys=False, allow_unicode=True, width=100), encoding="utf-8")
    counts["unknown_sources"] = len(unknown)
    if unknown:
        counts["unknown"] = sorted(unknown)
    return counts


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--kind", help="only one kind (bjt, jfet, ...)")
    ap.add_argument("--dry", action="store_true", help="say what would be written and write nothing")
    a = ap.parse_args(argv)

    counts = promote(only=a.kind, dry=a.dry)
    print(f"{counts['parts']:,} parts, {counts['models']:,} candidate models "
          f"({counts['verified']:,} scored against a datasheet, {counts['with_datasheet']:,} parts "
          f"with a datasheet link)" + (" — dry run" if a.dry else ""))
    print(f"{counts['uncurated_models']:,} models the curation never judged, {counts['uncurated_parts']:,} of "
          f"them for parts it never reached; {counts['with_copies']:,} models list their copies elsewhere")
    print(f"{counts['change_kinds']} kinds of fixup, each with its reason, in {model_changes().name}")
    print(f"{counts['published_symbols']:,} models linked to the symbol their own copy was published with")
    if not a.dry:
        print(f"{counts['bytes'] / 1e6:.1f} MB into {model_part('<kind>', '<PART>').parent.parent}")
    if counts.get("unknown"):
        print(f"! {counts['unknown_sources']} sources are named by a model but have no registry entry: "
              + ", ".join(counts["unknown"][:8]), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
