# Characterising the vacuum-tube SPICE models

The tube bench, specified before it is built: a catalogue of measurements that reproduces, from a model
alone, every table and every graph the makers printed for triodes, pentodes, beam tetrodes, rectifiers,
signal diodes and the converter, at the makers' own conditions and on universal ladders around them. It
follows the transistor bench ([model-characterisation.md](model-characterisation.md)) and the op-amp bench
([opamp-characterisation.md](opamp-characterisation.md)) in its principles and its format, and it was drawn,
like the op-amp bench, from a survey of what the sheets measure: 50 sheets, 344 pages, every graph and every
table row transcribed with its conditions.

Status: this page is the specification and the evidence behind it — the survey
(`data/datasheets/survey/tube/`), the ladders it gives, the measurements, their drawings
([bench-drawings.md](bench-drawings.md), `docker/circuitikz/benches_tube.py`), and a preview of the
measurements on ngspice over every curated model of 45 surveyed parts (`docker/sim/preview/tube_preview.py`,
"What the preview says" below). Eight entries, the triode's, are in the catalogue (`data/bench/measurements.yaml`)
and the 12AX7's models are measured with them on its part page, an example of what the whole battery will publish
("The entries published so far"); the other entries and the decks in the simulator images come after, in the
order of [bench-roadmap.md](bench-roadmap.md).

## Principles

The transistor bench's five principles hold — behaviour only, intrinsic ladders, numbers not opinions,
explained once per measurement, reproducible — with four additions that tubes force:

- **Two layers: universal, and the sheet's own conditions.** Tubes span four decades of current and two of
  voltage: a 12AX7 works at 1 mA and 250 V, a 300B at 60 mA and 300 V, a 6C33C at 540 mA and 120 V, a
  6C45P at 40 mA with a transconductance of 45 mA/V. A ladder sized for one is empty for the next, and the
  conditions that matter (an operating point, a load, a drive) are the maker's, not a decade. So every
  model runs the *universal layer* — wide ladders, the same for every model of a kind, plus points the
  model itself sets (its own cut-off, its own current at zero bias) — and then the *sheet layer*: every
  table row and every graph the survey transcribed for that part and its equivalents, run at the sheet's
  own conditions on every model of the part (`tube-sheet-points`, `tube-sheet-figures`). The sheet enters
  only as a list of conditions; judging the fit stays the comparison step's job.
- **Absences are results.** No tube model met here has anode shot noise, a heater, a warm-up, a
  temperature, gas or leakage current, or secondary emission; almost none has the initial-velocity
  current that flows into a grid held below zero (the current a grid-leak bias runs on); many have no grid
  current at all, and the most common pentode equation has a screen current that does not depend on the
  anode voltage. Each measurement says which of its numbers can come out `absent` and from what in the text
  (`tube-card`), as the op-amp bench does for macromodels.
- **The dialect is a fact about the model.** Tube models are written for PSpice (`VALUE={}`, `PWR`,
  `PWRS`, `PARAMS:`), for LTspice (`B` sources, `URAMP`, `**`, a parameter passed to a subcircuit that
  never declares it) or for Micro-Cap, often in one file. Which mode of each simulator reads a model, and
  what had to be declared for it to load, is published by `tube-runs`; the text is never rewritten beyond
  declaring what a caller passes.
- **The test circuits are the sheets', idealised as the sheets' test sets were, and solved rather than
  waited for.** An output transformer is ideal: push-pull, a centre-tapped primary whose halves sit at
  v = Raa/4 · (i1 − i2); single-ended, an anode at Vb − RL · (ia − Ī), an infinite primary inductance through
  which the mean current Ī is free to shift with signal as it does through a real winding. "Rk adequately
  by-passed" (GE's words) is an ideal bypass: the cathode held at Rk times the mean cathode current under
  signal; a screen fed through a resistor and decoupled is held at the supply less Rg2 times its mean
  current. Each of those means is an unknown per copy, started at the zero-signal operating point (found
  with the real resistors) and solved by the secant method over short transients, so a sheet's
  steady-state number is reached in a few periods instead of the seconds a 100 µF bypass takes to settle.
  A rectifier's plate-supply impedance is the sheet's figure per plate and its AC volts are measured
  without load, as GE's footnote says. Where a sheet does not state a part of the circuit (a coupling
  capacitor, a source impedance), the universal value is used and named.

## Conventions

- **Pins by name.** A/P/PLATE/ANODE is the anode, G/G1 the control grid, G2/S the screen, G3 the
  suppressor (at the cathode unless a measurement drives it), K/C the cathode; A1/A2 the plates of a
  full-wave rectifier. A model whose pins carry no names (numbers with no comment), or a heater, is not run
  until its pins are traced, never guessed. A pentode modelled strapped as a triode (Ayumi's `…T`
  subcircuits) runs the triode battery and is laid over the sheet's triode-connected curves.
- **Symbols.** The European spelling throughout — Va, Vg1, Vg2, Ia, Ig1, Ig2, ra, gm, µ, Raa, Rk — with
  the American one beside it once: Eb, Ec1, Ec2, Ib, Ic1, Ic2, rp, Gm, µ, Rp (plate-to-plate load), Rk.
  GE's resistance-coupled charts call the plate resistor Rp, the next stage's grid resistor Rs and the
  stage's own grid resistor Rg1; the bench keeps those names for those charts. A sheet's own symbols are
  kept in the survey and in every chart a sheet is laid over.
- **Sampling.** Anode sweeps in 1 V steps (0.1 V below 50 V), grid sweeps in 10 mV steps; AC at 20 points
  per decade from 1 Hz to 10 MHz and spot values at 1 kHz; transients at 200 points per period, written on
  the deck's own time grid (`.options interp`), read over their last periods, the harmonics by Goertzel;
  rectifiers run 40 mains periods and are read over the last five; `reltol = 1e-4`; one deck packs every
  copy the analysis allows. No waveform file may pass 200 MB: a deck whose solver collapses its step is
  `failed`, never a full disk.
- **No temperature, no heater.** The models have neither, so nothing is run against them; the heater rows
  of the sheets are recorded and `tube-heater` reports the absence. A model that does carry heater pins
  is the exception the measurement exists for.
- **The model's own scale.** I0, the anode current at Va = 250 V and Vg1 = 0 (Vg2 = 250 V for a pentode),
  read by `tube-runs`, decides which ladder steps a chart shows first, the "auto" grid step (the model's
  cut-off at 250 V over eight, on the 1-2-2.5-5 series) and the fallback operating point of a part with no
  sheet table (Ia = I0/3).

## What the makers' sheets measure

The survey read 50 sheets, the parts the index's schematics use most (38) and a set of less-used ones
chosen to widen the kinds (12): small-signal triodes, power triodes, small-signal and remote-cut-off
pentodes, beam power tubes, transmitting beam tetrodes, a line-output pentode, rectifiers, signal diodes,
a converter, a tuning indicator and a glow regulator. They are scans with no text layer, so every page was
rendered and read by eye, and every graph (axes, span, scale, the stepped family and its values, every
fixed condition, what is drawn on it) and every table row (quantity, symbol, value, unit and every
condition that defines it, footnotes included) was transcribed with its page:
`data/datasheets/survey/tube/` — `sheets.csv`, `figures.csv`, `matrix.csv` and the table rows in
`tables-{triode,pentode,beam,other}.csv` (split by kind to keep each file small): 237 graphs and 5,074 table rows,
each with the measurement that reproduces it (`bench`). The sheets themselves are linked, never copied;
`sheets.csv` holds each one's address and sha256.

| sheet | type | maker | document | date | pages | graphs | table rows |
|---|---|---|---|---|---|---|---|
| [12AX7 (ECC83)](https://frank.pocnet.net/sheets/093/1/12AX7.pdf) | twin-triode | General Electric | ET-T509B | 6-53 | 4 | 4 | 122 |
| [12AU7-A / 12AU7 / 7AU7 (ECC82)](https://frank.pocnet.net/sheets/093/1/12AU7A.pdf) | twin-triode | General Electric | ET-T880A | 2-56 | 5 | 4 | 160 |
| [12AT7 (ECC81)](https://frank.pocnet.net/sheets/049/1/12AT7.pdf) | twin-triode | RCA | RCA 12AT7 Data | March 1, 1954 | 4 | 2 | 40 |
| [ECC88 (6DJ8)](https://frank.pocnet.net/sheets/030/e/ECC88.pdf) | twin-triode | Philips | 939 2455 | 1.1.1958 | 7 | 3 | 43 |
| [6SN7-GTB / 6SN7-GTA / 12SN7-GTA](https://frank.pocnet.net/sheets/093/6/6SN7GTB.pdf) | twin-triode | General Electric | ET-T899 | 10-54 | 5 | 4 | 162 |
| [EL84 (6BQ5)](https://frank.pocnet.net/sheets/129/e/EL84.pdf) | power-pentode | Mullard | EL84 Output pentode, pages D1–D4, C1–C18 | JANUARY 1964 | 22 | 18 | 178 |
| [EL34 (6CA7)](https://frank.pocnet.net/sheets/129/e/EL34.pdf) | power-pentode | Mullard | EL34 Output pentode, pages D1–D5, C1–C14 | JANUARY 1964 | 19 | 14 | 187 |
| [6L6-GC](https://frank.pocnet.net/sheets/049/6/6L6GC.pdf) | beam-tetrode | RCA | DATA 1-5 | 8-60 | 10 | 5 | 277 |
| [6V6-GT (5V6-GT)](https://frank.pocnet.net/sheets/093/6/6V6GT.pdf) | beam-tetrode | General Electric | ET-T914 | 3-55 | 6 | 7 | 103 |
| [6AU6 / 6AU6A (EF94)](https://frank.pocnet.net/sheets/127/6/6AU6.pdf) | pentode | Tung-Sol | Plate #6531 | August 1, 1962 | 4 | 4 | 49 |
| [5Y3-GT](https://frank.pocnet.net/sheets/093/5/5Y3GT.pdf) | rectifier | General Electric | ET-T965 | 10-55 | 5 | 6 | 24 |
| [GZ34 (5AR4)](https://frank.pocnet.net/sheets/129/g/GZ34_Mullard.pdf) | rectifier | Mullard | GZ34 558-1 to 558-6, Issue 2 |  | 6 | 4 | 43 |
| [6BA6 (EF93)](https://frank.pocnet.net/sheets/049/6/6BA6.pdf) | remote-cutoff-pentode | RCA | DATA | 3-61 | 6 | 4 | 29 |
| [EF86 (6267)](https://frank.pocnet.net/sheets/030/e/EF86.pdf) | pentode | Philips | 939 1649 | 4.4.1956 | 12 | 6 | 144 |
| [ECC99](https://www.jj-electronic.com/images/stories/product/preamplifying_tubes/pdf/ecc99.pdf) | twin-triode | JJ Electronic |  |  | 2 | 2 | 20 |
| [6AL5 (also 3AL5, 12AL5) (EB91)](https://frank.pocnet.net/sheets/093/6/6AL5.pdf) | diode | General Electric | ET-T882 | 8-54 | 3 | 2 | 36 |
| [6C4 (EC90)](https://frank.pocnet.net/sheets/093/6/6C4.pdf) | triode | General Electric | ET-T1604 | 3-60 | 4 | 4 | 135 |
| [6SL7-GT / 12SL7-GT](https://frank.pocnet.net/sheets/093/6/6SL7GT.pdf) | twin-triode | General Electric | ET-T1450 | 12-56 | 4 | 4 | 109 |
| [6BE6 (EK90)](https://frank.pocnet.net/sheets/049/6/6BE6.pdf) | heptode | RCA | DATA | May 3, 1954 | 8 | 4 | 98 |
| [300B](https://frank.pocnet.net/sheets/084/3/300B.pdf) | power-triode | Western Electric | Bell System Practices, Transmission … | January 1950 | 6 | 6 | 60 |
| [807](https://frank.pocnet.net/sheets/049/8/807.pdf) | beam-tetrode | RCA | Beam Power Tube, DATA 1–4 | NOV. 5, 1954 | 14 | 7 | 366 |
| [6J5](https://frank.pocnet.net/sheets/093/6/6J5.pdf) | triode | General Electric | ET-T299A | 6-52 | 4 | 4 | 117 |
| [2A3](https://frank.pocnet.net/sheets/049/2/2A3.pdf) | power-triode | RCA | RCA 2A3 DATA pages 1-2 | October 15, 1947 | 4 | 3 | 43 |
| [ECC85 (6AQ8)](https://frank.pocnet.net/sheets/030/e/ECC85.pdf) | twin-triode | Philips | 939 0027 | 11.11.1954 | 11 | 7 | 48 |
| [6H6](https://frank.pocnet.net/sheets/093/6/6H6.pdf) | diode | General Electric | ET-T297 | 4-46 | 2 | 2 | 34 |
| [6SJ7, 6SJ7-GT](https://frank.pocnet.net/sheets/049/6/6SJ7.pdf) | pentode | RCA | DATA | June 15, 1948 | 7 | 6 | 50 |
| [6AQ5 (5AQ5) (EL90)](https://frank.pocnet.net/sheets/093/6/6AQ5.pdf) | beam-tetrode | General Electric | ET-T885 | 6-55 | 6 | 7 | 80 |
| [12AY7](https://frank.pocnet.net/sheets/049/1/12AY7.pdf) | twin-triode | RCA | RCA 12AY7 Tentative Data | April 1, 1953 | 3 | 1 | 25 |
| [6K7](https://frank.pocnet.net/sheets/093/6/6K7.pdf) | remote-cutoff-pentode | General Electric | ET-T307 | 5-46 | 3 | 2 | 34 |
| [6X4 (EZ90)](https://frank.pocnet.net/sheets/049/6/6X4.pdf) | rectifier | RCA | DATA 1-2 | OCT. 1, 1953 | 8 | 6 | 23 |
| [6CG7 / 8CG7](https://frank.pocnet.net/sheets/093/6/6CG7.pdf) | twin-triode | General Electric | ET-T941B | 11-56 | 5 | 4 | 165 |
| [RCA-6F6](https://frank.pocnet.net/sheets/028/6/6F6.pdf) | power-pentode | RCA | RCA-6F6 "Power Amplifier Pentode", … | not printed | 4 | 2 | 78 |
| [6J7](https://frank.pocnet.net/sheets/093/6/6J7.pdf) | pentode | General Electric | ET-T302 | 7-46 | 3 | 2 | 166 |
| [5881](https://frank.pocnet.net/sheets/127/5/5881.pdf) | beam-tetrode | Tung-Sol | Plate #6482, #6483, #6484 | June 1, 1962 | 6 | 6 | 166 |
| [35W4](https://frank.pocnet.net/sheets/093/3/35W4.pdf) | rectifier | General Electric | ET-T407C | 5-60 | 3 | 2 | 64 |
| [12DW7](https://frank.pocnet.net/sheets/106/1/12DW7.pdf) | twin-triode | Sylvania | Sylvania Type 12DW7 AF Amplifier and Phase … | 6-1-61 | 2 | 2 | 52 |
| [KT88](https://frank.pocnet.net/sheets/086/k/KT88.pdf) | beam-tetrode | M-O Valve Co | KT88 Issue 5 | December 1974 | 8 | 6 | 167 |
| [6550](https://frank.pocnet.net/sheets/127/6/6550.pdf) | beam-tetrode | Tung-Sol | Plate #6755 | July 1, 1963 | 8 | 10 | 119 |
| [6C33C (6С33С, 6S33S)](https://frank.pocnet.net/sheets/113/6/6S33S.pdf) | power-triode | Soviet | handbook pages 132-134 | not printed | 3 | 3 | 37 |
| [6N1P (6Н1П)](https://frank.pocnet.net/sheets/164/6/6N1Pspec.pdf) | twin-triode | Svetlana | Svetlana Technical Data 6N1P Dual Audio … | 4/99 | 2 | 1 | 16 |
| [6C45П-Е (6S45P-E) (6S45PE)](https://frank.pocnet.net/sheets/112/6/6S45PE.pdf) | triode | Soviet | bilingual handbook pages 'ТРИОД / TRIODE … |  | 2 | 0 | 31 |
| [EM84](https://frank.pocnet.net/sheets/030/e/EM84.pdf) | indicator | Philips | 938 3201 / 938 3202 | 4.4.1959 | 6 | 1 | 34 |
| [0A2 (printed 'OA 2') (150C2)](https://frank.pocnet.net/sheets/030/0/0A2.pdf) | voltage-regulator | Philips | sheet 1: 939 4364 | 4.4.1954 | 10 | 0 | 27 |
| [6146](https://frank.pocnet.net/sheets/049/6/6146.pdf) | beam-tetrode | RCA | VHF Beam Power Amplifier, Tentative Data 1–4 | MAY 1, 1952 | 29 | 14 | 754 |
| [EF184 (6EJ7)](https://frank.pocnet.net/sheets/030/e/EF184.pdf) | pentode | Philips | sheet 1: 938 3557 | 3.3.1959 | 15 | 7 | 108 |
| [6CW4](https://frank.pocnet.net/sheets/049/6/6CW4.pdf) | triode | RCA | DATA 1-3 | 1-63 | 6 | 4 | 28 |
| [3S4](https://frank.pocnet.net/sheets/106/3/3S4.pdf) | power-pentode | Sylvania |  |  | 2 | 2 | 39 |
| [PL509 (40KG6)](https://frank.pocnet.net/sheets/010/p/PL509.pdf) | power-pentode | Philips | Data handbook Electronic components and … | November 1969 | 10 | 8 | 44 |
| [EL156](https://frank.pocnet.net/sheets/128/e/EL156.pdf) | power-pentode | Telefunken | Telefunken EL 156 Endpentode data sheet, … | sheet codes 010165 | 14 | 11 | 107 |
| [6B4G](https://frank.pocnet.net/sheets/127/6/6B4G.pdf) | power-triode | Tung-Sol | Plate 174-1, 175-1 | Nov. 7, 1938 | 2 | 0 | 33 |

### What the sheets print, and what reproduces it

Every graph and table row of the survey by what it shows (the survey's `test`), and the measurement that
reproduces it (its `bench`); `matrix.csv` gives the same per sheet.

| what the sheet prints | sheets | graphs | table rows | measured by |
|---|---|---|---|---|
| mechanical | 50 | 0 | 170 | not measured |
| heater | 49 | 0 | 392 | `tube-heater` |
| ratings | 44 | 6 | 533 | `tube-sheet-points` |
| typical-operation | 42 | 0 | 439 | `pentode-params`, `triode-params`, `tube-sheet-points`, `diode-signal` |
| capacitances | 40 | 0 | 299 | `tube-capacitance`, `tube-sheet-points` |
| anode-characteristics | 38 | 59 | 0 | `pentode-anode`, `triode-anode` |
| transfer | 25 | 27 | 0 | `pentode-transfer`, `triode-transfer` |
| cutoff | 19 | 0 | 31 | `triode-transfer`, `pentode-transfer`, `tube-sheet-points` |
| power-output | 16 | 24 | 1260 | `pentode-power-pp`, `pentode-power-se`, `triode-power-pp`, `triode-power-se` |
| small-signal-params | 15 | 19 | 0 | `triode-params`, `pentode-params` |
| triode-connected | 15 | 24 | 156 | `pentode-power-pp`, `pentode-triode`, `pentode-power-se` |
| rc-amplifier | 11 | 2 | 884 | `triode-rc-amplifier`, `pentode-rc-amplifier` |
| other | 10 | 0 | 23 | not measured |
| anode-characteristics-positive-grid | 9 | 9 | 0 | `triode-positive-grid`, `pentode-positive-grid` |
| screen-current | 9 | 15 | 0 | `pentode-screen` |
| deflection | 6 | 3 | 84 | `pentode-anode` |
| grid-current | 6 | 4 | 7 | `pentode-grid-current`, `triode-grid-current`, `indicator-shadow` |
| noise | 6 | 0 | 13 | `pentode-noise`, `triode-noise` |
| rectifier-ratings | 6 | 7 | 65 | `rectifier-surge`, `diode-signal` |
| rectifier-drop | 5 | 4 | 3 | `rectifier-drop`, `diode-signal` |
| ultralinear | 5 | 9 | 153 | `pentode-power-pp`, `pentode-power-se`, `pentode-ultralinear` |
| rectifier-regulation | 4 | 7 | 22 | `rectifier-regulation` |
| rf-operation | 4 | 0 | 459 | not measured |
| converter | 2 | 8 | 42 | `heptode-conversion`, `tube-sheet-points` |
| diode-characteristic | 2 | 4 | 0 | `diode-signal` |
| life-test | 2 | 0 | 4 | not measured |
| remote-cutoff | 2 | 2 | 5 | `pentode-remote-cutoff` |
| distortion | 1 | 1 | 0 | `pentode-power-se` |
| drive-characteristics | 1 | 2 | 0 | `pentode-power-pp` |
| indicator | 1 | 1 | 16 | `indicator-shadow` |
| voltage-regulator | 1 | 0 | 14 | not measured |

### Two layers, and what varies between makers

Every sheet has the **characteristics** — a few typical values at one or two operating points, the
maximum ratings, the heater, the capacitances — and most add **operating tables**, columns of a circuit
the maker tested (an amplifier class, a supply voltage, a load, a bias) with what it gave, and
**average characteristic curves**. The families of curves are few and recur in every maker's set; what
varies is the conditions and the notation:

- **General Electric, RCA and Sylvania (1950s, 15, 12 and 2 sheets).** Eb, Ec, Ib; design-centre then design-maximum
  ratings; the resistance-coupled amplifier chart (GE, 8 sheets: Ebb 90/180/300 V × Rp 0.1/0.24/0.51 MΩ ×
  Rs 0.1/0.24/0.51/1 MΩ, Rk given per cell, gain read at 2.0 V rms out, Eo the largest rms output at 5 %
  THD, Rk "adequately by-passed"); cut-off as the grid voltage for Ib = 10 µA; µ, gm and rp against
  plate current or grid voltage; the heater warm-up test circuit (4 × rated voltage through 3 × the heater
  resistance, timed to 80 %); rectifier rating charts I–III (the operating area, the rectification
  efficiency Ē/(√2·Es), the minimum plate-supply resistance) and operation curves at 50 V steps of AC per
  plate.
- **Mullard and Philips (1954–1964, 10 sheets).** Va, Vg1, Ia, ra; "operating conditions" for one valve
  in class A and for two in push-pull — fixed bias, cathode bias, ultralinear at 20 % and 43 % taps,
  triode-connected, with the continuous-sine-wave columns apart; curve sheets of Pout and distortion
  against Raa and against drive, Ia and Ig2 against drive; the input for 50 mW (sensitivity); the grid's
  limit as −Vg1 at Ig1 = +0.3 µA; the equivalent noise resistance (300 Ω for the ECC88, 0.5 kΩ for the
  ECC85) and the EF86's 2 µV of noise over 25 Hz–10 kHz; anode curves dashed beyond the dissipation
  hyperbola. Mullard notes that a sustained sine wave readjusts a cathode bias and costs about 10 % of the
  fixed-bias output: the steady-state condition the bench solves for.
- **Tung-Sol, Genalex, Western Electric (6 sheets).** Push-pull and ultralinear tables against
  plate-to-plate load, ultralinear curves drawn about a quiescent point (Ec2 = 400 + 0.43 ΔEp, 450 + 0.40 ΔEp,
  255 + 0.4 Va) with a second screen-voltage scale; the 300B's grid voltages referred to the mid-point of an
  AC-heated filament (2.5 V less from the negative leg on DC); the KT88's intermodulation at 50 Hz and
  6 kHz, 4:1.
- **Soviet handbooks and Svetlana, JJ (4 sheets).** Ua, Ug, Uh; nominal values with ± spreads; one
  operating point, sometimes without its bias (6C45P: 150 V, 40 mA, the cathode resistor not stated);
  the 6C33C characterised at Ua = 120 V with a 35 Ω cathode resistor, one cathode or two.
- **Transmitting and line-output tubes (807, 6146, EL156, PL509).** Constant-current charts, class AB1/AB2
  audio beside class B and C RF columns (CCS and ICAS), positive-grid curves to +30 V; the EL156 in German
  with Telefunken's symbols; the PL509's characteristics measured with pulses.
- **Tests one maker prints and the others do not.** Grid-leak (zero-bias) rows with Rg1 = 10 MΩ and no
  cathode resistor in GE's resistance-coupled charts (12 of the 12AX7's 30 cells, 16 of the 6J7's), which only
  a model with the initial-velocity grid current can bias; the 6BE6's
  conversion transconductance against oscillator grid current; the EM84's shadow length against grid
  voltage; the 0A2's burning voltage against current; the 6AL5's detector curves (DC output against input
  against load resistance); microphony and hum figures (EF86, PL509), which no model can carry.

## Universal conditions

The ladders the universal layer draws from, each the union of the values the sheets fix, so that a sheet's
own number is on the ladder and models can be laid over one another. Counts are the sheets that name the
value in a condition.

| ladder | values | what the sheets say |
|---|---|---|
| anode voltage | 0–1000 V swept (1 V steps, 0.1 V below 50 V); spot values 12, 25, 50, 90, 100, 150, 180, 200, 250, 300, 350, 400, 450, 500, 600, 750 V | 250 V named by 24 sheets, 200 and 300 V by 17, 100 and 150 V by 15, 180 V by 12, 50 V by 11, 90 V by 9, 400 V by 8, 350 V by 7, 450 and 500 V by 6, 600 V by 4, 750 V by 2; 12–50 V is where pedals run a 12AX7 |
| screen voltage | 50, 100, 150, 175, 200, 225, 250, 300, 350, 400, 450 V | 250 V (12 sheets), 100 V (11), 200 and 300 V (9), 150 V (8), 50 V (5), 180 and 225 V (4) |
| control-grid voltage | 0 to −10 V in 0.25 V, to −30 V in 0.5 V, to −60 V in 1 V, to −150 V in 2.5 V, to −300 V in 5 V; positive +0.5, 1, 2, 5, 10, 15, 20, 30, 40, 50 V | the families' steps: 0.5 V (12AX7), 1 V (EL84), 2 V (KT88 at low screen), 2.5 V (6L6GC), 4 V, 5 V (EL34, 6550), 10 V (2A3, 6C33C), 20 V (300B); positive to +15 V (5881), +30 V (6F6, 807), +40 V (6F6 triode) |
| anode current | 10 µA to 1 A, 1-2-5 | cut-off at 10 µA (GE, RCA, Sylvania; 11 sheets), 0.5 mA (GE pentodes), 1 mA (6550); operating points 0.5 mA (12AX7) to 540 mA (6C33C) |
| load, single-ended and push-pull | 1.5–12 kΩ: 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6, 6.6, 7, 8, 9, 10, 12 kΩ; and ×0.25 to ×4 around each sheet column | 5 kΩ (8 sheets), 3 kΩ (6), 4 and 6 kΩ (5), 2.5 and 10 kΩ (4), 5.5 and 8 kΩ (3) |
| resistance-coupled stage | Ebb 90, 180, 300 V and 100, 200, 250, 350, 400 V; Rp 47, 100, 220/240, 470/510 kΩ; Rs 0.1, 0.24, 0.47/0.51, 1, 2.2 MΩ; Rg1 0.1 and 1 MΩ; Rk per cell and the model's optimum on E12 | GE's chart in 8 sheets (the same three supplies, plate and grid resistors), the 6J7's 120 cells, the EF86's tables at Vb 200/250/400 V |
| drive | 0 to 1.25 × the sheet's, in 5 % steps; 2 V rms out (gain); the 5 % THD point; the grid-current onset | peak grid voltage equal to the bias (RCA class A1), grid-to-grid rms (Mullard), Esig rms (GE); 50 mW sensitivity (Mullard) |
| ultralinear tap | 0.2, 0.4, 0.43, 0.5 of the half-primary | 20 % and 43 % (Mullard), 40 % (Genalex, Tung-Sol 6550), 43 % (Tung-Sol 5881) |
| rectifier | AC per plate 150–550 V in 50 V steps (and 117 V half-wave); Rs per plate 0, 25, 50, 75, 100, 135, 150, 200 Ω; C 4, 8, 10, 16, 20, 32, 40, 60 µF; L 5, 10, 20, 40 H and infinite; Idc 0–300 mA; 50 and 60 Hz | the 5Y3's curves at 150–500 V with C = 20 µF and Rs = 50 or 135 Ω; the GZ34's at 60 µF and L = 10 and 40 H with 0, 2×50 and 2×100 Ω; the 6X4's choke-input chart at 60 Hz |
| frequency | DC; 1 kHz (AC parameters, distortion); 1 Hz–10 MHz (response); 1 MHz (capacitances); 50, 60 Hz (mains); 455 kHz (detector) | no sheet states the frequency of its gm or distortion figures; the KT88's IMD at 50 Hz + 6 kHz |

## The measurements

Each entry follows the catalogue's shape: what it is and why, the circuit (and its drawing,
`data/bench/drawings/<id>.svg` from `docker/circuitikz/drawings/<id>.tex`), the conditions, how the numbers
are read, the outputs, what drives them in the model's equations, what a high and a low value mean, what the
measurement cannot tell, how many surveyed sheets print it, and the test method it resembles. Twenty-nine of
the 41 have a drawing of their own; `pentode-positive-grid`, `-remote-cutoff`, `-grid-current` and
`-distortion` are drawn by `pentode-anode`, `pentode-transfer`, `triode-grid-current` and
`pentode-rc-amplifier`, whose decks they share, and the views and text readings (`tube-card`, `tube-heater`,
`tube-sheet-points`, `tube-sheet-figures`, `tube-agreement`, `triode-constant-current`, `pentode-screen`,
`indicator-shadow`) have no circuit of their own. The test
methods cited are the parts of IEC 60151, *Measurements of the electrical properties of electronic tubes and
valves*: part 1 (electrode currents), 2 (heater current), 10 (audio-frequency output power and distortion),
12 (electrode resistance, transconductance, amplification factor and conversion parameters), 13 (emission)
and 15 (spurious electrode currents); and MIL-STD-1311, the test methods for electron tubes.

The model terms named under each entry are those of the families the index holds most: Koren's equations
(`MU`, `EX`, `KG1`, `KG2`, `KP`, `KVB`, `RGI`, the capacitances `CCG`, `CGP`, `CCP`), the Derk/Reefman
extension (`TriodeK`, `BTetrodeD`: the screen's `KG2`, `SC`, `AP`, `W`, `NU`, `LAM` shaping the knee and
the screen current at low anode voltage), Ayumi's (a 3/2-power cathode current split between anode, screen
and grid by fitted ratios) and the plain Child-Langmuir law (a perveance and an exponent of 1.5).

### Every tube

#### What the model text carries (`tube-card`)

Group `load` · analysis `text` · no engine.

Read from the text before anything runs, as `opamp-card` is for macromodels: the family (Koren, Derk/Reefman,
Ayumi, Child-Langmuir 3/2, a parameterised macro of another author), the pins and the roles traced to them,
and which physics the equations carry, so that every `absent` the bench publishes names its cause: a
grid-current term (a diode, or a source in Vg1 above zero), a grid current below zero (the initial-velocity
current), interelectrode capacitances, a screen current that depends on the anode voltage, a knee term, a
heater, a temperature, a noise source (any element that is not a behavioural source), a dialect
(`VALUE={}`, `PWR`/`PWRS`, `URAMP`, `**`, `^`, `IF()`, `LIMIT`), parameters a caller passes and the
subcircuit does not declare, a domain limit (a `LOG()` or a fractional power of an argument that goes
negative past cut-off).

**Outputs.** `family`; `pins`; `grid_current` (none, above zero, also below zero); `capacitances` (none,
constant, junction-dependent through a diode's `CJO`); `screen_on_anode` (true, false); `knee`; `heater`;
`noise_sources`; `dialect`; `undeclared_params`; `domain_limit`.

**What it cannot tell.** That a term is right: the measurements below say how it behaves.

**Standard.** none

#### Does the model load, in which dialect, and at what operating points (`tube-runs`)

Group `load` · analysis `op` · engines qspice, ngspice, ltspice · symbols I0, Ia, Ig2, Ig1.

The first fact about a model, and the one tube models fail most: whether each simulator reads it, and in which
of its modes. ngspice is tried as it comes, then with its PSpice (`psa`), LTspice (`lta`) and combined
(`ltpsa`) compatibilities, then with the parameters a caller passes declared on the `.SUBCKT` line (an
LTspice habit ngspice refuses); QSPICE and LTspice run as they come. The operating points read are the
quickest sanity check of a tube model and the model's own scale I0.

**Circuit.** Three kinds of copy: a triode at Va = 100 and 250 V with Vg1 = 0, −2 and −10 V; a pentode at
Va = 100 and 250 V, Vg2 = 250 V, Vg1 = 0 and −10 V; a diode at 10 and 50 V; one operating point.

**Conditions.** {triode: {va: [100, 250], vg1: [0, -2, -10]}, pentode: {va: [100, 250], vg2: 250, vg1: [0, -10]}, diode: {va: [10, 50]}, modes: [none, psa, lta, ltpsa], declare_params: [false, true]}

**Extraction.** The first mode that settles to finite currents; the error class of the last failure when none
does: `syntax` (a construct the engine does not know), `params` (an undeclared or missing parameter),
`subckt` (a dependency not in the file), `domain` (`out of range for log`, a negative base under a
fractional power), `convergence`, `timeout`.

**Outputs.**

- `runs`: true when the engine returned an operating point
- `mode`: the first ngspice mode that read it; `params_declared`: whether the parameters had to be declared
- `error_class`: as above, empty when it ran
- `i0` (A): Ia at 250 V and 0 V (and Vg2 = 250 V), the model's own scale
- `ia@{va},{vg}`, `ig2@…`, `ig1@…` (A): the currents at the points above

**What it cannot tell.** That the model is right; a model that loads in one engine only is a dialect fact,
not a verdict.

**In the sheets.** Every sheet's first page gives one or two of these points.

**Standard.** none

#### Interelectrode capacitances, and the Miller input (`tube-capacitance`)

Group `capacitance` · analysis `ac` · engines qspice, ngspice, ltspice · symbols Cg1k, Cg1a, Cak, Cg1g2, Cg2k, Cag2, Cin, Cout.

The direct capacitances every sheet tabulates, measured as the sheets define them: one electrode driven, every
other held at AC ground, the current into each undriven one read. The sheets give them cold and with or without
a shield; a model gives one set of constants, often with the grid-current diode's junction capacitance (Koren's
`CJO = 10 pF`) added to Cg1k without its author having meant it, which this measurement shows. The Miller input
of a stage, Cg1k + (1 + A)·Cg1a at the gain A of each resistance-coupled cell, is what sets the upper corner of
a high-µ stage fed from a pot: it is published beside the RC chart's cells.

**Circuit.** Copy A drives the control grid, B the anode, C the screen, each with 1 V of AC at 1 MHz on its
bias; the other electrodes sit on their DC sources, read through their ammeters.

**Conditions.** {va: 250, vg2: 250, vg1: [cut-off, Ia = I0/4], f: 1e6, v_ac: 1}

**Extraction.** C = Im(i)/(2πf) for each pair; the sheets' input and output capacitances as sums
(Cin = Cg1k + Cg1g2, Cout = Cak + Cag2); hot over cold.

**Outputs.** `c_g1k`, `c_g1a`, `c_ak`, `c_g1g2`, `c_g2k`, `c_ag2` (F), cold and hot; `c_in`, `c_out` (F);
`c_miller@{cell}` (F).

**Model terms that drive it.** `CCG`, `CGP`, `CCP` (Koren), `CCG1`, `CCG2`, `CG1G2`, `CPG1` (Derk), the
grid diode's `CJO`.

**A high value.** A Cg1k several pF above the sheet's is the grid diode's junction in parallel.

**A low value.** Zero: no capacitances in the model, `absent`, and no upper corner anywhere.

**What it cannot tell.** The shield's effect, the socket and wiring, and the hot cathode's space-charge
increase of Cg1k, which no model carries.

**In the sheets.** 39 sheets, 267 rows (with and without shield; RCA's "with shell connected to cathode").

**Standard.** resembles IEC 60151 interelectrode capacitance measurement and the RETMA/EIA shield conditions the
GE sheets name

#### Heater and filament (`tube-heater`)

Group `heater` · analysis `text` · no engine.

Every sheet gives the heater's voltage and current, most the heater-cathode voltage limits, GE the warm-up time
and its test circuit (four times the rated voltage through three times the heater's resistance, timed to 80 %),
the directly heated tubes their filament (2.5 V, 5 V) and the grid voltages referred to its mid-point. No model
in the index has a heater, so this measurement reports the absence and, for a model that has heater pins, runs
the warm-up circuit and the emission against heater voltage.

**Outputs.** `heater_modelled` (false for every model met); for one that is: `warm_up` (s), `ia@{ef}` (A).

**What it cannot tell.** The hum a heater induces, the cathode's emission life.

**In the sheets.** 49 sheets, 392 rows.

**Standard.** resembles IEC 60151-2 (heater current) and the warm-up test of the GE sheets

#### Every table row of the sheets, at its conditions (`tube-sheet-points`)

Group `sheet` · analysis `op`, `ac`, `tran` · engines qspice, ngspice, ltspice.

The sheet layer for numbers. Every row of `data/datasheets/survey/tube/tables-*.csv` for the part and its
equivalents is grouped into the cases a sheet column defines (page, section, conditions) and run on every
model of the part through the measurement its `bench` column names: a characteristics column through
`*-params` (Ia, Ig2, gm, ra, µ — a pentode's printed µ is µg1g2), a resistance-coupled cell through
`*-rc-amplifier`, an operating column through `*-power-se` or `*-power-pp`, a rectifier column through
`rectifier-regulation`, a capacitance row through `tube-capacitance`. Each number is published beside the
sheet's, with the page. A characteristics point is run twice: at the sheet's grid voltage, and at the
sheet's anode current (the grid voltage found for it), because a model whose bias is off but whose slopes are
right agrees at the current and not at the voltage — and the difference is the model's contact-potential
error, not its shape.

**Conditions.** the survey's rows, their conditions parsed into Va (Eb, Ua), Vb (Ebb), Vg2 (Ec2, Ug2), Vg1 (Ec,
Ug), Rk, RL (Ra, Ra-a, plate-to-plate), Rs (next grid), Rg1, Rg2 (Rsg), the drive (peak per grid, grid-to-grid,
rms), the connection (pentode, ultralinear at the printed tap, triode) and the bias (fixed or cathode, common
or per valve); a push-pull column's currents are per valve when printed "2 ×", else halved from the pair.

**Outputs.** `sheet`, `model@vg`, `model@ia`, `vg1@ia`, and the ratio model/sheet, per row.

**What it cannot tell.** Whether a difference is the model's or the sheet's (a sheet is one bogey tube of a
production spread); the comparison step weighs that.

**In the sheets.** 3,330 rows in 49 sheets are conditions or results a deck can reproduce (the rest are
ratings, heater and mechanical data, and RF and deflection columns).

**Standard.** none

#### Every graph of the sheets, redrawn (`tube-sheet-figures`)

Group `sheet` · analysis `dc`, `tran` · engines qspice, ngspice, ltspice.

The sheet layer for curves. Every graph of `figures.csv` for the part is redrawn from the model on the
sheet's own axes: the x span and scale, the stepped family and its exact values, every fixed electrode,
the connection (pentode, triode-connected, ultralinear about the printed quiescent point and tap), so that
the crop of the sheet (CLAUDE.md rule 1) and the model's curves can be laid over each other. Static graphs
(anode, positive-grid, transfer, screen-current, triode-connected, ultralinear, cut-off, the rectifier's
plate characteristic) are replayed from the row alone; operating graphs (power against load or drive,
distortion, regulation) through the measurement their `bench` column names, at the graph's fixed conditions.

**Conditions.** the survey's graph rows: x, x_from, x_to, x_scale, family, family_values, fixed,
connection.

**Outputs.** per graph, the model's curves on the sheet's grid; `replayed` (ok, or the reason the row alone
cannot drive it: an axis, a family or a screen voltage not printed).

**What it cannot tell.** The sheet's curve as numbers: the sheets are scans; digitising the curves is the
comparison step's work, and the crops are what a reader compares by eye.

**In the sheets.** 237 graphs in 47 sheets; 153 of them static.

**Standard.** none

#### Do the three simulators agree? (`tube-agreement`)

Group `load` · analysis `derived` · engines qspice, ngspice, ltspice.

The same as for every kind: per output, the largest relative difference between engines, and the decks
whose waveforms differ by more than the tolerance. Tube models make it sharper than transistors do: the
three engines read `PWRS`, `URAMP`, `**` and `^` differently, and LTspice's `^` is a logical XOR in a B
source (the reason Ayumi's models are carried with `**` in the curated tree).

**Outputs.** `max_rel_diff@{output}`; `disagreeing_decks`.

**Standard.** none

### Triodes

#### Anode characteristics (`triode-anode`)

Group `static` · analysis `dc` · engines qspice, ngspice, ltspice · symbols Ia(Va), Ig.

The chart every triode sheet opens with: anode current against anode voltage, one trace per grid voltage.
Three things are read at a glance: the spacing of the traces (µ: a trace's shift along the voltage axis per
volt of grid), their slope (ra), and their curvature (the 3/2 law that makes a triode's second harmonic). A
model fitted at one operating point draws a good family near it and a wrong one at the corners: near zero
anode voltage, where pedals run a 12AX7, and near cut-off, where the traces of a real tube bunch and a
model's stay evenly spaced.

**Circuit.** One copy per grid voltage of the ladder, each grid held by its source, every anode on one swept
supply through its ammeter; the positive-grid copies read their grid current too.

**Conditions.** {va_sweep: {from: 0, to: 1000, step: 1, fine_below: 50, fine_step: 0.1, unit: V}, vg1: "0 to −300 V: 0.25 V steps to −10, 0.5 V to −30, 1 V to −60, 2.5 V to −150, 5 V to −300", vg1_positive: [0.5, 1, 2, 5, 10, 15, 20, 30, 40, 50], families: [0.25, 0.5, 1, 2, 2.5, 4, 5, 10, 20, auto]}

**Extraction.** Each trace on the grid; a family is a subset (0 down in its step to the model's cut-off);
the auto step is the cut-off at 250 V over eight on the 1-2-2.5-5 series. Ia at the spot anode voltages
for each family member; the dissipation hyperbola of the part's rating, when the survey has it, is drawn
over the family.

**Outputs.** `ia@{va},{vg}` (A) at the spot values; `ia@0V,0V` (A), the current with no anode voltage, zero
in any physical model; `ia@5V,0V`, `ia@12V,0V`, `ia@25V,0V` (A), the low-voltage region; `auto_step` (V).

Curves: Ia against Va per grid step, one family per step size; Ig against Va for the positive traces.

Beside the point under the cursor: P (W), Va·Ia; ra (Ω), the local slope; µ, from the neighbouring trace.

**Model terms that drive it.** `MU`, `EX`, `KG1`, `KP`, `KVB` (Koren); the perveance and exponent (3/2 law).

**A high value.** Traces that keep climbing steeply at high anode voltage are a low ra.

**A low value.** Traces evenly spaced into cut-off are a model with constant µ: no real triode has it.

**Out of range.** A current at Va = 0: Duncan's 12AX7A passes 0.35 mA there (its 3/2 law carries an offset of
45 V on the anode voltage), and at 5 V, Vg1 = 0 the 12AX7 models of the index give from 0.03 mA (Koren) to
0.59 mA (Ayumi): a factor of twenty in the region a pedal runs the tube in, which the sheets draw from the
origin on their anode charts and give no table point for.

**What it cannot tell.** The thermal droop of a real anode at full dissipation.

**In the sheets.** 18 sheets, 22 graphs (and 15 sheets' triode-connected pentode graphs, `pentode-triode`).

**Standard.** resembles IEC 60151-1 (electrode currents); the sheets' average plate characteristics

#### Positive-grid characteristics (`triode-positive-grid`)

Group `static` · analysis `dc` · engines qspice, ngspice, ltspice · symbols Ia(Va), Ig(Va) at Vg1 > 0.

Class A2 and AB2 drive the grid positive, and the 300B, 2A3, 6C33C, 6C4, 12AU7 and 6SN7 sheets draw the
region: the anode traces above zero bias and, dashed, the grid's own current, largest where the anode
voltage is low (the grid steals the cathode current the anode cannot take). A model whose grid diode is a
plain exponential to the cathode gets the grid current right at high anode voltage and far too small at
low, where it matters for the clipping of a driven output stage.

**Circuit.** The anode deck's positive copies.

**Conditions.** {vg1: [0, 0.5, 1, 2, 5, 10, 15, 20, 30, 40, 50], va_sweep: {from: 0, to: 600, step: 1}}

**Outputs.** `ia@{va},+{vg}`, `ig@{va},+{vg}` (A); `grid_share@{va},+{vg}`: Ig/(Ia + Ig).

**Model terms that drive it.** `RGI` and the grid diode (Koren); Ayumi's grid split term.

**A low value.** No grid current at all: `absent`, and the A2 region is a fiction.

**In the sheets.** 5 triode sheets and 4 pentode ones, 9 graphs.

**Standard.** resembles IEC 60151-1

#### Transfer characteristics, cut-off and the 3/2 law (`triode-transfer`)

Group `static` · analysis `dc` · engines qspice, ngspice, ltspice · symbols Ia(Vg1), Vg1(cut-off).

Anode current against grid voltage at fixed anode voltages: the curve the bias is set on. Its foot is the
cut-off the sheets quote as the grid voltage for 10 µA (GE, RCA, Sylvania), its upper part the 3/2 law, and
how far a model keeps to 1.5 as the exponent is the first-order source of its distortion.

**Circuit.** One copy per anode voltage, the grids on one swept source through their ammeters.

**Conditions.** {vg1_sweep: {from: -300, to: 5, step: 0.01, unit: V}, va: [12, 25, 50, 90, 100, 150, 180, 200, 250, 300, 350, 400, 450, 500], cutoff_ia: [1e-6, 1e-5, 1e-4]}

**Extraction.** Cut-off by log interpolation at each current; the local exponent d ln Ia / d ln(Vg1 + Va/µ)
between 10 % and 90 % of Ia at Vg1 = 0; the curvature at the operating point of each RC cell.

**Outputs.** `vg_cutoff@{va}` (V) at 10 µA (and 1 µA, 100 µA); `exponent@{va}`; `ia@{va},0V` (A).

Curves: Ia against Vg1 per anode voltage, lin and log.

**Model terms that drive it.** `EX`, `KP`, `MU` (Koren); the exponent of the Child-Langmuir law.

**A high value.** An exponent near 1.5 everywhere is the textbook law, held by the plain 3/2 models.

**A low value.** A foot that falls off a cliff (no current below a sharp cut-off) is a `URAMP` or a
`LIMIT` that a real cathode has no equivalent of.

**In the sheets.** 18 sheets, 13 graphs; cut-off rows in 19 sheets.

**Standard.** resembles IEC 60151-1; the cut-off condition of the GE and RCA sheets

#### Amplification factor, transconductance and anode resistance (`triode-params`)

Group `static` · analysis `ac` · engines qspice, ngspice, ltspice · symbols µ, gm, ra.

The three numbers every triode sheet prints at its operating points, and the curves of them against anode
current or grid voltage (15 sheets). They are measured as small-signal quantities at 1 kHz, one pair of
copies per point: AC on the grid with the anode held (gm), AC on the anode with the grid held (ra), and µ as
their product. GE draws µ, rp and gm against plate current for seven of its triodes (12AX7, 12AU7, 6SN7, 6C4,
6SL7, 6J5, 6CG7), the curves on which a model's constant µ shows; the bench publishes µ at the lowest current over
µ at its highest.

**Circuit.** Copies A and B per (Va, Ia), the grid voltage for each from the transfer sweep.

**Conditions.** {va: [12, 25, 50, 90, 100, 150, 180, 200, 250, 300, 350, 400, 450, 500], ia: "10 µA to 1 A, 1-2-5", f: 1000, sheet_points: [at the sheet's Vg1, at the sheet's Ia]}

**Outputs.** `gm@{ia},{va}` (S), `ra@{ia},{va}` (Ω), `mu@{ia},{va}`; `mu_low/mu_high@250V`; and every sheet point,
at the sheet's grid voltage and at its current.

Curves: µ, gm and ra against Ia at each Va (the GE and RCA "average characteristics"); against Vg1 at each Va
(the 300B and 2A3 sheets).

**Model terms that drive it.** `MU`, `KG1`, `EX`, `KP`, `KVB`.

**A high value.** gm above the sheet's at the sheet's current with ra below it: a model fitted for gain at
the cost of the curve's shape.

**A low value.** µ flat to within a percent from 10 µA to 10 mA: the constant-µ equation.

**In the sheets.** 19 sheets, 16 graphs and 115 rows.

**Standard.** resembles IEC 60151-12 (electrode resistance, transconductance, amplification factor)

#### Grid current: onset, contact potential and input resistance (`triode-grid-current`)

Group `static` · analysis `dc` · engines qspice, ngspice, ltspice · symbols Ig(Vg1), Vg1(Ig = 0.3 µA).

Where the grid starts to conduct is where a stage clips asymmetrically and where a coupling capacitor
starts charging: the guitar amplifier's blocking and the grid-leak bias both live here. Mullard and Philips
print it as −Vg1 at Ig1 = +0.3 µA; GE and RCA build their zero-bias chart cells on the small negative
current a grid draws below zero (the initial-velocity current) into a 10 MΩ leak. Most models have a diode
to the cathode with an offset; almost none have the current below zero.

**Circuit.** The transfer deck with the grid swept through zero at three anode voltages, the grid current
read through its ammeter.

**Conditions.** {vg1_sweep: {from: -5, to: 5, step: 0.01}, vg1_sweep_power: {from: -5, to: 50, step: 0.02}, va: [100, 250, 400], onset: [3e-7, 1e-6]}

**Outputs.** `vg@ig=0.3uA`, `vg@ig=1uA` (V); `ig@0V`, `ig@+1V`, `ig@+5V` (A); `rin@+1V` (Ω); `ig_below_zero`
(the current at −0.5 V, or `absent`).

**Model terms that drive it.** `RGI`, the grid diode `DX` (Koren); Ayumi's `IG` term and its offset.

**A high value.** An onset well below zero bias is a grid that loads the previous stage at rest.

**A low value.** No current up to +5 V: no grid-current term, `absent`.

**What it cannot tell.** Gas current and leakage, which add a positive grid current a real tube has and
no model does.

**In the sheets.** 6 sheets (EL34, EF184, EM84, 6146, 807, 6C45P), 4 graphs and 7 rows.

**Standard.** resembles IEC 60151-15 (spurious electrode currents)

#### Constant-current characteristics (`triode-constant-current`)

Group `static` · analysis `derived` · engines qspice, ngspice, ltspice · symbols Va(Vg1) at constant Ia.

The transmitting tubes' chart: the anode-grid plane with contours of equal anode (and grid) current, on
which a class B or C load line is a straight line. It is a view of the anode deck's surface, not a deck of its
own.

**Conditions.** {from: [triode-anode, triode-positive-grid], ia_contours: "the sheet's, else 1-2-5 from I0/100 to 2·I0"}

**Outputs.** contours; nothing else.

**In the sheets.** the 807 and 6146 (as `pentode-transfer`).

**Standard.** none

#### The resistance-coupled amplifier chart (`triode-rc-amplifier`)

Group `amplifier` · analysis `op`, `ac`, `tran` · engines qspice, ngspice, ltspice · symbols gain, Eo, Ia, Vk.

GE's and RCA's chart, cell by cell: for a supply Ebb, a plate resistor Rp and the next stage's grid resistor
Rs, the cathode resistor that biases the stage, the voltage gain and Eo, the largest output before the
distortion reaches 5 %. It is the most complete statement a sheet makes about a small triode in use, and the
eight sheets that print it give 649 numbers. The bench runs each cell as GE defines it — gain at 2.0 V rms
out, Eo at 5 % THD, Rk "adequately by-passed" (an ideal bypass, solved), the stage's own grid resistor Rg1 —
and adds what the chart implies: the quiescent point, the drive at which grid current starts, the harmonics
at every level, and the model's own optimum Rk.

**Circuit.** Ebb through Rp and an ammeter to the anode; the cathode on its ideal bypass; the output through
a 10 µF coupling capacitor into Rs; the drive on the grid with Rg1 to ground; fifteen copies per cell, one
per drive level in half-octave steps from the one that gives 2 V rms.

**Conditions.** {cells: "every cell of the part's chart", universal: {ebb: [90, 180, 300, 100, 200, 250, 350, 400], rp: [47e3, 100e3, 240e3, 510e3], rs: [100e3, 240e3, 510e3, 1e6, 2.2e6], rg1: [1e5, 1e6], rk: "E12 from 100 Ω to 22 kΩ"}, f: 1000, periods: 30, read_last: 10}

**Extraction.** The quiescent point from an operating point with the real Rk; the bypass voltage per copy
iterated to Rk times the mean cathode current; gain = v_out/v_in at the 2 V copy and at small signal; Eo by
log-log interpolation of THD against output to 5 %; the first drive at which the grid's peak current passes
1 µA; for the universal cells, the Rk that maximises Eo.

**Outputs.** `gain@2Vrms`, `gain_ac`, `eo@5%` (V rms), `ia0` (A), `vk` (V), `drive_at_grid_current` (V peak),
`h2..h5@{vout}` (%), `rk_opt` (Ω), per cell; and beside them the sheet's gain and Eo.

Curves: gain and Eo against Rp per supply; THD against output per cell.

**Model terms that drive it.** `MU`, `KG1`, `EX`, `KP` (the gain and the curvature); `RGI` and the grid
diode (Eo, where the grid conducts before the anode bottoms).

**A high value.** An Eo far above the sheet's is a model without grid current: nothing clips at the grid, and
the 5 % point slides out to where the anode bottoms.

**A low value.** A gain well below the sheet's at every supply is a µ fitted low or an ra fitted high.

**What it cannot tell.** The coupling capacitors' and the bypass's low-frequency effects (the bypass is ideal),
which `triode-frequency` and `triode-distortion` take up.

**In the sheets.** 8 sheets, 649 rows (12AX7, 12AU7, 12AY7 by reference, 6C4, 6CG7, 6J5, 6SL7, 6SN7).

**Standard.** the GE and RCA resistance-coupled amplifier chart conditions

#### Harmonics against level, load and bias (`triode-distortion`)

Group `amplifier` · analysis `tran` · engines qspice, ngspice, ltspice · symbols THD, H2, H3, H4, H5.

What a stage's distortion is made of as it is driven harder: the second harmonic of the 3/2 law at low level,
the third and the odd orders as the grid conducts or the anode bottoms, the sign of the second (which way the
waveform leans). The sheets print it only for output stages and as the chart's 5 % point; for preamplifier
stages it is model against model, and the measurement that separates a model fitted to a curve from one
fitted to a point.

**Circuit.** The chart's middle cell, with its cathode bypassed (ideal), by 25 µF, or not at all, and a source
resistance of 0, 10 k or 100 kΩ.

**Conditions.** {vout: [0.1, 0.3, 1, 2, 3, 5, 10, 20, 30, 50], rp_factor: [0.5, 1, 2], rk_factor: [0.5, 1, 2], ck: [ideal, 25e-6, none], rsrc: [0, 1e4, 1e5]}

**Outputs.** `thd@{vout}`, `h2@{vout}` … `h5@{vout}` (%); `h2_sign`; `h3/h2@{vout}`.

**What it cannot tell.** What the part does: no sheet gives it for a small triode.

**In the sheets.** the RC charts' 5 % points; distortion curves in 1 output-stage sheet (5881).

**Standard.** resembles IEC 60151-10 (audio-frequency output power and distortion), model against model

#### Grid-current clipping, blocking and recovery (`triode-overload`)

Group `amplifier` · analysis `tran` · engines qspice, ngspice, ltspice · symbols Vg(mean), t_recover.

A guitar amplifier's preamplifier is driven far past its grid's onset; the grid current charges the coupling
capacitor, the stage biases itself further off, and after the burst it takes a time constant to recover —
"blocking". No sheet measures it; every amplifier that overdrives a triode depends on it, and only a model
with grid current can show it.

**Circuit.** The chart's middle cell, fed through a 22 nF coupling capacitor and a grid stopper, the 1 MΩ
grid leak at the grid, Rk with 25 µF.

**Conditions.** {burst: {f: 1000, periods: 20, level: [1, 3, 10, 30], unit: "× the grid-current onset"}, after: 0.1, cin: 22e-9, rgl: 1e6, rstop: [0, 1e3, 68e3]}

**Outputs.** `vg_shift@{level}` (V), `gain_drop_after@{level}` (dB), `t_recover@{level}` (s), and the
clipped waveform's duty cycle.

**A low value.** No shift at any level: no grid current, `absent`.

**In the sheets.** none.

**Standard.** none

#### Response with source resistance and load capacitance (`triode-frequency`)

Group `amplifier` · analysis `ac` · engines qspice, ngspice, ltspice · symbols f(−3 dB).

The upper corner of a stage is the Miller input of a high-µ triode against the source resistance, and the
output's resistance against the next stage's input and the wiring. It needs the capacitances and nothing else
of the model.

**Conditions.** {cells: "the chart's", rsrc: [0, 1e3, 1e4, 4.7e4, 1e5, 4.7e5, 1e6], cl: [0, 10e-12, 47e-12, 100e-12], f: {from: 1, to: 1e7, per_decade: 20}}

**Outputs.** `f_high@{rsrc},{cl}` (Hz), `f_low` (Hz), `gain_ac` per cell.

**A low value.** No upper corner: no capacitances in the model, `absent`.

**In the sheets.** none print a response; 39 print the capacitances it follows from.

**Standard.** none

#### Cathode follower and cathodyne (`triode-cathode-follower`)

Group `amplifier` · analysis `ac`, `tran` · engines qspice, ngspice, ltspice · symbols gain, Zout, swing.

Two circuits every tube amplifier uses and no sheet tabulates except by an application note (the 12DW7's
cathodyne line): the follower's gain, output resistance and swing, and the split-load phase inverter's
balance and its two unequal output resistances.

**Conditions.** {ebb: [250, 300], ia: [I0/8, I0/4, I0/2], rg: 1e6, cathodyne_rl: [22e3, 47e3, 100e3], thd_limits: [1, 5]}

**Outputs.** follower: `gain`, `zout` (Ω), `swing@1%`, `swing@5%` (V rms); cathodyne: `balance` (|va|/|vk|),
`zout_a`, `zout_k` (Ω), `swing@5%`.

**In the sheets.** none (the 12DW7 names the use).

**Standard.** none

#### Single-ended output stage (`triode-power-se`)

Group `output` · analysis `tran` · engines qspice, ngspice, ltspice · symbols Pout, D2, D3, THD, Ia(0), Ia(max).

The power triode sheets' operating tables (300B, 2A3, 6B4G, 6C33C; the triode-connected columns of the
pentodes) and their curves of power and distortion against load: a supply, a bias (fixed, or a cathode
resistor), a load reflected through an ideal transformer, a drive, and what came out — the power, the
second and third harmonics, the anode current at rest and at full signal. The bench runs every column and a
ladder around it.

**Circuit.** The anode on Vb − RL·(ia − Ī) through its ammeter (an ideal transformer: Ī the mean current under
signal, solved), the cathode on its ideal bypass or grounded, the grid on its bias with the drive on top.

**Conditions.** {columns: "every single-ended column of the part's sheets", rl_factor: [0.25, 0.35, 0.5, 0.7, 1, 1.4, 2, 2.8, 4], drive_factor: "0 to 1.25 in 0.05 steps", bias: [fixed, cathode], fallback: {vb: 250, ia: "I0/3", rl: "2·ra"}, f: 1000, periods: 6, read_last: 4}

**Extraction.** Pout from the fundamental of the load voltage, the harmonics by Goertzel; the mean anode
current at zero and full drive; the peak grid current; the output resistance from the output at two loads.

**Outputs.** `pout`, `thd`, `d2`, `d3`, `ia0`, `ia_max`, `ig1_peak`, `zout`, per column; the curves against load
and drive.

**Model terms that drive it.** everything of `triode-anode` and `triode-positive-grid`.

**A high value.** A power well above the sheet's at the sheet's drive: a model whose traces stay too far apart
at low anode voltage.

**A low value.** Pout falling off before the sheet's drive: grid current setting in early.

**What it cannot tell.** The transformer's own losses and its primary inductance at low frequencies.

**In the sheets.** 3 sheets, 43 rows and 1 graph (and the triode-connected columns of 15 pentode sheets).

**Standard.** resembles IEC 60151-10 (audio-frequency output power and distortion)

#### Push-pull output stage (`triode-power-pp`)

Group `output` · analysis `tran` · engines qspice, ngspice, ltspice · symbols Pout, THD, D3, Ia(0), Ia(max).

Two valves on an ideal centre-tapped primary, v = Raa/4 · (i1 − i2) on each half, driven in antiphase: class A1,
AB1 and AB2 columns of the 300B, 2A3 and 6B4G sheets (and the triode-connected push-pull columns of the
pentodes). Even harmonics cancel; what is left is the third and the crossover, and the anode current that
rises with drive in class AB.

**Conditions.** {columns: "every push-pull column", raa_factor: [0.25, 0.35, 0.5, 0.7, 1, 1.4, 2, 2.8, 4], drive_factor: "0 to 1.25 in 0.05 steps", bias: [fixed, cathode common, cathode per valve], imd: {f1: 50, f2: 6000, ratio: 4}}

**Outputs.** `pout`, `thd`, `d3`, `d5`, `ia0`, `ia_max` (per valve), `ig1_peak`, `zout`, `imd`, per column.

**In the sheets.** 3 sheets, 48 rows (with 1,116 rows of pentode push-pull columns under `pentode-power-pp`).

**Standard.** resembles IEC 60151-10

#### Noise (`triode-noise`)

Group `noise` · analysis `noise` · engines qspice, ngspice, ltspice · symbols en, Req.

A triode's anode current carries shot noise, which a sheet states as an equivalent noise resistance in the
grid (300 Ω for the ECC88, 0.5 kΩ for the ECC85). A behavioural source in a SPICE model is noiseless, so
every model met has none: the measurement reports the noise of the stage and the share that comes from
inside the model, which is the finding.

**Conditions.** {ebb: 250, rp: 1e5, rk: 1.5e3, bypass: ideal, rsrc: [0, 1e3, 1e4], f: {from: 1, to: 1e5, per_decade: 10}}

**Outputs.** `en@10Hz`, `en@1kHz`, `en@10kHz` (V/√Hz) referred to the grid; `inside_share@1kHz`; `req` (Ω);
`noise_note`: absent when the share is zero.

**In the sheets.** 3 sheets, 3 rows.

**Standard.** none

### Pentodes and beam tetrodes

#### Anode and screen characteristics (`pentode-anode`)

Group `static` · analysis `dc` · engines qspice, ngspice, ltspice · symbols Ia(Va), Ig2(Va), knee, ra.

The pentode's chart: anode current against anode voltage per control-grid voltage at a fixed screen, and,
dashed, the screen's current, which rises steeply below the knee as the anode stops collecting. The knee sets
how far an output stage can swing; the screen current at low anode voltage sets how hot the screen runs at
full drive. Koren's pentode equation makes the screen current a function of the grids alone, so its screen
curve is flat across the knee; the Derk/Reefman and Ayumi equations bend it.

**Circuit.** One copy per (Vg2, Vg1), every anode on one swept supply through its ammeter, each screen on
its source through its ammeter, the suppressor at the cathode.

**Conditions.** {va_sweep: {from: 0, to: 1000, step: 1, fine_below: 50, fine_step: 0.1}, vg2: [50, 100, 150, 175, 200, 225, 250, 300, 350, 400, 450], vg1: "the triode ladder"}

**Outputs.** `ia@{va},{vg2},{vg1}`, `ig2@…` (A); `knee@{vg2},{vg1}` (V, Ia at 90 % of its value at Va = Vg2);
`ra@{va},{vg2},{vg1}` (Ω); `ig2_rise@50V/{vg2}`: the screen current at 50 V over its value at Va = Vg2.

**Model terms that drive it.** `KG1`, `KG2`, `KVB` (the knee's `ATAN`), Derk's `SC`, `AP`, `W`, `NU`, `LAM`.

**A low value.** A screen-current rise of exactly 1: the screen equation has no anode in it.

**In the sheets.** 23 sheets, 40 graphs (the PL509's measured with pulses).

**Standard.** resembles IEC 60151-1

#### Positive-grid characteristics, pentode (`pentode-positive-grid`)

Group `static` · analysis `dc` · engines qspice, ngspice, ltspice · symbols Ia, Ig1, Ig2 at Vg1 > 0.

The AB2 region the 5881, 6F6, 6AQ5, 6V6 and 807 sheets draw: anode, screen and grid currents with the grid
driven positive. As `triode-positive-grid`, per screen voltage.

**Conditions.** {vg1: [0, 5, 10, 15, 20, 30], vg2: [250, 300], va_sweep: {from: 0, to: 600, step: 1}}

**Outputs.** `ia@…`, `ig1@…`, `ig2@…` (A).

**In the sheets.** 4 sheets, 4 graphs.

**Standard.** resembles IEC 60151-1

#### Transfer characteristics and cut-off, pentode (`pentode-transfer`)

Group `static` · analysis `dc` · engines qspice, ngspice, ltspice · symbols Ia(Vg1), Ig2(Vg1).

Anode and screen current against control-grid voltage, one curve per screen voltage (the 6550's at
Eb = 500 V and Ec2 150–300 V) or per anode voltage; the cut-off; and, for the beam tubes, the constant-current
view.

**Conditions.** {vg1_sweep: {from: -150, to: 5, step: 0.01}, va: [100, 250, 300, 400, 500], vg2: "the screen ladder", cutoff_ia: [1e-5, 5e-4, 1e-3]}

**Outputs.** `vg_cutoff@{va},{vg2}` (V); `ia@{va},{vg2},0V` (A); `gm@…` (S).

**A low value.** A model that fails before cut-off (`domain`): Koren's screen equation takes the logarithm of
Vg2/µ + Vg1, which turns negative there.

**In the sheets.** 14 sheets, 14 graphs; cut-off rows in the GE pentode sheets (Ec1 at Ib = 0.5 mA) and the 6550
(−40 V at 1 mA).

**Standard.** resembles IEC 60151-1

#### Transconductance, anode resistance and µg1g2 (`pentode-params`)

Group `static` · analysis `ac` · engines qspice, ngspice, ltspice · symbols gm, ra, gm2, µg1g2.

The pentode's three small-signal numbers, by three copies per point: AC on the grid (gm), on the anode (ra), on
the screen (gm2). The amplification factor a pentode sheet prints is the screen's over the grid's, µg1g2 =
gm/gm2 (11 for the EL34), not gm·ra, which for a pentode is in the thousands; the bench publishes both.

**Conditions.** {va: [100, 250, 400], vg2: "the screen ladder", ia: "10 µA to 1 A, 1-2-5", f: 1000, sheet_points: [at the sheet's Vg1, at the sheet's Ia]}

**Outputs.** `gm@…` (S), `ra@…` (Ω), `gm2@…` (S), `mu_g1g2@…`, `mu@…` (gm·ra).

**In the sheets.** 19 sheets, 262 rows and 3 graphs.

**Standard.** resembles IEC 60151-12

#### Screen current and the knee (`pentode-screen`)

Group `static` · analysis `derived` · engines qspice, ngspice, ltspice · symbols Ig2(Va), Ig2/Ia.

The screen's own curves, drawn by 9 sheets (6550, 6AQ5, 6V6, 6146, 807, EF184 …): the current against anode
voltage per grid voltage, and the ratio to the anode current, which a model fitted to the anode family
alone gets wrong first. A view of `pentode-anode`'s screen ammeters, with the ratios at the operating
points of the part's output columns.

**Outputs.** `ig2/ia@{va},{vg2},{vg1}`; `ig2_rise@50V/{vg2}`; the knee per screen voltage.

**In the sheets.** 9 sheets, 15 graphs.

**Standard.** resembles IEC 60151-1

#### Remote cut-off (`pentode-remote-cutoff`)

Group `static` · analysis `dc` · engines qspice, ngspice, ltspice · symbols gm(Vg1), Vg1(gm).

A variable-µ pentode's transconductance falls over decades as its grid goes negative; AGC stages ride on it.
The sheets give the bias for a tiny transconductance (6K7: 2 µmho; 6BA6: 40 µmho) and draw gm on a log
axis, with the screen sometimes fed through a resistor (6BA6: 33 kΩ from 250 V; 6SJ7: 250 kΩ from 300 V).

**Conditions.** {vg1_sweep: {from: -60, to: 0, step: 0.01}, va: 250, vg2: [100, 250], series_screen: [[33e3, 250], [250e3, 300]], gm_levels: [2e-6, 1e-5, 4e-5, 1e-4]}

**Outputs.** `vg1@gm={g}` (V); gm against Vg1 on a log scale.

**A low value.** A gm that drops to nothing within a few volts: a sharp-cut-off equation for a remote-cut-off
part.

**In the sheets.** 2 sheets, 2 graphs and 5 rows.

**Standard.** resembles IEC 60151-12

#### Strapped as a triode (`pentode-triode`)

Group `static` · analysis `dc`, `ac` · engines qspice, ngspice, ltspice.

Fifteen sheets draw and tabulate their pentode strapped as a triode, the screen to the anode, often through
100 Ω: the connection single-ended amplifiers use. The whole triode battery (anode, transfer, params, grid
current) runs again with the strap; a model written as a triode-connected pentode (Ayumi's `…T`) runs the
triode battery directly and is compared here.

**Outputs.** the triode battery's, prefixed `triode:`.

**In the sheets.** 15 sheets, 18 graphs and 30 characteristics rows; their output columns under
`pentode-power-se` and `-pp`.

**Standard.** resembles IEC 60151-1 and -12

#### Ultralinear characteristics (`pentode-ultralinear`)

Group `static` · analysis `dc` · engines qspice, ngspice, ltspice · symbols Ia(Va) with Vg2 = V0 + x(Va − V0).

The screen tapped at a fraction x of the half-primary sees a share of the anode's swing: statically, Vg2 = V0 +
x·(Va − V0) about the quiescent point V0, exactly the curves the Genalex KT88, Tung-Sol 5881 and 6550 sheets
draw, with a second screen-voltage scale.

**Conditions.** {x: [0.2, 0.4, 0.43, 0.5], v0: "the sheet's quiescent point, and 250–450 V in 50 V steps", va_sweep: {from: 0, to: 800}, vg1: "the sheet's steps"}

**Outputs.** `ia@{va},{vg1}` per (x, V0); `ra@V0`.

**In the sheets.** 5 sheets, 9 graphs (the KT88's at 40 %, the 6550's at 40 %, the 5881's at 43 %); their output
columns under `pentode-power-pp`.

**Standard.** none

#### Grid current, pentode (`pentode-grid-current`)

As `triode-grid-current`, with the screen at its ladder: the onset (Mullard's −Vg1 at Ig1 = +0.3 µA for the
EL34 and EF184), the current at zero and positive bias, the grid's share of the cathode current.

**In the sheets.** 4 sheets, 4 graphs and 4 rows. **Standard.** resembles IEC 60151-15

#### The resistance-coupled amplifier chart, pentode (`pentode-rc-amplifier`)

Group `amplifier` · analysis `op`, `ac`, `tran` · engines qspice, ngspice, ltspice · symbols gain, Eo.

The pentode chart adds the screen resistor (the 6J7's 120 cells; the EF86's tables A to C at Vb 100 to 400 V,
and its triode-connected tables, where the output and distortion are read at the onset of grid
current). Run as `triode-rc-amplifier`, the screen fed from Ebb through Rg2 and ideally decoupled (held at Ebb
less Rg2 times its mean current, solved).

**Conditions.** {cells: "every cell of the part's chart", rg2: "as printed (Rsg, Rg2)", universal_rg2_over_rp: [2, 3, 4, 5]}

**Outputs.** as `triode-rc-amplifier`, plus `vg2` (V) and `ig2` (A) per cell.

**In the sheets.** 3 sheets, 235 rows and 2 graphs.

**Standard.** the GE and Philips chart conditions

#### Harmonics, pentode stage (`pentode-distortion`)

As `triode-distortion`, on the pentode chart's middle cell, with the screen resistor ×0.5, 1 and 2: a pentode
stage's distortion is mostly third-order where a triode's is second, and it moves with the screen.

**Standard.** resembles IEC 60151-10, model against model

#### Single-ended output stage, pentode (`pentode-power-se`)

Group `output` · analysis `tran` · engines qspice, ngspice, ltspice · symbols Pout, THD, D2, D3, Ia, Ig2.

Every single-ended column of the sheets — pentode, ultralinear and triode-connected; fixed and cathode bias; the
screen straight on its supply or through Rg2 — and the curves around them: power and distortion against load
(Mullard, GE "operation characteristics at Esig = 8.8 V rms"), against drive, against screen voltage; Ia and Ig2
against drive; the input for 50 mW. Run as `triode-power-se` with the screen on its ideal decoupling.

**Conditions.** {columns: "every single-ended column", rl_factor: "0.25 to 4", vg2_offset: [-50, 0, 50], drive_factor: "0 to 1.25", sensitivity: 0.05}

**Outputs.** `pout`, `thd`, `d2`, `d3`, `ia0`, `ia_max`, `ig2_0`, `ig2_max`, `ig1_peak`, `vin@50mW`, `zout`, per
column; with the sheet's values beside them.

**In the sheets.** 11 sheets, 15 graphs and 332 rows.

**Standard.** resembles IEC 60151-10

#### Push-pull output stage, pentode and ultralinear (`pentode-power-pp`)

Group `output` · analysis `tran` · engines qspice, ngspice, ltspice · symbols Pout, THD, D3, D5, Ia, Ig2, IMD.

The largest body of numbers in the survey: 1,116 rows in 12 sheets. Every push-pull column — pentode with
fixed or cathode bias (the cathode resistor common to both valves or one per valve, as printed), ultralinear at
the printed tap with the screen's series resistor, triode-connected, and Mullard's continuous-sine-wave columns
apart — run on the ideal centre-tapped primary, the screens on their decoupled supply or on the taps (each
half at x·v from the centre, the screen currents in the primary's balance), and the curves around them:
Pout and distortion against Raa and against drive, the anode and screen currents against drive, the KT88's
intermodulation. The anode current that rises with drive in class AB, and the cathode bias that falls back
with it (Mullard's 10 %), are solved per copy.

**Conditions.** {columns: "every push-pull column", raa_factor: "0.25 to 4", drive_factor: "0 to 1.25", vb_factor: [0.9, 1, 1.1], imd: {f1: 50, f2: 6000, ratio: 4}}

**Outputs.** `pout`, `thd`, `d3`, `d5`, `ia0`, `ia_max`, `ig2_0`, `ig2_max` (per valve), `ig1_peak`, `zout`,
`imd`, per column; with the sheet's values beside them.

**A low value.** `failed` with error class `domain`: a model whose screen equation cannot be evaluated past
cut-off cannot be driven into class AB at all.

**In the sheets.** 12 sheets, 25 graphs and 1,116 rows.

**Standard.** resembles IEC 60151-10

#### Noise, pentode (`pentode-noise`)

As `triode-noise`, with the screen through 390 kΩ and decoupled: the EF86's noise condition (Vb = 250 V,
Ra = 100 kΩ), integrated over 25 Hz–10 kHz beside its 2 µV. A pentode adds partition noise to the shot noise;
no model has either.

**In the sheets.** 3 sheets, 10 rows. **Standard.** none

### Rectifiers and diodes

#### Tube voltage drop (`rectifier-drop`)

Group `supply` · analysis `dc` · engines qspice, ngspice, ltspice · symbols Ia(Va).

The plate characteristic each rectifier sheet draws (the 5Y3's to 440 mA at about 115 V): the drop at the
currents the supply runs at, which with the transformer's resistance sets the regulation. Swept from below
zero, so that the initial-velocity current a real diode passes at Va = 0 (the 6AL5's and 6H6's curves start
there) shows or is `absent`.

**Conditions.** {va_sweep: {from: -5, to: 300, step: 0.05}, plates: each alone}

**Outputs.** `va@{ia}` (V) at 1, 10, 100, 250, 500 mA; `ia@0V`, `ia@-1V` (A); `exponent`, `perveance` (10–100 V).

**In the sheets.** 4 sheets, 4 graphs.

**Standard.** resembles IEC 60151-1

#### Full-wave rectifier: regulation, ripple and peak current (`rectifier-regulation`)

Group `supply` · analysis `tran` · engines qspice, ngspice, ltspice · symbols Vdc(Idc), ripple, Ia(peak).

The rectifier sheets' operation characteristics: DC output voltage at the filter's input against DC load
current, one curve per AC voltage per plate, for a capacitor-input filter (C stated) and a choke-input one,
with the plate-supply impedance per plate the curve assumes. Run with two windings in antiphase, each with
its supply resistance and the plate ammeter, the filter, and a resistive load sized for each target current
(the current published is the one that flowed).

**Conditions.** {vac_per_plate: "150 to 550 V in 50 V steps", rs_per_plate: [0, 25, 50, 75, 100, 135, 150, 200], c1: [4e-6, 8e-6, 10e-6, 16e-6, 20e-6, 32e-6, 40e-6, 60e-6], l: [5, 10, 20, 40, infinite], c2: [10e-6, 40e-6], idc: "0 to 300 mA in 10 mA steps", f: [50, 60], periods: 40, read_last: 5, sheet_curves: "every regulation graph with its own C, L and Rs"}

**Outputs.** `vdc@{vac},{idc}` (V), `ripple_pp` (V), `ia_peak` (A, steady, per plate), `efficiency`
(Vdc/(√2·Vac), GE's rectification efficiency), per filter; the regulation slope.

**What it cannot tell.** The transformer's leakage inductance (part of a real plate-supply impedance), and
the voltage drop of a cold filament at switch-on.

**In the sheets.** 4 sheets, 7 graphs and 22 rows.

**Standard.** the GE rating-chart and operation-characteristic conditions

#### Switch-on surge (`rectifier-surge`)

Group `supply` · analysis `tran` · engines qspice, ngspice, ltspice · symbols ia(t) peak.

The rating the sheets guard hardest: the plate current when a hot rectifier switches onto a discharged
capacitor (2.5 A for the 5Y3, 1 A for the 6X4), and the minimum plate-supply resistance that keeps it there
(GE's rating chart III). The regulation deck from discharged capacitors, switched at the mains' zero
crossing and at its peak.

**Outputs.** `surge_peak@{vac},{c1},{rs},{phase}` (A); `rs_min` (Ω) for the sheet's rating.

**In the sheets.** 4 sheets, 7 graphs and 45 rows.

**Standard.** the GE rating-chart conditions

#### Signal diode: initial-velocity current and detection (`diode-signal`)

Group `supply` · analysis `dc`, `tran` · engines qspice, ngspice, ltspice · symbols Ia(Va), Vdc(Vin).

The 6AL5's and 6H6's plate characteristic from below zero, where a vacuum diode conducts by the electrons'
own energy (the contact potential), and their detector curves: DC output against input voltage per load
resistance.

**Conditions.** {va_sweep: {from: -3, to: 20, step: 0.01}, detector: {vin_rms: "1 to 100 V", f: [1000, 455000], rl: [1e5, 2.5e5, 5e5, 1e6], cl: 100e-12}}

**Outputs.** `ia@0V`, `ia@-1V` (A), `va@10uA` (V); `vdc@{vin},{rl}` (V).

**In the sheets.** 2 sheets, 4 graphs and 32 rows.

**Standard.** resembles IEC 60151-1

### Other kinds, where a model exists

#### Frequency converter: conversion transconductance (`heptode-conversion`)

Group `amplifier` · analysis `tran` · engines qspice, ngspice, ltspice · symbols gc.

The 6BE6's sheet gives its conversion transconductance against the signal grid's bias and against the
oscillator grid's current (set at 0.5 mA with 10 V rms into 20 kΩ). The bench runs it for a model with a
separate signal grid (Reefman's heptode): the anode current's component at |fosc − fsig| over the signal's
amplitude. The ECC85's triode-mixer curves (Sc against oscillator voltage) are the same measurement on a
triode.

**Outputs.** `gc@{vg3},{ig1}` (S).

**In the sheets.** 2 sheets, 8 graphs and 42 rows.

**Standard.** resembles IEC 60151-12 (conversion parameters)

#### Tuning indicator (`indicator-shadow`)

The EM84's shadow length against grid voltage needs the deflection electrode and the target, which no model
in the index carries; its triode section, where modelled, runs the triode battery, and the shadow is
`absent`. **In the sheets.** 1 sheet. **Standard.** none

## Which groups matter for which use

| use | groups | look at |
|---|---|---|
| Preamplifier or line stage (12AX7, 12AT7, 12AU7, 6DJ8, EF86) | params, rc-amplifier, frequency, noise | µ, gm, ra at the stage's current (and how µ falls at low current), the chart's gain and Eo at the supply used, the Miller input with the source resistance, whether the model has noise at all |
| Guitar preamplifier driven into clipping | grid-current, overload, distortion, positive-grid | the grid-current onset and the input resistance above it, blocking after a burst, H2 against H3 as the stage clips; a model without grid current neither clips at the grid nor blocks |
| Low-voltage ("starved plate") stage, tube pedals | anode, transfer, params at 12–50 V | the 3/2 law near zero anode voltage, µ and ra at 12–25 V, where most models were never fitted |
| Phase splitter (cathodyne, long-tailed pair) | cathode-follower, params | the balance and the two outputs' resistances, µ and ra matched at the operating current |
| Single-ended output stage (300B, 2A3, EL84, 6V6) | power-se, positive-grid, anode, screen | Pout, D2 and D3 against load and drive, the mean current's shift with signal, the knee, the screen current at low anode voltage |
| Push-pull output stage (EL34, 6L6GC, KT88, 6550) | power-pp, ultralinear, screen, triode-connected | Pout, THD and D3 against Raa and drive per connection, Ia and Ig2 at zero and full signal, whether the model can be driven past cut-off at all |
| Power supply, rectifier sag | rectifier-regulation, rectifier-surge, rectifier-drop | DC volts against load current per filter, the ripple, the peak and switch-on plate currents against the ratings |
| RF, IF and AGC stages (6BA6, 6AU6, 6K7) | remote-cutoff, transfer, conversion | gm over the whole grid range on a log scale, the bias for 2, 10 and 40 µmho, the conversion transconductance |

## What is not measured

Heater warm-up and filament hum, microphony, life and reliability, gas, leakage and insulation, the
mechanical data, class B/C radio-frequency operation and its 459 table rows, the PL509's pulse ratings:
none is in any model, and none is simulable from the equations the models carry. The maximum ratings are
limits, not behaviour; they are kept as conditions the bench never exceeds silently (a sheet layer point
beyond a rating is run and flagged) and drawn as the dissipation hyperbola on the anode charts. The 0A2's
glow discharge and the EM84's fluorescent target have no model in the index; their sheets are surveyed and
not run. Twin triodes are run one section at a time; the 12DW7's two different sections are two models.

## What the preview says

`docker/sim/preview/tube_preview.py` ran the measurements above on ngspice 45.2 over every curated model of the
45 surveyed parts that have one (291 models; 39 minutes with six at a time), the universal layer and the sheet
layer together: 1164 characteristics values, 462 resistance-coupled cells, 452 output columns over 267 models. It is the draft of `decks_tube.py`, not the
pipeline: its numbers are not published, and the per-model results stay with the private tree. What they say
about the models as a whole is below.

**Loading.** 267 of the 291 models ran: 73 as they come, 53 in ngspice's PSpice mode, 141 only with the
parameters their callers pass declared on the `.SUBCKT` line. Of the 24 that did not, 12 failed on their own
domain (a logarithm of a negative argument at the very first operating point), 4 on parameters, 4 on a
subcircuit their file calls and does not hold, 4 for other reasons. Over the whole curated tree (816 models of 162
parts) the same check loads 635; 99 more have pins with no names and are not run.

**What the models carry.** Per family (the family read from the text as `tube-card` would): how many draw grid
current at +1 V, how many pentodes' screen current rises below the knee (the screen current at 50 V over its
value at Va = Vg2, above 1.05), how many put any noise into the stage from inside, how many have capacitances.

| family | models | grid current at +1 V | screen current rises below the knee | noise from inside | capacitances |
|---|---|---|---|---|---|
| Koren | 127 | 72/127 | 22/55 | 0/127 | 94/127 |
| Ayumi | 49 | 33/49 | 16/16 | 0/49 | 49/49 |
| 3/2 law | 44 | 12/29 | 13/15 | 0/29 | 29/29 |
| Derk/Reefman | 24 | 14/22 | 8/8 | 0/22 | 22/22 |
| other | 23 | 7/9 | — | 0/9 | 9/9 |

No model has noise of its own. The Koren pentode's screen current depends on the grids alone in 33 of its 55
models; Ayumi's, Derk's and the 3/2-law pentodes all bend it. Koren's and Derk's grid diode adds its junction
capacitance (`CJO = 10 pF`, reverse-biased) to Cg1k: the 12AX7's Koren model reads 8.0 pF where its `CCG` says
2.3 pF, the EL34's Derk model 18.4 pF for 15.4 pF.

**Against the sheets, by family.** The median distance from the sheet's value (|model/sheet − 1|), and in
brackets how many values it is the median of. The characteristics (Ia, gm, µ) are read at the sheet's own
anode and grid voltages and at its anode current; the RC chart's gain and Eo as GE defines them; the output
columns at the sheet's supply, bias, load and drive.

| family | Ia at the sheet's Vg1 | gm at the sheet's Ia | µ at the sheet's Ia | RC gain | RC Eo | Pout | THD | Ia at rest |
|---|---|---|---|---|---|---|---|---|
| Koren | 4 % (169) | 6 % (131) | 5 % (97) | 12 % (228) | 26 % (225) | 8 % (115) | 48 % (115) | 7 % (98) |
| 3/2 law | 5 % (45) | 8 % (41) | 5 % (29) | 14 % (81) | 68 % (78) | 8 % (54) | 51 % (54) | 9 % (38) |
| Ayumi | 4 % (42) | 4 % (36) | 4 % (30) | 7 % (78) | 16 % (78) | 5 % (44) | 36 % (44) | 6 % (36) |
| Derk/Reefman | 14 % (38) | 6 % (35) | 6 % (29) | 8 % (66) | 30 % (66) | 10 % (27) | 88 % (27) | 9 % (19) |
| other | 30 % (5) | 10 % (5) | 40 % (4) | 64 % (9) | 70 % (5) | 2 % (2) | 30 % (2) | 5 % (2) |

Every family reproduces the operating points within a few per cent, and the output stages' power within 5 to
10 %. The resistance-coupled chart's Eo is where the families part: a model without grid current (most of the
plain 3/2-law ones) overshoots it by two-thirds, because nothing clips at the grid before the anode bottoms.
Distortion is where every family is weakest: a median of 36 to 88 % from the sheet's figure, worst at the
sheets' lowest distortions (Mullard's 0.35 % ultralinear column) and in class AB, where the crossover depends
on the curvature near cut-off that the models were not fitted on.

**Output stages.** 242 of the 452 output columns ran. The 210 that did not are all models of Koren's family:
its screen equation takes the logarithm of Vg2/µ + Vg1, which is negative past cut-off, so a pentode, an
ultralinear or a strapped pentode driven into class AB fails (89 of its 121 push-pull pentode columns, 51 of
72 ultralinear). Every other family ran every column. Where they ran, the 300B's Western Electric columns came
out at 0.98–1.01 of the sheet's power across nine models (Ayumi's 300B: 5.95 W for 6 W, 62 → 74 mA for
62 → 74 mA), the EL34's Mullard columns at 0.96–1.03 (40.4 W for the ultralinear 40 W, 19.6 W for the
triode-connected 19 W), the KT88's at 0.86–0.94, the 6550's at 1.01–1.12.

**The best model per part**, by the mean of those distances over everything its sheets give, with the medians
of its ratios to the sheet:

| part | models compared | best model | Ia at the sheet's Vg1 | gm, ra, µ at the sheet's Ia | RC gain, Eo | Pout, THD, Ia(0) |
|---|---|---|---|---|---|---|
| 12AU7 | 10 | ayumi | 1.00 | 1.00, 1.02, 1.02 | 1.08, 1.01 | —, —, — |
| 12AX7 | 8 | suusi-tubes | 0.92 | 0.95, 1.00, 0.95 | 1.09, 0.97 | —, —, — |
| 12AY7 | 8 | ayumi-2 | 1.00 | 1.01, 1.07, 1.08 | —, — | —, —, — |
| 300B | 9 | suusi-tubes | 0.98 | —, —, — | —, — | 0.99, 0.70, 0.97 |
| 5881 | 5 | suusi-tubes | 1.06 | 1.15, —, 1.00 | —, — | 1.14, 1.00, 0.99 |
| 6146 | 5 | ayumi | 1.64 | —, —, — | —, — | —, —, — |
| 6550 | 9 | koren | 1.15 | —, —, — | —, — | 1.10, 0.86, 1.15 |
| 6AQ5 | 2 | reefman | 0.87 | 0.99, 0.71, 1.02 | —, — | —, —, — |
| 6AQ8 | 2 | ayumi | 1.29 | 1.08, —, 0.95 | —, — | —, —, — |
| 6C33C | 9 | bordodynov-5 | — | 0.74, 0.69, — | —, — | —, —, — |
| 6C4 | 4 | ayumi | 1.01 | 1.09, 1.00, 1.09 | 1.05, 0.87 | —, —, — |
| 6C45 | 2 | bordodynov-2 | — | 1.03, —, 0.91 | —, — | —, —, — |
| 6CA7 | 7 | suusi-tubes | 1.04 | 1.01, 1.43, 1.02 | —, — | 0.96, 2.82, 1.05 |
| 6CG7 | 7 | reefman | 0.99 | 1.03, 0.97, 1.01 | 1.09, 1.05 | —, —, — |
| 6DJ8 | 9 | ayumi | 0.99 | 0.98, —, 0.98 | —, — | —, —, — |
| 6J5 | 1 | bordodynov | 1.07 | 1.01, 0.98, 0.99 | 1.17, 1.17 | —, —, — |
| 6L6GC | 9 | reefman | 0.97 | 1.02, 1.19, — | —, — | —, —, — |
| 6SL7 | 9 | ayumi | 0.96 | 1.03, 0.94, 0.97 | 1.06, 1.45 | —, —, — |
| 6SN7 | 10 | suusi-tubes-2 | 0.97 | 1.03, 0.99, 1.03 | 1.10, 1.03 | —, —, — |
| 6V6GT | 10 | reefman | 0.96 | 1.03, 1.04, 0.97 | —, — | —, —, — |
| 807 | 3 | suusi-tubes | 0.98 | —, —, — | —, — | —, —, — |
| ECC85 | 7 | suusi-tubes-2 | 1.04 | 1.03, —, 1.04 | —, — | —, —, — |
| ECC99 | 4 | suusi-tubes | 0.96 | 1.02, 1.02, 1.03 | —, — | —, —, — |
| EF184 | 1 | reefman | 0.49 | 0.84, 1.57, 1.21 | —, — | —, —, — |
| EF86 | 7 | ayumi-2 | 0.99 | 1.00, 0.67, 1.02 | —, — | —, —, — |
| EL34 | 9 | ayumi | 0.94 | 0.87, 1.09, 0.94 | —, — | 1.03, 3.19, 1.00 |
| EL84 | 10 | bordodynov | 1.03 | —, —, — | —, — | —, —, — |
| EL90 | 3 | bordodynov-2 | 1.03 | 1.05, 2.29, 1.00 | —, — | —, —, — |
| KT88 | 4 | ayumi-2 | — | 0.98, 1.01, 1.03 | —, — | 0.94, 1.70, 0.84 |

**The spread between a part's models** is often larger than any model's distance from the sheet: the 12AX7's
eight models give from 0.46 to 1.25 times the sheet's anode current at the sheet's operating points, the 6C4's
from 1.01 to 21.6.

| part | models | Ia/sheet at the sheet's Vg1, lowest–highest model | gm/sheet at the sheet's Ia | Pout/sheet |
|---|---|---|---|---|
| 12AU7 | 10 | 0.94–1.11 | 1.00–1.16 | — |
| 12AX7 | 8 | 0.46–1.25 | 0.95–1.24 | — |
| 12AY7 | 8 | 1.00–1.03 | 0.90–1.06 | — |
| 300B | 9 | 0.96–1.04 | — | 0.98–1.01 |
| 5881 | 5 | 1.06–1.48 | 1.15–1.15 | 1.13–1.24 |
| 6146 | 5 | 1.64–1.84 | — | — |
| 6550 | 9 | 0.97–1.15 | 1.05–1.09 | 1.01–1.12 |
| 6AQ5 | 2 | 0.87–0.99 | 0.99–1.04 | — |
| 6AQ8 | 2 | 1.29–1.29 | 1.08–1.08 | — |
| 6C33C | 9 | — | 0.74–1.58 | — |
| 6C4 | 4 | 1.01–21.56 | 0.23–1.09 | — |
| 6C45 | 2 | — | 1.03–1.03 | — |
| 6CA7 | 7 | 0.98–1.13 | 0.84–1.13 | 0.96–1.02 |
| 6CG7 | 7 | 0.96–1.02 | 1.03–1.12 | — |
| 6DJ8 | 9 | 0.68–1.06 | 0.62–1.03 | — |
| 6J5 | 1 | 1.07–1.07 | 1.01–1.01 | — |
| 6L6GC | 9 | 0.91–1.12 | 1.02–1.19 | — |
| 6SL7 | 9 | 0.87–1.21 | 1.01–1.28 | — |
| 6SN7 | 10 | 0.82–1.01 | 1.02–1.14 | — |
| 6V6GT | 10 | 0.96–1.06 | 0.91–1.06 | — |
| 807 | 3 | 0.89–1.19 | — | — |
| ECC85 | 7 | 0.82–1.30 | 0.88–1.12 | — |
| ECC99 | 4 | 0.90–0.96 | 1.02–1.13 | — |
| EF184 | 1 | 0.49–0.49 | 0.84–0.84 | — |
| EF86 | 7 | 0.71–1.20 | 0.95–1.06 | — |
| EL34 | 9 | 0.86–1.12 | 0.87–1.13 | 0.96–1.03 |
| EL84 | 10 | 0.78–1.10 | 0.96–1.05 | 0.90–1.03 |
| EL90 | 3 | 1.03–1.03 | 1.05–1.05 | — |
| KT88 | 4 | — | 0.98–1.01 | 0.86–0.94 |

**Low anode voltage.** At Va = 0 Duncan's 12AX7A passes 0.35 mA (its 3/2 law carries an offset of 45 V); at
5 V and Vg1 = 0 the 12AX7 models give from 0.03 mA (Koren) to 0.59 mA (Ayumi). No sheet tabulates the region;
the GE chart draws it from the origin.

**Graphs.** 590 ok, 154 family not read, 95 failed, 70 model strapped as a triode, 26 not a static graph, 17 grid voltage not read, 17 anode voltage not read, 9 axis not read, 7 ultralinear tap not read, 2 screen voltage not read — of the 987 graph-and-model pairs; "strapped as a
triode" is a pentode part's `…T` model, which answers only its sheet's triode-connected graphs. The rows a
graph cannot be redrawn from alone (a family labelled only on the scan, a fixed electrode not printed) are the
survey's to complete, not the model's.

## The entries published so far

The catalogue (`data/bench/measurements.yaml`) carries the first eight entries, the triode's, as the site's
method page shows them; the 12AX7's ten curated models were measured with them, on ngspice, by
`docker/sim/preview/tube_records.py`, and their records sit in `data/verification/models/supplement/` until a
release packs them. What follows is generated from the catalogue (`sei bench methods --write`).

<!-- measurements:start -->
Catalogue version `m-13`; the codes and the uses table are in [model-characterisation.md](model-characterisation.md).

### Vacuum tubes

#### Does the model load, in which dialect, and at what operating points (`tube-runs`)

Group `dc` · analysis `op` · engines ngspice · symbols I0, Ia, Ig.

The first fact about a tube model, and the one tube models fail most: whether ngspice reads it, and in which of its modes. Tube models are written for PSpice, for LTspice or for Micro-Cap, often in one file; the model is tried as it comes, then in ngspice's PSpice (psa), LTspice (lta) and combined (ltpsa) compatibility modes, then again with the parameters its callers pass declared on the .SUBCKT line (an LTspice habit ngspice refuses). The mode that settles, and whether parameters had to be declared, are published as results; the text is never rewritten beyond that. Read at four operating points, the quickest sanity check of a triode model and its own scale: I0, the anode current at 250 V and zero bias.

**Circuit.** Four copies of the triode, cathode grounded: anode at 100 V and the grid at 0 V; anode at 250 V and the grid at 0, −2 and −10 V; one operating point, every anode and grid current read through its source.

Drawing: DUT; anode supply; grid source; ammeters in anode and grid. Differs from the netlist: the drawing also shows the pentode and diode copies of the battery; a triode runs copy A only.

**Conditions.** {points: [[100, 0], [250, 0], [250, -2], [250, -10]], modes: [none, psa, lta, ltpsa], declare_params: [False, True]}

**Extraction.** The first mode that settles to finite currents, trying every mode as the model comes before declaring any parameter; the anode and grid currents at each point (a grid current is positive into the grid).

**Outputs.**

- `runs`: true when ngspice returned an operating point
- `mode`: the ngspice mode that read it: none, psa, lta or ltpsa
- `params_declared`: whether the parameters its callers pass had to be declared on the .SUBCKT line
- `error_class`: when it does not load in any mode: params, subckt, domain or syntax
- `ia@{va},{vg}` (A): anode current at the point; at 250 V and 0 V it is I0, the model's own scale
- `ig@{va},{vg}` (A): grid current at the point

**What it cannot tell.** That the model is right: a model that loads in one mode only is a dialect fact, not a verdict.

**Standard.** none

#### Interelectrode capacitances (`tube-capacitance`)

Group `capacitance` · analysis `ac` · engines ngspice · symbols Cg1k, Cg1a, Cak.

The direct capacitances every sheet tabulates, measured as the sheets define them: one electrode driven with 1 V of AC at 1 MHz, every other electrode held at AC ground through its source, and the current into each undriven one read. The sheets give them cold; a model gives one set of constants, often with the grid-current diode's junction capacitance added to Cg1k without its author having meant it, which the cold and hot values show: biased at cut-off, the diode is off and adds its zero-bias junction; hot, at a quarter of I0, it adds more.

**Circuit.** Three copies of the triode at 250 V on the anode: the grid driven, the anode driven, the cathode driven, each with 1 V of AC on its bias; the grid at the model's cut-off at 250 V (cold), and again at the grid voltage that gives a quarter of I0 (hot).

Drawing: DUT; one electrode driven with 1 V of AC; the others at AC ground through ammeters. Differs from the netlist: the drawing shows a pentode and its screen; a triode has no screen copy.

**Conditions.** {va: 250, vg1: [cut-off at 10 µA, the grid voltage for I0/4], f: 1e+06, v_ac: 1}

**Extraction.** C = Im(i) / (2πf) for each pair of electrodes, the larger of the two directions.

**Outputs.**

- `c_g1k` (F): grid to cathode, cold (the grid at cut-off)
- `c_g1a` (F): grid to anode, cold: the Miller capacitance's root
- `c_ak` (F): anode to cathode, cold
- `c_g1k@hot` (F): grid to cathode at a quarter of I0
- `c_g1a@hot` (F): grid to anode at a quarter of I0
- `c_ak@hot` (F): anode to cathode at a quarter of I0

**Card parameters that drive it:** CCG, CGP, CCP, CJO.

**A high value.** A Cg1k several pF above the sheet's, larger hot than cold, is the grid diode's junction in parallel.

**A low value.** Zero everywhere: no capacitances in the model, and no upper corner in any stage built with it.

**What it cannot tell.** The shield's effect, the socket and the wiring, and a hot cathode's space-charge increase of Cg1k.

**Standard.** resembles IEC 60151 interelectrode capacitance measurement, with the shield conditions the GE sheets name

#### Anode characteristics (`triode-anode`)

Group `dc` · analysis `dc` · engines ngspice · symbols Ia(Va), Vg1.

The chart every triode sheet opens with: anode current against anode voltage, one trace per grid voltage. Three things are read at a glance: the spacing of the traces (µ: a trace's shift along the voltage axis per volt of grid), their slope (ra), and their curvature (the 3/2 law that makes a triode's second harmonic). The grid step is the model's own: its cut-off at 250 V over eight, on the 1-2-2.5-5 series, so that nine traces from zero bias reach cut-off whatever the tube (0.5 V for a 12AX7, as GE draws it). Near zero anode voltage, where pedals run a 12AX7, models that agree at the sheet's points disagree by a factor of twenty (0.03 to 0.59 mA at 5 V and zero bias).

**Circuit.** Nine copies of the triode, cathode grounded, the grid of trace k held at k steps below zero, every anode on one supply swept from 0 to 600 V in 1 V steps, each anode current read through a 0 V source.

Drawing: DUT; swept anode supply; grid voltage source at −k × step; ammeter in the anode; ammeter in the grid. Differs from the netlist: the copies are drawn as one triode with a stepped grid.

**Conditions.** {traces: 9, step: {from: tube-runs and triode-transfer, cutoff_at_va: 250, cutoff_ia: 1e-05, divisor: 8, series: [1, 2, 2.5, 5]}, va_sweep: {from: 0, to: 600, step: 1, unit: V}}

**Extraction.** Each trace on the grid; a trace stops where Va × Ia passes the power at the model's own I0 point (250 V × I0), as a sheet dashes its traces past the dissipation limit. The zero-bias trace read at 0, 5, 12, 25, 50 and 250 V.

**Outputs.**

- `vg1_step` (V): the grid step: the model's cut-off at 250 V over eight, on the 1-2-2.5-5 series
- `ia@{va},0V` (A): anode current at zero bias, at 0, 5, 12, 25, 50 and 250 V: zero at 0 V in any physical model
- `p_limit` (W): the power each trace stops at: 250 V × I0

Curves: Ia, Vg1=0·step (ia against va, lin, at Vg1/step = 0); Ia, Vg1=-1·step (ia against va, lin, at Vg1/step = -1); Ia, Vg1=-2·step (ia against va, lin, at Vg1/step = -2); Ia, Vg1=-3·step (ia against va, lin, at Vg1/step = -3); Ia, Vg1=-4·step (ia against va, lin, at Vg1/step = -4); Ia, Vg1=-5·step (ia against va, lin, at Vg1/step = -5); Ia, Vg1=-6·step (ia against va, lin, at Vg1/step = -6); Ia, Vg1=-7·step (ia against va, lin, at Vg1/step = -7); Ia, Vg1=-8·step (ia against va, lin, at Vg1/step = -8). Shown first: Vg1/step = all.

Beside the point under the cursor: P (W), power dissipated at the anode, Va × Ia; ra (Ω), anode resistance, the local slope of the trace.

**Card parameters that drive it:** MU, EX, KG1, KP, KVB.

**A high value.** Traces that keep climbing steeply at high anode voltage are a low ra; a current at Va = 0 is an offset in the model's 3/2 law, which no tube has.

**A low value.** Traces evenly spaced into cut-off are a model with constant µ: no real triode has it.

**What it cannot tell.** The thermal droop of a real anode at full dissipation, and the spread between tubes of one type.

**Standard.** resembles IEC 60151-1 (electrode currents); the sheets' average plate characteristics

#### Transfer characteristics and cut-off (`triode-transfer`)

Group `dc` · analysis `dc` · engines ngspice · symbols Ia(Vg1), Vg1(cut-off).

Anode current against grid voltage at fixed anode voltages: the curve the bias is set on. Its foot is the cut-off the sheets quote as the grid voltage for 10 µA (GE, RCA, Sylvania), its upper part the 3/2 law. The sweep runs from −300 V, so it serves every triode; each curve is drawn from a quarter beyond the point where its current falls to a thousandth of its zero-bias value, up to +1 V.

**Circuit.** Six copies of the triode, cathode grounded, one per anode voltage held by its source, every grid on one source swept from −300 V to +5 V in 20 mV steps through a 0 V source each (the grid current, read by triode-grid-current from the same sweep).

Drawing: DUT; anode supply; swept grid source; ammeter in the anode; ammeter in the grid. Differs from the netlist: the copies are drawn as one triode.

**Conditions.** {va: [100, 150, 200, 250, 300, 400], vg1_sweep: {from: -300, to: 5, step: 0.02, unit: V}, cutoff_ia: 1e-05}

**Extraction.** Each curve on the grid, finer near zero; the cut-off by log interpolation where the current passes 10 µA; the current at zero bias. A model whose equations fail before −300 V is swept from the deepest start it can be evaluated at (−100, −40, −15 or −5 V), which is published.

**Outputs.**

- `vg_cutoff@{va}` (V): grid voltage where the anode current falls to 10 µA
- `ia@{va},0V` (A): anode current at zero bias
- `sweep_from` (V): where the sweep could start: −300 V unless the model fails before

Curves: Ia, Va=100V (ia against vg1, lin, at Va = 100); Ia, Va=150V (ia against vg1, lin, at Va = 150); Ia, Va=200V (ia against vg1, lin, at Va = 200); Ia, Va=250V (ia against vg1, lin, at Va = 250); Ia, Va=300V (ia against vg1, lin, at Va = 300); Ia, Va=400V (ia against vg1, lin, at Va = 400). Shown first: Va = all.

Beside the point under the cursor: gm (S), transconductance, the local slope of the curve.

**Card parameters that drive it:** MU, EX, KG1, KP.

**A high value.** A cut-off far more negative than the sheet's is a µ fitted low.

**A low value.** A foot that falls off a cliff (no current below a sharp cut-off) is a URAMP or LIMIT that a real cathode has no equivalent of.

**What it cannot tell.** The exponent of the 3/2 law on its own: triode-params reads its consequences, µ and gm against current.

**Standard.** resembles IEC 60151-1; the cut-off condition of the GE and RCA sheets

#### Amplification factor, transconductance and anode resistance against current (`triode-params`)

Group `dc` · analysis `ac` · engines ngspice · symbols µ, gm, ra.

The three numbers every triode sheet prints at its operating points, and GE's curves of them against plate current: measured as small-signal quantities at 1 kHz at a ladder of anode currents, at three anode voltages. Real triodes lose µ at low current; a model fitted at one point usually keeps it, which the ratio of µ at the lowest current to µ at its highest shows.

**Circuit.** Two copies per point: AC on the grid with the anode held (gm), AC on the anode with the grid held (1/ra); the grid voltage for each anode current from the transfer sweep; µ = gm · ra.

Drawing: DUT; anode supply; grid bias with 1 V of AC; ammeter in the anode. Differs from the netlist: two copies per point, drawn side by side once.

**Conditions.** {va: [100, 250, 400], ia: [1e-05, 2e-05, 5e-05, 0.0001, 0.0002, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1], f: 1000, v_ac: 1}

**Extraction.** gm = |i_a / v_g|, ra = |v_a / i_a|, µ = gm · ra; a current the model does not reach below zero bias is left out.

**Outputs.**

- `mu@1mA,{va}`: amplification factor at 1 mA
- `gm@1mA,{va}` (S): transconductance at 1 mA
- `ra@1mA,{va}` (Ω): anode resistance at 1 mA
- `mu_ratio@250V`: µ at the lowest current over the largest µ, at 250 V: 1 is a constant-µ model

Curves: µ, Va=100V (mu against ia, lin, at Va = 100); µ, Va=250V (mu against ia, lin, at Va = 250); µ, Va=400V (mu against ia, lin, at Va = 400); gm, Va=100V (gm against ia, log, at Va = 100); gm, Va=250V (gm against ia, log, at Va = 250); gm, Va=400V (gm against ia, log, at Va = 400); ra, Va=100V (ra against ia, log, at Va = 100); ra, Va=250V (ra against ia, log, at Va = 250); ra, Va=400V (ra against ia, log, at Va = 400). Shown first: Va = all.

**Card parameters that drive it:** MU, EX, KG1, KP, KVB.

**A high value.** gm above the sheet's at the sheet's current with ra below it: a model fitted for gain at the cost of the curve's shape.

**A low value.** µ flat to within a percent over three decades of current: the constant-µ equation.

**What it cannot tell.** What the stage does with them: triode-rc-amplifier runs the stage.

**Standard.** resembles IEC 60151-12 (electrode resistance, transconductance, amplification factor)

#### Grid current: onset, contact potential and input resistance (`triode-grid-current`)

Group `dc` · analysis `dc` · engines ngspice · symbols Ig(Vg1), Vg1(Ig = 0.3 µA).

Where the grid starts to conduct is where a stage clips asymmetrically and a coupling capacitor starts charging: the guitar amplifier's blocking and the grid-leak bias both live here. Mullard and Philips print it as the grid voltage at +0.3 µA; GE and RCA build their zero-bias chart cells on the small negative current a real grid draws below zero, which few models have.

**Circuit.** The transfer sweep's grid ammeters, at three anode voltages.

Drawing: DUT; anode supply; swept grid source; ammeter in the grid.

**Conditions.** {va: [100, 250, 400], vg1_sweep: {from: -5, to: 5, unit: V, from_measurement: triode-transfer}, onset: [3e-07, 1e-06]}

**Extraction.** The grid current on the grid (positive into the grid); the grid voltage where it passes +0.3 µA and +1 µA; its value at −0.5, 0, +1 and +5 V; the input resistance at +1 V as the slope over ±50 mV.

**Outputs.**

- `vg@ig=0.3uA` (V): grid voltage where the grid current passes +0.3 µA, Mullard's limit
- `vg@ig=1uA` (V): grid voltage where it passes +1 µA
- `ig@{vg}` (A): grid current at −0.5, 0, +1 and +5 V (250 V on the anode)
- `rin@+1V` (Ω): the grid's input resistance at +1 V

Curves: Ig, Va=100V (ig against vg1, lin, at Va = 100); Ig, Va=250V (ig against vg1, lin, at Va = 250); Ig, Va=400V (ig against vg1, lin, at Va = 400). Shown first: Va = 250.

Beside the point under the cursor: rin (Ω), the grid's input resistance, the local slope.

**Card parameters that drive it:** RGI, IS, CJO.

**A high value.** An onset well below zero bias is a grid that loads the previous stage at rest.

**A low value.** No current up to +1 V: the model has no grid current (`absent`), so nothing in it clips at the grid or blocks.

**What it cannot tell.** Gas current and leakage, which add a positive grid current a real tube has and no model does.

**Standard.** resembles IEC 60151-15 (spurious electrode currents)

#### The resistance-coupled amplifier chart (`triode-rc-amplifier`)

Group `distortion` · analysis `tran` · engines ngspice · symbols gain, Eo, Ia.

GE's and RCA's chart, cell by cell, for the cells the part's own sheet prints: for a supply Ebb, a plate resistor Rp and the next stage's grid resistor Rs, the cathode resistor the sheet gives, run as GE defines it — the gain at 2.0 V rms out, Eo the largest output (rms) before the distortion reaches 5 %, the cathode resistor "adequately by-passed" (an ideal bypass: the cathode held at Rk times the stage's mean current under signal, found by iteration). The grid-leak cells (Rg1 = 10 MΩ, no cathode resistor) rest on the small current a real grid draws below zero: a model without it runs them at zero bias. The harmonics against the output level are drawn for the chart's middle cell (300 V, 240 kΩ, 510 kΩ).

**Circuit.** Ebb through Rp and an ammeter to the anode; the cathode on its ideal bypass; the output through 10 µF into Rs; a 1 kHz sine on the grid, with the stage's own grid resistor Rg1 to ground; fifteen copies per cell, one per drive level in half-octave steps from the one that gives 2 V rms out.

Drawing: DUT; supply Ebb; plate resistor Rp; ammeter in the anode; ideal cathode bypass; coupling capacitor; next grid resistor Rs; grid resistor Rg1; 1 kHz source; voltmeter on the output. Differs from the netlist: the fifteen drive levels are drawn as one source.

**Conditions.** {cells: every cell of the part's sheet: Ebb, Rp, Rs, Rg1 and Rk as printed, f: 1000, periods: 30, read_last: 10, vout_for_gain: 2, thd_for_eo: 5, bypass: ideal, cc: 1e-05}

**Extraction.** The quiescent point from an operating point with the real Rk; the bypass voltage per copy iterated to Rk times the mean cathode current; the gain from the copy that gives 2 V rms; Eo by log-log interpolation of THD against output to 5 %; the harmonics by Goertzel over the last ten periods; the first drive (peak) at which the grid's current passes 1 µA.

**Outputs.**

- `gain@{cell}`: voltage gain at 2.0 V rms out; a cell is Ebb, Rp, Rs, and grid-leak for Rg1 = 10 MΩ
- `eo@{cell}` (V): the largest output, rms, at 5 % THD
- `ia0@{cell}` (A): the quiescent anode current with the sheet's Rk
- `vk@{cell}` (V): the quiescent cathode voltage, the bias
- `grid_onset@{cell}` (V): the peak drive at which the grid current passes 1 µA

Curves: THD (thd against vout, log); H2 (h2 against vout, log); H3 (h3 against vout, log).

**Card parameters that drive it:** MU, EX, KG1, KP, RGI.

**A high value.** An Eo far above the sheet's is a model without grid current: nothing clips at the grid, and the 5 % point slides out to where the anode bottoms.

**A low value.** A gain below the sheet's at every supply is a µ fitted low or an ra fitted high.

**What it cannot tell.** The coupling capacitors' and a real bypass's low-frequency effects, and the next stage's Miller input.

**Standard.** the GE and RCA resistance-coupled amplifier chart conditions

#### Noise (`triode-noise`)

Group `noise` · analysis `noise` · engines ngspice · symbols en, Req.

A triode's anode current carries shot noise, which a sheet states as an equivalent noise resistance in the grid (300 Ω for the ECC88). A behavioural source in a SPICE model is noiseless, so most tube models have none: the stage's noise is read, referred to the input, with the share of it that comes from inside the model. A share of zero is the finding, coded `absent`; the noise left is the resistors'.

**Circuit.** A grounded-cathode stage: 250 V through 100 kΩ, 1.5 kΩ in the cathode bypassed by 1 F, the input through 1 kΩ; ngspice's noise analysis from 1 Hz to 100 kHz.

Drawing: DUT; supply Ebb; plate resistor; bypassed cathode resistor; source resistance; noise source; voltmeter on the output.

**Conditions.** {ebb: 250, rp: 100000, rk: 1500, rsrc: 1000, f: {from: 1, to: 100000, per_decade: 10, unit: Hz}}

**Extraction.** The input-referred noise at 10 Hz, 1 kHz and 10 kHz; at 1 kHz the share of the output noise from the subcircuit's own elements, and the equivalent noise resistance en²/4kT less the source's.

**Outputs.**

- `en@{f}` (V/√Hz): input-referred noise of the stage at 10 Hz, 1 kHz, 10 kHz
- `inside_share@1kHz`: the share of the output noise that comes from inside the model
- `req@1kHz` (Ω): equivalent noise resistance in the grid, less the 1 kΩ source

**A low value.** A share of zero: the model has no noise of its own, and the stage is as quiet as its resistors.

**What it cannot tell.** Flicker noise and its corner, which no model met here carries.

**Standard.** none
<!-- measurements:end -->

## Next steps

What remains to carry the tubes through the pipeline that the bipolar bench runs is the checklist of
[bench-roadmap.md](bench-roadmap.md): the catalogue entries (kind `tube`, the measurements above with
these ids), `decks_tube.py` in the simulator images on the shape of `tube_preview.py`'s decks, the
`tube-card` reader in `models/cards.py`, the SVGs of the drawings (`make bench-drawings-all`), and the runs
in QSPICE and LTspice, whose dialects differ from ngspice's on exactly the constructs listed under
`tube-runs`.
