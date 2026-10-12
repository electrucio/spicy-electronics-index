"""Which of a distributor's products are the part asked about: the filter, with the noise it was written for."""
from spicy_electronics_index.distributors import match


def product(symbol, *numbers, maker="X"):
    return {"symbol": symbol, "manufacturer": {"id": 1, "name": maker}, "manufacturer_symbols": list(numbers)}


def test_the_bare_number_is_exact_and_a_suffix_is_a_variant():
    assert match.keep("TL072", product("TL072CP", "TL072CP")) == "variant"
    assert match.keep("2N2222", product("2N2222-CDI", "2N2222")) == "exact"
    assert match.keep("BD139", product("BD139", "BD139")) == "exact"
    assert match.keep("TL072", product("TL072CD-ST", "TL072CD")) == "variant"
    assert match.keep("BC547", product("BC547BTA", "BC547BTA")) == "variant"
    assert match.keep("BD139", product("BD139-16", "BD139-16")) == "variant"       # a gain group after a separator


def test_a_longer_number_that_happens_to_start_the_same_is_not_the_part():
    assert match.keep("LM833", product("LM8330TME/NOPB", "LM8330TME/NOPB")) is None   # a digit follows
    assert match.keep("LM833", product("LM833N/NOPB", "LM833N/NOPB")) == "variant"


def test_a_number_that_merely_contains_the_part_is_not_the_part():
    assert match.keep("J201", product("MMBFJ201", "MMBFJ201")) is None
    assert match.keep("J201", product("J201189", "NH000GG50V100-1")) is None          # a fuse
    assert match.keep("J201", product("LMJ2018811130DL3T1", "LMJ2018811130DL3T1LFG")) is None


def test_case_and_separators_do_not_matter():
    assert match.keep("tl072cp", product("TL072CP", "TL072CP")) == "exact"
    assert match.keep("2SC1815", product("2SC1815GRTE2FT", "2SC1815-GR(TE2,F,T)")) is None   # brackets and commas are not a suffix
    assert match.keep("2SC1815", product("2SC1815-GR", "2SC1815 GR")) is None        # nor is a space
    assert match.keep("2SC1815", product("2SC1815-GR", "2SC1815-GR")) == "variant"


def test_rest_after_skips_separators_while_matching():
    assert match.rest_after("TL072CD-ST", "TL072") == "CD-ST"
    assert match.rest_after("2N-2222", "2N2222") == ""
    assert match.rest_after("TL071CP", "TL072") is None
    assert match.rest_after("TL07", "TL072") is None
    assert match.rest_after("X", "") is None


def test_collect_keeps_exact_over_variant_for_the_same_symbol_and_drops_noise():
    exact = [product("BD139", "BD139")]
    searched = [product("BD139", "BD139"), product("BD139-16", "BD139-16"), product("BD1396STU", "BD1396STU"),
                product("", "BD139")]
    found = match.collect("BD139", exact, searched)
    assert found["BD139"][1] == "exact"
    assert found["BD139-16"][1] == "variant"
    assert "BD1396STU" not in found and "" not in found


def test_price_breaks_are_written_as_returned():
    prices = {"elements": [{"amount": 1, "price": 0.813, "special": False}, {"amount": 4, "price": 0.708, "special": False}]}
    assert match.price_breaks(prices) == "1:0.813;4:0.708"
    assert match.price_breaks(None) == ""
    assert match.price_breaks({"elements": []}) == ""


def test_rank_puts_exact_numbers_first_then_what_is_in_stock_and_caps_the_list():
    rows = [{"symbol": "C", "match": "variant", "stock": "0"}, {"symbol": "B", "match": "variant", "stock": "12"},
            {"symbol": "A", "match": "exact", "stock": ""}, {"symbol": "D", "match": "variant", "stock": "3"}]
    assert [r["symbol"] for r in match.rank(rows)] == ["A", "B", "D", "C"]
    many = [{"symbol": f"S{i:03d}", "match": "variant", "stock": "1"} for i in range(60)]
    assert len(match.rank(many)) == match.CAP


def test_top_level_names_the_first_level_ancestor_of_every_category():
    cats = [{"id": 1, "parent_id": 1, "name": ""}, {"id": 2, "parent_id": 1, "name": "Semiconductors"},
            {"id": 3, "parent_id": 2, "name": "Op amps"}, {"id": 4, "parent_id": 3, "name": "THT op amps"},
            {"id": 5, "parent_id": 1, "name": "Connectors"}, {"id": 6, "parent_id": 99, "name": "orphan"}]
    top = match.top_level(cats)
    assert top[4] == "Semiconductors" and top[3] == "Semiconductors" and top[2] == "Semiconductors"
    assert top[5] == "Connectors" and top[1] == "" and top[6] == "orphan"


def test_collect_lets_the_caller_have_the_last_word_on_a_category():
    wrench = {"symbol": "KT-6550", "manufacturer_symbols": ["6550"], "category": {"id": 900}}
    assert match.collect("6550", [wrench], [], ok=lambda e: e["category"]["id"] != 900) == {}
    assert "KT-6550" in match.collect("6550", [wrench], [])
