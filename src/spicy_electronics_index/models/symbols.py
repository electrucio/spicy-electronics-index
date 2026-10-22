"""The LTspice symbols (.asy) the model sources ship, and which model each one places.

A model SPICE has no element for — a loudspeaker, a relay, a transformer — is placed in LTspice through
its symbol, a file of its own that its author published beside it, often in the same archive. So a recipe
model gains the symbol published with it, as a link like its own: then "Get it" leads to every file the
model needs, the archive that holds both or each file where it is. Links only, the .asy is a third
party's file (rule 1).

A symbol is the model's when it names it (`SpiceModel`, or `Value` on a symbol whose prefix is X, as
LTspice reads them; a symbol that names nothing, or puts a file name there, is named by its own file
name, and in the second case by its Value and Value2 too) and has as many pins as the model, and when it comes from the model's own copy: the
same archive, or the same folder of separate downloads, which for a forum thread is the post that
brought them (a library and the zip of its symbols); a symbol that names the file LTspice is to load
(`ModelFile`) must name the model's. A symbol of that name from another collection is not taken, because
collections renumber pins and rename models; a wrong symbol is worse than none.

    sei models symbols        # read every .asy into config.spice_symbols()
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from spicy_electronics_index.core.config import spice_models_root, spice_symbols

FILE_NAME = re.compile(r"\.(lib|sub|cir|inc|txt|mod|ckt|sp)$", re.I)


def norm(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def read(text: str) -> dict:
    """What an .asy says about the model it places: prefix, model, model file, pins in SpiceOrder."""
    attrs: dict[str, str] = {}
    pins: list[tuple[int, str]] = []
    name = None
    for line in text.splitlines():
        w = line.split(None, 2)
        if not w:
            continue
        if w[0] == "SYMATTR" and len(w) == 3:
            attrs[w[1]] = w[2].strip()
        elif w[0] == "PIN":
            name = None
        elif w[0] == "PINATTR" and len(w) == 3:
            if w[1] == "PinName":
                name = w[2].strip()
            elif w[1] == "SpiceOrder" and w[2].strip().isdigit():
                pins.append((int(w[2]), name or ""))
    prefix = attrs.get("Prefix", "")
    model = attrs.get("SpiceModel") or (attrs.get("Value", "") if prefix.upper() == "X" else "")
    model_file = attrs.get("ModelFile", "")
    out = {"prefix": prefix, "model": model, "model_file": model_file, "pins": [n for _, n in sorted(pins)]}
    if FILE_NAME.search(model):              # Trafos.lib written where the model's name goes
        out["model_file"], out["model"] = model_file or model, ""
        # Such a symbol is named by its file, and by what its Value and Value2 say: the collections that
        # write it so put the subcircuit's name in either (tube.lib's EZ81, LF353.mod's LF353/NS).
        if prefix.upper() == "X" and (names := [attrs[k] for k in ("Value", "Value2") if attrs.get(k)]):
            out["names"] = names
    return out


def scan(root: Path) -> list[dict]:
    out = []
    for p in sorted((root / "sources").rglob("*")):
        if p.suffix.lower() != ".asy" or not p.is_file():
            continue
        data = p.read_bytes()
        s = read(data.decode("latin-1"))
        if s["prefix"].upper() not in ("X", ""):
            continue                        # a resistor, a diode: placed by its own element, not a model
        rel = str(p.relative_to(root))
        out.append({"file": rel, "source": rel.split("/")[1], "sha256": hashlib.sha256(data).hexdigest(), **s})
    return out


def load(path: Path | None = None) -> dict[str, list[dict]]:
    """The symbols by the model each places (normalised name); empty when the list was never written."""
    path = path or spice_symbols()
    out: dict[str, list[dict]] = defaultdict(list)
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            s = json.loads(line)
            for key in dict.fromkeys(norm(n) for n in [s["model"] or Path(s["file"]).stem, *s.get("names", [])]):
                out[key].append(s)
    return out


@lru_cache(maxsize=1)
def posts() -> dict[str, str]:
    """`sources/<source>/extracted/<archive>` -> the post folder the archive was delivered in.

    A forum thread is delivered one folder per post (`models/thread.py`), and what one post brought is one
    place, as a folder of separate downloads is: kevinkr's #117 gives `tube_lib.zip` and `Tubes_sym.zip`.
    """
    root = spice_models_root() / "sources"
    out: dict[str, str] = {}
    for p in root.glob("*/raw/thread-*/*/*") if root.is_dir() else []:
        rel = p.relative_to(root)
        out[f"sources/{rel.parts[0]}/extracted/{p.stem}"] = f"sources/{rel.parent.as_posix()}"
    return out


def folder(file: str) -> str:
    """The place a file shares with its neighbours: the archive it was unpacked from, or its folder; for
    an archive a post brought, the post's folder."""
    parts = Path(file).parts
    if len(parts) > 3 and parts[2] == "extracted":
        place = "/".join(parts[:4])                # sources/<source>/extracted/<archive>
        return posts().get(place, place)
    return str(Path(file).parent)


def symbol_for(name: str, pins: int, model_file: str, by_model: dict[str, list[dict]]) -> dict | None:
    """The symbol published with this copy of a model, or None: same archive or folder, same name, as
    many pins. Several in that place (one collection files a symbol twice): the shortest path."""
    if not model_file:
        return None
    place, own = folder(model_file), Path(model_file).name.lower()
    hits = [s for s in by_model.get(norm(name), [])
            if folder(s["file"]) == place and len(s["pins"]) == pins and s["prefix"].upper() in ("X", "")
            and (not s["model_file"] or Path(s["model_file"].replace("\\", "/")).name.lower() == own)]
    return min(hits, key=lambda s: (len(s["file"]), s["file"])) if hits else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="read every LTspice symbol the model sources ship")
    ap.parse_args(argv)
    found = scan(spice_models_root())
    out = spice_symbols()
    out.write_text("".join(json.dumps(s, ensure_ascii=False) + "\n" for s in found), encoding="utf-8")
    print(f"{len(found):,} symbols of subcircuits, from {len({s['source'] for s in found})} sources -> {out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
