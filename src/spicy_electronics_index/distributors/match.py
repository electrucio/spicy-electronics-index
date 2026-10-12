"""Which of a distributor's products are the part a reader asked about. Pure functions, no I/O.

A distributor files what it sells under its own symbol and the maker's number, and a search for a bare
type returns the family around it with noise mixed in: `LM833` brings the LM8330 keypad controller,
`J201` brings fuses and RJ45 sockets whose numbers contain the letters. A wrong offer is worse than
none (rule 4), so a product is kept only when one of its maker numbers *is* the part or is the part
followed by a suffix that looks like a grade or package: a letter first, or a separator, then at most
seven more characters. `TL072CP` and `BD139-16` are TL072 and BD139; `LM8330` is not LM833, because a
digit runs straight on; `MMBFJ201` is not J201, because the part is not its prefix.
"""
from __future__ import annotations

import re

NOT_ALNUM = re.compile(r"[^A-Z0-9]")
# What may follow the part number in a maker's number that is still the same part: a letter (a grade, a
# package, a packing) and at most seven more characters, or a separator and then anything that short —
# BD139-16 is a BD139 selected for gain, LM8330 is another device because a digit runs straight on.
SUFFIX = re.compile(r"^(?:[A-Z][A-Z0-9/-]{0,7}|[-/][A-Z0-9][A-Z0-9/-]{0,7})$")
CAP = 40            # offers published per part; past this the rest are counted, not listed


def norm(s: str) -> str:
    """Upper case, letters and digits only: `2sc1815-gr` and `2SC1815 GR` are the same number."""
    return NOT_ALNUM.sub("", (s or "").upper())


def rest_after(number: str, part: str) -> str | None:
    """What follows `part` in `number`, separators in `number` skipped while matching; None when `part`
    is not its prefix. `rest_after("TL072CD-ST", "TL072")` is `"CD-ST"`."""
    want, up, i, j = norm(part), (number or "").upper(), 0, 0
    if not want:
        return None
    while j < len(up) and i < len(want):
        c = up[j]
        if c.isalnum():
            if c != want[i]:
                return None
            i += 1
        j += 1
    return up[j:] if i == len(want) else None


def keep(part: str, element: dict) -> str | None:
    """'exact' when a maker number of the product is the part, 'variant' when one is the part with a
    grade or package suffix, None otherwise."""
    best = None
    # The distributor's own symbol is a maker number too when it is the bare type: TME files the Toshiba
    # 2SC1815 as `2SC1815` and, once withdrawn, drops the maker's number from the record altogether.
    if norm(element.get("symbol") or "") == norm(part) and norm(part):
        return "exact"
    for number in element.get("manufacturer_symbols") or []:
        rest = rest_after(number, part)
        if rest is None:
            continue
        if rest == "":
            return "exact"
        if SUFFIX.match(rest):
            best = "variant"
    return best


def collect(part: str, exact: list[dict], searched: list[dict], ok=None) -> dict[str, tuple[dict, str]]:
    """The products that are this part, by distributor symbol: those the exact look-up returned, then
    those of the family search that pass `keep`. An exact match wins over a variant for the same symbol.

    `ok(element)`, when given, is the last word: the number alone cannot tell a 6550 valve from a 6550
    socket wrench or a 300B from an N connector, but the distributor's category can, and the caller
    knows which categories the part's kind may sit in."""
    found: dict[str, tuple[dict, str]] = {}
    for e in exact:
        if e.get("symbol") and keep(part, e) == "exact" and (ok is None or ok(e)):
            found[e["symbol"]] = (e, "exact")
    for e in searched:
        m = keep(part, e)
        if m and e.get("symbol") and (e["symbol"] not in found or m == "exact") and (ok is None or ok(e)):
            found[e["symbol"]] = (e, m)
    return found


def top_level(categories: list[dict]) -> dict[int, str]:
    """Each category id → the name of its first-level ancestor (Semiconductors, Connectors, Passives…).
    The distributor's list is flat, every node naming its parent; the root names itself and has no name."""
    by = {c["id"]: c for c in categories if "id" in c}
    out: dict[int, str] = {}
    for cid in by:
        node, seen = cid, set()
        while node in by and node not in seen:
            seen.add(node)
            parent = by[node].get("parent_id")
            if parent is None or parent == node or parent not in by or by[parent].get("parent_id") in (None, parent):
                break
            node = parent
        out[cid] = by[node].get("name", "")
    return out


def price_breaks(prices: dict | None) -> str:
    """`amount:price;…` as the distributor returned them: `1:0.813;4:0.708;10:0.629`."""
    return ";".join(f"{p.get('amount')}:{p.get('price')}" for p in ((prices or {}).get("elements") or []))


def in_stock(row: dict) -> bool:
    try:
        return int(row.get("stock") or 0) > 0
    except ValueError:
        return False


def rank(rows: list[dict]) -> list[dict]:
    """Exact numbers first, then what is in stock, then by symbol; at most CAP of them."""
    return sorted(rows, key=lambda r: (r.get("match") != "exact", not in_stock(r), r.get("symbol", "")))[:CAP]
