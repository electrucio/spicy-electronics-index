"""The index database as a few small tables and back.

The round trip is the test: a dump nobody has restored is a hope. What must survive is everything the
OCR tree cannot give back — the ids, a figure's parent, the classifier's verdicts, the parts read on
each page — and the text must come back from the OCR files exactly as `ingest` writes it.
"""
from __future__ import annotations

import csv
import gzip
import sqlite3

import pytest

from spicy_electronics_index.core import config, pagesio
from spicy_electronics_index.schematics import restore_index as R
from spicy_electronics_index.schematics.ingest import SCHEMA

PAGES_A = [{"page": 1, "blocks": [{"text": " TL072 "}, {"text": "R1 10k"}]},
           {"page": 2, "blocks": [{"text": ""}]},                       # an empty page: no text row
           {"page": 3, "blocks": [{"text": "NE5532"}]}]
PAGES_B = [{"page": 1, "blocks": [{"text": "2N3904"}]}]


def write_map(rows):
    path = config.ocr_map()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["source", "doc_key", "text_method", "pages", "ocr_file", "origin"])
        w.writerows(rows)


@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.setenv("SEI_MATERIAL", str(tmp_path / "material"))
    # Document 1's file is named the old way (relative to the private root, `ocr/` and all); document 2's
    # path is stale and only the map knows where it went; document 3 is a figure of 1 with no file at all.
    pagesio.write_pages(config.ocr_root() / "esp", "p1.pdf", PAGES_A)
    pagesio.write_pages(config.ocr_root() / "esp", "p2-renamed.pdf", PAGES_B)
    write_map([["esp", "https://x/p2.pdf", "ocr", 1, "esp/p2-renamed.pdf.jsonl.gz", "ocr"]])

    original = tmp_path / "original.sqlite"
    db = sqlite3.connect(original)
    db.executescript(SCHEMA)
    db.execute("INSERT INTO sources VALUES ('esp', 'site', 'ESP', 'https://x/')")
    db.executemany("INSERT INTO documents (doc_id, source, doc_key, role, parent_doc_id, title, public_url, "
                   "page_url_tpl, page_offset, sha256, year, n_pages, text_method, ocr_path, extractor_version) "
                   "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", [
                       (10, "esp", "https://x/p1.pdf", "schematic", None, "P1", "https://x/p1.pdf",
                        "{url}#page={n}", 0, "a" * 64, 1999, 3, "ocr", "ocr/esp/p1.pdf.jsonl.gz", "parts-1"),
                       (20, "esp", "https://x/p2.pdf", "schematic", None, "P2", "https://x/p2.pdf",
                        None, 0, None, None, 1, "text", "esp/p2-old-name.pdf.jsonl.gz", "parts-1"),
                       (30, "esp", "https://x/fig.png", "figure", 10, "", "https://x/fig.png",
                        None, 0, None, None, None, None, None, None)])
    db.executemany("INSERT INTO pages (page_id, doc_id, page_no, n_blocks, n_parts, seq_run, ad_score, is_ad, "
                   "has_schematic, classifier_version, w_pt, h_pt) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", [
                       (100, 10, 1, 2, 1, 0.5, 0, 0, 1, "adfilter-1", 595.0, 842.0),
                       (101, 10, 2, 1, 0, 0.0, 3, 1, 0, "adfilter-1", 595.0, 842.0),
                       (102, 10, 3, 1, 1, 0.0, 0, 0, 0, "adfilter-1", None, None),
                       (200, 20, 1, 1, 1, 0.0, 0, 0, 1, "adfilter-1", 612.0, 792.0)])
    db.executemany("INSERT INTO parts VALUES (?,?,?,?,?,?)", [
        (1, "TL072", "TL072", "opamp", "ic", 1), (2, "NE5532", "NE5532", "opamp", "", 1),
        (3, "2N3904", "2N3904", "bjt", "transistor", 1)])
    db.executemany("INSERT INTO page_parts VALUES (?,?,?,?,?,?,?,?,?)", [
        (100, 1, 1, 1, "high", "ocr", "TL072", "[[1, 2, 3, 4]]", "R1"),
        (102, 2, 1, 0, "high", "ocr", "NE5532", "[]", ""),            # an empty string, not NULL
        (200, 3, 1, 0, "medium", "text", "2N3904", "[]", None)])
    db.execute("INSERT INTO ingest_runs VALUES ('esp', '2026-01-01 00:00:00', '2026-01-01 00:01:00', 'ingest-1', 2, 4)")
    for pid, text in ((100, "TL072\nR1 10k"), (102, "NE5532"), (200, "2N3904")):
        db.execute("INSERT INTO page_text VALUES (?, ?)", (pid, text))
        db.execute("INSERT INTO fts(rowid, text) VALUES (?, ?)", (pid, text))
    db.commit()
    db.close()
    return tmp_path, original


def rows(db, table):
    return db.execute(f"SELECT * FROM {table} ORDER BY 1, 2").fetchall()


def test_dump_writes_every_non_derived_table_with_null_marked(world):
    tmp, original = world
    counts = R.dump(tmp / "dump", original, say=lambda s: None)

    assert counts == {"sources": 1, "documents": 3, "pages": 4, "parts": 3, "page_parts": 3, "ingest_runs": 1}
    names = {p.name for p in (tmp / "dump").iterdir()}
    assert names == {"sources.csv", "documents_full.csv.gz", "pages_full.csv.gz", "parts.csv",
                     "page_parts_full.csv.gz", "ingest_runs.csv", "schema.sql", "SHA256SUMS"}
    with gzip.open(tmp / "dump" / "page_parts_full.csv.gz", "rt", encoding="utf-8", newline="") as f:
        got = list(csv.reader(f))
    assert got[0] == ["page_id", "part_id", "n", "n_label", "conf", "read_by", "raw", "boxes", "near"]
    assert [r[-1] for r in got[1:]] == ["R1", "", R.NULL]        # an empty string and a NULL stay apart
    schema = (tmp / "dump" / "schema.sql").read_text()
    assert "CREATE VIRTUAL TABLE fts" in schema and "fts_data" not in schema and "sqlite_stat1" not in schema
    assert R.check_sums(tmp / "dump") == []


def test_restore_gives_the_tables_back_and_the_text_from_the_ocr(world):
    tmp, original = world
    R.dump(tmp / "dump", original, say=lambda s: None)

    counts = R.restore(tmp / "dump", tmp / "restored.sqlite", workers=1, say=lambda s: None)

    assert counts["tables"] == {"sources": 1, "documents": 3, "pages": 4, "parts": 3, "page_parts": 3,
                                "ingest_runs": 1}
    text = counts["text"]
    assert text["documents with pages"] == 2 and text["with an OCR file"] == 2 and text["without"] == 0
    assert text["pages with text"] == 3 and text["unreadable"] == 0
    a, b = sqlite3.connect(original), sqlite3.connect(tmp / "restored.sqlite")
    for table in ("sources", "documents", "pages", "parts", "page_parts", "ingest_runs", "page_text"):
        assert rows(a, table) == rows(b, table), table
    # ids and types survived: a figure still names its parent, a real is a real, a NULL is a NULL
    assert b.execute("SELECT parent_doc_id FROM documents WHERE doc_id = 30").fetchone() == (10,)
    assert b.execute("SELECT typeof(seq_run), typeof(w_pt), typeof(sha256) FROM pages "
                     "JOIN documents USING (doc_id) WHERE page_id = 102").fetchone() == ("real", "null", "text")
    # the search index was rebuilt over the text that came back
    assert [r[0] for r in b.execute("SELECT rowid FROM fts WHERE fts MATCH 'tl072'")] == [100]
    assert b.execute("SELECT COUNT(*) FROM sqlite_stat1").fetchone()[0] > 0
    assert not (tmp / "restored.sqlite.part").exists()


def test_restore_never_overwrites_and_refuses_a_damaged_dump(world):
    tmp, original = world
    R.dump(tmp / "dump", original, say=lambda s: None)
    (tmp / "taken.sqlite").write_bytes(b"mine")
    with pytest.raises(FileExistsError):
        R.restore(tmp / "dump", tmp / "taken.sqlite", say=lambda s: None)
    assert (tmp / "taken.sqlite").read_bytes() == b"mine"

    (tmp / "dump" / "parts.csv").write_text("part_id,part,base_part,family,kind,in_dictionary\n", encoding="utf-8")
    with pytest.raises(ValueError, match="parts.csv"):
        R.restore(tmp / "dump", tmp / "other.sqlite", say=lambda s: None)
    assert not (tmp / "other.sqlite").exists()


def test_a_document_whose_file_is_gone_is_counted_not_fatal(world):
    tmp, original = world
    R.dump(tmp / "dump", original, say=lambda s: None)
    (config.ocr_root() / "esp" / "p2-renamed.pdf.jsonl.gz").unlink()

    counts = R.restore(tmp / "dump", tmp / "restored.sqlite", workers=1, say=lambda s: None)

    assert counts["text"]["without"] == 1 and counts["text"]["pages with text"] == 2
    b = sqlite3.connect(tmp / "restored.sqlite")
    assert b.execute("SELECT COUNT(*) FROM pages WHERE doc_id = 20").fetchone() == (1,)   # the row stays
    assert b.execute("SELECT COUNT(*) FROM page_text WHERE page_id = 200").fetchone() == (0,)


def test_the_default_target_is_the_project_database(world):
    tmp, original = world
    R.dump(tmp / "dump", original, say=lambda s: None)
    counts = R.restore(tmp / "dump", text=False, say=lambda s: None)
    assert counts["path"] == str(config.index_db()) and config.index_db().is_file()
    assert "text" not in counts
