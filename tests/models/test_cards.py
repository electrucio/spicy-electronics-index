"""What a card cannot represent is read from which parameters it lacks. Every card here is invented."""
import json

import pytest

from spicy_electronics_index.bench import record
from spicy_electronics_index.core import config
from spicy_electronics_index.models import cards as C


def read(text):
    return C.read("model", text)


def test_a_bipolar_card_without_collector_capacitance_cannot_give_a_cob():
    card = read(".MODEL QX NPN (IS=1E-14 BF=200 CJE=20P CJC=0 TF=400P VAF=100)")
    assert card["family"] == "gummel-poon"
    assert card["absent"] == ["XTF", "CJC", "TR", "IKF", "ISE", "RB", "RE", "RC", "KF", "XTB"]
    assert card["present"] == ["TF", "CJE", "VAF"]
    assert card["default"] == ["BR", "NF", "NE"]                # left at SPICE's own values: nobody fitted them
    assert C.cannot(card, "cob") == ("CJC",)
    assert C.cannot(card, "cib") is None and C.cannot(card, "ft") is None
    assert C.cannot(card, "hFE") is None                       # nothing is needed for a DC gain


def test_a_zero_is_absent_and_an_expression_is_unknown():
    card = read(".MODEL QX NPN (IS=1E-14 BF=200 TF=0 KF={kf} VAF=0)")
    assert "TF" in card["absent"] and "VAF" in card["absent"]
    assert card["unknown"] == ["KF"]


def test_a_value_that_does_nothing_counts_as_absent_and_says_why():
    card = read(".MODEL QX NPN (IS=1E-14 BF=200 VAF=1E6 RB=1E-6 BR=4 NF=1.02)")
    assert "VAF" in card["absent"] and card["why"]["VAF"].startswith(">= 1e4")
    assert "RB" in card["absent"] and card["why"]["RB"] == "<= 1 mΩ"
    assert card["default"] == ["NE"]                             # BR and NF were set
    assert C.cannot(card, "hoe") == ("VAF",)


def test_extensions_beyond_the_family_are_named():
    card = read(".MODEL QX NPN (IS=1E-14 BF=200 BVCBO=60 RCO=10 VO=5 GAMMA=1E-9 QUASIMOD=1)")
    assert card["extensions"] == ["breakdown", "quasi-saturation"] and card["breakdown"]


def test_mosfet_cards_are_read_by_family():
    v = read(".MODEL MX VDMOS (RG=3 VTO=4 KP=20 CGDMAX=1N CGDMIN=50P CGS=1.2N CJO=800P TT=100N BV=100 RS=5M RD=10M)")
    assert v["family"] == "vdmos" and v["type"] == "VDMOS"
    assert v["absent"] == ["RDS", "KSUBTHRES", "TEXP0", "TRD1", "TCVTH", "KF"] and "geometry" not in v
    assert C.cannot(v, "trr") is None and C.cannot(v, "vbrdss") is None
    l3 = read(".MODEL MY NMOS (LEVEL=3 VTO=2 KP=30U CGSO=1N CGDO=0.3N)")
    assert l3["family"] == "mos-level-3" and l3["geometry"] == "default"
    assert C.cannot(l3, "trr") == () and C.cannot(l3, "coss") is None      # the overlap Cgd alone gives a Coss
    assert C.cannot(read(".MODEL MV NMOS (VTO=2 KP=30U)"), "coss") == ("CBD", "CGDO")
    assert read(".MODEL MZ NMOS (LEVEL=49 TOX=1E-8)")["family"] == "bsim3"
    assert read(".MODEL MW PMOS (VTO=-2 KP=10U)")["family"] == "mos-level-1"
    assert read(".MODEL MQ NMOS (LEVEL=2026 VTO=1)")["family"] == "qspice-2026"
    garbled = read(".MODEL MG NMOS (LEVEL=1.23234e+18 VTO=1)")           # a Micro-Cap binary library converted to text
    assert garbled["family"] == "mos-level-unknown" and "level-garbled" in garbled["dialect"] and "absent" not in garbled


def test_a_subcircuit_header_gives_its_pins_and_a_thermal_node_only_around_a_device():
    sub = C.read("subckt", ".SUBCKT IPB017N10 drain gate source Tj Tcase PARAMS: dVth=0" "\n"
                           "M1 d1 g1 s1 s1 MOSMOD L=1u W=1" "\n" ".ENDS")
    assert sub["pins"] == {"order": ["DRAIN", "GATE", "SOURCE", "TJ", "TCASE"], "mapped": {"d": 0, "g": 1, "s": 2},
                           "thermal": [3, 4]}
    assert sub["thermal_pin"]
    bjt = C.read("subckt", ".SUBCKT BC550X C B E" "\n" "Q1 C B E QMOD" "\n" ".ENDS")
    assert bjt["pins"]["mapped"] == {"b": 1, "c": 0, "e": 2} and "thermal_pin" not in bjt
    numbered = C.read("subckt", ".SUBCKT X 1 2 3" "\n" "Q1 1 2 3 QMOD" "\n" ".ENDS")
    assert numbered["pins"] == {"order": ["1", "2", "3"], "mapped": {}, "thermal": []}
    digital = C.read("subckt", ".SUBCKT GATE IN OUT TC" "\n" "U1 IN OUT TC DIG" "\n" ".ENDS")   # Micro-Cap's digital TC pin
    assert digital["pins"]["thermal"] == [] and "thermal_pin" not in digital


def test_a_subcircuit_with_its_closure_names_the_devices_inside():
    chain = [("model", "mosmod", ".MODEL MOSMOD NMOS (LEVEL=3 VTO=3)"), ("model", "dbody", ".MODEL DBODY D (IS=1E-12)"),
             ("subckt", "x", ".SUBCKT X D G S" "\n" "M1 D G S S MOSMOD" "\n" "D1 S D DBODY" "\n" ".ENDS")]
    out = C.read_chain(chain)
    assert out["family"] == "subckt" and out["inner"] == ["D", "NMOS"] and out["pins"]["mapped"] == {"d": 0, "g": 1, "s": 2}
    assert C.read_chain([("model", "q", ".MODEL Q NPN (BF=100)")])["family"] == "gummel-poon"


def test_no_gummel_poon_card_has_a_breakdown_unless_it_carries_an_extension_for_it():
    assert C.cannot(read(".MODEL QX NPN (IS=1E-14 BF=200)"), "vbrceo") == ()
    assert C.cannot(read(".MODEL QX NPN (IS=1E-14 BF=200 BVCEO=40)"), "vbrceo") is None


def test_a_card_of_another_family_is_named_and_nothing_is_claimed_about_it():
    vbic = read(".MODEL QV NPN (LEVEL=9 IS=1E-16)")
    assert vbic == {"family": "bjt-level-9", "type": "NPN"}
    assert C.cannot(vbic, "cob") is None
    assert read(".MODEL QA AKO:QBASE NPN (BF=300)")["family"] == "ako"
    assert C.read("subckt", ".SUBCKT X 1 2 3\n.ENDS")["family"] == "subckt"


def test_a_jfet_card_lacking_cgd_has_no_reverse_transfer_capacitance():
    card = read(".MODEL JX NJF (VTO=-0.5 BETA=40M LAMBDA=0 CGS=30P IS=1F)")
    assert card["family"] == "jfet" and "CGD" in card["absent"] and "LAMBDA" in card["absent"]
    assert card["present"] == ["CGS"]
    assert C.cannot(card, "crss") == ("CGD",)
    assert C.cannot(card, "ciss") is None                      # CGS alone gives an input capacitance
    assert C.cannot(card, "vbrgss") == ()


def test_a_diode_without_transit_time_has_no_reverse_recovery():
    card = read(".MODEL DX D (IS=2.5N RS=0.5 N=1.8 CJO=4P BV=100)")
    assert C.cannot(card, "trr") == ("TT",) and C.cannot(card, "cd") is None and C.cannot(card, "vbr") is None


@pytest.mark.parametrize("text, flag", [
    (".MODEL QX NPN (IS=1E-14 BF=200 IKF=10A)", "unit-a"),
    (".MODEL QX NPN (IS=1E-14 BF=200 mfg=Acme Vceo=40)", "catalogue-fields"),
    (".MODEL QX NPN (IS=1E-14 BF=200 NK=4.8)", "nk-above-1"),
    (".MODEL QX NPN (IS=1E-14 BF=200 NF=0.85 NR=1.34)", "nr-above-nf"),
    (".MODEL QX PNP (IS=1E-14 BF=200 NR=1.5)", "nr-above-nf"),
    (".MODEL JX NJF (VTO=-1 BETA=1M ISR=1P NR=2)", "jfet-extensions"),
    (".MODEL DX D (Ron=0.1 Roff=1G Vfwd=0.6)", "ltspice-diode"),
])
def test_what_one_simulator_reads_differently_is_noted(text, flag):
    assert flag in read(text).get("dialect", [])


def test_the_ratings_a_card_declares_are_kept_as_numbers():
    card = read('.MODEL QX NPN (IS=1E-14 BF=200 mfg=Philips Vceo=40 Icrating=200m)')
    assert card["ratings"] == {"vceo": 40.0, "icrating": 0.2, "mfg": "PHILIPS"}       # the reader upper-cases the card
    assert "ratings" not in read(".MODEL QX NPN (IS=1E-14 BF=200)")


def test_milliamperes_are_not_mistaken_for_the_ampere_unit():
    assert "dialect" not in read(".MODEL QX NPN (IS=1E-14 BF=200 IKF=100MA)")


def test_a_reverse_emission_coefficient_at_or_below_the_forward_one_is_not_an_artefact():
    assert "dialect" not in read(".MODEL QX NPN (IS=1E-14 BF=200 NF=1.01 NR=1.02)")
    assert "dialect" not in read(".MODEL QX NPN (IS=1E-14 BF=200 NF=1.2 NR=1.0)")


def test_a_step_rewrites_its_own_section_of_the_record_and_keeps_the_others(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PUBLIC_DATA", tmp_path)
    assert record.write_section("bjt", "QX", "claims", {"h1": {"no": ["distortion"]}})
    assert record.write_section("bjt", "QX", "cards", {"h1": {"family": "gummel-poon"}})
    assert not record.write_section("bjt", "QX", "cards", {"h1": {"family": "gummel-poon"}})   # no change
    doc = json.loads(config.verification("bjt", "QX").read_text())
    assert doc["claims"] and doc["cards"] and doc["schema"] == 1
    # a part nothing is known about has no record at all
    record.write_section("bjt", "QX", "claims", {})
    record.write_section("bjt", "QX", "cards", {})
    assert not config.verification("bjt", "QX").exists()
    assert not record.write_section("bjt", "QY", "claims", {})
