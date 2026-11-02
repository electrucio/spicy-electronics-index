"""Numbers the OCR cut short: measured on an export, committed, never re-measured."""
from spicy_electronics_index.core.parts import truncated as T

SCHEME = {"2N390", "2N3904", "2N3906", "1N34", "1N340", "2N107", "2N1070", "BC54", "BC547"}


def measure(documents, listed=()):
    return {r["name"]: r for r in T.measure(documents, lambda p: p in listed, lambda p: p in SCHEME, today="2026-11-02")}


def test_a_number_twenty_times_rarer_than_the_ones_it_starts_is_cut_short():
    rows = measure({"2N390": 28, "2N3904": 2727, "2N3906": 1560})
    assert rows == {"2N390": {"name": "2N390", "documents": 28, "longer": "2N3904 2N3906",
                              "longer_documents": 4287, "measured": "2026-11-02"}}


def test_what_a_list_holds_or_is_not_rare_enough_stays():
    assert measure({"1N34": 416, "1N340": 3}, listed={"1N34"}) == {}
    assert measure({"2N107": 188, "2N1070": 400}) == {}                 # only twice as rare


def test_only_a_digit_makes_a_number_longer_and_only_a_strict_scheme_counts():
    assert measure({"2N390": 1, "2N390A": 500}) == {}                   # a grade is the same number
    assert measure({"TL07": 1, "TL072": 500}) == {}                      # not a strict scheme


def test_a_listed_number_stays_listed_when_the_next_export_no_longer_has_it():
    old = {"2N390": {"name": "2N390", "documents": 28, "longer": "2N3904", "longer_documents": 4509,
                     "measured": "2026-11-02"}}
    new = list(measure({"BC54": 2, "BC547": 900}).values())
    assert [r["name"] for r in T.merged(old, new)] == ["2N390", "BC54"]
    assert T.merged(old, [{**old["2N390"], "documents": 1}])[0]["documents"] == 28


def test_a_curated_model_or_a_sourced_wanted_list_vouches_for_a_short_number():
    """1N91 has a curated model and a repair shop's stock list sells 2N555: real, however rare."""
    held = T.vouched()
    assert {"1N91", "2N555"} <= held and "2N390" not in held
