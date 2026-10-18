"""Publishing the characterisation: four significant figures, agreement between engines, nothing of the
card, and a ledger that knows which engines a model has been through."""
import json

from spicy_electronics_index.bench import catalogue as C
from spicy_electronics_index.bench import character as K
from spicy_electronics_index.bench import character_publish as P
from spicy_electronics_index.core import config
from spicy_electronics_index.core.ledger import (
    CHARACTER_FIELDS,
    CHARACTER_STAGES,
    CHARACTER_VERSIONED,
    Ledger,
)


def test_four_significant_figures_through_lists_and_dicts():
    assert P.sig({"a": 1.23456789e-12, "b": [0.123456, None, True], "c": "x"}) == {"a": 1.235e-12, "b": [0.1235, None, True], "c": "x"}


def test_agreement_classes_and_the_odd_engine_out():
    units = {("bjt-x", "cob"): "F"}
    a = P.agree({"qspice": {"hfe@1mA": 100.0}, "ngspice": {"hfe@1mA": 100.5}}, units, "bjt-x")
    assert a[1] == "1%" and a[2] == ["ngspice", "qspice"] and a[3] is None
    a = P.agree({"qspice": {"hfe@1mA": 100.0}, "ngspice": {"hfe@1mA": 104.0}, "ltspice": {"hfe@1mA": 100.2}}, units, "bjt-x")
    assert a[1] == "5%" and a[3] is None
    a = P.agree({"qspice": {"hfe@1mA": 100.0}, "ngspice": {"hfe@1mA": 130.0}, "ltspice": {"hfe@1mA": 100.2}}, units, "bjt-x")
    assert a[1] == ">5%" and a[3] == "ngspice"
    # below the floor of the unit, two values count as equal: a capacitance of 1e-17 F is no capacitance
    a = P.agree({"qspice": {"cob@10V": 1e-17}, "ngspice": {"cob@10V": 5e-17}}, units, "bjt-x")
    assert a[1] == "1%"
    # and a leakage at the solvers' floor is the solvers', whatever the unit table says
    a = P.agree({"qspice": {"icbo@10V": 1e-11}, "ngspice": {"icbo@10V": 2e-11}}, {}, "bjt-breakdown")
    assert a[1] == "1%"
    assert P.agree({"qspice": {"hfe@1mA": 100.0}}, units, "bjt-x") is None


def fake_result(engine, hfe=150.0):
    return {"id": "h1", "engine": engine, "version": "v", "catalogue": C.version(),
            "values": {"bjt-hfe-ic": {"hfe@1mA,5V": hfe, "vbe@1mA,5V": 0.6543219}, "bjt-capacitance": {"cob@10V": 1.98765e-12}},
            "codes": {"bjt-hfe-ic": "ok", "bjt-capacitance": "ok"}, "errors": {},
            "derived": {"ib@1mA": 1e-3 / hfe},
            "curves": {"bjt-hfe-ic": {"hFE, VCE=5V": [None, 123.456789 * hfe / 150, 130.0 * hfe / 150]}, "bjt-switching": {"IC(t), 100mA": [[3.112345e-6, 0.0961234], [3.1e-6, 0.0]]}},
            "decks": {"dc": {"ids": ["bjt-hfe-ic"], "analysis": "dc", "pack": 10, "digest": "abc", "wall_s": 0.1, "cpu_s": 0.05}},
            "error": None}


def fake_job():
    return {"id": "h1", "kind": "bjt", "family": "gummel-poon", "polarity": "npn", "changes": ["renamed"], "parts": ["bjt/QX"]}


def fake_info(engine):
    return {"engine": engine, "image": "sha256:img", "bench": {"commit": "c", "clean": True}, "on": "2026-10-04", "version": "character-1"}


def test_a_record_holds_every_engine_s_numbers_the_primary_s_curves_and_no_card():
    doc = C.load()
    rec = P.build_record("h1", {"qspice": (fake_info("qspice"), fake_result("qspice"), fake_job()),
                               "ngspice": (fake_info("ngspice"), fake_result("ngspice", 151.0), fake_job())}, doc)
    assert rec["values"]["bjt-hfe-ic"]["qspice"]["hfe@1mA,5V"] == 150.0
    assert rec["values"]["bjt-hfe-ic"]["qspice"]["vbe@1mA,5V"] == 0.6543          # four significant figures
    assert rec["values"]["bjt-hfe-ic"]["ngspice"] == {}                             # within 1 % of the primary: not repeated
    assert rec["curves"]["bjt-hfe-ic"]["hFE, VCE=5V"] == [None, 123.5, 130.0]       # read on hover, slopes too: four figures
    assert rec["curves"]["bjt-switching"]["IC(t), 100mA"] == [[3.1123e-6, 0.09612], [3.1e-6, 0.0]]   # a waveform keeps five on its time
    assert rec["agree"]["bjt-hfe-ic"][1] == "1%" and rec["values"]["bjt-agreement"]["all"]["agree_1pct"] == 1.0
    assert rec["codes"]["bjt-agreement"] == "ok" and rec["runs"] == {"qspice": "ok", "ngspice": "ok"}
    assert rec["decks"]["dc"]["qspice"] == {"digest": "abc", "pack": 10} and rec["parts"] == ["bjt/QX"]
    assert rec["primary"] == "qspice"
    far = P.build_record("h1", {"qspice": (fake_info("qspice"), fake_result("qspice"), fake_job()),
                               "ngspice": (fake_info("ngspice"), fake_result("ngspice", 180.0), fake_job())}, doc)
    assert far["values"]["bjt-hfe-ic"]["ngspice"] == {"hfe@1mA,5V": 180.0} and far["agree"]["bjt-hfe-ic"][1] == ">5%"
    assert far["other_curves"] == {"ngspice": {"bjt-hfe-ic": {"hFE, VCE=5V": [None, 148.1, 156.0]}}}   # its curve where it differs
    assert rec["other_curves"] == {}                                                            # none where it agrees within 1 %
    assert not P.curve_differs([1.0, None], [1.0, 2.0]) and not P.curve_differs([1e-17, 1.0], [5e-17, 1.004], floor=1e-16)
    assert P.curve_differs([1.0, 2.0], [1.0, 2.05]) and P.waveform_differs({"tr@100mA": 1.0e-8}, {"tr@100mA": 1.06e-8})
    assert not P.waveform_differs({"tr@100mA": 1.0e-8}, {"tr@100mA": 1.03e-8})
    text = json.dumps(rec)
    assert "card" not in text and ".model" not in text.lower() and "private_" + "material" not in text


def test_a_model_run_in_one_engine_alone_has_no_agreement():
    rec = P.build_record("h1", {"ngspice": (fake_info("ngspice"), fake_result("ngspice"), fake_job())}, C.load())
    assert rec["agree"] == {} and rec["codes"]["bjt-agreement"] == "n/a" and "bjt-agreement" not in rec["values"]


def test_an_amplifiers_agreement_is_the_catalogues_opamp_entry():
    job = {**fake_job(), "kind": "amplifier", "family": "subckt", "polarity": "n"}
    rec = P.build_record("h1", {"ngspice": (fake_info("ngspice"), fake_result("ngspice"), job)}, C.load())
    assert rec["codes"]["opamp-agreement"] == "n/a" and "amplifier-agreement" not in rec["codes"]


def test_the_ledger_knows_which_engines_a_model_has_been_through(tmp_path):
    led = Ledger(tmp_path / "state.csv", stages=CHARACTER_STAGES, fields=CHARACTER_FIELDS, versioned=CHARACTER_VERSIONED)
    dig = "d1"
    assert not K.fresh_for(led, "h1", "qspice", dig)
    led.stamp("h1", "character", version=K.VERSION, character_in=dig, engines="qspice")
    assert K.fresh_for(led, "h1", "qspice", dig) and not K.fresh_for(led, "h1", "ngspice", dig)
    assert not K.fresh_for(led, "h1", "qspice", "d2")                  # the catalogue changed: run again


def test_the_published_tree_is_whitelisted(tmp_path, monkeypatch):
    rec = P.build_record("0123456789abcdef0123456789abcdef01234567",
                         {"qspice": (fake_info("qspice"), fake_result("qspice"), fake_job())}, C.load())
    monkeypatch.setattr(config, "PUBLIC_DATA", tmp_path)
    assert P.write(rec["hash"], rec) and not P.write(rec["hash"], rec)
    p = config.character(rec["hash"])
    assert p.parent.name == "01" and json.loads(p.read_text())["schema"] == 1


def test_the_latest_run_is_the_last_of_the_day_by_number_not_by_alphabet(tmp_path, monkeypatch):
    for name in ("2026-10-05-3", "2026-10-06", "2026-10-06-2", "2026-10-06-9", "2026-10-06-10"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "run.json").write_text("{}")
    monkeypatch.setattr(P, "character_runs", lambda engine: tmp_path)
    assert P.latest_run("qspice").name == "2026-10-06-10"


def test_a_model_takes_its_newest_result_across_the_runs_of_one_catalogue_version(tmp_path, monkeypatch):
    """A rerun of the models a run missed completes it: each model takes its newest result of this version."""
    doc = C.load()
    def run(name, version, hashes, hfe):
        d = tmp_path / name
        d.mkdir()
        (d / "run.json").write_text(json.dumps({**fake_info("qspice"), "catalogue": {"version": version}}))
        (d / "jobs.jsonl").write_text("".join(json.dumps({**fake_job(), "id": h}) + "\n" for h in hashes))
        (d / "results-0.jsonl").write_text("".join(json.dumps({**fake_result("qspice", hfe), "id": h}) + "\n" for h in hashes))
    run("2026-10-06-2", doc["version"], ["h1", "h2"], 150.0)
    run("2026-10-06-10", doc["version"], ["h2"], 160.0)          # the rerun of h2 alone, newer
    run("2026-10-06-11", "m-0", ["h1", "h2"], 999.0)            # another catalogue version: ignored
    monkeypatch.setattr(P, "character_runs", lambda engine: tmp_path if engine == "qspice" else tmp_path / "none")
    written = {}
    monkeypatch.setattr(P, "write", lambda h, rec: written.setdefault(h, rec) is rec)
    monkeypatch.setattr(P, "ledger", lambda: type("L", (), {"stamp": lambda *a, **k: None, "save": lambda self: None})())
    P.publish()
    assert written["h1"]["values"]["bjt-hfe-ic"]["qspice"]["hfe@1mA,5V"] == 150.0
    assert written["h2"]["values"]["bjt-hfe-ic"]["qspice"]["hfe@1mA,5V"] == 160.0


def test_a_record_keeps_the_tracer_families_in_range_and_the_first_supply_s_waveforms():
    flat = [0.0] * 28
    curves = {"bjt-tracer": {**{f"IC, step {k}, auto": [1e-3 * k] * 28 for k in range(1, 6)},
                             **{f"IC, step {k}, IB step=1µA": [1e-7 * k] * 28 for k in range(1, 6)},       # top trace 0.5 µA: noise floor
                             **{f"IC, step {k}, IB step=1mA": [0.1 * k] * 28 for k in range(1, 6)},        # top trace 0.5 A: kept
                             **{f"IC, step {k}, IB step=100mA": [10.0 * k] * 28 for k in range(1, 6)}},    # top trace 50 A: beyond any part
              "bjt-switching": {"IC(t), 100mA": [[0.0, 0.0]], "IC(t), 100mA, VCC=30V": [[0.0, 0.0]], "ts": flat}}
    got = P.trim_curves(curves)
    fams = {n.split(", ")[-1] for n in got["bjt-tracer"]}
    assert fams == {"auto", "IB step=1mA"} and len(got["bjt-tracer"]) == 10
    assert set(got["bjt-switching"]) == {"IC(t), 100mA", "ts"}
