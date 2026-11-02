"""The number printed on a scanned page: read off archive.org's page numbers, never guessed across a break."""
import csv

import pytest

from spicy_electronics_index.core import config
from spicy_electronics_index.schematics import printed as P

AOE = "https://archive.org/details/the-art-of-electronics-3rd-ed-2015_202510"


def leaf(n, number=""):
    return {"leafNum": n, "pageNumber": number}


def test_a_leaf_takes_the_number_read_on_it():
    got = P.numbered([leaf(0), leaf(1, "xii"), leaf(655, "623"), leaf(656, "624")])
    assert got == {1: ("xii", "read"), 655: ("623", "read"), 656: ("624", "read")}


def test_an_unread_leaf_takes_its_number_only_inside_an_unbroken_run():
    got = P.numbered([leaf(10, "8"), leaf(11), leaf(12, "10"),        # 9 between 8 and 10: the run holds
                      leaf(27, "29"), leaf(28), leaf(29), leaf(30, "34")])   # two leaves, four numbers: pages missing
    assert got[11] == ("9", "between")
    assert 28 not in got and 29 not in got


@pytest.fixture
def books(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PUBLIC_DATA", tmp_path / "data")

    def put(path, fields, rows):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(fields)
            w.writerows(rows)

    put(config.schematics_documents("books"), ("id", "key", "title", "url", "parent", "role", "year", "month", "pages", "sha"),
        [["g", f"{AOE}#horowitz-hill", "The Art of Electronics", AOE, "", "book", "", "", "1225", ""],
         ["s", "https://archive.org/details/opamps#mancini", "Op Amps for Everyone", "https://archive.org/details/opamps", "", "book", "", "", "440", ""],
         ["5", "https://example.org/winder.pdf#winder", "Filter Design", "https://example.org/winder.pdf", "", "book", "", "", "458", ""]])
    put(config.schematics_pages("books"), ("doc", "page", "url", "schematic", "parts"),
        [["g", "656", f"{AOE}/page/n655/mode/2up", "0", "4"],
         ["g", "657", f"{AOE}/page/n656/mode/2up", "0", "1"],
         ["s", "33", "https://archive.org/details/opamps?q=LM358", "0", "1"],      # a search names no leaf
         ["5", "12", "https://example.org/winder.pdf#page=12", "0", "1"]])          # not on archive.org
    asked = []

    def ask(item):
        asked.append(item)
        return f"https://archive.org/download/{item}/x_page_numbers.json", {"pages": [leaf(655, "623"), leaf(656)]}

    monkeypatch.setattr(P, "ask", ask)
    return asked


def test_only_leaf_links_on_archive_org_are_numbered_and_each_page_gets_a_row(books):
    assert P.leaves("books") == {f"{AOE}#horowitz-hill": {"656": 655, "657": 656}}
    P.run("books")
    rows = {r["page"]: r for r in P.load()}
    assert (rows["656"]["printed"], rows["656"]["how"]) == ("623", "read")
    assert (rows["657"]["printed"], rows["657"]["how"]) == ("", "unread")     # asked, and nothing read: recorded


def test_a_document_already_numbered_is_not_asked_again(books):
    P.run("books")
    P.run("books")
    assert books == ["the-art-of-electronics-3rd-ed-2015_202510"]
