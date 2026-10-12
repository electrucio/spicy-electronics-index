"""What TME, a distributor, sells of the parts this index holds: order numbers, their status, stock and
prices, as its API answered on the day recorded in `checked`.

    sei distributors tme [--part TL072] [--top-per-kind 100] [--limit N] [--max-age 30] [--refresh]

A reader who finds a part here asks next whether it can still be bought, and roughly for how much.
TME's API terms (2026-07-01) license showing its data on a website of one's own, provided the notice in
the registry is shown beside it and nothing is derived from it; so the tables hold TME's values verbatim
with a date, and the page says "net prices, as TME returned them on ...". Mouser, Digi-Key and Farnell
forbid storing their data, and are not asked.

Per part, four endpoints: `/products` by maker number (exact), `/products/search` by phrase (the family:
TL072CP, TL072IP, TL072CDT, with noise that `match.keep` drops), then `/products/data` (stock and price
breaks), `/products/parameters` and `/products/files` for the symbols kept, fifty symbols a call. Every
answer is kept whole, gzipped, in the private tree (`distributor_cache`): a new use of a field costs a
re-read, not a call, and TME's right to have its data deleted (§8.10) is met by deleting one directory.
What is published is a few fields per order number — never the description TME wrote, never a photo
file, only its address.

The ledger keeps one row per part. `match` is versioned on the filter rules; `data` is versioned on the
table's columns and also ages: after `max_age` days a part's prices and stock are asked for again. A
part TME has nothing for gets one row with an empty symbol, so the page can say "not at TME on <date>".
"""
from __future__ import annotations

import argparse
import base64
import csv
import gzip
import json
import os
import sys
import time
from collections import defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

import yaml

from spicy_electronics_index.core import http
from spicy_electronics_index.core.config import (
    distributor_cache,
    distributors_files,
    distributors_registry,
    distributors_state,
    distributors_table,
    known_parts,
    schematics_parts,
)
from spicy_electronics_index.core.ledger import Ledger, today
from spicy_electronics_index.distributors import match

# Credentials live outside the repository (rule 6) and are never printed. The environment moves them.
TOKEN_FILE = Path(os.environ.get("SEI_TME_TOKEN", "~/.config/spicy-electronics-index/tme_api_token")).expanduser()
SECRET_FILE = Path(os.environ.get("SEI_TME_SECRET", "~/.config/spicy-electronics-index/tme_api_secret")).expanduser()

DISTRIBUTOR = "tme"
STAGES = ("match", "data", "params", "files")
VERSIONED = ("match", "data")
FIELDS = ("key", "match_at", "match_v", "n_exact", "n_variant", "data_at", "data_v", "params_at", "files_at",
          "http", "skip_reason")
MATCH_VERSION = "3"     # the rules of distributors/match.py; 2: a product must sit in a category its kind allows;
                        # 3: the part is also asked for as a TME symbol, which is how withdrawn products come back
DATA_VERSION = "1"      # the columns of the public table
BATCH = 50              # symbols or maker numbers per call, the API's own limit
PAGES = 3               # pages of 100 read of a family search
TABLE = ("part", "symbol", "match", "manufacturer", "mpn", "category", "case", "status", "stock", "min_order",
         "multiples", "unit", "prices", "currency", "price_type", "vat_rate", "country", "photo", "checked")
FILES = ("part", "symbol", "kind", "type", "url", "file_name", "language", "checked")
PUBLISHED_DOCS = ("DTE",)   # a data sheet TME hosts; LNK is a text file holding a link, behind a bot challenge
PHOTO_SIZE = "prime"        # the size TME serves with its watermark, which §8.2 asks to keep


def registry() -> dict:
    p = distributors_registry()
    return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}) if p.exists() else {}


class Client:
    """The API with a token that renews itself. Every call goes through `core.http`, so the host pacing
    and the waits a 429 asks for are the ones every other fetch here obeys."""

    def __init__(self, entry: dict):
        self.base = str(entry.get("api", "https://api.tme.eu")).rstrip("/")
        self.country = str(entry.get("country", "ES"))
        self.currency = str(entry.get("currency", "EUR"))
        self.language = str(entry.get("language", "en"))
        self.delay = float(entry.get("delay", 0.15))
        self.data_delay = float(entry.get("data_delay", 0.5))
        self._token, self._until = "", 0.0

    @staticmethod
    def credentials() -> tuple[str, str]:
        for f in (TOKEN_FILE, SECRET_FILE):
            if not f.exists():
                raise SystemExit(f"no TME credentials: put the token in {TOKEN_FILE} and the application secret "
                                 f"in {SECRET_FILE}, or set SEI_TME_TOKEN / SEI_TME_SECRET to where they are")
        return TOKEN_FILE.read_text(encoding="utf-8").strip(), SECRET_FILE.read_text(encoding="utf-8").strip()

    def token(self) -> str:
        if self._token and time.time() < self._until - 30:
            return self._token
        tok, sec = self.credentials()
        basic = base64.b64encode(f"{tok}:{sec}".encode("utf-8")).decode("ascii")
        r = http.post(f"{self.base}/auth/token", data={"grant_type": "client_credentials"},
                      headers={"Authorization": f"Basic {basic}"}, delay=self.delay)
        if not r.ok:
            raise SystemExit(f"TME would not issue a token: HTTP {r.status} {r.why}".rstrip())
        d = json.loads(r.body)
        self._token = d["access_token"]
        self._until = time.time() + float(d.get("expires_in", 300))
        return self._token

    def _headers(self) -> dict[str, str]:
        # `request-context: anonymous`: market prices, not the prices of the account the token belongs to
        return {"Authorization": f"Bearer {self.token()}", "Accept-Language": self.language,
                "request-context": "anonymous", "Accept": "application/json"}

    def get(self, path: str, params: dict, delay: float | None = None) -> http.Response:
        url = f"{self.base}{path}?{urlencode({'country': self.country, **params}, doseq=True)}"
        pace = self.delay if delay is None else delay
        r = http.get(url, delay=pace, headers=self._headers(), timeout=60)
        if r.status == 401:          # the token aged out between two calls: one fresh token, one more try
            self._token = ""
            r = http.get(url, delay=pace, headers=self._headers(), timeout=60)
        return r


# ---- the cache: every answer, whole ---------------------------------------------------------------
def safe(part: str) -> str:
    return part.replace("/", "_")


def kept(cache: Path, part: str, what: str) -> Path:
    return cache / f"{safe(part)}.{what}.json.gz"


def keep(path: Path, payload: dict) -> None:
    path.write_bytes(gzip.compress(json.dumps(payload, ensure_ascii=False).encode("utf-8")))


def read_kept(path: Path) -> dict | None:
    return json.loads(gzip.decompress(path.read_bytes())) if path.exists() else None


def elements(body: bytes) -> list[dict]:
    try:
        return (json.loads(body).get("data") or {}).get("elements") or []
    except (ValueError, AttributeError):
        return []


def searched_elements(pages: list[dict]) -> list[dict]:
    out = []
    for pg in pages:
        out += ((pg.get("data") or {}).get("products") or {}).get("elements") or []
    return out


# ---- which parts ----------------------------------------------------------------------------------
def documents() -> dict[str, int]:
    p = schematics_parts()
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        return {r["part"]: int(r["documents"] or 0) for r in csv.DictReader(f)}


def dictionary_kinds() -> dict[str, str]:
    """The kind the dictionary files each part under, which says what the distributor may sell it as."""
    p = known_parts()
    if not p.exists():
        return {}
    kinds: dict[str, str] = {}
    with open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            k = (r.get("kind") or "").strip()
            if r.get("name") and k and k != "kind" and not k.startswith("alias of"):
                kinds[r["name"]] = k
    return kinds


def wanted(only: list[str] | None = None, top_per_kind: int = 0) -> list[str]:
    """The parts to ask about: those named, or the dictionary's parts, most printed first — or the
    `top_per_kind` most printed of each kind the dictionary files them under."""
    if only:
        return list(dict.fromkeys(only))
    docs = documents()
    kinds = dictionary_kinds()
    by_docs = lambda p: (-docs.get(p, 0), p)  # noqa: E731
    if not top_per_kind:
        return sorted(kinds, key=by_docs)
    by_kind: dict[str, list[str]] = defaultdict(list)
    for p, k in kinds.items():
        by_kind[k].append(p)
    chosen = {p for ps in by_kind.values() for p in sorted(ps, key=by_docs)[:top_per_kind]}
    return sorted(chosen, key=by_docs)


# ---- the tables -----------------------------------------------------------------------------------
def load(path: Path, key: tuple[str, ...]) -> dict[tuple, dict]:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return {tuple(r[k] for k in key): r for r in csv.DictReader(f)}


def save(path: Path, columns: tuple[str, ...], rows: dict[tuple, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
        w.writeheader()
        for k in sorted(rows):
            w.writerow({c: rows[k].get(c, "") for c in columns})
    tmp.replace(path)


def drop(rows: dict[tuple, dict], part: str) -> None:
    for k in [k for k in rows if k[0] == part]:
        del rows[k]


def with_scheme(url: str) -> str:
    return "https:" + url if url.startswith("//") else url


def photo_of(element: dict) -> str:
    return with_scheme(((element.get("assets") or {}).get("primary_photo") or {}).get(PHOTO_SIZE) or "")


def case_of(params: dict | None) -> str:
    for p in ((params or {}).get("parameters") or {}).get("elements") or []:
        if p.get("name") == "Case":
            vals = p.get("values") or []
            return str(vals[0].get("value", "")) if vals else ""
    return ""


def offer_row(part: str, symbol: str, element: dict, m: str, data: dict | None, params: dict | None,
              country: str, checked: str) -> dict:
    prices = (data or {}).get("prices") or {}
    return {
        "part": part, "symbol": symbol, "match": m,
        "manufacturer": (element.get("manufacturer") or {}).get("name", ""),
        "mpn": "; ".join(element.get("manufacturer_symbols") or []),
        "category": (element.get("category") or {}).get("name", ""),
        "case": case_of(params),
        "status": " ".join(element.get("product_status") or []),
        "stock": "" if data is None or data.get("stock_quantity") is None else str(data["stock_quantity"]),
        "min_order": element.get("minimal_amount", ""), "multiples": element.get("multiples", ""),
        "unit": (element.get("unit") or {}).get("short_name", ""),
        "prices": match.price_breaks(prices), "currency": prices.get("currency", ""),
        "price_type": prices.get("type", ""), "vat_rate": (prices.get("tax") or {}).get("rate", ""),
        "country": country, "photo": photo_of(element), "checked": checked,
    }


def none_row(part: str, country: str, checked: str) -> dict:
    return {"part": part, "symbol": "", "match": "none", "country": country, "checked": checked}


def file_rows(part: str, symbol: str, element: dict, files: dict | None, checked: str) -> list[dict]:
    out = []
    photo = photo_of(element)
    if photo:
        out.append({"part": part, "symbol": symbol, "kind": "photo", "type": PHOTO_SIZE, "url": photo,
                    "file_name": "", "language": "", "checked": checked})
    for d in ((files or {}).get("documents") or {}).get("elements") or []:
        if d.get("type") in PUBLISHED_DOCS and d.get("url"):
            out.append({"part": part, "symbol": symbol, "kind": "document", "type": d["type"],
                        "url": with_scheme(d["url"]), "file_name": d.get("file_name", ""),
                        "language": d.get("language", ""), "checked": checked})
    return out


def categories(client: Client, cache: Path, max_age: int) -> list[dict]:
    """The distributor's whole category list, asked for once per `max_age` and kept with the rest."""
    path = cache / "_categories.json.gz"
    held = read_kept(path)
    if held and not stale(held.get("asked", ""), max_age):
        return held["elements"]
    r = client.get("/products/categories/list", {})
    if not r.ok:
        if held:
            return held["elements"]
        raise SystemExit(f"TME would not list its categories: HTTP {r.status} {r.why}".rstrip())
    els = elements(r.body)
    keep(path, {"asked": today(), "elements": els})
    return els


def allowed_for(entry: dict, kind: str | None) -> set[str] | None:
    """The first-level categories a part of this kind may be sold under, from the registry; None when
    the registry sets no such rule."""
    rules = entry.get("categories")
    if not rules:
        return None
    chosen = rules.get(kind or "", None) if kind in rules else rules.get("default")
    return set(chosen or [])


def stale(when: str, max_age: int) -> bool:
    if not when:
        return True
    try:
        return (date.today() - date.fromisoformat(when)).days > max_age
    except ValueError:
        return True


def chunks(items: list, n: int):
    for i in range(0, len(items), n):
        yield items[i:i + n]


# ---- the run --------------------------------------------------------------------------------------
def run(entry: dict, parts: list[str], max_age: int = 30, refresh: bool = False, limit: int = 0,
        client: Client | None = None, reread: bool = False) -> dict[str, int]:
    """`reread`: match again from the answers kept, without asking for them — how a change of the filter
    rules (a new MATCH_VERSION) is applied to every part at no cost to the distributor."""
    led = Ledger(distributors_state(DISTRIBUTOR), stages=STAGES, fields=FIELDS, versioned=VERSIONED)
    cache = distributor_cache(DISTRIBUTOR)
    cache.mkdir(parents=True, exist_ok=True)
    table = load(distributors_table(DISTRIBUTOR), ("part", "symbol"))
    files = load(distributors_files(DISTRIBUTOR), ("part", "symbol", "kind", "url"))
    client = client or Client(entry)
    country = client.country
    counts: dict[str, int] = defaultdict(int)
    checked = today()
    kinds = dictionary_kinds()
    tops = match.top_level(categories(client, cache, max_age)) if entry.get("categories") else {}

    def ok_for(part: str):
        allowed = allowed_for(entry, kinds.get(part))
        if allowed is None:
            return None
        return lambda e: tops.get((e.get("category") or {}).get("id")) in allowed

    def flush():
        led.save()
        save(distributors_table(DISTRIBUTOR), TABLE, table)
        save(distributors_files(DISTRIBUTOR), FILES, files)

    def left(part: str, r: http.Response) -> None:
        print(f"  {part}: {r.why or r.status} — left for the next run", file=sys.stderr)
        counts["failed"] += 1

    # 1. match: who still needs it, and who matched nothing long enough ago to be asked again
    to_match = []
    for p in parts:
        r = led.get(p)
        if r and r["skip_reason"]:
            continue
        if refresh or not led.done(p, "match", version=MATCH_VERSION):
            to_match.append(p)
        elif not int(r["n_exact"] or 0) + int(r["n_variant"] or 0) and stale(r["match_at"], max_age):
            to_match.append(p)
    if limit:
        to_match = to_match[:limit]
    exact: dict[str, list[dict]] = {}
    failed: set[str] = set()
    held_pages: dict[str, list[dict]] = {}
    held_exact: set[str] = set()
    if reread:
        for p in list(to_match):
            mpns, search = read_kept(kept(cache, p, "mpns")), read_kept(kept(cache, p, "search"))
            if mpns is not None and search is not None:
                exact[p] = [e for e in mpns.get("elements", []) if match.keep(p, e) == "exact"]
                held_pages[p] = search.get("pages", [])
                if mpns.get("by") == "mpns+symbols":
                    held_exact.add(p)
    # Two exact look-ups: by the maker's number, and by TME's own symbol. The second is how a product
    # TME has withdrawn is found at all: its search no longer lists it, and its record may have lost the
    # maker's number, but the symbol `2SC1815` still answers, marked NOT_IN_OFFER — the dated evidence
    # that it was sold here once.
    for by in ("mpns[]", "symbols[]"):
        for batch in chunks([p for p in to_match if p not in held_exact and p not in failed], BATCH):
            r = client.get("/products", {by: batch})
            counts["calls"] += 1
            if r.status == 400:
                for p in batch:
                    led.skip(p, "the API rejects the number (400)", http=400)
                continue
            if not r.ok:
                for p in batch:
                    left(p, r)
                failed |= set(batch)
                continue
            els = elements(r.body)
            for p in batch:
                have = {e.get("symbol") for e in exact.get(p, [])}
                exact.setdefault(p, []).extend(e for e in els if match.keep(p, e) == "exact" and e.get("symbol") not in have)
                keep(kept(cache, p, "mpns"), {"asked": checked, "mpns": p, "by": "mpns+symbols" if by == "symbols[]" else "mpns",
                                              "elements": exact[p]})
    found: dict[str, dict[str, tuple[dict, str]]] = {}
    for p in to_match:
        if p in failed or (led.get(p) or {}).get("skip_reason"):
            continue
        pages: list[dict] = held_pages.get(p, [])
        for page in range(1, PAGES + 1):
            if p in held_pages:
                break
            r = client.get("/products/search", {"scope[]": ["products", "counters"], "phrase": p, "limit": 100, "page": page})
            counts["calls"] += 1
            if not r.ok:
                left(p, r)
                failed.add(p)
                break
            d = json.loads(r.body)
            pages.append(d)
            if page >= int(((d.get("data") or {}).get("counters") or {}).get("pages") or 1):
                break
        if p in failed:
            continue
        if p not in held_pages:
            keep(kept(cache, p, "search"), {"asked": checked, "phrase": p, "pages": pages})
        found[p] = match.collect(p, exact.get(p, []), searched_elements(pages), ok_for(p))
        n_exact = sum(1 for _, m in found[p].values() if m == "exact")
        led.stamp(p, "match", version=MATCH_VERSION, n_exact=n_exact, n_variant=len(found[p]) - n_exact, http=200)
        led.clear_after(p, "match")
        counts["matched"] += 1
        if not found[p]:
            drop(table, p)
            drop(files, p)
            table[(p, "")] = none_row(p, country, checked)
            led.stamp(p, "data", version=DATA_VERSION)
            counts["none"] += 1
        if counts["matched"] % BATCH == 0:
            flush()

    # 2. data: parts matched now, and parts whose prices and stock are older than max_age
    need = []
    for p in parts:
        r = led.get(p)
        if not r or r["skip_reason"] or not r["match_at"] or p in failed:
            continue
        if p in found:
            if found[p]:
                need.append(p)
        elif refresh or r["data_v"] != DATA_VERSION or stale(r["data_at"], max_age):
            found[p] = match.collect(p, (read_kept(kept(cache, p, "mpns")) or {}).get("elements", []),
                                     searched_elements((read_kept(kept(cache, p, "search")) or {}).get("pages", [])), ok_for(p))
            if found[p]:
                need.append(p)
            else:
                drop(table, p)
                drop(files, p)
                table[(p, "")] = none_row(p, country, checked)
                led.stamp(p, "data", version=DATA_VERSION)
    pairs = [(s, p) for p in need for s in found[p]]
    answers: dict[str, dict[str, dict]] = {"data": {}, "params": {}, "files": {}}
    lost: dict[str, set[str]] = {"data": set(), "params": set(), "files": set()}
    asks = (("data", "/products/data", {"currency": client.currency, "scope[]": ["prices", "stock"]}, client.data_delay),
            ("params", "/products/parameters", {}, client.delay),
            ("files", "/products/files", {}, client.delay))
    for what, path, extra, pace in asks:
        for batch in chunks(pairs, BATCH):
            r = client.get(path, {**extra, "symbols[]": [s for s, _ in batch]}, delay=pace)
            counts["calls"] += 1
            if not r.ok:
                for p in dict.fromkeys(p for _, p in batch):
                    left(f"{p} ({what})", r)
                lost[what] |= {p for _, p in batch}
                continue
            for e in elements(r.body):
                if e.get("symbol"):
                    answers[what][e["symbol"]] = e
    for p in need:
        if p in lost["data"]:
            continue
        syms = found[p]
        keep(kept(cache, p, "data"), {"asked": checked, "elements": [answers["data"][s] for s in syms if s in answers["data"]]})
        for what in ("params", "files"):
            if p not in lost[what]:
                keep(kept(cache, p, what), {"asked": checked, "elements": [answers[what][s] for s in syms if s in answers[what]]})
                led.stamp(p, what)
        rows = [offer_row(p, s, e, m, answers["data"].get(s), answers["params"].get(s), country, checked)
                for s, (e, m) in syms.items()]
        drop(table, p)
        drop(files, p)
        for row in match.rank(rows):
            table[(p, row["symbol"])] = row
            for fr in file_rows(p, row["symbol"], syms[row["symbol"]][0], answers["files"].get(row["symbol"]), checked):
                files[(p, fr["symbol"], fr["kind"], fr["url"])] = fr
            counts["offers"] += 1
        led.stamp(p, "data", version=DATA_VERSION)
        counts["priced"] += 1
    flush()
    return dict(counts)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="sei distributors tme")
    ap.add_argument("--part", action="append", help="only these parts (repeatable)")
    ap.add_argument("--top-per-kind", type=int, default=0, help="the N most printed parts of each kind in the dictionary")
    ap.add_argument("--limit", type=int, default=0, help="at most this many parts matched in this run")
    ap.add_argument("--max-age", type=int, default=None, help="days before prices and stock are asked for again")
    ap.add_argument("--refresh", action="store_true", help="ask again for every part, whatever its age")
    ap.add_argument("--reread", action="store_true", help="match again from the answers kept, asking for nothing")
    a = ap.parse_args(argv)
    entry = registry().get(DISTRIBUTOR)
    if not entry:
        print(f"{DISTRIBUTOR}: not in {distributors_registry()}", file=sys.stderr)
        return 2
    if entry.get("status") in ("paused", "blocked", "proposed"):
        print(f"{DISTRIBUTOR}: {entry['status']} — see its notes in the registry; not asked", file=sys.stderr)
        return 0
    parts = wanted(a.part, a.top_per_kind)
    max_age = a.max_age if a.max_age is not None else int(entry.get("max_age", 30))
    c = run(entry, parts, max_age=max_age, refresh=a.refresh, limit=a.limit, reread=a.reread)
    print(f"{DISTRIBUTOR}: {len(parts)} parts in scope, {c.get('matched', 0)} matched now "
          f"({c.get('none', 0)} with nothing), {c.get('priced', 0)} priced, {c.get('offers', 0)} offers written, "
          f"{c.get('calls', 0)} calls, {c.get('failed', 0)} left for the next run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
