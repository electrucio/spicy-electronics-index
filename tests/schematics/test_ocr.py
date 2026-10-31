"""The reading stage: what it takes from the ledger, how shards divide it, and the page decision."""
import csv

import pytest

from spicy_electronics_index.core.ledger import Ledger
from spicy_electronics_index.schematics import ocr


class FakePage:
    """Only what the text-layer path asks of a page: its words, each with a box, a block and a line."""

    def __init__(self, words):
        self._words = words

    def get_text(self, what):
        return self._words


def test_a_text_layer_becomes_line_blocks_in_the_rendered_pages_pixels():
    words = [(10, 20, 30, 28, "IC1", 0, 0, 0), (35, 20, 60, 28, "TL072", 0, 0, 1),
             (10, 40, 25, 48, "R1", 0, 1, 0)]
    blocks = ocr._text_blocks(FakePage(words), zoom=2.0)
    assert [b["text"] for b in blocks] == ["IC1 TL072", "R1"]        # one block per line, words joined
    assert blocks[0]["box"] == [20, 40, 120, 56]                     # the line's bounding box, times the zoom
    assert all(b["conf"] == 1.0 for b in blocks)                     # a text layer is not a guess


def test_a_page_with_no_text_layer_and_no_ocr_says_so_instead_of_writing_an_empty_page(tmp_path):
    """The failure that matters: a scanned sheet read without an OCR loaded would otherwise be stored as a
    page with nothing on it, and the ledger would call it done."""
    pytest.importorskip("fitz")
    import fitz

    doc = fitz.open()
    doc.new_page()
    path = tmp_path / "scan.pdf"
    doc.save(path)
    with pytest.raises(RuntimeError, match="no text layer"):
        ocr.read_document(path, "pdf", read_image=None)


def _ledger_with(tmp_path, n):
    led = Ledger(tmp_path / "state" / "src.csv")
    for i in range(n):
        led.stamp(f"https://example.org/{i}.pdf", "download", sha256=f"{i:040d}", type="pdf", http=200)
    led.save()
    return led


def test_shards_divide_the_work_once_each(monkeypatch, tmp_path):
    monkeypatch.setattr(ocr, "registry_entry", lambda source: {})
    monkeypatch.setattr(ocr, "schematics_state", lambda source: tmp_path / "state" / "src.csv")
    _ledger_with(tmp_path, 40)
    halves = [ocr.run("src", shard=f"{k}/2", dry=True)["to read"] for k in (0, 1)]
    assert sum(halves) == 40 and min(halves) >= 10                  # all of it, roughly halved
    assert ocr.run("src", dry=True)["to read"] == 40


def test_a_shard_keeps_its_documents_whatever_the_others_have_stamped(tmp_path):
    """The 2026-10-06 batch: a shard that reaches a source after another has stamped some of it must not
    see its share move — or two shards read the same document and nobody reads its neighbour."""
    keys = [f"https://example.org/{i}.pdf" for i in range(400)]
    mine = {k for k in keys if ocr.shard_of(k, 4) == 1}
    later = {k for k in keys[150:] if ocr.shard_of(k, 4) == 1}     # the first 150 read by others meanwhile
    assert later == {k for k in mine if k in keys[150:]}
    assert set().union(*({k for k in keys if ocr.shard_of(k, 4) == s} for s in range(4))) == set(keys)


def test_a_document_already_read_is_not_offered_again(monkeypatch, tmp_path):
    monkeypatch.setattr(ocr, "registry_entry", lambda source: {})
    monkeypatch.setattr(ocr, "schematics_state", lambda source: tmp_path / "state" / "src.csv")
    led = _ledger_with(tmp_path, 3)
    led.stamp("https://example.org/1.pdf", "ocr", version=ocr.OCR_VERSION, n_pages=4, text_method="ocr_boxes")
    led.save()
    assert ocr.run("src", dry=True)["to read"] == 2


def test_the_map_is_appended_to_never_rewritten(monkeypatch, tmp_path):
    monkeypatch.setattr(ocr, "ocr_map", lambda: tmp_path / "ocr_map.csv")
    ocr._note_in_map("src", "https://example.org/a.pdf", "ocr_boxes", 12, "aaa_a.pdf")
    ocr._note_in_map("src", "https://example.org/b.pdf", "text", 3, "bbb_b.pdf")
    rows = list(csv.DictReader(open(tmp_path / "ocr_map.csv", encoding="utf-8")))
    assert [r["doc_key"] for r in rows] == ["https://example.org/a.pdf", "https://example.org/b.pdf"]
    assert rows[0]["ocr_file"] == "src/aaa_a.pdf.jsonl.gz" and rows[1]["pages"] == "3"


def test_a_published_key_never_carries_a_path_out_of_a_disk():
    """Ten exported Elektor keys were `<url>#/data/<account>/audio-index/elektor/ia_pdfs/<file>`. The
    fragment identifies the document and is published with it, so it keeps its last two segments only."""
    from spicy_electronics_index.schematics.export import publishable_key

    # split so this file does not itself carry the shape the guard refuses
    leaked = "https://archive.org/download/x/e991018.pdf#" + "/data" + "/someone/audio-index/elektor/ia_pdfs/e991018.pdf"
    assert publishable_key(leaked) == "https://archive.org/download/x/e991018.pdf#ia_pdfs/e991018.pdf"
    kept = "https://archive.org/download/x/e991026.pdf#Elektor 1999/e991026.pdf"
    assert publishable_key(kept) == kept                      # a relative fragment is the document's name
    assert publishable_key("https://example.org/a.pdf") == "https://example.org/a.pdf"


def test_a_source_read_in_japanese_carries_its_language_in_the_stamp(monkeypatch, tmp_path):
    """Read in English is not read in Japanese: a document stamped with the default is read again when its
    source asks for another language, and one read in that language is not."""
    assert ocr.version_for({}) == ocr.OCR_VERSION
    assert ocr.version_for({"ocr": {"lang": "japan"}}) == f"{ocr.OCR_VERSION}-japan"
    monkeypatch.setattr(ocr, "registry_entry", lambda source: {"ocr": {"lang": "japan"}})
    monkeypatch.setattr(ocr, "schematics_state", lambda source: tmp_path / "state" / "src.csv")
    led = _ledger_with(tmp_path, 3)
    led.stamp("https://example.org/0.pdf", "ocr", version=ocr.OCR_VERSION, n_pages=1, text_method="ocr_boxes")
    led.stamp("https://example.org/1.pdf", "ocr", version=f"{ocr.OCR_VERSION}-japan", n_pages=1, text_method="ocr_boxes")
    led.save()
    assert ocr.run("src", dry=True)["to read"] == 2


def test_a_design_is_read_again_when_its_reader_changes_and_a_scan_is_not(monkeypatch, tmp_path):
    from spicy_electronics_index.schematics import cad
    monkeypatch.setattr(ocr, "registry_entry", lambda source: {})
    monkeypatch.setattr(ocr, "schematics_state", lambda source: tmp_path / "state" / "src.csv")
    led = _ledger_with(tmp_path, 2)
    led.stamp("https://example.org/2.asc", "download", sha256="2" * 40, type="ltspice_asc", http=200)
    led.stamp("https://example.org/0.pdf", "ocr", version=ocr.OCR_VERSION, n_pages=1, text_method="ocr_boxes")
    led.stamp("https://example.org/2.asc", "ocr", version=ocr.OCR_VERSION, n_pages=1, text_method="text")
    led.save()
    assert ocr.run("src", dry=True)["to read"] == 2               # 1.pdf, never read; 2.asc, read by an older reader
    led.stamp("https://example.org/2.asc", "ocr", version=f"{ocr.OCR_VERSION}-cad{cad.VERSION}", n_pages=1,
              text_method="text")
    led.save()
    assert ocr.run("src", dry=True)["to read"] == 1


def test_a_design_already_on_disk_is_written_again_when_its_reader_changed(monkeypatch, tmp_path):
    """The page file of a scan says it was read; the page file of a design says an older reader read it."""
    from spicy_electronics_index.core import pagesio
    from spicy_electronics_index.schematics import cad
    monkeypatch.setattr(ocr, "registry_entry", lambda source: {})
    monkeypatch.setattr(ocr, "schematics_state", lambda source: tmp_path / "state" / "src.csv")
    monkeypatch.setattr(ocr, "ocr_root", lambda: tmp_path / "ocr")
    monkeypatch.setattr(ocr, "ocr_map", lambda: tmp_path / "ocr_map.csv")
    monkeypatch.setattr(ocr, "downloads", lambda source: tmp_path / "downloads")
    url = "https://example.org/amp.asc"
    led = Ledger(tmp_path / "state" / "src.csv")
    led.stamp(url, "download", sha256="a" * 40, type="ltspice_asc", http=200)
    led.stamp(url, "ocr", version=ocr.OCR_VERSION, n_pages=1, text_method="text")
    led.save()
    name = ocr.safe_name(url, "ltspice_asc")
    (tmp_path / "downloads" / "ltspice_asc").mkdir(parents=True)
    (tmp_path / "downloads" / "ltspice_asc" / name).write_text(
        "Version 4\nSHEET 1 1 1\nSYMBOL npn 0 0 R0\nSYMATTR InstName Q1\nSYMATTR Value 2SC1815\n", encoding="utf-8")
    pagesio.write_pages(tmp_path / "ocr" / "src", name, [{"page": 1, "w": 0, "h": 0, "how": "cad", "blocks": []}])
    counts = ocr.run("src")
    assert counts["read"] == 1 and counts["already there"] == 0
    row = Ledger(tmp_path / "state" / "src.csv").get(url)
    assert row["ocr_v"] == f"{ocr.OCR_VERSION}-cad{cad.VERSION}"
    texts = [b["text"] for p in pagesio.read_pages(pagesio.out_path(tmp_path / "ocr" / "src", name)) for b in p["blocks"]]
    assert "2SC1815" in texts


def test_pages_already_on_disk_get_their_stamp_instead_of_being_offered_forever(monkeypatch, tmp_path):
    from spicy_electronics_index.core import pagesio
    monkeypatch.setattr(ocr, "registry_entry", lambda source: {})
    monkeypatch.setattr(ocr, "schematics_state", lambda source: tmp_path / "state" / "src.csv")
    monkeypatch.setattr(ocr, "ocr_root", lambda: tmp_path / "ocr")
    monkeypatch.setattr(ocr, "ocr_map", lambda: tmp_path / "ocr_map.csv")
    monkeypatch.setattr(ocr, "downloads", lambda source: tmp_path / "downloads")
    url = "https://example.org/sheet.pdf"
    led = Ledger(tmp_path / "state" / "src.csv")
    led.stamp(url, "download", sha256="b" * 40, type="pdf", http=200)
    led.save()
    name = ocr.safe_name(url, "pdf")
    (tmp_path / "downloads" / "pdf").mkdir(parents=True)
    (tmp_path / "downloads" / "pdf" / name).write_bytes(b"%PDF-1.4 not opened here")
    pagesio.write_pages(tmp_path / "ocr" / "src", name, [{"page": 1, "w": 1, "h": 1, "how": "ocr", "blocks": []},
                                                          {"page": 2, "w": 1, "h": 1, "how": "text", "blocks": []}])
    counts = ocr.run("src")
    assert counts["already there"] == 1 and counts["read"] == 0
    row = Ledger(tmp_path / "state" / "src.csv").get(url)
    assert (row["ocr_v"], row["n_pages"], row["text_method"]) == (ocr.OCR_VERSION, "2", "ocr_boxes")
    assert ocr.run("src", dry=True)["to read"] == 0


def test_a_page_record_carries_its_size_in_points_because_the_file_will_not_stay(tmp_path):
    """The retention rule deletes a scan once read; the zoom link needs the page's points to say where
    on the sheet a part sits, and 481,319 pages were released before the record said so."""
    pytest.importorskip("fitz")
    import fitz
    path = tmp_path / "a.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    for i in range(12):                                  # 72 words: past TEXT_WORDS, so no render
        page.insert_text((72, 72 + 14 * i), "IC1 TL072 R1 C1 U2 NE5532")
    doc.save(path)
    doc.close()
    pages = ocr.read_document(path, "pdf", read_image=None)
    assert (pages[0]["w_pt"], pages[0]["h_pt"]) == (612.0, 792.0)


# --- version 2: a layer that is not text, and a page printed sideways ---------------------------------

GARBLED = "! \"# $%& A5P4{+SS+=>,f4Y5PY<475+ NSL4xP4OP*{+*6PL4 {+*4-5P4Y+ ,->,NPL4O*+ -PY->+,4+{4 *G/%HCD%E%4)4/".split()


def test_a_layer_in_a_font_with_no_character_map_is_not_text():
    """The Denon AVR-1803 manual's parts list, as its text layer gives it."""
    assert not ocr.legible(GARBLED * 5)


def test_a_font_mapped_onto_the_wrong_letters_is_not_text():
    pioneer = "ßóěđéÎ Ü·®»˝¬ Ű˛»®ą§ ÓŃÍ ŃÎÜŰÎ ŇŃň ÎÎĘďçëč ÍĚŰÎŰŃ ßÓĐÔ×Ú×ŰÎ ßóěđéÎ ĚŘ×Í ÓßŇËßÔ".split()
    assert not ocr.legible(pioneer * 3)


@pytest.mark.parametrize("text", [
    # a parts list, with the codes a factory prints
    "Ref. No. Part No. Description Remark R457 1-218-959-11 RES-CHIP 10K 5% 1/16W C101 1-164-004-11 CERAMIC 0.1uF",
    # a pin-voltage table: lone digits are neither text nor garbage
    "IC2001 MODE 1 2 3 4 5 6 7 8 9 10 11 12 VCC GND 5.0 0 2.5 4.9 0 0 3.3 3.3 0.1 5.0 MAIN P.C.B.",
    # a contents page: dot leaders count for nothing
    "Table of Contents Preface . . . . . . . . . . . . xix 1. How to Use This Book . . . . . . 1 2. Switches . . . 9",
    # Japanese, which runs without spaces and has its own punctuation
    "本誌のご購入はこちら 講義⑤ その３：ロスなく 高周波信号を伝えるには 電磁波は，ちょうど池の表面の水の波（講義①の図",
])
def test_what_a_manual_really_prints_is_text(text):
    assert ocr.legible(text.split() * 4)


def test_too_few_words_to_judge_is_taken_as_text_as_it_always_was():
    assert ocr.legible(GARBLED[:6])


def test_a_garbled_layer_is_rendered_and_read_like_a_scan(tmp_path):
    pytest.importorskip("fitz")
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    for i, word in enumerate(GARBLED * 3):
        page.insert_text((20 + 60 * (i % 8), 30 + 14 * (i // 8)), word, fontsize=6)
    path = tmp_path / "manual.pdf"
    doc.save(path)
    seen = []
    pages = ocr.read_document(path, "pdf", read_image=lambda img: seen.append(img.shape) or
                              [{"box": [10, 10, 90, 20], "text": "PARTS LIST", "conf": 0.99}])
    assert len(seen) == 1 and pages[0]["how"] == "ocr"
    assert pages[0]["blocks"][0]["text"] == "PARTS LIST"


@pytest.mark.parametrize("quarter", [1, 3])
def test_a_box_read_on_a_turned_image_lands_where_the_word_is_on_the_upright_one(quarter):
    np = pytest.importorskip("numpy")
    img = np.zeros((40, 100), dtype=np.uint8)           # h=40, w=100
    img[5:9, 70:90] = 255                                # a "word" at x 70..89, y 5..8
    turned = np.rot90(img, quarter)
    ys, xs = np.nonzero(turned)
    box = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
    assert ocr.unturn(box, quarter, w=100, h=40) == [70, 5, 89, 8]


def test_a_sideways_sheet_is_read_turned_and_its_boxes_come_back_upright():
    np = pytest.importorskip("numpy")
    img = np.zeros((300, 200, 3), dtype=np.uint8)

    def read(image):
        if image.shape[:2] == (300, 200):                # upright: every line stands on end, and is noise
            return [{"box": [10 * i, 0, 10 * i + 8, 60], "text": "d61 dBL", "conf": 0.5} for i in range(20)]
        return [{"box": [5, 5 + 9 * i, 60, 12 + 9 * i], "text": f"R{i}01 2SK117 10K", "conf": 0.9}
                for i in range(20)]                      # turned (200 high, 300 wide): lines lie flat

    blocks, turned = ocr.read_upright(read, img)
    assert turned in (90, 270)
    assert "2SK117" in blocks[0]["text"]
    assert all(0 <= b["box"][0] <= b["box"][2] < 200 and 0 <= b["box"][1] <= b["box"][3] < 300 for b in blocks)


def test_an_upright_page_is_read_once():
    np = pytest.importorskip("numpy")
    calls = []

    def read(image):
        calls.append(image.shape)
        return [{"box": [5, 5 + 10 * i, 160, 13 + 10 * i], "text": "R101 10K C12 0.1uF", "conf": 0.9}
                for i in range(30)]

    assert ocr.read_upright(read, np.zeros((300, 200, 3), dtype=np.uint8))[1] == 0
    assert len(calls) == 1


def test_an_earlier_reading_stands_until_recheck_marks_it(monkeypatch, tmp_path):
    monkeypatch.setattr(ocr, "registry_entry", lambda source: {})
    monkeypatch.setattr(ocr, "schematics_state", lambda source: tmp_path / "state" / "src.csv")
    led = _ledger_with(tmp_path, 3)
    led.stamp("https://example.org/0.pdf", "ocr", version="ocr_boxes-1", n_pages=1, text_method="text")
    led.stamp("https://example.org/1.pdf", "ocr", version="ocr_boxes-1" + ocr.UNREADABLE, n_pages=1,
              text_method="text")
    led.save()
    assert sorted(ocr.pending(Ledger(tmp_path / "state" / "src.csv"), {})) == [
        "https://example.org/1.pdf", "https://example.org/2.pdf"]


def test_recheck_marks_the_documents_read_from_an_illegible_layer_and_nothing_else(monkeypatch, tmp_path):
    from spicy_electronics_index.core import pagesio

    monkeypatch.setattr(ocr, "registry_entry", lambda source: {})
    monkeypatch.setattr(ocr, "schematics_state", lambda source: tmp_path / "state" / "src.csv")
    monkeypatch.setattr(ocr, "ocr_root", lambda: tmp_path / "ocr")
    led = _ledger_with(tmp_path, 3)
    good = [{"page": 1, "how": "text", "blocks": [{"box": [0, 0, 1, 1], "text": "R101 10K Main amplifier board",
                                                   "conf": 1.0}] * 10}]
    bad = [{"page": 1, "how": "text", "blocks": [{"box": [0, 0, 1, 1], "text": " ".join(GARBLED * 3), "conf": 1.0}]}]
    for i, pages in enumerate((good, bad)):
        url = f"https://example.org/{i}.pdf"
        led.stamp(url, "ocr", version="ocr_boxes-1", n_pages=1, text_method="text")
        pagesio.write_pages(tmp_path / "ocr" / "src", ocr.safe_name(url, "pdf"), pages)
    led.save()

    assert ocr.recheck("src", dry=True) == {"checked": 2, "to read again": 1, "pages refused": 1}
    assert Ledger(tmp_path / "state" / "src.csv").rows["https://example.org/1.pdf"]["ocr_v"] == "ocr_boxes-1"
    ocr.recheck("src")
    rows = Ledger(tmp_path / "state" / "src.csv").rows
    assert rows["https://example.org/1.pdf"]["ocr_v"] == "ocr_boxes-1" + ocr.UNREADABLE
    assert rows["https://example.org/0.pdf"]["ocr_v"] == "ocr_boxes-1"
    assert pagesio.is_done(tmp_path / "ocr" / "src", ocr.safe_name("https://example.org/1.pdf", "pdf"))  # kept
