"""What the open EDA libraries say about each part: the data sheet their symbol links, the package it is
drawn in, and the values their authors typed beside it.

    sei datasheets libraries [--source kicad_symbols] [--refresh]

KiCad's official symbol library names 22,583 symbols and links a data sheet from 19,655 of them; Horizon
EDA's pool and LibrePCB's base library are smaller but type each part's limits with a unit (V_CEO 45 V,
I_C 100 mA). All three are kept in git under licences that allow reading and quoting them, and all three
are maintained by people who had the data sheet open, which is the whole value: a part-to-sheet link and
a one-line description that somebody checked, for parts no maker's catalogue lists any more.

Each library is cloned once, shallow and at a pinned release or commit, into the private tree (it is
third-party content) and read from there; `--refresh` pulls it again. What is published is a row per part
this project knows, in the same table as the makers' catalogues (`data/datasheets/catalogue/<source>.csv`)
so the site shows them together, plus the columns the libraries have and the catalogues do not: the maker
as the library writes it, the package, the keywords and the typed values. The library's own text — a
symbol drawing, a footprint — stays where it is; the row links to it.

A library's `maker` is who the library names, or, when it names nobody, the manufacturer whose own site
serves the linked sheet. A sheet on a distributor's or an archive's host names no maker.

KiCad's footprint library is read after its symbols, for the packages those symbols give the indexed
parts: mounting, pins, pad spacing, body size and the drawing each was measured from, into
`data/datasheets/packages/kicad_footprints.csv`.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import urlparse

from spicy_electronics_index.core.config import datasheet_catalogue, datasheet_packages, datasheets_cache
from spicy_electronics_index.core.ledger import today
from spicy_electronics_index.core.parts import catalogue
from spicy_electronics_index.datasheets.harvest import known, registry

# The catalogue table's columns, then what only a library gives.
FIELDS = ("part", "source", "maker", "category", "status", "name", "title", "revision", "url", "page", "checked",
          "maker_text", "package", "keywords", "parameters")

# Whose site serves a sheet, by host, for the makers the catalogue knows. A link to a distributor or an
# archive (mouser.com, datasheetarchive.com) is a link, not a maker.
HOSTS = {
    "ti.com": "texas-instruments", "ti.com.cn": "texas-instruments", "national.com": "national", "burr-brown.com": "burr-brown",
    "onsemi.com": "onsemi", "onsemi.cn": "onsemi", "fairchildsemi.com": "fairchild", "motorola.com": "motorola",
    "nxp.com": "nxp", "nexperia.com": "nexperia", "semiconductors.philips.com": "philips",
    "vishay.com": "vishay", "analog.com": "analog-devices", "linear.com": "linear-technology",
    "maximintegrated.com": "maxim", "maxim-ic.com": "maxim", "toshiba.semicon-storage.com": "toshiba",
    "renesas.com": "renesas", "intersil.com": "intersil", "zetex.com": "zetex", "diodes.com": "diodes",
    "st.com": "stmicroelectronics", "infineon.com": "infineon", "irf.com": "international-rectifier",
    "panasonic.com": "panasonic", "rohm.com": "rohm", "nisshinbo-microdevices.co.jp": "nisshinbo",
    "njr.com": "new-japan-radio", "thatcorp.com": "that", "microchip.com": "microchip",
    "microsemi.com": "microsemi", "wolfspeed.com": "wolfspeed", "broadcom.com": "broadcom",
    "linearsystems.com": "linear-systems", "centralsemi.com": "central", "sanken-ele.co.jp": "sanken",
    "diotec.com": "diotec", "taiwansemi.com": "taiwan-semiconductor", "ttelectronics.com": "tt-electronics",
    "kec.co.kr": "kec", "cdil.com": "cdil", "jj-electronic.com": "jj-electronic",
}

# A KiCad symbol is sometimes named with its package: LM317_TO-220, L7805_TO220. The head is the part,
# the tail the package, only when the tail is plainly one.
PACKAGE_TAIL = re.compile(
    r"^(?:TO-?\d|SOT|SOIC|SOP|SO-?\d|SSOP|TSSOP|MSOP|VSSOP|DIP|PDIP|CDIP|DFN|QFN|QFP|LQFP|TQFP|PLCC|D2?PAK|DPAK|"
    r"SIP|ZIP|SC-?\d|SOD|DO-?\d|SMD|THT|TH$|HTSSOP|HSOP|WSON|SON|BGA|LGA|CSP|WLCSP|MLP|ISOWATT|TO)", re.I)

# LibrePCB writes units as words; the row writes them as the sheets do.
UNITS = {
    "none": "", "volt": "V", "millivolt": "mV", "microvolt": "µV", "kilovolt": "kV",
    "ampere": "A", "milliampere": "mA", "microampere": "µA", "nanoampere": "nA", "picoampere": "pA",
    "watt": "W", "milliwatt": "mW", "microwatt": "µW", "kilowatt": "kW",
    "ohm": "Ω", "milliohm": "mΩ", "kiloohm": "kΩ", "megaohm": "MΩ", "gigaohm": "GΩ",
    "farad": "F", "millifarad": "mF", "microfarad": "µF", "nanofarad": "nF", "picofarad": "pF",
    "henry": "H", "millihenry": "mH", "microhenry": "µH", "nanohenry": "nH",
    "hertz": "Hz", "kilohertz": "kHz", "megahertz": "MHz", "gigahertz": "GHz",
    "second": "s", "millisecond": "ms", "microsecond": "µs", "nanosecond": "ns", "picosecond": "ps",
    "celsius": "°C", "kelvin": "K", "percent": "%", "ppm": "ppm", "decibel": "dB",
}


# --- which names are parts ----------------------------------------------------------------------------

def known_names() -> dict[str, str]:
    """Every part number the project knows, by its upper-case form, with the spelling the index uses."""
    out: dict[str, str] = {}
    for k in sorted(known()):
        out.setdefault(k.upper(), k)
    return out


def is_part_like(name: str) -> bool:
    """A library also names battery clips "53" and generic symbols "LED": a part number here has a letter
    and a digit both. A bare number a census happens to list is not taken on that coincidence."""
    return bool(re.search(r"[A-Za-z]", name) and re.search(r"\d", name))


def indexed(name: str, names: dict[str, str]) -> str:
    """The index's spelling of `name` when the index knows it, else ""."""
    n = name.strip()
    return names.get(n.upper(), "") if is_part_like(n) else ""


def host_maker(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    for h, maker in HOSTS.items():
        if host == h or host.endswith("." + h):
            return maker
    return ""


def maker_of(text: str, url: str = "") -> str:
    """The maker named, by the catalogue's aliases; when nobody is named, the one whose site serves the
    sheet. A maker the catalogue does not know is still the maker named: the sheet's host does not stand
    in for it (Comchip's 1N4007 is not onsemi's because the device links onsemi's sheet)."""
    if text:
        return catalogue.maker_of(text)[0]
    return host_maker(url) if url else ""


def row(**kw) -> dict:
    r = {k: "" for k in FIELDS}
    r.update(kw)
    r["checked"] = today()
    return r


# --- KiCad --------------------------------------------------------------------------------------------

SYMBOL = re.compile(r'^\t\(symbol "([^"]+)"(.*?)(?=^\t\(symbol "|\Z)', re.M | re.S)
PROPERTY = re.compile(r'\(property "([^"]+)" "((?:[^"\\]|\\.)*)"')


def kicad_properties(body: str) -> dict[str, str]:
    """The symbol's own properties; a derived symbol (`extends`) carries its own copy of each."""
    return {k: v.replace('\\"', '"') for k, v in PROPERTY.findall(body)}


def kicad_name(name: str, names: dict[str, str]) -> tuple[str, str]:
    """The indexed part a symbol name is, and the package its name carries when the part is only the head:
    "BC547" -> (BC547, ""); "LM317_TO-220" -> (LM317, TO-220); "Q_NPN_CBE" -> ("", "")."""
    part = indexed(name, names)
    if part:
        return part, ""
    head, sep, tail = name.partition("_")
    if sep and PACKAGE_TAIL.match(tail):
        part = indexed(head, names)
        if part:
            return part, tail
    return "", ""


def kicad_rows(lib: str, text: str, names: dict[str, str], source: str, ref: str, page: str) -> Iterator[dict]:
    """Each indexed part a `.kicad_sym` library names, with the data sheet, description, footprint and
    keywords its symbol carries. `lib` is the library's file stem (Transistor_BJT)."""
    for m in SYMBOL.finditer(text):
        part, pkg = kicad_name(m.group(1), names)
        if not part:
            continue
        p = kicad_properties(m.group(2))
        url = p.get("Datasheet", "").strip()
        url = url if url.lower().startswith("http") else ""
        package = p.get("Footprint", "").strip() or pkg          # Package_TO_SOT_THT:TO-92_Inline, as KiCad names it
        maker_text = p.get("Manufacturer", "").strip()
        params = f"MPN {p['MPN'].strip()}" if p.get("MPN", "").strip() else ""
        name = p.get("Description", "").strip()
        if not url and not name:                    # a bare symbol: nothing a reader can follow
            continue
        yield row(part=part, source=source, maker=maker_of(maker_text, url), category=lib, name=name, revision=ref, url=url,
                  page=page.format(ref=ref, path=f"{lib}.kicad_sym"), maker_text=maker_text, package=package,
                  keywords=p.get("ki_keywords", "").strip(), parameters=params)


def read_kicad(root: Path, names: dict[str, str], source: str, ref: str, page: str) -> Iterator[dict]:
    for f in sorted(root.glob("*.kicad_sym")):
        yield from kicad_rows(f.stem, f.read_text(encoding="utf-8", errors="replace"), names, source, ref, page)


# --- Horizon EDA --------------------------------------------------------------------------------------

def horizon_field(j: dict, key: str) -> str:
    """A pool field is `[inherited, value]`. After `horizon_resolve` an inherited one carries the base
    part's value; one still flagged inherited has no base to read from and is left blank."""
    v = j.get(key)
    if isinstance(v, list) and len(v) == 2:
        return "" if v[0] else str(v[1]).strip()
    return str(v or "").strip()


def horizon_resolve(j: dict, by_uuid: dict[str, dict], depth: int = 0) -> dict:
    """The part with what it inherits filled in: a field flagged inherited, or absent, is the base part's
    (AMS1117-3.3 takes its sheet and package from AMS1117), and tags add to the base's when `inherit_tags`."""
    base = by_uuid.get(j.get("base", "")) if j.get("base") else None
    if base is None or depth > 8:
        return j
    base = horizon_resolve(base, by_uuid, depth + 1)
    out = dict(base)
    for k, v in j.items():
        if isinstance(v, list) and len(v) == 2 and v[0] is True:
            continue
        out[k] = v
    if j.get("inherit_tags"):
        out["tags"] = sorted(set(base.get("tags") or []) | set(j.get("tags") or []))
    return out


def horizon_packages(root: Path) -> dict[str, str]:
    """Package name by uuid, from the pool's packages/ tree."""
    out = {}
    for f in root.glob("packages/**/package.json"):
        try:
            j = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if j.get("uuid") and j.get("name"):
            out[j["uuid"]] = j["name"]
    return out


def horizon_row(j: dict, relpath: str, packages: dict[str, str], names: dict[str, str], source: str, ref: str,
                page: str) -> dict | None:
    """One pool part (`parts/<category>/.../<file>.json`) as a row, when its MPN is a part the index knows."""
    mpn = horizon_field(j, "MPN")
    part = indexed(mpn, names)
    if not part:
        return None
    url = horizon_field(j, "datasheet")
    url = url if url.lower().startswith("http") else ""
    maker_text = horizon_field(j, "manufacturer")
    params = [f"{k} {v}" for k, v in (j.get("parametric") or {}).items() if k != "table" and str(v).strip()]
    if mpn.upper() != part.upper():
        params.insert(0, f"MPN {mpn}")
    cat = "/".join(relpath.split("/")[1:-1])          # parts/ic/opamp/ti/ne5532d.json -> ic/opamp/ti
    return row(part=part, source=source, maker=maker_of(maker_text, url), category=cat,
               name=horizon_field(j, "description"), revision=ref, url=url, page=page.format(ref=ref, path=relpath),
               maker_text=maker_text, package=packages.get(j.get("package", ""), ""),
               keywords=", ".join(j.get("tags") or []), parameters="; ".join(params))


def read_horizon(root: Path, names: dict[str, str], source: str, ref: str, page: str) -> Iterator[dict]:
    packages = horizon_packages(root)
    parts: list[tuple[str, dict]] = []
    for f in sorted(root.glob("parts/**/*.json")):
        try:
            j = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if j.get("type", "part") == "part":
            parts.append((f.relative_to(root).as_posix(), j))
    by_uuid = {j["uuid"]: j for _, j in parts if j.get("uuid")}
    for relpath, j in parts:
        r = horizon_row(horizon_resolve(j, by_uuid), relpath, packages, names, source, ref, page)
        if r:
            yield r


# --- LibrePCB -----------------------------------------------------------------------------------------

LP_NAME = re.compile(r'^\s*\(name "((?:[^"\\]|\\.)*)"', re.M)
LP_FIELD = re.compile(r'^\s*\((description|keywords|package) "?((?:[^"\\)]|\\.)*)"?\)', re.M)
LP_RESOURCE = re.compile(r'\(resource "((?:[^"\\]|\\.)*)"[^()]*\(mediatype "[^"]*"\)\s*\(url "([^"]*)"\)', re.S)
LP_PART = re.compile(r'^\s*\(part "((?:[^"\\]|\\.)*)" \(manufacturer "((?:[^"\\]|\\.)*)"\)(.*?)^\s*\)', re.M | re.S)
LP_ATTR = re.compile(r'\(attribute "([^"]+)" \(type \w+\) \(unit (\w+)\) \(value "((?:[^"\\]|\\.)*)"\)')


def librepcb_packages(root: Path) -> dict[str, str]:
    out = {}
    for f in root.glob("pkg/*/package.lp"):
        head = f.read_text(encoding="utf-8", errors="replace")[:400]
        m = LP_NAME.search(head)
        if m:
            out[f.parent.name] = m.group(1)
    return out


def librepcb_rows(text: str, relpath: str, packages: dict[str, str], names: dict[str, str], source: str,
                  ref: str, page: str) -> Iterator[dict]:
    """A device (`dev/<uuid>/device.lp`) names a part the index knows, or one of its orderable parts does.
    One row per manufacturer the device lists, with the MPNs and the typed values; a value that differs
    between a manufacturer's MPNs shows every value it takes."""
    m = LP_NAME.search(text)
    if not m:
        return
    device = m.group(1)
    fields = {k: v for k, v in LP_FIELD.findall(text)}
    parts = LP_PART.findall(text)
    part = indexed(device, names) or next((indexed(mpn, names) for mpn, _, _ in parts), "")
    if not part:
        return
    urls = [u for _, u in LP_RESOURCE.findall(text) if u.lower().startswith("http")]
    url = urls[0] if urls else ""
    by_maker: dict[str, tuple[list[str], dict[str, list[str]], list[str]]] = {}
    for mpn, maker_text, body in parts:
        mpns, attrs, status = by_maker.setdefault(maker_text, ([], {}, []))
        mpns.append(mpn)
        for name, unit, value in LP_ATTR.findall(body):
            if name == "PACKAGING":
                continue
            if name == "STATUS":
                if value not in status:
                    status.append(value)
                continue
            text_value = f"{value} {UNITS.get(unit, unit)}".strip()
            if text_value not in attrs.setdefault(name, []):
                attrs[name].append(text_value)
    common = dict(category=fields.get("keywords", ""), name=fields.get("description", "").split("\\n")[0].strip(),
                  revision=ref, url=url, page=page.format(ref=ref, path=relpath),
                  package=packages.get(fields.get("package", ""), ""), keywords=fields.get("keywords", ""))
    if not by_maker:
        yield row(part=part, source=source, maker=host_maker(url), **common)
        return
    for maker_text, (mpns, attrs, status) in by_maker.items():
        params = [f"MPN {', '.join(mpns)}"] + [f"{k} {' / '.join(v)}" for k, v in attrs.items()]
        yield row(part=part, source=source, maker=maker_of(maker_text, url), status=", ".join(status),
                  maker_text=maker_text, parameters="; ".join(params), **common)


def read_librepcb(root: Path, names: dict[str, str], source: str, ref: str, page: str) -> Iterator[dict]:
    packages = librepcb_packages(root)
    for f in sorted(root.glob("dev/*/device.lp")):
        yield from librepcb_rows(f.read_text(encoding="utf-8", errors="replace"), f.relative_to(root).as_posix(),
                                 packages, names, source, ref, page)


# --- KiCad footprints ---------------------------------------------------------------------------------

PACKAGE_FIELDS = ("footprint", "source", "description", "tags", "mounting", "pads", "pad_spacing_mm", "drill_mm",
                  "body_x_mm", "body_y_mm", "courtyard_x_mm", "courtyard_y_mm", "reference", "model_3d", "page",
                  "revision", "checked")
TOKEN = re.compile(r'"(?:[^"\\]|\\.)*"|[()]|[^\s()"]+')
GRAPHICS = {"fp_line", "fp_rect", "fp_circle", "fp_arc", "fp_poly"}


def sexp(text: str) -> list:
    """A KiCad file as nested lists: `(a "b" (c 1))` -> ['a', 'b', ['c', '1']]."""
    stack: list[list] = [[]]
    for tok in TOKEN.findall(text):
        if tok == "(":
            stack.append([])
        elif tok == ")":
            done = stack.pop()
            stack[-1].append(done)
        else:
            stack[-1].append(tok[1:-1].replace('\\"', '"') if tok.startswith('"') else tok)
    return stack[0][0] if stack[0] else []


def children(node: list, name: str) -> Iterator[list]:
    for c in node[1:]:
        if isinstance(c, list) and c and c[0] == name:
            yield c


def first(node: list, name: str, default: str = "") -> str:
    c = next(children(node, name), None)
    return str(c[1]) if c and len(c) > 1 else default


def layer_of(item: list) -> str:
    return first(item, "layer")


def points(item: list) -> list[tuple[float, float]]:
    """Every coordinate a graphic item is drawn through; a circle by its centre and a point on it, an arc
    by its three points, so a bounding box over them is the outline's within a line width."""
    out = []
    for c in item[1:]:
        if not isinstance(c, list) or not c:
            continue
        if c[0] in ("start", "end", "mid", "center") and len(c) >= 3:
            out.append((float(c[1]), float(c[2])))
        elif c[0] == "pts":
            out += [(float(p[1]), float(p[2])) for p in c[1:] if isinstance(p, list) and p[0] == "xy"]
    if item[0] == "fp_circle" and len(out) == 2:          # centre and a point on the rim: the box is the disc
        (cx, cy), (px, py) = out
        r = ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5
        out = [(cx - r, cy - r), (cx + r, cy + r)]
    return out


def extent(fp: list, layer: str) -> tuple[str, str]:
    """The width and height, in mm, of everything drawn on `layer` (text aside)."""
    pts = [p for item in fp[1:] if isinstance(item, list) and item and item[0] in GRAPHICS and layer_of(item) == layer
           for p in points(item)]
    if not pts:
        return "", ""
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return f"{max(xs) - min(xs):.2f}", f"{max(ys) - min(ys):.2f}"


def pad_facts(fp: list) -> tuple[int, str, str]:
    """How many pads, the smallest centre-to-centre distance between two of them (the pitch along a row
    of pins; on a SOT-23, whose middle pin is on the other side, twice the pitch), and the drill."""
    pads = [p for p in children(fp, "pad") if len(p) > 1 and str(p[1]) != ""]
    at = []
    drills = set()
    for p in pads:
        a = next(children(p, "at"), None)
        if a and len(a) >= 3:
            at.append((float(a[1]), float(a[2])))
        d = next(children(p, "drill"), None)
        if d and len(d) > 1 and not isinstance(d[1], list):
            drills.add(f"{float(d[1]):g}")
    best = None
    for i, (x1, y1) in enumerate(at):
        for x2, y2 in at[i + 1:]:
            dist = ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
            if dist > 0.01 and (best is None or dist < best):
                best = dist
    return len(pads), f"{best:.2f}" if best else "", " / ".join(sorted(drills))


REFERENCE = re.compile(r"https?://[^\s,)]+|(?:see|from|per|after)\s+([^,()]+?\.pdf)|JEDEC\s+[A-Z]{1,3}-?\d+[A-Z]*", re.I)


def footprint_row(text: str, relpath: str, source: str, ref: str, page: str) -> dict | None:
    """One `.kicad_mod` as a row: what the footprint says about the package, never the drawing itself."""
    fp = sexp(text)
    if not fp or fp[0] not in ("footprint", "module"):
        return None
    lib = relpath.split("/")[0].removesuffix(".pretty")
    descr = first(fp, "descr")
    refs = [re.sub(r"^(?:see|from|per|after)\s+", "", m.group(0), flags=re.I) for m in REFERENCE.finditer(descr)]
    bx, by = extent(fp, "F.Fab")
    cx, cy = extent(fp, "F.CrtYd")
    n, pitch, drill = pad_facts(fp)
    model = first(fp, "model").rsplit("/", 1)[-1]
    return {"footprint": f"{lib}:{fp[1]}", "source": source, "description": descr, "tags": first(fp, "tags"),
            "mounting": first(fp, "attr").replace("through_hole", "through hole"), "pads": str(n),
            "pad_spacing_mm": pitch, "drill_mm": drill, "body_x_mm": bx, "body_y_mm": by, "courtyard_x_mm": cx,
            "courtyard_y_mm": cy, "reference": "; ".join(refs), "model_3d": model,
            "page": page.format(ref=ref, path=relpath), "revision": ref, "checked": today()}


def footprints_wanted() -> set[str]:
    """The footprints the indexed parts' KiCad symbols name, from the symbols' own table."""
    p = datasheet_catalogue("kicad_symbols")
    if not p.exists():
        return set()
    with open(p, encoding="utf-8") as f:
        return {r["package"] for r in csv.DictReader(f) if ":" in r.get("package", "")}


def read_footprints(root: Path, names: dict[str, str], source: str, ref: str, page: str) -> Iterator[dict]:
    wanted = footprints_wanted()
    for name in sorted(wanted):
        lib, _, fp = name.partition(":")
        f = root / f"{lib}.pretty" / f"{fp}.kicad_mod"
        if not f.is_file():
            continue
        r = footprint_row(f.read_text(encoding="utf-8", errors="replace"), f.relative_to(root).as_posix(), source, ref,
                          page)
        if r:
            yield r


READERS = {"kicad_symbols": read_kicad, "horizon_pool": read_horizon, "librepcb_base": read_librepcb,
           "kicad_footprints": read_footprints}
# Where each source's rows go and what their columns are: parts into the catalogue, packages into their own table.
TABLES = {"kicad_footprints": (datasheet_packages, PACKAGE_FIELDS)}


# --- the clone, the run, the table --------------------------------------------------------------------

def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()


def checkout(source: str, entry: dict, refresh: bool) -> tuple[Path, str]:
    """The library's clone in the private tree, shallow and at the registry's `ref`, and the revision the
    rows cite: the tag when `ref` is one, else the commit's date and short hash."""
    root = datasheets_cache(source)
    if not (root / ".git").is_dir():
        root.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "-q", "--depth", "1", "--branch", entry["ref"], entry["repo"], str(root)],
                       check=True)
    elif refresh:
        git(root, "fetch", "-q", "--depth", "1", "origin", entry["ref"])
        git(root, "checkout", "-q", "FETCH_HEAD")
    tags = git(root, "tag", "--points-at", "HEAD").split()
    sha = git(root, "rev-parse", "HEAD")
    date = git(root, "log", "-1", "--format=%cs")
    return root, revision(entry["ref"], tags, sha, date)


def revision(ref: str, tags: list[str], sha: str, date: str) -> tuple[str, str]:
    """What the rows cite and what their links use: the tag, when `ref` is one the clone sits on; else the
    commit's date and short hash to read, and the full hash in the link, which a branch name would not
    keep pointing at."""
    if ref in tags:
        return ref, ref
    return f"{date} ({sha[:7]})", sha


def write(source: str, rows: list[dict]) -> Path:
    table, fields = TABLES.get(source, (datasheet_catalogue, FIELDS))
    p = table(source)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for r in sorted(rows, key=lambda r: tuple(r.get(k, "") for k in fields[:1] + fields[2:5])):
            w.writerow({k: r.get(k, "") for k in fields})
    tmp.replace(p)
    return p


def run(source: str, entry: dict, refresh: bool = False) -> list[dict]:
    root, (ref, link_ref) = checkout(source, entry, refresh)
    names = known_names()
    seen: set[tuple] = set()
    out = []
    _, fields = TABLES.get(source, (datasheet_catalogue, FIELDS))
    page = entry["page"].replace("{ref}", link_ref)            # the readers fill in {path}
    for r in READERS[source](root, names, source, ref, page):
        key = tuple(r.get(k, "") for k in fields)
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="sei datasheets libraries")
    ap.add_argument("--source", action="append", help="only these sources (repeatable)")
    ap.add_argument("--refresh", action="store_true", help="pull the library again before reading it")
    a = ap.parse_args(argv)
    reg = registry()
    names = a.source or [s for s in READERS if (reg.get(s) or {}).get("status") == "active"]
    for s in names:
        if s not in READERS or s not in reg:
            print(f"{s}: not a registered library with a reader", file=sys.stderr)
            return 2
        if reg[s].get("status") in ("paused", "blocked"):
            print(f"{s}: {reg[s]['status']} — see its notes in the registry; not read", file=sys.stderr)
            continue
        rows = run(s, reg[s], a.refresh)
        p = write(s, rows)
        if s in TABLES:
            sized = sum(1 for r in rows if r["body_x_mm"])
            print(f"{s} ({rows[0]['revision'] if rows else '-'}): {len(rows)} footprints the indexed parts come in, "
                  f"{sized} with a body size, {sum(1 for r in rows if r['reference'])} naming their drawing -> {p}")
            continue
        parts = {r["part"] for r in rows}
        with_url = {r["part"] for r in rows if r["url"]}
        with_values = {r["part"] for r in rows if r["parameters"]}
        print(f"{s} ({rows[0]['revision'] if rows else '-'}): {len(rows)} rows for {len(parts)} known parts, "
              f"{len(with_url)} with a data sheet link, {len(with_values)} with typed values -> {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
