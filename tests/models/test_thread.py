"""A forum thread gathered in a browser becomes one delivery: the attachments, and the posts' models alone."""
import csv
import io
import tarfile
import zipfile

import pytest

from spicy_electronics_index.core import config
from spicy_electronics_index.models import ingest as I
from spicy_electronics_index.models import thread as T

THREAD = "https://forum.example/community/threads/tube-models.243950"
TRIODE = ".SUBCKT TRIODE 1 2 3\nR1 1 3 1k\n.ENDS TRIODE\n"
SYMBOL = b"Version 4\nSymbolType CELL\nSYMATTR Prefix X\nSYMATTR Value 6SN7\n"


def post(n: int) -> str:
    return f"{THREAD}/post-{n}"


def att(id_: int) -> str:
    return f"https://forum.example/community/attachments/file.{id_}/"


def header(id_: str, name: str, number: str, user: str, n: int, attached: str = "") -> str:
    rule = "* " + "=" * 74
    lines = [rule, '* Modelo SPICE extraido del hilo', f"* {THREAD}/",
             f"* ID catalogo: {id_}   Valvula: {name}   Tipo: Triodo   Subcircuito: {name}",
             "* Autor original: someone  [firma en el modelo]", "* Fuente original: -",
             f"* Primera aparicion: {number} por {user} (2014-03-18) - rol: autor", f"* {post(n)}"]
    if attached:
        lines.append(f"* Adjunto: {attached}")
    return "\n".join(lines + [rule]) + "\n"


def tar_gz(members: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def zip_of(members: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in members.items():
            z.writestr(name, data)
    return buf.getvalue()


@pytest.fixture()
def trees(tmp_path, monkeypatch):
    """An empty private tree and registry, so nothing is "already held"."""
    monkeypatch.setenv("SEI_SPICE_MODELS", str(tmp_path / "models"))
    monkeypatch.setenv("SEI_MATERIAL", str(tmp_path / "material"))
    monkeypatch.setattr(config, "model_state", lambda s: tmp_path / "state" / f"{s}.csv")
    monkeypatch.setattr(config, "model_sources", lambda s=None: (tmp_path / "reg" / f"{s}.yaml") if s else tmp_path / "reg")
    for m in (I, __import__("spicy_electronics_index.models.fetch", fromlist=["x"])):
        for n in ("model_state", "model_sources"):
            if hasattr(m, n):
                monkeypatch.setattr(m, n, getattr(config, n))
    (tmp_path / "reg").mkdir()
    I._held.clear()
    return tmp_path


@pytest.fixture()
def collection(tmp_path):
    root = tmp_path / "thread"
    files = {
        # post 10: a library, and the symbols for it in a zip of their own
        (101, "tubes.txt", 10): b"* tubes\n.SUBCKT 12AX7 P G K\nX1 P G K TRIODE\n.ENDS\n" + TRIODE.encode(),
        (102, "Tubes_sym.zip", 10): zip_of({"Tubes/6SN7.asy": SYMBOL, "Tubes/readme.txt": b"symbols"}),
        # post 20: a project zip, opened for its model and its symbol only
        (201, "amp.zip", 20): zip_of({"amp/6V6.inc": b".SUBCKT 6V6 P G2 G K\n.ENDS\n", "amp/6V6.asy": SYMBOL,
                                      "amp/scope.png": b"\x89PNG....", "amp/amp.asc": b"TEXT 1 2 Left 2 !.tran 1"}),
        # post 30: a schematic whose directives hold a model the index cannot read there
        (301, "test.asc", 30): b"Version 4\nTEXT 0 0 Left 2 !.SUBCKT EL84 P G2 G K\\n.ENDS\n",
        # post 40: a .tar.gz the forum calls .zip; post 41: the same files as a real zip
        (401, "curves.zip", 40): tar_gz({"curves/300B.lib": b".SUBCKT 300B P G K\n.ENDS\n"}),
        (411, "curves.zip", 41): zip_of({"300B.lib": b".SUBCKT 300B P G K\n.ENDS\n"}),
        # post 50: a document with no model in it
        (501, "datasheet.pdf", 50): b"%PDF-1.4 nothing here",
    }
    rows = []
    (root / "attachments" / "files").mkdir(parents=True)
    for (id_, name, n), data in files.items():
        local = f"attachments/files/att{id_}_{name}"
        (root / local).write_bytes(data)
        rows.append(dict(attachment_id=id_, filename=name, local_path=local, kind="file", ext=name.rsplit(".", 1)[1],
                         size_bytes=len(data), post_num=f"#{n}", post_id=n, author="poster", post_datetime="2014-03-18T02:41:09+0100",
                         post_url=post(n), attachment_url=att(id_)))
    with open(root / "attachments_manifest.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    models = {
        "M0001_12AX7": header("M0001", "12AX7", "#10", "kevin", 10, "tubes.txt") + "* tubes\n.SUBCKT 12AX7 P G K\n.ENDS\n",
        "M0002_6V6": header("M0002", "6V6", "#20", "poster", 20, "amp.zip -> amp/6V6.inc") + ".SUBCKT 6V6 P G2 G K\n.ENDS\n",
        "M0003_EL84": header("M0003", "EL84", "#30", "poster", 30, "test.asc") + ".SUBCKT EL84 P G2 G K\n.ENDS\n",
        "M0004_300B": header("M0004", "300B", "#40", "cogs", 40, "curves.zip -> curves/300B.lib") + ".SUBCKT 300B P G K\n.ENDS\n",
        # post 60: two models in the text, one of them unclosed, the other with a dependency the catalogue
        # appended that the post also gives as a model of its own
        "M0005_6SN7": header("M0005", "6SN7", "#60", "koonw", 60)
        + "* --- cabecera del archivo/libreria original ---\n* LIBRARY HEAD\n"
        + ".SUBCKT 6SN7 P G K\nX1 P G K TRIODE\n.ENDS\n\n* --- dependencia incluida desde la misma fuente ---\n" + TRIODE,
        "M0006_TRIODE": header("M0006", "TRIODE", "#60", "koonw", 60) + TRIODE,
        "M0007_0A3": header("M0007", "0A3", "#60", "koonw", 60)
        + ".SUBCKT 0A3 1 2\nD1 2 1 DF\n\n* .ENDS anadido por el catalogo (no estaba en el original)\n.ENDS 0A3\n",
        # post 70: a curve tracer's macro, not SPICE
        "M0008_6L6": header("M0008", "6L6", "#70", "cogs", 70) + "koren8(6L6, 1.2, 3.4)\n",
    }
    (root / "modelos_spice" / "valvulas").mkdir(parents=True)
    for name, text in models.items():
        (root / "modelos_spice" / "valvulas" / f"{name}.inc").write_text(text, encoding="utf-8")
    return root


def test_each_model_comes_from_where_it_was_first_published(collection, trees):
    out = T.deliver(collection, "diyaudio", "2026-10-22")
    assert set(out.files) == {
        "thread-243950/10/att101_tubes.txt", "thread-243950/10/att102_Tubes_sym.zip", "thread-243950/20/att201_amp.zip",
        "thread-243950/41/att411_curves.zip", "thread-243950/30/EL84_post30.txt", "thread-243950/60/6SN7_post60.txt"}
    by_file = {r["fichero"]: r for r in out.rows}
    assert by_file["thread-243950/10/att101_tubes.txt"]["url_descarga"] == att(101)
    assert by_file["thread-243950/10/att101_tubes.txt"]["url_pagina"] == post(10)
    assert by_file["thread-243950/60/6SN7_post60.txt"]["url_descarga"] == post(60)
    assert out.files["thread-243950/10/att101_tubes.txt"] == (collection / "attachments/files/att101_tubes.txt").read_bytes()
    assert out.counts["models_not_spice"] == 1 and out.counts["models_in_a_repacked_archive"] == 1
    assert any("curves.zip (#40" in x and att(411) in x for x in out.left_out)


def test_a_zip_is_opened_for_its_models_and_symbols_only(collection, trees):
    out = T.deliver(collection, "diyaudio", "2026-10-22")
    by_file = {r["fichero"]: r for r in out.rows}
    assert by_file["thread-243950/20/att201_amp.zip"]["miembros"].split(";") == ["amp/6V6.inc", "amp/6V6.asy"]
    assert by_file["thread-243950/10/att102_Tubes_sym.zip"]["miembros"] == "Tubes/6SN7.asy"
    assert out.counts["symbol_archives"] == 1


def test_a_post_file_holds_the_models_alone_as_the_post_gave_them(collection, trees):
    text = T.deliver(collection, "diyaudio", "2026-10-22").files["thread-243950/60/6SN7_post60.txt"].decode()
    assert text.startswith(f"* {post(60)} — koonw\n")
    assert "catalogo" not in text and "dependencia" not in text and "cabecera" not in text
    assert text.count(".SUBCKT TRIODE") == 1                      # the dependency is the post's own model
    assert f"{T.ENDS_SAID}\n.ENDS 0A3" in text
    assert "* LIBRARY HEAD" in text
    asc = T.deliver(collection, "diyaudio", "2026-10-22").files["thread-243950/30/EL84_post30.txt"].decode()
    assert "* from the attachment test.asc" in asc and ".SUBCKT EL84" in asc


def test_what_the_source_already_holds_is_not_delivered_again(collection, trees):
    from spicy_electronics_index.models.fetch import Manifest
    m = Manifest("diyaudio")
    m.add(post(60), "raw/6SN7_post60.txt", b"held")
    m.save()
    (config.spice_source("diyaudio") / "raw").mkdir(parents=True)
    (config.spice_source("diyaudio") / "raw" / "6SN7_post60.txt").write_bytes(b"held")
    I._held.clear()
    out = T.deliver(collection, "diyaudio", "2026-10-22")
    assert "thread-243950/60/6SN7_post60.txt" not in out.files and out.counts["held_already"] == 1


def test_the_delivery_is_what_ingest_takes(collection, trees, tmp_path):
    out = T.deliver(collection, "diyaudio", "2026-10-22")
    home = T.write(collection, "diyaudio", out, tmp_path / "into", "2026-10-22")
    counts = I.ingest(home)
    assert counts["into:diyaudio"] == 6
    src = trees / "models/sources/diyaudio"
    assert (src / "extracted/att201_amp/amp/6V6.inc").is_file() and (src / "extracted/att201_amp/amp/6V6.asy").is_file()
    assert not (src / "extracted/att201_amp/amp/scope.png").exists()
    led = {r["key"]: r for r in csv.DictReader(open(trees / "state/diyaudio.csv", encoding="utf-8"))}
    assert led[post(60)]["status"] == "downloaded" and led[att(101)]["status"] == "downloaded"
    assert not any(k.startswith("part:") for k in led)            # a thread answers no search of its own
    assert (src / "delivery/descargas_thread-243950.csv").is_file()
    assert (src / "delivery/DELIVERY_thread-243950.md").is_file()
