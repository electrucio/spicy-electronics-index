"""Read what has been downloaded and not read yet, page by page, with boxes.

    sei schematics ocr --source audiocircuit [--limit N] [--gpu 0] [--shard 0/4] [--dry]

The stage between `download` and `index`, and the only one that wants a GPU. It takes its work from the
ledger — everything downloaded whose `ocr` stamp is missing or of an older version — so it can be run
again and again while a download is still going, and the two stages need no coordinating. Nothing is
read twice: rule 5 is the ledger's, and the stamp carries the version below.

Per page, not per document: a page with a text layer worth reading is read from it, with the boxes the
layer already gives; a page without one is rendered and passed to the OCR. That is why a born-digital
service manual with two scanned pages at the end does not lose them, and why a scanned sheet with a
typed cover does not lose the sheet.

"Worth reading" is asked of the layer itself since version 2. A PDF can carry text in a font with no
character map, and then the layer is words of `A5P4{+SS+=>` — the Denon AVR-1803 manual has 43 such
pages, its parts list among them, and version 1 took them for born-digital text because there were more
than fifty of them. A layer that does not read as text (`legible`) is now rendered and OCR'd like a scan.
And a rendered page whose lines of text mostly run up the page is read on its side as well, both
ways, keeping the reading with the most words shaped like a schematic's (designators, values, type
numbers): service manuals print their schematic sheets sideways, and an OCR told nothing about that
reads `d61 dBL` where the sheet says `2SK117`. 8.4% of the 994,650 pages version 1 rendered look like
that, so the two extra readings cost about a sixth more. PaddleOCR's own page-orientation model was
tried first and is no use here: it called a sideways schematic upside down with 0.32 confidence. The
boxes are turned back, so they always say where on the upright page a word is.

`--recheck` judges what version 1 read with the same test and marks each document whose layer it would
now refuse, so the next run reads it again; nothing else read by version 1 is read twice (rule 5). The
old reading stays where it is, and keeps serving the index, until the new one replaces it.

Boxes are the point. These are big scanned drawings with no text layer, where ctrl+F finds nothing and
the eye finds nothing either, so a result has to be able to say *where* on the sheet the part is.

Ported from `ocr_raw.py` in the staging tree, behaviour first (rule 7): same page decision, same render
sizes, same record shape, same version stamp, so what was read before is not read again.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import os
import re
import sys
import time
import unicodedata
from pathlib import Path

from spicy_electronics_index.core import pagesio
from spicy_electronics_index.core.config import (
    downloads,
    ocr_map,
    ocr_root,
    ocr_superseded,
    require,
    schematics_state,
)
from spicy_electronics_index.core.ledger import Ledger
from spicy_electronics_index.schematics import cad
from spicy_electronics_index.schematics.download import registry_entry, safe_name

OCR_VERSION = "ocr_boxes-2"          # 2: a layer that does not read as text is rendered; a sideways page is turned
EARLIER = ("ocr_boxes-1",)           # still a good reading, unless --recheck marked it UNREADABLE
UNREADABLE = "-unreadable-layer"     # what --recheck appends to an earlier stamp: read it again
LONG = 4000                          # the long side in pixels a page is rendered at, within 150..300 dpi
MAX_PAGES = 600                      # 80 cut thirty service manuals short: their schematics are at the end
TEXT_WORDS = 50                      # a page with this many words in its text layer is read, not rendered
IMAGE_TYPES = {"gif", "png", "jpeg", "tiff", "bmp"}
OCR_MODELS = "PP-OCRv5"              # see _reader(): v6 needs a newer paddle than the one that is here
LEGIBLE = 0.4                        # below this share of legible words a layer is not text
FOREIGN = 0.3                        # above this share of non-ASCII Latin letters it is a font mapped wrong
SIDEWAYS = 0.45                      # this share of a page's text boxes standing taller than wide: read it turned
_STRIP = ".,:;()[]\"'「」（）、。・"
_NEVER = set("{}<>*=@~^|\\`$")       # in no word of a manual, and in most words of a garbled layer


def version_for(entry: dict) -> str:
    """The stamp a source's documents carry. A source read in another language than the default carries
    it in the stamp, so what was read in English is never taken for what was read in Japanese, and a
    change of language is a new version like any other (rule 5)."""
    return _with_lang(OCR_VERSION, entry)


def _with_lang(version: str, entry: dict) -> str:
    lang = (entry.get("ocr") or {}).get("lang", "en")
    return version if lang == "en" else f"{version}-{lang}"


def accepted(entry: dict, row: dict) -> set[str]:
    """Every stamp that counts as read for this row: this version, or an earlier one --recheck has not
    marked. A design carries its own reader's version as well (see `run`)."""
    out = {_with_lang(v, entry) for v in (OCR_VERSION, *EARLIER)}
    return {f"{v}-cad{cad.VERSION}" for v in out} if row.get("type") in cad.KINDS else out


def is_read(entry: dict, row: dict) -> bool:
    return bool(row.get("ocr_at")) and row.get("ocr_v", "") in accepted(entry, row)


def pending(led: Ledger, entry: dict) -> list[str]:
    """What this stage still has to read in a source: downloaded, not skipped, and not read by any
    accepted version. A design is stamped `text`, which to the ledger means "no OCR pass", and that is
    right for a page with a text layer and wrong for a design, whose reader can change: it is asked
    about by version. A reading --recheck marked is wanted again whatever it was taken from — mostly from
    a text layer, which is exactly what the ledger would otherwise say needs no OCR."""
    return [key for key, row in led.rows.items()
            if row["download_at"] and not row["skip_reason"]
            and (row.get("type") in cad.KINDS or led._applies(row, "ocr")
                 or row.get("ocr_v", "").endswith(UNREADABLE))
            and not is_read(entry, row)]


def legibility(words: list[str]) -> tuple[float | None, float, int]:
    """(share of words that read as words, share of Latin letters outside ASCII, words counted).

    A word reads as a word when at least two of its characters and seven in ten are letters or digits,
    in any script, and none is a character no manual prints in a word (`_NEVER`). Dot leaders, rules
    and lone characters are not counted either way: a contents page and a pin table are full of them."""
    good = counted = latin = foreign = 0
    for word in words:
        w = word.strip(_STRIP)
        if not w or set(w) <= set(".…·-_") or (len(w) == 1 and w.isalnum()):
            continue
        counted += 1
        alnum = sum(1 for c in w if c.isalnum())
        if alnum >= 2 and alnum >= 0.7 * len(w) and not set(w) & _NEVER:
            good += 1
        for c in w:
            if c.isalpha() and "LATIN" in unicodedata.name(c, ""):
                latin += 1
                foreign += not c.isascii()
    return (good / counted if counted else None), (foreign / latin if latin else 0.0), counted


def legible(words: list[str]) -> bool:
    """Whether a text layer reads as text. Too few words to judge is taken as text, as it always was."""
    share, foreign, counted = legibility(words)
    return counted < 20 or (share >= LEGIBLE and foreign <= FOREIGN)


def _reader(gpu: int | None, lang: str = "en"):
    """The OCR itself, loaded only when a page actually needs it — a run with nothing to render must not
    ask for a GPU, and a machine without one must still be able to read born-digital documents."""
    if gpu is not None:
        os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu)
    import numpy as np
    from paddleocr import PaddleOCR

    # The model family is pinned. Left to itself PaddleOCR 3.x fetches PP-OCRv6, which a paddle 3.0
    # build refuses with "Type of attribute: strides is not right" on the first page it is given.
    # `lang` is the registry's: a Japanese magazine is read with PP-OCRv5's Japanese model, which reads the
    # Latin of a part number as well, where the English one turns every kana into a string of letters.
    engine = PaddleOCR(lang=lang, ocr_version=OCR_MODELS, use_doc_orientation_classify=False,
                       use_doc_unwarping=False, use_textline_orientation=False,
                       text_det_limit_side_len=LONG, text_det_limit_type="max")

    def read(img):
        blocks = []
        for res in engine.predict(img):
            for box, txt, score in zip(res["rec_polys"], res["rec_texts"], res["rec_scores"]):
                b = np.asarray(box)
                blocks.append({"box": [int(b[:, 0].min()), int(b[:, 1].min()), int(b[:, 0].max()), int(b[:, 1].max())],
                               "text": txt, "conf": round(float(score), 3)})
        return blocks

    return read


def _open(path: Path, kind: str):
    """A document as pages, whatever it arrived as. MuPDF reads PDFs and most images; the TIFFs it cannot
    decode come through Pillow, including the old JPEG-in-TIFF whose whole JPEG sits in tag 513."""
    import fitz

    try:
        doc = fitz.open(path)
        doc[0].get_pixmap(matrix=fitz.Matrix(0.05, 0.05))
        return doc
    except Exception:                                            # noqa: BLE001
        from PIL import Image

        try:
            im = Image.open(path).convert("L")
        except Exception:                                        # noqa: BLE001
            tif = Image.open(path)
            off, length = tif.tag_v2.get(513), tif.tag_v2.get(514)
            with open(path, "rb") as fh:
                fh.seek(off)
                im = Image.open(io.BytesIO(fh.read(length))).convert("L")
        doc = fitz.open()
        page = doc.new_page(width=im.width, height=im.height)
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        page.insert_image(page.rect, stream=buf.getvalue())
        return doc


def _text_blocks(page, zoom):
    """The text layer as line blocks with their boxes, in the rendered page's own pixels."""
    lines: dict = {}
    for x0, y0, x1, y1, word, block, line, _ in page.get_text("words"):
        d = lines.setdefault((block, line), {"box": [x0, y0, x1, y1], "words": []})
        d["box"] = [min(d["box"][0], x0), min(d["box"][1], y0), max(d["box"][2], x1), max(d["box"][3], y1)]
        d["words"].append(word)
    return [{"box": [int(v * zoom) for v in d["box"]], "text": " ".join(d["words"]), "conf": 1.0}
            for d in lines.values()]


def _words(blocks: list[dict]) -> list[str]:
    return [w for b in blocks for w in b["text"].split()]


_SHAPED = re.compile(r"^(?:(?:R|C|L|D|Q|IC|TR|VR|ZD|SW|CN|J|T|X|F|U)\d{1,4}[A-Z]?"   # designators
                     r"|\d+(?:\.\d+)?[pnuµmkKM]?[FHVWΩ]?"                         # values
                     r"|\d?[A-Z]{1,4}\d{2,5}[A-Z]{0,3}"                            # type numbers
                     r"|[A-Za-z]{3,})$")                                              # words


def _shaped(blocks: list[dict]) -> int:
    """How many words of a reading are shaped like a schematic's: the measure of a page read the right
    way up, since the wrong way still yields letters and digits, only not in those shapes."""
    return sum(1 for w in _words(blocks) if _SHAPED.match(w.strip(".,:;()")))


def _standing(blocks: list[dict]) -> float | None:
    """Share of the text boxes (three characters or more) that are taller than wide, or None under 20."""
    long = [b for b in blocks if len(b["text"].strip()) >= 3]
    if len(long) < 20:
        return None
    return sum(1 for b in long if b["box"][3] - b["box"][1] > 1.5 * (b["box"][2] - b["box"][0])) / len(long)


def unturn(box: list[int], quarter: int, w: int, h: int) -> list[int]:
    """A box read on an image turned by `numpy.rot90(img, quarter)` (counter-clockwise quarters), as a box
    on the upright image of width `w` and height `h`."""
    x0, y0, x1, y1 = box
    if quarter == 1:                     # upright (x, y) went to (y, w - 1 - x)
        return [w - 1 - y1, x0, w - 1 - y0, x1]
    if quarter == 3:                     # upright (x, y) went to (h - 1 - y, x)
        return [y0, h - 1 - x1, y1, h - 1 - x0]
    return list(box)


def read_upright(read_image, img) -> tuple[list[dict], int]:
    """Read a rendered page the way up it reads best: upright, unless SIDEWAYS of its text boxes stand on
    end, and then on either side as well, keeping the reading with the most schematic-shaped words. ->
    (blocks with their boxes on the upright page, degrees the page was turned counter-clockwise)."""
    import numpy as np

    blocks = read_image(img)
    standing = _standing(blocks)
    if standing is None or standing < SIDEWAYS:
        return blocks, 0
    h, w = img.shape[:2]
    best = (_shaped(blocks), 0, blocks)
    for quarter in (1, 3):
        turned = read_image(np.ascontiguousarray(np.rot90(img, quarter)))
        count = _shaped(turned)
        if count > best[0]:
            best = (count, quarter, [{**b, "box": unturn(b["box"], quarter, w, h)} for b in turned])
    return best[2], 90 * best[1]


def read_document(path: Path, kind: str, read_image=None) -> list[dict]:
    """-> one page record per page, in the shape core.pagesio documents."""
    if kind in cad.KINDS:
        return cad.read(path, kind)       # a design, not a picture: its fields are read, nothing is OCR'd
    import fitz
    import numpy as np

    fitz.TOOLS.mupdf_display_errors(False)
    doc = _open(path, kind)
    pages = []
    for pno in range(min(doc.page_count, MAX_PAGES)):
        page = doc[pno]
        long_pt = max(page.rect.width, page.rect.height)
        if kind == "pdf":
            zoom = min(max(LONG / long_pt, 150 / 72), 300 / 72)
        else:
            zoom = 2.0 if long_pt < 1200 else min(1.0, LONG / long_pt)
        words = page.get_text("words") if kind == "pdf" else []
        turned = 0
        if len(words) >= TEXT_WORDS and legible([w[4] for w in words]):
            blocks, how = _text_blocks(page, zoom), "text"
            w_px, h_px = int(page.rect.width * zoom), int(page.rect.height * zoom)
        else:
            if read_image is None:
                raise RuntimeError(f"page {pno + 1} of {path.name} has no text layer, or none legible, and no OCR is loaded")
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csGRAY, alpha=False)
            img = np.stack([np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w)] * 3, axis=-1)
            (blocks, turned), how, w_px, h_px = read_upright(read_image, img), "ocr", pix.w, pix.h
        blocks.sort(key=lambda b: (round(b["box"][1] / 12), b["box"][0]))
        # The size in points travels with the page, because the file does not: the retention rule
        # deletes a scan once it is read, and the zoom link needs the page's points to say where on the
        # sheet a part sits. 481,319 pages of audiocircuit were read and released before this line.
        pages.append({"page": pno + 1, "w": w_px, "h": h_px, "how": how, "blocks": blocks,
                      "w_pt": round(page.rect.width, 1), "h_pt": round(page.rect.height, 1)}
                     | ({"turned": turned} if turned else {}))
    return pages


def _note_in_map(source: str, url: str, method: str, n_pages: int, name: str) -> None:
    """Append to the map that says which file holds which document. Appending, not rewriting: shards run
    beside one another, and a row already there is a document already read."""
    path = ocr_map()
    header = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        if header:
            w.writerow(["source", "doc_key", "text_method", "pages", "ocr_file", "origin"])
        w.writerow([source, url, method, n_pages, f"{source}/{name}.jsonl.gz", "ocr"])


def run(source: str, *, limit: int = 0, gpu: int | None = None, shard: str = "0/1", dry: bool = False) -> dict:
    entry = registry_entry(source)                              # refuses a source that is not registered
    version, lang = version_for(entry), (entry.get("ocr") or {}).get("lang", "en")
    led = Ledger(schematics_state(source))
    k, n = (int(x) for x in shard.split("/"))

    def version_of(row: dict) -> str:
        # A design is read by cad.py and not by the OCR, so it carries that reader's version: when the
        # reader changes what it keeps, every design is read again and no scan is.
        return f"{version}-cad{cad.VERSION}" if row.get("type") in cad.KINDS else version

    todo = [key for key in sorted(pending(led, entry)) if shard_of(key, n) == k]
    if limit:
        todo = todo[:limit]
    folder = ocr_root() / source
    counts = {"to read": len(todo), "read": 0, "already there": 0, "file gone": 0, "failed": 0, "pages": 0}
    if dry or not todo:
        return counts

    read_image, pages_rendered = None, 0
    for url in todo:
        row = led.row(url)
        kind = row.get("type") or "pdf"
        name = safe_name(url, kind)
        again = row.get("ocr_v", "").endswith(UNREADABLE)       # its page file is the reading being replaced
        # A page file already written is a page already read — for a scan. A design's pages are its
        # reader's output, and the ledger has just said that reader has changed, so they are written again.
        if kind not in cad.KINDS and not again and pagesio.is_done(folder, name):
            # Read by another run that never got to stamp it — a trial, a shard that was killed. The pages
            # are the work; the stamp is taken from them, or the ledger offers this document forever.
            pages = pagesio.read_pages(pagesio.existing(folder, name))
            how = "ocr_boxes" if any(p.get("how") == "ocr" for p in pages) else "text"
            led.stamp(url, "ocr", version=version_of(row), n_pages=len(pages), text_method=how)
            counts["already there"] += 1
            continue
        path = downloads(source) / kind / name
        if not path.exists():
            counts["file gone"] += 1                             # `sei schematics verify --repair` fetches these back
            continue
        t0 = time.time()
        try:
            if read_image is None and kind not in ("html", *cad.KINDS):
                read_image = _reader(gpu, lang)                  # loaded once, on the first document
            pages = read_document(path, kind, read_image)
        except Exception as e:                                   # noqa: BLE001  a broken file must not stop the batch
            counts["failed"] += 1
            print(f"  ERROR {name}: {str(e)[:120]}", file=sys.stderr, flush=True)
            continue
        if again:
            supersede(source, name)
        pagesio.write_pages(folder, name, pages)
        how = "ocr_boxes" if any(p["how"] == "ocr" for p in pages) else "text"
        _note_in_map(source, url, how, len(pages), name)
        led.stamp(url, "ocr", version=version_of(row), n_pages=len(pages), text_method=how)
        if again:
            led.clear_after(url, "ocr")                          # so `ingest` replaces what it holds
        counts["read"] += 1
        counts["pages"] += len(pages)
        pages_rendered += sum(1 for p in pages if p["how"] == "ocr")
        if counts["read"] % 25 == 0:
            led.save()
        print(f"  {name[:60]}: {len(pages)} pages ({sum(1 for p in pages if p['how'] == 'ocr')} by OCR)"
              f" in {time.time() - t0:.0f}s", flush=True)
    led.save()
    counts["rendered pages"] = pages_rendered
    return counts


def shard_of(key: str, n: int) -> int:
    """Which of `n` shards reads this document: fixed by its key alone. It was its place in the pending
    list, which is the same for every shard only while none has stamped anything yet. Shards that reach a
    source at different times — every batch with more than one source — saw different lists: on
    2026-10-06 four shards made 3,732 readings of 1,470 Renesas notes and left 3,109 unread."""
    return int(hashlib.sha1(key.encode("utf-8")).hexdigest(), 16) % n


def supersede(source: str, name: str) -> None:
    """Move a reading about to be replaced out of the OCR tree, keeping it."""
    old = pagesio.existing(ocr_root() / source, name)
    if old is None:
        return
    dest = ocr_superseded(source)
    dest.mkdir(parents=True, exist_ok=True)
    old.replace(dest / old.name)
    pagesio.done_path(ocr_root() / source, name).unlink(missing_ok=True)


def recheck(source: str, dry: bool = False) -> dict:
    """Mark for reading again each document an earlier version read from a layer `legible` refuses.

    Only the ledger changes: the earlier stamp gets UNREADABLE appended, which no version accepts, so
    `pending` offers the document again, `verify --repair` fetches it back if its file was released, and
    the old reading keeps serving the index until the new one is written over it."""
    entry = registry_entry(source)
    led = Ledger(schematics_state(source))
    earlier = {_with_lang(v, entry) for v in EARLIER}
    folder = ocr_root() / source
    counts = {"checked": 0, "to read again": 0, "pages refused": 0}
    marked = []
    for key, row in led.rows.items():
        if row["skip_reason"] or row.get("type") in cad.KINDS or row.get("ocr_v") not in earlier:
            continue
        path = pagesio.existing(folder, safe_name(key, row.get("type") or "pdf"))
        if path is None:
            continue
        counts["checked"] += 1
        refused = sum(1 for p in pagesio.iter_pages(path)
                      if p.get("how") == "text" and not legible(_words(p.get("blocks") or [])))
        if refused:
            marked.append(key)
            counts["to read again"] += 1
            counts["pages refused"] += refused
    if marked and not dry:
        fresh = Ledger(schematics_state(source))                 # re-read now: another stage may have saved
        for key in marked:
            r = fresh.rows[key]
            fresh.stamp(key, "ocr", version=r["ocr_v"] + UNREADABLE, when=r["ocr_at"],
                        n_pages=r["n_pages"], text_method=r["text_method"])
        fresh.save()
    return counts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="sei schematics ocr", description=__doc__.splitlines()[0])
    ap.add_argument("--source", action="append", required=True, help="a source with documents downloaded (repeatable)")
    ap.add_argument("--limit", type=int, default=0, help="at most this many documents")
    ap.add_argument("--gpu", type=int, default=None, help="which GPU to give the OCR")
    ap.add_argument("--shard", default="0/1", help="k/n: read only every nth document, for running several at once")
    ap.add_argument("--dry", action="store_true", help="say how much there is to read and read nothing")
    ap.add_argument("--recheck", action="store_true",
                    help="mark what an earlier version read from an illegible text layer, to be read again")
    a = ap.parse_args(argv)
    require(ocr_root().parent, "reading downloaded documents")
    for source in a.source:
        if a.recheck:
            counts = recheck(source, dry=a.dry)
        else:
            counts = run(source, limit=a.limit, gpu=a.gpu, shard=a.shard, dry=a.dry)
        print(f"{source}: " + ", ".join(f"{v} {k}" for k, v in counts.items() if v))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
