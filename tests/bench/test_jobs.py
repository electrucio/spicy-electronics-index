"""How a recipe model becomes the bench's card: an AKO card ("a kind of" another) written out in full."""
from spicy_electronics_index.bench import jobs
from spicy_electronics_index.models import cards as C


def chain(*defs):
    return [("model", name, body) for name, body in defs]


def params(card):
    return C.card_params(card)[2]


def test_an_ako_card_takes_its_base_and_puts_its_own_parameters_on_top():
    c = chain(("mp25a", ".model mp25a pnp (IS=1e-12 BF=30 VAF=50)"),
              ("mp26a", ".model mp26a ako: mp25a pnp (BF=60 mfg=GERMANIUM_USSR)"))
    card = jobs.resolve_ako(c)
    assert card.startswith(".model DUT PNP (")
    assert params(card) == {"IS": "1E-12", "BF": "60", "VAF": "50", "MFG": "GERMANIUM_USSR"}
    got, changes = jobs.prepare(c, "qspice")
    assert changes == ["renamed", "ako-resolved", "catalogue-fields"] and "MFG" not in params(got)


def test_a_chain_of_ako_cards_is_followed_to_the_first_plain_one():
    c = chain(("a", ".model a npn (IS=1e-14 BF=100 TF=1n)"), ("b", ".model b ako:a npn (BF=200)"),
              ("c", ".model c ako:b npn (TF=2n)"))
    assert params(jobs.resolve_ako(c)) == {"IS": "1E-14", "BF": "200", "TF": "2N"}


def test_an_ako_card_without_its_base_or_of_another_type_or_in_a_loop_is_not_measured():
    assert jobs.resolve_ako(chain(("x", ".model x ako:missing npn (BF=10)"))) is None
    assert jobs.prepare(chain(("x", ".model x ako:missing npn (BF=10)")), "qspice") is None
    assert jobs.resolve_ako(chain(("a", ".model a pnp (BF=10)"), ("b", ".model b ako:a npn (BF=20)"))) is None
    assert jobs.resolve_ako(chain(("a", ".model a ako:b npn (BF=1)"), ("b", ".model b ako:a npn (BF=2)"))) is None


def test_a_plain_card_is_only_renamed():
    got, changes = jobs.prepare(chain(("q1", ".model Q1 NPN (IS=1e-14 BF=100)")), "qspice")
    assert got.startswith(".model DUT NPN") and changes == ["renamed"]


def sub(name, text):
    return ("subckt", name, text)


DARLINGTON = """.SUBCKT BC517 1 2 3
* TERMINALS: C B E
Q1 1 2 4 QPWR .1
Q2 1 4 3 QPWR
.MODEL QPWR NPN (IS=1.2P BF=245 CJE=147P)
.ENDS"""


def test_a_darlington_is_traced_to_its_pins_and_renamed_with_everything_inside():
    got, why = jobs.subckt_card([sub("BC517", DARLINGTON)], "qspice")
    assert why == "" and got["pins"] == ["c", "b", "e"] and got["polarity"] == "npn"
    assert ".SUBCKT DUT 1 2 3" in got["card"] and "Q1 1 2 4 QPWR_DUT .1" in got["card"] and ".MODEL QPWR_DUT NPN" in got["card"]


def test_pins_in_another_order_with_lead_inductances_a_tab_and_a_diode():
    text = """.SUBCKT P 1 2 3 4 5 6
LB 1 11 2N
LE 3 33 3N
LC 2 22 0.4N
RTAB 2 4 0
Q1 22 11 33 QP
D1 5 6 DD
.MODEL QP PNP (BF=100)
.MODEL DD D (IS=1E-14)
.ENDS"""
    roles, why = jobs.subckt_roles([sub("P", text)])
    assert roles == ["b", "c", "e", "c", "nc", "nc"], why


def test_the_authors_comments_must_agree_with_the_circuit():
    said = """.SUBCKT T 1 2 3
*        base emitter collector
*node:    1      2        3
Q1 3 1 2 QN
.MODEL QN NPN (BF=100)
.ENDS"""
    assert jobs.subckt_roles([sub("T", said)])[0] == ["b", "e", "c"]
    wrong = said.replace("Q1 3 1 2 QN", "Q1 1 2 3 QN")
    roles, why = jobs.subckt_roles([sub("T", wrong)])
    assert roles is None and "disagree" in why


def test_what_cannot_be_told_for_sure_is_not_measured():
    shorted = ".SUBCKT S 1 2 3\nQ1 1 2 3 QN\nR0 2 3 0\n.MODEL QN NPN (BF=1)\n.ENDS"
    assert jobs.subckt_roles([sub("S", shorted)])[0] is None                      # base and emitter joined
    pair = ".SUBCKT CP 1 2 3\nQ1 4 2 3 QN\nQ2 1 4 3 QP\n.MODEL QN NPN (BF=1)\n.MODEL QP PNP (BF=1)\n.ENDS"
    got, why = jobs.subckt_card([sub("CP", pair)], "qspice")
    assert got is None and "both polarities" in why
    assert jobs.subckt_card([sub("J", ".SUBCKT J 10 20 30\nJ1 10 20 30 JN\n.MODEL JN NJF (BETA=1M)\n.ENDS")], "qspice")[0] is None


def test_a_card_an_element_happens_to_be_named_after_is_not_a_dependency():
    other = sub("Q1", ".SUBCKT Q1 1 2\nR1 1 2 1K\n.ENDS")
    got, _ = jobs.subckt_card([other, sub("BC517", DARLINGTON)], "qspice")
    assert ".SUBCKT DUT" in got["card"] and "R1 1 2 1K" not in got["card"]


def test_a_card_named_like_its_subcircuit_keeps_its_own_name_and_a_missing_end_is_added():
    same = ".SUBCKT BC847BM 1 2 3\nQ1 3 1 2 BC847BM\n.MODEL BC847BM NPN (BF=300)\n.ENDS"
    got, _ = jobs.subckt_card([sub("BC847BM", same)], "qspice")
    assert ".SUBCKT DUT 1 2 3" in got["card"] and "Q1 3 1 2 BC847BM_DUT" in got["card"] and ".MODEL BC847BM_DUT NPN" in got["card"]
    open_ended = ".SUBCKT X 1 2 3\nQ1 1 2 3 QN\n.MODEL QN NPN (BF=100)\n* the vendor's file ends here"
    got, _ = jobs.subckt_card([sub("X", open_ended)], "qspice")
    assert got["card"].rstrip().endswith(".ENDS") and "ends-added" in got["changes"]
    assert "ends-added" not in jobs.subckt_card([sub("BC517", DARLINGTON)], "qspice")[0]["changes"]


def test_a_subcircuit_closed_with_a_librarys_endl_is_closed_with_ends():
    endl = ".SUBCKT S6144 1 2 3\nQ1 2 1 3 QN\n.MODEL QN NPN (BF=335)\n.ENDL S6144\n* ON Semiconductor"
    got, _ = jobs.subckt_card([sub("S6144", endl)], "ngspice")
    assert ".ENDL" not in got["card"].upper() and got["card"].count(".ENDS") == 1 and "ends-added" in got["changes"]
