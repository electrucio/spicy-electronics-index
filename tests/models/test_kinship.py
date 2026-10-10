"""How models are related by their cards: fingerprints and counts, never values. Every card is invented."""
from spicy_electronics_index.models import cards as C
from spicy_electronics_index.models import kinship as K


def params(text):
    return C.card_params(text)[2]


A = params(".MODEL QA NPN (IS=1E-14 BF=200 CJE=20P CJC=4P TF=400P TR=40N VJC=0.75 MJC=0.33 VAF=100)")
B = params(".MODEL QB NPN (IS=2E-14 BF=150 CJE=20P CJC=4P TF=400P TR=40N VJC=0.75 MJC=0.33 VAF=80)")   # same names, other fit
A2 = params(".MODEL QA2 NPN (IS=1E-14 BF=220 CJE=20P CJC=4P TF=400P TR=40N VJC=0.75 MJC=0.33 VAF=100)")  # A with BF changed
D = params(".MODEL QD NPN (IS=1E-14 BF=200 CJE=20P CJC=4P TF=400P TR=40N VJC=0.75 MJC=0.33 VAF=100 mfg=Acme)")
E = params(".MODEL QE PNP (IS=5E-15 BF=90 CJE=12P CJC=6P TF=600P VAF=60)")


def test_same_names_other_values_is_the_same_physics_and_a_changed_value_is_a_derived_card():
    kin = K.compute({"bjt/QX": {"a": A, "b": B, "a2": A2}})["bjt/QX"]
    assert kin["a"]["params"] == kin["b"]["params"] == kin["a2"]["params"]
    assert kin["a"]["same_parameters"] == ["a2", "b"]
    assert kin["a"]["derived_from_or_to"] == ["a2"] and kin["a2"]["derived_from_or_to"] == ["a"]
    assert "derived_from_or_to" not in kin["b"]                  # three values differ: a new fit, not a copy


def test_catalogue_fields_do_not_make_two_cards_differ():
    kin = K.compute({"bjt/QX": {"a": A, "d": D}})["bjt/QX"]
    assert kin["a"]["params"] == kin["d"]["params"] and "derived_from_or_to" not in kin["a"]


def test_a_dynamic_block_shared_with_another_part_is_a_template_and_names_no_value():
    kin = K.compute({"bjt/QX": {"a": A}, "bjt/QY": {"b": B}, "bjt/QZ": {"e": E}})
    assert kin["bjt/QX"]["a"]["template"] == kin["bjt/QY"]["b"]["template"]
    assert kin["bjt/QX"]["a"]["template_parts"] == 1
    assert "template" not in kin["bjt/QZ"]["e"]
    assert "20P" not in str(kin) and "400P" not in str(kin) and "4E-12" not in str(kin).upper()


def test_a_template_is_counted_across_parts_not_within_one():
    kin = K.compute({"bjt/QX": {"a": A, "b": B}})
    assert "template" not in kin["bjt/QX"]["a"]
