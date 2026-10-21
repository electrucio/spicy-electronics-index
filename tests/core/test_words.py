"""The words the Projects tab looks up, cut the same way here and in the browser."""
import json
from pathlib import Path

from spicy_electronics_index.core.words import shard_of, words

CASES = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "words_cases.json").read_text(encoding="utf-8"))


def test_the_shared_cases_cut_into_the_same_words_as_in_the_browser():
    for case in CASES:
        assert words(case["text"]) == case["words"], case["text"]


def test_a_word_is_found_in_the_split_of_its_first_two_letters():
    assert shard_of("wah") == "wa" and shard_of("5f6a") == "5f"
