"""The preview bench's results as one Markdown page: python3 bench_report.py results.json <out.md> [models dir]."""
import hashlib
import json
import sys
from pathlib import Path

r = json.load(open(sys.argv[1]))
out = Path(sys.argv[2])
models_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else None

# where each model came from (the recipe's `get`, data/models/parts/<kind>/<part>.yaml) and its file in the models dir
SOURCES = {
    "jfet/J201": ("Central Semiconductor", "https://www.centralsemi.com/docs/ENGINEERING/csm/J201.LIB", "J201_csm.LIB"),
    "jfet/2N5457": ("Central Semiconductor", "https://www.centralsemi.com/docs/ENGINEERING/csm/2N5457_CSM.LIB", "2N5457_CSM.LIB"),
    "jfet/2N3819": ("Central Semiconductor", "https://www.centralsemi.com/docs/ENGINEERING/csm/CSM1455.LIB", "CSM1455.LIB"),
    "mosfet/2N7000": ("Zetex, 2000, via LTwiki", "https://ltwiki.org/files/LTspiceIV/Vendor%20List/Zetex/2n7000.lib", "zetex_2n7000.lib"),
    "mosfet/BS170": ("Diodes Incorporated (BS170P)", "https://www.diodes.com/spice/download/4537/BS170P.spice.txt", "BS170P.spice.txt"),
    "mosfet/IRF510": ("International Rectifier, 1988, via LTwiki (pwrmos.lib, the IRF510 card alone)", "https://ltwiki.org/files/LTspiceIV/Vendor%20List/Spice-Models-collection/pwrmos.lib", "irf510.lib"),
    "opamp/TL072": ("Texas Instruments, PSpice PARTS 1989", "https://www.ti.com/lit/zip/SLOJ067", "TL072.301"),
    "opamp/NE5532": ("Texas Instruments, PSpice PARTS 1989, via the LTwiki collection (lib/sub/NE553x.lib)", "http://bordodynov.ltwiki.org/lib.zip", "NE553x.lib"),
    "opamp/RC4558": ("Texas Instruments, PSpice PARTS 1989", "https://www.ti.com/lit/zip/SLOJ053", "RC4558.301"),
}


def si(x, unit=""):
    if x is None:
        return "n/a"
    if isinstance(x, str):
        return x
    if isinstance(x, bool):
        return "yes" if x else "no"
    if x == 0:
        return f"0 {unit}"
    pre = [(1e9, "G"), (1e6, "M"), (1e3, "k"), (1, ""), (1e-3, "m"), (1e-6, "µ"), (1e-9, "n"), (1e-12, "p"), (1e-15, "f")]
    for s, p in pre:
        if abs(x) >= s * 0.9995:
            return f"{x / s:.3g} {p}{unit}"
    return f"{x:.3g} {unit}"


def db(x):
    return "n/a" if x is None else (x if isinstance(x, str) else f"{x:.1f} dB")


def table(title, parts, rows):
    lines = [f"### {title}", "", "| | " + " | ".join(parts) + " |", "|---|" + "---|" * len(parts)]
    for label, key, unit in rows:
        cells = []
        for p in parts:
            v = r.get(p, {}).get(key)
            cells.append(db(v) if unit == "dB" else ("%.1f %%" % v if unit == "%" and isinstance(v, float) else cell(v, unit)))
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def cell(v, unit):
    if isinstance(v, (list, tuple)) and v and not isinstance(v[0], (list, tuple)):
        return ", ".join(si(x, unit) if isinstance(x, (int, float)) else str(x) for x in v)
    if isinstance(v, (list, tuple)):
        return "; ".join(" / ".join(si(x) if isinstance(x, (int, float)) else str(x) for x in row) for row in v)
    return si(v, unit)


def facts(title, parts):
    lines = [f"### {title}", "", "| | " + " | ".join(names(parts)) + " |", "|---|" + "---|" * len(parts)]
    keys = ["family", "pins", "model types", "transistors (temperature and shot noise carriers)", "behavioural sources", "supply resistor RP",
            "flicker noise (KF/AF)", "temperature coefficients (TC1/TC2/XTI/EG)", "transit time (TT/TF)", "breakdown (BV)"]
    for k in keys:
        cells = []
        for p in parts:
            v = r.get(p, {}).get("card", {}).get(k)
            cells.append(" ".join(v) if isinstance(v, list) else str(v))
        lines.append(f"| {k} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def series(title, parts, key, xunit, yunit):
    lines = [f"**{title}**", ""]
    for p in parts:
        s = r.get(p, {}).get(key)
        if isinstance(s, list) and s and isinstance(s[0], list):
            lines.append(f"- {p.split('/')[1]}: " + ", ".join(f"{si(x, xunit)} → {si(y, yunit)}" for x, y in s))
    return "\n".join(lines) + "\n"


J = ["jfet/J201", "jfet/2N5457", "jfet/2N3819"]
M = ["mosfet/2N7000", "mosfet/BS170", "mosfet/IRF510"]
A = ["opamp/TL072", "opamp/NE5532", "opamp/RC4558"]
def names(ps):
    return [p.split("/")[1] for p in ps]

names_ = names

doc = ["# Preview of the FET and op-amp benches on ngspice", "",
       "One model per part, ngspice 42 on this machine (the project's pinned image carries ngspice 47; QSPICE and "
       "LTspice were not available here). The decks are the draft of `decks_jfet`, `decks_mos` and `decks_opamp` "
       "for the measurements of `docs/fet-characterisation.md` and `docs/opamp-characterisation.md`; the numbers are "
       "what each model does, not the published characterisation, which comes through `measurements.yaml`, the "
       "pinned images and the records. 25 °C unless said; `n/a` is a point the model never reached.", "",
       f"Noise calibration: ngspice's `inoise_spectrum` for a 1 kΩ source resistance reads {si(r['ngspice_inoise_1k'], 'V/√Hz')} "
       "(4.07 nV/√Hz expected), so it is a density in V/√Hz.", "",
       "## Models", "", "| part | published by | address | sha256 of the file read |", "|---|---|---|---|"]
for key, (who, url, fname) in SOURCES.items():
    sha = hashlib.sha256((models_dir / fname).read_bytes()).hexdigest() if models_dir and (models_dir / fname).exists() else "(models dir not given)"
    doc.append(f"| {key.split('/')[1]} | {who} | {url} | `{sha}` |")
doc += ["", "## JFETs", "",
       "Models: J201, 2N5457 and 2N3819 as Central Semiconductor publishes them (Shichman-Hodges cards with the "
       "LTspice gate-current extensions, which ngspice ignores with a warning).", ""]
doc.append(table("Transfer (jfet-transfer, jfet-gm, jfet-temperature)", J, [
    ("IDSS at VDS = 10 V", "idss@10V", "A"), ("IDSS at 5 V", "idss@5V", "A"), ("IDSS at 15 V", "idss@15V", "A"),
    ("VGS(off) at ID = 1 µA, 10 V", "vgsoff@1uA,10V", "V"), ("VGS(off) at 10 nA", "vgsoff@10nA,10V", "V"),
    ("gfs at VGS = 0, 10 V", "gfs@0V,10V", "S"), ("gm at ID = 100 µA", "gm@100µA,10V", "S"), ("gm at 1 mA", "gm@1mA,10V", "S"),
    ("gm at 5 mA", "gm@5mA,10V", "S"), ("VGS at 100 µA", "vgs@100µA,10V", "V"), ("VGS at 1 mA", "vgs@1mA,10V", "V"),
    ("IDSS at −55 °C", "idss@10V,-55C", "A"), ("IDSS at 125 °C", "idss@10V,125C", "A"),
    ("VGS(off) at −55 °C", "vgsoff@1uA,10V,-55C", "V"), ("VGS(off) at 125 °C", "vgsoff@1uA,10V,125C", "V")]))
doc.append(table("Output characteristics (jfet-tracer)", J, [
    ("ID at 10 V, VGS = 0", "id@10V,vgs=0", "A"), ("knee (90 % of ID at 15 V)", "knee90%@vgs=0", "V"), ("ro at 10 V, VGS = 0", "ro@10V,vgs=0", "Ω")]))
for p in J:
    s, i = r[p].get("tracer_steps"), r[p].get("tracer_id@10V")
    if s and i:
        doc.append(f"- {p.split('/')[1]} traces at 10 V, VGS steps a fifth of VGS(off): " + ", ".join(f"{a:+.3g} V → {si(b, 'A')}" for a, b in zip(s, i)))
doc.append("")
doc.append(table("Gate, capacitances and noise (jfet-gate, jfet-capacitance, jfet-noise)", J, [
    ("IGSS at VGS = −15 V", "igss@-15V", "A"), ("VGS(forward) at IG = 1 mA", "vgs(fwd)@1mA", "V"),
    ("noise stage ID", "noise_id", "A"), ("en at 10 Hz (VDS = 10 V)", "en@10Hz", "V/√Hz"), ("en at 1 kHz", "en@1kHz", "V/√Hz"), ("en at 10 kHz", "en@10kHz", "V/√Hz"), ("1/f corner", "1/f corner", "Hz")]))
doc.append(table("Ohmic region, gm against frequency, the analogue switch, a stage's distortion, breakdown (jfet-ohmic, jfet-frequency, jfet-switch, jfet-distortion, jfet-breakdown)", J, [
    ("rDS(on) at VGS = 0, VDS = 0", "rds_on@vgs=0", "Ω"), ("gm at 1 kHz (stage current)", "gm@1kHz", "S"), ("f where |id/ig| = 1", "f(|id/ig|=1)", "Hz"),
    ("switch t_on 10–90 % (1 V into 10 kΩ ‖ 100 pF)", "t_on(10-90)", "s"), ("switch t_off 90–10 %", "t_off(90-10)", "s"), ("on level (1 V in)", "v_on (1 V through 10 kΩ)", "V"),
    ("stage current", "noise_id", "A"), ("stage gain (RD for VDS = 10 V)", "stage gain", ""), ("THD, 100 mVpk at 1 kHz", "thd(cs stage, 100mVpk)", ""),
    ("ID off at 30 V", "id(off)@30V", "A"), ("ID off at 60 V", "id(off)@60V", "A"), ("breakdown", "breakdown", "")]))
doc.append(series("Ciss against VGS at VDS = 15 V, 1 MHz", J, "ciss_vs_vgs@15V", "V", "F"))
doc.append(series("Crss against VGS at VDS = 15 V, 1 MHz", J, "crss_vs_vgs@15V", "V", "F"))
doc.append(series("Cgs (Ciss − Crss) against VGS at VDS = 15 V", J, "cgs_vs_vgs@15V", "V", "F"))
doc.append(series("Cgd against VDG at VGS = 0", J, "cgd_vs_vdg@vgs=0", "V", "F"))
doc.append(table("The rest of the JFET bench (jfet-gate, jfet-switch, jfet-distortion, jfet-temperature)", J, [
    ("gate leakage: VGS, VDS, IG, drain's share, source's share", "gate leakage (VGS, VDS, IG, ID share, IS share)", "A"),
    ("charge injection into 1 nF at turn-off", "charge injection (1 nF hold)", "C"), ("THD of a source follower, 1 Vpk", "thd(source follower, 1 Vpk)", ""),
    ("IDSS at 100 °C", "idss@10V,100C", "A"), ("IDSS at 150 °C", "idss@10V,150C", "A"), ("VGS(off) at 150 °C", "vgsoff@1uA,10V,150C", "V"),
    ("VGS at 100 µA, −55 °C", "vgs@100uA,10V,-55C", "V"), ("VGS at 100 µA, 125 °C", "vgs@100uA,10V,125C", "V"),
    ("zero-TC point (VGS, ID)", "zero-TC point (VGS, ID)", ""), ("agreement", "agreement", "")]))
doc.append(facts("What the card says (jfet-card)", J))
doc += ["## MOSFETs", "",
        "Models: 2N7000 as Zetex published it in 2000 (a level-1 subcircuit with its own body diode), BS170 as Diodes "
        "Incorporated publishes BS170P (subcircuit), IRF510 as International Rectifier's 1988 level-3 card.", ""]
doc.append(table("Transfer and threshold (mos-transfer, mos-gm, mos-temperature)", M, [
    ("Vth at ID = 250 µA, VDS = 5 V", "vth@250uA,5V", "V"), ("Vth at 1 mA", "vth@1mA,5V", "V"),
    ("ID at VGS = 3 V", "id@vgs=3V,5V", "A"), ("ID at 4.5 V", "id@vgs=4.5V,5V", "A"), ("ID at 5 V", "id@vgs=5V,5V", "A"), ("ID at 10 V", "id@vgs=10V,5V", "A"),
    ("gfs at 10 mA", "gfs@10mA,5V", "S"), ("gfs at 100 mA", "gfs@100mA,5V", "S"), ("gfs at 1 A", "gfs@1A,5V", "S"),
    ("Vth at 1 mA, −55 °C", "vth@1mA,5V,-55C", "V"), ("Vth at 1 mA, 125 °C", "vth@1mA,5V,125C", "V"),
    ("ID at 10 V, −55 °C", "id@vgs=10V,5V,-55C", "A"), ("ID at 10 V, 125 °C", "id@vgs=10V,5V,125C", "A")]))
doc.append(table("On-resistance and body diode (mos-rdson, mos-body-diode)", M, [
    ("RDS(on) at VGS = 4.5 V, VDS = 0.1 V", "rdson@vgs=4.5V,0.1V", "Ω"), ("RDS(on) at VGS = 10 V, VDS = 0.1 V", "rdson@vgs=10V,0.1V", "Ω"),
    ("VSD at 100 mA", "vsd@100mA", "V"), ("VSD at 1 A", "vsd@1A", "V")]))
for p in M:
    s = r[p].get("tracer_id@10V")
    if s:
        doc.append(f"- {p.split('/')[1]} ID at VDS = 10 V per VGS step: " + ", ".join(f"{a:g} V → {si(b, 'A')}" for a, b in s))
doc.append("")
doc.append(table("Gate charge, switching, reverse recovery, noise, distortion, breakdown (mos-gate-charge, mos-switching, mos-body-diode, mos-noise, mos-distortion, mos-breakdown)", M, [
    ("conditions", "switch conditions", ""), ("Qg to VGS = 10 V (IG = 100 µA)", "qg@10V", "C"), ("Qgs, to the plateau", "qgs (to plateau)", "C"), ("Qgd, the plateau", "qgd (plateau)", "C"), ("plateau voltage", "v_plateau", "V"),
    ("td(on)", "td(on)", "s"), ("tr", "tr", "s"), ("td(off)", "td(off)", "s"), ("tf", "tf", "s"),
    ("IRM", "irm", "A"), ("trr", "trr", "s"), ("reverse recovery", "reverse recovery", ""),
    ("en at 10 Hz (ID = 10 mA)", "en@10Hz", "V/√Hz"), ("en at 1 kHz", "en@1kHz", "V/√Hz"), ("1/f", "1/f", ""), ("THD of a 10 mA stage, 100 mVpk", "thd(cs stage, 100mVpk)", ""),
    ("IDSS at 60 V", "idss@60V", "A"), ("IDSS at 100 V", "idss@100V", "A"), ("breakdown", "breakdown", "")]))
doc.append(series("Ciss against VDS (VGS = 0, 1 MHz)", M, "ciss_vs_vds", "V", "F"))
doc.append(series("Coss against VDS", M, "coss_vs_vds", "V", "F"))
doc.append(series("Crss against VDS", M, "crss_vs_vds", "V", "F"))
doc.append(series("Ciss against VGS at VDS = 0", M, "ciss_vs_vgs@vds=0", "V", "F"))
doc.append(table("RDS(on) against current and drive, third quadrant, inductive switching, follower (mos-rdson, mos-body-diode, mos-switching, mos-distortion)", M, [
    ("RDS(on) vs ID at VGS = 10 V (A / Ω)", "rdson_vs_id@vgs=10V", ""), ("RDS(on) vs ID at VGS = 4.5 V", "rdson_vs_id@vgs=4.5V", ""),
    ("drive floor (RDS(on) < 2× its 10 V value)", "drive floor (RDS(on) < 2× its 10 V value)", "V"),
    ("VSD at 100 mA with the channel on (VGS = 10 V)", "vsd@100mA,vgs=10V (channel on)", "V"), ("VSD at 1 A, channel on", "vsd@1A,vgs=10V (channel on)", "V"),
    ("inductive conditions", "inductive conditions", ""), ("Eon (clamped inductive)", "eon (2nd pulse, 300 ns window)", "J"), ("Eoff", "eoff (300 ns window)", "J"),
    ("THD of a source follower, 1 Vpk, 10 mA", "thd(source follower, 1 Vpk)", "")]))
doc.append(table("Temperature (mos-temperature)", M, [
    ("Vth at 1 mA, −55 °C", "vth@1mA,5V,-55C", "V"), ("100 °C", "vth@1mA,5V,100C", "V"), ("125 °C", "vth@1mA,5V,125C", "V"), ("150 °C", "vth@1mA,5V,150C", "V"), ("175 °C", "vth@1mA,5V,175C", "V"),
    ("RDS(on) at 10 V, −55 °C", "rdson@vgs=10V,-55C", "Ω"), ("125 °C", "rdson@vgs=10V,125C", "Ω"), ("175 °C", "rdson@vgs=10V,175C", "Ω"),
    ("gfs at 100 mA, −55 °C", "gfs@100mA,-55C", "S"), ("125 °C", "gfs@100mA,125C", "S"), ("175 °C", "gfs@100mA,175C", "S"),
    ("VSD at 100 mA, −55 °C", "vsd@100mA,-55C", "V"), ("125 °C", "vsd@100mA,125C", "V"), ("175 °C", "vsd@100mA,175C", "V"),
    ("zero-TC point (VGS, ID)", "zero-TC point (VGS, ID)", ""), ("agreement", "agreement", "")]))
doc.append(facts("What the card says (mos-card)", M))
doc += ["## Op-amps", "",
        "Models: TL072 and RC4558 as TI publishes them (PSpice PARTS macromodels of 1989, Boyle family), NE5532 TI's PARTS "
        "macromodel of the same year as the LTwiki collection carries it. One amplifier each, ±15 V unless said, "
        "RL = 2 kΩ, CL = 100 pF for the dynamic decks.", ""]
doc.append(table("Supply, input and offset (opa-runs, opa-iq, opa-bias, opa-offset)", A, [
    ("IQ at ±5 V", "iq@±5V", "A"), ("IQ at ±9 V", "iq@±9V", "A"), ("IQ at ±15 V", "iq@±15V", "A"), ("IQ at ±18 V", "iq@±18V", "A"),
    ("VOS at ±15 V", "vos@±15V", "V"), ("VOS at ±5 V", "vos@±5V", "V"), ("IB+", "ib+", "A"), ("IB−", "ib-", "A"), ("IOS", "ios", "A"),
    ("VICR−", "vicr-", "V"), ("VICR+", "vicr+", "V"), ("CMRR (DC, from VOS vs VCM)", "cmrr_dc", "dB"),
    ("phase reversal within the rails", "reversal_within_rails", ""), ("phase reversal 1 V beyond the rails", "reversal_1V_beyond_rails", "")]))
doc.append(table("Gain, bandwidth and rejection (opa-aol, opa-cmrr-f, opa-psrr-f)", A, [
    ("AOL (DC)", "aol_dc", "dB"), ("dominant pole", "f_p1", "Hz"), ("GBW read at 10 kHz", "gbw@10kHz", "Hz"), ("GBW read at 100 kHz", "gbw@100kHz", "Hz"),
    ("unity-gain frequency (2 kΩ ‖ 100 pF)", "f_unity", "Hz"), ("phase margin", "phase_margin", "°"),
    ("CMRR at 100 Hz", "cmrr@100Hz", "dB"), ("CMRR at 1 kHz", "cmrr@1kHz", "dB"), ("CMRR at 100 kHz", "cmrr@100kHz", "dB"),
    ("PSRR+ at 100 Hz", "psrr+@100Hz", "dB"), ("PSRR+ at 10 kHz", "psrr+@10kHz", "dB"), ("PSRR− at 100 Hz", "psrr-@100Hz", "dB"), ("PSRR− at 10 kHz", "psrr-@10kHz", "dB")]))
doc.append(table("Output (opa-swing, opa-isc, opa-zout)", A, [
    ("VOM+ into 600 Ω", "vom+@600Ω", "V"), ("VOM+ into 2 kΩ", "vom+@2kΩ", "V"), ("VOM+ into 10 kΩ", "vom+@10kΩ", "V"),
    ("VOM− into 600 Ω", "vom-@600Ω", "V"), ("VOM− into 2 kΩ", "vom-@2kΩ", "V"), ("ISC+", "isc+", "A"), ("ISC−", "isc-", "A"),
    ("ZO closed-loop (G = 1) at 1 kHz", "zo_cl@1kHz", "Ω"), ("at 100 kHz", "zo_cl@100kHz", "Ω"), ("at 1 MHz", "zo_cl@1MHz", "Ω"),
    ("ZO open-loop at 1 kHz", "zo_ol@1kHz", "Ω"), ("ZO open-loop at 1 MHz", "zo_ol@1MHz", "Ω")]))
doc.append(table("Dynamics, noise and distortion (opa-slew, opa-step, opa-noise, opa-thd-f)", A, [
    ("SR rising (10 V step, G = 1)", "sr+", "V/s"), ("SR falling", "sr-", "V/s"), ("rise time 10–90 %, 10 mV step", "tr(10-90)@100pF", "s"),
    ("overshoot, 10 mV step, 100 pF", "overshoot@100pF", "%"), ("en at 10 Hz (RS = 0)", "en@10Hz", "V/√Hz"), ("en at 1 kHz", "en@1kHz", "V/√Hz"),
    ("en at 10 kHz", "en@10kHz", "V/√Hz"), ("THD at 1 kHz, 3 Vrms, 2 kΩ, G = 1", "thd@1kHz,3Vrms,2k", ""), ("H2/H1", "h2/h1", ""), ("H3/H1", "h3/h1", "")]))
doc.append(table("Large signal and settling (opa-settling, opa-overload, opa-max-vo-f, opa-thd-level, opa-aol-swing)", A, [
    ("settling to 0.1 %, 2 V step", "ts@0.1%,2V", "s"), ("to 0.01 %, 2 V", "ts@0.01%,2V", "s"), ("to 0.1 %, 10 V", "ts@0.1%,10V", "s"), ("to 0.01 %, 10 V", "ts@0.01%,10V", "s"),
    ("overload recovery, G = −10, 1.2·VS", "trec(−)", "s"), ("output while overloaded", "vout(overloaded)", "V"),
    ("full-power bandwidth from SR and VOM", "fpbw (SR/2πVOM)", "Hz"), ("THD at 10 Vpk, 20 kHz", "thd@10Vpk,20kHz", ""), ("at 50 kHz", "thd@10Vpk,50kHz", ""), ("at 100 kHz", "thd@10Vpk,100kHz", ""),
    ("output at 10 Vpk in, 100 kHz", "vopk@100kHz", "V"),
    ("THD at 1 kHz, 0.1 Vrms", "thd@1kHz,0.1Vrms", ""), ("1 Vrms", "thd@1kHz,1Vrms", ""), ("6 Vrms", "thd@1kHz,6Vrms", ""), ("10 Vrms (clipping)", "thd@1kHz,10Vrms", ""),
    ("AOL over ±10 V (DC, 2 kΩ)", "aol@±10V,2k", "V/V"), ("AOL over ±13 V", "aol@±13V,2k", "V/V")]))
doc.append(table("Closed loop, stability and the rest (opa-closed-loop, opa-stability, opa-noise-rs, opa-emirr, opa-separation)", A, [
    ("−3 dB bandwidth at G = 10", "bw@G=10", "Hz"), ("G = 100", "bw@G=100", "Hz"), ("G = 1000", "bw@G=1000", "Hz"), ("G = −1", "bw@G=-1", "Hz"),
    ("phase margin at CL = 10 pF", "pm@10pF", "°"), ("100 pF", "pm@100pF", "°"), ("1 nF", "pm@1nF", "°"), ("10 nF", "pm@10nF", "°"),
    ("overshoot, 100 mV step, 100 pF", "overshoot(100mV)@100pF", "%"), ("1 nF", "overshoot(100mV)@1nF", "%"),
    ("total noise at 1 kHz, RS = 1 kΩ", "vt@1kHz,rs=1kΩ", "V/√Hz"), ("RS = 10 kΩ", "vt@1kHz,rs=10kΩ", "V/√Hz"), ("RS = 100 kΩ", "vt@1kHz,rs=100kΩ", "V/√Hz"), ("RS = 1 MΩ", "vt@1kHz,rs=1MΩ", "V/√Hz"),
    ("in at 1 kHz, from RS = 100 kΩ", "in@1kHz (from RS=100k)", "A/√Hz"),
    ("EMIRR, 100 mVpk at 100 MHz", "emirr@100MHz", "dB"), ("channel separation", "channel separation", "")]))
doc.append(table("Against temperature, supply and common mode (opa-iq, opa-offset, opa-bias, opa-aol, opa-swing, opa-isc)", A, [
    ("turn-on: settled 10 mV after a ±3 → ±15 V ramp at 0.3 V/µs", "turn-on (settled 10 mV after a ±3→±15 V ramp at 0.3 V/µs)", "s"),
    ("VOS at −55 °C", "vos@-55C", "V"), ("VOS at 125 °C", "vos@125C", "V"), ("offset drift", "offset drift", "V/°C"),
    ("IB+ at −55 °C", "ib+@-55C", "A"), ("IB+ at 125 °C", "ib+@125C", "A"), ("IB+ at VCM = −13 V", "ib+@vcm=-13V", "A"), ("IB+ at VCM = +13 V", "ib+@vcm=13V", "A"),
    ("IQ at −55 °C", "iq@-55C", "A"), ("IQ at 125 °C", "iq@125C", "A"),
    ("ZICM at 1 kHz", "zicm@1kHz", "Ω"), ("ZICM at 1 MHz", "zicm@1MHz", "Ω"), ("CICM", "cicm (from 1 MHz)", "F"), ("ZID at 1 kHz", "zid@1kHz", "Ω"), ("ZID at 1 MHz", "zid@1MHz", "Ω"),
    ("CMRR at 1 kHz, VCM = −13 V", "cmrr@1kHz,vcm=-13V", "dB"), ("VCM = +13 V", "cmrr@1kHz,vcm=13V", "dB"), ("PSRR both rails, 100 Hz", "psrr(both)@100Hz", "dB"), ("10 kHz", "psrr(both)@10kHz", "dB"),
    ("EMIRR at 10 MHz", "emirr@10MHz", "dB"), ("400 MHz", "emirr@400MHz", "dB"), ("1 GHz", "emirr@1GHz", "dB"),
    ("AOL (DC) into 600 Ω", "aol_dc@600Ω", "dB"), ("into 10 kΩ", "aol_dc@10kΩ", "dB"), ("at ±5 V", "aol_dc@±5V", "dB"), ("at ±9 V", "aol_dc@±9V", "dB"), ("at −55 °C", "aol_dc@-55C", "dB"), ("at 125 °C", "aol_dc@125C", "dB"),
    ("GBW at 100 kHz, 600 Ω", "gbw@100kHz,600Ω", "Hz"), ("at ±5 V", "gbw@100kHz,±5V", "Hz"), ("at −55 °C", "gbw@100kHz,-55C", "Hz"), ("at 125 °C", "gbw@100kHz,125C", "Hz"),
    ("phase margin into 600 Ω", "pm@600Ω", "°"), ("at ±5 V", "pm@±5V", "°"), ("at 125 °C", "pm@125C", "°"),
    ("VOM+ at ±5 V", "vom+@2kΩ,±5V", "V"), ("VOM− at ±5 V", "vom-@2kΩ,±5V", "V"), ("VOM+ at ±9 V", "vom+@2kΩ,±9V", "V"), ("VOM+ at −55 °C", "vom+@2kΩ,-55C", "V"), ("VOM+ at 125 °C", "vom+@2kΩ,125C", "V"),
    ("ISC+ at ±5 V", "isc+@±5V", "A"), ("ISC+ at −55 °C", "isc+@-55C", "A"), ("ISC+ at 125 °C", "isc+@125C", "A"),
    ("VOUT vs IOUT sourcing (A / V)", "vo_vs_io (sourcing)", ""),
    ("ZO closed loop at 1 kHz, G = 10", "zo@1kHz,G=10", "Ω"), ("G = 100", "zo@1kHz,G=100", "Ω"), ("G = 1000", "zo@1kHz,G=1000", "Ω"), ("at 100 kHz, G = 10", "zo@100kHz,G=10", "Ω")]))
doc.append(table("Dynamics, the rest (opa-stability, opa-slew, opa-settling, opa-overload, opa-phase-reversal)", A, [
    ("peaking at G = 100, RT = 100 Ω", "peak@G=100,rt=100Ω", "dB"), ("RT = 1 kΩ", "peak@G=100,rt=1kΩ", "dB"), ("RT = 10 kΩ", "peak@G=100,rt=10kΩ", "dB"), ("RT = 100 kΩ", "peak@G=100,rt=100kΩ", "dB"),
    ("SR at G = −1, 100 pF", "sr@G=-1,100pF", "V/s"), ("SR at G = 1, 20 pF", "sr@G=1,20pF", "V/s"), ("SR, 2 V step", "sr@2V,G=1", "V/s"), ("SR, 20 V step", "sr@20V,G=1", "V/s"),
    ("SR at ±5 V (4 V step)", "sr@±5V,G=1", "V/s"), ("SR at 125 °C", "sr@125C,G=1", "V/s"),
    ("settling to 0.1 %, 10 V, G = −1", "ts@0.1%,10V,G=-1", "s"), ("to 0.01 %", "ts@0.01%,10V,G=-1", "s"), ("positive overload recovery", "trec(+)", "s"),
    ("input current at +16 V", "iin@+16V", "A"), ("at −16 V", "iin@-16V", "A"), ("at +14 V", "iin@+14V", "A")]))
doc.append(table("Noise, weighted and integrated (opa-noise, opa-noise-rs)", A, [
    ("en rms 0.1–10 Hz", "en rms 0.1-10Hz", "V"), ("en p-p 0.1–10 Hz (6.6 × rms)", "en p-p 0.1-10Hz (6.6×rms)", "V"), ("en rms 10 Hz–10 kHz", "en rms 10Hz-10kHz", "V"), ("en rms 20 Hz–20 kHz", "en rms 20Hz-20kHz", "V"),
    ("en at 1 kHz, ±5 V", "en@1kHz,±5V", "V/√Hz"),
    ("flat 20 Hz–20 kHz, RS = 300 Ω", "en rms flat 20Hz-20kHz, rs=300Ω", "V"), ("A-weighted, RS = 300 Ω", "en rms A-weighted, rs=300Ω", "V"), ("RIAA-weighted (30 kHz), RS = 2.2 kΩ", "en rms RIAA-weighted (30 kHz), rs=2200Ω", "V"),
    ("A-weighted, RS = 2.2 kΩ", "en rms A-weighted, rs=2200Ω", "V")]))
doc.append(table("Distortion against frequency, load, and intermodulation (opa-thd-f, opa-thd-load, opa-imd)", A, [
    ("THD at 20 Hz, 3 Vrms, G = 1", "thd@20Hz,3Vrms,G=1", ""), ("100 Hz", "thd@100Hz,3Vrms,G=1", ""), ("1 kHz", "thd@1kHz,3Vrms,G=1", ""), ("10 kHz", "thd@10kHz,3Vrms,G=1", ""), ("20 kHz", "thd@20kHz,3Vrms,G=1", ""),
    ("THD at 1 kHz, 1 Vrms, G = 1", "thd@1kHz,1Vrms,G=1", ""), ("20 kHz, 1 Vrms, G = 1", "thd@20kHz,1Vrms,G=1", ""),
    ("THD at 1 kHz, 3 Vrms, G = 10", "thd@1kHz,3Vrms,G=10", ""), ("10 kHz, G = 10", "thd@10kHz,3Vrms,G=10", ""), ("20 kHz, G = 10", "thd@20kHz,3Vrms,G=10", ""), ("20 Hz, G = 10", "thd@20Hz,3Vrms,G=10", ""),
    ("THD at 1 kHz, 3 Vrms into 100 Ω", "thd@1kHz,3Vrms,rl=100Ω", ""), ("output into 100 Ω (3 Vrms in)", "vout@3Vrms in,rl=100Ω", "V"), ("into 300 Ω", "thd@1kHz,3Vrms,rl=300Ω", ""), ("into 600 Ω", "thd@1kHz,3Vrms,rl=600Ω", ""), ("into 10 kΩ", "thd@1kHz,3Vrms,rl=10kΩ", ""),
    ("IMD SMPTE (60 Hz + 7 kHz 4:1, 3 Vrms)", "imd SMPTE (60 Hz + 7 kHz 4:1, 3 Vrms)", ""), ("IMD CCIF (19 + 20 kHz, 3 Vrms)", "imd CCIF (19 + 20 kHz, 3 Vrms)", "")]))
doc.append(facts("What the model text says (opa-card)", A))
doc += ["## What the models cannot do, as the numbers say it", "",
        "- The three JFET cards have no 1/f noise term (KF): en is flat to 10 Hz and the corner the bench finds is the "
        "card's thermal floor meeting its own flat value, not a 1/f corner. Their gate leakage at −15 V is the card's IS "
        "(30 pA), not a measured IGSS. The 2N3819 card has LAMBDA = 0.02 and draws the Early slope; the J201 card's "
        "LAMBDA gives ro of megohms.",
        "- The MOSFET cards' Ciss and Crss do not move with VDS (level 1 and 3 give Cgs and Cgd as constants per width); only "
        "Coss, which is the body-diode junction, falls with voltage. None recovers in reverse: the body diode's current "
        "collapses in a capacitive spike, because a level-3 card's TT is not read and the Zetex and Diodes subcircuits give "
        "their diode none. None breaks down: the current at 100 V is the leakage at 60 V scaled by the card's RDS or IS. The "
        "2N7000 subcircuit leaks 10 µA at 60 V through a resistor across the channel.",
        "- The op-amp macromodels (Boyle family, 1989) give one VOS whatever the supply or common mode, bias currents equal on "
        "both inputs, PSRR flat with frequency (the supply enters only through the output stage's clamps), an output swing "
        "that does not depend on the load (13.5 V into 600 Ω as into 10 kΩ), no distortion beyond slew and clipping (THD of "
        "a few parts per million at 3 Vrms), and a white noise density only. The TL072 model's supply current scales with "
        "the supply through its RP resistor: 14 mA at ±15 V where the sheet's amplifier draws 1.4 mA, which is a known "
        "trait of the PARTS macromodels and the first thing a reader of the page should see.",
        "- All three op-amp models reverse the output's phase when the input goes 1 V beyond a rail, and none within the rails. "
        "With both rails modulated in antiphase the PSRR reads above 240 dB: the macromodel's supply paths are symmetric and "
        "cancel, which no real part does. The gain peaking against the feedback network's resistance (RT) is zero at every RT "
        "because the model has no input capacitance to speak of (CICM below a femtofarad).",
        "- The clamped-inductive switching deck is the fixture with the inductor replaced by a current source and a freewheel "
        "diode; the 2N7000 and BS170 subcircuits' Eon/Eoff are what their level-1 channel plus a constant Cgd give.",
        "", "## Next", "",
        "The same decks in QSPICE and LTspice on the maintainer's machine, through `measurements.yaml` entries so the "
        "numbers carry their conditions and the catalogue version; the transients of the FET benches (switching, gate charge, "
        "reverse recovery), the op-amps' settling, overload, max VO vs f and channel separation; and the datasheet figures "
        "of the survey beside each number."]
out.write_text("\n".join(doc) + "\n")
print(out, len(doc))
