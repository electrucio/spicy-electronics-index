"""Rows for data/parts/relations.csv from the forum extract of Aksenov, Nefedov and Yushin's table of foreign
transistors and their approximate Soviet analogues (references S98 and S99). See README.md beside this file.

    uv run python -I docs/surveys/aksenov-mrb1190/extract.py <extract.pdf> > rows.csv

Reads the PDF (never committed: rule 1) with PyMuPDF, walks the three columns the text layer yields in turn
(foreign type, package, approximate domestic analogue), keeps the pairs that touch a part the index knows or
wants, and prints them as relation rows, the Soviet part transliterated the way the index already names
MP42B and P416 (Б B, В V, Г G, Д D, Е E, Ж ZH, И I, К K, М M, П P, Т T), with the Cyrillic kept in the note.
What it drops is said on stderr: a cell typed in Latin letters whose suffix could be Б or В, and any name
that does not look like a Soviet type number once the typist's З-for-3 and О-for-0 are put right.
"""
import csv
import re
import sys
from pathlib import Path

import pymupdf

from spicy_electronics_index.core.config import known_parts, wanted_parts

CYR = re.compile(r"[Ѐ-ӿ]")
LOOK = str.maketrans("АВСЕНКМОРТХУІ", "ABCEHKMOPTXYI")          # Cyrillic look-alikes typed in a Latin column
PKG_LOOK = str.maketrans("АВСЕНКМОРТХУІПЗ", "ABCEHKMOPTXYIP3")
LAT2CYR = str.maketrans("KTMPAEDG", "КТМПАЕДГ")                 # the unambiguous letters of a Latin-typed cell
TRANSLIT = str.maketrans({"А": "A", "Б": "B", "В": "V", "Г": "G", "Д": "D", "Е": "E", "Ж": "ZH", "З": "Z", "И": "I",
                          "Й": "Y", "К": "K", "Л": "L", "М": "M", "Н": "N", "О": "O", "П": "P", "Р": "R", "С": "S",
                          "Т": "T", "У": "U", "Ф": "F", "Х": "KH", "Ц": "TS", "Ч": "CH", "Ш": "SH", "Щ": "SHCH",
                          "Ы": "Y", "Э": "E", "Ю": "YU", "Я": "YA"})
SOV = re.compile(r"^(?:[КK][ТT]|[ГG][ТT]|FT|[МM][ГG][ТT]|[МM][ПP]|[ПP]\s?[\dЗО]|[12][ТT]\d)")
SOV_NAME = re.compile(r"^[А-Я]{1,3}\d{2,4}[А-Я]{0,2}\d?$")      # КТ3129Б9: the 9 is a package
HEADERS = {"ЗАРУБЕЖНЫЕ ТРАНЗИСТОРЫ И ИХ ОТЕЧЕСТВЕННЫЕ АНАЛОГИ", "Зарубежный транзистор", "Зарубежной транзистор",
           "Тип прибора", "Корпус", "Приближенный", "отечественный аналог", "отечественный", "аналог"}
SUFFIXES = "АБВГДЕЖИ"                                          # the order a range like АМ—ГМ runs through
REFS, STATUS = "S98 S99", "draft"


def trim(s: str) -> str:
    return re.sub(r"^[\s.\-–]+|[\s.\-–']+$", "", s)


def digits_right(name: str) -> str:
    """ВСЗОО was BC300 and ГТЗЗОЖ ГТ330Ж: a З or О among the digits is a 3 or a 0."""
    m = re.match(r"^([^\d]*?)([\dЗО]+)(.*)$", name)
    if not m or not re.search(r"\d", m.group(2)) and len(m.group(2)) < 2:
        return name
    return m.group(1) + m.group(2).replace("З", "3").replace("О", "0") + m.group(3)


def foreign(line: str) -> str | None:
    f = digits_right(trim(line).translate(LOOK).replace(" ", ""))
    return f if re.match(r"^[A-Z0-9][A-Z0-9/.-]*$", f) and not SOV.match(f) else None


def package(line: str) -> str | None:
    p = line.translate(PKG_LOOK).replace(" ", "")
    return p if not CYR.search(p) else None


def soviet_names(cell: str) -> tuple[list[str], list[str]]:
    """The type numbers in one analogue cell — "МП42Б, МП20А", "КТ373 (Б, В)", "KT818 (АМ—ГМ)" — and the
    names given up on."""
    cell = trim(cell)
    m = re.match(r"^(\S+?)\s*\(([^)]*)\)$", cell)
    names: list[str] = []
    if m:
        base, inside = m.group(1), m.group(2)
        for item in (x.strip() for x in re.split(r"[,;]", inside)):
            r = re.match(r"^([А-Я])(М?)[—–-]([А-Я])(М?)$", item)
            if r and r.group(1) in SUFFIXES and r.group(3) in SUFFIXES:
                a, b = SUFFIXES.index(r.group(1)), SUFFIXES.index(r.group(3))
                names += [base + SUFFIXES[k] + r.group(2) for k in range(a, b + 1)]
            elif item:
                names.append(base + item)
    else:
        names = [x.strip(" .") for x in re.split(r"[,;]", cell) if x.strip(" .")]
    kept, dropped = [], []
    for n in names:
        n = digits_right(n.replace(" ", ""))
        head = n[:3] if n[:3] in ("MGT",) else n[:2]
        if head in ("KT", "GT", "MP", "FT", "MGT") or not CYR.search(n):      # typed in Latin letters
            tail = n[len(head):]
            if head == "FT" or re.search(r"[A-Z]", tail.translate(LAT2CYR)):  # a B, C, V... nobody can read back
                dropped.append(n)
                continue
            n = head.translate(LAT2CYR) + tail.translate(LAT2CYR)
        (kept if SOV_NAME.match(n) else dropped).append(n)
    return kept, dropped


def triples(pdf: Path) -> tuple[list[tuple[str, str, str]], list[str]]:
    lines = [x.strip() for page in pymupdf.open(pdf) for x in page.get_text().splitlines() if x.strip()]
    body = [x for x in lines if x not in HEADERS and not x.startswith(("Для создания", "Издательство", "(авторы"))]
    out, unparsed, i = [], [], 0
    while i < len(body):
        f = foreign(body[i])
        if f and i + 2 < len(body) and package(body[i + 1]) is not None and (CYR.search(body[i + 2]) or SOV.match(body[i + 2])):
            out.append((f, package(body[i + 1]) or "", body[i + 2]))
            i += 3
        else:
            unparsed.append(body[i])
            i += 1
    return out, unparsed


def parts_of_interest() -> dict[str, str]:
    """Every part the index knows or wants, with its kind."""
    out = {}
    for path in (wanted_parts(), known_parts()):
        with open(path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                out[r["part"]] = r.get("kind", "")
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    rows, unparsed = triples(Path(argv[1]))
    index = parts_of_interest()
    pairs: dict[tuple[str, str], str] = {}
    dropped: list[tuple[str, str]] = []
    for f, pkg, cell in rows:
        kept, lost = soviet_names(cell)
        dropped += [(f, n) for n in lost if f in index]
        for s in kept:
            pairs.setdefault((f, s), pkg)
    w = csv.writer(sys.stdout, lineterminator="\n")
    n = 0
    for (f, s), pkg in sorted(pairs.items()):
        ts = s.translate(TRANSLIT)
        if f not in index and ts not in index:
            continue
        note = f"Aksenov, Nefedov and Yushin (1992): {s} is the approximate domestic analogue of the {f}" + (f", package {pkg}" if pkg else "")
        w.writerow([ts, "approximate_analogue_of", f, REFS, note, STATUS])
        n += 1
    print(f"{len(rows)} table rows read, {len(unparsed)} lines not part of a row, {len(pairs)} pairs, "
          f"{n} rows touching the index, {len(dropped)} analogue names dropped as unreadable for parts the index "
          f"has: {' '.join(f'{f}:{s}' for f, s in dropped)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
