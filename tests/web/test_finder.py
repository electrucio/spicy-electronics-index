"""The Projects tab's data: each unit is a document as the part pages show it, holding its parts."""
from __future__ import annotations

import csv

import pytest

from spicy_electronics_index.core import config
from spicy_electronics_index.web import finder as F
from spicy_electronics_index.web import parts as P

DOC_FIELDS = ("id", "key", "title", "url", "parent", "role", "year", "month", "pages", "sha")


@pytest.fixture
def data(tmp_path, monkeypatch):
    """Five sources: a site with a figure and a sheet another archive also holds, that archive, a magazine
    issue read on two pages running, GitHub designs, and a forum the site does not show."""
    root = tmp_path / "data"
    monkeypatch.setattr(config, "PUBLIC_DATA", root)
    (root / "schematics").mkdir(parents=True)

    def put(path, fields, rows):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(fields)
            w.writerows(rows)

    def source(name, docs, pages, uses, lines=()):
        put(config.schematics_documents(name), DOC_FIELDS, docs)
        put(config.schematics_pages(name), ("doc", "page", "url", "schematic", "parts"), pages)
        put(config.schematics_uses(name), ("part", "doc", "page", "times", "near"), uses)
        put(config.schematics_lines(name), ("doc", "page", "part", "kind", "line"), lines)

    (root / "schematics" / "sources.yaml").write_text(
        "esp: {kind: site, title: ESP, home_url: 'https://e.org/', status: active, era: mixed}\n"
        "el34world: {kind: factory, title: El34World, home_url: 'https://el.example/', status: active, era: vintage}\n"
        "mag: {kind: magazine, title: Mag, home_url: 'https://m.example/', status: active, era: vintage}\n"
        "openhw: {kind: site, title: Open hardware, home_url: 'https://o.example/', status: active, era: modern}\n"
        "forum: {kind: forum, title: A forum, home_url: 'https://f.example/', status: active}\n",
        encoding="utf-8")
    source("esp",
           [["0", "k0", "Fuzz project", "https://esp.example/fuzz.htm", "", "project_page", "", "", "1", "aa"],
            ["1", "k1", "Fuzz figure", "https://esp.example/fuzz.gif", "0", "figure", "", "", "1", "bb"],
            ["2", "k2", "Bassman 5F6-A", "https://esp.example/bassman.pdf", "", "schematic", "1959", "", "1", "deadbeef"],
            ["3", "k3", "Pulled", "https://esp.example/pulled.htm", "", "project_page", "", "", "1", "cc"]],
           [["0", "1", "https://esp.example/fuzz.htm", "0", "1"], ["1", "1", "https://esp.example/fuzz.gif", "1", "2"],
            ["2", "1", "https://esp.example/bassman.pdf#page=1", "1", "2"], ["3", "1", "https://esp.example/pulled.htm", "0", "1"]],
           [["2N3904", "0", "1", "1", ""], ["TL072CP", "1", "1", "2", "IC1"], ["2N5457", "1", "1", "1", "Q2"],
            ["12AX7", "2", "1", "2", "V1"], ["NE555", "3", "1", "1", ""], ["7812", "0", "1", "1", ""]],
           [["0", "1", "2N3904", "mention", "Named as an alternative to the 2N5088."],
            ["1", "1", "2N5457", "project", "The JFET buffer."],
            ["0", "1", "7812", "none", "A mains rating, not a part."]])
    source("el34world",
           [["0", "k9", "Fender Bassman", "https://el.example/bassman.pdf", "", "schematic", "1959", "", "1", "deadbeef"]],
           [["0", "1", "https://el.example/bassman.pdf#page=1", "1", "1"]],
           [["12AX7", "0", "1", "1", ""], ["EL34", "0", "1", "2", ""]])
    source("mag",
           [["0", "km", "Mag 1975-02", "https://m.example/1975-02.pdf", "", "issue", "1975", "2", "3", "ee"]],
           [["0", "1", "https://m.example/1975-02.pdf#page=1", "1", "1"], ["0", "2", "https://m.example/1975-02.pdf#page=2", "1", "1"],
            ["0", "3", "https://m.example/1975-02.pdf#page=3", "0", "1"]],
           [["BC547B", "0", "1", "1", ""], ["TL072", "0", "2", "1", ""], ["2N3055", "0", "3", "1", ""]])
    gh = "https://github.com/someone/synths/blob/HEAD/"
    source("openhw",
           [["0", "g0", "someone/synths: vcf.sch", gh + "vcf.sch", "", "schematic", "", "", "1", "f0"],
            ["1", "g1", "someone/synths: vcf.brd", gh + "vcf.brd", "", "schematic", "", "", "1", "f1"],
            ["2", "g2", "someone/synths: vco.sch", gh + "vco.sch", "", "schematic", "", "", "1", "f2"]],
           [["0", "1", gh + "vcf.sch", "1", "1"], ["1", "1", gh + "vcf.brd", "1", "1"], ["2", "1", gh + "vco.sch", "1", "1"]],
           [["LM13700", "0", "1", "1", ""], ["TL074", "1", "1", "1", ""], ["TL074", "2", "1", "1", ""]])
    source("forum",
           [["0", "kf", "Attachment", "https://f.example/a.pdf", "", "schematic", "", "", "1", "ff"]],
           [["0", "1", "https://f.example/a.pdf", "1", "1"]],
           [["2SK170", "0", "1", "1", ""]])
    (root / "schematics" / "withdrawn.csv").write_text("# withdrawn\nkey,reason\nk3,takedown\n", encoding="utf-8")
    return root


def build(data):
    idx = P.index()
    names = sorted(idx["uses"])
    facets, _ = P.usage_facets(idx)
    units, docs, _ = F.payloads(idx, names, facets, "ss", F.stamp_of(*names))
    return idx, names, facets, units, docs


def parts_of(units, names, field="used"):
    """Each unit's parts by name, decoded from the lengths and steps."""
    out, at = [], 0
    for n in units["units"][field]:
        ids, prev = [], 0
        for d in units["units"][field + "Ids"][at:at + n]:
            prev += d
            ids.append(names[prev])
        out.append(ids)
        at += n
    return out


def find(docs, title):
    return docs["title"].index(title)


def test_a_figure_is_read_with_the_page_that_holds_it(data):
    """The fuzz page names a 2N3904 and holds a figure with the JFET: one project, not two."""
    _, names, _, units, docs = build(data)
    n = find(docs, "Fuzz project")
    assert "Fuzz figure" not in docs["title"]
    assert parts_of(units, names)[n] == ["2N5457", "TL072CP"]
    assert units["units"]["flags"][n] & F.SCHEMATIC        # the figure is a drawing


def test_a_part_only_named_is_kept_apart_from_the_parts_used(data):
    _, names, _, units, docs = build(data)
    n = find(docs, "Fuzz project")
    assert parts_of(units, names, "named")[n] == ["2N3904"]


def test_what_summarise_read_as_not_a_part_and_what_was_withdrawn_are_not_there(data):
    _, names, _, units, docs = build(data)
    assert "7812" not in names and "NE555" not in names and "Pulled" not in docs["title"]


def test_a_source_the_site_does_not_show_is_not_there(data):
    _, names, _, units, docs = build(data)
    assert "2SK170" not in names and "Attachment" not in docs["title"]


def test_one_sheet_in_two_archives_is_one_unit_that_names_the_other(data):
    _, names, _, units, docs = build(data)
    assert docs["title"].count("Bassman 5F6-A") + docs["title"].count("Fender Bassman") == 1
    n = find(docs, "Fender Bassman")              # the copy more of its parts are read on stands for it
    assert parts_of(units, names)[n] == ["12AX7", "EL34"]
    assert docs["also"][str(n)] == ["esp"] and docs["aka"][str(n)] == ["Bassman 5F6-A"]
    assert docs["url"][n] == "https://el.example/bassman.pdf"


def test_a_magazine_issue_is_a_unit_per_page_and_says_which_pages_run_on(data):
    _, names, facets, units, docs = build(data)
    pages = [i for i, t in enumerate(docs["title"]) if t == "Mag 1975-02"]
    assert [units["units"]["page"][i] for i in pages] == [1, 2, 3]
    assert [parts_of(units, names)[i] for i in pages] == [["BC547B"], ["TL072"], ["2N3055"]]
    assert [bool(units["units"]["flags"][i] & F.AFTER) for i in pages] == [False, True, True]
    assert docs["url"][pages[1]] == "https://m.example/1975-02.pdf#page=2"
    assert facets[units["units"]["facet"][pages[0]]]["key"] == "mag/1970s"
    assert units["units"]["year"][pages[0]] == 1975 and docs["date"][pages[0]] == "1975-02"


def test_a_board_and_its_schematic_are_one_design_and_the_folder_is_not(data):
    """vcf.sch and vcf.brd are one design; vco.sch beside them is another, so each says the folder holds two."""
    _, names, _, units, docs = build(data)
    vcf, vco = find(docs, "someone/synths: vcf.sch"), find(docs, "someone/synths: vco.sch")
    assert "someone/synths: vcf.brd" not in docs["title"]
    assert parts_of(units, names)[vcf] == ["LM13700", "TL074"] and parts_of(units, names)[vco] == ["TL074"]
    assert docs["sheets"] == {str(vcf): 2, str(vco): 2}


def test_parts_are_rows_of_the_index_and_both_files_carry_its_stamps(data):
    _, names, facets, units, docs = build(data)
    assert units["partsStamp"] == F.stamp_of(*names) and units["sourcesStamp"] == "ss"
    assert units["findStamp"] == docs["findStamp"]
    assert len(units["units"]["role"]) == len(docs["title"])
    assert sum(f["n"] for f in units["facets"]) >= len(docs["title"])
    assert units["eras"][P.sources().index("openhw")] == "modern"


def test_what_i_have_can_be_matched_through_the_type_and_the_makers_names(data):
    """A TL072CP is a TL072 in a DIP; a bare 7812 is anybody's 7812 (here read as not a part, so absent)."""
    _, names, _, units, _ = build(data)
    assert units["up"]["TL072CP"] == ["TL072"] and units["up"]["BC547B"] == ["BC547"]
    assert "TL072" not in units["up"]


def test_the_units_keep_their_order_from_one_build_to_the_next(data):
    first = build(data)[3]
    assert build(data)[3] == first


def test_the_words_of_the_summaries_are_found_on_their_units_and_the_commonest_are_left_out(data, monkeypatch):
    """The JFET buffer line is on the fuzz project (its figure); a word on every unit finds nothing."""
    monkeypatch.setattr(F, "COMMON", 0.5)
    idx = P.index()
    names = sorted(idx["uses"])
    units, docs, shards = F.payloads(idx, names, P.usage_facets(idx)[0], "ss", F.stamp_of(*names))
    fuzz = docs["title"].index("Fuzz project")
    assert "jf" in units["shards"] and shards["jf"]["words"]["jfet"] == [fuzz]
    assert shards["jf"]["findStamp"] == units["findStamp"]
    assert "buffer" in shards["bu"]["words"] and "alternative" in shards["al"]["words"]
    assert units["common"] == []


def test_a_split_too_big_is_split_again_by_three_letters(data, monkeypatch):
    monkeypatch.setattr(F, "SHARD_BYTES", 1)
    idx = P.index()
    names = sorted(idx["uses"])
    units, _, shards = F.payloads(idx, names, P.usage_facets(idx)[0], "ss", F.stamp_of(*names))
    assert "jfe" in units["shards"] and "jf" not in units["shards"] and set(shards) == set(units["shards"])


def test_the_relations_travel_by_name_with_what_each_is_worth(data):
    (data / "parts").mkdir(exist_ok=True)
    (data / "parts" / "relations.csv").write_text(
        "part,relation,other,refs,note,status\n"
        "LSK170,replacement_for,2SK170,S32,\"Linear Systems: a direct replacement\",draft\n", encoding="utf-8")
    units = build(data)[3]
    assert units["relations"] == [["LSK170", "replacement_for", "2SK170", ["S32"], "Linear Systems: a direct replacement", "draft"]]
    assert units["coverage"]["replacement_for"] == ["out", "substitute"]
