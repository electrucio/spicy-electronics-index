"""The file a part is served from: one per part, even on a disk that ignores case."""
import json
from pathlib import Path

import pytest

from spicy_electronics_index.core.partfile import part_file

FIXTURE = json.loads((Path(__file__).parents[1] / "fixtures" / "part_files.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", FIXTURE["cases"], ids=lambda c: c["part"])
def test_the_file_is_the_fixtures(case):
    assert part_file(case["part"]) == case["file"]


def test_names_that_differ_only_in_case_never_share_a_file_on_a_case_insensitive_disk():
    names = ["CORE", "Core", "core", "cORE", "DPDT", "dpdt", "uA723", "UA723"]
    files = {part_file(n).casefold() for n in names}
    assert len(files) == len(names)


def test_a_part_in_capitals_keeps_its_own_name():
    assert part_file("2N3904") == "2N3904" and part_file("APT1608LSECK/J3-PRV") == "APT1608LSECK/J3-PRV"


def test_a_name_holding_the_mark_is_refused():
    with pytest.raises(ValueError):
        part_file("A~1")
