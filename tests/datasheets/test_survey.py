"""The survey reads a sheet's figure titles three ways and maps each to a test; the registry says how
every sheet is reached, and robots.txt decides which are not."""
import re

import pytest
import yaml

from spicy_electronics_index.core import config
from spicy_electronics_index.datasheets import survey as SV

# Titles as the sheets print them (TI new and legacy, onsemi, Nisshinbo read by hand, Analog Devices),
# and the test each draws. One per rule family, so a rule that stops matching is caught here.
TITLES = [
    ("Offset Voltage Production Distribution", "vos_distribution"),
    ("Offset Voltage vs Temperature", "vos_vs_t"),
    ("VIO vs VCM", "vos_vs_vcm"),
    ("Input Offset vs Common Mode Voltage", "vos_vs_vcm"),
    ("Input Bias Current vs Free-Air Temperature", "ib_vs_t"),
    ("Normalized Input Bias Current and Input Offset Current vs Temperature", "ib_vs_t"),
    ("Input Common Mode Voltage Range versus Temperature", "vicr_vs_t"),
    ("CMRR and PSRR (Power Supply Rejection Ratio) vs Frequency", "cmrr_vs_f"),
    ("Common Mode Rejection versus Frequency", "cmrr_vs_f"),
    ("Supply Voltage Sensitivity vs Frequency", "psrr_vs_f"),
    ("PSSR vs Frequency", "psrr_vs_f"),
    ("EMIRR (Electromagnetic Interference Rejection Ratio) vs Frequency", "emirr_vs_f"),
    ("Open-Loop Gain and Phase vs Frequency", "aol_phase_vs_f"),
    ("LARGE SIGNAL DIFFERENTIAL VOLTAGE AMPLIFICATION vs FREQUENCY", "aol_phase_vs_f"),
    ("Open Loop Frequency Response", "aol_phase_vs_f"),
    ("Closed-Loop Gain vs Frequency", "closed_loop_gain_vs_f"),
    ("Gain Bandwidth Product versus Temperature", "gbw_vs_t"),
    ("Phase Margin versus Differential Source Resistance", "phase_margin_vs_rs"),
    ("Phase Margin vs Capacitive Load", "phase_margin_vs_cl"),
    ("Maximum Peak Output Voltage vs Frequency", "vout_vs_f"),
    ("Maximum Output Voltage vs. Frequency", "vout_vs_f"),           # Nisshinbo, read by hand
    ("Output Saturation Voltage versus Load Current", "vout_vs_iout"),
    ("Output Voltage Swing vs Output Current (Sinking)", "vout_vs_iout"),
    ("Output Sinking Characteristics", "vout_vs_iout"),
    ("Output Voltage vs Load Resistance", "vout_vs_rl"),
    ("Short-Circuit Current vs Temperature", "isc_vs_t"),
    ("Output Impedance versus Frequency", "zout_vs_f"),
    ("Normalized Slew Rate vs Free-Air Temperature", "slew_vs_t"),
    ("Large-Signal Step Response (Rising)", "large_step"),
    ("Non-Inverting Amplifier Slew Rate Response", "large_step"),
    ("Settling Time vs Output Step", "settling"),
    ("Positive Overload Recovery", "overload_recovery"),
    ("No Phase Reversal", "phase_reversal"),
    ("Current Drawn by the Input of the Voltage Follower (IIN) vs the Input Voltage", "input_overvoltage"),
    ("Small-Signal Step Response, Rising", "small_step"),
    ("Small-Signal Voltage Follower Response", "small_step"),
    ("Small-Signal Overshoot vs Capacitive Load", "overshoot_vs_cl"),
    ("Input Voltage Noise Spectral Density vs Frequency", "en_vs_f"),
    ("Equivalent Input Noise Voltage vs Frequency", "en_vs_f"),
    ("Input Referred Noise Voltage and Current versus Frequency", "en_vs_f"),
    ("Current Noise Density vs Frequency", "in_vs_f"),
    ("0.1-Hz to 10-Hz Noise", "noise_0p1_10"),
    ("Total Input Referred Noise Voltage versus Source Resistance", "noise_vs_rs"),
    ("Equivalent input noise voltage vs. source resistance", "noise_vs_rs"),   # Nisshinbo, JIS-A weighted
    ("Voltage Noise Density vs Supply Voltage", "en_vs_vs"),
    ("Total Harmonic Distortion + Noise vs Frequency", "thd_vs_f"),
    ("Total Harmonic Distortion versus Output Voltage", "thd_vs_level"),
    ("THD+N vs Load Resistance", "thd_vs_rl"),
    ("FFT, CCIF Input (19 kHz + 20 kHz)", "spectrum"),
    ("Channel Separation vs Frequency", "channel_separation_vs_f"),
    ("Quiescent Current vs Supply Voltage", "iq_vs_vs"),
    ("Supply Current per Amplifier vs Free-Air Temperature", "iq_vs_t"),
    ("Input Bias Current", "ib_other"),                                # National: the axes say the rest
    ("Unity-Gain Amplifier", "test_circuit"),
    ("Gain-of-10 Inverting Amplifier", "test_circuit"),
    ("Input Offset-Voltage Null Circuit for PS Package (SO, 8) Only", "vos_adjust"),
    ("MIRROR GAIN vs FREE-AIR TEMPERATURE", "norton"),
    ("TL071H DBV Package, 5-Pin SOT-23", "skip"),
    ("Measured Deviation From Ideal RIAA Response", "skip"),
    ("Operational Amplifier Board Layout for Noninverting Configuration", "skip"),
    ("Input and Output Voltages of the Inverting Amplifier", "skip"),
    ("Positive Over-Voltage Recovery", "overload_recovery"),            # 3PEAK, and ST's "Overvoltage Recovery"
    ("VOUT vs. IOUT, Source", "vout_vs_iout"),
    ("IQ vs. VCC, TP1242L1", "iq_vs_vs"),
    ("Vio temperature co-efficient distribution (-40 °C to 25 °C)", "vos_drift_distribution"),
    ("Electromagnetic Interference Rejection Ratio", "emirr_vs_f"),
    ("Thermistor Measurement", "skip"),
    ("Supply Current – Supply Voltage", "iq_vs_vs"),                   # Rohm writes a dash for "vs"
    ("Input Offset Voltage - Ambient Temperature", "vos_vs_t"),
    ("40dB Gain/Phase vs. Frequency", "closed_loop_gain_vs_f"),        # Nisshinbo
    ("Offset Voltage Change Due to Thermal Shock", "vos_thermal_shock"),
    ("0.1 Hz to 10 Hz p-p Noise Tester Frequency Response", "test_circuit"),
    ("Pulsed Operation", ""),
]


@pytest.mark.parametrize("title,expected", TITLES)
def test_a_title_maps_to_its_test(title, expected):
    assert SV.classify(title)[0] == expected


def test_every_rule_names_a_category_and_a_bench_and_ids_are_unique():
    ids = [t[0] for t in SV.TESTS]
    assert len(ids) == len(set(ids))
    for tid, cat, bench, pats in SV.TESTS:
        assert cat in "ABCDEFGHIJKN" and len(cat) == 1
        assert bench == "none" or bench.startswith("opamp-")
        assert pats and all(re.compile(p) for p in pats)


def test_the_table_of_graphs_gives_each_axis_its_figure_number():
    rows = [{"y": 1, "text": "Table of Graphs"},
            {"y": 2, "text": "VIO | Input offset voltage | vs Temperature | 1"},
            {"y": 3, "text": "AVD | Differential voltage amplification | vs Supply voltage | vs Load resistance | vs Frequency | 9 | 10 | 11, 12"},
            {"y": 4, "text": "Vn | Equivalent input noise voltage"},
            {"y": 5, "text": "vs Bandwidth | vs Source resistance | 17 | 18"},
            {"y": 6, "text": "PARAMETER MEASUREMENT INFORMATION"},
            {"y": 7, "text": "SR | Slew rate | vs Temperature | 99"}]
    got = SV.table_of_graphs(rows)
    assert got == [("1", "Input offset voltage vs Temperature"),
                   ("9", "Differential voltage amplification vs Supply voltage"),
                   ("10", "Differential voltage amplification vs Load resistance"),
                   ("11, 12", "Differential voltage amplification vs Frequency"),
                   ("17", "Equivalent input noise voltage vs Bandwidth"),
                   ("18", "Equivalent input noise voltage vs Source resistance")]


def page_of_figures():
    """A page as the sheets print them: two captions side by side, one wrapping onto a second line; a
    legacy graph titled in capitals on three lines with "Figure 8" under it; a bare title; the
    conditions printed in each figure's column; a sentence in prose that names a figure."""
    pymupdf = pytest.importorskip("pymupdf")
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((80, 100), "TA = 25°C", fontsize=8)
    page.insert_text((330, 100), "G = 1, CL = 20 pF", fontsize=8)
    page.insert_text((70, 300), "Figure 5-1. Offset Voltage Production Distribution", fontsize=9)
    page.insert_text((320, 300), "Figure 5-2. CMRR and PSRR (Power Supply Rejection", fontsize=9)
    page.insert_text((380, 312), "Ratio) vs Frequency", fontsize=9)
    page.insert_text((100, 400), "LARGE SIGNAL", fontsize=10)
    page.insert_text((80, 412), "DIFFERENTIAL VOLTAGE AMPLIFICATION", fontsize=10)
    page.insert_text((150, 424), "vs", fontsize=10)
    page.insert_text((130, 436), "FREQUENCY", fontsize=10)
    page.insert_text((110, 470), "VCC = 15 V", fontsize=8)
    page.insert_text((140, 600), "Figure 8", fontsize=9)
    page.insert_text((340, 600), "Input Bias Current vs. Temperature", fontsize=9)
    page.insert_text((100, 740), "Figure 9.", fontsize=9)                   # Rohm: number, quantity, "- axis"
    page.insert_text((100, 752), "Maximum Output Voltage", fontsize=9)
    page.insert_text((110, 764), "- Load Resistance", fontsize=9)
    page.insert_text((60, 700), "Figure 7-2 illustrates the ESD circuits contained in the device.", fontsize=9)
    return page


def test_captions_side_by_side_are_two_figures_and_a_wrapped_one_is_whole():
    figs = {f["n"]: f for f in SV.figures_of(page_of_figures(), 3)}
    assert figs["5-1"]["title"] == "Offset Voltage Production Distribution"
    assert figs["5-2"]["title"] == "CMRR and PSRR (Power Supply Rejection Ratio) vs Frequency"
    assert "TA = 25°C" in figs["5-1"]["printed"] and "TA = 25°C" not in figs["5-2"]["printed"]
    assert "G = 1, CL = 20 pF" in figs["5-2"]["printed"]
    assert "7-2" not in figs                           # prose is not a caption


def test_a_legacy_three_line_title_and_a_bare_title_are_read():
    figs = SV.figures_of(page_of_figures(), 3)
    eight = next(f for f in figs if f["n"] == "8")
    assert eight["title"] == "LARGE SIGNAL DIFFERENTIAL VOLTAGE AMPLIFICATION vs FREQUENCY"
    assert "VCC = 15 V" in eight["printed"]
    bare = [f for f in figs if f["source"] == "bare"]
    assert [f["title"] for f in bare] == ["Input Bias Current vs. Temperature"]
    nine = next(f for f in figs if f["n"] == "9")
    assert nine["title"] == "Maximum Output Voltage - Load Resistance" and SV.classify(nine["title"])[0] == "vout_vs_rl"
    assert SV.classify(eight["title"])[0] == "aol_phase_vs_f"


def test_the_registry_says_how_every_sheet_is_reached_and_why_some_are_not():
    reg = yaml.safe_load(config.datasheet_survey_registry("opamp").read_text(encoding="utf-8"))
    ids = [s["id"] for s in reg["sheets"]]
    assert len(ids) == len(set(ids))
    makers = {s["maker"] for s in reg["sheets"]}
    assert {"ti", "onsemi", "umw", "3peak", "adi", "st", "nisshinbo"} <= makers
    for s in reg["sheets"]:
        assert s["how"] in SV.HOWS, s["id"]
        if s["how"] in ("direct", "wayback"):
            assert s["url"].startswith("https://"), s["id"]
        elif s["how"] == "wayback-prefix":
            assert s["prefix"] and re.compile(s["pick"]), s["id"]
        else:
            assert "robots.txt" in s["why"] and s["url"], s["id"]   # linked, never fetched, and said why
        assert "nisshinbo" not in s.get("url", "").lower() or s["how"] == "none"
        assert "microchip" not in s.get("url", "").lower() or s["how"] == "none"


def test_the_published_tables_are_consistent_with_each_other():
    sheets = SV.load_csv(config.datasheet_survey("opamp", "sheets"))
    figures = SV.load_csv(config.datasheet_survey("opamp", "figures"))
    if not sheets:
        pytest.skip("the survey has not been published")
    by_doc = {s["doc"]: s for s in sheets}
    counts = {}
    for f in figures:
        assert f["doc"] in by_doc
        assert f["title"]
        assert SV.classify(f["title"])[0] == f["test"]     # figures.csv carries today's mapping
        counts[f["doc"]] = counts.get(f["doc"], 0) + 1
    for doc, s in by_doc.items():
        if s["figures"]:
            assert int(s["figures"]) == counts.get(doc, 0), doc
        if s["sha256"]:
            assert re.fullmatch(r"[0-9a-f]{64}", s["sha256"]) and s["url"].startswith("https://")
