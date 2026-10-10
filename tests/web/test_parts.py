

def test_a_list_spelling_a_part_in_other_capitals_lands_on_the_index_page():
    """uA723 from the dictionary's spelling goes on UA723's page, not on a second, nearly empty one."""
    from spicy_electronics_index.web.parts import fold_case
    index = {"UA723": [], "TL072": []}
    got = fold_case({"uA723": ["repo-a"], "UA723": ["repo-b"], "Core": ["x"], "TL072": ["y"]}, index)
    assert got == {"UA723": ["repo-a", "repo-b"], "Core": ["x"], "TL072": ["y"]} or \
        got == {"UA723": ["repo-b", "repo-a"], "Core": ["x"], "TL072": ["y"]}
