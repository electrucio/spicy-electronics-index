"""The decks inside the simulator images: they cover the catalogue, write the same text every time, and
read numbers the way the catalogue says. Imported from the checkout, as the images mount them."""
import hashlib
import math
import os
import sys

import pytest

from spicy_electronics_index.bench import catalogue as C
from spicy_electronics_index.core import config

os.environ.setdefault("SIM_ENGINE", "ngspice")
sys.path.insert(0, str(config.sim_bench().parent))
from bench import character as incar  # noqa: E402
from bench import decks_bjt, num  # noqa: E402

CAT = {m["id"]: m for m in C.measurements()}


def test_every_bipolar_measurement_has_a_deck_or_is_derived():
    served = {i for d in decks_bjt.plan(CAT, "qspice") for i in d.ids}
    derived = {i for i, m in CAT.items() if m["analysis"] == "derived"}
    assert set(C.ids("bjt")) - derived == served
    assert "bjt-agreement" in derived


def test_an_engine_only_runs_the_decks_of_the_measurements_it_is_listed_for():
    lt = {i for d in decks_bjt.plan(CAT, "ltspice") for i in d.ids}
    assert "bjt-noise" not in lt and "bjt-distortion" not in lt and "bjt-ft" in lt


def test_the_same_job_gives_the_same_deck_text_and_digest():
    deck = decks_bjt.DcMain(CAT)
    a = incar.deck_text(deck, [("DUT", 1, "", {})], "model.lib", "ngspice")
    b = incar.deck_text(deck, [("DUT", 1, "", {})], "model.lib", "ngspice")
    assert a == b and a.startswith("* character dc\n.include \"model.lib\"\n")
    assert incar.digest(a) == hashlib.sha256(a.encode()).hexdigest()
    pnp = incar.deck_text(deck, [("DUT", -1, "", {})], "model.lib", "ngspice")
    assert pnp != a and pnp.count("I=-exp") == a.count("I=exp") and "VH1 ch1 0 -5" in pnp


def test_a_packed_deck_renames_the_copies_and_keeps_one_sweep():
    deck = decks_bjt.DcMain(CAT)
    text = incar.deck_text(deck, [("DUT0", 1, "_0", {}), ("DUT1", 1, "_1", {})], "models.lib", "qspice")
    assert text.count(".dc VX") == 1 and "QG_0 cg_0 bg_0 0 DUT0" in text and "QG_1 cg_1 bg_1 0 DUT1" in text
    assert ".save" in text and text.count(".save") == 2


def test_decks_that_need_the_operating_point_wait_for_it():
    assert not decks_bjt.Early(CAT).ready({}) and not decks_bjt.Ft(CAT).ready({})
    assert decks_bjt.Early(CAT).ready({"ib@1mA": 1e-5})
    noise = decks_bjt.Noise(CAT, 1e-3, 0)
    assert not noise.ready({"ib@1mA": 1e-5}) and noise.ready({"ib@1mA": 1e-5, "vbe@1mA": 0.65})
    assert not decks_bjt.Thd(CAT).ready({}) and decks_bjt.Thd(CAT).ready({"thd_gain": 17.0})


def test_every_transient_has_a_time_step_above_zero_and_ltspice_gets_its_options():
    for deck in decks_bjt.plan(CAT, "ltspice"):
        text = incar.deck_text(deck, [("DUT", 1, "", {"ib@1mA": 1e-5, "vbe@1mA": 0.65, "ib@100mA": 1e-3, "thd_gain": 17.0})],
                               "model.lib", "ltspice")
        assert ".options plotwinsize=0 numdgt=15" in text
        for line in text.splitlines():
            if line.startswith(".tran"):
                assert float(line.split()[1]) > 0, line


def test_output_keys_follow_the_catalogue_spelling():
    assert num.si(1e-3, "A") == "1mA" and num.si(0.5, "V") == "500mV" and num.si(1e5, "Hz") == "100kHz"
    assert num.si(1e-4, "A") == "100µA" and num.si(10, "A") == "10A" and num.si(1e5, "Ω") == "100kΩ"


def test_the_arithmetic_the_decks_share():
    assert num.log_interp([1, 10, 100], [0, 1, 2], 31.622776601683793) == pytest.approx(1.5)
    assert num.loglog_interp([1, 10], [10, 1000], 3.1622776601683795) == pytest.approx(100)
    assert num.crossing([0, 1, 2, 3], [0, 0, 1, 1], 0.5, 0, True) == pytest.approx(1.5)
    assert num.grid_points({"from": 1e-6, "to": 1e-3, "per_decade": 1}) == pytest.approx([1e-6, 1e-5, 1e-4, 1e-3])
    assert num.grid_points({"values": [1, 2]}) == [1, 2] and len(num.grid_points({"from": 0.5, "to": 30, "step": 0.5})) == 60
    xs = [i / 1000 for i in range(1000)]
    ys = [0.0 if x < 0.5 else 1.0 for x in xs]
    thinned = num.thin(xs, ys, 60)
    assert len(thinned) <= 60 and thinned[0] == [0.0, 0.0] and any(abs(p[0] - 0.5) < 0.002 for p in thinned)
    samples = [math.sin(2 * math.pi * 4 * i / 4096) * 0.7 for i in range(4096)]
    assert num.goertzel(samples, 4) == pytest.approx(0.7, rel=1e-6) and num.goertzel(samples, 8) < 1e-9


def test_the_gummel_plot_reads_the_base_current_as_source_minus_collector():
    deck = decks_bjt.DcMain(CAT)
    isrc = [10 ** (-9 + 0.05 * i) for i in range(181)]
    vbe = [0.0592 * math.log10(0.99 * s / 1e-14) for s in isrc]           # an ideal diode with IS = 1e-14
    ic = [0.99 * s for s in isrc]                                           # hFE = 99 throughout
    vals, curves, code = deck.gummel(isrc, ic, vbe)
    assert code == "ok" and vals["hfe_peak"] == pytest.approx(99, rel=1e-6)
    assert vals["n_fit"] == pytest.approx(0.0592 / num.DECADE_MV_25, rel=1e-3)
    assert vals["is_fit"] == pytest.approx(1e-14, rel=0.02)
    assert len(curves["IC"]) == len(curves["IB"]) == len(num.grid_points(CAT["bjt-gummel"]["grid"]))
    k = num.grid_points(CAT["bjt-gummel"]["grid"]).index(0.5)
    assert curves["IC"][k] == pytest.approx(1e-14 * 10 ** (0.5 / 0.0592), rel=0.02)   # the diode line, read at VBE = 0.5 V


# the derived points a deck may ask for, as any real model gives them (the lines the catalogue quotes
# never carry one of these numbers)
DERIVED = {"ib@30µA": 1.4e-7, "ib@300µA": 1.3e-6, "ib@3mA": 1.3e-5, "vbe@10µA": 0.5, "vbe@30µA": 0.53, "vbe@300µA": 0.65, "vbe@3mA": 0.71, "ib@1µA": 1e-8, "ib@10µA": 5e-8, "ib@100µA": 4.435e-07, "ib@1mA": 4.449e-06, "ib@10mA": 4.578e-05,
           "ib@100mA": 1e-3, "ib@1A": 0.1, "ib@10A": 1.0, "vbe@100µA": 0.6207, "vbe@1mA": 0.68, "vbe@10mA": 0.7405,
           "ic_at_hfe_peak": 0.02, "ic_max_converged": 1.0, "thd_gain": 17.16}


def test_the_catalogue_quotes_its_decks_verbatim():
    """Every directive line the method page shows is a line of the QSPICE deck of that measurement."""
    texts: dict[str, list[str]] = {}
    for deck in decks_bjt.plan(CAT, "qspice"):
        text = incar.deck_text(deck, [("DUT", 1, "", DERIVED)], "model.lib", "qspice")
        for mid in deck.ids:
            texts.setdefault(mid, []).append(text)
    quoted = 0
    for mid, m in CAT.items():
        if m["kind"] != "bjt":
            continue                                 # the other kinds: test_character_decks_kinds.py
        for line in m.get("directives") or []:
            if line.startswith("*"):
                continue
            assert any(f"\n{line}\n" in t for t in texts.get(mid, [])), f"{mid}: {line!r} is not in its deck"
            quoted += 1
    assert quoted > 60


def test_a_collector_current_with_a_ceiling_is_cut_at_its_peak():
    """A card with NK > 1 has IC rise, peak and fall as the drive grows, at the same current whatever VCE: the
    decks keep the rising branch and publish the peak. A peak that moves with VCE, or shows at 5 V only, is the
    transistor saturated through its own resistances by an absurd drive, and is cut but not published."""
    assert num.until_peak([1.0, 2.0, 3.0, 2.5, 2.0]) == 3
    assert num.until_peak([1.0, 2.0, 3.0]) == 3
    assert num.until_peak([1.0, 2.0, 3.0, 2.995]) == 4        # a wobble under 1 % is not a ceiling
    deck = decks_bjt.DcMain(CAT)
    ib = [10 ** (-9 + 0.05 * i) for i in range(181)]
    ic_up = [100 * b for b in ib]
    vb = [0.6 + 0.06 * math.log10(c / 1e-3) for c in ic_up]
    vbs = {5.0: vb, 1.0: vb, 10.0: vb}

    def ceiling(k):
        return ic_up[:k] + [ic_up[k - 1] * (1 - 0.02 * (j + 1)) for j in range(len(ib) - k)]

    text = incar.deck_text(deck, [("DUT", 1, "", {})], "model.lib", "qspice")
    assert "VH1 ch1 0 5" in text and "VH3 ch3 0 2" in text and "VH5 ch5 0 6" in text
    vals, cur, code, _ = deck.hfe(ib, {5.0: ceiling(150), 1.0: ceiling(150), 10.0: ceiling(150)}, vbs, 5.0)
    assert code == "ok" and vals["ic_peak"] == pytest.approx(ic_up[149])
    assert "VBE, VCE=1V" in cur and "VBE, VCE=10V" in cur and "hFE, VCE=5V" in cur
    vals2, _, _, _ = deck.hfe(ib, {5.0: ic_up, 1.0: ic_up, 10.0: ic_up}, vbs, 5.0)
    assert "ic_peak" not in vals2
    vals3, cur3, _, _ = deck.hfe(ib, {5.0: ceiling(150), 1.0: ceiling(140), 10.0: ic_up}, vbs, 5.0)   # at 10 V it keeps rising
    assert "ic_peak" not in vals3 and cur3["hFE, VCE=5V"] == cur["hFE, VCE=5V"]
    vals4, _, _, _ = deck.hfe(ib, {5.0: ceiling(150), 1.0: ceiling(140), 10.0: ceiling(165)}, vbs, 5.0)   # it moves with VCE
    assert "ic_peak" not in vals4


def test_a_saturation_step_counts_only_when_the_collector_sits_below_the_base():
    deck = decks_bjt.DcMain(CAT)
    ib = [10 ** (-8 + 0.05 * i) for i in range(161)]
    vbs = [0.75] * len(ib)
    # saturated to 100 mA of forced IC (VCE 0.1 V), then the transistor cannot pass the current: VCE climbs to 20 V
    vcs = [0.1 if 10 * b <= 0.1 else 20.0 for b in ib]
    vals, cur, code = decks_bjt.saturation(CAT, ib, vcs, vbs, 10.0, deck.clamp)
    assert code == "ok" and "vcesat@100mA,10" in vals and "vcesat@1A,10" not in vals and "rce_sat" in vals
    assert set(cur) == {"VCE(sat), IC/IB=10", "VBE(sat), IC/IB=10"}
    vals20, _, _ = decks_bjt.saturation(CAT, ib, vcs, vbs, 20.0, deck.clamp, summary=False)
    assert "vcesat@100mA,20" in vals20 and "rce_sat" not in vals20
    text = incar.deck_text(deck, [("DUT", 1, "", {})], "model.lib", "qspice")
    assert "BSC 0 cs I=10*exp" in text and "BSC20 0 cs20 I=20*exp" in text and "QS50 cs50 bs50 0 DUT" in text


def test_the_ft_deck_keeps_the_gain_against_frequency_and_the_beta_cut_off():
    deck = decks_bjt.Ft(CAT)
    fr = [10 ** (3 + i / 20) for i in range(161)]            # 1 kHz to 100 GHz
    hfe, fb = 200.0, 1e6                                      # a one-pole gain: 200 flat, −3 dB at 1 MHz, fT = 200 MHz
    h = [hfe / math.sqrt(1 + (f / fb) ** 2) for f in fr]
    d = {"frequency": fr}
    for i in range(len(deck.ladder)):
        d[f"i(vct{i})"] = h
        d[f"i(vcu{i})"] = [v * 1.1 for v in h]        # at 10 V the gain is a tenth higher
    derived = {f"ib@{si}": 1e-5 for si in ("100µA", "1mA", "10mA", "100mA", "1A", "10A")}
    values, curves, codes, _ = deck.measure(d, 1, "", derived)
    assert values["bjt-ft"]["f_beta@1mA,5V"] == pytest.approx(fb, rel=0.05)
    assert values["bjt-ft"]["ft@1mA,5V"] == pytest.approx(hfe * fb, rel=0.1)
    assert values["bjt-ft"]["ft@1mA,10V"] == pytest.approx(1.1 * hfe * fb, rel=0.1)
    assert values["bjt-hfe-ac"]["hfe_ac@1mA,10V"] == pytest.approx(1.1 * hfe, rel=1e-3)
    grid = num.grid_points(decks_bjt.curve_grid(CAT, "bjt-ft", "|hfe|, 1mA, VCE=5V"))
    assert len(curves["bjt-ft"]["|hfe|, 1mA, VCE=5V"]) == len(grid) and curves["bjt-ft"]["|hfe|, 1mA, VCE=5V"][0] == pytest.approx(hfe, rel=1e-3)
    assert {c["name"] for c in CAT["bjt-ft"]["curves"]} <= set(curves["bjt-ft"])
    assert {c["name"] for c in CAT["bjt-hfe-ac"]["curves"]} <= set(curves["bjt-hfe-ac"])
    text = incar.deck_text(deck, [("DUT", 1, "", derived)], "model.lib", "qspice")
    assert "VCT0 ct0 0 5" in text and "VCU0 cu0 0 10" in text and "QU5 cu5 bu5 0 DUT" in text


def test_finalize_derives_the_curves_the_catalogue_names():
    """The temperature slopes, the switching times against current and the noise curves come from several
    decks; `finalize` names them exactly as the catalogue does."""
    cat = CAT
    gt = num.grid_points(cat["bjt-temperature"]["grid"])
    vb25 = [0.65 - 0.002 * 0 for _ in gt]
    curves = {"bjt-temperature": {"VBE, −55°C": [v + 0.16 for v in vb25], "VBE, 25°C": vb25, "VBE, 125°C": [v - 0.2 for v in vb25],
                                  "VBE, 150°C": [v - 0.25 for v in vb25], "VBE, 100°C": [v - 0.15 for v in vb25]}}
    values = {"bjt-switching": {"td@10mA,10V,3µs": 1e-9, "td@100mA,10V,3µs": 2e-9, "ts@100mA,10V,3µs": 5e-7, "ts@100mA,30V,3µs": 6e-7,
                                "ts@100mA,10V,100µs": 9e-7}}
    f = [10 ** (i / 20) for i in range(121)]
    en = [2e-9 * math.sqrt(1 + 100 / x) for x in f]
    tot = [math.sqrt(e * e + (1e-12 * 1e5) ** 2 + 4 * num.K_B * num.T_K * 1e5) for e in en]
    derived = {"_noise@1mA@0": [f, en], "_noise@1mA@100kΩ": [f, tot], "_noise@100µA@0": [f, en],
               "_hfe25@1mA": 100.0, "_hfe125@1mA": 140.0, "_hfe150@1mA": 150.0, "_hfe-55@1mA": 70.0, "_vbe150@1mA": 0.4, "_vbe-55@1mA": 0.81}
    decks_bjt.finalize(cat, values, curves, derived)
    tc = curves["bjt-temperature"]
    assert tc["dVBE/dT, −55 to 25°C"][0] == pytest.approx(-0.16 / 80) and tc["dVBE/dT, 25 to 100°C"][0] == pytest.approx(-0.15 / 75)
    assert tc["dVBE/dT, 100 to 125°C"][0] == pytest.approx(-0.05 / 25)
    assert tc["dVBE/dT, 125 to 150°C"][0] == pytest.approx(-0.05 / 25)
    tv = values["bjt-temperature"]
    assert tv["hfe_150_over_25@1mA"] == 1.5 and tv["hfe_125_over_25@1mA"] == 1.4 and tv["hfe_m55_over_25@1mA"] == 0.7
    assert tv["dvbe_dt@1mA"] == pytest.approx((0.4 - 0.81) / 205)
    sw_ics = CAT["bjt-switching"]["conditions"]["ic_ladder"]
    assert curves["bjt-switching"]["td"][sw_ics.index(1e-2)] == 1e-9 and curves["bjt-switching"]["ts"][sw_ics.index(1e-1)] == 5e-7
    assert curves["bjt-switching"]["ts, VCC=30V"][sw_ics.index(1e-1)] == 6e-7 and len(curves["bjt-switching"]["td"]) == len(sw_ics)
    assert curves["bjt-switching"]["ts, 100µs"][sw_ics.index(1e-1)] == 9e-7
    nc = curves["bjt-noise"]
    assert "en, 1mA" in nc and "in, 1mA" in nc and "en, 100µA" in nc and "in, 100µA" not in nc
    assert "NF wideband, 1mA" in nc and "VT wideband, 1mA" in nc and "NF wideband, 100µA" not in nc
    assert values["bjt-noise"]["nf_wide@1mA,1k"] > 0
    ics = [c for c in CAT["bjt-noise"]["conditions"]["ic_ladder"]]
    assert nc["en at 1kHz"][ics.index(1e-4)] is not None and nc["en at 1kHz"][ics.index(1e-2)] is None
    rs = num.grid_points(decks_bjt.curve_grid(cat, "bjt-noise", "NF, 1mA"))
    assert len(nc["NF, 1mA"]) == len(rs) == len(nc["VT, 1mA"])
    assert min(nc["NF, 1mA"]) == pytest.approx(min(10 * math.log10((2e-9 ** 2 + (1e-12 * r) ** 2 + 4 * num.K_B * num.T_K * r) / (4 * num.K_B * num.T_K * r)) for r in rs), rel=0.05)
    named = {c["name"] for c in cat["bjt-noise"]["curves"]} | {c["name"] for c in cat["bjt-temperature"]["curves"]} | {c["name"] for c in cat["bjt-switching"]["curves"]}
    produced = set(nc) | set(tc) | set(curves["bjt-switching"])
    assert produced <= named


def test_a_sweep_the_simulator_stopped_early_is_refused():
    """A copy that will not converge spoils every copy of its pack, and the simulator may exit 0 with three
    points: the measurement refuses them, so that the pack is run one model at a time."""
    assert decks_bjt.sweep_points({"from": 1e-9, "to": 1, "per_decade": 20}) == 181
    assert decks_bjt.step_points({"from": 0, "to": 10, "step": 0.02}) == 501
    with pytest.raises(RuntimeError, match="stopped at 3 of 181"):
        decks_bjt.DcMain(CAT).measure({"v(x)": [-9, -8.95, -8.9]}, 1, "", {})
    with pytest.raises(RuntimeError, match="stopped"):
        decks_bjt.Temp(CAT, -55).measure({"v(x)": [-9, -8.95, -8.9]}, 1, "", {})
    assert len(decks_bjt.whole({"v(sw)": [0.0] * 500}, "V(sw)", 501)) == 500      # one point short is a rounding


def test_the_saturation_region_deck_reads_vce_against_base_current_at_fixed_collector_currents():
    deck = decks_bjt.VceIb(CAT)
    text = incar.deck_text(deck, [("DUT", 1, "", {})], "model.lib", "qspice")
    assert "IV0 0 cv0 0.001" in text and "IV3 0 cv3 1" in text and "QV2 cv2 bv2 0 DUT" in text and ".model DCLMP" in text
    ib = [10 ** (-9 + 0.05 * i) for i in range(181)]
    d = {"v(x)": [-9 + 0.05 * i for i in range(181)]}
    for k, ic in enumerate(deck.ladder):
        # the collector sits at the clamp until IB reaches IC/100, then falls as 0.1 V plus a tail
        d[f"v(cv{k})"] = [30.0 if b < ic / 100 else 0.1 + 2.0 * (ic / 100) / b for b in ib]
    values, curves, codes, _ = deck.measure(d, 1, "", {})
    assert codes["bjt-vce-ib"] == "ok" and set(curves["bjt-vce-ib"]) == {c["name"] for c in CAT["bjt-vce-ib"]["curves"]}
    assert values["bjt-vce-ib"]["ib_edge@10mA"] == pytest.approx(2.0 * 1e-4 / 0.9, rel=0.1)
    grid = num.grid_points(CAT["bjt-vce-ib"]["grid"])
    vce = curves["bjt-vce-ib"]["VCE, IC=1mA"]
    assert len(vce) == len(grid) and vce[0] is None and vce[-1] == pytest.approx(0.1, abs=0.01)


def test_the_curve_tracer_runs_one_family_per_universal_step_and_the_auto_one():
    deck = decks_bjt.Tracer(CAT)
    assert deck.ready({})                                         # the universal families need no operating point
    text = incar.deck_text(deck, [("DUT", 1, "", DERIVED)], "model.lib", "qspice")
    assert "QK1 ck1 bk1 0 DUT" in text and "IU11 0 bu11 1e-06" in text and "IU165 0 bu165 0.5" in text and "QU165 cu165 bu165 0 DUT" in text
    assert "IK5 0 bk5 " in text and incar.deck_text(deck, [("DUT", 1, "", {})], "model.lib", "qspice").count("QK") == 0
    pts = decks_bjt.step_points(deck.sw)
    d = {"v(sw)": [0.02 * i for i in range(pts)]}
    for k in range(1, 6):
        d[f"i(vk{k})"] = [min(vv * 50, 1.0) * k * 1e-3 for vv in d["v(sw)"]]
        for j in range(1, len(deck.steps) + 1):
            d[f"i(vu{j}{k})"] = [min(vv * 50, 1.0) * k * deck.steps[j - 1] * 100 for vv in d["v(sw)"]]
    values, curves, codes, _ = deck.measure(d, 1, "", DERIVED)
    assert codes["bjt-tracer"] == "ok" and set(curves["bjt-tracer"]) == {c["name"] for c in CAT["bjt-tracer"]["curves"]}
    assert curves["bjt-tracer"]["IC, step 5, IB step=1mA"][-1] == pytest.approx(0.5)
    assert values["bjt-tracer"]["ic@10V,step5"] == pytest.approx(5e-3)


def test_every_quoted_line_has_its_pnp_twin_in_the_pnp_deck():
    """The dialog of a PNP part shows the PNP deck: every quoted line maps to the line in its place, and the
    sources carry the opposite sign."""
    from spicy_electronics_index.bench.deck import pnp_directives
    for mid, m in CAT.items():
        npn = [x for x in m.get("directives") or [] if not x.startswith("*")]
        if not npn or m["kind"] != "bjt":
            continue
        pnp = [x for x in pnp_directives(m) if not x.startswith("*")]
        texts = [incar.deck_text(d, [("DUT", -1, "", DERIVED)], "model.lib", "qspice") for d in decks_bjt.plan(CAT, "qspice") if mid in d.ids]
        for line in pnp:
            assert any(f"\n{line}\n" in t for t in texts), f"{mid}: {line!r} is not in its PNP deck"
    hfe = pnp_directives(CAT["bjt-hfe-ic"])
    assert "VH1 ch1 0 -5" in hfe and "BH1 0 bh1 I=-exp(2.302585092994046*V(x))" in hfe and "QH1 ch1 bh1 0 DUT" in hfe
    sat = pnp_directives(CAT["bjt-saturation"])
    assert "DCL cl cs DCLMP" in sat and "VCL cl 0 -30" in sat


def test_ic_against_vbe_ft_at_a_fixed_frequency_and_the_on_voltages():
    deck = decks_bjt.DcMain(CAT)
    ib = [10 ** (-9 + 0.05 * i) for i in range(181)]
    ic = [100 * b for b in ib]
    vb = [0.6 + 0.06 * math.log10(c / 1e-3) for c in ic]
    vals, cur, _, _ = deck.hfe(ib, {5.0: ic, 1.0: ic, 10.0: ic}, {5.0: vb, 1.0: vb, 10.0: vb}, 5.0)
    g = num.grid_points(decks_bjt.curve_grid(CAT, "bjt-hfe-ic", "IC, VCE=5V"))
    k = g.index(0.6) if 0.6 in g else min(range(len(g)), key=lambda j: abs(g[j] - 0.6))
    assert len(cur["IC, VCE=5V"]) == len(g) and cur["IC, VCE=5V"][k] == pytest.approx(1e-3, rel=0.02)   # 1 mA at 0.6 V
    ft = decks_bjt.Ft(CAT)
    fr = [10 ** (3 + i / 20) for i in range(161)]
    h = [200.0 / math.sqrt(1 + (f / 1e6) ** 2) for f in fr]                # fT = 200 MHz, f_beta = 1 MHz
    d = {"frequency": fr, **{f"i(vct{i})": h for i in range(6)}, **{f"i(vcu{i})": h for i in range(6)}}
    values, curves, _, _ = ft.measure(d, 1, "", {f"ib@{x}": 1e-5 for x in ("100µA", "1mA", "10mA", "100mA", "1A", "10A")})
    assert values["bjt-ft"]["ft_at@1mA,5V,100MHz"] == pytest.approx(200e6, rel=0.02)
    assert values["bjt-ft"]["ft_at@1mA,5V,20MHz"] == pytest.approx(200e6, rel=0.02)
    assert values["bjt-ft"]["ft_at@1mA,5V,1MHz"] is None              # at the beta cut-off: not the sheets' reading
    assert {"fT at 20MHz, VCE=5V", "fT at 100MHz, VCE=10V", "fT at 1MHz, VCE=5V"} <= set(curves["bjt-ft"])
    # a slow power part: fT = 2.5 MHz, a capacitive floor at |hfe| = 0.3; at 100 MHz the product means nothing
    hp = [max(50.0 / math.sqrt(1 + (f / 5e4) ** 2), 0.3) for f in fr]
    dp = {"frequency": fr, **{f"i(vct{i})": hp for i in range(6)}, **{f"i(vcu{i})": hp for i in range(6)}}
    vp, _, _, _ = ft.measure(dp, 1, "", {f"ib@{x}": 1e-5 for x in ("100µA", "1mA", "10mA", "100mA", "1A", "10A")})
    assert vp["bjt-ft"]["ft_at@1mA,5V,1MHz"] == pytest.approx(2.5e6, rel=0.05) and vp["bjt-ft"]["ft_at@1mA,5V,100MHz"] is None
    sat_g = num.grid_points(CAT["bjt-saturation"]["grid"])
    curves2 = {"bjt-hfe-ic": {"VBE, VCE=5V": [0.6 + 0.01 * j for j in range(len(num.grid_points(CAT["bjt-hfe-ic"]["grid"])))]},
               "bjt-saturation": {"VBE(sat), IC/IB=10": [0.7] * len(sat_g), "VCE(sat), IC/IB=10": [0.05] * len(sat_g)}}
    values2 = {"bjt-saturation": {"vbesat@1mA,10": 0.72}, "bjt-hfe-ic": {"vbe@1mA,5V": 0.65}}
    decks_bjt.finalize(CAT, values2, curves2, {})
    ov = curves2["bjt-on-voltages"]
    assert set(ov) == {c["name"] for c in CAT["bjt-on-voltages"]["curves"]}
    assert len(ov["VBE(on), VCE=5V"]) == len(sat_g) and ov["VBE(on), VCE=5V"][0] == pytest.approx(0.6 + 0.01 * 10)   # 100 µA: the 11th point of the hFE grid
    assert values2["bjt-on-voltages"]["vbe_sat_rise@1mA"] == pytest.approx(0.07)


def test_the_switching_decks_run_every_current_from_both_supplies_at_every_pulse_and_keep_the_quoted_names():
    decks = [d for d in decks_bjt.plan(CAT, "qspice") if isinstance(d, decks_bjt.Switching)]
    c = CAT["bjt-switching"]["conditions"]
    assert len(decks) == len(c["ic_ladder"]) * len(c["vcc"]) * len(c["pulses"])
    names = {d.name for d in decks}
    assert "sw100mA" in names and "sw100mA-30V" in names and "sw2A-30V" in names
    assert "sw100mA-10µs" in names and "sw1A-30V-100µs" in names and len(names) == len(decks)
    d30 = next(d for d in decks if d.name == "sw1A-30V")
    text = incar.deck_text(d30, [("DUT", 1, "", {})], "model.lib", "qspice")
    assert "VCC vcc 0 30" in text and "RL vcc cs 30" in text and "RB in b 100" in text
    long = incar.deck_text(next(d for d in decks if d.name == "sw1A-100µs"), [("DUT", 1, "", {})], "model.lib", "qspice")
    assert "1.00102e-04 10.7" in long or "0.000100102 10.7" in long or "10.7 0.000100102" in long or ".tran 1e-08" in long
    assert ".tran 1e-08 0.0001501" in long or ".tran 1e-08 1.50104e-04" in long


def test_a_step_that_did_not_switch_says_how_far_it_got():
    deck = next(d for d in decks_bjt.plan(CAT, "qspice") if isinstance(d, decks_bjt.Switching) and d.name == "sw1A")
    t = [i * 1e-8 for i in range(900)]
    d = {"time": t, "i(vs)": [0.02 if 1e-7 < x < 3.1e-6 else 0.0 for x in t],
         "v(in)": [10.7 if 1.02e-7 <= x <= 3.102e-6 else -9.3 for x in t]}
    values, _, codes, _ = deck.measure(d, 1, "", {})
    v = values["bjt-switching"]
    assert v["on@1A,10V,3µs"] == pytest.approx(0.02, rel=0.05) and v["td@1A,10V,3µs"] is None and codes["bjt-switching"] == "n/a"


def test_cob_goes_on_to_high_voltage_and_cib_stops_at_30_v():
    deck = decks_bjt.Cap(CAT)
    text = incar.deck_text(deck, [("DUT", 1, "", {})], "model.lib", "qspice")
    assert "VO11 ao11 0 DC 300 AC 1" in text and "VI7 ai7 0 DC 30 AC 1" in text and "VI8 " not in text
    fr = [10 ** (5 + i / 10) for i in range(21)]
    d = {"frequency": fr}
    for i in range(len(deck.vo)):
        d[f"i(vo{i})"] = [complex(0, 2 * math.pi * f * 1e-12) for f in fr]
    for i in range(len(deck.vs)):
        d[f"i(vi{i})"] = [complex(0, 2 * math.pi * f * 5e-12) for f in fr]
    values, curves, _, _ = deck.measure(d, 1, "", {})
    assert values["bjt-capacitance"]["cob@300V"] == pytest.approx(1e-12) and "cib@300V" not in values["bjt-capacitance"]
    assert len(curves["bjt-capacitance"]["Cob"]) == 12 and len(curves["bjt-capacitance"]["Cib"]) == 8


def test_a_capacitance_is_read_as_a_meter_reads_a_junction_behind_the_base_resistance():
    # the onsemi 2N3055 card: 81 nF of emitter junction behind 3.67 ohm of base resistance; at 1 MHz the
    # parallel reading |Im I|/w gives 18 nF, the series-equivalent reading the 81 nF the card holds
    deck = decks_bjt.Cap(CAT)
    fr = [10 ** (5 + i / 10) for i in range(21)]

    def series_rc(r, c):
        return [1 / complex(r, -1 / (2 * math.pi * f * c)) for f in fr]

    d = {"frequency": fr}
    for i in range(len(deck.vo)):
        d[f"i(vo{i})"] = series_rc(0.08, 4.5e-12)                       # a picofarad junction: as before
    for i in range(len(deck.vs)):
        d[f"i(vi{i})"] = series_rc(3.67, 81e-9)
    values, _, codes, _ = deck.measure(d, 1, "", {})
    cap = values["bjt-capacitance"]
    assert cap["cib@100mV"] == pytest.approx(81e-9, rel=1e-9)
    assert cap["cob@10V"] == pytest.approx(4.5e-12, rel=1e-9)
    assert codes["bjt-capacitance"] == "ok"
    # a card with no capacitance: a pure conductance reads zero, not an infinite series capacitance
    for i in range(len(deck.vo)):
        d[f"i(vo{i})"] = [complex(1e-9, 0) for _ in fr]
    values, _, codes, _ = deck.measure(d, 1, "", {})
    assert values["bjt-capacitance"]["cob@10V"] == 0 and codes["bjt-capacitance"] == "absent"


def test_100_c_joins_the_temperatures_and_its_spans():
    temps = [d.temp for d in decks_bjt.plan(CAT, "qspice") if isinstance(d, decks_bjt.Temp)]
    assert sorted(temps) == [-55.0, 100.0, 125.0, 150.0]
    names = {c["name"] for c in CAT["bjt-temperature"]["curves"]}
    assert {"hFE, 100°C", "VCE(sat), 100°C", "IC, 100°C", "dVBE/dT, 25 to 100°C", "dVBE/dT, 100 to 125°C"} <= names


def test_a_subcircuit_is_instanced_through_its_own_pin_order():
    lines = ["VO0 ao0 0 DC 1 AC 1", "QO0 ao0 bo0 eo0 DUT", "QX ca cb ce OTHER"]
    out = incar.as_device(lines, "DUT", ["b", "e", "c", "nc", "c"])
    assert out == ["VO0 ao0 0 DC 1 AC 1", "XO0 bo0 eo0 ao0 nc3QO0 ao0 DUT", "RNC3QO0 nc3QO0 0 1e9", "QX ca cb ce OTHER"]
    assert incar.as_device(lines, "DUT", None) == lines                    # a card's deck is untouched


def test_a_packed_subcircuit_renames_itself_and_everything_inside_it():
    card = ".MODEL QPWR_DUT NPN (BF=100)\n.SUBCKT DUT 1 2 3\nQ1 1 2 3 QPWR_DUT\n.ENDS"
    assert incar.rename(card, "DUT4") == ".MODEL QPWR_DUT4 NPN (BF=100)\n.SUBCKT DUT4 1 2 3\nQ1 1 2 3 QPWR_DUT4\n.ENDS"
    assert incar.rename(".model DUT NPN (BF=100)", "DUT4") == ".model DUT4 NPN (BF=100)"


def test_a_subcircuit_deck_differs_from_the_cards_only_in_its_transistor_lines():
    deck = decks_bjt.Cap(CAT)
    a = incar.deck_text(deck, [("DUT", 1, "", {})], "model.lib", "qspice").splitlines()
    b = incar.deck_text(deck, [("DUT", 1, "", {}, ["c", "b", "e"])], "model.lib", "qspice").splitlines()
    assert len(a) == len(b) and [x for x, y in zip(a, b) if x != y] == [x for x in a if x.startswith("Q")]
    assert all(y.startswith("X") for x, y in zip(a, b) if x != y)
