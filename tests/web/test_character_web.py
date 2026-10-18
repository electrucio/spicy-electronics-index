"""The characterisation as the site gets it: the method page from the catalogue, a part's file from its
models' records, and a build that still works without the private roots."""
import json

from spicy_electronics_index.bench import catalogue as C
from spicy_electronics_index.bench import character_publish as P
from spicy_electronics_index.core import config
from spicy_electronics_index.web import build as web_build
from spicy_electronics_index.web import character as W

HASH = "0123456789abcdef0123456789abcdef01234567"


def test_the_method_page_is_the_catalogue_plus_the_drawings_that_exist():
    doc = W.methods_payload()
    assert doc["version"] == C.version() and {m["id"] for m in doc["measurements"]} == set(C.ids())
    assert isinstance(doc["drawings"], list) and all(d.removesuffix("-pnp") in set(C.ids()) for d in doc["drawings"])
    # every bipolar drawing has its PNP twin; a FET or an amplifier has none
    assert all(f"{d}-pnp" in doc["drawings"] for d in doc["drawings"] if d.startswith("bjt-") and not d.endswith("-pnp"))
    assert not any(d.endswith("-pnp") for d in doc["drawings"] if not d.startswith("bjt-"))
    assert all(m["id"] in doc["drawings"] for m in doc["measurements"] if m["drawing"]["file"])      # every file named exists
    hfe = next(m for m in doc["measurements"] if m["id"] == "bjt-hfe-ic")
    assert "VH1 ch1 0 -5" in hfe["directives_pnp"] and len(hfe["directives_pnp"]) == len(hfe["directives"])


def fake_record():
    result = {"id": HASH, "engine": "qspice", "version": "v", "catalogue": C.version(),
              "values": {"bjt-hfe-ic": {"hfe@1mA,5V": 150.0}}, "codes": {"bjt-hfe-ic": "ok"}, "errors": {},
              "derived": {"ib@1mA": 6.6667e-06}, "curves": {"bjt-hfe-ic": {"hFE, VCE=5V": [100.0, 150.0]}},
              "decks": {"dc": {"ids": ["bjt-hfe-ic"], "analysis": "dc", "pack": 10, "digest": "abc" * 20, "cpu_s": 0.1}}, "error": None}
    info = {"engine": "qspice", "image": "sha256:img", "bench": {"commit": "c", "clean": True}, "on": "2026-10-04", "version": "character-1"}
    job = {"id": HASH, "kind": "bjt", "family": "gummel-poon", "polarity": "npn", "changes": ["renamed"], "parts": ["bjt/QX"]}
    return P.build_record(HASH, {"qspice": (info, result, job)}, C.load())


def test_a_part_file_joins_the_records_to_the_page_s_model_list(tmp_path, monkeypatch):
    rec = fake_record()
    version = C.version()
    monkeypatch.setattr(config, "PUBLIC_DATA", tmp_path)        # the catalogue moves with it: read first
    P.write(HASH, rec)
    recipe = {"part": "QX", "kind": "bjt", "models": [{"hash": "nothing-published"}, {"hash": HASH}, {}]}
    payload = W.part_payload(recipe)
    assert set(payload["models"]) == {"1"} and payload["primary"] == "qspice" and payload["catalogue"] == version
    assert payload["models"]["1"] == {"hash": HASH, "polarity": rec["polarity"]}     # the index: the record is its own file
    model = W.model_payload(W.record_of(HASH))
    assert model["values"]["bjt-hfe-ic"]["qspice"]["hfe@1mA,5V"] == 150.0
    assert "card" not in json.dumps(payload) and "card" not in json.dumps(model)
    assert W.summary(payload) == {"n": 1, "m": 2}          # hfe-ic and the agreement entry
    assert W.part_payload({"models": [{"hash": "none"}]}) is None and W.summary(None) is None


def test_the_build_writes_the_method_page_without_the_private_roots(tmp_path, monkeypatch):
    def explode():
        raise AssertionError("web build touched a private tree")
    monkeypatch.setattr(config, "material_root", explode)
    monkeypatch.setattr(config, "spice_models_root", explode)
    monkeypatch.setattr("spicy_electronics_index.web.build.web_data", lambda: tmp_path)
    manifest = web_build.build()
    assert "character" in manifest["have"]
    doc = json.loads((tmp_path / "bench" / "methods.json").read_text(encoding="utf-8"))
    assert doc["version"] == C.version()


def test_the_models_table_ranks_by_what_the_bench_found_and_says_why(monkeypatch):
    from spicy_electronics_index.bench import record as R
    recs = {
        "a": {"primary": "qspice", "runs": {"qspice": "ok", "ngspice": "ok", "ltspice": "ok"}, "codes": {"bjt-ft": "ok"},
              "values": {"bjt-agreement": {"all": {"agree_1pct": 0.9, "odd_engine": "ltspice", "disagreeing": ["bjt-ft"]}}},
              "errors": {}, "engines": {"qspice": {"cpu_s": 5.0}}},
        "b": {"primary": "qspice", "runs": {"qspice": "ok", "ngspice": "failed"}, "codes": {"bjt-ft": "suspect"},
              "values": {"bjt-agreement": {"all": {"agree_1pct": 0.4}}}, "errors": {"bjt-switching": {"ltspice": "sw1A: timeout; "}},
              "engines": {"qspice": {"cpu_s": 40.0}}},
    }
    cards = {"a": {"family": "gummel-poon", "absent": ["KF"]}, "b": {"family": "gummel-poon", "absent": ["KF", "VAF", "TR"], "dialect": ["nk-above-1"]}}
    monkeypatch.setattr(W, "record_of", lambda h: recs.get(h))
    monkeypatch.setattr(R, "load", lambda kind, part: {"cards": cards})
    recipe = {"kind": "bjt", "part": "QX", "models": [{"source": "x", "name": "unmeasured"}, {"source": "y", "name": "b", "hash": "b"}, {"source": "z", "name": "a", "hash": "a"}]}
    out = W.ranked(recipe)
    assert [m["name"] for m in out["models"]] == ["a", "b", "unmeasured"]
    a, b, u = out["models"]
    assert a["bench"] == {"rank": 1, "covers": [12, 13], "missing": ["1/f noise"], "artefacts": [], "agree": 0.9, "differs_on": 1,
                          "sims": {"qspice": "ok", "ngspice": "ok", "ltspice": "differs"}, "cpu_s": 5.0, "flags": []}
    assert list(a["bench"]["sims"]) == ["qspice", "ngspice", "ltspice"]          # the bench's order, default first
    # a simulator that failed says so, and one never tried is left out
    assert b["bench"]["sims"] == {"qspice": "ok", "ngspice": "failed"}
    assert b["bench"]["flags"] == ["IC ceiling (NK > 1)", "suspect ×1", "ltspice: timeout in switching"] and b["bench"]["covers"] == [10, 13]
    assert u["bench"] == {"rank": 3}
    # what a simulator made of a model is shown, not ranked: a fuller card with an LTspice timeout stays ahead
    cards["b"] = {"family": "gummel-poon", "absent": [], "default": ["NF"], "extensions": ["breakdown"]}
    out = W.ranked(recipe)
    assert [m["name"] for m in out["models"]] == ["b", "a", "unmeasured"]
    assert out["models"][0]["bench"]["defaults"] == ["NF"] and out["models"][0]["bench"]["extensions"] == ["breakdown"]
    assert recipe["models"][0]["name"] == "unmeasured"            # the recipe itself is left alone
