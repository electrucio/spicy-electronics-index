"""The symbol a model was published with: same place, same name, as many pins, the model's own file."""
from __future__ import annotations

from spicy_electronics_index.models import symbols as S

ASY = """Version 4
SymbolType CELL
SYMATTR Prefix X
SYMATTR Value Relay_2A2B
SYMATTR ModelFile Relay_2A2B.sub
PIN 0 0 NONE 8
PINATTR PinName Coil+
PINATTR SpiceOrder 1
PIN 0 32 NONE 8
PINATTR PinName Coil-
PINATTR SpiceOrder 2
"""


def sym(file, model="Relay_2A2B", pins=("Coil+", "Coil-"), model_file="", prefix="X"):
    return {"file": file, "source": file.split("/")[1], "sha256": "x", "prefix": prefix, "model": model,
            "model_file": model_file, "pins": list(pins)}


def test_a_symbol_names_its_model_by_spicemodel_or_by_the_value_of_an_x_symbol():
    s = S.read(ASY)
    assert s == {"prefix": "X", "model": "Relay_2A2B", "model_file": "Relay_2A2B.sub", "pins": ["Coil+", "Coil-"]}
    assert S.read(ASY.replace("SYMATTR Value Relay_2A2B", "SYMATTR SpiceModel R2")).get("model") == "R2"
    assert S.read(ASY.replace("Prefix X", "Prefix R"))["model"] == ""        # a resistor's value is not a model


def test_only_the_symbol_published_beside_the_model_is_taken():
    by = {S.norm("Relay_2A2B"): [
        sym("sources/loosweb-relay/raw/downloads/Relay_2A2B.asy", model_file="Relay_2A2B.sub"),
        sym("sources/bordodynov/extracted/lib/sym/Relay_2A2B.asy")]}
    got = S.symbol_for("Relay_2A2B", 2, "sources/loosweb-relay/raw/downloads/Relay_2A2B.sub", by)
    assert got["file"] == "sources/loosweb-relay/raw/downloads/Relay_2A2B.asy"
    # inside one archive the symbol may sit in another folder of it
    got = S.symbol_for("relay_2a2b", 2, "sources/bordodynov/extracted/lib/sub/relays.lib", by)
    assert got["file"] == "sources/bordodynov/extracted/lib/sym/Relay_2A2B.asy"
    assert S.symbol_for("Relay_2A2B", 2, "sources/ltwiki/extracted/lib/sub/x.lib", by) is None   # another collection's


def test_a_symbol_with_other_pins_or_another_model_file_is_not_the_models():
    by = {S.norm("VINT30"): [sym("sources/b/extracted/lib/sym/v.asy", "VINT30", ("A",)),
                             sym("sources/b/extracted/lib/sym/w.asy", "VINT30", ("A", "B"), "speaker.lib")]}
    assert S.symbol_for("VINT30", 2, "sources/b/extracted/lib/sub/parlante.lib", by) is None
    assert S.symbol_for("VINT30", 2, "sources/b/extracted/lib/sub/speaker.lib", by)["file"].endswith("w.asy")


def test_a_symbol_that_names_no_model_or_a_file_is_named_by_its_file():
    s = S.read(ASY.replace("SYMATTR Value Relay_2A2B\n", "").replace("SYMATTR ModelFile Relay_2A2B.sub\n", "SYMATTR SpiceModel Trafos.lib\n"))
    assert (s["model"], s["model_file"]) == ("", "Trafos.lib")
    by = {S.norm("XFMR2"): [sym("sources/b/extracted/lib/sym/xfmr2.asy", "", ("1", "2"), "Trafos.lib")]}
    assert S.symbol_for("XFMR2", 2, "sources/b/extracted/lib/sub/Trafos.lib", by)["file"].endswith("xfmr2.asy")
    assert S.symbol_for("XFMR2", 2, "sources/b/extracted/lib/sub/Other.lib", by) is None
