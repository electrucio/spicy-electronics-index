"""What is kept of the research datasets, now that they are deleted: the published table and the list."""
from __future__ import annotations

import csv

import pytest
import yaml

from spicy_electronics_index.core.config import dataset_table, datasets_registry

PUBLISHED = dataset_table("part_repos")


@pytest.mark.skipif(not PUBLISHED.is_file(), reason="datasets not distilled yet")
def test_the_table_publishes_a_link_and_nothing_copied_from_the_project():
    """The repository name is the tail of the link, and its blurb is third-party prose — one of them
    named a student. Part, how many sheets, and where to look."""
    with open(PUBLISHED, encoding="utf-8") as fh:
        fields = next(csv.reader(fh))
    assert fields == ["part", "sheets", "url"]


@pytest.mark.skipif(not PUBLISHED.is_file(), reason="datasets not distilled yet")
def test_every_part_in_the_published_table_is_one_the_index_knows():
    """A row for a part with no page would point nowhere."""
    from spicy_electronics_index.core.parts.extractor import KNOWN
    known = {p for p, _ in KNOWN.values()}
    with open(PUBLISHED, encoding="utf-8") as fh:
        parts = {r["part"] for r in csv.DictReader(fh)}
    assert not (parts - known)


@pytest.mark.skipif(not datasets_registry().is_file(), reason="datasets not distilled yet")
def test_the_published_registry_names_a_source_and_a_licence_for_each():
    doc = yaml.safe_load(datasets_registry().read_text(encoding="utf-8"))
    assert doc["datasets"] and doc["not_available"]
    for e in doc["datasets"]:
        assert e["id"] and e["licence"] and e["source"], e
