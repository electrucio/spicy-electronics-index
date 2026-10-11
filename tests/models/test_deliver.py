"""A collection gathered in a browser becomes deliveries ingest takes: every file with its address."""
import csv
import io
import tarfile
import zipfile

import pytest

from spicy_electronics_index.core import config
from spicy_electronics_index.models import deliver as D
from spicy_electronics_index.models import ingest as I

MODEL = b".model BAS28 D(IS=1e-14)\n"
SUBCKT = b".SUBCKT X 1 2\n.ENDS\n"
PAGE = b"<!DOCTYPE html><html><title>Sign in</title></html>"


def tar_with(path, members: dict[str, bytes]) -> None:
    with tarfile.open(path, "w") as t:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))


def zip_with(path, members: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w") as z:
        for name, data in members.items():
            z.writestr(name, data)


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
    root = tmp_path / "SPICE-models"
    (root / "44_Central_Semi").mkdir(parents=True)
    (root / "49_MCC").mkdir()
    (root / "45_PANJIT").mkdir()
    tar_with(root / "44_Central_Semi/Central_Semi_SPICE_models.tar", {
        "Central_Semi/FUENTE.txt": b"Central Semi listing\nOK: 3\n",
        "Central_Semi/Diodos/BAS28.LIB": MODEL,
        "Central_Semi/Diodos/BAS56.LIB": PAGE,                       # a login page saved as a model
        "Central_Semi/Bipolares/2N3963.LIB": SUBCKT,
        "Central_Semi/Bipolares/Thumbs.db": b"\x00\x01",
        "__MACOSX/._x.LIB": b"junk",
    })
    tar_with(root / "49_MCC/MCC_SPICE_models.tar", {
        "MCC/diodes/1N4148W.zip": _zipbytes({"1N4148W.lib": MODEL}),
        "MCC/mosfets/BSS84.zip": _zipbytes({"BSS84.lib": SUBCKT}),
    })
    zip_with(root / "45_PANJIT/PANJIT_SPICE_Models.zip", {"01. MOSFET/2N7002K.txt": MODEL})
    (root / "MANIFEST.tsv").write_text(
        "fecha\tcarpeta\tarchivo\tbytes\turl\tnota\n"
        "2026-10-10_11:26\t44_Central_Semi\tCentral_Semi_SPICE_models.tar\t1\thttps://my.centralsemi.com/x\tlisting\n"
        "2026-10-10_12:00\t49_MCC\tMCC_SPICE_models.tar\t1\thttps://www.mccsemi.com/\t\n"
        "2026-10-10_13:00\t45_PANJIT\tPANJIT_SPICE_Models.zip\t1\thttps://www.panjit.com.tw/en/Support?filter=34\t\n",
        encoding="utf-8")
    (root / "SEGURIDAD.md").write_text("| x | 1 | `" + "0" * 64 + "` |\n", encoding="utf-8")
    return root


def _zipbytes(members: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in members.items():
            z.writestr(name, data)
    return buf.getvalue()


def rows(path):
    return list(csv.DictReader(open(path, encoding="utf-8")))


def test_every_file_arrives_with_the_vendors_own_address(collection, trees, tmp_path):
    out = D.deliver_source(D.SPECS["central-semi"], D.Context(collection))
    home = D.write(D.SPECS["central-semi"], D.Context(collection), out, tmp_path / "into")
    by_file = {r["fichero"]: r for r in rows(home / "descargas.csv")}
    assert by_file["Diodos/BAS28.LIB"]["url_descarga"] == "https://www.centralsemi.com/docs/ENGINEERING/csm/BAS28.LIB"
    assert by_file["Diodos/BAS28.LIB"]["pieza"] == "BAS28" and by_file["Diodos/BAS28.LIB"]["fecha"] == "2026-10-10"
    assert by_file["Bipolares/2N3963.LIB"]["estado"] == "encontrado"
    assert (home / "central-semi" / "Diodos" / "BAS28.LIB").read_bytes() == MODEL
    assert (home / "DELIVERY.md").read_text().startswith("# central-semi")


def test_a_page_saved_as_a_model_is_recorded_as_not_published(collection, trees):
    out = D.deliver_source(D.SPECS["central-semi"], D.Context(collection))
    page = [r for r in out.rows if r["estado"] == "no_publicado"]
    assert len(page) == 1 and page[0]["pieza"] == "BAS56" and page[0]["fichero"] == ""
    assert page[0]["url_descarga"].endswith("/BAS56.LIB")
    assert out.counts["left:junk"] == 3        # Thumbs.db, the __MACOSX fork and the round's own note


def test_what_the_source_already_holds_is_not_delivered_again(collection, trees):
    from spicy_electronics_index.models.fetch import Manifest
    m = Manifest("central-semi")
    m.add("https://www.centralsemi.com/docs/ENGINEERING/csm/BAS28.LIB", "raw/BAS28.LIB", MODEL)
    m.save()
    (config.spice_source("central-semi") / "raw").mkdir(parents=True)
    (config.spice_source("central-semi") / "raw" / "BAS28.LIB").write_bytes(MODEL)
    I._held.clear()
    out = D.deliver_source(D.SPECS["central-semi"], D.Context(collection))
    assert out.counts["held_already"] == 1 and "Diodos/BAS28.LIB" not in out.files


def test_an_archive_offered_on_a_page_carries_the_page_and_no_address(collection, trees, tmp_path):
    out = D.deliver_source(D.SPECS["panjit"], D.Context(collection))
    assert len(out.rows) == 1
    r = out.rows[0]
    assert r["url_descarga"] == "" and r["url_pagina"] == "https://www.panjit.com.tw/en/Support?filter=34"
    assert r["fichero"] == "PANJIT_SPICE_Models.zip"


def test_zips_inside_a_tar_are_files_ingest_will_open(collection, trees):
    out = D.deliver_source(D.SPECS["mcc"], D.Context(collection))
    assert set(out.files) == {"diodes/1N4148W.zip", "mosfets/BSS84.zip"}
    assert {r["url_descarga"] for r in out.rows} == {"https://www.mccsemi.com/diodespicemodel/1N4148W.zip",
                                                     "https://www.mccsemi.com/diodespicemodel/BSS84.zip"}


def test_the_delivery_is_what_ingest_takes(collection, trees, tmp_path):
    """End to end: deliver, then ingest the result as the maintainer would."""
    c = D.Context(collection)
    home = D.write(D.SPECS["mcc"], c, D.deliver_source(D.SPECS["mcc"], c), tmp_path / "into")
    counts = I.ingest(home)
    assert counts["into:mcc"] == 2 and counts["unpacked"] == 2
    led = {r["key"]: r for r in rows(trees / "state/mcc.csv")}
    assert led["https://www.mccsemi.com/diodespicemodel/1N4148W.zip"]["status"] == "downloaded"
    assert led["part:1N4148W"]["status"] == "downloaded"
    assert (trees / "models/sources/mcc/extracted/1N4148W/1N4148W.lib").is_file()
    assert (trees / "models/sources/mcc/delivery/DELIVERY.md").is_file()


def test_an_insecure_file_is_never_delivered(collection, trees):
    import hashlib
    sha = hashlib.sha256(SUBCKT).hexdigest()
    (collection / "SEGURIDAD.md").write_text(f"| x | 1 | `{sha}` |\n", encoding="utf-8")
    out = D.deliver_source(D.SPECS["central-semi"], D.Context(collection))
    assert out.counts["left:insecure"] == 1 and "Bipolares/2N3963.LIB" not in out.files


def test_nothing_in_the_log_names_this_machine(collection, trees):
    out = D.deliver_source(D.SPECS["central-semi"], D.Context(collection))
    D.check_public(out, collection)
    out.rows[0]["url_descarga"] = f"file://{collection}/x"
    with pytest.raises(ValueError):
        D.check_public(out, collection)


def test_an_address_off_the_vendors_host_is_refused(collection, trees, monkeypatch):
    bad = D.Spec("central-semi", "x", ("44_Central_Semi/Central_Semi_SPICE_models.tar",), "https://x/", ("www.centralsemi.com",),
                 select=lambda m: m.endswith(".LIB"), url=lambda m, c: "https://evil.example/" + m)
    with pytest.raises(ValueError, match="not an address"):
        D.deliver_source(bad, D.Context(collection))


def test_a_signed_link_is_refused(collection, trees):
    bad = D.Spec("central-semi", "x", ("44_Central_Semi/Central_Semi_SPICE_models.tar",), "https://x/", ("www.centralsemi.com",),
                 select=lambda m: m.endswith(".LIB"), url=lambda m, c: "https://www.centralsemi.com/f?token=abc")
    with pytest.raises(ValueError, match="not an address"):
        D.deliver_source(bad, D.Context(collection))


def test_a_tar_member_that_escapes_is_skipped(tmp_path, trees):
    root = tmp_path / "c"
    (root / "44_Central_Semi").mkdir(parents=True)
    tar_with(root / "44_Central_Semi/Central_Semi_SPICE_models.tar", {
        "Central_Semi/../../escape.LIB": MODEL, "Central_Semi/ok.LIB": MODEL})
    out = D.deliver_source(D.SPECS["central-semi"], D.Context(root))
    assert list(out.files) == ["ok.LIB"]


def test_a_library_is_opened_only_for_its_exemplars(tmp_path, trees):
    root = tmp_path / "c"
    (root / "02_Murata/LTspice").mkdir(parents=True)
    zip_with(root / "02_Murata/LTspice/murata-lib-ltspice-s-mlcc-2606.zip", {
        "murata-lib-ltspice-s-mlcc-2606/sub/Murata_static/MLCC/GRM.lib": b".SUBCKT GRM188R71H104KA93 1 2\n.ENDS\n",
        "murata-lib-ltspice-s-mlcc-2606/sub/Murata_static/MLCC/GCM.lib": SUBCKT,
    })
    (root / "MANIFEST.tsv").write_text(
        "fecha\tcarpeta\tarchivo\tbytes\turl\tnota\n"
        "2026-10-10_11:28\t02_Murata/LTspice\tmurata-lib-ltspice-s-mlcc-2606.zip\t1\t"
        "https://www.murata.com/-/media/x/murata-lib-ltspice-s-mlcc-2606.ashx\tv26.06\n", encoding="utf-8")
    out = D.deliver_source(D.SPECS["murata"], D.Context(root))
    r = out.rows[0]
    assert r["url_descarga"].startswith("https://www.murata.com/") and r["fichero"] == "murata-lib-ltspice-s-mlcc-2606.zip"
    assert "*/sub/Murata_static/MLCC/GRM.lib" in r["miembros"].split(";")
    assert out.counts.get("archive_missing") == 3           # the other three archives of the spec are not here


@pytest.mark.parametrize("member,part", [
    ("Central_Semi/Diodos/BZX84C4V7.LIB", "BZX84C4V7"),
    ("SPICE_Model/MOSFETs/si4202dy_ps.txt", "SI4202DY"),
    ("spice/discrete/transistor/mosfet/rs7l200cg_SPICE.zip", "RS7L200CG"),
    ("parts/506_1N6263W.spice.txt", "506"),
    ("ST/power-transistors/spice_model/stp55nf06_spice.txt", "STP55NF06"),
])
def test_the_part_a_file_is_about(member, part):
    assert D.part_of(member) == part


def test_a_newer_ti_product_is_addressed_by_its_lit_code(tmp_path):
    c = D.Context(tmp_path)
    assert D._ti_url("TI_productos_nuevos/BUF802/SBOMC43.zip", c) == "https://www.ti.com/lit/zip/SBOMC43"
    assert D._ti_url("TI_productos_nuevos/X/readme.zip", c) is None


def test_ti_takes_what_is_wanted_or_analogue(tmp_path, trees, monkeypatch):
    root = tmp_path / "c"
    (root / "28_TI").mkdir(parents=True)
    tar_with(root / "28_TI/TI_PSpice_models_5351.tar", {
        "pspice/INDICE.txt": (b"head\n\nINDICE (archivo, codigo lit, titulo):\n"
                              b"pspice/ADC3442__slam228.zip\tSLAM228\tADC3xxx Pspice Model\n"
                              b"pspice/OPA1692__sbom912.zip\tSBOM912\tOPA1692 PSpice Model\n"
                              b"pspice/TL072__sloj067.zip\tSLOJ067\tTL07x PSpice Model\n"
                              b"pspice/LM2576__snvm001.zip\tSNVM001\tLM2576 TINA-TI Reference Design\n"),
        "pspice/ADC3442__slam228.zip": _zipbytes({"a.lib": SUBCKT}),
        "pspice/OPA1692__sbom912.zip": _zipbytes({"b.lib": SUBCKT + b"x"}),
        "pspice/TL072__sloj067.zip": _zipbytes({"c.lib": SUBCKT + b"xx"}),
        "pspice/LM2576__snvm001.zip": _zipbytes({"d.lib": SUBCKT + b"xxx"}),
    })
    (root / "MANIFEST.tsv").write_text("fecha\tcarpeta\tarchivo\tbytes\turl\tnota\n", encoding="utf-8")
    c = D.Context(root)
    monkeypatch.setattr(D.Context, "wanted", {"TL072"})
    out = D.deliver_source(D.SPECS["ti"], c)
    assert set(out.files) == {"pspice/OPA1692__sbom912.zip", "pspice/TL072__sloj067.zip"}
    assert {r["url_descarga"] for r in out.rows} == {"https://www.ti.com/lit/zip/SBOM912", "https://www.ti.com/lit/zip/SLOJ067"}
    assert {r["pieza"] for r in out.rows} == {"OPA1692", "TL072"}


@pytest.mark.parametrize("member,taken,rel,url", [
    ("SPICE_model/BC807-16.txt", True, "BC807-16.txt", "https://assets.nexperia.com/documents/spice-model/BC807-16.txt"),
    ("Nexperia_extra/SPICE_model/NX3008CBKS.ZIP", True, "NX3008CBKS.ZIP", "https://assets.nexperia.com/documents/spice-model/NX3008CBKS.ZIP"),
    ("Nexperia_extra/SPICE_model/BAT760.prm", True, "BAT760.prm", None),
    ("Nexperia_extra/SPICE_model/PMV20XNEA.lib", True, "PMV20XNEA.lib", None),
    ("Nexperia_extra/Thermal_model/x.txt", False, "", None),
    ("Thermal_design/PBSS4360Z_cauer.txt", False, "", None),
])
def test_nexperias_two_tars_are_read_alike(member, taken, rel, url):
    """The round's second tar carries a top folder of its own, and models in .lib and .prm as well as .txt.
    The asset store answers for .txt and .zip by name; .prm and .lib have no address and get the product page."""
    s = D.SPECS["nexperia"]
    assert s.select(member) is taken
    if taken:
        assert s.rel(member) == rel
        assert s.url(member, None) == url
        assert s.page_of(member) == f"https://www.nexperia.com/product/{rel.split('.')[0]}"


def test_only_what_the_recipes_cite_is_delivered(collection, trees):
    """A trimmed delivery: files by checksum, archives whole but opened only for the cited members."""
    import hashlib
    keep = {hashlib.sha256(MODEL).hexdigest()}                      # BAS28.LIB, and the member inside 1N4148W.zip
    out = D.deliver_source(D.SPECS["central-semi"], D.Context(collection), keep)
    assert list(out.files) == ["Diodos/BAS28.LIB"] and out.counts["left:not_cited"] == 1
    out = D.deliver_source(D.SPECS["mcc"], D.Context(collection), keep)
    assert list(out.files) == ["diodes/1N4148W.zip"]
    assert out.rows[0]["miembros"] == "1N4148W.lib"
