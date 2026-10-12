"""The TME stage against a pretend API: what it publishes, what it keeps, and what it never asks twice."""
import csv
import gzip
import json

import pytest

from spicy_electronics_index.core import config, http
from spicy_electronics_index.distributors import tme

ENTRY = {"api": "https://api.example", "country": "ES", "currency": "EUR", "language": "en", "delay": 0, "data_delay": 0}
PHOTO = "//cdn.example/x/732574_1.jpg?width=640&height=480&wat=1&ci_sign=abc"


def product(symbol, number, maker="TEXAS INSTRUMENTS", status=(), photo=PHOTO):
    return {"symbol": symbol, "manufacturer": {"id": 77, "name": maker}, "manufacturer_symbols": [number],
            "description": "IC: operational amplifier; 3MHz; Ch: 2", "category": {"id": 112844, "name": "THT operational amplifiers"},
            "product_status": list(status), "minimal_amount": 1, "multiples": 1, "unit": {"id": "ST", "short_name": "pcs"},
            "assets": {"primary_photo": {"prime": photo, "thumbnail": photo}}}


CATALOGUE = {
    "TL072CP": product("TL072CP", "TL072CP"),
    "TL072IP": product("TL072IP", "TL072IP"),
    "TL072CD-ST": product("TL072CD-ST", "TL072CD", maker="STMicroelectronics"),
    "LM8330TME/NOPB": product("LM8330TME/NOPB", "LM8330TME/NOPB"),
    "LM833N/NOPB": product("LM833N/NOPB", "LM833N/NOPB"),
    "BD139": product("BD139", "BD139", maker="STMicroelectronics", status=("NOT_IN_OFFER", "CANNOT_BE_ORDERED")),
}
DATA = {
    "TL072CP": {"symbol": "TL072CP", "stock_quantity": 4320, "unit": {"short_name": "pcs"},
                "prices": {"elements": [{"amount": 1, "price": 0.813, "special": False}, {"amount": 4, "price": 0.708, "special": False}],
                           "tax": {"type": "VAT", "rate": 21.0}, "currency": "EUR", "type": "NET"}},
    "TL072IP": {"symbol": "TL072IP", "stock_quantity": 0, "prices": {"elements": [], "tax": {"type": "VAT", "rate": 21.0}, "currency": "EUR", "type": "NET"}},
    "TL072CD-ST": {"symbol": "TL072CD-ST", "stock_quantity": 90, "prices": {"elements": [{"amount": 1, "price": 0.5, "special": False}], "tax": {"type": "VAT", "rate": 21.0}, "currency": "EUR", "type": "NET"}},
    "LM833N/NOPB": {"symbol": "LM833N/NOPB", "stock_quantity": 7, "prices": {"elements": [{"amount": 1, "price": 1.0, "special": False}], "tax": {"type": "VAT", "rate": 21.0}, "currency": "EUR", "type": "NET"}},
    "BD139": {"symbol": "BD139", "stock_quantity": 0, "prices": {"elements": [], "tax": {"type": "VAT", "rate": 21.0}, "currency": "EUR", "type": "NET"}},
}
PARAMS = {s: {"symbol": s, "parameters": {"elements": [{"id": 35, "name": "Case", "values": [{"id": 1, "value": "DIP8"}]}]}}
          for s in CATALOGUE}
FILES = {"TL072CP": {"symbol": "TL072CP", "assets": {}, "documents": {"elements": [
    {"url": "//www.example/Document/abc/TL072-LNK.txt", "type": "LNK", "file_name": "TL072-LNK.txt", "language": "EN"},
    {"url": "//www.example/Document/def/tl072.pdf", "type": "DTE", "file_name": "tl072.pdf", "language": "EN"}]}}}
CATEGORIES = [{"id": 111000, "parent_id": 111000, "name": ""}, {"id": 112140, "parent_id": 111000, "name": "Semiconductors"},
              {"id": 100421, "parent_id": 112140, "name": "Analog and mixed integrated circuits"},
              {"id": 112844, "parent_id": 100421, "name": "THT operational amplifiers"},
              {"id": 112607, "parent_id": 111000, "name": "Workplace Equipment"}, {"id": 900, "parent_id": 112607, "name": "Wrenches Sets"}]
WITHDRAWN = {"symbol": "2SC1815", "manufacturer": None, "manufacturer_symbols": [], "description": "Transistor: NPN; bipolar; 60V",
             "category": {"id": 112844, "name": "NPN THT transistors"}, "product_status": ["NOT_IN_OFFER", "CANNOT_BE_ORDERED"],
             "minimal_amount": 1, "multiples": 1, "unit": {"id": "ST", "short_name": "pcs"}, "assets": None}
WRENCH = product("KT-6550", "6550", maker="KING TONY")
WRENCH["category"] = {"id": 900, "name": "Wrenches Sets"}
CATALOGUE_EXTRA = {"KT-6550": WRENCH, "2SC1815": WITHDRAWN}
SEARCH = {"TL072": ["TL072CP", "TL072IP", "TL072CD-ST"], "LM833": ["LM8330TME/NOPB", "LM833N/NOPB"], "J201": [], "BD139": ["BD139"], "6550": ["KT-6550"], "2SC1815": []}
CATALOGUE.update(CATALOGUE_EXTRA)


class FakeClient:
    """Answers like the API, counts calls, and fails where a test asks it to."""

    def __init__(self, fail=()):
        self.country, self.currency, self.delay, self.data_delay = "ES", "EUR", 0, 0
        self.calls = []
        self.fail = set(fail)

    def get(self, path, params, delay=None):
        self.calls.append((path, params))
        if path in self.fail:
            return http.Response(503, path, why="busy")
        if path == "/products" and "mpns[]" in params:
            wanted = {tme.match.norm(m) for m in params["mpns[]"]}
            els = [e for e in CATALOGUE.values() if e["manufacturer_symbols"] and tme.match.norm(e["manufacturer_symbols"][0]) in wanted]
        elif path == "/products":
            wanted = {tme.match.norm(m) for m in params["symbols[]"]}
            els = [e for e in CATALOGUE.values() if tme.match.norm(e["symbol"]) in wanted]
        elif path == "/products/search":
            syms = SEARCH.get(params["phrase"], [])
            body = {"status": "OK", "data": {"products": {"elements": [CATALOGUE[s] for s in syms]},
                                              "counters": {"pages": 1, "count": len(syms)}}}
            return http.Response(200, path, body=json.dumps(body).encode())
        elif path == "/products/data":
            els = [DATA[s] for s in params["symbols[]"] if s in DATA]
        elif path == "/products/parameters":
            els = [PARAMS[s] for s in params["symbols[]"] if s in PARAMS]
        elif path == "/products/files":
            els = [FILES[s] for s in params["symbols[]"] if s in FILES]
        elif path == "/products/categories/list":
            els = CATEGORIES
        else:
            return http.Response(404, path)
        return http.Response(200, path, body=json.dumps({"status": "OK", "data": {"elements": els}}).encode())


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PUBLIC_DATA", tmp_path / "data")
    monkeypatch.setattr(config, "material_root", lambda: tmp_path / "private")
    return tmp_path


def table():
    with open(config.distributors_table("tme"), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def files():
    with open(config.distributors_files("tme"), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_what_is_published_per_order_number(home):
    client = FakeClient()
    counts = tme.run(ENTRY, ["TL072", "LM833", "J201", "BD139"], client=client)
    rows = {(r["part"], r["symbol"]): r for r in table()}
    assert list(rows[("TL072", "TL072CP")]) == list(tme.TABLE)
    cp = rows[("TL072", "TL072CP")]
    assert cp["match"] == "variant" and cp["manufacturer"] == "TEXAS INSTRUMENTS" and cp["mpn"] == "TL072CP"
    assert cp["case"] == "DIP8" and cp["status"] == "" and cp["stock"] == "4320"
    assert cp["prices"] == "1:0.813;4:0.708" and cp["currency"] == "EUR" and cp["price_type"] == "NET" and cp["vat_rate"] == "21.0"
    assert cp["photo"] == "https:" + PHOTO and cp["checked"] == tme.today()
    assert ("TL072", "TL072CD-ST") in rows and ("LM833", "LM833N/NOPB") in rows
    assert ("LM833", "LM8330TME/NOPB") not in rows                      # the keypad controller is not an LM833
    assert rows[("J201", "")]["match"] == "none"                           # asked, nothing kept, dated
    bd = rows[("BD139", "BD139")]
    assert bd["match"] == "exact" and bd["status"] == "NOT_IN_OFFER CANNOT_BE_ORDERED" and bd["prices"] == ""
    assert counts["matched"] == 4 and counts["none"] == 1 and counts["priced"] == 3


def test_links_are_published_but_a_link_file_behind_a_challenge_is_not(home):
    tme.run(ENTRY, ["TL072"], client=FakeClient())
    kinds = {(r["symbol"], r["kind"], r["type"]) for r in files()}
    assert ("TL072CP", "photo", "prime") in kinds
    assert ("TL072CP", "document", "DTE") in kinds
    assert not any(t == "LNK" for _, _, t in kinds)
    assert all(r["url"].startswith("https://") for r in files())


def test_the_distributors_prose_stays_out_of_the_public_files(home):
    tme.run(ENTRY, ["TL072"], client=FakeClient())
    for p in (config.distributors_table("tme"), config.distributors_files("tme"), config.distributors_state("tme")):
        assert "operational amplifier; 3MHz" not in p.read_text(encoding="utf-8")


def test_every_answer_is_kept_whole_in_the_private_tree(home):
    tme.run(ENTRY, ["TL072"], client=FakeClient())
    cache = config.distributor_cache("tme")
    kept = {p.name for p in cache.iterdir()}
    assert kept == {f"TL072.{w}.json.gz" for w in ("mpns", "search", "data", "params", "files")}
    search = json.loads(gzip.decompress((cache / "TL072.search.json.gz").read_bytes()))
    assert search["pages"][0]["data"]["products"]["elements"][0]["description"].startswith("IC: operational")


def test_a_second_run_asks_nothing_and_a_stale_part_asks_only_for_prices(home):
    first = FakeClient()
    tme.run(ENTRY, ["TL072", "J201"], client=first)
    second = FakeClient()
    tme.run(ENTRY, ["TL072", "J201"], client=second)
    assert second.calls == []
    led = tme.Ledger(config.distributors_state("tme"), stages=tme.STAGES, fields=tme.FIELDS, versioned=tme.VERSIONED)
    led.stamp("TL072", "data", version=tme.DATA_VERSION, when="2020-01-01")
    led.save()
    third = FakeClient()
    tme.run(ENTRY, ["TL072", "J201"], client=third)
    assert {p for p, _ in third.calls} == {"/products/data", "/products/parameters", "/products/files"}
    assert {r["symbol"] for r in table() if r["part"] == "TL072"} == {"TL072CP", "TL072IP", "TL072CD-ST"}


def test_a_failed_call_leaves_the_part_for_the_next_run(home):
    tme.run(ENTRY, ["TL072"], client=FakeClient(fail={"/products/data"}))
    led = tme.Ledger(config.distributors_state("tme"), stages=tme.STAGES, fields=tme.FIELDS, versioned=tme.VERSIONED)
    assert led.get("TL072")["match_at"] and not led.get("TL072")["data_at"]
    assert not config.distributors_table("tme").exists() or not [r for r in table() if r["part"] == "TL072"]
    again = FakeClient()
    tme.run(ENTRY, ["TL072"], client=again)
    assert "/products/search" not in {p for p, _ in again.calls}       # the match stands; only the prices were owed
    assert [r for r in table() if r["part"] == "TL072"]


def test_refresh_asks_again_and_replaces_the_rows(home):
    tme.run(ENTRY, ["TL072"], client=FakeClient())
    DATA["TL072CP"]["stock_quantity"] = 1
    try:
        tme.run(ENTRY, ["TL072"], refresh=True, client=FakeClient())
        assert {r["symbol"]: r["stock"] for r in table()}["TL072CP"] == "1"
    finally:
        DATA["TL072CP"]["stock_quantity"] = 4320


def test_wanted_takes_the_most_printed_of_each_kind(home, tmp_path):
    config.known_parts().parent.mkdir(parents=True, exist_ok=True)
    config.known_parts().write_text("name,part,kind,from\nTL072,TL072,opamp,x\nNE5532,NE5532,opamp,x\n2N3904,2N3904,bjt,x\n"
                                    "BC547,BC547,bjt,x\n12AX7,12AX7,tube,x\nECC83,ECC83,alias of 12AX7,x\n", encoding="utf-8")
    config.schematics_parts().parent.mkdir(parents=True, exist_ok=True)
    config.schematics_parts().write_text("part,documents,pages,uses,sources\nNE5532,50,1,1,a\nTL072,900,1,1,a\nBC547,20,1,1,a\n", encoding="utf-8")
    assert tme.wanted(top_per_kind=1) == ["TL072", "BC547", "12AX7"]
    assert tme.wanted() == ["TL072", "NE5532", "BC547", "12AX7", "2N3904"]
    assert tme.wanted(["BC547", "BC547", "X"]) == ["BC547", "X"]


def test_the_credentials_are_read_from_outside_the_repository(monkeypatch, tmp_path):
    monkeypatch.setattr(tme, "TOKEN_FILE", tmp_path / "t")
    monkeypatch.setattr(tme, "SECRET_FILE", tmp_path / "s")
    with pytest.raises(SystemExit, match="no TME credentials"):
        tme.Client.credentials()
    (tmp_path / "t").write_text("a" * 50 + "\n")
    (tmp_path / "s").write_text("b" * 20)
    assert tme.Client.credentials() == ("a" * 50, "b" * 20)


def test_a_products_category_must_fit_the_kind_of_the_part(home):
    """A 6550 is a valve in the dictionary; TME's 6550 is a socket wrench, and the number alone cannot tell."""
    config.known_parts().parent.mkdir(parents=True, exist_ok=True)
    config.known_parts().write_text("name,part,kind,from\n6550,6550,tube,x\nTL072,TL072,opamp,x\n", encoding="utf-8")
    entry = {**ENTRY, "categories": {"default": ["Semiconductors", "Optoelectronics"]}}
    client = FakeClient()
    tme.run(entry, ["6550", "TL072"], client=client)
    rows = {(r["part"], r["symbol"]): r for r in table()}
    assert rows[("6550", "")]["match"] == "none"
    assert ("TL072", "TL072CP") in rows
    assert sum(1 for p, _ in client.calls if p == "/products/categories/list") == 1
    assert (config.distributor_cache("tme") / "_categories.json.gz").exists()


def test_reread_matches_again_from_what_was_kept_without_asking(home, monkeypatch):
    tme.run(ENTRY, ["TL072"], client=FakeClient())
    monkeypatch.setattr(tme, "MATCH_VERSION", "99")
    again = FakeClient()
    tme.run(ENTRY, ["TL072"], client=again, reread=True)
    asked = {p for p, _ in again.calls}
    assert "/products/search" not in asked and "/products" not in asked
    assert "/products/data" in asked                                   # prices are asked for afresh
    led = tme.Ledger(config.distributors_state("tme"), stages=tme.STAGES, fields=tme.FIELDS, versioned=tme.VERSIONED)
    assert led.get("TL072")["match_v"] == "99"


def test_a_product_the_distributor_withdrew_is_found_by_its_symbol_and_kept_as_evidence(home):
    client = FakeClient()
    tme.run(ENTRY, ["2SC1815"], client=client)
    rows = {(r["part"], r["symbol"]): r for r in table()}
    row = rows[("2SC1815", "2SC1815")]
    assert row["match"] == "exact" and row["manufacturer"] == "" and row["mpn"] == ""
    assert row["status"] == "NOT_IN_OFFER CANNOT_BE_ORDERED" and row["prices"] == "" and row["photo"] == ""
    assert sum(1 for p, q in client.calls if p == "/products" and "symbols[]" in q) == 1
