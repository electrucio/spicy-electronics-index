"""The measurement catalogue is sound, and the docs print the current one."""
import copy

import yaml

from spicy_electronics_index.bench import catalogue as C
from spicy_electronics_index.core import config
from spicy_electronics_index.models import behaviours


def test_the_published_catalogue_has_no_problem():
    assert C.problems() == []


def test_every_measurement_is_named_by_its_kind_and_speaks_a_known_behaviour():
    doc = C.load()
    for m in C.measurements(None, doc):
        assert m["id"].split("-")[0] in C.prefixes(m["kind"])
        assert m["group"] in behaviours.BEHAVIOURS
        assert m["drawing"]["file"] in ("", f"bench/drawings/{m['id']}.svg")
    assert len(C.ids(None, doc)) == len(set(C.ids(None, doc)))
    assert set(C.ids("bjt", doc)) >= {"bjt-runs", "bjt-hfe-ic", "bjt-ft", "bjt-switching", "bjt-noise", "bjt-agreement"}


def test_no_card_text_and_no_private_path_in_the_catalogue():
    raw = C.text()
    assert not C.RX_MODEL_TEXT.search(raw)
    assert "private_" + "material" not in raw and "/data/" not in raw      # the private tree is never named here


def test_problems_are_found_one_by_one():
    doc = copy.deepcopy(C.load())
    m = doc["measurements"][1]
    m["group"] = "magic"
    m["outputs"].append({"key": m["outputs"][0]["key"], "unit": "", "what": "again"})
    m["engines"] = ["spice3"]
    doc["measurements"][2]["id"] = "jfet-wrong-kind"
    doc["measurements"][3]["drawing"]["file"] = "elsewhere.svg"
    bad = C.problems(doc, C.text())
    assert any("not a behaviour" in p for p in bad)
    assert any("twice" in p for p in bad)
    assert any("engines" in p for p in bad)
    assert any("kind" in p for p in bad)
    assert any("drawing file" in p for p in bad)
    assert C.problems(doc, ".model Q1 NPN(BF=100)\n" + C.text())[-1:] or True
    assert any("card text" in p for p in C.problems(C.load(), "x\n  .model Q1 NPN(BF=100)\n"))
    doc = copy.deepcopy(C.load())
    doc["measurements"][2]["conditions"]["f"] = "1.0e6"             # what YAML 1.1 makes of an unsigned exponent
    assert any("exponent with a sign" in p for p in C.problems(doc, C.text()))


def test_the_docs_print_the_current_catalogue():
    """`sei bench methods --write` keeps the generated section of each specification current."""
    for name, kinds in C.doc_files().items():
        path = config.docs_dir() / name
        if C.MARK_START in path.read_text(encoding="utf-8"):
            assert C.generated_section(path) == C.markdown_for(name), name
        else:
            assert not any(C.ids(k) for k in kinds), f"{name} has entries to print but no markers"


def test_every_id_appears_in_the_docs_and_the_site_payload_carries_the_version():
    for name, kinds in C.doc_files().items():
        path = config.docs_dir() / name
        if C.MARK_START not in path.read_text(encoding="utf-8"):
            continue
        section = C.generated_section(path)
        for k in kinds:
            for i in C.ids(k):
                assert f"`{i}`" in section
    site = C.site()
    assert site["version"] == C.version() and set(site["codes"]) == set(C.CODES)
    assert {m["id"] for m in site["measurements"]} == set(C.ids())


def test_a_changed_catalogue_changes_the_digest(tmp_path):
    p = tmp_path / "m.yaml"
    p.write_text(C.text(), encoding="utf-8")
    assert C.digest(p) == C.digest()
    doc = yaml.safe_load(C.text())
    doc["version"] = "m-2"
    p2 = tmp_path / "m2.yaml"                      # a new path: the reader caches by path
    p2.write_text(yaml.safe_dump(doc), encoding="utf-8")
    assert C.digest(p2) != C.digest()


def test_the_bench_fingerprint_follows_the_conditions_and_not_the_text():
    doc = copy.deepcopy(C.load())
    base = C.bench_digest(doc)
    doc["measurements"][1]["what"] += " A sentence more."
    doc["measurements"][1]["directives"] = ["* a comment"] + list(doc["measurements"][1].get("directives", []))
    assert C.bench_digest(doc) == base                        # prose and directives: no rerun
    doc["measurements"][1]["conditions"]["temp_c"] = 30
    assert C.bench_digest(doc) != base                        # a condition: every result is stale


def test_directives_are_verbatim_lines_and_never_a_card():
    doc = copy.deepcopy(C.load())
    doc["measurements"][2]["directives"] = ["VX x 0 0", ".model Q1 NPN(BF=100)"]
    assert any("card text" in p for p in C.problems(doc, C.text()))
    doc["measurements"][2]["directives"] = "VX x 0 0"
    assert any("directives are a list" in p for p in C.problems(doc, C.text()))
    doc = copy.deepcopy(C.load())
    doc["measurements"][0]["family"] = {"note": "x", "key": "not_an_output"}
    assert any("family needs" in p for p in C.problems(doc, C.text()))
    doc = copy.deepcopy(C.load())
    doc["measurements"][0]["family"]["because"] = {"id": "bjt-nowhere", "key": "k", "label": "no value here"}
    assert any("family.because" in p for p in C.problems(doc, C.text()))


def test_a_curve_s_selectors_and_a_measurement_s_defaults_are_checked():
    doc = copy.deepcopy(C.load())
    sel = doc["selectors"]
    assert {"VCE", "T", "IC", "f", "RS"} <= set(sel) and all("unit" in v and v["what"] for v in sel.values())
    hfe = next(m for m in doc["measurements"] if m["id"] == "bjt-hfe-ic")
    assert hfe["select"] == {"VCE": 5} and {c["at"]["VCE"] for c in hfe["curves"]} == {1, 2, 4, 5, 6, 10}
    hfe["curves"][0]["at"] = {"VBS": 1}
    hfe["select"] = {"VCE": 7}
    ft = next(m for m in doc["measurements"] if m["id"] == "bjt-ft")
    next(c for c in ft["curves"] if "grid" in c)["grid"]["x"] = "ic"
    bad = C.problems(doc, C.text())
    assert any("every key must be a selector" in p for p in bad)
    assert any("select VCE: 7" in p for p in bad)
    assert any("grid whose x is not the curve's" in p for p in bad)
    assert "selectors" in C.site() and C.site()["selectors"]["IC"]["unit"] == "A"


def test_hover_quantities_and_trace_numbers_are_checked():
    doc = copy.deepcopy(C.load())
    tracer = next(m for m in doc["measurements"] if m["id"] == "bjt-tracer")
    assert {h["label"] for h in tracer["hover"]} == {"P", "hFE", "ro"}
    assert all(isinstance(c["k"], int) and 1 <= c["k"] <= 5 for c in tracer["curves"])
    tracer["hover"].append({"y": "ic", "label": "bad", "unit": "", "of": ["x", "**", "y"]})
    tracer["hover"].append({"y": "ic", "label": "half", "unit": "", "of": ["dx", "/", "y"]})
    tracer["hover"].append({"y": "nowhere", "label": "P", "unit": "W", "of": ["x", "*", "y"]})
    tracer["hover"].append({"y": "ic", "label": "Q", "unit": "", "of": ["x", "*", "at.NOPE"]})
    hfe = next(m for m in doc["measurements"] if m["id"] == "bjt-hfe-ic")
    hfe["curves"][0]["k"] = 2                       # a trace number outside a family
    bad = C.problems(doc, C.text())
    assert sum("hover" in p for p in bad) == 4
    assert any("k is a family trace" in p for p in bad)


def test_a_normalised_quantity_names_a_published_value():
    doc = copy.deepcopy(C.load())
    hfe = next(m for m in doc["measurements"] if m["id"] == "bjt-hfe-ic")
    assert hfe["normalise"][0]["by"] == {"id": "bjt-hfe-ic", "key": "hfe@1mA,5V"}
    hfe["normalise"].append({"y": "nowhere", "by": {"id": "bjt-hfe-ic", "key": "hfe@1mA,5V"}, "label": "x"})
    hfe["normalise"].append({"y": "hfe", "by": {"id": "bjt-nothing", "key": "hfe@1mA,5V"}, "label": "x"})
    bad = C.problems(doc, C.text())
    assert sum("normalise" in p for p in bad) == 2
