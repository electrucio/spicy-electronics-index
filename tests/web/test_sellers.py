"""The sellers list: a registry the site can show, every entry whole, no country leading."""
import re

import yaml

from spicy_electronics_index.core import config
from spicy_electronics_index.core.parts import catalogue
from spicy_electronics_index.web import parts as P

DATE = re.compile(r"\d{4}-\d{2}(-\d{2})?")


def registry():
    return yaml.safe_load(config.sellers_registry().read_text(encoding="utf-8"))


def test_every_seller_is_whole_and_of_a_declared_kind_and_group():
    doc = registry()
    types, groups = set(doc["types"]), {g["id"] for g in doc["groups"]}
    kinds = {k for k, _ in P.DEVICES}
    makers = set(catalogue.makers())
    refs = set(catalogue.references())
    ids = [s["id"] for s in doc["sellers"]]
    assert len(ids) == len(set(ids)), "a seller id repeats"
    for s in doc["sellers"]:
        assert s["type"] in types, s["id"]
        assert s["group"] in groups, s["id"]
        assert s["url"].startswith("https://"), s["id"]
        assert re.fullmatch(r"[A-Z]{2}", s["base"]), s["id"]
        if s["base"] == "WW":   # a platform is based nowhere; a shop is based somewhere
            assert s["type"] in ("marketplace", "independent"), s["id"]
        assert s["useful_for"] and s["title"] and s["checked"], s["id"]
        assert s.get("priority", 2) in (1, 2, 3), s["id"]
        if "search" in s:
            assert "{part}" in s["search"] and s["search"].startswith("https://"), s["id"]
        assert set(s.get("kinds") or []) <= kinds, s["id"]
        assert set(s.get("makers") or []) <= makers, s["id"]
        # A profile is the seller in the maintainer's words, dated and linked, never a quotation.
        about = s.get("about")
        if about:
            assert about["url"].startswith("https://") and about["says"], s["id"]
            assert isinstance(about["checked"], str) and DATE.fullmatch(about["checked"]), s["id"]
            assert '"' not in about["says"] and "“" not in about["says"], s["id"]
        ships = s.get("ships")
        if ships:
            assert ships["text"], s["id"]
            assert not ships.get("url") or ships["url"].startswith("https://"), s["id"]
            assert not ships.get("checked") or (isinstance(ships["checked"], str) and DATE.fullmatch(ships["checked"])), s["id"]
        for o in s.get("opinions") or []:
            assert o["forum"] and o["title"] and o["gist"], s["id"]
            assert o["url"].startswith("https://"), s["id"]
            assert isinstance(o["date"], str) and DATE.fullmatch(o["date"]), s["id"]
            assert '"' not in o["gist"] and "“" not in o["gist"], s["id"]
    for g in doc["groups"]:
        assert g["title"] and g["note"] and isinstance(g["kinds"], list), g["id"]
        assert set(g["kinds"]) <= kinds, g["id"]
        if g.get("caveat"):
            assert g["caveat"] in refs, g["id"]


def test_a_part_page_never_lists_a_box_maker_or_a_fabricator():
    """A group with no kinds is on no part page; the maker's store comes through `makers` only."""
    doc = registry()
    by_id = {g["id"]: g for g in doc["groups"]}
    for gid in ("enclosures", "pcb_fab", "maker", "project_pcbs", "direct", "regional", "search"):
        assert by_id[gid]["kinds"] == [], gid
    assert by_id["broadline"]["kinds"] and by_id["marketplace_surplus"]["kinds"]
    stores = [s for s in doc["sellers"] if s["group"] == "direct" and s.get("makers")]
    assert {s["id"] for s in stores} >= {"ti_direct", "adi_buy", "microchipdirect"}
    ti = next(s for s in stores if s["id"] == "ti_direct")
    assert {"texas-instruments", "national"} <= set(ti["makers"])   # the lineage: a National part is TI's now


def test_a_marketplace_is_based_nowhere():
    doc = registry()
    platforms = {s["id"]: s["base"] for s in doc["sellers"] if s["type"] == "marketplace"}
    assert platforms and all(base == "WW" for base in platforms.values()), platforms


def test_the_site_gets_the_list_by_priority_then_name_and_never_by_country():
    got = P.sellers()
    assert set(got) == {"types", "groups", "sellers"}
    keys = [(s.get("priority", 2), s["title"].lower()) for s in got["sellers"]]
    assert keys == sorted(keys)
    assert all(set(s) <= set(P.SELLER_KEYS) for s in got["sellers"])
    assert any(s.get("search") for s in got["sellers"])
    by_id = {s["id"]: s for s in got["sellers"]}
    assert by_id["ti_direct"]["makers"][0] == "texas-instruments"
    assert by_id["mouser"]["robots"] and by_id["mouser"]["search_result"]   # the profile's facts travel
    assert by_id["ebay"]["base"] == "WW"


def test_an_empty_kinds_list_travels_because_it_means_no_part_page(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PUBLIC_DATA", tmp_path)
    reg = config.sellers_registry()
    reg.parent.mkdir(parents=True)
    reg.write_text(
        "types: {specialist: a shop}\n"
        "groups:\n- {id: g, title: G, note: n, kinds: [opamp]}\n"
        "sellers:\n"
        "- {id: a, title: A, url: 'https://a.example/', type: specialist, base: DE, group: g, useful_for: x,"
        " checked: '2026-10-12', kinds: []}\n"
        "- {id: b, title: B, url: 'https://b.example/', type: specialist, base: DE, group: g, useful_for: x,"
        " checked: '2026-10-12', priority: 1}\n",
        encoding="utf-8")
    got = P.sellers()
    assert [s["id"] for s in got["sellers"]] == ["b", "a"]
    assert got["sellers"][1]["kinds"] == [] and "kinds" not in got["sellers"][0]


def test_no_registry_means_no_list(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PUBLIC_DATA", tmp_path)
    assert P.sellers() == {}
