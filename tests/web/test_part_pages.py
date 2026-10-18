"""What one part's page carries, and what it leaves out."""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from spicy_electronics_index.core import config
from spicy_electronics_index.web import parts as P

SOURCES = ["esp", "el34world"]
REPO = Path(__file__).resolve().parents[2]


@pytest.fixture
def data(tmp_path, monkeypatch):
    """A tiny exported index: one sheet published twice, and one part with a model."""
    root = tmp_path / "data"
    monkeypatch.setattr(config, "PUBLIC_DATA", root)
    (root / "schematics").mkdir(parents=True)

    def put(path, fields, rows):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(fields)
            w.writerows(rows)

    put(config.schematics_documents("esp"),
        ("id", "key", "title", "url", "parent", "role", "year", "month", "pages", "sha"),
        [["0", "k1", "Bassman 5F6-A", "https://esp.example/bassman.pdf", "", "schematic", "1959", "", "1", "deadbeef"],
         ["1", "k2", "Opamp Bypassing", "https://esp.example/p00.htm", "", "project_page", "", "", "1", "cafe"]])
    put(config.schematics_pages("esp"), ("doc", "page", "url", "schematic", "parts"),
        [["0", "1", "https://esp.example/bassman.pdf#page=1&zoom=200,10,20&h=792", "1", "9"],
         ["1", "1", "https://esp.example/p00.htm", "0", "2"]])
    put(config.schematics_uses("esp"), ("part", "doc", "page", "times", "near"),
        [["12AX7", "0", "1", "2", "V1 V2"], ["TL072", "1", "1", "1", "IC1"]])
    put(config.schematics_lines("esp"), ("doc", "page", "part", "kind", "line"),
        [["0", "1", "12AX7", "project", "First and second preamp stages V1 and V2 of the Bassman 5F6-A."]])

    (root / "schematics" / "sources.yaml").write_text(
        "esp: {kind: site, title: ESP, home_url: 'https://e.org/', status: active}\n"
        "el34world: {kind: factory, title: El34World, home_url: 'https://el34.example/', status: active}\n",
        encoding="utf-8")
    put(config.schematics_documents("el34world"),
        ("id", "key", "title", "url", "parent", "role", "year", "month", "pages", "sha"),
        [["0", "k3", "Fender Bassman", "https://el34.example/bassman.pdf", "", "schematic", "1959", "", "1", "deadbeef"]])
    put(config.schematics_pages("el34world"), ("doc", "page", "url", "schematic", "parts"),
        [["0", "1", "https://el34.example/bassman.pdf#page=1", "1", "9"]])
    put(config.schematics_uses("el34world"), ("part", "doc", "page", "times", "near"),
        [["12AX7", "0", "1", "1", ""]])

    put(config.schematics_parts(), ("part", "documents", "pages", "uses", "sources"),
        [["12AX7", "2", "2", "2", "el34world esp"], ["TL072", "1", "1", "1", "esp"]])

    recipe = config.model_part("opamp", "TL072")
    recipe.parent.mkdir(parents=True, exist_ok=True)
    recipe.write_text(
        "part: TL072\nkind: opamp\n"
        "models:\n"
        "- source: ti\n  name: TL072\n  def: subckt\n  verbatim: true\n"
        "  get: {url: 'https://ti.example/tl072.lib', sha256: aa, lines: {TL072: [1, 9]}}\n"
        "- source: ltwiki\n  name: TL082\n  def: subckt\n  verbatim: true\n"
        "  note: 'STAND-IN: model of TL082, not of TL072; the equivalence is declared in data/models/wanted.yaml'\n"
        "  get: {url: 'https://lt.example/tl082.lib'}\n"
        "- source: kicad\n  name: TL07x\n  def: subckt\n  verbatim: true\n"
        "  note: 'found under the alias TL07x; pins from names'\n"
        "  get: {url: 'https://k.example/tl07x.lib'}\n",
        encoding="utf-8")
    return root


def test_one_sheet_published_twice_is_one_result_that_names_the_other(data):
    idx = P.index()
    page = P.part_payload("12AX7", idx, None)
    assert len(page["docs"]) == 1
    assert page["docs"][0]["also"] == ["el34world"]
    assert page["n"]["copies"] == 1


def test_a_sheet_filed_under_two_names_keeps_both_on_the_page(data):
    """audiocircuit files the Denon "AVR-1803/883" manual twice, byte for byte; whichever copy is kept,
    the name the other carries must still be on the page for someone looking for it."""
    page = P.part_payload("12AX7", P.index(), None)
    kept = page["docs"][0]
    assert kept["t"] == "Bassman 5F6-A" and kept["aka"] == ["Fender Bassman"]


def test_a_page_link_travels_with_its_deep_link(data):
    idx = P.index()
    page = P.part_payload("12AX7", idx, None)
    assert page["docs"][0]["p"][0][1].endswith("&zoom=200,10,20&h=792")


def test_the_recipe_is_trimmed_to_what_the_page_shows_and_carries_no_model_text(data):
    idx = P.index()
    recipes, _ = P.model_recipes()
    page = P.part_payload("TL072", idx, recipes["TL072"])
    m = page["models"]["models"][0]
    assert m["source"] == "ti"
    assert m["get"]["url"] == "https://ti.example/tl072.lib"
    assert "lines" not in m["get"] and "sha256" not in m["get"]   # the page does not need them
    assert "score" not in m and "rows" not in m and "preferred" not in page["models"]


def test_a_makers_catalogue_category_gives_a_kind_when_nothing_nearer_does():
    """Toshiba files the RN2903 under bipolar transistors with bias resistors: a BJT, where the number's
    shape says nothing. Words the menu has no device for give nothing rather than a guess."""
    row = lambda category, title="": [  # noqa: E731
        "toshiba_parametric", "toshiba", category, "ACTIVE", title, "", "https://t.example/x", "", "2026-10-12", ""]
    assert P.catalogue_kind([row("Bipolar Transistors > Transistors with Bias Resistors (BRT, Digital Transistors)")]) == "bjt"
    assert P.catalogue_kind([row("Isolators/Solid State Relays > Photorelays (MOSFET Output)")]) == "opto"
    assert P.catalogue_kind([row("Small-signal Product > Zener Diode")]) == "zener"
    assert P.catalogue_kind([row("transistors")]) == "transistor"
    assert P.catalogue_kind([row("Precision ADCs"), row("Load switches")]) == ""
    assert P.catalogue_kind([row("N-Channel", "IRF540 power MOSFET")]) == "mosfet"
    idx = {"catalogue_kind": {"RN2903": "bjt"}, "dictionary": {}}
    assert P.part_kind("RN2903", {}, {}, idx["catalogue_kind"]) == "bjt"
    assert P.kind_of("RN2903", None, idx) == "bjt"
    assert P.kind_of("RN2903", None, {"dictionary": {"RN2903": "mosfet"}, "catalogue_kind": {"RN2903": "bjt"}}) == "mosfet"


def test_a_part_page_says_its_kind_and_the_devices_it_answers_to(data):
    """The sellers section picks the sellers for the part's kind from the page, not from the menu's words."""
    idx = P.index()
    recipes, _ = P.model_recipes()
    page = P.part_payload("TL072", idx, recipes["TL072"])
    assert page["kind"] == "opamp" and page["devices"] == ["opamp"]
    page = P.part_payload("XQ9999", idx, None)   # a part nothing knows: the keys are absent, not empty
    assert "kind" not in page and "devices" not in page


def test_a_stand_in_or_an_alias_is_said_beside_the_model():
    """A stand-in is a model of another part: the page must say so without the reader opening anything."""
    stand_in, alias = P.trim_models({"models": [
        {"source": "a", "name": "PC817", "def": "subckt", "get": {},
         "note": "STAND-IN: model of PC817, not of EL357N; equivalence declared in catalog/wanted.yaml"},
        {"source": "b", "name": "OPA161x", "def": "subckt", "get": {},
         "note": "found under the alias OPA161x; pins from names"},
    ]})["models"]
    assert stand_in["standin"] == "PC817" and "alias" not in stand_in
    assert alias["alias"] == "OPA161x" and "standin" not in alias


def test_a_model_only_a_simulator_ships_is_got_from_its_published_copy():
    qs, lt = P.trim_models({"models": [
        {"source": "qspice", "name": "2N3904", "def": "model", "get": {"installed_with": "QSPICE"},
         "copies": [{"source": "x", "name": "2N3904", "get": {"installed_with": "LTspice"}},
                    {"source": "bordodynov-qspice", "name": "2N3904", "get": {"url": "https://disk.example/q", "member": "QSPICE/bjt.txt"}}]},
        {"source": "ltspice-native", "name": "2N3906", "def": "model", "get": {"installed_with": "LTspice"}},
    ]})["models"]
    assert qs["get"] == {"installed_with": "QSPICE", "url": "https://disk.example/q", "via": "bordodynov-qspice",
                         "member": "QSPICE/bjt.txt"}
    assert lt["get"] == {"installed_with": "LTspice"}           # no published copy: it says what ships it


def test_the_symbol_published_with_a_model_reaches_the_page_as_a_link():
    m, = P.trim_models({"models": [{"source": "bordodynov", "name": "SPEAKER", "def": "subckt",
        "get": {"url": "http://b.example/lib.zip", "member": "sub/speaker.lib", "sha256": "x",
                "symbol": {"url": "http://b.example/lib.zip", "member": "sym/speaker.asy", "sha256": "y"}}}]})["models"]
    assert m["get"]["symbol"] == {"url": "http://b.example/lib.zip", "member": "sym/speaker.asy", "sha256": "y"}


def test_the_source_names_are_not_repeated_in_every_part_file(data):
    """They are the same in all of them; repeating them cost 90 MB across 15,558 files."""
    page = P.part_payload("12AX7", P.index(), None)
    assert "sources" not in page


def test_the_search_index_holds_every_part_from_either_side(data):
    idx = P.index()
    recipes, _ = P.model_recipes()
    rows, menu = P.search_index(idx, recipes)
    assert [r[0] for r in rows] == ["12AX7", "TL072"]
    assert dict((r[0], r[3]) for r in rows)["TL072"] == 3     # three model candidates
    at = {d["key"]: i for i, d in enumerate(menu)}
    assert dict((r[0], r[4]) for r in rows)["TL072"] & (1 << at["opamp"])   # from its recipe
    assert dict((r[0], r[4]) for r in rows)["12AX7"] & (1 << at["tube"])    # from the dictionary


def test_a_part_page_says_how_many_documents_and_how_many_copies_were_folded(data):
    page = P.part_payload("12AX7", P.index(), None)
    assert page["n"] == {"documents": 1, "shown": 1, "copies": 1}


def test_a_part_carries_the_open_source_projects_that_place_it(data, monkeypatch):
    """The third answer to "where is it used", and the only one pointing at a live board."""
    table = config.dataset_table("part_repos")
    table.parent.mkdir(parents=True, exist_ok=True)
    table.write_text("part,sheets,url\n"
                     "12AX7,3,https://github.com/a/one\n"
                     "12AX7,1,https://github.com/b/two\n", encoding="utf-8")
    page = P.part_payload("12AX7", P.index(), None)
    assert page["n"]["repos"] == 2
    # with no attention read yet, the one that places it on most sheets leads
    assert page["repos"][0][:2] == ["a/one", 3]


def test_the_index_says_what_kind_of_thing_each_source_is(data):
    """A factory sheet, a magazine page and a GitHub board are three different answers, so the page
    groups them apart — which it can only do if it knows which is which."""
    idx = P.index()
    assert idx["kinds"]["esp"] == "site"
    assert idx["kinds"]["el34world"] == "factory"


def test_a_page_link_is_stored_as_what_to_add_to_its_document(data):
    """All 94,170 of them are a suffix of the document's URL; writing them whole was three quarters of
    the URL text on a part's page, and that was the reason to cut documents that should not be cut."""
    page = P.part_payload("12AX7", P.index(), None)
    link = page["docs"][0]["p"][0][1]
    assert link.startswith("#page=")
    assert page["docs"][0]["u"] + link == \
        "https://esp.example/bassman.pdf#page=1&zoom=200,10,20&h=792"


def test_nothing_is_cut_from_a_part(data):
    """The 12AX7 is in 1,817 documents across 33 sources. Keeping the top two hundred meant 147 factory
    sheets crowding out Wireless World and Elektor, which is the part of the answer people want."""
    idx = P.index()
    for part in ("12AX7", "TL072"):
        page = P.part_payload(part, idx, None)
        assert page["n"]["shown"] == page["n"]["documents"]
        assert all("more" not in d for d in page["docs"])


def test_a_part_filed_under_two_kinds_is_reported_rather_than_hidden(data):
    """Five are, each curated once as silicon and once as germanium. Under the Pro-Electron convention
    the first letter settles it — B is silicon — but until the curation is merged, keeping one quietly
    is how the wrong one won: `bjt-ge` sorts after `bjt`."""
    other = config.model_part("bjt-ge", "TL072")
    other.parent.mkdir(parents=True, exist_ok=True)
    other.write_text("part: TL072\nkind: bjt-ge\nmodels: []\n", encoding="utf-8")
    recipes, clashes = P.model_recipes()
    assert clashes == ["TL072"]
    assert recipes["TL072"]["kind"] == "opamp"       # the one with more candidates, not the last read


def test_a_part_answers_to_every_device_it_could_be(data):
    """A JEDEC number cannot be told apart by its pattern: 2N3904 is a transistor, 2N5457 a JFET.
    Guessing one would hide the other, and the menu is a way of finding things."""
    at = {k: i for i, (k, _, _) in enumerate(P.MENU)}
    bits = P.device_bits(P.KIND_MAP["bjt/jfet/mosfet"])
    for d in ("bjt", "jfet", "mosfet"):
        assert bits & (1 << at[d]), d
    assert not bits & (1 << at["tube"])


def test_a_relay_is_under_relays_and_still_under_passives():
    """The finer passive entries work like NPN under BJT: the parent keeps listing everything under it."""
    at = {k: i for i, (k, _, _) in enumerate(P.MENU)}
    bits = P.device_bits(P.KIND_MAP["relay"])
    assert bits == (1 << at["passive"]) | (1 << at["relay"])
    assert at["ldr"] >= 32                  # past what a 32-bit integer holds, which is the point
    assert [k for k, _, parent in P.MENU if parent == "passive"] == [k for k, _ in P.PASSIVE_DEVICES]


def test_every_kind_the_data_carries_is_mapped_or_deliberately_not(data):
    """An unmapped kind silently drops its parts out of every menu entry."""
    from spicy_electronics_index.core.parts.extractor import FAMILIES
    for _family, kind, _rx, _strict in FAMILIES:
        assert kind in P.KIND_MAP, f"the extractor can produce {kind!r} and nothing maps it"


def test_the_menu_ships_whole_so_a_bit_always_means_the_same_device(data):
    """The bit a part carries is a position in this menu. Dropping the devices nothing answers to would
    renumber the rest and the filter would quietly select the wrong one; the site hides them instead."""
    idx = P.index()
    recipes, _ = P.model_recipes()
    rows, menu = P.search_index(idx, recipes)
    assert [d["key"] for d in menu] == [k for k, _, _ in P.MENU]
    assert len(menu) <= 53                  # the browser reads a row's bits as a double, exact to 2^53
    at = {d["key"]: i for i, d in enumerate(menu)}
    assert dict((r[0], r[4]) for r in rows)["TL072"] & (1 << at["opamp"])


def test_the_projects_are_ordered_by_stars_and_the_dead_ones_dropped(data):
    """287 projects place a TL072; what a reader wants is the five anybody has looked at."""
    config.dataset_table("part_repos").parent.mkdir(parents=True, exist_ok=True)
    config.dataset_table("part_repos").write_text(
        "part,sheets,url\n"
        "12AX7,1,https://github.com/a/small\n"
        "12AX7,9,https://github.com/b/big\n"
        "12AX7,1,https://github.com/c/gone\n", encoding="utf-8")
    config.dataset_table("repo_stats").write_text(
        "url,status,stars,forks,watchers,pushed,archived,moved_to,checked\n"
        "https://github.com/a/small,live,3,0,1,2026-01-01,0,,2026-09-22\n"
        "https://github.com/b/big,live,900,50,30,2026-01-01,0,https://github.com/b/renamed,2026-09-22\n"
        "https://github.com/c/gone,gone,,,,,,,2026-09-22\n", encoding="utf-8")
    page = P.part_payload("12AX7", P.index(), None)
    assert [r[0] for r in page["repos"]] == ["b/renamed", "a/small"]   # stars first, renamed followed
    assert page["repos"][0][2] == 900


def test_a_page_link_carries_the_line_saying_what_the_part_does_there(data):
    """"page 47" is a link and not yet an answer; the line beside it is what `summarise` wrote."""
    page = P.part_payload("12AX7", P.index(), None)
    p = page["docs"][0]["p"][0]
    assert p[4] == "First and second preamp stages V1 and V2 of the Bassman 5F6-A."
    assert p[5] == "project"


def test_a_line_in_a_later_volume_is_found_like_any_other(data):
    """audiocircuit's lines outgrew one file; a source written as volumes reads as if it were one, and a
    volume is not taken for a source of its own."""
    from spicy_electronics_index.core import csvvol
    filler = [["1", "1", f"X{i}", "mention", "a line that only fills the first volume"] for i in range(40)]
    csvvol.write(config.schematics_lines("esp"), ("doc", "page", "part", "kind", "line"),
                 filler + [["0", "1", "12AX7", "project", "Preamp V1 and V2 of the Bassman 5F6-A."]],
                 max_bytes=600)
    assert len(csvvol.volumes(config.schematics_lines("esp"))) > 1
    page = P.part_payload("12AX7", P.index(), None)
    assert page["docs"][0]["p"][0][4] == "Preamp V1 and V2 of the Bassman 5F6-A."
    assert P.sources() == sorted(SOURCES)


def test_a_page_not_summarised_yet_ends_at_the_count(data):
    """A clone without the model cache exports no lines, and the page must read exactly as before."""
    page = P.part_payload("TL072", P.index(), None)
    assert len(page["docs"][0]["p"][0]) == 4


def test_a_document_that_only_mentions_the_part_sorts_after_one_that_uses_it(data):
    """Two schematics of the same weight, and the one that sorts first by title only sells the part:
    the one whose every summarised page is a mention, an advert or not a component at all goes after
    the one that uses it. A page not summarised yet is not moved either way."""
    with open(config.schematics_uses("esp"), "a", newline="", encoding="utf-8") as f:
        csv.writer(f, lineterminator="\n").writerows(
            [["TL072", "0", "1", "9", ""], ["TL072", "2", "1", "9", ""]])
    with open(config.schematics_documents("esp"), "a", newline="", encoding="utf-8") as f:
        csv.writer(f, lineterminator="\n").writerow(
            ["2", "k9", "A Sale", "https://esp.example/sale.pdf", "", "schematic", "", "", "1", "beef"])
    with open(config.schematics_pages("esp"), "a", newline="", encoding="utf-8") as f:
        csv.writer(f, lineterminator="\n").writerow(
            ["2", "1", "https://esp.example/sale.pdf#page=1", "1", "9"])
    with open(config.schematics_lines("esp"), "a", newline="", encoding="utf-8") as f:
        csv.writer(f, lineterminator="\n").writerows(
            [["0", "1", "TL072", "project", "Tone stack buffer IC1 of the Bassman 5F6-A."],
             ["2", "1", "TL072", "advert", "Offered at a price in a mail-order list."]])
    page = P.part_payload("TL072", P.index(), None)
    assert [d["t"] for d in page["docs"]] == ["Bassman 5F6-A", "A Sale", "Opamp Bypassing"]



def test_a_page_read_as_not_this_part_is_left_off_the_page_and_out_of_every_count(data):
    """A pin label or a power rating is the extractor's mistake, not a use: AC127 on a "110/127 V" selector,
    AC110W on a "110 W" label. `summarise` reads such a page as not this part, and the page, the counts and
    the list leave it out, so a part only ever read that way is not listed for its uses."""
    with open(config.schematics_uses("esp"), "a", newline="", encoding="utf-8") as f:
        csv.writer(f, lineterminator="\n").writerows([["TL072", "0", "1", "1", ""], ["AC110W", "0", "1", "1", ""]])
    with open(config.schematics_lines("esp"), "a", newline="", encoding="utf-8") as f:
        csv.writer(f, lineterminator="\n").writerows(
            [["0", "1", "TL072", "none", "A pin label on the power supply, not a component."],
             ["0", "1", "AC110W", "none", "The 110 W rating on the mains label."]])
    idx = P.index()
    page = P.part_payload("TL072", idx, None)
    assert [d["t"] for d in page["docs"]] == ["Opamp Bypassing"]
    assert page["n"]["documents"] == 1
    rows, _ = P.search_index(idx, P.model_recipes()[0])
    counts = {r[0]: (r[1], r[2]) for r in rows}
    assert counts["TL072"] == (1, 1)
    assert "AC110W" not in counts

def test_a_part_says_the_oldest_dated_document_that_prints_it(data):
    idx = P.index()
    page = P.part_payload("12AX7", idx, None)
    year, title, si, url = page["about"]["first"]
    assert year == 1959 and title in ("Bassman 5F6-A", "Fender Bassman")    # both copies are from 1959
    assert url.endswith("bassman.pdf")


def test_what_no_source_says_is_left_out_rather_than_guessed(data):
    # The fixture has no naming schemes, no families and no catalogue: the page gets the first appearance,
    # which the index itself vouches for, and nothing else.
    idx = P.index()
    assert set(P.part_payload("TL072", idx, None).get("about", {})) <= {"first"}


def test_a_variant_borrows_its_types_sheets_and_a_bare_number_its_makers_names():
    from spicy_electronics_index.web.parts import kin_names
    assert kin_names("NJM4558D") == [("package", "NJM4558")]
    assert kin_names("BC547BTA") == [("packing", "BC547B"), ("grade", "BC547")]
    assert kin_names("2SC1815GR") == [("grade", "2SC1815")]
    assert ("maker's name", "L7812") in kin_names("7812") and ("maker's name", "SN74HC04") in kin_names("74HC04")
    # another part, not a package of one: less current, a better grade, another rating, another voltage
    for other in ("LM317L", "LM358A", "6L6GC", "TIP31C"):
        assert kin_names(other) == []


def test_japanese_packages_and_unbuffered_4000_names_find_their_type():
    from spicy_electronics_index.web.parts import kin_names
    assert kin_names("NJM4556AL") == [("package", "NJM4556A")]
    assert kin_names("NE5534AN") == [("package", "NE5534A")]
    assert ("maker's name", "CD4011B") in kin_names("CD4011")
    assert kin_names("LM317L") == []            # L is a package only on the Japanese makers' names


def test_a_jrc_name_is_sold_as_njm():
    from spicy_electronics_index.web.parts import kin_names
    assert ("maker's name", "NJM4558") in kin_names("JRC4558D")


def test_a_bare_valve_is_filed_by_its_envelope():
    from spicy_electronics_index.web.parts import kin_names
    assert ("envelope", "5Y3GT") in kin_names("5Y3") and ("envelope", "12B4A") in kin_names("12B4")


def test_a_sheet_running_over_pages_is_linked_at_its_first(tmp_path, monkeypatch):
    from spicy_electronics_index.web import parts as wp
    d = tmp_path / "pages"
    d.mkdir()
    (d / "books.csv").write_text(
        "part,book,leaf,printed,maker,title,year,checked,kind,link\n"
        "LT1028,bk,10,8,,Linear Databook,1990,,sheet,\nLT1028,bk,11,9,,Linear Databook,1990,,sheet,\n"
        "LT1028,bk,12,10,,Linear Databook,1990,,sheet,\nLT1028,bk,40,38,,Linear Databook,1990,,sheet,\n")
    monkeypatch.setattr(wp, "datasheet_pages", lambda source: d / f"{source}.csv")
    got = wp.databook_pages()["LT1028"]
    assert [r[0].rsplit("/", 1)[-1] for r in got] == ["n9", "n39"]


def test_a_forum_is_indexed_but_not_shown_and_a_repository_is_whatever_found_it(data):
    """diyAudio's attachments and Toragi's zips stay out of the site until it is decided they belong;
    a GitHub sheet is shown even when a journal found it, because the page lists it as a project."""
    reg = data / "schematics" / "sources.yaml"
    reg.write_text(reg.read_text(encoding="utf-8")
                   + "diyaudio: {kind: forum, title: diyAudio, home_url: 'https://d.example/', status: active}\n"
                   + "hardwarex: {kind: journal, title: HardwareX, home_url: 'https://h.example/', status: active}\n",
                   encoding="utf-8")
    for src, url in (("diyaudio", "https://d.example/att/1.pdf"),
                     ("hardwarex", "https://github.com/a/board/blob/HEAD/b.kicad_sch")):
        with open(config.schematics_documents(src), "w", encoding="utf-8") as f:
            f.write(f"id,key,title,url,parent,role,year,month,pages,sha\n0,k,T,{url},,schematic,2001,,1,{src}\n")
        with open(config.schematics_pages(src), "w", encoding="utf-8") as f:
            f.write(f"doc,page,url,schematic,parts\n0,1,{url},1,1\n")
        with open(config.schematics_uses(src), "w", encoding="utf-8") as f:
            f.write("part,doc,page,times,near\nTL072,0,1,1,U1\n")
    idx = P.index()
    page = P.part_payload("TL072", idx, None)
    assert sorted(idx["sources"][d["s"]] for d in page["docs"]) == ["esp", "hardwarex"]
    rows, _ = P.search_index(idx, {})
    assert dict((r[0], r[1]) for r in rows)["TL072"] == 2       # the forum's document is not counted


def test_a_part_only_a_hidden_source_prints_is_listed_without_its_documents(data):
    """A source the site does not show still says which parts exist. 2SK180 is printed only in diyAudio's
    attachments: it is in the list, with no document counted and none on its page."""
    reg = data / "schematics" / "sources.yaml"
    reg.write_text(reg.read_text(encoding="utf-8")
                   + "diyaudio: {kind: forum, title: diyAudio, home_url: 'https://d.example/', status: active}\n",
                   encoding="utf-8")
    url = "https://d.example/att/1.pdf"
    with open(config.schematics_documents("diyaudio"), "w", encoding="utf-8") as f:
        f.write(f"id,key,title,url,parent,role,year,month,pages,sha\n0,k,T,{url},,schematic,2022,,1,x\n")
    with open(config.schematics_pages("diyaudio"), "w", encoding="utf-8") as f:
        f.write(f"doc,page,url,schematic,parts\n0,1,{url},1,1\n")
    with open(config.schematics_uses("diyaudio"), "w", encoding="utf-8") as f:
        f.write("part,doc,page,times,near\n2SK180,0,1,1,Q1\n")
    idx = P.index()
    rows, _ = P.search_index(idx, {})
    assert dict((r[0], (r[1], r[2])) for r in rows)["2SK180"] == (0, 0)
    assert "2SK180" in P.all_names(idx, {})
    assert P.part_payload("2SK180", idx, None).get("docs", []) == []


def test_databook_pages_are_listed_apart_from_the_makers_sheets(data):
    idx = P.index()
    idx["databook"] = {"TL072": [["https://archive.org/details/bk/page/n9", "", "", "Linear Databook p. 8",
                                  "archive_databooks", "a page of a databook (1990)"]]}
    idx["books"] = {"archive_databooks"}
    idx["sheets"] = {"TL072": [["https://ti.example/tl072.pdf", "ti", "", "", "ti_datasheets", ""]]}
    about = P.part_payload("TL072", idx, None)["about"]
    assert [r[0] for r in about["sheets"]] == ["https://ti.example/tl072.pdf"]
    assert [r[4] for r in about["books"]] == ["archive_databooks"]


def test_a_repository_among_the_documents_carries_its_stars(data):
    """The page lists every repository in one list by stars, whichever way it was found."""
    idx = P.index()
    idx["repo_stats"] = {"a/board": {"stars": "7", "forks": "1", "watchers": "2", "status": "live"}}
    idx["uses"]["TL072"] = [(idx["sources"].index("esp"), {"doc": "9", "page": "1", "times": "1", "near": ""})]
    idx["documents"]["esp"]["9"] = {"title": "a/board: b.kicad_sch", "url": "https://github.com/a/board/blob/HEAD/b.kicad_sch"}
    assert P.part_payload("TL072", idx, None)["stars"] == {"a/board": [7, 1, 2]}


def test_an_issue_is_dated_to_the_month_when_its_row_says_so():
    assert P.issue_date({"year": "1985", "month": "8"}) == "1985-08"
    assert P.issue_date({"year": "1985", "month": ""}) == "1985"
    assert P.issue_date({"year": "", "month": "08"}) == ""


def test_a_model_librarys_device_type_files_a_part_nothing_else_does(data):
    """1SS133 is in no recipe or dictionary, but a model library defines it as a D model: it is a diode
    of some sort, which is enough to read its JIS name as a signal diode."""
    idx = P.index()
    idx["modelled"] = {"1SS133": P.MODEL_LIBRARY_KINDS["diode"]}
    assert P.devices_of("1SS133", "", idx) == ("diode", "diode-ge", "zener", "led")
    assert P.devices_of("1SS133", "bjt", idx) == ("bjt",)             # a narrower kind wins
    assert P.devices_of("2SC1815", "", idx) == ()


def test_a_family_narrows_the_devices_a_part_could_be():
    assert P.narrowed(("diode", "diode-ge", "zener", "led"), "signal-diode") == ("diode", "diode-ge")
    assert P.narrowed(("bjt", "jfet", "mosfet"), "jfet") == ("jfet",)
    assert P.narrowed(("bjt",), "jfet") == ("bjt",)           # nothing shared: the part's own kind stands
    assert P.narrowed(("bjt",), "") == ("bjt",)


def test_a_transistor_is_filed_by_polarity_only_when_every_source_agrees(data):
    """2SC1815's name says NPN and nothing says otherwise. 2SA1295's name says PNP and a catalogue title
    says NPN: it stays a silicon BJT, and its page shows both sources rather than picking one."""
    import shutil
    shutil.copytree(REPO / "data" / "parts" / "schemes", config.naming_schemes())     # the JIS letters
    idx = P.index()
    for part in ("2SC1815", "2SA1295", "BC109"):
        idx["uses"][part] = [(0, {"doc": "0"})]
    cat = dict.fromkeys(P.CATALOGUE_FIELDS, "")
    idx["catalogued"]["2SA1295"] = [[{**cat, "maker": "sanken", "title": "Silicon NPN transistor",
                                      "page": "https://x.example/2sa1295"}[k] for k in P.CATALOGUE_FIELDS]]
    rows, menu = P.search_index(idx, {})
    at = {d["key"]: i for i, d in enumerate(menu)}
    bits = {r[0]: r[4] for r in rows}
    assert bits["2SC1815"] & (1 << at["bjt-npn"]) and bits["2SC1815"] & (1 << at["bjt"])
    assert not bits["2SC1815"] & (1 << at["bjt-pnp"])
    assert bits["2SA1295"] & (1 << at["bjt"])
    assert not bits["2SA1295"] & ((1 << at["bjt-npn"]) | (1 << at["bjt-pnp"]))
    assert not bits["BC109"] & ((1 << at["bjt-npn"]) | (1 << at["bjt-pnp"]))     # nothing says which
    assert {d["key"]: d.get("parent") for d in menu}["bjt-npn"] == "bjt"
    claims = P.about("2SA1295", idx, None)["polarity"]
    assert sorted(c[:3] for c in claims) == [["NPN", "catalogue", "sanken"], ["PNP", "name", "jis-c7012"]]


def test_a_grade_of_a_type_is_what_its_type_is_and_a_pair_is_not(data):
    """BC547B is a grade of BC547, which the libraries define as NPN. BC847BPN folds back to BC847 too,
    but it is an NPN and a PNP in one package. 2SC1815G's G is no rank JIS knows, and its C still says NPN."""
    import shutil
    shutil.copytree(REPO / "data" / "parts" / "schemes", config.naming_schemes())
    idx = P.index()
    idx["modelled_polarity"] = {"BC547": [["NPN", "spice_definitions", "https://x.example/lib"]],
                                "BC847": [["NPN", "spice_definitions", "https://x.example/lib"]]}
    idx["sheet_polarity"] = {"AC127": [["NPN", "AC127 NPN germanium transistor", "https://y.example/ac127"]]}
    bjt = P.KIND_MAP["bjt"]
    assert P.polarity_claims("BC547B", bjt, None, idx) == [["NPN", "type", "BC547", ""]]
    assert P.polarity_claims("BC847BPN", bjt, None, idx) == []
    assert P.polarity_claims("2SC1815G", bjt, None, idx) == [["NPN", "name", "jis-c7012", ""]]
    assert P.polarity_claims("AC127", P.KIND_MAP["bjt-ge"], None, idx) == [
        ["NPN", "sheet", "AC127 NPN germanium transistor", "https://y.example/ac127"]]



def test_a_family_that_allows_passives_keeps_the_finer_passive_entries():
    # "other" allows passives: a relay filed under it is still a relay, not only hardware
    assert P.catalogue.families()["other"]["kinds"] == ["passive"]
    assert P.narrowed(("passive", "relay"), "other") == ("passive", "relay")
    assert P.narrowed(("passive", "magnetic-core"), "other") == ("passive", "magnetic-core")


def test_the_page_leaves_the_bench_columns_empty_for_exactly_the_passive_entries():
    """web/src/parts.tsx keeps its own list of the kinds the bench never measures; it must be the menu's."""
    import re
    from pathlib import Path
    ts = (Path(__file__).parents[2] / "web" / "src" / "parts.tsx").read_text(encoding="utf-8")
    block = ts[ts.index("export const NOT_BENCHED"):ts.index("function PhysicsCell")]
    assert set(re.findall(r"'([a-z-]+)'", block)) == {"passive", *(k for k, _ in P.PASSIVE_DEVICES)}


def test_the_usage_filter_counts_each_part_by_source_a_magazine_by_decade_and_a_book_by_title(data):
    """The list's filter needs, per part, how many times each source writes it — a magazine by decade,
    the books source by title, and every GitHub repository under one entry — and the pieces add up to
    the part's usages in the index."""
    reg = config.schematics_registry()
    reg.write_text(reg.read_text(encoding="utf-8")
                   + "ww: {kind: magazine, title: WW, home_url: 'https://ww.example/', status: active}\n"
                   + "books: {kind: book, title: Books, home_url: 'https://b.example/', status: active}\n",
                   encoding="utf-8")
    fields = ("id", "key", "title", "url", "parent", "role", "year", "month", "pages", "sha")
    ww = [["0", "a", "Oct 1975", "https://ww.example/1975-10.pdf", "", "issue", "1975", "10", "1", ""],
          ["1", "b", "Jan 1983", "https://ww.example/1983-01.pdf", "", "issue", "1983", "1", "1", ""],
          ["2", "c", "Undated", "https://ww.example/x.pdf", "", "issue", "", "", "1", ""],
          ["3", "d", "A board", "https://github.com/o/r/blob/main/x.sch", "", "schematic", "2021", "", "1", ""]]
    books = [["0", "e", "Valley & Wallman — Vacuum Tube Amplifiers", "https://b.example/vw.pdf", "", "book", "", "", "1", ""],
             ["1", "f", "Ben Duncan — High Performance Audio Power Amplifiers", "https://b.example/bd.pdf", "", "book", "", "", "1", ""]]
    import csv
    for path, head, body in [
        (config.schematics_documents("ww"), fields, ww),
        (config.schematics_pages("ww"), ("doc", "page", "url", "schematic", "parts"),
         [[d[0], "1", d[3] + "#page=1", "1", "1"] for d in ww]),
        (config.schematics_uses("ww"), ("part", "doc", "page", "times", "near"),
         [["12AX7", "0", "1", "3", ""], ["12AX7", "1", "1", "1", ""], ["12AX7", "2", "1", "1", ""], ["TL072", "3", "1", "2", ""]]),
        (config.schematics_documents("books"), fields, books),
        (config.schematics_pages("books"), ("doc", "page", "url", "schematic", "parts"),
         [[d[0], "1", d[3] + "#page=1", "1", "1"] for d in books]),
        (config.schematics_uses("books"), ("part", "doc", "page", "times", "near"),
         [["12AX7", "0", "1", "4", ""], ["12AX7", "1", "1", "1", ""], ["12AX7", "1", "2", "1", ""]]),
    ]:
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(head)
            w.writerows(body)
    idx = P.index()
    menu, by_part = P.usage_facets(idx)
    keys = [f["key"] for f in menu]
    # the groups in the page's order; the most written source first; a magazine's decades oldest first,
    # undated last; a book per title, A to Z
    assert keys == ["esp", "el34world",
                    "books/Ben Duncan — High Performance Audio Power Amplifiers", "books/Valley & Wallman — Vacuum Tube Amplifiers",
                    "ww/1970s", "ww/1980s", "ww", "github"]
    assert [f["group"] for f in menu] == ["projects", "projects", "paper", "paper", "paper", "paper", "paper", "github"]
    assert menu[4] == {"key": "ww/1970s", "group": "paper", "source": "ww", "label": "1970s", "by": "decade", "n": 3, "docs": 1}
    assert menu[3]["by"] == "title" and menu[3]["n"] == 4
    assert "label" not in menu[0] and menu[-1]["source"] == "github"
    assert by_part["12AX7"] == [[0, 2], [1, 1], [2, 2], [3, 4], [4, 3], [5, 1], [6, 1]]
    assert by_part["TL072"] == [[0, 1], [7, 2]]
    search, _ = P.search_index(idx, {})
    for row in search:
        assert sum(n for _, n in by_part.get(row[0], [])) == row[1]
