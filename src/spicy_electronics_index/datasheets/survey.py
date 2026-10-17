"""What the data sheets of one kind of part measure: every figure of a set of sheets, classified by the
test it draws, and the conditions printed on them — the evidence a bench for that kind is drawn from
(docs/opamp-characterisation.md for op-amps).

    sei datasheets survey --kind opamp [--fetch] [--limit N] [--reread]

The sheets are those of the survey's registry (`config.datasheet_survey_registry(kind)`): maker, part, the
maker's own address and how it is reached — direct where the maker's robots.txt lets a script read the
sheet; from the Internet Archive's capture of that same address where the maker's site refuses scripts
(ST, Analog Devices, Rohm: what harvest.py does, and data/datasheets/sources.yaml records how each was
found out); not at all where robots.txt disallows the PDF (Nisshinbo, Microchip), in which case the
address is published and the sheet is not read. `--fetch` fetches the sheets the store does not hold
(`config.datasheet_survey_store(kind)`, private), through the polite client; the ledger keeps each sheet's
link, the copy it was read from, checksum, size and page count, which is what is published of it.

What is read off a sheet is the titles of its figures — a numbered caption ("Figure 5-12. Offset Voltage
vs Temperature"), a row of a legacy TI "Table of Graphs" (symbol, quantity, "vs" axis, figure number), or
the bare "Input Noise Voltage vs Frequency" printed over a graph — the condition lines printed beside each,
the sheet's document number, revision and date, and how often each supply, load, capacitance, level,
frequency, gain, temperature and source resistance is named anywhere in it. Nothing else leaves the PDF: a
title and a condition are facts about what the maker measured, and the drawings stay on the page.

Every title is mapped to a canonical test (`TESTS`: the id, its category A–K, the regexes, and the bench
measurement that draws the same graph for a model). Published under `config.datasheet_survey(kind, …)`:
`sheets.csv`, `figures.csv` (a title no rule maps keeps an empty test: that column is the list to grow the
rules from), `matrix.csv` (tests by sheet) and `conditions.csv`; and the section between the survey marks
of the kind's characterisation document is rewritten from them. Reading a sheet is ledgered by its
checksum and the reader's version; the mapping and the tables are recomputed from `figures.csv` on
every run, so a new rule costs no second reading.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import yaml

from spicy_electronics_index.core import http
from spicy_electronics_index.core.config import (
    datasheet_survey,
    datasheet_survey_registry,
    datasheet_survey_state,
    datasheet_survey_store,
    docs_dir,
    require,
)
from spicy_electronics_index.core.ledger import Ledger

READ_VERSION = "survey-1"
STAGES = ("fetch", "read")
VERSIONED = ("read",)
FIELDS = ("key", "url", "copy", "http", "bytes", "sha256", "pages", "fetch_at", "read_at", "read_v", "skip_reason")
SHEET_FIELDS = ("doc", "maker", "part", "url", "copy", "sha256", "bytes", "pages", "images", "document", "revision", "date",
                "title", "figures", "untitled", "mapped", "how", "why")
FIGURE_FIELDS = ("doc", "n", "page", "title", "printed", "source", "test", "category", "bench")
CONDITION_FIELDS = ("doc", "kind", "value", "count")
PROJECT_UA = "spicy-electronics-index (+https://electrucio.github.io/spicy-electronics-index/)"
CDX = "https://web.archive.org/cdx/search/cdx"
ARCHIVE_DELAY = 10.0        # the archive refused connections at one request every 3 s (sources.yaml)
HOWS = ("direct", "wayback", "wayback-prefix", "none")
MARK_START, MARK_END = "<!-- survey:start -->", "<!-- survey:end -->"
DOCS = {"opamp": "opamp-characterisation.md"}

# ---- the canonical tests ------------------------------------------------------------------------------
# (id, category, bench measurement, regexes on the lower-cased title). The first rule that matches wins,
# so the specific come before the general. Categories: A supply, B input DC, C range and rejection,
# D gain and frequency, E output, F large signal, G small signal, H noise, I distortion, J multichannel,
# K test circuits and measurement information.
V = r"(?:vs\.?|versus|against|as a function of)"
TESTS = [
    # A supply
    ("iq_vs_vs", "A", "opa-iq", [rf"operating current.*{V}.*(operating|supply) voltage", rf"\biq\b.*{V}.*(vcc|vdd|\bvs\b|supply)",rf"(quiescent|supply|power supply) current.*{V}.*(supply|vcc|v\+|vs\b)", rf"\bi(cc|q|dd|s)\b.*{V}.*supply", rf"(supply|quiescent) current.*{V}.*voltage"]),
    ("iq_vs_t", "A", "opa-iq", [rf"operating current.*{V}.*temp", rf"\biq\b.*{V}.*temp",rf"(quiescent|supply|power supply) current.*{V}.*temp", rf"\bi(cc|q|dd|s)\b.*{V}.*temp"]),
    ("pd_vs_t", "A", "none", [rf"(power dissipation|dissipation).*{V}.*temp", r"derating"]),
    ("pd_vs_vs", "A", "none", [rf"(power dissipation|dissipation).*{V}.*supply"]),
    ("turn_on", "A", "opa-iq", [r"turn[- ]?on", r"start[- ]?up", r"power[- ]on"]),
    ("vs_range", "A", "opa-runs", [r"supply voltage range", rf"operating voltage.*{V}", rf"supply voltage.*{V}.*temp"]),
    # B input DC
    ("vos_distribution", "B", "opa-offset", [r"offset voltage.*(distribution|histogram)", r"vos.*distribution", r"offset.*production"]),
    ("vos_drift_distribution", "B", "opa-offset", [r"(offset|vos).*drift.*(distribution|histogram)", r"(offset|vio).*temp.*co.?efficient", r"(offset|vio).*temp\.? co\b"]),
    ("vos_warmup", "B", "opa-offset", [r"warm[- ]?up", rf"offset.*{V}.*time after power"]),
    ("vos_longterm", "B", "opa-offset", [r"long[- ]term", r"elapsed time", r"time \(months\)", rf"offset.*{V}.*\btime\b"]),
    ("vos_thermal_shock", "B", "opa-offset", [r"thermal shock"]),
    ("vos_vs_t", "B", "opa-offset", [rf"(offset voltage|input offset(?! current)).*{V}.*temp", rf"\bvio\b.*{V}.*temp", rf"\bvos\b.*{V}.*temp", r"offset.*drift.*(units|representative)", rf"offset voltage drift.*{V}"]),
    ("vos_vs_vcm", "B", "opa-offset", [rf"(offset voltage|input offset(?! current)).*{V}.*common", rf"\bvio\b.*{V}.*(vcm|common)", rf"\bvos\b.*{V}.*(vcm|common)", rf"offset voltage.*{V}.*input voltage"]),
    ("vos_vs_vs", "B", "opa-offset", [rf"offset voltage.*{V}.*(power supply|supply)", rf"\bvio\b.*{V}.*supply"]),
    ("vos_vs_rs", "B", "opa-offset", [rf"offset voltage.*{V}.*source resist"]),
    ("vos_adjust", "B", "none", [r"offset.*(null|adjust|trim)", r"(null|nulling|adjust).*offset", r"\bvos\b.*adjust"]),
    ("ib_vs_t", "B", "opa-bias", [rf"input bias.*{V}.*temp",rf"bias current.*{V}.*temp", r"bias current and (input )?offset", rf"\biib\b.*{V}.*temp", rf"\bib\b.*{V}.*temp"]),
    ("ib_vs_vcm", "B", "opa-bias", [rf"bias current.*{V}.*(common|input voltage|vcm)", rf"\bib\b.*{V}.*(vcm|common)"]),
    ("ib_vs_vs", "B", "opa-bias", [rf"bias current.*{V}.*supply"]),
    ("ios_vs_t", "B", "opa-bias", [rf"offset current.*{V}.*temp", rf"\biio\b.*{V}.*temp", rf"\bios\b.*{V}.*temp"]),
    ("ios_vs_vcm", "B", "opa-bias", [rf"offset current.*{V}.*(common|vcm)"]),
    ("zin_vs_f", "B", "opa-bias", [rf"input (impedance|resistance|capacitance).*{V}"]),
    # C range and rejection
    ("vicr_vs_t", "C", "opa-offset", [rf"^input voltage.*{V}.*temp",rf"common.mode (input )?(voltage )?range.*{V}.*temp", rf"input voltage range.*{V}.*temp", rf"\bvicr\b.*{V}.*temp"]),
    ("vicr_vs_vs", "C", "opa-offset", [rf"common.mode (input )?(voltage )?range.*{V}.*supply", rf"input voltage range.*{V}.*supply", rf"\bvicr\b.*{V}.*supply", rf"input (common.mode )?voltage.*{V}.*supply"]),
    ("cmrr_vs_f", "C", "opa-cmrr-f", [rf"(cmrr|cmr|common.mode rejection).*{V}.*freq", r"cmrr and psrr.*freq", r"common.mode rejection and (power.)?supply rejection"]),
    ("cmrr_vs_t", "C", "opa-offset", [rf"(cmrr|cmr|common.mode rejection).*{V}.*temp"]),
    ("cmrr_vs_vcm", "C", "opa-offset", [rf"(cmrr|cmr|common.mode rejection).*{V}.*(common|vcm)"]),
    ("psrr_vs_f", "C", "opa-psrr-f", [rf"(psrr|pssr|psr|power.supply rejection|supply.voltage rejection|supply voltage sensitivity|ksvr).*{V}.*freq"]),
    ("psrr_vs_t", "C", "opa-offset", [rf"(psrr|psr|power.supply rejection|supply.voltage rejection|supply voltage sensitivity|ksvr).*{V}.*temp"]),
    ("psrr_vs_vs", "C", "opa-offset", [rf"(psrr|psr|power.supply rejection|supply.voltage rejection).*{V}.*supply"]),
    ("emirr_vs_f", "C", "opa-emirr", [r"emirr", r"emi rejection", r"\bemi\b", r"electromagnetic interference"]),
    ("rejection_vs_t", "C", "opa-offset", [rf"^rejection.*{V}.*temp"]),
    # D gain and frequency
    ("aol_phase_vs_f", "D", "opa-aol", [rf"(open.loop|large.signal|differential).*(gain|amplification|response).*{V}.*freq", rf"gain.*phase.*{V}.*freq", r"open.loop (frequency|gain).*(response|phase)", rf"(gain|phase).*shift.*{V}.*freq", r"\bgain/phase\b", rf"\bavd\b.*{V}.*freq", r"(voltage )?gain and phase", r"bode", rf"phase (shift|margin).*{V}.*freq", r"open.loop.*gain.*(magnitude|phase)"]),
    ("closed_loop_gain_vs_f", "D", "opa-closed-loop", [rf"closed.loop (gain|output|response|frequency).*{V}.*freq", r"\d+\s*db gain", r"closed.loop.*(freq|response)", rf"(voltage )?gain.*{V}.*freq.*closed", r"(small.signal )?(frequency|gain) response"]),
    ("aol_vs_t", "D", "opa-aol", [rf"(open.loop|large.signal|differential|voltage).*(gain|amplification).*{V}.*temp", rf"\b(avd|avol|aol)\b.*{V}.*temp"]),
    ("aol_vs_vs", "D", "opa-aol-swing", [rf"(open.loop|large.signal|differential|voltage).*(gain|amplification).*{V}.*supply", rf"\b(avd|avol|aol)\b.*{V}.*supply"]),
    ("aol_vs_rl", "D", "opa-aol-swing", [rf"(open.loop|large.signal|differential|voltage).*(gain|amplification).*{V}.*load", rf"\b(avd|avol|aol)\b.*{V}.*load"]),
    ("aol_vs_vo", "D", "opa-aol-swing", [rf"(open.loop|large.signal|differential|voltage).*(gain|amplification).*{V}.*output", rf"\b(avd|avol|aol)\b.*{V}.*output"]),
    ("gbw_vs_vs", "D", "opa-aol", [rf"(gain.bandwidth|gbw|gbp|unity.gain (bandwidth|frequency)|bandwidth).*{V}.*supply"]),
    ("gbw_vs_t", "D", "opa-aol", [rf"(gain.bandwidth|gbw|gbp|unity.gain (bandwidth|frequency)|bandwidth and phase|normalized.*bandwidth).*{V}.*temp", r"slew rate, gain bandwidth", r"(gain.bandwidth|gbw).*(and|,).*phase margin"]),
    ("gbw_vs_rl", "D", "opa-aol", [rf"(gain.bandwidth|gbw|unity.gain bandwidth).*{V}.*load"]),
    ("phase_margin_vs_cl", "D", "opa-stability", [rf"(phase|gain) margin.*{V}.*(capacit|load cap|\bcl\b|load)"]),
    ("phase_margin_vs_rs", "D", "opa-stability", [rf"(phase|gain) (margin|shift).*{V}.*(source resist|\brt\b|resist)"]),
    ("phase_margin_vs_t", "D", "opa-aol", [rf"(phase|gain) (margin|shift).*{V}.*temp"]),
    ("phase_vs_vs", "D", "opa-aol", [rf"phase (margin|shift).*{V}.*supply"]),
    ("gain_vs_f_comp", "D", "opa-aol", [r"compensation", r"\bcomp\b"]),
    # E output
    ("vout_vs_f", "E", "opa-max-vo-f", [r"large.signal frequency response",rf"(maximum|peak|output|undistorted).*(output )?(voltage|swing).*{V}.*freq", r"(power|output|swing|large.signal) bandwidth", rf"\bvo(m|pp|\(pp\))?\b.*{V}.*freq"]),
    ("vout_vs_iout", "E", "opa-swing", [r"output characteristics.*(sourc|sink)", rf"output current.*{V}.*output voltage", rf"\bvout\b.*{V}.*\biout\b",r"(sinking|sourcing) characteristics", rf"(low|high) level output.*{V}.*output", rf"saturation.*{V}.*load current", rf"saturation.*{V}.*current",rf"(output|saturation).*(voltage|swing).*{V}.*(output current|iout|sink|source|\bio\b)", rf"(output|saturation) voltage.*{V}.*current", rf"(high|low).level output.*{V}.*current", rf"\bvo[hl]\b.*{V}", r"output.*(sink|source).*current"]),
    ("vout_vs_rl", "E", "opa-swing", [rf"saturation.*{V}.*load",rf"(output|saturation|peak|maximum).*(voltage|swing).*{V}.*load (resist|current)?", rf"(output|saturation).*voltage.*{V}.*\brl\b", rf"\bvo(m|pp)?\b.*{V}.*load"]),
    ("vout_vs_vs", "E", "opa-swing", [rf"(maximum|peak|output).*(voltage|swing).*{V}.*supply", rf"\bvo(m|pp)?\b.*{V}.*supply", rf"output (voltage )?swing.*{V}.*(vcc|vs\b)"]),
    ("vout_vs_t", "E", "opa-swing", [rf"(maximum|peak|output).*(voltage|swing).*{V}.*temp", rf"\bvo(m|pp)?\b.*{V}.*temp"]),
    ("isc_vs_t", "E", "opa-isc", [rf"current limit.*{V}.*temp",rf"short.circuit.*{V}.*temp", rf"\bios\b.*{V}.*temp.*short"]),
    ("isc_vs_time", "E", "opa-isc", [rf"short.circuit.*{V}.*time", r"short.circuit.*(duration|time)"]),
    ("isc_vs_vs", "E", "opa-isc", [rf"short.circuit.*{V}.*supply"]),
    ("zout_vs_f", "E", "opa-zout", [rf"output (impedance|resistance).*{V}.*freq", rf"\bz(o|out)\b.*{V}.*freq", r"(open|closed).loop output impedance"]),
    ("cl_drive", "E", "opa-stability", [r"(capacitive load|load capacitance).*(drive|stability|stable)", rf"stability.*{V}.*capacit"]),
    # F large signal
    ("slew_vs_t", "F", "opa-slew", [rf"slew rate.*{V}.*temp", rf"\bsr\b.*{V}.*temp"]),
    ("slew_vs_vs", "F", "opa-slew", [rf"slew rate.*{V}.*supply"]),
    ("slew_vs_cl", "F", "opa-slew", [rf"slew rate.*{V}.*(capacit|load)"]),
    ("slew_vs_gain", "F", "opa-slew", [rf"slew rate.*{V}.*gain"]),
    ("large_step", "F", "opa-slew", [r"^large signal$",r"large.signal.*(step|pulse|transient|response|waveform)", r"(inverting|non.?inverting|follower).*(slew|large.signal|pulse)", r"(voltage|unity).?(gain )?follower.*(pulse|large)", r"pulse response.*large", r"slew(ing)? (response|waveform)", rf"large.signal.*{V}.*time", r"output.*swing.*(step|pulse)"]),
    ("settling", "F", "opa-settling", [r"settling"]),
    ("overload_recovery", "F", "opa-overload", [r"overload", r"over.?drive recovery", r"saturation recovery", r"over.?voltage recovery"]),
    ("phase_reversal", "F", "opa-phase-reversal", [r"phase reversal", r"phase inversion"]),
    ("input_overvoltage", "F", "opa-phase-reversal", [rf"{V} the input voltage", r"input (over.?voltage|beyond)", rf"output voltage( node)?.*{V}.*input( voltage)?$", rf"(differential|positive|negative) output voltage.*{V}.*input"]),
    # G small signal
    ("small_step", "G", "opa-step", [r"^small signal$",r"dynamic (performance|response)", r"small.signal.*(follower|response)",r"small.signal.*(step|pulse|transient|response|waveform)", r"pulse response.*small", r"(step|pulse|transient) response", r"(rising|falling) edge"]),
    ("overshoot_vs_cl", "G", "opa-stability", [rf"overshoot.*{V}.*(capacit|load)", r"overshoot.*\bcl\b", r"amplifier overshoot", r"overshoot"]),
    # I distortion
    ("thd_vs_f", "I", "opa-thd-f", [rf"(thd|distortion|harmonic).*{V}.*freq"]),
    ("thd_vs_level", "I", "opa-thd-level", [rf"(thd|distortion).*{V}.*(output (voltage|amplitude|level|swing)|amplitude|level|\bvo\b|vout|voltage)"]),
    ("thd_vs_rl", "I", "opa-thd-load", [rf"(thd|distortion).*{V}.*load"]),
    ("thd_vs_gain", "I", "opa-thd-f", [rf"(thd|distortion).*{V}.*gain"]),
    ("imd", "I", "opa-imd", [r"intermodulation", r"\bimd\b", r"two.tone"]),
    ("spectrum", "I", "opa-thd-f", [r"\bfft\b", r"output spectrum"]),
    ("thd_other", "I", "opa-thd-f", [r"\bthd\b", r"harmonic distortion", r"distortion"]),
    # H noise
    ("noise_0p1_10", "H", "opa-noise", [r"0\.1.?hz.*10.?hz", r"low.frequency noise", rf"noise.*{V}.*time", r"peak.to.peak noise", r"noise.*(10 s|1 s/div|time record)"]),
    ("en_vs_vs", "H", "opa-noise", [rf"noise.*{V}.*supply"]),
    ("en_vs_t", "H", "opa-noise", [rf"noise.*{V}.*temp"]),
    ("noise_vs_rs", "H", "opa-noise-rs", [rf"noise.*{V}.*source (resist|impedance)", rf"noise figure.*{V}", rf"total noise.*{V}", rf"noise.*{V}.*\brs\b"]),
    ("noise_vs_bandwidth", "H", "opa-noise", [rf"noise.*{V}.*bandwidth", r"integrated noise", r"rms noise.*bandwidth"]),
    ("in_vs_f", "H", "opa-noise", [rf"(current noise|noise current).*{V}.*freq", r"(current noise|noise current) (density|spectral)"]),
    ("en_vs_f", "H", "opa-noise", [rf"(voltage )?noise.*(density|spectral|voltage|\bvn\b|\ben\b).*{V}.*freq", rf"(input|equivalent).*noise.*{V}.*freq", r"noise (voltage|current).*freq", rf"\bnoise\b.*{V}.*freq", r"noise spectral density", r"noise density"]),
    # J multichannel
    ("channel_separation_vs_f", "J", "opa-separation", [r"channel separation", r"crosstalk", r"cross.talk"]),
    # K test circuits and measurement information (not tests of the device, but how the tests are made)
    ("test_circuit", "K", "none", [r"test circuit", r"^test figure", r"testing circuit", r"measurement circuit", r"test (set.?up|fixture|configuration)", r"(null|nulling) circuit", r"^unity.gain (amplifier|follower|buffer)$", r"^(inverting|non.?inverting) amplifier$", r"gain.of.\d+ (inverting )?amplifier", r"noise.*circuit", r"(circuit|setup) for", r"(slew.rate|settling.time|distortion|noise).*(circuit|setup)", r"offset.*(null|adjust).*circuit", r"input (protection|circuit)", r"equivalent (input )?circuit"]),
    # A quantity named without its axis (National's "Input Bias Current" over a graph whose axes say the rest)
    ("vicr_other", "C", "opa-offset", [r"common.mode (input )?voltage (range|limit)", r"input voltage range", r"common.mode voltage (low|high)"]),
    ("vout_other", "E", "opa-swing", [r"output (voltage )?swing", r"^voltage swing", r"output saturation", r"undistorted output", r"maximum (peak )?output voltage", r"output voltage$"]),
    ("isc_other", "E", "opa-isc", [r"short.circuit", r"current limit"]),
    ("zout_other", "E", "opa-zout", [r"output impedance"]),
    ("aol_other", "D", "opa-aol", [r"open.loop (voltage )?gain", r"voltage gain$", r"differential voltage amplification", r"large.signal.*gain"]),
    ("gbw_other", "D", "opa-aol", [r"gain.bandwidth", r"\bgbw\b", r"unity.gain bandwidth"]),
    ("slew_other", "F", "opa-slew", [r"slew rate"]),
    ("ib_other", "B", "opa-bias", [r"bias current"]),
    ("ios_other", "B", "opa-bias", [r"offset current"]),
    ("vos_other", "B", "opa-offset", [r"offset voltage"]),
    ("iq_other", "A", "opa-iq", [r"supply current", r"quiescent current"]),
    ("cmrr_other", "C", "opa-cmrr-f", [r"\bcmrr\b", r"common.mode rejection"]),
    ("psrr_other", "C", "opa-psrr-f", [r"\bpsrr\b", r"power.supply rejection", r"supply.voltage rejection"]),
    ("noise_other", "H", "opa-noise", [r"\bnoise\b"]),
    # Norton (current-differencing) amplifiers: their own tests, kept apart from the voltage-input op-amp's
    ("norton", "N", "none", [r"mirror", r"norton", r"current.differencing", rf"input current.*{V}", r"pull.?down current", r"low.level output current"]),
]
# What is not a figure of a measurement: packages, pins, layouts, block diagrams, application circuits
# and their responses (a RIAA preamp's deviation is the circuit's, not the amplifier's).
SKIP = re.compile(r"(package|pin (configuration|function|assignment|out|connection)|pinout|top view|layout|block diagram|"
                  r"functional (block|diagram)|schematic|tape|reel|footprint|land pattern|stencil|marking|outline|"
                  r"dimensions|application|typical connection|circuit diagram|symbol|ordering|thermal pad|soldering|"
                  r"reflow|\bdie\b|\bbond|\bboard\b|\bpcb\b|\bevm\b|example circuit|filter\b|generator|regulator|"
                  r"headphone|preamp|microphone|mic amp|\bdriver\b|\bbridge\b|buffer$|integrator|rectifier|oscillator|"
                  r"comparator|detector|monitor|converter|servo|limiter|\bclamp|reference|multiplexer|summing|"
                  r"instrumentation|riaa|\bnab\b|tone.control|equali[sz]er|panning|adder|subtracter|line receiver|"
                  r"phantom|sample and hold|\bvco\b|isolating|boosting|wiring|guard|composite|cancellation|driving|"
                  r"doubler|interface|voltage.controlled|ac coupled|high impedance|input pair|input stage|esd|"
                  r"protection|current source$|current sink$|i-v|\bdac\b|baxandall|simulation|notch|distribution amplifier|"
                  r"ac amplifier|telephone|load cell|thermocouple|photodiode|transimpedance|cable|coaxial|of the inverting amplifier|"
                  r"supply rails|flat amp|photovoltaic|compliance|high frequency pulse|basic (inverting|noninverting)|dc coupled|"
                  r"power supply configurations|thermistor|current sense|current pump|high.gain amplifier|unused op.?amp|single supply inverting|^[a-z]{1,4}(?:, [a-z]{1,4})*,? and [a-z]{1,4}$)", re.I)
# Named before the skip list is asked: a test circuit is a circuit, and an offset-null circuit is not an application.
FIRST = ("vos_adjust", "test_circuit")


def normalise(title: str) -> str:
    t = title.lower().replace("—", "-").replace("–", "-").replace("’", "'")
    t = re.sub(r"\(.*?\)", " ", t)                  # "(LM358B)", "(sinking)"
    t = t.replace("versus", "vs").replace("vs.", "vs")
    t = re.sub(r"[^a-z0-9+/%°.\- ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def classify(title: str) -> tuple[str, str, str]:
    """(test id, category, bench) for a figure title, or ('', '', '') when no rule matches. A title the
    skip list names is a package, a pin-out or an application and is ('skip', '', '')."""
    c = normalise(title)
    if not c:
        return "", "", ""
    rules = {r[0]: r for r in TESTS}
    for tid in FIRST:
        if any(re.search(p, c) for p in rules[tid][3]):
            return tid, rules[tid][1], rules[tid][2]
    if SKIP.search(c):
        return "skip", "", ""
    for tid, cat, bench, pats in TESTS:
        for p in pats:
            if re.search(p, c):
                return tid, cat, bench
    return "", "", ""



COND_RES = {
    "supply": re.compile(r"\bV(?:S|CC|DD|EE|SS|\+|\+/V[-–]|\+/[-–]|CC\+|CC[-–]|CC/VEE|SUPPLY)\s*=\s*(±?\s*[\d.]+\s*V(?:\s*(?:to|…|\.\.\.|[-–])\s*±?\s*[\d.]+\s*V)?)", re.I),
    "rl": re.compile(r"\bR\s*L\s*[=≥>]+\s*([\d.]+\s*[kKM]?\s*(?:Ω|ohm))", re.I),
    "cl": re.compile(r"\bC\s*L\s*[=≤<]+\s*([\d.]+\s*[pnµu]F)", re.I),
    "vo": re.compile(r"\bV(?:O|OUT|O\(PP\)|OPP)\s*=\s*([±]?[\d.]+\s*V\s*(?:RMS|rms|pp|p-p|PP|P-P)?)", re.I),
    "f": re.compile(r"\bf\s*=\s*([\d.]+\s*[kMG]?Hz)", re.I),
    "gain": re.compile(r"\b(?:G|AV|A\s*V|ACL|AVD|GAIN)\s*=\s*([+\-–]?\d+(?:\.\d+)?(?:\s*V/V|\s*dB)?)", re.I),
    "temp": re.compile(r"\bT\s*[AJ]?\s*=\s*([\-–]?\d+\s*°?\s*C)\b", re.I),
    "rs": re.compile(r"\bR\s*S\s*[=≤<]+\s*([\d.]+\s*[kKM]?\s*(?:Ω|ohm))", re.I),
    "vcm": re.compile(r"\bV\s*(?:CM|IC|ICM)\s*=\s*([^,;\n|]{1,20})", re.I),
    "band": re.compile(r"(0\.1\s*Hz\s*to\s*10\s*Hz|10\s*Hz\s*to\s*10\s*kHz|20\s*Hz\s*to\s*20\s*kHz|80\s*kHz|22\s*kHz|30\s*kHz)", re.I),
}
# The maker's document number, on the first two pages: TI's literature number (SLOS080W, SNOSBH0C), onsemi's
# MC33078/D, ST's DS2298, ADI's D00291-0-10/15(H) print code, Renesas' FN957.
DOC_NUMBER = {
    "ti": re.compile(r"\b(S[A-Z]{3}(?:\d{3}|[A-Z]{2}\d)[A-Z]{0,2})\b"),
    "onsemi": re.compile(r"\b([A-Z]{2,4}\d{3,6}[A-Z]?/D)\b"),
    "st": re.compile(r"\b(DS\d{4,5})\b"),
    "adi": re.compile(r"\b(D\d{5}-\d+-\d+/\d+\([A-Z0-9]+\))"),
    "nxp": re.compile(r"\b(\d{10,11}|NE\d{4}[A-Z_]*\s+\d+)\b"),
    "rohm": re.compile(r"\b(\d{4}\.\d{3}\.\d{3}\.\d{3})\b"),
    "renesas": re.compile(r"\b(FN\d{3,4}(?:\.\d+)?)\b"),
}
REVISION = re.compile(r"\b(?:Rev(?:ision)?\.?\s*([A-Z]{1,2}|\d+(?:\.\d+)?)|Ver\.?\s*([\d.\-]+))\b")
DATE = re.compile(r"\b((?:JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER|"
                  r"January|February|March|April|May|June|July|August|September|October|November|December|"
                  r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?,?\s+\d{4})\b")

# ---- reading a sheet -------------------------------------------------------------------------------
# "Figure 5-12. Title", "FIGURE 12. TITLE", "Fig. 3 Title", ADI's "TPC 12. Title"; a legacy TI "Figure 8" with no
# title at all (its title is printed over the graph). "Figure 7-2 illustrates…" in prose is not a caption.
CAPTION = re.compile(r"^(?:Figure|FIGURE|Fig\.?|TPC)\s*(\d+(?:[-–]\d+)?[a-z]?)(?:\s*[.:]\s*(.*))?$")
BARE = re.compile(r"^([A-Za-z][A-Za-z0-9 /().,+\-–°%']{2,70}?)\s+(?:vs\.?|versus)\s+([A-Za-z0-9 /().,+\-–°%']{2,60}?)\s*$")
VS_LINE = re.compile(r"^(?:vs\.?|versus)$", re.I)
INCOMPLETE = re.compile(r"(\bvs\.?|\bversus|\band|\bof|\bthe|\bat|\bfor|\bwith|\bpower|\bsupply|\bper|,|-|–|\()$", re.I)
COND = re.compile(r"[A-Za-z]\w*\s*[=≤≥<>]\s*[±\-–]?\d")
GAP = 12.0          # points between two words that end a segment: the next column, or a table's next cell
NEAR = 14.0         # points between a line and the next that wraps it


def segments_of(page) -> tuple[list[dict], list[dict]]:
    """The page's text twice: as `rows`, words clustered by their vertical centre and read across the whole
    page (a table row's cells come out as one line, ' | ' between cells), and as `segments`, the pieces of
    those rows that a gap of more than GAP points separates (a caption, its neighbour in the next column
    and a plot's id are three segments). Each carries its box; a rotated axis title is one tall word and
    is left out."""
    words = [w for w in page.get_text("words") if w[4].strip() and (w[3] - w[1]) < 30]
    words.sort(key=lambda w: ((w[1] + w[3]) / 2, w[0]))
    clusters: list[list] = []
    for w in words:
        cy = (w[1] + w[3]) / 2
        if clusters and abs(cy - clusters[-1][0]) <= 2.5:
            clusters[-1][1].append(w)
        else:
            clusters.append([cy, [w]])
    rows, segments = [], []
    for cy, ws in clusters:
        ws.sort(key=lambda w: w[0])
        pieces: list[list] = [[ws[0]]]
        for a, b in zip(ws, ws[1:]):
            if b[0] - a[2] <= GAP:
                pieces[-1].append(b)
            else:
                pieces.append([b])
        for piece in pieces:
            segments.append({"y": cy, "x0": min(w[0] for w in piece), "x1": max(w[2] for w in piece),
                             "top": min(w[1] for w in piece), "bottom": max(w[3] for w in piece),
                             "text": " ".join(w[4] for w in piece), "row": len(rows)})
        rows.append({"y": cy, "text": " | ".join(" ".join(w[4] for w in piece) for piece in pieces)})
    return segments, rows


def overlaps(a: dict, b: dict) -> bool:
    return a["x0"] < b["x1"] and b["x0"] < a["x1"]


def below(segments: list[dict], i: int, near: float = NEAR) -> int | None:
    """The segment that wraps segment i: the nearest one under it within `near` points, in its column.
    Lines are told apart by their centres: the glyph boxes of two lines of a title overlap by a point."""
    s = segments[i]
    best = None
    for j in range(i + 1, min(len(segments), i + 16)):
        o = segments[j]
        if o["y"] < s["y"] + 3:
            continue
        if o["top"] - s["bottom"] > near:
            break
        if overlaps(o, s) and (best is None or o["y"] < segments[best]["y"]):
            best = j
    return best


def above(segments: list[dict], i: int, near: float = NEAR) -> int | None:
    s = segments[i]
    best = None
    for j in range(i - 1, max(-1, i - 16), -1):
        o = segments[j]
        if o["y"] > s["y"] - 3:
            continue
        if s["top"] - o["bottom"] > near:
            break
        if overlaps(o, s) and (best is None or o["y"] > segments[best]["y"]):
            best = j
    return best


def wraps(title: str, nxt: str) -> bool:
    """Whether `nxt`, printed right under `title`, continues it."""
    if CAPTION.match(nxt) or COND.search(nxt) or len(nxt) > 70 or VS_LINE.match(nxt):
        return False
    if not title or INCOMPLETE.search(title) or title.count("(") > title.count(")") or nxt[:1].islower() \
            or (nxt.startswith("(") and nxt.endswith(")")):
        return True
    # "Figure 7. Input Common Mode Voltage" / "Range versus Temperature": a short line of words, in
    # title case, under a caption that does not end a sentence
    return (nxt[:1].isupper() and len(nxt.split()) <= 6 and wordy(nxt) and not title.endswith(".")
            and len(title.split()) <= 10)


def wordy(s: str) -> bool:
    """A title's part, not a tick label or a table cell: a word of three letters or more, few digits."""
    return bool(re.search(r"[A-Za-z]{3,}", s)) and len(re.findall(r"\d", s)) <= 2


def all_caps(s: str) -> bool:
    letters = [c for c in s if c.isalpha()]
    return len(letters) >= 3 and all(c.isupper() for c in letters)


def vs_title(segments: list[dict], i: int, used: set) -> str:
    """The title printed as three lines over a legacy graph — the quantity (itself on one or two lines),
    "vs", the axis — given the index of the "vs" line."""
    up, down = above(segments, i), below(segments, i)
    if up is None or down is None:
        return ""
    q, ax = segments[up]["text"], segments[down]["text"]
    if COND.search(q + ax) or len(q) > 70 or len(ax) > 60 or CAPTION.match(q) or CAPTION.match(ax) \
            or not wordy(q) or not wordy(ax) or re.search(r"[≤≥=<>]", q + ax):
        return ""
    used.update({i, up, down})
    up2 = above(segments, up)
    if up2 is not None and all_caps(q) and all_caps(segments[up2]["text"]) and len(segments[up2]["text"]) < 60 \
            and not COND.search(segments[up2]["text"]):
        q = segments[up2]["text"] + " " + q
        used.add(up2)
    return f"{q} vs {ax}"


def table_of_graphs(rows: list[dict]) -> list[tuple[str, str]]:
    """The rows of a legacy TI "Table of Graphs": (figure number, "quantity vs axis") for each "vs" cell.
    A row names its quantity once and lists several axes, each with its figure number; a row with only
    axes continues the quantity of the row above."""
    out, name, inside = [], "", False
    for r in rows:
        t = r["text"]
        if re.search(r"table of graphs", t, re.I):
            inside = True
            continue
        if not inside:
            continue
        if re.match(r"^\s*(Figure|FIGURE)\s+\d", t) or re.search(r"(?i)^\s*\d+(\.\d+)*\s+[A-Z][a-z]+ [A-Z]", t) \
                or re.search(r"(?i)parameter measurement|electrical characteristics", t):
            inside = False
            continue
        cs = [c.strip() for c in t.split("|") if c.strip()]
        axes = [c for c in cs if re.match(r"(?i)^(vs\.?|versus)\s", c)]
        head = cs[:cs.index(axes[0])] if axes else cs
        before = [c for c in head if not re.fullmatch(r"[A-Za-zΔφ][A-Za-z0-9()/+\-–]{0,6}", c) and not re.fullmatch(r"[\d, ]+", c)]
        if before:
            name = before[-1]                    # a row with only a quantity names the rows under it
        if not axes:
            continue
        numbers = [c for c in cs if re.fullmatch(r"\d+(?:\s*,\s*\d+)*", c)]
        for i, ax in enumerate(axes):
            n = numbers[i] if i < len(numbers) else ""
            axis = re.sub(r"(?i)^(vs\.?|versus)\s+", "", ax)
            out.append((n, f"{name} vs {axis}" if name else ""))
    return out


def figures_of(page, pno: int) -> list[dict]:
    """The figures a page prints: numbered captions (joined with the line that wraps them, or given the
    title printed over a legacy graph when the caption is only "Figure 8"), and bare "X vs Y" titles
    (joined with the line above when that is plainly the start of the same title), each with the
    condition lines printed within its column."""
    segments, _ = segments_of(page)
    found: list[dict] = []
    used: set[int] = set()
    for i, s in enumerate(segments):
        if i in used:
            continue
        m = CAPTION.match(s["text"])
        if m:
            n, title = m.group(1), (m.group(2) or "").strip(" .:")
            if title and not title[:1].isalnum() and title[:1] != "(":
                continue
            if title and title[:1].islower():
                continue
            j = below(segments, i)
            if j is not None and j not in used and wraps(title, segments[j]["text"]):
                title = (title + " " + segments[j]["text"]).strip()
                used.add(j)
            if not title:
                title = title_above(segments, i, used)
            used.add(i)
            found.append({"n": n, "page": pno, "title": title, "source": "caption", "seg": i})
    captions = [segments[k] for k in used if CAPTION.match(segments[k]["text"])]
    for i, s in enumerate(segments):
        if i in used or COND.search(s["text"]):
            continue
        t = s["text"]
        if any(overlaps(c, s) and 0 < c["y"] - s["y"] < 300 for c in captions):
            continue
        if BARE.match(t) and not re.search(r"(?i)^(table|section|chapter|\d)", t) and not re.search(r"\. |\.$", t) \
                and len(t.split()) <= 10 and wordy(t.split(" vs")[0]):
            title = t.strip()
            up = above(segments, i, 18.0)
            if up is not None and up not in used and prefix_of(segments[up]["text"], title):
                title = segments[up]["text"] + " " + title
                used.add(up)
            j = below(segments, i)
            if j is not None and j not in used and INCOMPLETE.search(title) and wraps(title, segments[j]["text"]):
                title = title + " " + segments[j]["text"]
                used.add(j)
            used.add(i)
            found.append({"n": "", "page": pno, "title": title, "source": "bare", "seg": i})
        elif VS_LINE.match(t):
            title = vs_title(segments, i, used)
            if title:
                found.append({"n": "", "page": pno, "title": title, "source": "bare", "seg": i})
    for f in found:
        s = segments[f["seg"]]
        printed = [o["text"] for j, o in enumerate(segments) if j != f["seg"] and overlaps(o, s)
                   and -20 <= s["y"] - o["y"] <= 230 and COND.search(o["text"]) and len(o["text"]) < 80]
        f["printed"] = " ; ".join(dict.fromkeys(printed))[:300]
        del f["seg"]
    return found


def prefix_of(up: str, title: str) -> bool:
    """Whether the line printed over a bare "X vs Y" title is the start of the same title: both in
    capitals, or the title plainly incomplete (begins in lower case, closes a bracket it never opened,
    names its quantity in one word), and the line above short and not a caption or a condition."""
    if CAPTION.match(up) or COND.search(up) or len(up) > 60 or VS_LINE.match(up) or re.search(r"\d{2}", up):
        return False
    quantity = re.split(r"\s+(?:vs\.?|versus)\s+", title, 1)[0]
    return ((all_caps(up) and all_caps(title)) or title[:1].islower() or title.count(")") > title.count("(")
            or len(quantity.split()) == 1 or bool(INCOMPLETE.search(up)))


def title_above(segments: list[dict], i: int, used: set) -> str:
    """The title a legacy TI sheet prints over its graph: found going up from the "Figure 8" caption
    within the figure's column, as the "vs" line between the quantity and the axis."""
    cap = segments[i]
    for j in range(i - 1, -1, -1):
        o = segments[j]
        if cap["y"] - o["y"] > 300:
            break
        if VS_LINE.match(o["text"]) and overlaps(o, cap) and j not in used:
            return vs_title(segments, j, used)
    return ""


def read(pdf: Path, maker: str) -> dict:
    """Everything the survey takes from one sheet."""
    import pymupdf
    doc = pymupdf.open(pdf)
    figs: list[dict] = []
    graphs: dict[str, str] = {}
    text_all = []
    images = 0
    for pno in range(doc.page_count):
        page = doc[pno]
        text_all.append(page.get_text("text"))
        images += len(page.get_images())
        _, rows = segments_of(page)
        for n, title in table_of_graphs(rows):
            for k in re.split(r"\s*,\s*", n):
                if k and title:
                    graphs.setdefault(k, title)
        figs += figures_of(page, pno + 1)
    for f in figs:          # a caption that is only a number, or a grade ("Figure 17. OP27A"): the Table of Graphs names it
        if f["n"] in graphs and (not f["title"] or re.fullmatch(r"[A-Z]{1,4}\d{2,5}[A-Z]?", f["title"])):
            f["title"], f["source"] = graphs[f["n"]], "table"
    for n, title in graphs.items():
        if not any(f["n"] == n for f in figs):
            figs.append({"n": n, "page": 0, "title": title, "source": "table", "printed": ""})
    # one figure per caption number; a bare title that a caption also carries is that caption's figure
    captioned = {normalise(f["title"]) for f in figs if f["source"] != "bare" and f["title"]}
    seen_n, seen_bare, out = set(), set(), []
    for f in figs:
        if f["source"] == "bare":
            k = normalise(f["title"])
            if k in captioned or k in seen_bare:
                continue
            seen_bare.add(k)
        else:
            if f["n"] in seen_n:
                continue
            seen_n.add(f["n"])
        out.append(f)
    out.sort(key=lambda f: (f["page"], figure_order(f["n"])))
    text = "\n".join(text_all)
    head = "\n".join(text_all[:2])
    meta = {"title": (doc.metadata or {}).get("title", "") or "", "pages": doc.page_count, "images": images}
    m = DOC_NUMBER.get(maker, re.compile(r"$^")).search(head)
    meta["document"] = m.group(1) if m else ""
    m = REVISION.search(meta["title"]) or REVISION.search(head)
    meta["revision"] = (m.group(1) or m.group(2)) if m else ""
    dates = DATE.findall(head)
    meta["date"] = dates[-1] if dates else ""
    conds = {k: Counter(re.sub(r"\s+", " ", v.strip()) for v in rx.findall(text)) for k, rx in COND_RES.items()}
    return {"figures": out, "meta": meta, "conditions": {k: c.most_common(15) for k, c in conds.items()}}


def figure_order(n: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", n)) or (0,)


# ---- fetching ----------------------------------------------------------------------------------------
def cdx(query: str) -> list[list[str]] | None:
    """The archive's captures, or None when the archive could not be asked: not the same as none."""
    r = http.get(f"{CDX}?{query}", ua=PROJECT_UA, delay=ARCHIVE_DELAY, timeout=180)
    if not r.ok:
        print(f"  cdx: {r.status} {r.why}", file=sys.stderr)
        return None
    try:
        return json.loads(r.text() or "[]")[1:]
    except ValueError:
        return []


def resolve(sheet: dict) -> tuple[str | None, str]:
    """(the address to fetch, the maker's own address it stands for): the first empty when the archive
    holds no capture, None when the archive could not be asked."""
    how = sheet["how"]
    if how == "direct":
        return sheet["url"], sheet["url"]
    if how == "wayback":
        bare = re.sub(r"^https?://", "", sheet["url"])
        rows = cdx(f"url={bare}&matchType=exact&filter=statuscode:200&filter=mimetype:application/pdf&fl=original,timestamp&output=json")
        if rows is None:
            return None, sheet["url"]
        row = max(rows, key=lambda r: r[1]) if rows else None
        return (f"https://web.archive.org/web/{row[1]}id_/{row[0]}", sheet["url"]) if row else ("", sheet["url"])
    rows = cdx(f"url={sheet['prefix']}&matchType=prefix&filter=statuscode:200&filter=mimetype:application/pdf"
               "&fl=original,timestamp&output=json&limit=20000")
    if rows is None:
        return None, ""
    rows = [r for r in rows if re.search(sheet["pick"], r[0].split("?")[0])]
    if not rows:
        return "", ""
    row = max(rows, key=lambda r: r[1])
    own = re.sub(r"^https?://([^/:]+)(:\d+)?", lambda m: "https://" + m.group(1).lower(), row[0]).split("?")[0]
    return f"https://web.archive.org/web/{row[1]}id_/{row[0]}", own


def fetch(sheet: dict, led: Ledger, store: Path) -> bool:
    """Fetch one sheet into the store and stamp the ledger; False when it could not be had."""
    key = sheet["id"]
    fetch_url, own = resolve(sheet)
    if fetch_url is None:                        # the archive could not be asked: tried again next run
        led.stamp(key, "fetch", url=own, http="0")
        print(f"{key}: the archive could not be reached", file=sys.stderr)
        return False
    if not fetch_url:
        led.stamp(key, "fetch", url=own, http="0", skip_reason="no capture found")
        print(f"{key}: no capture found", file=sys.stderr)
        return False
    r = http.get(fetch_url, ua=PROJECT_UA, delay=ARCHIVE_DELAY if "web.archive.org" in fetch_url else http.DELAY,
                 timeout=300, max_bytes=64 << 20)
    if not (r.ok and r.kind == "pdf"):
        led.stamp(key, "fetch", url=own, http=str(r.status), copy=fetch_url if fetch_url != own else "")
        print(f"{key}: {r.status} {r.kind or r.ctype} {r.why}".strip(), file=sys.stderr)
        return False
    store.mkdir(parents=True, exist_ok=True)
    (store / f"{key}.pdf").write_bytes(r.body)
    led.stamp(key, "fetch", url=own, copy=fetch_url if fetch_url != own else "", http="200", bytes=str(len(r.body)),
              sha256=r.sha256, pages=str(page_count(store / f"{key}.pdf")))
    return True


def page_count(pdf: Path) -> int:
    import pymupdf
    return pymupdf.open(pdf).page_count


# ---- publishing --------------------------------------------------------------------------------------
def registry(kind: str) -> dict:
    return yaml.safe_load(require(datasheet_survey_registry(kind), "the survey").read_text(encoding="utf-8"))


def csv_text(fields, rows) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def load_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def mapped(figures: list[dict]) -> list[dict]:
    """The figures with today's mapping, whatever they carried."""
    out = []
    for f in figures:
        tid, cat, bench = classify(f["title"])
        out.append({**f, "test": tid, "category": cat, "bench": bench})
    return out


def matrix(sheets: list[dict], figures: list[dict]) -> str:
    docs = [s["doc"] for s in sheets if s.get("figures") not in ("", "0", None)]
    counts: dict[str, Counter] = defaultdict(Counter)
    for f in figures:
        if f["test"] and f["test"] != "skip":
            counts[f["test"]][f["doc"]] += 1
    cats = {t[0]: (t[1], t[2]) for t in TESTS}
    rows = []
    for tid in [t[0] for t in TESTS]:
        row = {"test": tid, "category": cats[tid][0], "bench": cats[tid][1], "sheets": sum(1 for d in docs if counts[tid][d])}
        row.update({d: counts[tid][d] or "" for d in docs})
        rows.append(row)
    return csv_text(["test", "category", "bench", "sheets", *docs], rows)


def doc_section(kind: str, sheets: list[dict], figures: list[dict], conditions: list[dict]) -> str:
    """The evidence tables the characterisation document shows: the sheets read, the tests by category
    with how many sheets draw each, and the conditions most often named."""
    read = [s for s in sheets if s.get("figures") not in ("", "0", None)]
    out = ["", f"Survey of {len(read)} sheets read by `sei datasheets survey --kind {kind}` (reader `{READ_VERSION}`), "
           f"{sum(int(s['figures']) for s in read)} figure titles, {sum(int(s['mapped']) for s in read)} mapped to a test; "
           "the tables `data/datasheets/survey/" + kind + "/{sheets,figures,matrix,conditions}.csv` hold every row.", "",
           "| sheet | maker | document | revision | date | pages | figures | mapped | read from |", "|---|---|---|---|---|---|---|---|---|"]
    for s in sheets:
        link = f"[{s['part']}]({s['url']})" if s["url"] else s["part"]
        src = ("archive copy" if s["copy"] else "maker's site" if s.get("figures") not in ("", None)
               else f"not read: {s['why']}" if s["why"] else "not fetched yet")
        src = src.replace("HTTP 0", "the archive could not be reached")
        out.append(f"| {link} | {s['maker']} | {s['document']} | {s['revision']} | {s['date']} | {s['pages']} | {s['figures']} | {s['mapped']} | {src} |")
    docs_read = [s["doc"] for s in read]
    makers = sorted({s["maker"] for s in read})
    by_maker = {m: [s["doc"] for s in read if s["maker"] == m] for m in makers}
    present: dict[str, set] = defaultdict(set)
    for f in figures:
        if f["test"] and f["test"] != "skip":
            present[f["test"]].add(f["doc"])
    names = {"A": "A supply", "B": "B input DC", "C": "C range and rejection", "D": "D gain and frequency", "E": "E output",
             "F": "F large signal", "G": "G small signal", "H": "H noise", "I": "I distortion", "J": "J multichannel",
             "K": "K test circuits", "N": "N Norton amplifiers"}
    out += ["", f"Tests by category: how many of the {len(docs_read)} sheets draw each, in all and per maker "
            f"({', '.join(f'{m} {len(by_maker[m])}' for m in makers)}); `bench` is the measurement that draws the same graph for a model.", "",
            "| test | bench | sheets | " + " | ".join(makers) + " |", "|---|---|---|" + "---|" * len(makers)]
    last = ""
    for tid, cat, bench, _ in TESTS:
        if cat != last:
            out.append(f"| **{names.get(cat, cat)}** | | | " + " | ".join("" for _ in makers) + " |")
            last = cat
        n = len(present[tid])
        if not n:
            continue
        per = [str(sum(1 for d in by_maker[m] if d in present[tid]) or "") for m in makers]
        out.append(f"| `{tid}` | `{bench}` | {n} | " + " | ".join(per) + " |")
    unmapped = [f for f in figures if not f["test"]]
    out += ["", f"Titles no rule maps: {len(unmapped)} (listed in `figures.csv` with an empty `test`)."]
    allc: dict[str, Counter] = defaultdict(Counter)
    for c in conditions:
        allc[c["kind"]][c["value"]] += int(c["count"])
    out += ["", "Conditions named most often, over all sheets read (value, mentions):", ""]
    for k in COND_RES:
        if allc[k]:
            out.append(f"- **{k}**: " + ", ".join(f"{v} ({n})" for v, n in allc[k].most_common(12)))
    return "\n".join(out) + "\n"


def rewrite_doc(kind: str, section: str) -> bool:
    path = docs_dir() / DOCS[kind]
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    if MARK_START not in text or MARK_END not in text:
        return False
    a, b = text.index(MARK_START) + len(MARK_START), text.index(MARK_END)
    new = text[:a] + "\n" + section + text[b:]
    if new != text:
        path.write_text(new, encoding="utf-8")
        return True
    return False


def run(kind: str, do_fetch: bool = False, limit: int = 0, reread: bool = False, makers: list[str] | None = None) -> Counter:
    c: Counter = Counter()
    reg = registry(kind)
    led = Ledger(datasheet_survey_state(kind), stages=STAGES, fields=FIELDS, versioned=VERSIONED)
    store = datasheet_survey_store(kind)
    figures = {f["doc"]: [] for f in load_csv(datasheet_survey(kind, "figures"))}
    for f in load_csv(datasheet_survey(kind, "figures")):
        figures[f["doc"]].append(f)
    conditions = {}
    for r in load_csv(datasheet_survey(kind, "conditions")):
        conditions.setdefault(r["doc"], []).append(r)
    sheets_out = []
    read_meta = {s["doc"]: s for s in load_csv(datasheet_survey(kind, "sheets"))}
    for s in reg["sheets"]:
        key = s["id"]
        row = led.get(key) or {}
        pdf = store / f"{key}.pdf"
        if s["how"] == "none":
            led.stamp(key, "fetch", url=s.get("url", ""), skip_reason=s.get("why", "not fetched"))
        elif not pdf.exists() and do_fetch and (not limit or c["fetched"] < limit) and (not makers or s["maker"] in makers):
            c["fetched"] += fetch(s, led, store)
            led.save()                               # a run that dies keeps what it fetched
            row = led.get(key) or {}
        if pdf.exists() and (reread or not led.done(key, "read", READ_VERSION)) and (not makers or s["maker"] in makers):
            got = read(pdf, s["maker"])
            figures[key] = [{"doc": key, **f} for f in got["figures"]]
            conditions[key] = [{"doc": key, "kind": k, "value": v, "count": n} for k, lst in got["conditions"].items() for v, n in lst]
            read_meta[key] = {k: str(v) for k, v in got["meta"].items()}
            led.stamp(key, "read", version=READ_VERSION)
            c["read"] += 1
        row = led.get(key) or {}
        meta = read_meta.get(key, {})
        figs = mapped([f for f in figures.get(key, []) if f["title"]])
        untitled = sum(1 for f in figures.get(key, []) if not f["title"])
        figures[key] = figs
        sheets_out.append({"doc": key, "maker": s["maker"], "part": s["part"], "url": row.get("url") or s.get("url", ""),
                           "copy": row.get("copy", ""), "sha256": row.get("sha256", ""), "bytes": row.get("bytes", ""),
                           "pages": row.get("pages", ""), "images": meta.get("images", ""), "document": meta.get("document", ""), "revision": meta.get("revision", ""),
                           "date": meta.get("date", ""), "title": meta.get("title", ""),
                           "figures": str(len(figs)) if figs else ("0" if pdf.exists() else ""), "untitled": str(untitled) if pdf.exists() else "",
                           "mapped": str(sum(1 for f in figs if f["test"] and f["test"] != "skip")) if figs else "",
                           "how": s["how"], "why": s.get("why", "") or row.get("skip_reason", "")
                           or (f"HTTP {row['http']}" if row.get("http") not in (None, "", "200") else "")})
    led.save()
    all_figs = [f for s in sheets_out for f in figures.get(s["doc"], [])]
    all_conds = [r for s in sheets_out for r in conditions.get(s["doc"], [])]
    write(datasheet_survey(kind, "sheets"), csv_text(SHEET_FIELDS, sheets_out))
    write(datasheet_survey(kind, "figures"), csv_text(FIGURE_FIELDS, all_figs))
    write(datasheet_survey(kind, "conditions"), csv_text(CONDITION_FIELDS, all_conds))
    write(datasheet_survey(kind, "matrix"), matrix(sheets_out, all_figs))
    c["doc"] += rewrite_doc(kind, doc_section(kind, sheets_out, all_figs, all_conds))
    c["figures"] = len(all_figs)
    c["unmapped"] = sum(1 for f in all_figs if not f["test"])
    c["sheets"] = sum(1 for s in sheets_out if s["figures"] not in ("", "0"))
    return c


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--kind", default="opamp", help="the kind of part surveyed (its registry: data/datasheets/survey/<kind>.yaml)")
    ap.add_argument("--fetch", action="store_true", help="fetch the sheets the store does not hold, through the polite client")
    ap.add_argument("--limit", type=int, default=0, help="at most this many sheets fetched")
    ap.add_argument("--reread", action="store_true", help="read every sheet again with today's reader")
    ap.add_argument("--maker", action="append", help="only these makers' sheets are fetched or reread (repeatable)")
    args = ap.parse_args(argv)
    t0 = time.time()
    c = run(args.kind, do_fetch=args.fetch, limit=args.limit, reread=args.reread, makers=args.maker)
    print(f"{c['sheets']} sheets read ({c['read']} now, {c['fetched']} fetched): {c['figures']} figures, "
          f"{c['unmapped']} unmapped; doc {'rewritten' if c['doc'] else 'unchanged'}; {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
