"""The decks of the kinds beyond bipolars (JFET, MOSFET, op-amp): each covers its catalogue, writes the same
text every time, has a P-channel twin line for line, and is quoted verbatim by the catalogue."""
import os
import sys

import pytest

from spicy_electronics_index.bench import catalogue as C
from spicy_electronics_index.core import config

os.environ.setdefault("SIM_ENGINE", "ngspice")
sys.path.insert(0, str(config.sim_bench().parent))
from bench import character as incar  # noqa: E402

CAT = {m["id"]: m for m in C.measurements()}
# the derived points a deck may ask for, as a real model gives them: the catalogue's quoted lines are written
# from these (a JFET with VGS(off) = −1 V, IDSS = 3 mA, biased at the ladder currents it reaches)
DERIVED = {
    "jfet": {"_vgs_off": -1.0, "_idss": 3e-3, "_vgs_third": -0.42, "_id_third": 1e-3, "_rs_stage": 420.0, "_rd_stage": 8580.0,
             "_vgs@100µA": -1.5, "_vgs@1mA": -0.9, "_vgs@3mA": 0.0, "_cgs@10V": 3e-12, "_cgd@10V": 1.5e-12,
             "thd_gain_cs": 4.0, "thd_gain_sf": 0.9},
    "mosfet": {"_vth": 2.0, "_vgs@1mA": 2.0, "_vgs@3mA": 2.1, "_vgs@10mA": 2.2, "_vgs@30mA": 2.4, "_vgs@100mA": 2.7, "_vgs@300mA": 3.2,
               "_vgs@1A": 4.0, "_vgs@3A": 5.5, "thd_gain_cs": 3.0, "thd_gain_sf": 0.95},
    "opamp": {"_vos": 1e-5, "_iq": 1.4e-3},
}
# the catalogue's kind of each plan the image runs (an op-amp's group is "amplifier", its catalogue kind "opamp")
KIND_OF_PLAN = {"jfet": "jfet", "mosfet": "mosfet", "amplifier": "opamp"}
PLANS = [(p, k) for p, k in KIND_OF_PLAN.items() if p in incar.PLANS]


@pytest.mark.parametrize("plan,kind", PLANS)
def test_every_measurement_has_a_deck_or_is_derived(plan, kind):
    served = {i for d in incar.PLANS[plan].plan(CAT, "qspice") for i in d.ids}
    derived = {i for i in C.ids(kind) if CAT[i]["analysis"] == "derived"}
    assert set(C.ids(kind)) - derived == served
    assert f"{kind}-agreement" in derived


@pytest.mark.parametrize("plan,kind", PLANS)
def test_the_same_job_gives_the_same_text_and_a_p_channel_twin_line_for_line(plan, kind):
    der = DERIVED[kind]
    for deck in incar.PLANS[plan].plan(CAT, "qspice"):
        if not deck.ready(der):
            continue
        a = incar.deck_text(deck, [("DUT", 1, "", der)], "model.lib", "qspice")
        b = incar.deck_text(deck, [("DUT", 1, "", der)], "model.lib", "qspice")
        p = incar.deck_text(deck, [("DUT", -1, "", der)], "model.lib", "qspice")
        assert a == b and a.startswith(f"* character {deck.name}\n") and a.endswith(".end\n")
        assert len(p.splitlines()) == len(a.splitlines()), deck.name
        for line in a.splitlines():
            if line.startswith(".tran"):
                assert float(line.split()[1]) > 0, line


@pytest.mark.parametrize("plan,kind", PLANS)
def test_a_packed_deck_renames_the_copies_and_keeps_one_analysis(plan, kind):
    der = DERIVED[kind]
    for deck in incar.PLANS[plan].plan(CAT, "qspice"):
        if not deck.pack or not deck.ready(der):
            continue
        text = incar.deck_text(deck, [("DUT0", 1, "_0", der), ("DUT1", 1, "_1", der)], "models.lib", "qspice")
        analyses = [ln for ln in text.splitlines() if ln.split()[:1] and ln.split()[0] in (".dc", ".ac", ".tran", ".noise", ".op")]
        assert len(analyses) == 1, deck.name
        assert " DUT0" in text and " DUT1" in text and text.count(".save") == 2, deck.name


@pytest.mark.parametrize("plan,kind", PLANS)
def test_the_catalogue_quotes_its_decks_verbatim(plan, kind):
    """Every directive line the method page shows is a line of the QSPICE deck of that measurement."""
    der = DERIVED[kind]
    texts: dict[str, list[str]] = {}
    for deck in incar.PLANS[plan].plan(CAT, "qspice"):
        if not deck.ready(der):
            continue
        text = incar.deck_text(deck, [("DUT", 1, "", der)], "model.lib", "qspice")
        for mid in deck.ids:
            texts.setdefault(mid, []).append(text)
    quoted = 0
    for mid in C.ids(kind):
        for line in CAT[mid].get("directives") or []:
            if line.startswith("*"):
                continue
            assert any(f"\n{line}\n" in t for t in texts.get(mid, [])), f"{mid}: {line!r} is not in its deck"
            quoted += 1
    assert quoted > 30


@pytest.mark.parametrize("plan,kind", PLANS)
def test_output_keys_of_the_decks_follow_the_catalogue_spelling(plan, kind):
    """A deck's keys with a condition spell it as the catalogue does (1mA, 10V), never a raw number."""
    for mid in C.ids(kind):
        for o in CAT[mid]["outputs"]:
            key = o["key"]
            assert "{" not in key.split("@")[0], key
