# Characterising the SPICE transistor models

Every transistor model the site lists runs through the same bench: a catalogue of measurements at
universal conditions — decades of current, a short list of voltages, a few temperatures — the same for
every model of a kind. What comes out is numbers and curves per model, never an opinion. This page is the
bench's specification; the site's method page (`?bench=`) shows the same catalogue. How the simulators
are built and run: [docker/sim/README.md](../docker/sim/README.md).

## Principles

- **Behaviour only.** Reading what the real part does (its data sheet) and judging how well a model fits
  it are separate tasks. Nothing here depends on a data sheet or on the part's class, so a model is
  characterised the day it is indexed.
- **Intrinsic ladders.** Conditions span any discrete transistor (1 µA to 10 A, 1 to 10 V, −55 to 150 °C).
  Where a condition would depend on the part, the summary points come from the model itself (the
  current at which hFE peaks, the highest step that still converges).
- **Numbers, not opinions.** Values at a fixed number of significant figures, decimated curves, a code
  where a number cannot stand, the agreement between simulators, and the digest of every deck.
- **Explained once, per measurement.** Each measurement has one explanation (below, and on the method
  page); per-model cells link to it and carry no prose.
- **Reproducible.** Pinned images, deterministic deck text, a sha256 per deck in every result, the
  catalogue version in every file.

What the card itself contains — family, level, which parameters are present *and effective*, pins,
kinship — is read from its text by `sei models cards`. The behaviour groups the site shows are those of
`src/spicy_electronics_index/models/behaviours.py`.

## What is measured

The catalogue is `data/bench/measurements.yaml`; `make bench-methods` checks it and rewrites this
section from it, so the two never differ. Conventions: bipolar DC sweeps drive the base from a
behavioural current source `IB = 10^V(x)` while a voltage source sweeps `x` (a current into a
junction converges where forcing the collector current does not); sampling is 20 points per decade
in DC, 20 to 40 per decade in AC, `reltol = 1e-4`, 25 °C unless the entry says otherwise, SI units
throughout; one deck packs several copies of the transistor wherever the analysis allows it, and a
transient is one deck per step.

<!-- measurements:start -->
Catalogue version `m-12`. Codes a number can be replaced by:

- `ok` — measured
- `absent` — the card has no parameter for this physics, so the number would be the simulator's default, not the model's
- `n/a` — the model never reached this step (not saturated, not conducting, not switched) or the step is above the card's own breakdown
- `failed` — the simulator did not return a waveform for this deck; the error class is recorded
- `suspect` — a value no transistor has (the behavioural base drive settling on a wrong point in one engine); kept out of the numbers

Which groups of measurements matter for which use:

| use | groups | look at |
|---|---|---|
| Small-signal audio stage or preamplifier | dc, noise, capacitance, distortion | hFE and VBE between 100 µA and 1 mA, how flat hFE is over that range, en at 10 Hz to 1 kHz and the 1/f corner, Cob. The switching times do not matter. |
| Power output stage | high-current, temperature, dc, switching | hFE at 1 A and above and where it starts to fall, VCE(sat) and its slope with current, VBE and hFE against temperature, fT at high current. A model whose gain never falls will flatter an output stage. |
| Switch or driver | switching, high-current, breakdown, dc | td, tr, ts and tf at the switched current and the stored charge behind ts, VCE(sat) at that current, and whether breakdown is modelled at all (in most cards it is not). |
| RF and video | frequency, capacitance, noise | fT against IC and where it peaks, Cob and Cib against voltage, NF. The 1 kHz h-parameters do not matter. |
| Current sources, mirrors and differential pairs | dc, temperature | the Early voltage (output resistance), VBE and its slope with temperature, hFE at the operating current, and the reverse gain. |

### Bipolar transistors

#### Output characteristics, as a curve tracer draws them (`bjt-tracer`)

Group `dc` · analysis `dc` · engines qspice, ngspice, ltspice · symbols IC(VCE), IB.

The family of curves a data sheet opens with and a curve tracer draws on its screen: collector current against collector-emitter voltage, one trace per step of base current, the steps equal. Three things are read at a glance. The knee near the origin, where the transistor comes out of saturation: its position is VCE(sat), its sharpness the collector resistance. The slope of the flat part, which is the Early effect: a trace that keeps climbing means a low output resistance, and the traces extrapolate to meet the voltage axis at −VA. The spacing of the traces, which is the current gain: equal spacing means hFE is constant across the range, traces that bunch at the top mean it falls at high current. In a model the knee needs RC and BR, the slope needs VAF, the spacing IKF and the ISE/NE pair; a card without VAF draws the flat, parallel lines no transistor has.

**Circuit.** Five copies of the transistor, each with a fixed base current of one to five times a step. The step is either one of sixteen universal values (a 1-2-5 series from 1 µA to 100 mA, which spans the steps small-signal and power data sheets use), so that models can be laid over one another, or "auto": a fifth of the base current that gave IC = 10 mA at VCE = 5 V in the hFE sweep, so that the top trace runs near 10 mA whatever the model's gain. Eighty-five copies in all share one sweep: the collector voltage of every copy is swept together from 0 to 10 V in 20 mV steps and each collector current is read through a 0 V source.

Drawing: DUT; swept VCE source 0 to 10 V; base current source at k times the step; ammeter in the collector. Differs from the netlist: the eighty-five copies are drawn as one transistor with a stepped base current.

**Conditions.** {steps: 5, top: {ic: 0.01, vce: 5}, ib_steps: [1e-06, 2e-06, 5e-06, 1e-05, 2e-05, 5e-05, 0.0001, 0.0002, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1], vce_sweep: {from: 0, to: 10, step: 0.02, unit: V}, temp_c: 25}

**The deck (QSPICE), line by line.**

- `VK1 sw ck1 0` — a 0 V source from the swept node to the first copy's collector: reads its IC
- `QK1 ck1 bk1 0 DUT` — the first auto copy; IK1 (not shown) feeds its base one auto step of base current, IK2 to IK5 two to five steps; the universal families are copies QU11 to QU165 fed by IU11 to IU165
- `VSW sw 0 0` — the collector supply of every copy, swept
- `.dc VSW 0 10 0.02` — the sweep: 0 to 10 V in 20 mV steps
- the auto step is a fifth of the base current that gave IC = 10 mA at 5 V in the hFE sweep; the universal steps are a 1-2-5 series from 1 µA to 100 mA

**Extraction.** Each trace is the collector current of one copy, sampled on the grid, which is fine near the knee and coarser along the flat part. The auto step is kept so that a reader can put numbers on that family's spacing; the top auto trace's current at 10 V is kept as a figure. The universal families are published as they come: at a step too small for a power part they sit near zero, at one too large for a small-signal part they run into the rail, which is itself what the chart shows. Nothing else is read here: VA, VCE(sat) and hFE have their own measurements. A model whose hFE sweep never reached 10 mA has no auto family.

**Outputs.**

- `ib_step` (A): the auto step: the base current per trace that puts the top trace near 10 mA at 5 V; trace k carries k times it
- `ic@10V,step5` (A): collector current of the top auto trace at 10 V

Curves: IC, step 1, auto (ic against vce, lin, at IB step = auto); IC, step 2, auto (ic against vce, lin, at IB step = auto); IC, step 3, auto (ic against vce, lin, at IB step = auto); IC, step 4, auto (ic against vce, lin, at IB step = auto); IC, step 5, auto (ic against vce, lin, at IB step = auto); IC, step 1, IB step=1µA (ic against vce, lin, at IB step = 1e-06); IC, step 2, IB step=1µA (ic against vce, lin, at IB step = 1e-06); IC, step 3, IB step=1µA (ic against vce, lin, at IB step = 1e-06); IC, step 4, IB step=1µA (ic against vce, lin, at IB step = 1e-06); IC, step 5, IB step=1µA (ic against vce, lin, at IB step = 1e-06); IC, step 1, IB step=2µA (ic against vce, lin, at IB step = 2e-06); IC, step 2, IB step=2µA (ic against vce, lin, at IB step = 2e-06); IC, step 3, IB step=2µA (ic against vce, lin, at IB step = 2e-06); IC, step 4, IB step=2µA (ic against vce, lin, at IB step = 2e-06); IC, step 5, IB step=2µA (ic against vce, lin, at IB step = 2e-06); IC, step 1, IB step=5µA (ic against vce, lin, at IB step = 5e-06); IC, step 2, IB step=5µA (ic against vce, lin, at IB step = 5e-06); IC, step 3, IB step=5µA (ic against vce, lin, at IB step = 5e-06); IC, step 4, IB step=5µA (ic against vce, lin, at IB step = 5e-06); IC, step 5, IB step=5µA (ic against vce, lin, at IB step = 5e-06); IC, step 1, IB step=10µA (ic against vce, lin, at IB step = 1e-05); IC, step 2, IB step=10µA (ic against vce, lin, at IB step = 1e-05); IC, step 3, IB step=10µA (ic against vce, lin, at IB step = 1e-05); IC, step 4, IB step=10µA (ic against vce, lin, at IB step = 1e-05); IC, step 5, IB step=10µA (ic against vce, lin, at IB step = 1e-05); IC, step 1, IB step=20µA (ic against vce, lin, at IB step = 2e-05); IC, step 2, IB step=20µA (ic against vce, lin, at IB step = 2e-05); IC, step 3, IB step=20µA (ic against vce, lin, at IB step = 2e-05); IC, step 4, IB step=20µA (ic against vce, lin, at IB step = 2e-05); IC, step 5, IB step=20µA (ic against vce, lin, at IB step = 2e-05); IC, step 1, IB step=50µA (ic against vce, lin, at IB step = 5e-05); IC, step 2, IB step=50µA (ic against vce, lin, at IB step = 5e-05); IC, step 3, IB step=50µA (ic against vce, lin, at IB step = 5e-05); IC, step 4, IB step=50µA (ic against vce, lin, at IB step = 5e-05); IC, step 5, IB step=50µA (ic against vce, lin, at IB step = 5e-05); IC, step 1, IB step=100µA (ic against vce, lin, at IB step = 0.0001); IC, step 2, IB step=100µA (ic against vce, lin, at IB step = 0.0001); IC, step 3, IB step=100µA (ic against vce, lin, at IB step = 0.0001); IC, step 4, IB step=100µA (ic against vce, lin, at IB step = 0.0001); IC, step 5, IB step=100µA (ic against vce, lin, at IB step = 0.0001); IC, step 1, IB step=200µA (ic against vce, lin, at IB step = 0.0002); IC, step 2, IB step=200µA (ic against vce, lin, at IB step = 0.0002); IC, step 3, IB step=200µA (ic against vce, lin, at IB step = 0.0002); IC, step 4, IB step=200µA (ic against vce, lin, at IB step = 0.0002); IC, step 5, IB step=200µA (ic against vce, lin, at IB step = 0.0002); IC, step 1, IB step=500µA (ic against vce, lin, at IB step = 0.0005); IC, step 2, IB step=500µA (ic against vce, lin, at IB step = 0.0005); IC, step 3, IB step=500µA (ic against vce, lin, at IB step = 0.0005); IC, step 4, IB step=500µA (ic against vce, lin, at IB step = 0.0005); IC, step 5, IB step=500µA (ic against vce, lin, at IB step = 0.0005); IC, step 1, IB step=1mA (ic against vce, lin, at IB step = 0.001); IC, step 2, IB step=1mA (ic against vce, lin, at IB step = 0.001); IC, step 3, IB step=1mA (ic against vce, lin, at IB step = 0.001); IC, step 4, IB step=1mA (ic against vce, lin, at IB step = 0.001); IC, step 5, IB step=1mA (ic against vce, lin, at IB step = 0.001); IC, step 1, IB step=2mA (ic against vce, lin, at IB step = 0.002); IC, step 2, IB step=2mA (ic against vce, lin, at IB step = 0.002); IC, step 3, IB step=2mA (ic against vce, lin, at IB step = 0.002); IC, step 4, IB step=2mA (ic against vce, lin, at IB step = 0.002); IC, step 5, IB step=2mA (ic against vce, lin, at IB step = 0.002); IC, step 1, IB step=5mA (ic against vce, lin, at IB step = 0.005); IC, step 2, IB step=5mA (ic against vce, lin, at IB step = 0.005); IC, step 3, IB step=5mA (ic against vce, lin, at IB step = 0.005); IC, step 4, IB step=5mA (ic against vce, lin, at IB step = 0.005); IC, step 5, IB step=5mA (ic against vce, lin, at IB step = 0.005); IC, step 1, IB step=10mA (ic against vce, lin, at IB step = 0.01); IC, step 2, IB step=10mA (ic against vce, lin, at IB step = 0.01); IC, step 3, IB step=10mA (ic against vce, lin, at IB step = 0.01); IC, step 4, IB step=10mA (ic against vce, lin, at IB step = 0.01); IC, step 5, IB step=10mA (ic against vce, lin, at IB step = 0.01); IC, step 1, IB step=20mA (ic against vce, lin, at IB step = 0.02); IC, step 2, IB step=20mA (ic against vce, lin, at IB step = 0.02); IC, step 3, IB step=20mA (ic against vce, lin, at IB step = 0.02); IC, step 4, IB step=20mA (ic against vce, lin, at IB step = 0.02); IC, step 5, IB step=20mA (ic against vce, lin, at IB step = 0.02); IC, step 1, IB step=50mA (ic against vce, lin, at IB step = 0.05); IC, step 2, IB step=50mA (ic against vce, lin, at IB step = 0.05); IC, step 3, IB step=50mA (ic against vce, lin, at IB step = 0.05); IC, step 4, IB step=50mA (ic against vce, lin, at IB step = 0.05); IC, step 5, IB step=50mA (ic against vce, lin, at IB step = 0.05); IC, step 1, IB step=100mA (ic against vce, lin, at IB step = 0.1); IC, step 2, IB step=100mA (ic against vce, lin, at IB step = 0.1); IC, step 3, IB step=100mA (ic against vce, lin, at IB step = 0.1); IC, step 4, IB step=100mA (ic against vce, lin, at IB step = 0.1); IC, step 5, IB step=100mA (ic against vce, lin, at IB step = 0.1). Drawn together, as a family: IB = k × step, k = 1 to 5. Shown first: IB step = auto.

Beside the point under the cursor: P (W), power dissipated in the transistor, VCE × IC; hFE, the DC gain at that point, IC over the trace's base current; ro (Ω), output resistance, the local slope of the trace.

**Card parameters that drive it:** VAF, RC, BR, IKF, ISE, NE, BF.

**A high value.** Traces that climb steeply along the flat part are a low Early voltage; a knee that reaches far to the right is a large collector resistance or a low reverse gain.

**A low value.** Flat, parallel, equally spaced traces are a card with no VAF and a constant hFE: tidy, and unlike any transistor.

**What it cannot tell.** The thermal droop a real tracer shows at high power (the model has no self-heating), and breakdown, which a plain Gummel-Poon card never reaches.

**Standard.** resembles the output characteristics every data sheet prints and a curve tracer draws; no test method

#### Does the card load? (`bjt-runs`)

Group `dc` · analysis `op` · engines qspice, ngspice, ltspice.

The first fact about a model: whether each simulator reads the card at all and finds one operating point. A card can fail for three different reasons, and the result says which: the text is not the dialect this simulator speaks (a parameter name it does not know, a unit it misreads), the solver cannot converge on it, or it took longer than the bench allows. A card that loads in one simulator and not in another is a dialect fact about the card, not a flaw in the simulator.

**Circuit.** The transistor with its emitter grounded, a 5 V source on the collector and a 10 µA current source into the base: the simplest common-emitter bias. The collector current and the base-emitter voltage at that point are read and published, because they are the quickest sanity check of a model (a small-signal silicon transistor shows about 1 mA and about 0.65 V).

Drawing: DUT; VCE source 5 V; base current source 10 µA; ammeter in the collector; voltmeter base to emitter.

**Conditions.** {vce: 5, ib: 1e-05, temp_c: 25}

**The deck (QSPICE), line by line.**

- `VH1 ch1 0 5` — the operating point is read on the hFE copy held at 5 V, at the step where the dial is -5: IB = 10 µA that copy's collector supply
- `BH1 0 bh1 I=exp(2.302585092994046*V(x))` — its base drive: a current source worth 10 to the power of the dial V(x), in amperes
- `QH1 ch1 bh1 0 DUT` — the transistor, emitter grounded
- `VX x 0 0` — the dial: a node whose voltage is the decade of the drive; nothing else reads it
- `.dc VX -9 0 0.05` — the sweep: the dial from -9 to 0 in steps of 0.05, so the drive runs 1 nA to 1 A at twenty points per decade
- `.options reltol=1e-4` — the solver's relative tolerance, tighter than the default

**Extraction.** The simulator's exit status and its log: a syntax message, a convergence message or a timeout become the error class. When it runs, IC and VBE at the operating point.

**Outputs.**

- `runs`: true when the simulator returned a solution
- `error_class`: syntax, convergence, timeout or empty when it ran
- `ic_op` (A): collector current at IB = 10 µA, VCE = 5 V
- `vbe_op` (V): base-emitter voltage at the same point

**What it cannot tell.** That the model is right: QSPICE in particular accepts cards with broken syntax and simulates something. "Runs" in one engine alone is weak evidence; agreement between engines is the stronger fact.

**Standard.** none

#### The Gummel plot — IC and IB against VBE at VCB = 0 (`bjt-gummel`)

Group `dc` · analysis `dc` · engines qspice, ngspice, ltspice · symbols IS, n, hFE.

The textbook picture of a bipolar transistor, and the plot its models are fitted on. Both the collector current and the base current rise exponentially with the base-emitter voltage, so on a logarithmic current axis they are two straight lines. The vertical distance between them is the current gain hFE. The slope of the collector line is set by physics (about 60 mV per decade at 25 °C), and how close the model keeps to it is the ideality factor n; its intercept is the saturation current IS, the number that decides VBE for a given current. The two lines are not straight for ever: at low currents the base line bends up (recombination in the emitter junction, which costs gain), and at high currents the collector line bends over (high injection and series resistance, which costs gain again). Where those bends sit is what separates a model fitted to measurements from one written from the headline numbers.

**Circuit.** The base node is fed by a current source that walks a decade every twenty points from 1 nA to 1 A. The collector is tied to the base through a 0 V source, so the collector-base voltage is zero and VCE equals VBE at every point — the condition the plot is defined at. The emitter is grounded. The source feeds base and collector together: the collector current is read through the 0 V source, the base current is what the source gives less that, and VBE is read at the base.

Drawing: DUT; base current source swept 1 nA to 1 A; 0 V source collector to base (ammeter); voltmeter base to emitter. Differs from the netlist: the base source is a behavioural source IB = 10^V(x) swept through V(x); it is drawn as a plain current source.

**Conditions.** {ib_sweep: {from: 1e-09, to: 1, per_decade: 20, unit: A}, vcb: 0, temp_c: 25}

**The deck (QSPICE), line by line.**

- `VX x 0 0` — the dial: a node whose voltage is the decade of the drive; nothing else reads it
- `BG 0 bg I=exp(2.302585092994046*V(x))` — the drive: 10 to the power of the dial, in amperes, into the base node, from which base and collector draw
- `VG cg bg 0` — a 0 V source from collector to base: VCB = 0, and the current through it is IC
- `QG cg bg 0 DUT` — the transistor, emitter grounded
- `.dc VX -9 0 0.05` — the sweep: the dial from -9 to 0 in steps of 0.05, 1 nA to 1 A at twenty points per decade
- read: IC through VG, IB as the drive less IC, VBE as the voltage of the base node

**Extraction.** Over the straight part of the collector line (IC between 10 µA and 1 mA, or the widest window that stays within 2 % of a straight fit) the slope in mV per decade gives n = slope / 59.2 mV, and the intercept gives IS. hFE is IC/IB at each point; its peak and the current at the peak are kept. The low-current ratio is hFE at 1 µA over the peak; the high-injection knee is the collector current at which hFE has fallen to half its peak on the high side, or "n/a" when it never does within the sweep. The two curves are the classic plot: IC and IB against VBE, on a 20 mV grid and a log scale, so that an ideal junction climbs 59 mV per decade and the gap between the lines is hFE.

**Outputs.**

- `is_fit` (A): saturation current from the intercept of the collector line
- `n_fit`: ideality factor from the slope of the collector line
- `fit_window` (A): the two collector currents the fit was taken between
- `hfe_peak`: the highest IC/IB along the sweep
- `ic_at_hfe_peak` (A): collector current at that peak
- `hfe_low_ratio`: hFE at IC = 1 µA divided by the peak
- `ikf_knee` (A): collector current where hFE is half its peak on the high side

Curves: IC (ic against vbe, log); IB (ib against vbe, log). Drawn together, as a family: IC (upper line) and IB (lower line) against VBE at VCB = 0.

Beside the point under the cursor: gm (S), transconductance, the local slope dIC/dVBE.

**Card parameters that drive it:** IS, NF, BF, ISE, NE, IKF, NK, RB, RE.

**A high value.** A high n (above 1.1) says the model's VBE moves more than physics per decade of current, which shows up as a wrong VBE at currents far from where it was fitted. A high hFE peak with a flat low side (ratio near 1) says no recombination term: the model keeps its gain at microamps, which real small-signal parts do not.

**A low value.** A knee that sits at a few milliamps in a model of a power transistor means IKF was set too low, and the model will understate the gain at the currents the part is used at; a knee that never comes means IKF is absent, and the model will flatter an output stage.

**What it cannot tell.** Anything about the collector voltage: the plot is taken at VCB = 0, so the Early effect is not in it. The hFE of a data sheet, taken at a fixed VCE, is the next measurement.

**Standard.** none — a model-extraction plot (Gummel and Poon, 1970), not a data-sheet test

#### DC current gain hFE and VBE against collector current, at fixed VCE (`bjt-hfe-ic`)

Group `dc` · analysis `dc` · engines qspice, ngspice, ltspice · symbols hFE, VBE(on).

The same current gain, measured the way data sheets print it: the collector held at a fixed voltage and hFE read at a few collector currents. This is where "hFE = 100 to 300 at 10 mA, 1 V" and "VBE(on) = 0.65 V at 1 mA" come from. Three collector voltages are used, because the Early effect makes the gain rise with VCE and the amount it rises is a property of the model. Two numbers derived from the curve matter beyond any single point: where the gain peaks, which says what current the transistor is happiest at, and how flat it is across the decade an amplifier stage uses, which is the first-order source of distortion in a stage without feedback.

**Circuit.** Three copies of the transistor, each with its emitter grounded and its collector held by a voltage source at 1 V, 5 V and 10 V. Each base is fed by the same swept current source as the Gummel plot, 1 nA to 1 A. The collector currents and the base-emitter voltages are read along the sweep; hFE and VBE are then read off the curves at each decade of collector current.

Drawing: DUT; VCE source (1, 2, 4, 5, 6 or 10 V); swept base current source; ammeter in the collector; voltmeter base to emitter. Differs from the netlist: the six VCE copies run in one deck; the drawing shows one, with the voltages listed.

**Conditions.** {ib_sweep: {from: 1e-09, to: 1, per_decade: 20, unit: A}, vce: [1, 5, 10, 2, 4, 6], ic_ladder: [1e-06, 1e-05, 0.0001, 0.001, 0.01, 0.1, 1, 10], temp_c: 25}

**The deck (QSPICE), line by line.**

- `VH0 ch0 0 1` — the collector supply of the first copy: 1 V
- `VH1 ch1 0 5` — of the second: 5 V, the copy the summary values come from
- `VH2 ch2 0 10` — of the third: 10 V
- `BH1 0 bh1 I=exp(2.302585092994046*V(x))` — the base drive of the 5 V copy: 10 to the power of the dial V(x), in amperes; the other copies have their own, reading the same dial
- `QH1 ch1 bh1 0 DUT` — the 5 V copy, emitter grounded
- `VX x 0 0` — the dial: a node whose voltage is the decade of the drive; nothing else reads it
- `.dc VX -9 0 0.05` — the sweep: 1 nA to 1 A at twenty points per decade
- read at each ladder current: hFE = IC / IB, IC being the collector supply's current, and VBE the base voltage

**Extraction.** For each VCE, the base current and VBE at each ladder current are interpolated along the sweep (logarithmically for the currents, linearly in log IC for VBE); hFE is IC over that base current. A value no transistor has (hFE above 10,000, or VBE outside 0.2 to 1.6 V) is marked suspect: it is the behavioural base drive settling on a wrong solution in one engine for cards with a base resistance near zero, and it is kept out of the numbers. A sweep whose collector current stops rising with base current and falls is cut at that peak, because reading the falling branch would mix two base currents for one collector current. When the peak sits at the same current at 5 and 10 V it is the card's own ceiling (NK above 1), published as ic_peak; a peak that moves with VCE is the transistor saturated through its own emitter and collector resistances by a base current no circuit applies, which is physics, and is not published. The peak and the current at the peak come from the 5 V curve; IC is also drawn against VBE, on a VBE grid, the way the "IC against VBE" charts of the sheets put it; the flatness is the largest hFE over the smallest between 100 µA and 10 mA at 5 V; the Early signature is hFE at 1 mA and 10 V over hFE at 1 mA and 1 V.

**Outputs.**

- `hfe@{ic},{vce}`: DC current gain at each ladder current and collector voltage
- `vbe@{ic},{vce}` (V): base-emitter voltage at the same points
- `hfe_peak`: highest hFE on the 5 V curve
- `ic_at_hfe_peak` (A): collector current at that peak
- `hfe_flatness`: max/min of hFE between 100 µA and 10 mA at 5 V
- `hfe_10v_over_1v`: hFE at 1 mA, 10 V over hFE at 1 mA, 1 V (the Early effect)
- `ic_peak` (A): the collector current at which IC stopped rising with base current and fell, at the same current at 5 and 10 V: a ceiling no transistor has (NK > 1 cards); not produced when IC rose to the end of the sweep, or when the peak moves with VCE or shows at one voltage only (the transistor saturated through its own resistances by an absurd drive)

Curves: hFE, VCE=1V (hfe against ic, log, at VCE = 1); hFE, VCE=2V (hfe against ic, log, at VCE = 2); hFE, VCE=4V (hfe against ic, log, at VCE = 4); hFE, VCE=5V (hfe against ic, log, at VCE = 5); hFE, VCE=6V (hfe against ic, log, at VCE = 6); hFE, VCE=10V (hfe against ic, log, at VCE = 10); VBE, VCE=1V (vbe against ic, lin, at VCE = 1); VBE, VCE=2V (vbe against ic, lin, at VCE = 2); VBE, VCE=4V (vbe against ic, lin, at VCE = 4); VBE, VCE=5V (vbe against ic, lin, at VCE = 5); VBE, VCE=6V (vbe against ic, lin, at VCE = 6); VBE, VCE=10V (vbe against ic, lin, at VCE = 10); IC, VCE=1V (ic against vbe, log, at VCE = 1); IC, VCE=2V (ic against vbe, log, at VCE = 2); IC, VCE=4V (ic against vbe, log, at VCE = 4); IC, VCE=5V (ic against vbe, log, at VCE = 5); IC, VCE=6V (ic against vbe, log, at VCE = 6); IC, VCE=10V (ic against vbe, log, at VCE = 10). Shown first: VCE = 5.

Beside the point under the cursor: IB (A), the base current at that point, IC over hFE; P (W), power dissipated in the transistor, VCE × IC; gm (S), transconductance, the local slope dIC/dVBE; P (W), power dissipated in the transistor, VCE × IC; gm (S), transconductance, the local slope dIC/dVBE.

**Card parameters that drive it:** BF, ISE, NE, IKF, NK, VAF, RB, RE, IS, NF.

**A high value.** A high flatness ratio (above 1.5 over two decades) is a gain that moves a lot with signal current: more distortion in an undegenerated stage, and a bias point that drifts with level. A high ratio between 10 V and 1 V means a low Early voltage.

**A low value.** A flatness of exactly 1.00 is a gain that does not move at all, which only a card with neither ISE nor IKF produces; it is a model nobody fitted to a curve. hFE at 1 µA far below the peak is normal for a real part and absent in most cards.

**What it cannot tell.** What the part does: a data sheet gives hFE as a range of production spread (100 to 300), and one model is one point in it. Comparing this number with the sheet is the comparison step, not this one.

**Standard.** resembles MIL-STD-750-3 (forward-current transfer ratio) and IEC 60747-7 static characteristics

#### AC current gain hfe against collector current, at 1 kHz (`bjt-hfe-ac`)

Group `dc` · analysis `ac` · engines qspice, ngspice, ltspice · symbols hfe.

The small-signal current gain: how much the collector current moves for a small wiggle of the base current, hfe = Δic / Δib, taken at 1 kHz where no capacitance matters yet. It is the gain an amplifier stage actually uses, and the one small-signal data sheets print as hfe or h21e. It is not the DC gain of the chart above: hFE is the ratio IC / IB, hfe the slope of IC against IB, so hfe runs above hFE where the gain is still rising with current and below it where the gain falls, and the two meet only where hFE is flat. A model whose DC gain bends shows the bend here, exaggerated.

**Circuit.** The fT deck's copies, read at 1 kHz: one copy per ladder current at VCE = 5 V and at 10 V, each with its DC base current and 1 A of AC on top; the AC collector current is |h21|, which at 1 kHz is hfe.

Drawing: DUT; VCE source 5 V; base bias current source with a small AC signal on top; ammeter in the collector. Differs from the netlist: the deck runs one copy per ladder current; the drawing shows one; the AC drive of 1 A is the simulator's unit signal, not a real amplitude.

**Conditions.** {vce: [5, 10], ic_ladder: [0.0001, 0.001, 0.01, 0.1, 1, 10], f: 1000}

**The deck (QSPICE), line by line.**

- `VCT0 ct0 0 5` — the collector supply of the first copy, 5 V; its current is the collector current, DC and AC
- `QT0 ct0 bt0 0 DUT` — the first copy; IBT0 (not shown) feeds its base the DC current for the ladder step with 1 A of AC on top; one copy per step
- `.ac dec 20 1000 1e+11` — twenty points per decade from 1 kHz to 100 GHz: the fT deck, read here at its first point
- read: hfe = the AC collector current over the 1 A of AC base current, at 1 kHz

**Extraction.** hfe at each ladder current is |h21| at 1 kHz: the AC collector current over the 1 A of AC base current. The ratio of hfe to hFE at 1 mA is kept: 1.0 where the DC gain is flat, above it where the gain rises with current, below it where it falls.

**Outputs.**

- `hfe_ac@{ic},{vce}`: small-signal current gain at 1 kHz, at 5 and at 10 V
- `hfe_ac_over_hfe@1mA`: AC gain over DC gain at 1 mA, 5 V: the slope of hFE against IC

Curves: hfe at 1 kHz, VCE=5V (hfe_ac against ic, log, at VCE = 5); hfe at 1 kHz, VCE=10V (hfe_ac against ic, log, at VCE = 10). Shown first: VCE = 5.

Beside the point under the cursor: P (W), power dissipated in the transistor, VCE × IC.

**Card parameters that drive it:** BF, ISE, NE, IKF, NK, VAF, TF.

**A high value.** An AC gain well above the DC gain at the same current is a gain still climbing steeply with current: the low-current fall (ISE, NE) reaching up to the operating point.

**A low value.** An AC gain well below the DC gain is the high-current fall (IKF) already at work; equal to it, a flat gain. An hfe that collapses at a ladder step before fT does is a card whose collector current has a ceiling.

**What it cannot tell.** The gain at higher frequencies, which is the fT measurement; and any dependence on VCE, since only 5 V is run here.

**Standard.** resembles the small-signal forward current transfer ratio (hfe, h21e) method of MIL-STD-750-3, at 1 kHz

#### Output characteristics, Early voltage and the 1 kHz h-parameters (`bjt-early`)

Group `dc` · analysis `dc` · engines qspice, ngspice, ltspice · symbols VA, hoe, hie, hre, hfe.

The family of curves on the first page of every transistor chapter: collector current against collector voltage at a few fixed base currents. In a real transistor the curves are not flat — the collector current keeps rising slowly with voltage, because a wider collector depletion layer narrows the base. Extrapolated backwards, the curves meet the voltage axis at one point, the Early voltage VA, and VA over IC is the output resistance of the transistor: what limits the gain of a stage with a current-source load and the quality of a current mirror. A card without VAF draws perfectly flat lines, an infinite output resistance that no transistor has, and a simulated cascode or mirror built on it will look better than the real one. The same deck reads the knee where each curve leaves saturation, and a small AC run at 1 mA gives the four h-parameters at 1 kHz that older data sheets print (hie, hre, hfe, hoe).

**Circuit.** Four copies of the transistor, emitters grounded, each with a fixed base current chosen from the previous measurement so that the collector current is about 100 µA, 1 mA, 10 mA and 100 mA at VCE = 5 V. One voltage source sweeps all four collectors from 0 to 30 V. For the h-parameters, two more copies at IB for 1 mA and VCE = 5 V: one driven by a small AC current into the base with the collector held (hie and hfe), one with the base current held and a small AC voltage on the collector (hre and hoe).

Drawing: DUT; fixed base current source; swept VCE source 0 to 30 V; ammeter in the collector; h-parameter copies A (base driven) and B (collector driven), each with a base voltmeter. Differs from the netlist: the four base currents run as four copies in one deck, drawn as one transistor; the h-parameter deck's two copies are the second row of the drawing.

**Conditions.** {vce_sweep: {from: 0, to: 30, step: 0.05, unit: V}, ic_targets: [0.0001, 0.001, 0.01, 0.1], h_parameters: {ic: 0.001, vce: 5, f: 1000}, temp_c: 25}

**The deck (QSPICE), line by line.**

- `VE0 sw ce0 0` — a 0 V source from the swept node to the first copy's collector: reads its IC
- `QE0 ce0 be0 0 DUT` — the first copy; IE0 (not shown, from the hFE sweep) feeds its base the current that gave IC = 100 µA at 5 V; three more copies for 1, 10 and 100 mA
- `VSW sw 0 0` — the collector supply of every copy, swept
- `.dc VSW 0 30 0.05` — the sweep: 0 to 30 V in steps of 50 mV
- `VCA ca 0 5` — the h-parameter deck: copy A biased at 5 V
- `QA ca ba 0 DUT` — copy A, its base fed the DC current for 1 mA plus 1 A of AC (IBA, not shown): hie and hfe
- `VCB cb 0 DC 5 AC 1` — copy B's collector supply, 5 V plus 1 V of AC, the output side driven: hre and hoe
- `.ac dec 10 100 10000` — ten points per decade from 100 Hz to 10 kHz; the four parameters are read at 1 kHz

**Extraction.** For each curve, the slope between 5 and 10 V gives VA = IC/(dIC/dVCE) − VCE taken at 5 V; the output admittance hoe is that slope on the 1 mA curve; the knee is the voltage where IC first reaches 90 % of its value at 5 V. A VA above 10,000 V is reported as "absent" (no Early effect), not as a number. The h-parameters are read from the AC deck at 1 kHz as the existing rows bench does.

**Outputs.**

- `va@{ic}` (V): Early voltage from the slope between 5 and 10 V
- `hoe@1mA,5V` (S): output admittance from the DC slope
- `vce_knee@{ic}` (V): collector voltage where the curve leaves saturation
- `hie@1mA` (Ω): input impedance at 1 kHz, output shorted
- `hre@1mA`: reverse voltage transfer ratio at 1 kHz
- `hoe_ac@1mA` (S): output admittance at 1 kHz

Curves: IC, 100µA (ic against vce, lin, at IC = 0.0001); IC, 1mA (ic against vce, lin, at IC = 0.001); IC, 10mA (ic against vce, lin, at IC = 0.01); IC, 100mA (ic against vce, lin, at IC = 0.1). Shown first: IC = all.

Beside the point under the cursor: P (W), power dissipated in the transistor, VCE × IC; ro (Ω), output resistance, the local slope of the trace.

**Card parameters that drive it:** VAF, VAR, RC, IKF, BF.

**A high value.** A VA of several hundred volts is a stiff current source and a high-gain stage; most small-signal NPNs sit between 50 and 150 V, PNPs lower, and a model far above the part's own figure will overstate voltage gain.

**A low value.** A VA below 20 V is a soft transistor, or a card whose VAF was set from a sheet's hoe at the wrong current. A knee above 1 V at 10 mA says a large collector resistance.

**What it cannot tell.** Breakdown: the sweep stops at 30 V and a plain card has no avalanche anyway (see the breakdown measurement). Nor the reverse Early voltage, which only shows in saturation.

**Standard.** resembles the output admittance (hoe) and h-parameter methods of MIL-STD-750-3, read from DC

#### VCE(sat) and VBE(sat) against collector current at forced hFE = 10, 20 and 50 (`bjt-saturation`)

Group `high-current` · analysis `dc` · engines qspice, ngspice, ltspice · symbols VCE(sat), VBE(sat).

How low the collector can be pulled when the transistor is driven hard: the figure that sets the loss of a saturated switch and the clipping floor of an output stage. Data sheets measure it with the base over-driven so that IC/IB = 10 (Toshiba, ST, onsemi), 20 (Nexperia) or 50 (Diodes), and print it at one or two currents; a Darlington uses 250, which is not run here. Two things make up the curve. At low currents VCE(sat) has a floor of a few tens of millivolts set by the reverse gain BR — the transistor in saturation is two forward-biased junctions, and the floor is the difference of their voltages. At high currents the curve rises along a straight line whose slope is the collector resistance RC (plus a share of RE): the ohmic part of the collector that no amount of base drive removes. A card with RC = 0 and a default BR has a VCE(sat) that neither rises with current nor has a realistic floor, and it will understate the loss of a switch and the heat of an output stage at full swing.

**Circuit.** Two matched current sources: one into the base, one into the collector carrying exactly ten times the base current, both walking the same sweep; two more copies carry twenty and fifty times. A diode from the collector to a 30 V source catches the collector of a transistor that cannot sink ten times its base current at that point, so the sweep passes through saturation without the solver failing; a point at which the collector sits at the clamp is reported "not saturated". The collector and base voltages are read along the sweep.

Drawing: DUT; base current source IB; collector current source 10·IB; clamp diode to 30 V; voltmeters collector and base to emitter. Differs from the netlist: the sources are behavioural (IB = 10^V(x)); the copies at 10, 20 and 50 times the base current are drawn as one with n.

**Conditions.** {ib_sweep: {from: 1e-08, to: 1, per_decade: 20, unit: A}, forced_hfe: [10, 20, 50], clamp_v: 30, ic_ladder: [0.0001, 0.001, 0.01, 0.1, 1, 10], temp_c: 25}

**The deck (QSPICE), line by line.**

- `BSB 0 bs I=exp(2.302585092994046*V(x))` — the base drive: 10 to the power of the dial, in amperes
- `BSC 0 cs I=10*exp(2.302585092994046*V(x))` — the collector drive: ten times the base drive, pulled out of the collector (hFE forced to 10)
- `DCL cs cl DCLMP` — a clamp diode from the collector node to 30 V: what the transistor cannot pass goes this way
- `VCL cl 0 30` — the 30 V the clamp holds
- `QS cs bs 0 DUT` — the transistor, emitter grounded
- `.dc VX -9 0 0.05` — the sweep: IB 1 nA to 1 A, IC ten times that
- read: VCE(sat) as the collector voltage, VBE(sat) as the base voltage; a step where the clamp conducts, or where VCE is not below VBE, is not saturated

**Extraction.** VCE(sat) and VBE(sat) interpolated at each ladder current where the transistor was saturated: the collector below the clamp, and VCE below VBE (the collector junction forward-biased); a step where the collector sits higher is the transistor in its active region, unable to pass the forced current, and is left out. The floor is VCE(sat) at 100 µA; the saturation resistance is the slope dVCE(sat)/dIC between 100 mA and 1 A, or between the two highest currents that saturated.

**Outputs.**

- `vcesat@{ic},{ratio}` (V): collector-emitter saturation voltage at each ladder current, at IC/IB = 10, 20 or 50
- `vbesat@{ic},{ratio}` (V): base-emitter voltage at the same points
- `vce_sat_floor` (V): VCE(sat) at 100 µA, IC/IB = 10
- `rce_sat` (Ω): slope of VCE(sat) with IC at high current, IC/IB = 10

Curves: VCE(sat), IC/IB=10 (vcesat against ic, log, at IC/IB = 10); VCE(sat), IC/IB=20 (vcesat against ic, log, at IC/IB = 20); VCE(sat), IC/IB=50 (vcesat against ic, log, at IC/IB = 50); VBE(sat), IC/IB=10 (vbesat against ic, lin, at IC/IB = 10); VBE(sat), IC/IB=20 (vbesat against ic, lin, at IC/IB = 20); VBE(sat), IC/IB=50 (vbesat against ic, lin, at IC/IB = 50). Shown first: IC/IB = 10.

Beside the point under the cursor: P (W), power dissipated in the collector junction, VCE(sat) × IC; IB (A), the base current that forces it, IC over the ratio; IB (A), the base current that forces it, IC over the ratio.

**Card parameters that drive it:** BR, NR, RC, RE, IKF, IKR, VAR.

**A high value.** A saturation resistance of an ohm or more in a small-signal part is plausible; in a model of a 10 A power transistor it means the model cannot be driven into a realistic VCE(sat) at rated current, and a simulated switch built on it dissipates far too much. A floor above 100 mV says a very small BR.

**A low value.** A slope of zero (the curve flat to 10 A) means RC is absent. A floor near zero means a default BR that nobody set: the model has not been fitted in saturation.

**What it cannot tell.** Quasi-saturation, the soft region between active and hard saturation that power transistors show: the plain Gummel-Poon model has no term for it (PSpice and LTspice carry an extension that only some cards use).

**Standard.** resembles MIL-STD-750-3 saturation voltage methods; IC/IB = 10 is the usual data-sheet condition

#### The saturation region — VCE against base current at fixed collector current (`bjt-vce-ib`)

Group `high-current` · analysis `dc` · engines qspice, ngspice, ltspice · symbols VCE(IB).

The chart one maker prints under "collector saturation region": the collector voltage against the base current while the collector current is held fixed. Read from right to left it is the story of a switch turning on: with little base drive the transistor cannot pass the current and the collector sits high; as the base current rises past IC over hFE the collector voltage collapses, first steeply, then along the slow tail of hard saturation that the reverse gain and the collector resistance set. It tells the designer how much base current a switch needs for a given collector current, and how much more buys how little. A card without a fitted BR and RC shows the collapse but not the tail, and a card whose hFE is wrong puts the knee at the wrong base current.

**Circuit.** One copy per collector current, 1 mA to 10 A: a current source pulls the collector current through the transistor from a 30 V rail by way of a clamp diode, so that a transistor unable to pass it has its collector caught at 30 V rather than the solver failing; the base is driven by the log sweep of base current. The collector voltage is read along the sweep; the points at which the clamp conducts are the transistor still off and are not published.

Drawing: DUT; fixed collector current source with a clamp diode to 30 V; swept base current source; voltmeter collector to emitter. Differs from the netlist: the seven collector currents run as copies in one deck, drawn as one; the base drive is behavioural (IB = 10^V(x)).

**Conditions.** {ic_ladder: [0.001, 0.01, 0.1, 1, 2, 5, 10], ib_sweep: {from: 1e-09, to: 1, per_decade: 20, unit: A}, clamp_v: 30, edge_v: 1, temp_c: 25}

**The deck (QSPICE), line by line.**

- `IV0 0 cv0 0.001` — the collector drive of the first copy: 1 mA pulled out of its collector
- `DCV0 cv0 cl0 DCLMP` — a clamp diode from that collector to 30 V: a transistor that cannot pass the current has its collector caught here
- `VCV0 cl0 0 30` — the 30 V the clamp holds
- `BV0 0 bv0 I=exp(2.302585092994046*V(x))` — the base drive: 10 to the power of the dial, in amperes
- `QV0 cv0 bv0 0 DUT` — the first copy, emitter grounded; the others carry 10 mA, 100 mA and 1 A
- `.dc VX -9 0 0.05` — the sweep: IB 1 nA to 1 A at twenty points per decade
- read: VCE as the collector voltage of each copy, where it sits below the clamp

**Extraction.** VCE on the base-current grid for each collector current, where the collector sat below the clamp. The base current at which VCE first falls to 1 V, the edge of saturation a designer sizes the base drive from, is kept per collector current; a copy whose collector never came off the clamp is "n/a".

**Outputs.**

- `ib_edge@{ic}` (A): the base current at which VCE has fallen to 1 V, the edge of saturation, at each collector current

Curves: VCE, IC=1mA (vce against ib, lin, at IC = 0.001); VCE, IC=10mA (vce against ib, lin, at IC = 0.01); VCE, IC=100mA (vce against ib, lin, at IC = 0.1); VCE, IC=1A (vce against ib, lin, at IC = 1); VCE, IC=2A (vce against ib, lin, at IC = 2); VCE, IC=5A (vce against ib, lin, at IC = 5); VCE, IC=10A (vce against ib, lin, at IC = 10). Shown first: IC = all.

Beside the point under the cursor: P (W), power dissipated in the transistor, VCE × IC; IC/IB, the forced gain at that point.

**Card parameters that drive it:** BF, IKF, BR, RC, RE, RB, NK.

**A high value.** A knee far to the right (a large base current needed for the collector to come down) is a low hFE at that current; a long, slowly falling tail is a large collector resistance.

**A low value.** A collapse that lands at once on a flat floor is a card with no RC and a default BR: it saturates like a switch with no ohmic part, which no transistor does.

**What it cannot tell.** Quasi-saturation, which the plain Gummel-Poon model does not have, and the thermal droop at high power, since the junction is held at 25 °C.

**Standard.** resembles the saturation region chart of onsemi data sheets; no test method

#### On voltages — VBE(sat), VBE(on) and VCE(sat) against collector current (`bjt-on-voltages`)

Group `dc` · analysis `derived` · engines qspice, ngspice, ltspice · symbols VBE(sat), VBE(on), VCE(sat).

The figure onsemi prints as "On voltages": the three voltages of a transistor that is on, against collector current, on one chart. VBE(on) is the base-emitter voltage in the active region (VCE = 5 V); VBE(sat) the same with the base over-driven (IC/IB = 10), a little higher because the base carries more current; VCE(sat) the collector-emitter voltage then. Together they show how much the base must be driven past the active region to saturate, and what the switch is left with.

**Circuit.** No circuit of its own: the curves are those of the hFE sweep at 5 V and of the forced-ratio saturation sweep at IC/IB = 10, laid on one chart.

**Conditions.** {from: [bjt-hfe-ic, bjt-saturation], vce: 5, forced_hfe: 10}

**Extraction.** The VBE curve of the hFE measurement at 5 V and the VBE(sat) and VCE(sat) curves of the saturation measurement at IC/IB = 10, on the saturation measurement's grid. The rise is VBE(sat) less VBE(on) at 1 mA.

**Outputs.**

- `vbe_sat_rise@1mA` (V): VBE(sat) at IC/IB = 10 less VBE(on) at 5 V, at 1 mA: the extra base voltage saturation takes

Curves: VBE(sat), IC/IB=10 (von against ic, lin); VBE(on), VCE=5V (von against ic, lin); VCE(sat), IC/IB=10 (von against ic, lin). Drawn together, as a family: VBE(sat) and VCE(sat) at IC/IB = 10; VBE(on) at VCE = 5 V.

**Card parameters that drive it:** IS, NF, BR, NR, RB, RE, RC, IKF.

**A high value.** A VBE(sat) far above VBE(on) at high current is a large base resistance: the base drive is lost in RB.

**A low value.** A VCE(sat) that crosses below zero at low current is a card with NR above NF: not a transistor's behaviour.

**What it cannot tell.** The sheet's own conditions where they differ (VBE(on) at 1 V, or at IC/IB = 20); those are in the hFE and saturation measurements.

**Standard.** resembles the "On voltages" chart of onsemi data sheets; no test method

#### The transistor used backwards — reverse current gain (`bjt-reverse`)

Group `dc` · analysis `dc` · engines qspice, ngspice, ltspice · symbols hFE(reverse), BR.

Emitter and collector exchanged. The reverse gain of a real transistor is small, one to ten, because the collector was not built to emit. It matters more than it seems: it decides the floor of VCE(sat), it decides how fast stored charge clears when a switch turns off, and it is what an over-driven input stage runs on when the signal reverses the collector junction. It is also the clearest sign of an unfitted card: a BR left at its default of 1 appears in thousands of library models.

**Circuit.** The transistor connected as in the hFE measurement, but with the emitter and the collector swapped: the emitter terminal is held at 1 V and the collector terminal grounded, the base fed by the swept current source. The current into the emitter terminal over the base current is the reverse gain.

Drawing: DUT drawn upside down; 1 V source on the emitter terminal; swept base current source; ammeter in the emitter lead.

**Conditions.** {ib_sweep: {from: 1e-08, to: 0.1, per_decade: 20, unit: A}, vec: 1, ic_ladder: [0.001], temp_c: 25}

**The deck (QSPICE), line by line.**

- `VR er 0 1` — the emitter held at 1 V
- `BR 0 br I=exp(2.302585092994046*V(x))` — the base drive: 10 to the power of the dial, in amperes
- `QR 0 br er DUT` — the transistor with its collector grounded and its emitter at 1 V: it runs backwards, the emitter acting as collector
- `.dc VX -9 0 0.05` — the sweep: 1 nA to 1 A
- read: the reverse gain as the emitter supply's current over the drive, at 1 mA

**Extraction.** The reverse gain interpolated at 1 mA of (reverse) collector current.

**Outputs.**

- `hfe_reverse@1mA`: reverse current gain at 1 mA, VEC = 1 V

**Card parameters that drive it:** BR, NR, IKR, VAR, ISC, NC.

**A high value.** A reverse gain above 10 is unusual in a real part; in a model it usually means BR was set equal to BF by a template.

**A low value.** Exactly 1.00 is the default nobody changed.

**Standard.** none

#### Cob and Cib against reverse voltage (`bjt-capacitance`)

Group `capacitance` · analysis `ac` · engines qspice, ngspice, ltspice · symbols Cob, Cib.

The two junction capacitances. Cob is the collector-base capacitance with the emitter open, the one data sheets print as "Cob = 4 pF at 10 V, 1 MHz"; in a common-emitter stage it is multiplied by the voltage gain (the Miller effect) and becomes the dominant pole that sets the bandwidth, and in an RF stage it is the feedback that makes the stage unstable. Cib is the emitter-base capacitance with the collector open; it adds to the input capacitance and it is the larger of the two. Both fall as the reverse voltage grows, because the depletion layer widens: on logarithmic axes the fall is a straight line whose slope is the grading coefficient M (one third for a linearly graded junction, one half for an abrupt one). A model whose capacitance does not fall with voltage, or has none, will get every frequency-dependent result wrong — bandwidth, slew, switching times, fT — however good its DC curves are.

**Circuit.** For Cob, a voltage source on the collector with a 1 V alternating component on top of the bias, the base grounded, and the emitter left open through a very large resistor. For Cib, the same with the emitter and the collector exchanged. The current drawn from the alternating source at 1 MHz gives the capacitance, as a capacitance meter reads it. Eight copies at eight bias voltages share one run.

Drawing: DUT; bias source with AC 1 V on the collector (or emitter); base grounded; third terminal open through 1 TΩ; AC ammeter. Differs from the netlist: the eight bias points run as eight copies in one deck; the drawing shows one.

**Conditions.** {v_ladder: [0.1, 0.5, 1, 2, 5, 10, 20, 30], cob_extra: [50, 100, 200, 300], f: 1e+06, ac_sweep: {from: 1000, to: 1e+08, per_decade: 20, unit: Hz}, temp_c: 25}

**The deck (QSPICE), line by line.**

- `VO0 ao0 0 DC 0.1 AC 1` — the Cob copy at 0.1 V: its collector held at the reverse voltage with 1 V of AC on top
- `VBO0 bo0 0 0` — its base grounded
- `REO0 eo0 0 1e9` — its emitter open: 1 GΩ to ground
- `QO0 ao0 bo0 eo0 DUT` — the Cob copy
- `VI0 ai0 0 DC 0.1 AC 1` — the Cib copy at 0.1 V: its emitter held at the reverse voltage with 1 V of AC
- `RCI0 ci0 0 1e9` — its collector open: 1 GΩ to ground
- `QI0 ci0 bi0 ai0 DUT` — the Cib copy, base grounded as above
- `.ac dec 10 100000 10000000` — ten points per decade from 100 kHz to 10 MHz; C = Im(I) / (2πf) is read at 1 MHz
- one such pair per reverse voltage: 0.1, 0.5, 1, 2, 5, 10, 20 and 30 V

**Extraction.** At each bias, the capacitance a meter reads at 1 MHz, the frequency of nearly every data sheet (a few older and power-transistor sheets use 100 kHz): the series-equivalent capacitance of the impedance the source sees, C = |I|² / (2π · 1 MHz · |Im I|), the reading meters use for a capacitance of low impedance. For a junction of picofarads it equals the parallel reading |Im I| / (2π · 1 MHz) to a part in a million; for the nanofarads of a power transistor's emitter junction behind a few ohms of base resistance it is the only reading the resistance does not pull down: the parallel one falls by 1 + (2πf·R·C)², a factor of 4.5 for 81 nF behind 3.7 Ω (catalogues before m-11 published the parallel reading). A card with no capacitance reads zero. Cob is also taken at 50, 100, 200 and 300 V, for high-voltage parts (beyond a part's own VCBO the number is the model's, not a transistor's). The grading coefficient is the slope of log C against log (V + VJ) between 1 and 10 V, with VJ taken as 0.7 V; the ratio C(1 V)/C(10 V) is published as the simpler figure.

**Outputs.**

- `cob@{v}` (F): collector-base capacitance, emitter open, at each ladder voltage
- `cib@{v}` (F): emitter-base capacitance, collector open, at each ladder voltage
- `cob_m`: grading coefficient of Cob between 1 and 10 V
- `cob_1v_over_10v`: Cob at 1 V over Cob at 10 V

Curves: Cob (cob against v, log); Cib (cib against v, log).

**Card parameters that drive it:** CJC, VJC, MJC, XCJC, CJE, VJE, MJE, FC.

**A high value.** A ratio C(1 V)/C(10 V) near 2 is a normal abrupt-ish junction; near 1 the capacitance is constant with voltage, which only happens when MJC is near zero. A Cob of tens of picofarads in a model of a small-signal part will halve its simulated bandwidth.

**A low value.** A Cob of exactly zero is a card without CJC: the model has no Miller capacitance and will show a bandwidth the part does not have. The code "absent" is used rather than the number.

**What it cannot tell.** Where the capacitance sits: a real transistor's Cob is partly inside the base resistance (the card splits it with XCJC), which only shows in the high-frequency response, not in this measurement. Some sheets print Cre (emitter grounded) instead of Cob; the two differ.

**Standard.** resembles the open-circuit output capacitance methods (MIL-STD-750-3, 1 MHz), read as a meter reads a capacitance of low impedance (series equivalent)

#### Transition frequency against collector current (`bjt-ft`)

Group `frequency` · analysis `ac` · engines qspice, ngspice, ltspice · symbols fT.

The frequency at which the common-emitter current gain has fallen to one: the single number that separates an audio transistor (100 to 300 MHz), a video one (around 1 GHz) and an RF one (tens of GHz). It is not a constant of the part. It rises with collector current, because the junction capacitances are charged faster by a larger current, it peaks, and then it falls again when high injection widens the base (the Kirk effect). Every data sheet draws this curve, and a model gets it from three things: the forward transit time TF (the time a carrier takes to cross the base), the two junction capacitances, and the parameters that describe the fall at high current (XTF, ITF, VTF). A card with TF but no capacitances, or capacitances but no TF, has an fT that is right at one current at best.

**Circuit.** The transistor with its emitter grounded, the collector held at 5 V (and a second set of copies at 10 V, the voltage Toshiba, Nexperia and the RF sheets use), the base biased by a current source set from the hFE measurement so that the collector current is one ladder step, with a 1 A alternating current added on top (the magnitude is arbitrary in a linear small-signal analysis). The alternating collector current, read through the collector source, is the current gain |h21| against frequency. Up to eight copies at eight collector currents share one run.

Drawing: DUT; VCE source 5 V; base bias current source with an AC component; AC ammeter in the collector. Differs from the netlist: the ladder currents run as copies in one deck; the drawing shows one.

**Conditions.** {vce: [5, 10], ic_ladder: [0.0001, 0.001, 0.01, 0.1, 1, 10], ac_sweep: {from: 1000, to: 1e+11, per_decade: 20, unit: Hz}, read_at: [1e+06, 2e+07, 1e+08], temp_c: 25}

**The deck (QSPICE), line by line.**

- `VCT0 ct0 0 5` — the collector supply of the first copy, 5 V; its current is the collector current
- `QT0 ct0 bt0 0 DUT` — the first copy; IBT0 (not shown) feeds its base the DC current for the ladder step with 1 A of AC on top; one copy per step
- `.ac dec 20 1000 1e+11` — twenty points per decade from 1 kHz to 100 GHz; the low end serves the AC gain measurement too
- read: |h21| = the AC collector current over the 1 A of AC base current; fT where it crosses 1

**Extraction.** Two readings per current: the frequency at which |h21| crosses 1 (interpolated on log-log axes), and |h21| times frequency taken where |h21| is between 2 and 10 — the way sheets measure it, which is less sensitive to the parasitics above the gain-bandwidth region. The peak and the current at the peak come from the second reading; the roll-off is fT at the highest ladder current reached over the peak. The whole |hfe| curve against frequency is kept at each current, five points per decade, and the beta cut-off is where it has fallen to 1/√2 of its 1 kHz value. fT is also read the way most sheets measure it, |hfe| × f at a fixed 1, 20 or 100 MHz (power parts are measured at 1 MHz, small-signal ones at 20 or 100 MHz). It is the same number where |hfe| falls as 1/f there, so it is given only where that frequency is above the beta cut-off and |hfe| is still 1.5 or more: below the cut-off the product is an underestimate, and near unity the base-collector capacitance feeds the drive straight through and the product means nothing.

**Outputs.**

- `ft@{ic},{vce}` (Hz): fT by extrapolation at each ladder current, at 5 and at 10 V
- `ft_unity@{ic},{vce}` (Hz): the frequency where |h21| = 1
- `ft_peak` (Hz): highest fT along the ladder at 5 V
- `ic_at_ft_peak` (A): collector current at that peak
- `ft_rolloff`: fT at the top current over the peak, at 5 V (1.0 = no fall)
- `f_beta@{ic},{vce}` (Hz): the beta cut-off: the frequency at which |hfe| has fallen to 1/√2 of its 1 kHz value
- `ft_at@{ic},{vce},{f}` (Hz): |hfe| × f at 1, 20 and 100 MHz, fT the way sheets measure it; given only where that frequency is above the beta cut-off and |hfe| there is 1.5 or more

Curves: fT, VCE=5V (ft against ic, log, at VCE = 5, f = extrapolated); fT, VCE=10V (ft against ic, log, at VCE = 10, f = extrapolated); fT at 1MHz, VCE=5V (ft against ic, log, at VCE = 5, f = 1e+06); fT at 20MHz, VCE=5V (ft against ic, log, at VCE = 5, f = 2e+07); fT at 100MHz, VCE=5V (ft against ic, log, at VCE = 5, f = 1e+08); fT at 1MHz, VCE=10V (ft against ic, log, at VCE = 10, f = 1e+06); fT at 20MHz, VCE=10V (ft against ic, log, at VCE = 10, f = 2e+07); fT at 100MHz, VCE=10V (ft against ic, log, at VCE = 10, f = 1e+08); |hfe|, 100µA, VCE=5V (h21 against f, log, at IC = 0.0001, VCE = 5); |hfe|, 1mA, VCE=5V (h21 against f, log, at IC = 0.001, VCE = 5); |hfe|, 10mA, VCE=5V (h21 against f, log, at IC = 0.01, VCE = 5); |hfe|, 100mA, VCE=5V (h21 against f, log, at IC = 0.1, VCE = 5); |hfe|, 1A, VCE=5V (h21 against f, log, at IC = 1, VCE = 5); |hfe|, 10A, VCE=5V (h21 against f, log, at IC = 10, VCE = 5); |hfe|, 100µA, VCE=10V (h21 against f, log, at IC = 0.0001, VCE = 10); |hfe|, 1mA, VCE=10V (h21 against f, log, at IC = 0.001, VCE = 10); |hfe|, 10mA, VCE=10V (h21 against f, log, at IC = 0.01, VCE = 10); |hfe|, 100mA, VCE=10V (h21 against f, log, at IC = 0.1, VCE = 10); |hfe|, 1A, VCE=10V (h21 against f, log, at IC = 1, VCE = 10); |hfe|, 10A, VCE=10V (h21 against f, log, at IC = 10, VCE = 10). Shown first: IC = 0.001, VCE = 5, f = extrapolated.

Beside the point under the cursor: P (W), power dissipated in the transistor, VCE × IC; f·|hfe| (Hz), the gain-bandwidth product; it equals fT where |hfe| falls as 1/f.

**Card parameters that drive it:** TF, XTF, VTF, ITF, PTF, CJE, CJC, RB, RE, RC.

**A high value.** An fT far above the part's family (a gigahertz in a model of an audio transistor) usually means a TF copied from another card or set to zero; its simulated stages will be too fast and may oscillate where the real circuit does not.

**What it cannot tell.** The curve at the sheet's own VCE when that is 20 V; fT also rises slowly with VCE. A card whose fT never falls at high current (roll-off 1.0) is missing XTF and ITF, which only the capability layer can say for sure. With no TF and no capacitances the gain never falls and the code is "absent".

**Standard.** resembles the small-signal current gain at frequency method (fT by extrapolation, MIL-STD-750-3)

#### td, tr, ts and tf in a resistive-load switch (`bjt-switching`)

Group `switching` · analysis `tran` · engines qspice, ngspice, ltspice · symbols td, tr, ts, tf.

The four times of a switching data sheet: the delay before the collector current starts, the rise to 90 %, the storage time before it starts to fall after the base is driven off, and the fall. The storage time is the one that matters and the one most models get wrong: a saturated transistor holds excess charge in its base, and the switch cannot turn off until that charge has been pulled out by the reverse base drive. In a model, that charge is the reverse transit time TR times the current; a card with TR = 0 turns off instantly, which no bipolar switch does. Fixtures scaled to ten currents from 10 mA to 10 A (a 1-2-5 series) are run from a 10 V and from a 30 V supply (the voltage most switching sheets use), because a model fitted at one current can be far off at another, and so that the four times can be drawn against current as the sheets draw them.

**Circuit.** A 10 V or 30 V supply through a load resistor chosen so that the switched current is the step (RL = VCC / IC), the collector current read through a 0 V source. The base is driven from a voltage pulse through a base resistor RB = 100 V / IC: a pulse from −9.3 V to +10.7 V then gives a forward base current and a reverse base current both equal to one tenth of the collector current past a 0.7 V base-emitter drop, as the 2N2222A fixture does. Edges of 2 ns, and three pulse lengths, because data sheets use pulses from microseconds to hundreds of microseconds (10 µs for the PN2222A, 10 to 500 µs for the 2N3904's storage time, 100 to 500 µs for the TIP31C) and a slow model, or a power transistor whose stored charge takes long to build, may not have switched on, or not fully, by the end of a short one: 3 µs on with 5 µs watched after the turn-off edge, 10 µs with 5 µs, and 100 µs with 50 µs, the largest time step growing with the pulse (0.25, 1 and 10 ns) so that a long pulse costs about what a short one does. Each waveform is published as 80 time and current pairs placed where it bends, the time at five significant figures, so that an edge of a few nanoseconds can still be read at 3 µs; the four times are also drawn against the switched current.

Drawing: DUT; supply 10 V; load resistor RL = 10 V / IC; pulse source; base resistor RB; probe on the collector.

**Conditions.** {vcc: [10, 30], ic_ladder: [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10], waveforms: [0.01, 0.1, 1, 10], forced_hfe: 10, rb_times_ic: 100, v_on: 10.7, v_off: -9.3, t_start_s: 1e-07, edge_s: 2e-09, pulses: [{t_on_s: 3e-06, t_after_s: 5e-06, max_step_s: 2.5e-10}, {t_on_s: 1e-05, t_after_s: 5e-06, max_step_s: 1e-09}, {t_on_s: 0.0001, t_after_s: 5e-05, max_step_s: 1e-08}], curve_points: 80, temp_c: 25}

**The deck (QSPICE), line by line.**

- `VCC vcc 0 10` — the supply, 10 V
- `RL vcc cs 100` — the load: 10 V over the switched current (100 Ω in the 100 mA deck)
- `VS cs c 0` — a 0 V source in the collector: reads IC
- `VIN in 0 PWL(0 -9.3 1e-07 -9.3 1.02e-07 10.7 3.102e-06 10.7 3.104e-06 -9.3)` — the drive: -9.3 V until 100 ns, up to 10.7 V in 2 ns, back down at 3.1 µs
- `RB in b 1000` — the base resistor: 100 V over the switched current, so that the drive gives IB = IC/10 on and off past a 0.7 V VBE
- `Q1 c b 0 DUT` — the transistor, emitter grounded
- `.tran 2.5e-10 8.104e-06 0 2.5e-10` — steps of at most 0.25 ns, to 8.1 µs
- one deck per switched current (10 mA to 10 A), supply (10 and 30 V) and pulse (3, 10 and 100 µs) scales VCC, RL and RB, and the pulse its step; td, tr, ts and tf are read from the 10 % and 90 % crossings of IC

**Extraction.** The 10 % and 90 % crossings of the collector current, measured from the 10 % points of the input edges: td from the input's rise to IC at 10 %; tr from 10 % to 90 %; ts from the input's fall to IC back at 90 %; tf from 90 % to 10 %. The stored charge is ts times the reverse base current. The collector current at the end of the pulse (the mean of its last fifth) is published over the switched current, at every step: below 0.9 the step did not switch, its times are left out, and the number says how far it got.

**Outputs.**

- `td@{ic},{vcc},{pulse}` (s): delay time at each switched current, supply and pulse length
- `tr@{ic},{vcc},{pulse}` (s): rise time
- `ts@{ic},{vcc},{pulse}` (s): storage time
- `tf@{ic},{vcc},{pulse}` (s): fall time
- `qs@{ic},{vcc},{pulse}` (C): stored charge, ts times the reverse base current
- `on@{ic},{vcc},{pulse}`: the collector current at the end of the pulse over the switched current: below 0.9 the step did not switch

Curves: IC(t), 10mA (ic against t, lin, at IC = 0.01, VCC = 10, pulse = 3e-06); IC(t), 100mA (ic against t, lin, at IC = 0.1, VCC = 10, pulse = 3e-06); IC(t), 1A (ic against t, lin, at IC = 1, VCC = 10, pulse = 3e-06); IC(t), 10A (ic against t, lin, at IC = 10, VCC = 10, pulse = 3e-06); IC(t), 10mA, VCC=30V (ic against t, lin, at IC = 0.01, VCC = 30, pulse = 3e-06); IC(t), 100mA, VCC=30V (ic against t, lin, at IC = 0.1, VCC = 30, pulse = 3e-06); IC(t), 1A, VCC=30V (ic against t, lin, at IC = 1, VCC = 30, pulse = 3e-06); IC(t), 10A, VCC=30V (ic against t, lin, at IC = 10, VCC = 30, pulse = 3e-06); IC(t), 10mA, 10µs (ic against t, lin, at IC = 0.01, VCC = 10, pulse = 1e-05); IC(t), 100mA, 10µs (ic against t, lin, at IC = 0.1, VCC = 10, pulse = 1e-05); IC(t), 1A, 10µs (ic against t, lin, at IC = 1, VCC = 10, pulse = 1e-05); IC(t), 10A, 10µs (ic against t, lin, at IC = 10, VCC = 10, pulse = 1e-05); IC(t), 10mA, VCC=30V, 10µs (ic against t, lin, at IC = 0.01, VCC = 30, pulse = 1e-05); IC(t), 100mA, VCC=30V, 10µs (ic against t, lin, at IC = 0.1, VCC = 30, pulse = 1e-05); IC(t), 1A, VCC=30V, 10µs (ic against t, lin, at IC = 1, VCC = 30, pulse = 1e-05); IC(t), 10A, VCC=30V, 10µs (ic against t, lin, at IC = 10, VCC = 30, pulse = 1e-05); IC(t), 10mA, 100µs (ic against t, lin, at IC = 0.01, VCC = 10, pulse = 0.0001); IC(t), 100mA, 100µs (ic against t, lin, at IC = 0.1, VCC = 10, pulse = 0.0001); IC(t), 1A, 100µs (ic against t, lin, at IC = 1, VCC = 10, pulse = 0.0001); IC(t), 10A, 100µs (ic against t, lin, at IC = 10, VCC = 10, pulse = 0.0001); IC(t), 10mA, VCC=30V, 100µs (ic against t, lin, at IC = 0.01, VCC = 30, pulse = 0.0001); IC(t), 100mA, VCC=30V, 100µs (ic against t, lin, at IC = 0.1, VCC = 30, pulse = 0.0001); IC(t), 1A, VCC=30V, 100µs (ic against t, lin, at IC = 1, VCC = 30, pulse = 0.0001); IC(t), 10A, VCC=30V, 100µs (ic against t, lin, at IC = 10, VCC = 30, pulse = 0.0001); td (td against ic, log, at VCC = 10, pulse = 3e-06); td, VCC=30V (td against ic, log, at VCC = 30, pulse = 3e-06); td, 10µs (td against ic, log, at VCC = 10, pulse = 1e-05); td, VCC=30V, 10µs (td against ic, log, at VCC = 30, pulse = 1e-05); td, 100µs (td against ic, log, at VCC = 10, pulse = 0.0001); td, VCC=30V, 100µs (td against ic, log, at VCC = 30, pulse = 0.0001); tr (tr against ic, log, at VCC = 10, pulse = 3e-06); tr, VCC=30V (tr against ic, log, at VCC = 30, pulse = 3e-06); tr, 10µs (tr against ic, log, at VCC = 10, pulse = 1e-05); tr, VCC=30V, 10µs (tr against ic, log, at VCC = 30, pulse = 1e-05); tr, 100µs (tr against ic, log, at VCC = 10, pulse = 0.0001); tr, VCC=30V, 100µs (tr against ic, log, at VCC = 30, pulse = 0.0001); ts (ts against ic, log, at VCC = 10, pulse = 3e-06); ts, VCC=30V (ts against ic, log, at VCC = 30, pulse = 3e-06); ts, 10µs (ts against ic, log, at VCC = 10, pulse = 1e-05); ts, VCC=30V, 10µs (ts against ic, log, at VCC = 30, pulse = 1e-05); ts, 100µs (ts against ic, log, at VCC = 10, pulse = 0.0001); ts, VCC=30V, 100µs (ts against ic, log, at VCC = 30, pulse = 0.0001); tf (tf against ic, log, at VCC = 10, pulse = 3e-06); tf, VCC=30V (tf against ic, log, at VCC = 30, pulse = 3e-06); tf, 10µs (tf against ic, log, at VCC = 10, pulse = 1e-05); tf, VCC=30V, 10µs (tf against ic, log, at VCC = 30, pulse = 1e-05); tf, 100µs (tf against ic, log, at VCC = 10, pulse = 0.0001); tf, VCC=30V, 100µs (tf against ic, log, at VCC = 30, pulse = 0.0001). Shown first: IC = 0.1, VCC = 10, pulse = 3e-06.

**Card parameters that drive it:** TF, TR, CJE, CJC, RB, BF, BR, IKF.

**A high value.** A storage time of microseconds at 100 mA is a slow switching transistor or a TR set for a power part; in a model of a 2N2369-class part it is wrong by two orders.

**A low value.** A storage time near zero at every current is a card without TR: the model switches off with no stored charge. The code "absent" is used.

**What it cannot tell.** The times with a speed-up capacitor, with an inductive load or with the sheet's own fixture values, all of which change them; the rows bench runs the sheet's own fixture when the sheet draws it. Transients also differ by up to 1 % between simulators because each chooses its own time steps.

**Standard.** resembles MIL-STD-750-3 pulse response and the JEDEC/MIL fixture of 2N2222A-type sheets, simplified

#### Voltage noise, current noise, the 1/f corner and NF (`bjt-noise`)

Group `noise` · analysis `noise` · engines qspice, ngspice · symbols en, in, NF.

The transistor's own noise, referred to its base so that it can be compared with the signal and the source. It has a voltage part — the shot noise of the collector current seen through the transistor's own 1/gm, plus the thermal noise of the base spreading resistance rbb' — and a current part, the shot noise of the base current. Below a corner frequency both are joined by flicker (1/f) noise, which rises as the frequency falls and sets what a preamplifier does at 10 Hz. Low-noise design is the trade between the two: a low collector current for low current noise, a high one for low voltage noise, with the source resistance deciding which wins. In a card, the voltage floor needs RB (without it the model has only shot noise and is quieter than any real part at high currents), and the 1/f part needs KF and AF: a card with KF = 0 has no flicker noise at all, which is the single most common gap in library models.

**Circuit.** A common-emitter stage at VCE = 5 V, the base biased by a current source for 10, 30, 100 and 300 µA, 1, 3 and 10 mA, the collector currents low-noise sheets draw. The noise input is a voltage source in series with a source resistance RG at the base; the output is taken as the collector current through a sensing source. Two runs per current: RG = 0, which gives the voltage noise alone, and RG = 100 kΩ, from which the current noise is separated. A third run at 1 mA with RG = 1 kΩ gives the noise figure data sheets print.

Drawing: DUT; VCE source 5 V; base bias current source; noise voltage source in series with RG; output sensing in the collector. Differs from the netlist: the output is taken through a current-controlled voltage source into a 1 MΩ load, which is how the simulators report input-referred noise.

**Conditions.** {vce: 5, ic_ladder: [1e-05, 3e-05, 0.0001, 0.0003, 0.001, 0.003, 0.01], rg: [0, 100000], nf: {ic: 0.001, rg: 1000, f: 1000}, band: [10, 15700], f_points: [10, 100, 1000, 10000, 100000], noise_sweep: {from: 1, to: 1e+06, per_decade: 20, unit: Hz}, temp_c: 25}

**The deck (QSPICE), line by line.**

- `VSENSE c cc 0` — a 0 V source in the collector: the sensing element
- `VC cc 0 5` — the collector supply, 5 V
- `Q1 c b 0 DUT` — the transistor, emitter grounded; IB (not shown) feeds its base the DC current for the step, and VIN carries the matching VBE plus the noise input
- `RG in b 0.001` — the source resistance, run 1: 0 Ω (1 mΩ), which gives the voltage noise alone
- `RG in b 100000` — run 2: 100 kΩ, which adds the current noise times 100 kΩ and the resistor's own thermal noise
- `RG in b 1000` — run 3, at 1 mA only: 1 kΩ, the data sheets' noise-figure condition
- `H1 out 0 VSENSE 1000` — the sensed current as a voltage: 1000 V per ampere
- `RLOAD out 0 1meg` — a load for that voltage
- `.noise V(out) VIN dec 20 1 1000000` — the noise analysis: twenty points per decade from 1 Hz to 1 MHz, referred to VIN

**Extraction.** en at each frequency point is the input-referred noise with RG = 0. With RG = 100 kΩ the input noise squared is en² + in²·RG² + 4kT·RG, from which in follows. The corner is the frequency at which en has risen to √2 times its 10 kHz value, "absent" when the spectrum is flat. NF at 1 kHz with RG = 1 kΩ is 10·log10 of the input noise squared over 4kT·RG. The floor ratio is en at 10 mA over en at 100 µA at 10 kHz, which shows whether rbb' depends on current. The curves against source resistance are computed from en and in at 1 kHz, the way low-noise sheets draw them: the total input noise VT = √(en² + in²·RS² + 4kT·RS), and NF = 10·log10(VT² / 4kT·RS); the correlation between en and in is neglected, as those sheets neglect it. The wideband figure integrates the same densities over 10 Hz to 15.7 kHz: NF = 10·log10 of the integral of VT² over that of 4kT·RS, and the total noise voltage is the square root of the integral of VT², in volts.

**Outputs.**

- `en@{f},{ic}` (V/√Hz): input voltage noise density
- `in@{f},{ic}` (A/√Hz): input current noise density
- `en_corner@{ic}` (Hz): frequency where en is √2 times its 10 kHz value
- `nf@1kHz,1mA,1k` (dB): noise figure at 1 kHz, IC = 1 mA, RG = 1 kΩ
- `en_floor_ratio`: en at 10 mA over en at 100 µA, at 10 kHz
- `nf_wide@1mA,1k` (dB): wideband noise figure, 10 Hz to 15.7 kHz, IC = 1 mA, RS = 1 kΩ

Curves: en, 10µA (en against f, log, at IC = 1e-05); en, 30µA (en against f, log, at IC = 3e-05); en, 100µA (en against f, log, at IC = 0.0001); en, 300µA (en against f, log, at IC = 0.0003); en, 1mA (en against f, log, at IC = 0.001); en, 3mA (en against f, log, at IC = 0.003); en, 10mA (en against f, log, at IC = 0.01); in, 10µA (in against f, log, at IC = 1e-05); in, 30µA (in against f, log, at IC = 3e-05); in, 100µA (in against f, log, at IC = 0.0001); in, 300µA (in against f, log, at IC = 0.0003); in, 1mA (in against f, log, at IC = 0.001); in, 3mA (in against f, log, at IC = 0.003); in, 10mA (in against f, log, at IC = 0.01); en at 10Hz (en against ic, log, at f = 10); en at 100Hz (en against ic, log, at f = 100); en at 1kHz (en against ic, log, at f = 1000); en at 10kHz (en against ic, log, at f = 10000); en at 100kHz (en against ic, log, at f = 100000); in at 10Hz (in against ic, log, at f = 10); in at 100Hz (in against ic, log, at f = 100); in at 1kHz (in against ic, log, at f = 1000); in at 10kHz (in against ic, log, at f = 10000); in at 100kHz (in against ic, log, at f = 100000); NF, 10µA (nf against rs, lin, at IC = 1e-05, band = spot 1 kHz); NF, 30µA (nf against rs, lin, at IC = 3e-05, band = spot 1 kHz); NF, 100µA (nf against rs, lin, at IC = 0.0001, band = spot 1 kHz); NF, 300µA (nf against rs, lin, at IC = 0.0003, band = spot 1 kHz); NF, 1mA (nf against rs, lin, at IC = 0.001, band = spot 1 kHz); NF, 3mA (nf against rs, lin, at IC = 0.003, band = spot 1 kHz); NF, 10mA (nf against rs, lin, at IC = 0.01, band = spot 1 kHz); NF wideband, 10µA (nf against rs, lin, at IC = 1e-05, band = 10 Hz to 15.7 kHz); NF wideband, 30µA (nf against rs, lin, at IC = 3e-05, band = 10 Hz to 15.7 kHz); NF wideband, 100µA (nf against rs, lin, at IC = 0.0001, band = 10 Hz to 15.7 kHz); NF wideband, 300µA (nf against rs, lin, at IC = 0.0003, band = 10 Hz to 15.7 kHz); NF wideband, 1mA (nf against rs, lin, at IC = 0.001, band = 10 Hz to 15.7 kHz); NF wideband, 3mA (nf against rs, lin, at IC = 0.003, band = 10 Hz to 15.7 kHz); NF wideband, 10mA (nf against rs, lin, at IC = 0.01, band = 10 Hz to 15.7 kHz); VT, 10µA (vt against rs, log, at IC = 1e-05); VT, 30µA (vt against rs, log, at IC = 3e-05); VT, 100µA (vt against rs, log, at IC = 0.0001); VT, 300µA (vt against rs, log, at IC = 0.0003); VT, 1mA (vt against rs, log, at IC = 0.001); VT, 3mA (vt against rs, log, at IC = 0.003); VT, 10mA (vt against rs, log, at IC = 0.01); VT wideband, 10µA (vt_band against rs, log, at IC = 1e-05); VT wideband, 30µA (vt_band against rs, log, at IC = 3e-05); VT wideband, 100µA (vt_band against rs, log, at IC = 0.0001); VT wideband, 300µA (vt_band against rs, log, at IC = 0.0003); VT wideband, 1mA (vt_band against rs, log, at IC = 0.001); VT wideband, 3mA (vt_band against rs, log, at IC = 0.003); VT wideband, 10mA (vt_band against rs, log, at IC = 0.01). Shown first: IC = 0.001, f = 1000, band = spot 1 kHz.

**Card parameters that drive it:** RB, RBM, IRB, KF, AF, IS, NF, BF.

**A high value.** A corner above 1 kHz is a noisy part or a KF set too high; a voltage noise above 2 nV/√Hz at 10 mA says a large rbb'.

**A low value.** A flat spectrum down to 1 Hz is a card with KF = 0: it says nothing about the part's 1/f noise, and the code is "absent" for the corner. A voltage noise that keeps falling with current without limit is a card with RB = 0.

**What it cannot tell.** Burst (popcorn) noise, which no SPICE model has; the current dependence of the corner in real parts; and what the part does, since noise is the behaviour makers measure least and model least.

**Standard.** resembles the spot noise figure method (MIL-STD-750-3) and the en/in curves of low-noise sheets

#### hFE, VBE and the saturation voltages at −55, 25, 100, 125 and 150 °C (`bjt-temperature`)

Group `temperature` · analysis `dc` · engines qspice, ngspice, ltspice · symbols dVBE/dT, hFE(T).

The two temperature effects every designer meets. The base-emitter voltage falls by about 2 mV for every kelvin of rise, which is the drift of every bias point, the reason output stages need thermal compensation, and the principle of the silicon thermometer. The current gain rises with temperature, typically by half again between 25 and 125 °C. A model carries the first through the temperature laws of IS (EG and XTI), which have defaults, so VBE always moves and only the slope is informative; it carries the second through XTB, which has a default of zero, so a card without XTB has a gain that does not move with temperature at all. Whether a simulation of an output stage runs away or settles depends on exactly these two numbers.

**Circuit.** The hFE deck at VCE = 5 V, with the forced-ratio saturation circuit (IC/IB = 10) alongside, run with the simulator's temperature set to −55, 25, 100, 125 and 150 °C. hFE and VBE are read at 1 mA and at 100 mA at each temperature; the saturation voltages are kept as curves.

Drawing: DUT; VCE source 5 V; swept base current source; ammeter in the collector; voltmeter base to emitter; a thermometer symbol. Differs from the netlist: the temperature is a simulator setting; the saturation copy (IC = 10 IB) that rides in each deck is drawn in the saturation bench.

**Conditions.** {vce: 5, ib_sweep: {from: 1e-09, to: 1, per_decade: 20, unit: A}, temps_c: [-55, 25, 100, 125, 150], ic_points: [0.001, 0.1]}

**The deck (QSPICE), line by line.**

- `.temp -55` — the first deck at -55 °C; the 25 °C point comes from the hFE deck
- `.temp 125` — the second at 125 °C, the third at 150 °C
- `VT ct 0 5` — the collector supply, 5 V
- `BT 0 bt I=exp(2.302585092994046*V(x))` — the base drive: 10 to the power of the dial, in amperes
- `QT ct bt 0 DUT` — the transistor, emitter grounded
- `.dc VX -9 0 0.05` — the sweep: 1 nA to 1 A

**Extraction.** dVBE/dT is the difference of VBE at 1 mA between 150 and −55 °C over 205 K. The gain ratios are hFE at 100, 125 and 150 °C and at −55 °C over hFE at 25 °C, at 1 mA and at 100 mA. A ratio of exactly 1.000 is reported "absent" (no XTB), not as a number. The curves keep hFE, VBE, VCE(sat) and VBE(sat) against IC at each temperature, and the slope of VBE with temperature against IC over each span between neighbouring temperatures, the way one maker prints it.

**Outputs.**

- `dvbe_dt@1mA` (V/K): slope of VBE with temperature at 1 mA
- `hfe_125_over_25@{ic}`: hFE at 125 °C over hFE at 25 °C
- `hfe_100_over_25@{ic}`: hFE at 100 °C over hFE at 25 °C
- `hfe_150_over_25@{ic}`: hFE at 150 °C over hFE at 25 °C
- `hfe_m55_over_25@{ic}`: hFE at −55 °C over hFE at 25 °C

Curves: hFE, −55°C (hfe against ic, log, at T = -55); hFE, 25°C (hfe against ic, log, at T = 25); hFE, 100°C (hfe against ic, log, at T = 100); hFE, 125°C (hfe against ic, log, at T = 125); hFE, 150°C (hfe against ic, log, at T = 150); VBE, −55°C (vbe against ic, lin, at T = -55); VBE, 25°C (vbe against ic, lin, at T = 25); VBE, 100°C (vbe against ic, lin, at T = 100); VBE, 125°C (vbe against ic, lin, at T = 125); VBE, 150°C (vbe against ic, lin, at T = 150); VCE(sat), −55°C (vcesat against ic, log, at T = -55); VCE(sat), 25°C (vcesat against ic, log, at T = 25); VCE(sat), 100°C (vcesat against ic, log, at T = 100); VCE(sat), 125°C (vcesat against ic, log, at T = 125); VCE(sat), 150°C (vcesat against ic, log, at T = 150); VBE(sat), −55°C (vbesat against ic, lin, at T = -55); VBE(sat), 25°C (vbesat against ic, lin, at T = 25); VBE(sat), 100°C (vbesat against ic, lin, at T = 100); VBE(sat), 125°C (vbesat against ic, lin, at T = 125); VBE(sat), 150°C (vbesat against ic, lin, at T = 150); IC, −55°C (ic against vbe, log, at T = -55); IC, 25°C (ic against vbe, log, at T = 25); IC, 100°C (ic against vbe, log, at T = 100); IC, 125°C (ic against vbe, log, at T = 125); IC, 150°C (ic against vbe, log, at T = 150); dVBE/dT, −55 to 25°C (dvbe_dt against ic, lin, at span = −55 to 25°C); dVBE/dT, 25 to 100°C (dvbe_dt against ic, lin, at span = 25 to 100°C); dVBE/dT, 100 to 125°C (dvbe_dt against ic, lin, at span = 100 to 125°C); dVBE/dT, 125 to 150°C (dvbe_dt against ic, lin, at span = 125 to 150°C). Shown first: T = all, span = all.

Beside the point under the cursor: IB (A), the base current at that point, IC over hFE; P (W), power dissipated in the collector junction, VCE(sat) × IC; gm (S), transconductance, the local slope dIC/dVBE.

**Card parameters that drive it:** XTB, XTI, EG, IS, NF.

**A high value.** A gain that doubles between 25 and 125 °C is a high XTB (above 2); real silicon parts sit between 1.3 and 1.8 times.

**A low value.** A VBE slope smaller than 1.5 mV/K in magnitude says an EG or XTI that was changed from the defaults without reason. Gain ratios of exactly 1 are a card without XTB.

**What it cannot tell.** Self-heating: the simulator holds the junction at the set temperature whatever the power; a real output transistor at 100 mA and 5 V is warmer than its heatsink. Leakage currents against temperature are below the simulators' floor and are not published.

**Standard.** resembles IEC 60747-7 temperature characteristics; data sheets print them as curve families

#### Is there any breakdown, and what leaks (`bjt-breakdown`)

Group `breakdown` · analysis `dc` · engines qspice, ngspice, ltspice · symbols V(BR)CEO, V(BR)CBO, V(BR)EBO, ICBO, ICEO.

A plain Gummel-Poon card has no avalanche. Its collector current stays flat to any voltage, so a simulation will never show a stage dying at VCEO, a zener-connected emitter junction at 6 V, or an output stage failing on an inductive kick. The cards that do model breakdown are the exceptions: LTspice's BVcbo and BVbe extensions, VBIC's avalanche terms, QSPICE's higher levels. This measurement mostly documents an absence, and it is here because the absence is the single most dangerous thing to forget when a simulation is trusted near the ratings. The leakage currents of a model, ICBO and ICEO, are set by IS and by the simulator's own minimum conductance; they are far below those of a real part and are published only with that note.

**Circuit.** Three sweeps. Collector to emitter with the base returned to the emitter through 1 MΩ, 0 to 300 V. Collector to base with the emitter open, 0 to 300 V. Emitter to base reversed with the collector open, 0 to 30 V. The current in each is read against the voltage.

Drawing: DUT; swept voltage source; 1 MΩ base return (first sweep); ammeter. Differs from the netlist: the three sweeps are three decks; the drawing shows the collector-emitter one.

**Conditions.** {vce_sweep: {from: 0, to: 300, step: 1, unit: V}, vcb_sweep: {from: 0, to: 300, step: 1, unit: V}, veb_sweep: {from: 0, to: 30, step: 0.1, unit: V}, breakdown_current: 0.001, leakage_points: {icbo: 10, iceo: 10, iebo: 5}, temp_c: 25}

**The deck (QSPICE), line by line.**

- `VA sw ca 0` — collector-base deck: a 0 V source from the swept node to the collector reads the current
- `REA ea 0 1e9` — the emitter open: 1 GΩ to ground
- `QA ca 0 ea DUT` — the transistor, base grounded
- `.dc VSW 0 300 1` — the sweep: 0 to 300 V in 1 V steps
- `RBA ba 0 1e6` — collector-emitter deck: the base tied to the emitter through 1 MΩ
- `QA ca ba 0 DUT` — the transistor, emitter grounded
- `VA sw ea 0` — emitter-base deck: the swept node drives the emitter
- `RCA ca 0 1e9` — the collector open: 1 GΩ to ground
- `.dc VSW 0 30 0.1` — the sweep: 0 to 30 V in 0.1 V steps
- read: the voltage at which the current passes 1 mA, else absent; the leakage at 10 V (5 V for the emitter junction)

**Extraction.** The breakdown voltage is the first voltage at which the current exceeds 1 mA; when the sweep ends without that, the code is "absent" with the voltage reached. ICBO and ICEO at 10 V and IEBO at 5 V are read directly, with a note when the value is below 10 pA (the floor the simulators' minimum conductance sets).

**Outputs.**

- `vbr_ceo` (V): collector-emitter breakdown with the base returned through 1 MΩ, or absent
- `vbr_cbo` (V): collector-base breakdown, emitter open, or absent
- `vbr_ebo` (V): emitter-base breakdown, collector open, or absent
- `icbo@10V` (A): collector-base leakage at 10 V
- `iceo@10V` (A): collector-emitter leakage at 10 V, base open
- `iebo@5V` (A): emitter-base leakage at 5 V

**Card parameters that drive it:** BVCBO, NBVCBO, BVBE, IBVBE, NBVBE, IS, ISC, ISE.

**A low value.** A breakdown that appears means the card carries an extension or a higher-level model; the number is then worth comparing with the sheet. Leakage below 10 pA is the simulator, not the model.

**What it cannot tell.** Anything about the real part's breakdown when the code is "absent": the model simply has no such physics. The simulators' minimum conductance (gmin, 1e-12 S) makes every leakage below about 10 pA at 10 V meaningless.

**Standard.** resembles the breakdown voltage and cutoff current methods of MIL-STD-750-3

#### A reference stage's harmonic distortion (model against model only) (`bjt-distortion`)

Group `distortion` · analysis `tran` · engines qspice, ngspice · symbols THD, HD2, HD3.

No data sheet gives a small-signal transistor's distortion, yet it is what audio users most want a model to predict. Distortion in a transistor stage comes from the curvature of its characteristics — the exponential VBE law, the gain changing with current, the Early effect, the capacitances changing with voltage — all of which the previous measurements describe one at a time. Here they act together in one fixed stage, so that two models of the same part can be compared, and a model that was fitted at one operating point can be told from one whose curvature is right. The stage is a textbook one: a common emitter with emitter degeneration, so that the exponential law is tamed by feedback and the gain curvature shows through.

**Circuit.** The emitter current is set by an ideal 1 mA current source below a 260 Ω emitter resistor (gm·RE = 10 at 1 mA); the resistor's lower end is held at signal ground by a large capacitor, so the degeneration is the resistor alone. The collector feeds a 5 kΩ load resistor from 10 V, which puts VCE near 5 V. The base is driven through 1 kΩ. A first short run measures the gain, and the input amplitude is then set so that the output swings 1 V peak at 1 kHz; ten cycles are simulated and the last four analysed.

Drawing: DUT; 1 mA current source under the emitter; emitter resistor 260 Ω bypassed to ground; load resistor 5 kΩ to 10 V; 1 kHz source with 1 kΩ; output probe on the collector. Differs from the netlist: nothing; the first gain-finding run is not drawn.

**Conditions.** {ie: 0.001, re: 260, rl: 5000, vcc: 10, rs: 1000, f: 1000, vout_peak: 1, cycles: 10, analysed_cycles: 4, steps_per_cycle: 4096}

**The deck (QSPICE), line by line.**

- `VCC vcc 0 10` — the supply, 10 V
- `RL vcc c 5000` — the collector load, 5 kΩ
- `RS in b 1000` — the source resistance, 1 kΩ
- `RE e x 260` — the emitter degeneration: 260 Ω, so that gm × RE = 10 at 1 mA
- `IE x vee 0.001` — the bias: 1 mA from an ideal current source in the emitter
- `VEE vee 0 -5` — the negative rail for that source
- `Q1 c b e DUT` — the transistor
- `VIN in 0 SIN(0 0.02 1000)` — the probe run: 20 mV at 1 kHz, to learn the stage's gain for this model
- `.tran 2.44140625e-07 0.01 0 2.44140625e-07` — the measuring run: ten cycles of 1 kHz, the last four analysed; its input level (not shown) is set for 1 V peak out

**Extraction.** The output over the last four cycles is resampled onto a uniform grid and the amplitudes of harmonics 2 to 10 are taken by Goertzel's algorithm; THD is the root sum of squares of those over the fundamental. HD2 and HD3 are published separately because a differential stage cancels the first and not the second.

**Outputs.**

- `thd`: total harmonic distortion of the reference stage, 1 V peak out
- `hd2`: second harmonic over the fundamental
- `hd3`: third harmonic over the fundamental

**Card parameters that drive it:** IS, NF, BF, ISE, NE, IKF, VAF, CJC, CJE, RB, RE.

**A high value.** Only against another model of the same part: the amplitude is fixed by the stage, not by the part, so the absolute figure is not a prediction of any circuit's distortion.

**A low value.** With this degeneration the stage sits around half a percent, nearly all of it second harmonic; two models of one part that differ by a factor of two here differ in the curvature of their gain or in their Early voltage, which the DC measurements then show.

**What it cannot tell.** The distortion of the real part, or of any other circuit. It is a comparison between models.

**Standard.** none

#### Do the three simulators agree? (`bjt-agreement`)

Group `dc` · analysis `derived` · engines qspice, ngspice, ltspice.

Not a circuit. Every number above is produced in QSPICE and in ngspice, and most in LTspice as well. Where the three agree to within 1 % the number is the model's; where one disagrees by more than 5 % the card is being read differently by that simulator — a unit it parses as something else, a parameter it clamps, an extension it ignores — and the result says which one is the odd one out and on which measurements. That is the "dialect" fact about a card, measured rather than guessed from its text.

**Conditions.** {tolerances: [0.01, 0.05], floors: {F: 1e-16, s: 1e-12}}

**Extraction.** For each published output, the spread (max − min over the mean) across the engines that produced it, classed as within 1 %, within 5 % or beyond; values below the floors count as zero. The engine that is alone outside the band is the odd one out.

**Outputs.**

- `agree_1pct`: share of outputs on which every engine agrees within 1 %
- `agree_5pct`: share within 5 %
- `odd_engine`: the engine most often alone outside 5 %, or none
- `disagreeing`: the measurement ids where the engines differ by more than 5 %

**What it cannot tell.** Which engine is right. Agreement says the card means one thing to all three; disagreement says the card depends on the dialect, and the card's text (the capability layer) usually shows why.

**Standard.** none
<!-- measurements:end -->

## Reproducing one number

Every published value carries the measurement id, the catalogue version, its conditions, the simulator
and its identity (ngspice's version string; the executable's sha256 for the Wine engines), the image
digest, the bench code's commit and the sha256 of the deck text. To repeat it:

1. Get the model from its recipe (`data/models/parts/<kind>/<part>.yaml`, `get` block: URL, file,
   member, sha256). The project never ships the text.
2. `sei bench deck <measurement-id> --card <file> --name <model> --engine ngspice` writes `model.lib`
   and the decks and prints each deck's sha256, which must equal the published one (the deck includes
   `model.lib` and never contains the card).
3. Run it in the pinned image: `docker run --rm -v "$PWD":/w spicy-electronics-index-ngspice simrun /w/<deck>.cir`,
   then `sei bench read <deck>.raw --measurement <id>` applies the same extraction.

Transients are not repeatable bit for bit across simulators (each chooses its own time steps).

## What is published, and where

- `data/bench/measurements.yaml` — the catalogue; `make bench-methods` checks it and rewrites the
  section above. Changing a measurement means bumping the catalogue version, which reruns every model.
- `data/bench/drawings/<id>.svg` — the circuit drawings, typeset by `make bench-drawings NAME=<id>` from
  `docker/circuitikz/drawings/<id>.tex` (`benches.py` writes the `.tex`; each header lists the deck lines
  it stands for).
- `data/verification/models/<hh>/<hash>.json` — one record per model hash: values per measurement and
  simulator, codes, curves of the primary engine, and of a secondary engine only where it differs by more
  than 1 %. Not in git: each catalogue version travels as the release asset `character-<version>.tar.gz`
  (`make bench-character-release`), named in `data/verification/models/release.json`; the site's build
  fetches it (`sei bench character-fetch`).
- `data/verification/models/state.csv` — the ledger (card hash, catalogue sha256, image ids per model).
- Never published: the cards, the jobs that carry them, the raw waveforms.

## What is not measured

Diodes on their own, IGBTs, SiC and GaN parts, op-amp macromodels, encrypted models; BSIM cards are
recorded by family and not run. A PSpice `AKO` card is run written out in full when its file holds the
base. A subcircuit of three to five pins (a Darlington, a transistor with its leads, a ThermalTrak part)
is run only when the role of every pin can be traced through its netlist — pin order is never assumed.
Self-heating is not simulated: the junction sits at the set temperature whatever the power.
