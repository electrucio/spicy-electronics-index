"""Who made a model is read from where its file sits, not from who we fetched it from."""
import pytest

from spicy_electronics_index.models import origin as O

CASES = [
    ("onsemi", "sources/onsemi/raw/mmbt2222a.lib", "onsemi", O.VENDOR),
    ("vishay/semis", "sources/vishay/semis/raw/si2301.lib", "vishay", O.VENDOR),
    ("linear-systems", "sources/linear-systems/raw/LSK170A_transcribed_from_pdf.lib", "linear-systems", O.VENDOR),
    ("ltspice-native", "sources/ltspice-native/raw/standard.bjt", "ltspice-native", O.SIMULATOR),
    ("cordell", "sources/cordell/raw/Cordell-Models.txt", "cordell", O.MODELLER),
    ("diyaudio", "sources/diyaudio/raw/Cabirio-BJTmodels.txt", "cabirio", O.FORUM),
    ("diyaudio", "sources/diyaudio/raw/6SF5_AN_ayumi.lib", "ayumi", O.MODELLER),
    ("groupsio-ltspice", "sources/groupsio-ltspice/extracted/standard.bjt 2/standard.bjt", "ltspice-group", O.COMPILATION),
    ("bordodynov", "sources/bordodynov/extracted/lib/cmp/standard.bjt", "bordodynov", O.COLLECTION),
    ("bordodynov", "sources/bordodynov/extracted/lib/sub/Zener_DiodesInc.lib", "diodes-inc", O.VENDOR_REDIST),
    ("bordodynov", "sources/bordodynov/extracted/lib/sub/Koren_Tubes.lib", "koren", O.MODELLER),
    ("bordodynov", "sources/bordodynov/extracted/lib/cmp/Original/standard.bjt", "ltspice-native", O.SIMULATOR),
    ("bordodynov-qspice", "sources/bordodynov-qspice/extracted/QSPICE0/QSPICE/KT-Cordell models.txt", "cordell", O.MODELLER),
    ("bordodynov-qspice", "sources/bordodynov-qspice/extracted/QSPICE0/QSPICE/npnmy.txt", "bordodynov-qspice", O.COLLECTION),
    ("bordodynov-qspice", "sources/bordodynov-qspice/extracted/QSPICE0/QSPICE/NPN.txt", "qspice", O.SIMULATOR),
    ("ltwiki", "sources/ltwiki/extracted/lib/lib/sub/Triode_Ayumi.lib", "ayumi", O.MODELLER),
    ("ltwiki", "sources/ltwiki/extracted/lib/lib/sub/texas.lib", "ti", O.VENDOR_REDIST),
    ("ltwiki", "sources/ltwiki/extracted/example/examples/Bordodynov/Mixer/a.asc", "bordodynov", O.COLLECTION),
    ("ltwiki", "sources/ltwiki/raw/Spice-Models-collection/Zetex.lib", "zetex", O.VENDOR_REDIST),
    ("ltwiki", "sources/ltwiki/raw/Spice-Models-collection/jbipolar.lib", "spice-models-collection", O.COLLECTION),
    ("ltwiki", "sources/ltwiki/extracted/Standard/Standard/standard.bjt", "ltspice-group", O.COMPILATION),
    ("ltwiki", "sources/ltwiki/extracted/LargeCollection/LargeCollection/LTspiceIV/lib/cmp/standard.bjt", "largecollection", O.COLLECTION),
    ("kicad-spice-library", "sources/kicad-spice-library/raw/KiCad-Spice-Library/Models/uncategorized/Bordodynovs Electronics Lib/cmp/standard.bjt", "bordodynov", O.COLLECTION),
    ("kicad-spice-library", "sources/kicad-spice-library/raw/KiCad-Spice-Library/Models/Manufacturer/Zetex Semiconductors/x.lib", "zetex", O.VENDOR_REDIST),
    ("kicad-spice-library", "sources/kicad-spice-library/raw/KiCad-Spice-Library/Models/Transistor/BJT/BJT.lib", "kicad-spice-library", O.AGGREGATE),
    ("spice-model-cd", "sources/spice-model-cd/raw/Motorola/Spice/PowerBJT/MJ15001.LIB", "motorola", O.VENDOR_REDIST),
    ("spice-model-cd", "sources/spice-model-cd/raw/SiMetrix/MOSFET.LB", "simetrix", O.SIMULATOR),
    ("microcap12", "sources/microcap12/extracted/mc12cd/LIBRARY/On_Semi.lib", "onsemi", O.VENDOR_REDIST),
    ("microcap12", "sources/microcap12/extracted/mc12cd/lbr_txt/msbjt_lbr.lib", "microcap12", O.SIMULATOR),
    ("robrobinette", "sources/robrobinette/extracted/Bassman/Koren_Tubes.INC", "koren", O.MODELLER),
    ("some-new-source", "sources/some-new-source/raw/x.lib", "some-new-source", O.COLLECTION),
    # the browser round of 2026-10-10
    ("mcc", "sources/mcc/extracted/1N4148W/1N4148W.lib", "mcc", O.VENDOR),
    ("taiwan-semi", "sources/taiwan-semi/raw/SPICE/1N4148WS.TXT", "taiwan-semi", O.VENDOR),
    ("panjit", "sources/panjit/extracted/PANJIT_SPICE_Models/01. MOSFET/2N7002K.txt", "panjit", O.VENDOR),
    ("samsung-electro-mechanics", "sources/samsung-electro-mechanics/extracted/Samsung_LTSPICE_Static_Library/sub/MLCC/General/x.mod",
     "samsung-electro-mechanics", O.VENDOR),
    ("fotoelektronika", "sources/fotoelektronika/extracted/1R5T/1R5T.lib", "fotoelektronika", O.MODELLER),
    ("tdsl-cigna", "sources/tdsl-cigna/extracted/tdsl_tubes_spice/12AX7.inc", "tdsl-cigna", O.MODELLER),
    ("stmicro", "sources/stmicro/raw/tl072.txt", "stmicro", O.VENDOR),
    ("stmicro", "sources/stmicro/raw/power-transistors/spice_model/bd139_spice.txt", "stmicro", O.VENDOR),
]


@pytest.mark.parametrize("source,file,who,cls", CASES)
def test_the_author_and_the_distance_from_them(source, file, who, cls):
    o = O.origin(source, file)
    assert (o["who"], o["cls"], o["how"]) == (who, cls, O.HOW[cls])


def test_a_mirror_of_an_archive_ranks_after_the_archives_own_home():
    from spicy_electronics_index.models import found as F
    own = F.rank("bordodynov", "sources/bordodynov/extracted/lib/cmp/standard.bjt")
    mirror = F.rank("ltwiki", "sources/ltwiki/extracted/lib/lib/cmp/standard.bjt")
    bundle = F.rank("kicad-spice-library", "sources/kicad-spice-library/raw/KiCad-Spice-Library/Models/uncategorized/Bordodynovs Electronics Lib/cmp/standard.bjt")
    assert own < mirror < bundle
    assert O.origin("ltwiki", "sources/ltwiki/extracted/Standard/Standard/standard.bjt")["mirror"]
    assert not O.origin("ltwiki", "sources/ltwiki/extracted/LargeCollection/LargeCollection/LTspiceIV/lib/cmp/standard.bjt")["mirror"]
    assert F.rank("groupsio-ltspice", "sources/groupsio-ltspice/extracted/Standard/standard.bjt") < F.rank("ltwiki", "sources/ltwiki/extracted/Standard/Standard/standard.bjt")


def test_a_vendor_file_mirrored_by_ltwiki_ranks_after_the_vendors_own():
    from spicy_electronics_index.models import found as F
    assert O.origin("stmicro", "sources/stmicro/raw/tl072.txt")["mirror"]
    assert not O.origin("stmicro", "sources/stmicro/raw/amplifiers-and-comparators/spice_model/tl07x_family.zip")["mirror"]
    assert not O.origin("stmicro", "sources/stmicro/extracted/tl07x_family/tl072.lib")["mirror"]
    assert (F.rank("stmicro", "sources/stmicro/extracted/tl07x_family/tl072.lib")
            < F.rank("stmicro", "sources/stmicro/raw/tl072.txt"))


def test_every_registered_vendor_of_the_round_has_a_rank_and_a_class():
    from spicy_electronics_index.models import found as F
    for s in ("mcc", "taiwan-semi", "panjit", "fotoelektronika", "tdsl-cigna", "samsung-electro-mechanics"):
        assert s in F.RANK and s in O.SOURCE_CLASS


def test_the_classes_run_from_the_maker_to_the_aggregate():
    assert O.VENDOR < O.VENDOR_REDIST < O.SIMULATOR < O.MODELLER < O.FORUM < O.COMPILATION < O.COLLECTION < O.AGGREGATE
    assert set(O.HOW) == {O.VENDOR, O.VENDOR_REDIST, O.SIMULATOR, O.MODELLER, O.FORUM, O.COMPILATION, O.COLLECTION, O.AGGREGATE}
    assert set(O.TEXT) == set(O.HOW.values()) == set(O.HOW_CLASS)      # every short name has its meaning
