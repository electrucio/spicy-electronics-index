"""Put the index database down as a few small tables, and build it back from them and the OCR tree.

    sei schematics dump-index DIR               write what the database holds that nothing else does
    sei schematics restore-index DIR            build index.sqlite again from DIR and the OCR on disk

`index.sqlite` is eleven gigabytes, and ten of them are `page_text` and its full-text index: the text of
every page, which the OCR tree already holds page by page. What the database alone knows is small — the
documents (with the figure-to-page links the old crawler recorded, which no stage writes any more), the
pages and what the classifier said of them, the parts and where they were read — and it goes down here
as CSV: a hundred megabytes that travel beside the OCR instead of a file that fits on no laptop.

`dump-index` writes one file per table, all columns, every row, primary-key order, `\\N` for NULL
(an empty field is an empty string, which exists: `page_parts.near` has four million of them), the exact
DDL as `schema.sql`, and a `SHA256SUMS`. Not written: `page_text` and `fts`, which come back from the
OCR; `sqlite_stat1`, which comes back from `ANALYZE`.

`restore-index` is the other half. It checks the sums, creates the database from `schema.sql`, loads the
tables with their ids intact — a figure names its parent by `doc_id`, and `export` knows documents by id
— then reads each document's OCR file and writes its pages' text under the `page_id` the loaded `pages`
row has, the way `ingest` would have: blocks joined by newlines, nothing written for an empty page.
Last it rebuilds `fts` and runs `ANALYZE`. The file is written beside its final name and moved into
place only when every step is done, and nothing that is already there is ever overwritten.

A document's OCR file is `ocr_path` under the private root, with or without the `ocr/` the old crawler
wrote before it; failing that, the map's line for (source, doc_key). Text regenerated this way is the
text `ingest` writes today, which for pages the old pipeline wrote differs in whitespace alone.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import sqlite3
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from spicy_electronics_index.core import pagesio
from spicy_electronics_index.core.config import index_db, material_root, ocr_map, ocr_root
from spicy_electronics_index.schematics.ingest import SCHEMA, page_text

NULL = r"\N"
SCHEMA_FILE = "schema.sql"
SUMS_FILE = "SHA256SUMS"
# Load order respects the foreign keys; the three that are large go down gzipped.
TABLES = ("sources", "documents", "pages", "parts", "page_parts", "ingest_runs")
LARGE = {"documents", "pages", "page_parts"}
# Derived from the rest, so never dumped: the text comes back from the OCR tree, the statistics from ANALYZE.
DERIVED = {"page_text", "fts", "sqlite_stat1"}
CHUNK = 20_000

csv.field_size_limit(sys.maxsize)


# --- the tables as files -----------------------------------------------------------------------------

def table_file(folder: Path, table: str) -> Path | None:
    """The file that holds `table` in `folder`, whichever spelling it was written with."""
    for name in (f"{table}_full.csv.gz", f"{table}.csv.gz", f"{table}_full.csv", f"{table}.csv"):
        if (folder / name).is_file():
            return folder / name
    return None


def _open_text(path: Path, mode: str):
    if path.suffix == ".gz":
        return gzip.open(path, mode + "t", encoding="utf-8", newline="")
    return open(path, mode, encoding="utf-8", newline="")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while b := f.read(1 << 20):
            h.update(b)
    return h.hexdigest()


def _column_types(db: sqlite3.Connection, table: str) -> list[tuple[str, str]]:
    return [(r[1], (r[2] or "").upper()) for r in db.execute(f"PRAGMA table_info({table})")]


def _convert(value: str, decl: str):
    """A CSV field back to what the column holds: NULL, an integer, a real, or the text as it is."""
    if value == NULL:
        return None
    if "INT" in decl:
        try:
            return int(value)
        except ValueError:
            pass
    if "INT" in decl or "REAL" in decl or "FLOA" in decl or "DOUB" in decl:
        try:
            return float(value)
        except ValueError:
            pass
    return value


def _schema_sql(db: sqlite3.Connection) -> str:
    """The DDL of what is dumped: tables, their indexes and the fts declaration; no shadow tables, no
    statistics, no automatic indexes (those have no SQL of their own)."""
    virtual = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE sql LIKE 'CREATE VIRTUAL TABLE%'")]
    out = []
    for name, sql in db.execute("SELECT name, sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY rowid"):
        if name.startswith("sqlite_"):
            continue
        if any(name.startswith(v + "_") for v in virtual):
            continue
        out.append(sql.strip() + ";")
    return "\n\n".join(out) + "\n"


def dump(folder: Path, source_db: Path | None = None, say=print) -> dict:
    """Write the non-derived tables of the index database into `folder`. Returns rows per table."""
    source_db = source_db or index_db()
    if not source_db.is_file():
        raise FileNotFoundError(f"{source_db} is not here; nothing to dump")
    folder.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(f"file:{source_db}?mode=ro", uri=True)
    counts: dict[str, int] = {}
    written: list[Path] = []
    tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY rowid")
              if not r[0].startswith("sqlite_")]
    virtual = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE sql LIKE 'CREATE VIRTUAL TABLE%'")]
    for table in TABLES + tuple(t for t in tables if t not in TABLES):
        if table in DERIVED or any(table.startswith(v + "_") for v in virtual) or table not in tables:
            continue
        cols = [c for c, _ in _column_types(db, table)]
        pk = [r[1] for r in sorted(db.execute(f"PRAGMA table_info({table})"), key=lambda r: r[5]) if r[5]]
        order = f"ORDER BY {', '.join(pk)}" if pk else "ORDER BY rowid"
        path = folder / (f"{table}_full.csv.gz" if table in LARGE else f"{table}.csv")
        n = 0
        with _open_text(path, "w") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(cols)
            for row in db.execute(f"SELECT {', '.join(cols)} FROM {table} {order}"):
                w.writerow([NULL if v is None else v for v in row])
                n += 1
        counts[table] = n
        written.append(path)
        say(f"  {table}: {n:,} rows -> {path.name}")
    schema = folder / SCHEMA_FILE
    schema.write_text(_schema_sql(db), encoding="utf-8")
    written.append(schema)
    db.close()
    with open(folder / SUMS_FILE, "w", encoding="utf-8") as f:
        for p in written:
            f.write(f"{_sha256(p)}  {p.name}\n")
    return counts


# --- and back ------------------------------------------------------------------------------------------

def check_sums(folder: Path) -> list[str]:
    """The files named in SHA256SUMS whose sum does not match, or that are missing. [] when all is well
    or there is no sums file."""
    sums = folder / SUMS_FILE
    if not sums.is_file():
        return []
    bad = []
    for line in sums.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        want, name = line.split(None, 1)
        name = name.strip().lstrip("*")
        if name == SUMS_FILE:
            continue
        p = folder / name
        if not p.is_file() or _sha256(p) != want:
            bad.append(name)
    return bad


def load_tables(db: sqlite3.Connection, folder: Path, say=print) -> dict[str, int]:
    """Load every dumped table, ids intact, in an order the foreign keys allow."""
    counts: dict[str, int] = {}
    for table in TABLES:
        path = table_file(folder, table)
        if path is None:
            say(f"  {table}: no file in {folder}, left empty")
            counts[table] = 0
            continue
        types = dict(_column_types(db, table))
        n = 0
        with _open_text(path, "r") as f:
            r = csv.reader(f)
            cols = next(r)
            unknown = [c for c in cols if c not in types]
            if unknown:
                raise ValueError(f"{path.name}: columns {unknown} are not in the schema of {table}")
            decl = [types[c] for c in cols]
            sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})"
            batch = []
            for row in r:
                batch.append([_convert(v, d) for v, d in zip(row, decl)])
                if len(batch) >= CHUNK:
                    db.executemany(sql, batch)
                    n += len(batch)
                    batch = []
            if batch:
                db.executemany(sql, batch)
                n += len(batch)
        db.commit()
        counts[table] = n
        say(f"  {table}: {n:,} rows")
    return counts


def ocr_file_for(ocr_path: str | None, source: str, doc_key: str, mapped: dict[tuple[str, str], str]) -> Path | None:
    """Where a document's pages are on this machine, or None.

    `ocr_path` was written relative to the private root by the old crawler (`ocr/<source>/<name>`) and
    relative to the OCR tree by `ingest` (`<source>/<name>`); both are tried. The map is the fallback,
    and the authority when the path recorded was renamed since (elektor's and the books' were).
    """
    if ocr_path:
        for p in (material_root() / ocr_path, ocr_root() / ocr_path):
            if p.is_file():
                return p
    name = mapped.get((source, doc_key))
    if name:
        p = ocr_root() / name
        if p.is_file():
            return p
    return None


def _map_rows() -> dict[tuple[str, str], str]:
    path = ocr_map()
    if not path.is_file():
        return {}
    with open(path, newline="", encoding="utf-8") as f:
        return {(r["source"], r["doc_key"]): r["ocr_file"] for r in csv.DictReader(f)
                if r.get("source") and r.get("doc_key") and r.get("ocr_file")}


def read_one(job):
    """(doc_id, path) -> (doc_id, [(page_no, text)], error). Runs in a worker; opens no database."""
    doc_id, path = job
    out = []
    try:
        for n, page in enumerate(pagesio.iter_pages(path), 1):
            text = page_text(page)
            if text:
                out.append((int(page.get("page") or n), text))
    except (OSError, ValueError) as e:
        return doc_id, None, str(e)[:120]
    return doc_id, out, None


def fill_text(db: sqlite3.Connection, workers: int = 12, limit: int = 0, say=print) -> dict:
    """Write `page_text` for every page whose document's OCR file is here, then rebuild `fts`."""
    mapped = _map_rows()
    docs = db.execute("SELECT d.doc_id, d.source, d.doc_key, d.ocr_path FROM documents d "
                      "WHERE EXISTS (SELECT 1 FROM pages p WHERE p.doc_id = d.doc_id) ORDER BY d.doc_id").fetchall()
    jobs, missing = [], 0
    for doc_id, source, key, ocr_path in docs:
        p = ocr_file_for(ocr_path, source, key, mapped)
        if p is None:
            missing += 1
        else:
            jobs.append((doc_id, str(p)))
    if limit:
        jobs = jobs[:limit]
    counts = {"documents with pages": len(docs), "with an OCR file": len(jobs), "without": missing,
              "unreadable": 0, "pages with text": 0, "page not in the index": 0}
    say(f"  {len(jobs):,} documents to read, {missing:,} have no OCR file here")
    t0, done = time.time(), 0
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for doc_id, pages, error in pool.map(read_one, jobs, chunksize=16):
            done += 1
            if error:
                counts["unreadable"] += 1
                say(f"  !! doc {doc_id}: {error}")
                continue
            page_ids = dict(db.execute("SELECT page_no, page_id FROM pages WHERE doc_id = ?", (doc_id,)))
            rows = []
            for page_no, text in pages:
                pid = page_ids.get(page_no)
                if pid is None:
                    counts["page not in the index"] += 1
                    continue
                rows.append((pid, text))
            db.executemany("INSERT INTO page_text (page_id, text) VALUES (?, ?)", rows)
            counts["pages with text"] += len(rows)
            if done % 5000 == 0:
                db.commit()
                rate = done / max(time.time() - t0, 1)
                say(f"  {done:,}/{len(jobs):,} documents, {counts['pages with text']:,} pages, "
                    f"{(len(jobs) - done) / max(rate, 0.001) / 60:.0f} min left")
    db.commit()
    say("  rebuilding the full-text index")
    db.execute("INSERT INTO fts(fts) VALUES ('rebuild')")
    db.commit()
    return counts


def restore(folder: Path, into: Path | None = None, *, workers: int = 12, limit: int = 0,
            text: bool = True, say=print) -> dict:
    """Build the index database at `into` (default: where the project keeps it) from `folder` + the OCR."""
    into = into or index_db()
    if into.exists():
        raise FileExistsError(f"{into} is already there; move it aside first — this never overwrites")
    bad = check_sums(folder)
    if bad:
        raise ValueError(f"{folder / SUMS_FILE}: these do not match: {', '.join(bad)}")
    schema = folder / SCHEMA_FILE
    ddl = schema.read_text(encoding="utf-8") if schema.is_file() else SCHEMA
    into.parent.mkdir(parents=True, exist_ok=True)
    part = into.with_name(into.name + ".part")
    if part.exists():
        part.unlink()
    db = sqlite3.connect(part)
    # A fresh file nobody reads yet: no journal to keep, and the whole of it is discarded on failure.
    db.execute("PRAGMA journal_mode = OFF")
    db.execute("PRAGMA synchronous = OFF")
    db.execute("PRAGMA cache_size = -1000000")
    db.executescript(ddl)
    say("tables")
    counts: dict = {"tables": load_tables(db, folder, say=say)}
    if text:
        say("text")
        counts["text"] = fill_text(db, workers=workers, limit=limit, say=say)
    say("statistics")
    db.execute("ANALYZE")
    db.commit()
    db.close()
    part.replace(into)
    counts["path"] = str(into)
    return counts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="sei schematics restore-index", description=__doc__.splitlines()[0])
    ap.add_argument("folder", help="the folder written by `dump-index`")
    ap.add_argument("--into", help="where to write the database (default: where the project keeps it)")
    ap.add_argument("--workers", type=int, default=12, help="how many processes read the OCR at once")
    ap.add_argument("--limit", type=int, default=0, help="read the OCR of at most this many documents (a trial)")
    ap.add_argument("--no-text", action="store_true", help="load the tables only; no page text, no search index")
    a = ap.parse_args(argv)
    try:
        c = restore(Path(a.folder), Path(a.into) if a.into else None, workers=a.workers, limit=a.limit,
                    text=not a.no_text, say=lambda s: print(s, file=sys.stderr))
    except (FileExistsError, FileNotFoundError, ValueError) as e:
        print(e, file=sys.stderr)
        return 1
    print(f"{c['path']}: " + " · ".join(f"{v:,} {k}" for k, v in c["tables"].items()), file=sys.stderr)
    if "text" in c:
        print(" · ".join(f"{v:,} {k}" for k, v in c["text"].items()), file=sys.stderr)
    return 0


def main_dump(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="sei schematics dump-index", description=__doc__.splitlines()[0])
    ap.add_argument("folder", help="where to write the tables")
    ap.add_argument("--db", help="the database to read (default: the project's index.sqlite)")
    a = ap.parse_args(argv)
    try:
        c = dump(Path(a.folder), Path(a.db) if a.db else None, say=lambda s: print(s, file=sys.stderr))
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 1
    print(f"{a.folder}: " + " · ".join(f"{v:,} {k}" for k, v in c.items()), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
