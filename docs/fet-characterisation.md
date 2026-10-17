# Characterising the SPICE JFET and MOSFET models

A proposed extension of [model-characterisation.md](model-characterisation.md) to the two field-effect
families. It keeps that page's principles (behaviour only, intrinsic ladders, numbers not opinions,
explained once per measurement, reproducible) and its section shape, so that
`data/bench/measurements.yaml` can grow two more kinds and `make bench-methods` can write these sections
the way it writes the bipolar one. Where a convention below differs from the bipolar bench it is because
the device is driven differently: a field-effect transistor is driven by a voltage, not a current, and
has no base to overdrive.

## Conventions for the field-effect benches

- **Gate drive.** DC sweeps drive the gate from a plain voltage source, stepped linearly (5 mV for a
  JFET, 10 mV for a MOSFET); there is no junction to force a current into. Where a measurement forces the
  *drain* current (on-resistance, the diode-connected threshold, the body diode) it uses the bipolar
  bench's behavioural dial, `ID = 10^V(x)`, with a clamp diode to a rail so that a copy that cannot pass
  the current is caught rather than failing.
- **Polarity.** A P-channel card (and a P-channel JFET) is run with every source reversed and the
  magnitudes published; the record carries `polarity: p`. Nothing else changes.
- **Ladders.** Drain current 1 µA to 100 A (power MOSFETs are rated to hundreds of amperes; a JFET
  stops at IDSS, so its ladder ends where the model does and the rest is `n/a`). Drain voltage 1, 5, 6,
  10, 15, 20, 25 V, the values the sheets of the main makers fix their curves at. Gate voltage for
  MOSFETs 2, 2.5, 3, 3.5, 4, 4.5, 5, 6, 8, 10, 15 V (logic-level and standard sheets together). Temperatures
  −55, 25, 100, 125, 150 and 175 °C (power MOSFETs are rated to 175 °C).
- **The model's own points.** Where a condition depends on the part — the gate voltage that puts the top
  tracer trace near 10 mA, the current a `k·IDSS` reading is taken at, the voltage the threshold is
  read at — it is derived from the model's own transfer sweep, and the derived value is published beside
  the universal ones.
- **Levels.** JFET cards are SPICE level 1 (Shichman-Hodges with the PSpice and LTspice extensions). MOSFET
  cards are level 1 and 3, the LTspice/QSPICE `VDMOS` card (ngspice reads it since version 28), and
  subcircuits that wrap one of those with an external body diode, capacitors and resistors; a BSIM card is
  recorded by family and not run, as in the bipolar bench. A subcircuit is run only when its three pins
  can be traced to drain, gate and source through its netlist.
- **What the device model lacks.** The level 1 and 3 MOSFET models have no reverse-recovery charge, no
  avalanche, no gate leakage and no self-heating; a plain JFET card has no gate breakdown and no
  impact-ionisation gate current (LTspice's `ALPHA`/`VK` add it). Each measurement below says what this
  does to it; several exist chiefly to document the absence.
- Sampling 20 points per decade where a current is swept, 20 to 40 per decade in AC, `reltol = 1e-4`,
  25 °C unless the entry says otherwise, one deck packs several copies where the analysis allows, a
  transient is one deck per step, as in the bipolar bench.

Which groups matter for which use:

| use | groups | look at |
|---|---|---|
| Audio preamplifier, pedal or microphone input (JFET) | dc, noise, capacitance, distortion | IDSS and VGS(off) (the bias point depends on both), gfs between 100 µA and IDSS, en at 10 Hz and 1 kHz and the 1/f corner, Ciss and Crss at the working VDS, the square-law exponent (second-harmonic character), the gate diode in forward bias (asymmetric clipping). |
| Analogue switch or voltage-controlled resistor (JFET) | ohmic, capacitance, switching | rDS(on) at VGS = 0 and how fast it rises towards VGS(off), the linearity of rDS with VDS, Crss (charge injection), ton/toff. |
| Class-AB or follower output stage (MOSFET) | temperature, dc, high-current, capacitance | the zero-temperature-coefficient point and dVth/dT (bias stability), gfs between 10 mA and 1 A, RDS(on) and its slope with temperature, Crss against VDS (the distortion mechanism at 20 kHz), the body diode's VSD. |
| Switch, driver or converter (MOSFET) | switching, gate-charge, high-current, body-diode, breakdown | RDS(on) at the drive voltage and current used, Qg, Qgd and the plateau voltage, td/tr/tf at that current and RG, Qgd/Qgs(th) (parasitic turn-on), the body diode's VSD and whether trr exists in the card, whether breakdown exists at all. |
| Current sources, cascodes, LTP input stages | dc, temperature | the output conductance gos (LAMBDA), gfs at the operating current, VGS(off) or Vth spread between two cards of the same part, the zero-TC point. |

### Junction field-effect transistors

#### Does the card load? (`jfet-runs`)

Group `dc` · analysis `op` · engines qspice, ngspice, ltspice.

The first fact about a model: whether each simulator reads the card and finds an operating point. The
operating point chosen is the one every JFET sheet starts from, the gate tied to the source and the drain
at 10 V, so that the drain current read is IDSS itself; the gate current at that point is read as well,
because it is the quickest sign that a card carries a gate diode (`IS`) at all.

**Circuit.** The transistor with its source grounded, the gate grounded through a 0 V source (an
ammeter), the drain held at 10 V.

Drawing: DUT; VDS source 10 V; gate to ground through an ammeter; ammeter in the drain.

**Conditions.** {vds: 10, vgs: 0, temp_c: 25}

**The deck (QSPICE), line by line.**

- `VD d 0 10` — the drain supply, 10 V; its current is IDSS
- `VG g 0 0` — the gate grounded through a 0 V source: reads the gate current
- `J1 d g 0 DUT` — the transistor, source grounded
- `.op` — one operating point
- `.options reltol=1e-4` — the solver's relative tolerance

**Extraction.** Exit status and log give the error class as in the bipolar bench; when it runs, the drain
and gate currents at the operating point.

**Outputs.**

- `runs`: true when the simulator returned a solution
- `error_class`: syntax, convergence, timeout or empty when it ran
- `idss_op` (A): drain current at VGS = 0, VDS = 10 V
- `ig_op` (A): gate current at the same point (the gate diode's reverse saturation current, or the simulator's floor)

**What it cannot tell.** That the model is right; QSPICE accepts cards other engines reject. Agreement
between engines is the stronger fact.

**Standard.** none

#### Output characteristics, as a curve tracer draws them (`jfet-tracer`)

Group `dc` · analysis `dc` · engines qspice, ngspice, ltspice · symbols ID(VDS), VGS.

The family every JFET sheet opens with: drain current against drain-source voltage, one trace per step of
gate voltage, the steps equal. Three things are read at a glance. Where each trace bends from the
ohmic region into saturation, which happens near VDS = VGS − VGS(off), so the knees march to the right as
the gate is opened; a card with large `RD` and `RS` rounds the knees and pulls them right. The slope of the
flat part, the output conductance, which in a card is `LAMBDA` alone: one number for all traces, so a
model's traces all climb at the same relative rate, which real JFETs do not quite do. And the spacing of
the traces, which is the square law: equal gate steps give traces that crowd together towards pinch-off and
spread apart near VGS = 0. The sheets of Linear Systems and Toshiba print this family twice, once to 25 V
and once zoomed to the first 2 V, where the device is a voltage-controlled resistor; both views are kept
from one sweep.

**Circuit.** Five copies of the transistor, each with its gate held at one to five times a step below
zero (an N-channel JFET is on at VGS = 0 and closes as the gate goes negative). The step is either one of
nine universal values (0.05, 0.1, 0.2, 0.25, 0.5, 1, 1.5, 2, 3 V, which spans the 50 mV steps of a
2SK170 sheet and the volt steps of a 2N4391), or "auto": a fifth of the model's own VGS(off) read in the
transfer sweep at 10 nA, so that the top trace is IDSS and the bottom one runs near pinch-off whatever the
model. One voltage source sweeps every drain from 0 to 25 V in 20 mV steps; each drain current is read
through a 0 V source.

Drawing: DUT; swept VDS source 0 to 25 V; gate voltage source at −k × step; ammeter in the drain.
Differs from the netlist: the fifty copies are drawn as one transistor with a stepped gate.

**Conditions.** {steps: 5, vgs_steps: [0.05, 0.1, 0.2, 0.25, 0.5, 1, 1.5, 2, 3], auto: {from: jfet-transfer, vgs_off_at: 1e-08, divisor: 5}, vds_sweep: {from: 0, to: 25, step: 0.02, unit: V}, zoom_to: 2, temp_c: 25}

**The deck (QSPICE), line by line.**

- `VK1 sw dk1 0` — a 0 V source from the swept node to the first copy's drain: reads its ID
- `VGK1 gk1 0 {-1*step}` — its gate, one auto step below ground; VGK2 to VGK5 at two to five steps; the universal families are copies JU11 to JU95 with VGU11 to VGU95
- `JK1 dk1 gk1 0 DUT` — the first auto copy, source grounded
- `VSW sw 0 0` — the drain supply of every copy, swept
- `.dc VSW 0 25 0.02` — the sweep: 0 to 25 V in 20 mV steps
- the auto step is VGS(off)/5 from the transfer sweep, VGS(off) read where ID = 10 nA at VDS = 10 V

**Extraction.** Each trace is one copy's drain current on the grid; the same data is published twice,
to 25 V and cut at 2 V (the ohmic view). The top auto trace's current at 10 V is kept as a figure; the knee
of each auto trace, the voltage at which it reaches 90 % of its value at 10 V, is kept as the saturation
voltage against gate step. The universal families are published as they come: for a 2N4391 (VGS(off)
near −8 V) the 0.05 V family is five traces almost on top of one another, for a 2SK170 (VGS(off) near
−0.4 V) the 3 V family is one trace and four at zero, which is itself what the chart shows.

**Outputs.**

- `vgs_step` (V): the auto step: VGS(off)/5 from the transfer sweep
- `idss@10V` (A): the top auto trace (VGS = 0) at 10 V
- `vds_knee@step{k}` (V): the voltage at which trace k reaches 90 % of its 10 V value

Curves: `ID, step k, auto` (id against vds, lin, at VGS step = auto, k = 0 to 5); `ID, step k, VGS step={v}` for each universal step; the same with `view = 0–2 V`. Drawn together, as a family: VGS = −k × step, k = 0 to 5 (k = 0 is VGS = 0, the IDSS trace). Shown first: VGS step = auto, view = 0–25 V.

Beside the point under the cursor: P (W), power dissipated in the transistor, VDS × ID; rDS (Ω), the chord resistance VDS/ID, which in the ohmic view is the controlled resistance; ro (Ω), output resistance, the local slope of the trace.

**Card parameters that drive it:** BETA, VTO, LAMBDA, RD, RS, B (LTspice's doping-tail parameter).

**A high value.** Traces that climb steeply along the flat part are a large LAMBDA (low output
resistance); knees far to the right are large RD and RS.

**A low value.** Perfectly flat traces are a card with LAMBDA = 0: an infinite output resistance no JFET
has, and a current-source or cascode simulated on it will look better than the real one.

**What it cannot tell.** Breakdown at the drain-gate junction (a plain card has none, see
`jfet-breakdown`) and the thermal droop at high power.

**Standard.** resembles the output characteristics every JFET sheet prints and a curve tracer draws; no test method

#### Transfer characteristic — ID against VGS at fixed VDS (`jfet-transfer`)

Group `dc` · analysis `dc` · engines qspice, ngspice, ltspice · symbols IDSS, VGS(off), gfs.

The one curve a JFET is specified by, and the one its model is fitted to: drain current against gate
voltage with the drain held. Its two ends are the two headline numbers of the sheet, IDSS where the gate is
at zero and VGS(off) where the current has fallen to a nanoampere or ten; everything between them is the
square law ID = IDSS (1 − VGS/VP)², whose slope is the transconductance. Real devices are not exactly
square — the exponent sits between 1.7 and 2.3 and is what gives a JFET stage its second-harmonic
character — and the current does not stop at pinch-off but tails off exponentially below it (LTspice's `B`
and the subthreshold region), which is where the low-current bias of a condenser-microphone stage sits.
Four drain voltages are run because the sheets fix different ones (onsemi 15 or 20 V, Toshiba and Linear
Systems 10 V, Nexperia 15 V) and because how much the curve moves with VDS is LAMBDA again. The log view
reaches 1 nA so that VGS(off) can be read at the three currents the sheets define it at.

**Circuit.** Four copies of the transistor, sources grounded, drains held at 5, 10, 15 and 20 V. One
voltage source sweeps every gate from −10 V (below the pinch-off of any discrete JFET) to +0.6 V (into
gate conduction) in 5 mV steps; each drain current is read through its supply.

Drawing: DUT; VDS source (5, 10, 15 or 20 V); swept VGS source; ammeter in the drain; ammeter in the gate.
Differs from the netlist: the four VDS copies run in one deck; the drawing shows one.

**Conditions.** {vgs_sweep: {from: -10, to: 0.6, step: 0.005, unit: V}, vds: [5, 10, 15, 20], vgs_off_currents: [1e-09, 1e-08, 1e-06], id_ladder: [1e-06, 1e-05, 0.0001, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1], fit_window: [0.05, 0.9], temp_c: 25}

**The deck (QSPICE), line by line.**

- `VT1 dt1 0 10` — the drain supply of the 10 V copy, the one the summary values come from; VT0, VT2, VT3 at 5, 15 and 20 V
- `VGS g 0 0` — the gate drive, swept, shared by every copy
- `JT1 dt1 g 0 DUT` — the 10 V copy, source grounded
- `.dc VGS -10 0.6 0.005` — the sweep: −10 V to +0.6 V in 5 mV steps
- read: ID as each supply's current; VGS(off) where ID crosses 1 nA, 10 nA and 1 µA; IDSS at VGS = 0

**Extraction.** IDSS is ID at VGS = 0 at each VDS. VGS(off) is the gate voltage at which ID has fallen to
1 nA, 10 nA and 1 µA (three definitions in use: Linear Systems 1 nA, onsemi 10 nA, Nexperia 1 µA), reported
"n/a" where the card's current never falls that far (no subthreshold tail). The square-law exponent n is
fitted as the slope of log ID against log (VP − VGS) between 5 % and 90 % of IDSS, with VP the 10 nA
VGS(off); the ratio gfs(0)·VP/IDSS, which is exactly 2 for a square law, is published as the simpler
figure. VGS at each ladder current is interpolated on the 10 V curve, and ID at VGS = 0, −0.1, −0.2,
−0.5, −1, −2, −5 V is kept for the universal view. The curve is published both linear (the sheet's view)
and on a log current axis to 1 nA (the subthreshold view). The gate current along the sweep is kept for
`jfet-gate`.

**Outputs.**

- `idss@{vds}` (A): drain current at VGS = 0, at 5, 10, 15 and 20 V
- `vgs_off@{current},{vds}` (V): gate voltage at ID = 1 nA, 10 nA and 1 µA
- `vgs@{id},{vds}` (V): gate voltage at each ladder current
- `n_fit`: the exponent of the fitted power law
- `gfs_vp_over_idss`: gfs(0) × VP / IDSS; 2 for an exact square law
- `idss_20v_over_5v`: IDSS at 20 V over IDSS at 5 V (the output conductance, read another way)

Curves: `ID, VDS={vds}` (id against vgs, lin); `ID log, VDS={vds}` (id against vgs, log). Shown first: VDS = 10, lin.

Beside the point under the cursor: gfs (S), transconductance, the local slope dID/dVGS; P (W), power dissipated, VDS × ID.

**Card parameters that drive it:** BETA, VTO, LAMBDA, B, RS, RD, ISR, NR.

**A high value.** An exponent above 2.2 is a card fitted with `B` for a doping tail; IDSS at 20 V far above
IDSS at 5 V (ratio above 1.15) is a large LAMBDA.

**A low value.** An exponent of exactly 2.00 and no current below VP is a plain Shichman-Hodges card:
right in the middle of the range, and wrong at both ends where low-current and clipping behaviour live.

**What it cannot tell.** Which grade of the part the card models: a sheet gives IDSS as a range per grade
(A, B, C, D), and one card is one point in it. Comparing is the comparison step.

**Standard.** resembles the transfer characteristics every JFET sheet prints (MIL-STD-750-3 IDSS and VGS(off) methods)

#### Transconductance and output conductance against drain current (`jfet-gm`)

Group `dc` · analysis `ac` · engines qspice, ngspice, ltspice · symbols gfs, gos, yfs.

The two small-signal parameters an amplifier stage is designed from. gfs (also yfs, |Yfs|) sets the gain of
a common-source stage with a given drain load; it rises with the square root of the drain current for a
square-law device, so doubling the bias current buys 41 % more gain, and it is highest at IDSS. gos is the
output conductance, 1/ro, which limits the gain of a stage with a current-source load; its ratio to gfs is
the intrinsic voltage gain of the transistor. The sheets draw gfs against ID (Toshiba, Linear Systems,
onsemi), gfs against VGS (onsemi) and gos against VDS (Linear Systems); the first two come from one AC run
and the third has its own copies.

**Circuit.** One copy per ladder current at VDS = 10 V (and a second set at 15 V): the gate biased by a
voltage from the transfer sweep so that the drain current is the ladder step, with 1 V of AC on top; the
AC drain current is gfs. For gos, copies at the same currents with the gate held and 1 V of AC on the
drain; and a swept-VDS family at four fixed currents, read for gos against VDS. All read at 1 kHz.

Drawing: DUT; VDS source 10 V; gate bias source with a small AC component (gfs copy); gate bias held and AC on the drain (gos copy); AC ammeter in the drain. Differs from the netlist: one copy per ladder current; the drawing shows one of each kind.

**Conditions.** {vds: [10, 15], id_ladder: [1e-05, 3e-05, 0.0001, 0.0003, 0.001, 0.002, 0.003, 0.005, 0.01, 0.02, 0.05, 0.1], gos_vds_sweep: {from: 0, to: 25, step: 0.05, unit: V}, gos_id: [0.0001, 0.001, 0.003, 0.01], f: 1000}

**The deck (QSPICE), line by line.**

- `VD0 d0 0 10` — the drain supply of the first gfs copy, 10 V; its AC current is gfs × 1 V
- `VG0 g0 0 DC {vgs_for_step} AC 1` — its gate: the bias for the ladder step, from the transfer sweep, plus 1 V of AC
- `JM0 d0 g0 0 DUT` — the first copy, source grounded; one per ladder step
- `VDO0 do0 0 DC 10 AC 1` — a gos copy: the drain driven with 1 V of AC, the gate held
- `.ac dec 10 100 10000` — ten points per decade from 100 Hz to 10 kHz; read at 1 kHz
- a second deck sweeps VDS 0 to 25 V at four fixed gate biases for gos against VDS

**Extraction.** gfs at each ladder current is the AC drain current over the 1 V of AC gate drive at
1 kHz; gos likewise from the drain-driven copy. gfs/√ID is published at 1 mA and at the top current: constant
for a square law, falling where RS degenerates the device. The intrinsic gain gfs/gos is kept at 1 mA.
gos against VDS at each fixed current is the local slope of the swept family between neighbouring points;
the equivalent Early voltage VA = ID/gos − VDS at 10 V is kept, "absent" above 10 000 V (LAMBDA = 0).

**Outputs.**

- `gfs@{id},{vds}` (S): transconductance at 1 kHz at each ladder current
- `gos@{id},{vds}` (S): output conductance at 1 kHz
- `gfs_over_sqrt_id@{id}` (S/√A): the square-law figure, at 1 mA and the top current
- `av_intrinsic@1mA`: gfs/gos at 1 mA, 10 V
- `va_equiv@{id}` (V): ID/gos − 10 V, the Early-voltage equivalent (1/LAMBDA), or absent

Curves: `gfs, VDS={vds}` (gfs against id, log); `gfs vs VGS, VDS={vds}` (gfs against vgs, lin); `gos, VDS={vds}` (gos against id, log); `gos vs VDS, ID={id}` (gos against vds, lin). Shown first: gfs, VDS = 10.

Beside the point under the cursor: P (W), VDS × ID; ro (Ω), 1/gos.

**Card parameters that drive it:** BETA, VTO, LAMBDA, RS, RD, B.

**A high value.** gfs/√ID that falls by more than 20 % between 1 mA and IDSS is a large RS; an intrinsic
gain above 1000 at 1 mA is a very small LAMBDA.

**A low value.** gos of exactly zero is a card with LAMBDA = 0 (code "absent" for VA); an intrinsic gain
below 30 is a soft device or a LAMBDA set from a sheet's gos at the wrong current.

**What it cannot tell.** The frequency dependence of either (next measurement), and the 1 MHz value Toshiba
quotes as |Yfs|, which the capacitances begin to touch.

**Standard.** resembles the forward transfer admittance and output admittance methods (MIL-STD-750-3, 1 kHz)

#### The ohmic region — rDS(on) against VGS and its linearity (`jfet-ohmic`)

Group `ohmic` · analysis `dc` · engines qspice, ngspice, ltspice · symbols rDS(on), rDS(VGS).

Below the knee a JFET is a resistor whose value the gate sets: the voltage-controlled resistor of
compressors, tremolos and gain cells, and the series element of an analogue switch. Two things describe
it. rDS(on) at VGS = 0, the lowest value, which in a card is RD + RS + the channel at full width (set by
BETA and VTO); and how the resistance rises as the gate closes, to infinity at VGS(off). A third thing is
what the gain-cell designer lives with: the resistance is not constant across the signal, because the
channel narrows on the drain side as VDS grows, so the resistor is non-linear and distorts; the classic
cure feeds half the drain signal back to the gate and cancels the second-order term. Both the raw
non-linearity and the cancelled one are measured.

**Circuit.** For rDS(on) against VGS, one copy with ±50 mV on the drain and the gate stepped from 0 to
VGS(off) (the model's own, 20 steps), the drain current read and the resistance taken as the chord. For
linearity, copies at VGS = 0, VGS(off)/4, VGS(off)/2 and 3·VGS(off)/4 with the drain swept −0.5 to +0.5 V,
once with the gate held and once with the gate fed VGS + VDS/2 through two 1 MΩ resistors.

Drawing: DUT; drain source ±50 mV (or swept ±0.5 V); gate source stepped; two 1 MΩ resistors from drain and from the gate bias to the gate (feedback copy); ammeter in the drain.

**Conditions.** {vds_small: 0.05, vgs_points: 20, lin_vds_sweep: {from: -0.5, to: 0.5, step: 0.005, unit: V}, lin_vgs_fractions: [0, 0.25, 0.5, 0.75], feedback: 0.5, temp_c: 25}

**The deck (QSPICE), line by line.**

- `VDR dr 0 0.05` — the drain at 50 mV: the ohmic region
- `VGR gr 0 {vgs}` — the gate, stepped from 0 towards VGS(off) in 20 steps
- `JR dr gr 0 DUT` — the transistor
- `.step param vgs 0 {vgs_off} {vgs_off/20}` — the gate steps
- `VDL dl 0 0` / `.dc VDL -0.5 0.5 0.005` — the linearity deck: the drain swept through zero
- `RF1 dl gl 1e6` / `RF2 gb gl 1e6` — the feedback copy: the gate at the mean of the drain and the bias, i.e. VGS + VDS/2

**Extraction.** rDS at each gate step is 50 mV over the drain current (the mean of the ±50 mV readings).
The gate voltage at which rDS has doubled, and at which it has risen tenfold, are kept. From the linearity
sweep the drain current is fitted to a cubic in VDS; the second- and third-order coefficients over the
first, at each VGS, are the distortion figures of the resistor, published for the plain and the feedback
copy. The asymmetry is rDS at +0.5 V over rDS at −0.5 V.

**Outputs.**

- `rds_on@0V` (Ω): rDS(on) at VGS = 0, VDS = 50 mV
- `rds@{fraction}` (Ω): rDS at VGS = VGS(off)/4, /2, 3/4
- `vgs_rds_x2` (V): gate voltage where rDS is twice rDS(on)
- `vgs_rds_x10` (V): gate voltage where rDS is ten times rDS(on)
- `rds_hd2@{fraction}`: second-order coefficient of ID(VDS) over the first, plain gate
- `rds_hd3@{fraction}`: third-order coefficient over the first
- `rds_hd2_fb@{fraction}`: the same with VDS/2 fed back to the gate
- `rds_asym@{fraction}`: rDS at +0.5 V over rDS at −0.5 V

Curves: `rDS vs VGS` (rds against vgs, log); `ID vs VDS ohmic, VGS={fraction}` (id against vds, lin); `rDS vs VDS, VGS={fraction}` (rds against vds, lin); `rDS vs VDS with feedback, VGS={fraction}`. Shown first: rDS vs VGS.

**Card parameters that drive it:** BETA, VTO, RD, RS, LAMBDA, B.

**A high value.** A second-order coefficient that the feedback copy does not reduce is a card whose
asymmetry does not come from the channel (RD ≠ RS); an rDS(on) far above the sheet's is RD + RS set from a
wrong figure.

**A low value.** rDS(on) of exactly 1/(2·BETA·|VTO|) is a card with RD = RS = 0.

**What it cannot tell.** Distortion in a real circuit, where the source impedance and the gate's
capacitive loading enter; this is the resistor alone.

**Standard.** resembles the rDS(on) methods of switching-JFET sheets (Nexperia, Vishay) and the VCR notes of the J111 and 2N4391 families; no test method for linearity

#### The gate diode — forward conduction, reverse leakage and the drain's share of it (`jfet-gate`)

Group `dc` · analysis `dc` · engines qspice, ngspice, ltspice · symbols IG, IGSS, IG(VDG).

The gate of a JFET is a diode to the channel, and it shows in three ways. Forward, it conducts at about
0.6 V: this is the clipping limit on the positive half of a guitar-pedal stage and the reason a JFET input
cannot be driven above its source by much; a card without `IS` has no forward conduction and clips
symmetrically. Reverse, it leaks: IGSS, nanoamperes or picoamperes, which sets the input current of an
electrometer stage and doubles every 10 K. And with the drain high the leakage grows far beyond IGSS,
because carriers accelerated in the drain-gate field ionise and the holes go to the gate; the sheets of
Linear Systems and Vishay draw IG against VDG at several drain currents, and the curve rises by decades
above VDG ≈ 10 V. A plain SPICE JFET card has no term for the third effect (LTspice adds `ALPHA` and `VK`),
so most models read a flat IGSS at any drain voltage, which flatters a high-voltage low-noise stage.

**Circuit.** Three decks. Forward: the gate driven 0 to +0.9 V with the drain and source grounded, the gate
current read. Reverse: the gate driven 0 to −40 V with drain and source grounded. Drain field: copies at four
drain currents (set by the gate bias from the transfer sweep) with the drain swept 0 to 25 V, the gate current
read through its bias source.

Drawing: DUT; gate source swept (forward and reverse decks), drain and source grounded, ammeter in the gate; drain swept with the gate biased (field deck). Differs from the netlist: three decks drawn as one.

**Conditions.** {vg_forward: {from: 0, to: 0.9, step: 0.005, unit: V}, vg_reverse: {from: 0, to: -40, step: 0.1, unit: V}, igss_points: [10, 20, 30], vdg_sweep: {from: 0, to: 25, step: 0.1, unit: V}, field_id: [0.0001, 0.001, 0.003, 0.01], temp_c: 25}

**The deck (QSPICE), line by line.**

- `VGF gf 0 0` / `.dc VGF 0 0.9 0.005` — the forward deck: the gate driven positive; its current is IG
- `JF 0 gf 0 DUT` — drain and source grounded
- `.dc VGF 0 -40 0.1` — the reverse deck, same copy
- `VDF df 0 0` / `.dc VDF 0 25 0.1` — the field deck: the drain swept
- `VGB gb 0 {vgs_for_id}` — the gate biased for the ladder current; its current is IG
- `JD df gb 0 DUT` — the field copy, one per current

**Extraction.** Forward: the gate voltage at IG = 10 µA and 1 mA (the clipping limit), the ideality and
IS of the gate diode fitted between 1 µA and 100 µA. Reverse: IGSS at 10, 20 and 30 V, with a note below
10 pA (the simulators' gmin floor). Field: IG at VDG = 5, 10, 15, 20 V at each current; the ratio IG(20 V)/
IG(5 V) at 1 mA, which is 1.0 for a card without impact ionisation and is then reported "absent".

**Outputs.**

- `vg_fwd@10uA` (V): forward gate voltage at IG = 10 µA
- `vg_fwd@1mA` (V): at 1 mA
- `is_gate` (A): saturation current of the gate diode from the forward fit
- `n_gate`: its ideality factor
- `igss@{v}` (A): reverse gate leakage at 10, 20, 30 V
- `ig@{vdg},{id}` (A): gate current at drain-gate voltage and drain current
- `ig_field_ratio@1mA`: IG at VDG = 20 V over IG at 5 V, or absent

Curves: `IG forward` (ig against vgs, log); `IG reverse` (ig against vgs, log); `IG vs VDG, ID={id}` (ig against vdg, log). Shown first: IG forward.

**Card parameters that drive it:** IS, N, ISR, NR, ALPHA, VK, XTI.

**A high value.** A forward gate voltage above 0.75 V at 1 mA is a large N or RS; IGSS above 1 nA at
25 °C in a card is an IS set for a power device.

**A low value.** Forward current absent is a card with IS = 0 (or 1e-30): it never clips on the gate. A
field ratio of exactly 1 is the absence of impact ionisation, the usual case.

**What it cannot tell.** The real part's leakage, which is dominated by surface and package effects a card
does not carry; and burst noise, which the gate diode causes in real parts.

**Standard.** resembles the IGSS and IG methods of MIL-STD-750-3 and the "IG vs VDS" charts of Linear Systems sheets

#### Ciss, Crss and the two junction capacitances against voltage (`jfet-capacitance`)

Group `capacitance` · analysis `ac` · engines qspice, ngspice, ltspice · symbols Ciss, Crss, Cgs, Cgd.

Two reverse-biased junctions, gate-source and gate-drain, both falling with voltage as the depletion
layer widens. Ciss = Cgs + Cgd is the input capacitance of a common-source stage and loads a guitar
pickup or a condenser capsule; Crss = Cgd is the feedback capacitance, multiplied by the gain into the
Miller input capacitance, and the charge injection of a switch. The sheets quote both at VDS = 10 or 15 V,
VGS = 0, 1 MHz. In a card they are `CGS` and `CGD` at zero bias with `PB` and `M` for the fall; a card
without them has a JFET of infinite bandwidth and no noise penalty from a capacitive source.

**Circuit.** For Ciss, the gate driven with 1 V of AC on top of its bias, drain and source joined; for
Crss, the gate with AC and the drain current read with the source grounded (the reverse transfer term); for
Cgs and Cgd alone, each junction with the third terminal open through 1 GΩ. Eight copies at eight reverse
voltages share one run.

Drawing: DUT; bias source with AC on the gate; drain and source tied (Ciss) or the drain read (Crss); third terminal open through 1 GΩ (Cgs, Cgd); AC ammeter.

**Conditions.** {v_ladder: [0.1, 0.5, 1, 2, 5, 10, 15, 20, 30], crss_vs_vds: {vgs: 0}, f: 1e+06, ac_sweep: {from: 100000, to: 1e+07, per_decade: 10, unit: Hz}, temp_c: 25}

**The deck (QSPICE), line by line.**

- `VGC gc 0 DC {-v} AC 1` — the Ciss copy at reverse voltage v: the gate held v below the channel with 1 V of AC
- `JC 0 gc 0 DUT` — drain and source joined to ground
- `VDX dx 0 {v}` / `VGX gx 0 AC 1` / `JX dx gx 0 DUT` — the Crss copy: the drain at v, AC on the gate, the AC drain current read through VDX
- `RGD gd 0 1e9` — the Cgd copy: source open through 1 GΩ
- `.ac dec 10 100000 10000000` — 100 kHz to 10 MHz; C = Im(I)/(2πf) read at 1 MHz, series-equivalent as in the bipolar bench
- one such set per ladder voltage

**Extraction.** At each voltage, the 1 MHz series-equivalent capacitance of each copy. The grading
coefficient is the slope of log C against log (V + PB) between 1 and 10 V, PB taken as 1 V; the ratio
C(1 V)/C(10 V) is the simpler figure. Ciss and Crss at 10 and 15 V, VGS = 0, are the sheet's points.

**Outputs.**

- `ciss@{v}` (F): input capacitance at each voltage
- `crss@{v}` (F): reverse transfer capacitance
- `cgs@{v}` (F), `cgd@{v}` (F): the two junctions alone
- `crss_m`: grading coefficient of Crss between 1 and 10 V
- `ciss_1v_over_10v`: Ciss at 1 V over Ciss at 10 V

Curves: `Ciss` (ciss against v, log); `Crss` (crss against v, log); `Cgs` (cgs against v, log); `Cgd` (cgd against v, log).

**Card parameters that drive it:** CGS, CGD, PB, M, FC.

**A high value.** A ratio near 2 is a normal abrupt-ish junction; Ciss of 30 pF or more in a card of a
low-noise JFET costs the stage its noise advantage with a high-impedance source.

**A low value.** Zero is a card without CGS and CGD: the code is "absent" and every frequency-dependent
result of the model is meaningless.

**What it cannot tell.** The capacitance's dependence on drain current when the channel is open (Cgs
rises), which a level 1 card does not carry.

**Standard.** resembles the Ciss and Crss methods of MIL-STD-750-3 at 1 MHz, read as a meter reads a low-impedance capacitance

#### Transconductance against frequency and the gain-bandwidth figure (`jfet-frequency`)

Group `frequency` · analysis `ac` · engines qspice, ngspice, ltspice · symbols yfs(f), fT.

How far up in frequency the transconductance holds. A JFET has no transit-time parameter in SPICE; its
frequency limit is set entirely by the capacitances against the transconductance, and the figure of merit
gfs/2π(Cgs + Cgd) plays the role fT plays for a bipolar. Toshiba sheets draw |Yfs| against frequency; the
RF-JFET sheets (BF245, J310) print the figure directly. Here the magnitude of the forward transfer
admittance is swept to 1 GHz at each ladder current, and read where it has fallen by 3 dB; the common-source
bandwidth of a fixed stage is read too, because that is what an audio user compares with the real circuit.

**Circuit.** The gfs copies of `jfet-gm` swept to 1 GHz. A second deck is a common-source stage: VDD = 18 V,
the source self-biased by a resistor chosen from the transfer sweep for ID = IDSS/3 and bypassed, the drain
load chosen for VDS = 9 V, driven from 1 kΩ, swept 1 Hz to 10 MHz.

Drawing: DUT; VDS source; gate bias with AC; AC ammeter (yfs deck). Common-source stage: RD, RS bypassed, 1 kΩ source resistance, probe on the drain.

**Conditions.** {vds: 10, id_ladder: [0.0001, 0.001, 0.003, 0.01, idss], ac_sweep: {from: 1000, to: 1e+09, per_decade: 20, unit: Hz}, stage: {vdd: 18, id_fraction: 0.333, vds: 9, rs_in: 1000, sweep: {from: 1, to: 1e+07, per_decade: 20}}}

**The deck (QSPICE), line by line.**

- `VD0 d0 0 10` / `VG0 g0 0 DC {vgs} AC 1` / `JY0 d0 g0 0 DUT` — a yfs copy, one per ladder current
- `.ac dec 20 1000 1e9` — 1 kHz to 1 GHz
- `VDD vdd 0 18` / `RD vdd dc {rd}` / `RS s 0 {rs}` / `CS s 0 1000u` / `RIN in g 1000` / `VIN in 0 AC 1` / `JS dc g s DUT` — the stage deck
- `.ac dec 20 1 1e7` — the stage's sweep

**Extraction.** |yfs| at each frequency and current; the frequency at which it has fallen to 1/√2 of its
1 kHz value; the figure gfs/2π(Cgs + Cgd) computed from the 1 kHz gfs and the 10 V capacitances. For the
stage, the mid-band gain at 1 kHz, the −3 dB frequency and the input capacitance seen at 1 kHz (the Miller
figure).

**Outputs.**

- `yfs_3db@{id}` (Hz): frequency where |yfs| has fallen by 3 dB
- `ft_equiv@{id}` (Hz): gfs / 2π(Cgs + Cgd) at 10 V
- `stage_gain@1kHz`: voltage gain of the reference common-source stage
- `stage_f3db` (Hz): its −3 dB frequency
- `stage_cin@1kHz` (F): its input capacitance

Curves: `|yfs|, ID={id}` (yfs against f, log); `stage gain` (av against f, log). Shown first: |yfs|, ID = 1 mA.

**Card parameters that drive it:** CGS, CGD, PB, M, BETA, VTO, RS, RD.

**A high value.** An fT equivalent in the gigahertz for an audio JFET is a card with no capacitances
(see `jfet-capacitance`).

**What it cannot tell.** Package inductance and the real part's distributed gate resistance, which set
the RF limit; this is the die model alone.

**Standard.** resembles the |Yfs| vs f chart of Toshiba sheets; no test method

#### Voltage noise, current noise, the 1/f corner and NF (`jfet-noise`)

Group `noise` · analysis `noise` · engines qspice, ngspice · symbols en, in, NF.

The reason JFETs are chosen for the first stage. The voltage noise is the channel's thermal noise seen
through the transconductance, about √(4kT·0.67/gfs), so it falls as the bias current rises and is lowest at
IDSS; the current noise is the shot noise of the gate leakage, picoamperes' worth, which is why a JFET wins
against any bipolar when the source is a megohm. Below a corner the 1/f part rises, and in JFETs the corner
sits anywhere from 10 Hz to 10 kHz depending on the process; a 2SK170 at 1 kHz reads under 1 nV/√Hz. In a
card the voltage floor comes from BETA and the current; the 1/f part needs KF and AF, which most cards
leave at zero and then say nothing about the part's low-frequency noise; the current noise needs IS.

**Circuit.** A common-source stage at VDS = 10 V, the gate biased by a voltage source (from the transfer
sweep) for 100 µA, 300 µA, 1, 2, 3 mA and IDSS. The noise input is a voltage source in series with RG at the
gate; the output is the drain current through a sensing source. Two runs per current, RG = 0 and RG =
10 MΩ (the current noise of a JFET needs a large resistor to show above the voltage noise). A third run at
2 mA with RG = 1 MΩ gives a noise figure.

Drawing: DUT; VDS source 10 V; gate bias; noise source with RG; sensing in the drain. Differs from the netlist: the output is a current-controlled voltage source into 1 MΩ, as in the bipolar bench.

**Conditions.** {vds: 10, id_ladder: [0.0001, 0.0003, 0.001, 0.002, 0.003, idss], rg: [0, 1e+07], nf: {id: 0.002, rg: 1e+06, f: 1000}, band: [10, 15700], audio_band: [20, 20000], f_points: [10, 100, 1000, 10000, 100000], noise_sweep: {from: 1, to: 1e+06, per_decade: 20, unit: Hz}, temp_c: 25}

**The deck (QSPICE), line by line.**

- `VSENSE d dd 0` / `VD dd 0 10` — the sensing source and the drain supply
- `VGB gb 0 {vgs_for_id}` — the gate bias for the step; VIN rides on it
- `RG in g 0.001` — run 1: RG = 0 (1 mΩ), the voltage noise alone
- `RG in g 1e7` — run 2: 10 MΩ, adds in² × RG² and the resistor's own 4kT·RG
- `J1 d g 0 DUT` — the transistor, source grounded
- `H1 out 0 VSENSE 1000` / `RLOAD out 0 1meg` — the sensed current as a voltage
- `.noise V(out) VIN dec 20 1 1000000` — 1 Hz to 1 MHz, referred to VIN

**Extraction.** As in the bipolar bench: en from the RG = 0 run; in from the 10 MΩ run less en² and
4kT·RG; the corner where en is √2 times its 10 kHz value, "absent" when flat; NF at 1 kHz with RG = 1 MΩ;
the curves of NF and total noise against RS at 1 kHz and over 10 Hz to 15.7 kHz. Two figures no sheet prints
are added because they are what an audio user hears: the input-referred noise integrated over 20 Hz to
20 kHz in volts rms, flat and A-weighted, at each current. The ratio en(IDSS)/en(100 µA) at 10 kHz is the
square-root law check.

**Outputs.**

- `en@{f},{id}` (V/√Hz), `in@{f},{id}` (A/√Hz)
- `en_corner@{id}` (Hz): the 1/f corner, or absent
- `nf@1kHz,2mA,1M` (dB): noise figure at RG = 1 MΩ
- `en_ratio_idss_over_100uA`: en at IDSS over en at 100 µA, 10 kHz
- `vn_20_20k@{id}` (V): input-referred noise, 20 Hz to 20 kHz, RG = 0
- `vn_a_weighted@{id}` (V): the same, A-weighted

Curves: `en, ID={id}` (en against f, log); `in, ID={id}`; `en at {f}` (en against id, log); `NF, ID={id}` (nf against rs, lin); `NF wideband, ID={id}`; `VT, ID={id}` (vt against rs, log). Shown first: en, ID = 2 mA.

**Card parameters that drive it:** BETA, VTO, RS, IS, KF, AF, RD.

**A high value.** A corner above 1 kHz is a high KF; en above 3 nV/√Hz at IDSS for a low-noise part is a
BETA set too low or a large RS.

**A low value.** A flat spectrum to 1 Hz is KF = 0, code "absent" for the corner; in below 1 fA/√Hz is
IS at the simulator's floor.

**What it cannot tell.** Burst noise, the gate leakage's dependence on drain voltage (which raises in at
high VDS in real parts) and the part's own noise, which makers measure on a few samples.

**Standard.** resembles the spot noise methods (MIL-STD-750-3) and the en/f charts of 2SK170, LSK170 and 2N5457 sheets

#### IDSS, VGS(off) and the zero-temperature-coefficient point (`jfet-temperature`)

Group `temperature` · analysis `dc` · engines qspice, ngspice, ltspice · symbols IDSS(T), VGS(off)(T), VGS(0TC).

Two opposed drifts. The pinch-off voltage falls in magnitude by about 2 mV/K (the gate junction's
built-in potential), which would raise the current at a fixed gate voltage; the channel's mobility falls
with temperature, which lowers it. The two cancel at one drain current, roughly where VGS(off) − VGS is
0.6 V, and a stage biased there holds its current over temperature; above it the current falls with heat,
below it rises. Only one sheet in the sample (Nexperia BF245) draws ID against temperature, but it is the
curve a bias designer wants. A plain card gets both drifts from the defaults of the gate diode and from
nothing at all for the mobility (LTspice adds `VTOTC` and `BETATCE`; PSpice has `XTI` for the diode only),
so most models drift one way only.

**Circuit.** The transfer deck at VDS = 10 V run at −55, 25, 100, 125 and 150 °C.

Drawing: DUT; VDS source 10 V; swept VGS source; ammeter in the drain; a thermometer symbol.

**Conditions.** {vds: 10, vgs_sweep: {from: -10, to: 0.6, step: 0.005, unit: V}, temps_c: [-55, 25, 100, 125, 150], vgs_points_fraction: [0, 0.25, 0.5, 0.75]}

**The deck (QSPICE), line by line.**

- `.temp -55` — the first deck; 25 °C comes from the transfer deck; then 100, 125, 150
- `VT dt 0 10` / `VGS g 0 0` / `JT dt g 0 DUT` — the transfer copy
- `.dc VGS -10 0.6 0.005`

**Extraction.** IDSS and VGS(off) (10 nA) at each temperature; dVGS(off)/dT and the IDSS ratio 125/25 °C.
The zero-TC point is the gate voltage at which the 25 and 125 °C curves cross (interpolated), and the
drain current there; "absent" when they do not cross within the sweep. ID against temperature at VGS = 0,
VGS(off)/4, /2 and 3/4 is kept, the way the BF245 sheet draws it.

**Outputs.**

- `idss@{T}` (A), `vgs_off@{T}` (V)
- `dvgsoff_dt` (V/K): slope of VGS(off) between −55 and 150 °C
- `idss_125_over_25`
- `vgs_0tc` (V): gate voltage of zero temperature coefficient, or absent
- `id_0tc` (A): drain current at that point

Curves: `ID, {T}°C` (id against vgs, lin); `ID vs T, VGS={fraction}` (id against T, lin). Shown first: ID, T = all.

**Card parameters that drive it:** VTOTC, BETATCE, XTI, EG, IS, N.

**A high value.** An IDSS that rises with temperature by more than 10 % is a card with a VTO drift and no
mobility term: real JFETs at IDSS fall with heat.

**A low value.** No crossing at all, with IDSS fixed, is a card with no temperature dependence beyond the
gate diode: it will bias perfectly in simulation and drift in the real circuit.

**What it cannot tell.** Self-heating, and the leakage's doubling per 10 K, which is below the simulators'
floor at 25 °C and only shows above 100 °C.

**Standard.** resembles the "ID vs Tj" chart of Nexperia JFET sheets and IEC 60747-8 temperature characteristics

#### The analogue switch — turn-on, turn-off and charge injection (`jfet-switch`)

Group `switching` · analysis `tran` · engines qspice, ngspice, ltspice · symbols ton, toff, Qinj.

A JFET switch is driven from VGS = 0 (on) to below VGS(off) (off). Its times are set by how fast the gate
charges Ciss through the drive resistor, and its curse is the charge that the gate step pushes through Cgd
and Cgs into the signal path: the glitch a sample-and-hold or a muting circuit lives with. The switching
sheets (J111, 2N4391, Nexperia BF/J series) quote ton and toff at a fixed load and drive; here one fixed
fixture serves every model so that they can be compared.

**Circuit.** The transistor between a 0 V signal source (through 0 V, an ammeter) and a load of 1 kΩ and
10 kΩ to ground; the gate driven from 0 V to −10 V (and from 0 to −2·VGS(off), the model's own) through
1 kΩ, with 10 ns edges. The drain-source current and the load voltage are watched.

Drawing: DUT in series between source and RL; gate pulse through 1 kΩ; probe on the load.

**Conditions.** {rl: [1000, 10000], v_off: [-10, auto], rg: 1000, edge_s: 1e-08, t_on_s: 2e-06, t_after_s: 2e-06, max_step_s: 1e-10, temp_c: 25}

**The deck (QSPICE), line by line.**

- `VS s 0 0` — the signal source at 0 V: its current is the switched current
- `JW l g s DUT` — the switch, drain to the load
- `RL l 0 1000` — the load
- `RG in g 1000` / `VIN in 0 PWL(0 -10 1e-7 -10 1.1e-7 0 2.1e-6 0 2.11e-6 -10)` — the gate drive: off, on for 2 µs, off
- `.tran 1e-10 4.2e-6` — the transient

**Extraction.** ton and toff from the 10 % and 90 % crossings of the load voltage under a 1 V signal
run; the injected charge as the integral of the load current glitch at the turn-off edge with the signal
at 0 V; the on-resistance from the on-state voltage divider.

**Outputs.**

- `ton@{rl},{voff}` (s), `toff@{rl},{voff}` (s)
- `q_inj@{rl},{voff}` (C): charge injected into the load at turn-off
- `rds_on_switch` (Ω): on-resistance in the fixture

Curves: `Vload(t), RL={rl}, Voff={voff}` (v against t, lin). Shown first: RL = 1 kΩ, Voff = −10 V.

**Card parameters that drive it:** CGS, CGD, PB, M, BETA, VTO, RD, RS.

**A high value.** Injected charge above 10 pC is a large Cgd; toff in microseconds is a card whose
capacitances are far too large or whose VGS(off) is deep.

**A low value.** Zero injection is a card without capacitances.

**What it cannot tell.** The times with the sheet's own fixture; and body-effect-like behaviour, which a
JFET has none of.

**Standard.** resembles the switching-time fixtures of analogue-switch JFET sheets, simplified

#### A reference stage's harmonic distortion (model against model only) (`jfet-distortion`)

Group `distortion` · analysis `tran` · engines qspice, ngspice · symbols THD, HD2, HD3.

What the audio user wants from a JFET model and no sheet prints. The curvature of a JFET stage is the
square law itself — nearly pure second harmonic in a common-source stage, which is the "character" pedal
builders describe — tamed by source degeneration, plus the output conductance and the capacitances. Two
fixed stages: a common-source stage with partial degeneration, where the square law shows, and a source
follower, where it should nearly vanish and what remains is gos and the gate diode; both at a level the
device sets for itself (IDSS/3), so that models of the same part are compared on equal footing.

**Circuit.** Common source: VDD = 18 V, the source resistor chosen from the transfer sweep for ID =
IDSS/3, unbypassed, the drain resistor for VDS = 9 V, driven from 10 kΩ. Follower: the same bias, drain to
VDD, source load 10 kΩ to ground, driven from 10 kΩ. A probe run sets the input for 1 V peak out at 1 kHz;
ten cycles simulated, the last four analysed. The common-source stage is also driven to 3 V peak out to show
the gate-diode clipping.

Drawing: DUT; RD, RS; VDD 18 V; 1 kHz source through 10 kΩ; probe on the drain (or source).

**Conditions.** {vdd: 18, id_fraction: 0.333, vds: 9, rs_in: 10000, rl_follower: 10000, f: 1000, vout_peak: [1, 3], cycles: 10, analysed_cycles: 4, steps_per_cycle: 4096}

**The deck (QSPICE), line by line.**

- `VDD vdd 0 18` / `RD vdd d {rd}` / `RS s 0 {rs}` — the stage, RD and RS from the transfer sweep
- `RIN in g 10000` / `VIN in 0 SIN(0 {amp} 1000)` — the drive
- `J1 d g s DUT` — the transistor
- `.tran 2.44140625e-07 0.01 0 2.44140625e-07` — ten cycles of 1 kHz

**Extraction.** As in the bipolar bench: harmonics 2 to 10 by Goertzel over the last four cycles; THD, HD2,
HD3 per stage and level; the stage's gain.

**Outputs.**

- `thd_cs@{level}`, `hd2_cs@{level}`, `hd3_cs@{level}`: the common-source stage at 1 V and 3 V peak out
- `thd_sf`, `hd2_sf`, `hd3_sf`: the source follower at 1 V peak out
- `gain_cs`, `gain_sf`: the stages' gains

**Card parameters that drive it:** BETA, VTO, B, LAMBDA, RS, RD, IS, CGS, CGD.

**A high value.** Only against another model of the same part. A follower above 0.1 % at 1 V is a large
LAMBDA or a card that conducts at the gate early.

**A low value.** A common-source HD3 far below HD2 is the square law; HD3 above HD2 is a card with `B`
or a wrong exponent.

**What it cannot tell.** The distortion of any real circuit; it is a comparison between models.

**Standard.** none

#### Is there any breakdown, and what leaks (`jfet-breakdown`)

Group `breakdown` · analysis `dc` · engines qspice, ngspice, ltspice · symbols V(BR)GSS, V(BR)DGO, IDSS(off).

A plain JFET card has no breakdown: the gate-source junction reverse-biased to 100 V passes only its
saturation current, and a drain swept to 300 V with the gate below pinch-off sees nothing. The sheets quote
V(BR)GSS of 25 to 40 V (BF245, J201) and up to 60 V (2N4391); a model used in a high-voltage phantom-powered
or tube-hybrid stage will not fail where the part does. Documented here as an absence, as in the bipolar
bench, with the leakage below pinch-off read beside it.

**Circuit.** Gate to source reversed 0 to −100 V, drain open. Drain to gate 0 to 300 V, source open. Drain
to source 0 to 300 V with the gate held at 2·VGS(off) (the off-state leakage, ID(off)).

Drawing: DUT; swept source; 1 GΩ opens; ammeter. Differs from the netlist: three decks drawn as one.

**Conditions.** {vgs_sweep: {from: 0, to: -100, step: 0.1, unit: V}, vdg_sweep: {from: 0, to: 300, step: 1, unit: V}, vds_off_sweep: {from: 0, to: 300, step: 1, unit: V}, breakdown_current: 0.001, leakage_points: {igss: 20, id_off: 15}, temp_c: 25}

**The deck (QSPICE), line by line.**

- `VA sw ga 0` / `RDA da 0 1e9` / `JA da ga 0 DUT` / `.dc VSW 0 -100 0.1` — gate-source, drain open
- `VB sw db 0` / `RSB sb 0 1e9` / `JB db 0 sb DUT` / `.dc VSW 0 300 1` — drain-gate, source open
- `VC sw dc 0` / `VGC gc 0 {2*vgs_off}` / `JC dc gc 0 DUT` / `.dc VSW 0 300 1` — drain-source, gate off

**Extraction.** The first voltage at which the current passes 1 mA, else "absent" with the voltage
reached; IGSS at 20 V and ID(off) at 15 V, with a note below 10 pA.

**Outputs.**

- `vbr_gss` (V): gate-source breakdown, or absent
- `vbr_dgo` (V): drain-gate breakdown, or absent
- `igss@20V` (A), `id_off@15V` (A)

**Card parameters that drive it:** none in the standard card (IS and ISR only set the leakage); zener diodes inside a subcircuit where present.

**What it cannot tell.** Anything about the part's breakdown when the code is "absent".

**Standard.** resembles the V(BR)GSS and IGSS methods of MIL-STD-750-3

#### Do the three simulators agree? (`jfet-agreement`)

Group `dc` · analysis `derived` · engines qspice, ngspice, ltspice.

As `bjt-agreement`, over every output above. JFET cards are where dialects bite most: `M` versus `MJ`
for the grading coefficient, `B`, `VTOTC`, `BETATCE`, `ALPHA` and `VK`, `ISR` and `NR` are each read by
one or two of the three engines and silently dropped by the others, so a card that uses them agrees in DC
and disagrees in capacitance, temperature or gate current. The disagreeing measurement ids say which.

**Conditions.** {tolerances: [0.01, 0.05], floors: {F: 1e-16, s: 1e-12, A: 1e-14}}

**Outputs.** `agree_1pct`, `agree_5pct`, `odd_engine`, `disagreeing`, as in the bipolar bench.

**Standard.** none

### MOSFETs

#### Does the card load? (`mos-runs`)

Group `dc` · analysis `op` · engines qspice, ngspice, ltspice.

Whether each simulator reads the card and finds an operating point, and the first sanity figures: the
drain current with the gate fully on at a low drain voltage (what a switch does) and with the gate at a
logic level. A card can fail for the three bipolar reasons and a fourth of its own: a subcircuit whose body
diode or resistors use a dialect the engine lacks (a `VDMOS` card in an old ngspice, an `AKO` in LTspice).

**Circuit.** The transistor with its source grounded, the drain at 1 V, the gate at 10 V; a second copy
with the gate at 4.5 V; a third with the gate grounded and the drain at −1 V (the body diode forward).

Drawing: DUT; VDS source 1 V; VGS source 10 V (or 4.5 V); ammeter in the drain; a third copy reversed.

**Conditions.** {vds: 1, vgs: [10, 4.5], diode_vsd: 1, temp_c: 25}

**The deck (QSPICE), line by line.**

- `VD d 0 1` / `VG g 0 10` / `M1 d g 0 0 DUT` — the on-state copy (a four-terminal card has its body tied to the source; a subcircuit its three pins)
- `VD2 d2 0 1` / `VG2 g2 0 4.5` / `M2 d2 g2 0 0 DUT` — the logic-level copy
- `VD3 d3 0 -1` / `M3 d3 0 0 0 DUT` — the diode copy
- `.op`

**Extraction.** Exit status and log give the error class; when it runs, the three currents.

**Outputs.**

- `runs`, `error_class`
- `id_on@10V` (A): drain current at VGS = 10 V, VDS = 1 V (≈ 1 V / RDS(on))
- `id_on@4.5V` (A): at VGS = 4.5 V
- `is_diode@1V` (A): body-diode current at VSD = 1 V, or absent (no diode in the card)

**What it cannot tell.** That the model is right; agreement is the stronger fact.

**Standard.** none

#### Output characteristics, as a curve tracer draws them (`mos-tracer`)

Group `dc` · analysis `dc` · engines qspice, ngspice, ltspice · symbols ID(VDS), VGS.

Drain current against drain-source voltage, one trace per gate voltage. For a power MOSFET the traces
are nearly vertical at the origin (the on-resistance) and bend into saturation at VDS = VGS − Vth; the
sheets of every maker print this family to 5 or 10 V with gate steps of half a volt near threshold and of
volts above. Read at a glance: the slope at the origin, which is RDS(on) at that gate voltage; where the
knee sits; the spacing, which is the transconductance and its rise with gate drive; and the slope of the
flat part, which is the channel-length modulation `LAMBDA` (small in a power device, large in a short
small-signal one). A `VDMOS` card has a separate parameter for the triode region's shape (`mtriode`)
and the knee is where cards fitted from headline numbers go wrong.

**Circuit.** Copies of the transistor at the universal gate ladder (2, 2.5, 3, 3.5, 4, 4.5, 5, 6, 8, 10,
15 V) and at five "auto" steps: the gate voltages that gave 10 mA, 30 mA, 100 mA, 300 mA and 1 A at
VDS = 5 V in the transfer sweep, so that the family spans two decades of current whatever the model's
threshold and transconductance. One source sweeps every
drain from 0 to 10 V in 10 mV steps; a second deck repeats it to 30 V in 50 mV steps.

Drawing: DUT; swept VDS source; gate voltage source at the step; ammeter in the drain. Differs from the netlist: the copies are drawn as one transistor with a stepped gate.

**Conditions.** {vgs_ladder: [2, 2.5, 3, 3.5, 4, 4.5, 5, 6, 8, 10, 15], auto: {from: mos-transfer, id_bottom: 0.01, id_top: 1, steps: 5, vds: 5}, vds_sweep: {from: 0, to: 10, step: 0.01, unit: V}, vds_sweep_wide: {from: 0, to: 30, step: 0.05, unit: V}, temp_c: 25}

**The deck (QSPICE), line by line.**

- `VK1 sw dk1 0` — reads the first copy's ID
- `VGK1 gk1 0 {vgs_k}` — its gate at the step
- `MK1 dk1 gk1 0 0 DUT` — the copy, source and body grounded
- `VSW sw 0 0` / `.dc VSW 0 10 0.01` — the sweep
- the auto steps are the gate voltages that gave 10 mA, 30 mA, 100 mA, 300 mA and 1 A at VDS = 5 V in the transfer sweep

**Extraction.** Each trace on the grid, both sweeps. The chord resistance at VDS = 0.1 V of each universal
trace (an RDS(on) reading at low current), the knee of each auto trace (90 % of its 10 V value), the slope
of the flat part between 5 and 10 V as output conductance.

**Outputs.**

- `vgs_auto@{k}` (V): the five auto gate voltages
- `rds_chord@0.1V,{vgs}` (Ω): VDS/ID at 0.1 V for each universal step, or n/a below threshold
- `vds_knee@auto{k}` (V)
- `gos_flat@auto{k}` (S): dID/dVDS between 5 and 10 V

Curves: `ID, VGS={vgs}` (id against vds, lin, to 10 V); `ID wide, VGS={vgs}` (to 30 V); `ID, auto k`. Drawn together, as a family. Shown first: auto, 0–10 V.

Beside the point under the cursor: P (W), VDS × ID; rDS (Ω), the chord VDS/ID; ro (Ω), the local slope.

**Card parameters that drive it:** VTO, KP (or BETA), LAMBDA, RD, RS, mtriode, Ksubthres, THETA (level 3), GAMMA.

**A high value.** A flat part that climbs steeply is a large LAMBDA — normal in a small-signal part,
wrong in a model of a 100 A switch. A knee that sits at several volts at modest current is a large RD.

**A low value.** Perfectly flat traces are LAMBDA = 0 and an infinite output resistance.

**What it cannot tell.** Thermal droop and breakdown; the traces beyond the part's VDS rating are the
model's, not a transistor's.

**Standard.** resembles the output characteristics every MOSFET sheet prints; no test method

#### Transfer characteristic — ID against VGS at fixed VDS, and the threshold (`mos-transfer`)

Group `dc` · analysis `dc` · engines qspice, ngspice, ltspice · symbols Vth, gfs, ID(VGS).

The curve a MOSFET model is fitted on: drain current against gate voltage with the drain held. On a log
current axis it has two parts: below threshold the current rises exponentially (60 to 100 mV per decade
at 25 °C), above it as a power of (VGS − Vth) — square in a long-channel device, nearer linear in a short
or velocity-saturated one, which is the difference between a lateral audio MOSFET and a trench switch.
Three definitions of the threshold are in use on the sheets (ID = 20 µA at Infineon, 250 µA at ST and
Vishay, 1 mA at Nexperia) and a fourth in the card (`VTO`, the extrapolated one); all four are read. The
drain voltage is fixed at the three values the sheets use (6 V Infineon, 15 V most, 25 V onsemi/Fairchild)
plus 1 V for the linear region. A level 1 card has no subthreshold current at all and simply stops at
VTO; level 3 and `VDMOS` (`Ksubthres`) carry a tail.

**Circuit.** Four copies, sources and bodies grounded, drains at 1, 6, 15 and 25 V. One source sweeps every
gate from −2 to +15 V in 10 mV steps; each drain current is read through its supply. A fifth copy is
diode-connected (drain tied to gate) and swept the same way, because that is how the sheets define Vth.

Drawing: DUT; VDS source (1, 6, 15 or 25 V); swept VGS source; ammeter in the drain; a fifth copy with drain tied to gate.

**Conditions.** {vgs_sweep: {from: -2, to: 15, step: 0.01, unit: V}, vds: [1, 6, 15, 25], vth_currents: [2e-05, 0.00025, 0.001], id_ladder: [1e-06, 1e-05, 0.0001, 0.001, 0.01, 0.1, 1, 10, 100], vgs_read: [2, 2.5, 3, 4, 4.5, 5, 6, 10], temp_c: 25}

**The deck (QSPICE), line by line.**

- `VT1 dt1 0 15` — the 15 V copy, the one the summary values come from; VT0, VT2, VT3 at 1, 6, 25 V
- `VGS g 0 0` / `.dc VGS -2 15 0.01` — the gate drive, swept
- `MT1 dt1 g 0 0 DUT` — the 15 V copy
- `VTD dtd g 0` / `MTD dtd g 0 0 DUT` — the diode-connected copy: its drain tied to the gate through an ammeter
- read: ID per copy; Vth where ID crosses 20 µA, 250 µA, 1 mA on the diode-connected copy and on the 15 V copy

**Extraction.** Vth at the three currents, diode-connected and at 15 V; the extrapolated Vth as the
intercept of √ID against VGS fitted between 10 and 100 mA at 15 V (the square-law region); the subthreshold
slope in mV/decade between 1 µA and 100 µA, "absent" where the card has no current below VTO; the exponent
of ID against (VGS − Vth) between 100 mA and the top current. ID at each read gate voltage and VGS at each
ladder current, at every VDS. gfs is the derivative, published in `mos-gm`.

**Outputs.**

- `vth@{current},diode` (V), `vth@{current},15V` (V)
- `vth_extrapolated` (V)
- `sub_slope` (V/decade): the subthreshold slope, or absent
- `n_fit`: exponent of the power law above threshold
- `id@{vgs},{vds}` (A), `vgs@{id},{vds}` (V)
- `id_25v_over_6v@1A`: ID at 25 V over ID at 6 V, VGS for 1 A (LAMBDA read another way)

Curves: `ID, VDS={vds}` (id against vgs, lin); `ID log, VDS={vds}` (id against vgs, log); `ID diode-connected` (log). Shown first: VDS = 15, lin.

Beside the point under the cursor: gfs (S), dID/dVGS; P (W), VDS × ID.

**Card parameters that drive it:** VTO, KP, GAMMA, PHI, THETA, Ksubthres, LAMBDA, RS, RD, NFS.

**A high value.** An exponent near 2 in a model of a trench power MOSFET is a long-channel fit: its
gfs at high current will be too high. A subthreshold slope above 120 mV/decade is a card fitted for a
soft turn-on.

**A low value.** No subthreshold current at all is a level 1 card: a switch that turns off exactly at
VTO, and a class-AB stage whose crossover region does not exist.

**What it cannot tell.** Where the part's threshold sits in its production spread (1 to 3 V on most
sheets); the card is one point.

**Standard.** resembles the transfer characteristics and VGS(th) methods of every MOSFET sheet (JEDEC JESD24-x, MIL-STD-750-3)

#### On-resistance against drain current, gate voltage and the drive floor (`mos-rdson`)

Group `high-current` · analysis `dc` · engines qspice, ngspice, ltspice · symbols RDS(on).

The headline number of a power MOSFET, and the one a card is most often fitted to at exactly one point.
It is not one number: it rises with current (the channel leaves the linear region as ID approaches the
saturation current for that VGS), falls as the gate is driven harder towards a floor set by the ohmic
parts (`RD` + `RS` + the fully open channel), and nearly doubles between 25 and 150 °C. The sheets draw it
against ID at two or three gate voltages (Infineon, Nexperia) and against VGS at one current (Nexperia,
Fairchild). Here the drain current is forced and the drain voltage read, so that the curve reaches the
rated current and beyond.

**Circuit.** One copy per gate voltage of the ladder (2.5, 3, 4, 4.5, 5, 6, 8, 10, 15 V), the gate held;
the drain current forced by the behavioural dial from 1 mA to 100 A with a clamp diode to a 30 V rail,
so that a copy that cannot pass the current is caught; VDS read. A second deck holds the current at
100 mA, 1 A and 10 A and sweeps the gate 0 to 15 V.

Drawing: DUT; forced drain current with clamp to 30 V; gate source at the step; voltmeter drain to source.
Differs from the netlist: the nine gate steps run as copies in one deck.

**Conditions.** {vgs_ladder: [2.5, 3, 4, 4.5, 5, 6, 8, 10, 15], id_sweep: {from: 0.001, to: 100, per_decade: 20, unit: A}, id_ladder: [0.001, 0.01, 0.1, 1, 2, 5, 10, 20, 50, 100], clamp_v: 30, vgs_sweep_at_id: [0.1, 1, 10], temp_c: 25}

**The deck (QSPICE), line by line.**

- `BR0 0 dr0 I=exp(2.302585092994046*V(x))` — the drain drive: 10 to the power of the dial, pulled out of the drain
- `DCL0 dr0 cl0 DCLMP` / `VCL0 cl0 0 30` — the clamp: what the transistor cannot pass goes to 30 V
- `VGR0 gr0 0 10` — the gate at the step
- `MR0 dr0 gr0 0 0 DUT` — the copy
- `.dc VX -3 2 0.05` — the dial: 1 mA to 100 A at twenty points per decade
- read: RDS(on) = V(dr0)/ID where the clamp is off and VDS < VGS − Vth (linear region)

**Extraction.** RDS(on) at each ladder current and gate voltage where the copy sat below the clamp and
in its linear region; "n/a" where it saturated (the current exceeds what the gate allows). The floor is
RDS(on) at 10 V and the lowest current; the slope with current is RDS(on) at the rated-current proxy (the
highest ladder step that still conducts) over the floor. From the gate sweep, RDS(on) against VGS at
three currents and the gate voltage at which it is within 10 % of its 15 V value.

**Outputs.**

- `rdson@{id},{vgs}` (Ω)
- `rdson_floor@10V` (Ω): at 10 V and 1 mA, essentially RD + RS + channel
- `rdson_slope@10V`: RDS(on) at the top conducting current over the floor
- `rdson_4v5_over_10v@1A`: the logic-level penalty
- `vgs_rdson_110pct@{id}` (V): gate voltage where RDS(on) is 1.1 × its 15 V value

Curves: `RDS(on), VGS={vgs}` (rdson against id, log); `RDS(on) vs VGS, ID={id}` (rdson against vgs, lin). Shown first: RDS(on), VGS = 10.

Beside the point under the cursor: P (W), RDS(on) × ID²; VDS (V), the on-state drop.

**Card parameters that drive it:** RD, RS, KP, VTO, THETA, Rds (VDMOS), mtriode.

**A high value.** A slope above 1.5 at 10 V is a card whose channel saturates near the rated current (KP
too small); a 4.5 V/10 V ratio above 2 is a threshold set high or a small KP.

**A low value.** A floor of zero is a card with RD = RS = 0 and a very large KP: its switch dissipates
nothing. A slope of exactly 1 to 100 A is the same card.

**What it cannot tell.** The temperature rise at the current, which doubles the real figure; see
`mos-temperature`.

**Standard.** resembles the RDS(on) methods of JEDEC JESD24-x and MIL-STD-750-3, pulsed

#### Transconductance and output conductance against drain current (`mos-gm`)

Group `dc` · analysis `ac` · engines qspice, ngspice, ltspice · symbols gfs, gos.

gfs sets the gain of a stage and, in a switch, how fast the current follows the gate during a
transition; the sheets draw it against ID at VDS = 15 V (ST, Vishay) and quote one value at the rated
current. For a square-law device it rises with √ID; in a real power MOSFET it goes nearly linear with ID
at low current (subthreshold) and saturates at high current (mobility degradation, `THETA`), which is
where a model fitted at one point misleads. gos is the output conductance, read as for the JFET, and is
what a MOSFET current source or cascode is limited by.

**Circuit.** As `jfet-gm`: copies at the ladder currents with the gate biased from the transfer sweep and
1 V of AC, VDS = 6 and 15 V, read at 1 kHz; gos from drain-driven copies and from a swept-VDS family at
four fixed currents.

Drawing: DUT; VDS source; gate bias with AC; AC ammeter in the drain; gos copies.

**Conditions.** {vds: [6, 15], id_ladder: [0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1, 3, 10, 30, 100], gos_vds_sweep: {from: 0, to: 30, step: 0.05, unit: V}, gos_id: [0.01, 0.1, 1, 10], f: 1000}

**The deck (QSPICE), line by line.**

- `VD0 d0 0 15` / `VG0 g0 0 DC {vgs} AC 1` / `MG0 d0 g0 0 0 DUT` — a gfs copy per ladder current
- `.ac dec 10 100 10000` — read at 1 kHz
- `VDO0 do0 0 DC 15 AC 1` — a gos copy, the gate held

**Extraction.** gfs and gos at each ladder current and VDS; gfs/√ID at 100 mA and at 10 A (its fall is
THETA at work); the intrinsic gain gfs/gos at 100 mA; the equivalent Early voltage ID/gos − VDS at 15 V,
"absent" above 10 000 V.

**Outputs.**

- `gfs@{id},{vds}` (S), `gos@{id},{vds}` (S)
- `gfs_over_sqrt_id@{id}` (S/√A)
- `av_intrinsic@100mA`, `va_equiv@{id}` (V)

Curves: `gfs, VDS={vds}` (gfs against id, log); `gos, VDS={vds}`; `gos vs VDS, ID={id}`. Shown first: gfs, VDS = 15.

**Card parameters that drive it:** KP, VTO, THETA, LAMBDA, RS, Ksubthres.

**A high value.** gfs still rising as √ID at 100 A is a card without THETA (level 1): it overstates the
gain and the switching speed at rated current.

**A low value.** gos of zero is LAMBDA = 0 (code "absent" for VA).

**What it cannot tell.** gfs at the sheet's pulsed, self-heated condition; and the 1 MHz value.

**Standard.** resembles the forward transconductance method (JEDEC JESD24-x, MIL-STD-750-3) at 1 kHz

#### Ciss, Coss, Crss against drain voltage, and against gate voltage (`mos-capacitance`)

Group `capacitance` · analysis `ac` · engines qspice, ngspice, ltspice · symbols Ciss, Coss, Crss.

The three capacitances every MOSFET sheet draws against VDS at VGS = 0, 1 MHz, on a log axis from
0.1 V to the rating. Ciss = Cgs + Cgd is nearly flat (the oxide); Coss = Cds + Cgd and Crss = Cgd fall by
one to two decades as the drain depletes, and the shape of that fall decides switching loss, the Miller
plateau and, in a follower output stage, the distortion at 20 kHz. Nexperia also draws Ciss and Crss
against VGS at low VDS, where the gate oxide capacitance takes over as the channel forms. A level 1 or 3
card has only the overlap terms (`CGSO`, `CGDO`, `CGBO`) and the body-diode junction (`CBD`): its Crss is
constant with voltage, which is wrong by a decade; a `VDMOS` card has the `Cgdmax/Cgdmin/a` law for Crss
and gets it right; subcircuit models add a voltage-dependent capacitor.

**Circuit.** Ciss: the gate driven with 1 V of AC at VGS = 0, the drain held at the bias through a large
inductor (AC open), source grounded. Coss: the drain driven with AC, gate and source grounded. Crss: AC on
the gate, the AC drain current read with the drain held. Copies at thirteen drain voltages from 0.1 to
300 V share one run. For the VGS view, copies at VDS = 0 with the gate biased 0 to 10 V.

Drawing: DUT; bias and AC sources; AC ammeters; three copies per voltage. Differs from the netlist: the copies run in one deck.

**Conditions.** {vds_ladder: [0.1, 0.5, 1, 2, 5, 10, 15, 20, 25, 30, 50, 100, 200, 300], vgs_ladder_at_vds0: [0, 1, 2, 3, 4, 5, 6, 8, 10], f: 1e+06, ac_sweep: {from: 100000, to: 1e+07, per_decade: 10, unit: Hz}, temp_c: 25}

**The deck (QSPICE), line by line.**

- `VDI di 0 {v}` / `LDI di dio 1` / `VGI gi 0 AC 1` / `MI dio gi 0 0 DUT` — the Ciss copy: the drain fed through 1 H, the gate driven
- `VDO do 0 DC {v} AC 1` / `MO do 0 0 0 DUT` — the Coss copy: the drain driven, gate grounded
- `VDR dr 0 {v}` / `VGR gr 0 AC 1` / `MR dr gr 0 0 DUT` — the Crss copy: the AC drain current through VDR over the gate drive
- `.ac dec 10 100000 10000000` — read at 1 MHz, series-equivalent
- one set per drain voltage; a second deck at VDS = 0 steps the gate for the VGS view

**Extraction.** The three capacitances at each voltage; Crss(1 V)/Crss(25 V) and Coss(1 V)/Coss(25 V) as
the shape figures; Qoss and Eoss at 25 V and at 100 V by integrating Coss over voltage (the sheets of
superjunction and GaN parts print both); the Miller ratio Crss/Ciss at 25 V. From the VGS view, Ciss at
VGS = 10 V over Ciss at 0 V (the oxide step).

**Outputs.**

- `ciss@{v}` (F), `coss@{v}` (F), `crss@{v}` (F)
- `crss_1v_over_25v`, `coss_1v_over_25v`
- `qoss@{v}` (C), `eoss@{v}` (J): at 25 and 100 V
- `miller_ratio@25V`: Crss/Ciss
- `ciss_10v_over_0v@vds0`: the gate-voltage dependence

Curves: `Ciss` (ciss against vds, log); `Coss`; `Crss`; `Ciss vs VGS` (ciss against vgs, lin, at VDS = 0); `Crss vs VGS`; `Eoss` (eoss against vds, log). Drawn together, as a family: Ciss, Coss, Crss against VDS. Shown first: the family.

**Card parameters that drive it:** CGSO, CGDO, CGBO, CBD, CBS, PB, MJ, Cgdmax, Cgdmin, a, Cgs, Cjo, m, Vj (VDMOS), TOX.

**A high value.** Crss(1 V)/Crss(25 V) near 1 is a constant Miller capacitance: a level 1 card, whose
switching waveforms and plateau will be wrong.

**A low value.** Zero everywhere is a card with no capacitance (code "absent"); a Coss that does not fall
is a missing CBD.

**What it cannot tell.** Capacitances with the channel conducting (the sheets take them at VGS = 0), and
the non-quasi-static effects at the switching edge.

**Standard.** resembles the Ciss/Coss/Crss methods of JEDEC JESD24-x at 1 MHz, read as a meter reads a low-impedance capacitance

#### Gate charge — VGS against Qg at constant gate current (`mos-gate-charge`)

Group `gate-charge` · analysis `tran` · engines qspice, ngspice, ltspice · symbols Qg, Qgs, Qgd, Vplateau.

The curve a gate driver is sized from. A constant current into the gate makes the gate voltage climb;
it climbs to the threshold (Qgs(th)), on to the plateau (Qgs) where the drain starts to fall, holds there
while Cgd is discharged by the whole drain swing (Qgd, the Miller charge), and climbs again to the drive
voltage (Qg total). The plateau voltage is Vth plus what the transconductance needs for the load current.
The sheets fix the load current near the rating and the supply at a fraction of the rating that differs
by maker (Nexperia 40 and 63 %, Infineon 20 and 80 %, ST 80 %, Vishay 20 and 80 %); here three universal
supplies and three currents are run so that any sheet's point is bracketed. Qgd/Qgs(th) is kept as the
parasitic-turn-on figure of a half-bridge.

**Circuit.** A constant current of 1 mA into the gate (10 mA for the two highest load currents); the drain
fed from the supply through an ideal current source of the load current with a clamp diode to the supply,
so that the drain sits at the rail until the transistor takes the current and then falls; source grounded.
The gate voltage against time is the charge curve (Q = IG × t).

Drawing: DUT; gate current source; load current source with clamp diode to VDD; probe on the gate and the drain.

**Conditions.** {ig: [0.001, 0.01], id_ladder: [0.1, 1, 10, 50], vdd_ladder: [10, 30, 100, 300], vgs_end: 12, vgs_read: [4.5, 10], max_step_s: 1e-09, temp_c: 25}

**The deck (QSPICE), line by line.**

- `IG 0 g 0.001` — the gate current, 1 mA
- `IL vdd d 1` / `DCL d vdd DCLMP` / `VDD vdd 0 30` — the load: 1 A pulled from the drain, caught at 30 V until the transistor conducts
- `M1 d g 0 0 DUT` — the transistor
- `.tran 1e-9 {12/0.001*cgs_guess}` — long enough for the gate to reach 12 V
- one deck per load current and supply

**Extraction.** From VGS(t): Qgs(th) at Vth (from `mos-transfer`), Qgs where the slope first falls below
half its initial value (plateau start), Qgd as the plateau's length, Qg at 4.5 and at 10 V, Vplateau as
the plateau's mean voltage, Qsw = Qgs − Qgs(th) + Qgd. A deck whose drain never fell (the gate reached
12 V with the clamp still conducting: the current is above what the card can pass) is "n/a".

**Outputs.**

- `qgs_th@{id},{vdd}` (C), `qgs@{id},{vdd}` (C), `qgd@{id},{vdd}` (C)
- `qg@4.5V,{id},{vdd}` (C), `qg@10V,{id},{vdd}` (C)
- `vplateau@{id},{vdd}` (V)
- `qgd_over_qgsth@1A,30V`: the parasitic-turn-on ratio

Curves: `VGS vs Qg, ID={id}, VDD={vdd}` (vgs against q, lin). Shown first: ID = 1 A, VDD = 30 V.

Beside the point under the cursor: VDS (V), the drain voltage at that charge; t (s).

**Card parameters that drive it:** CGSO, CGDO, Cgdmax, Cgdmin, a, Cgs, VTO, KP, RG.

**A high value.** A Qgd/Qgs(th) above 1.5 is a part prone to parasitic turn-on in a half-bridge; a
plateau of 7 V is a high threshold or a low gfs.

**A low value.** No plateau at all is a card with constant Cgd (level 1): the curve is a straight line
and the Miller charge does not exist.

**What it cannot tell.** The gate charge with the real driver's impedance and loop inductance.

**Standard.** resembles the gate charge method of JEDEC JESD24-2 at constant gate current

#### td(on), tr, td(off) and tf in a resistive-load switch, and Eon/Eoff clamped-inductive (`mos-switching`)

Group `switching` · analysis `tran` · engines qspice, ngspice, ltspice · symbols td(on), tr, td(off), tf, Eon, Eoff.

The four times every MOSFET sheet quotes at one point (VDD, ID, RG, VGS) and draws against ID or RG. In
a MOSFET there is no stored charge, so the times are the gate charging through RG: td(on) to threshold, tr
across the plateau (the Miller charge against RG), td(off) back to the plateau, tf across it again. A
model with the wrong Crss shape gets tr and tf wrong by the same factor. A second fixture, the clamped
inductive load that converter sheets use, gives the switching energies Eon and Eoff, which are what a
designer actually loses; SiC and GaN sheets draw them against ID, RG and T.

**Circuit.** Resistive: VDD of 10 and 30 V through RL = VDD/ID, the gate driven 0 to 10 V (and 0 to
4.5 V) through RG of 4.7, 10 and 25 Ω, edges of 2 ns, 2 µs on, scaled to ten currents from 10 mA to 10 A.
Clamped inductive: an inductor from VDD to the drain large enough to hold the current flat over the pulse,
an ideal diode across it, the current established by a first pulse and the switching read on the second;
Eon and Eoff as the integral of VDS × ID over the edges.

Drawing: DUT; VDD; RL; gate pulse through RG; probe on the drain (resistive). Inductor with freewheeling diode to VDD (inductive).

**Conditions.** {vdd: [10, 30], id_ladder: [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10], rg: [4.7, 10, 25], v_on: [10, 4.5], edge_s: 2e-09, t_on_s: 2e-06, t_after_s: 2e-06, max_step_s: 1e-10, inductive: {vdd: 30, id: [1, 10], rg: 10, l_h: 0.001}, temp_c: 25}

**The deck (QSPICE), line by line.**

- `VDD vdd 0 30` / `RL vdd d 30` — the supply and the load (30 Ω in the 1 A deck)
- `VIN in 0 PULSE(0 10 1e-7 2e-9 2e-9 2e-6 1)` / `RG in g 10` — the gate drive through RG
- `M1 d g 0 0 DUT` — the transistor
- `.tran 1e-10 4.2e-6` — the transient
- inductive deck: `L1 vdd d 1m` / `DFW d vdd DIDEAL` in place of RL, two pulses

**Extraction.** td(on) from the gate's 10 % to ID at 10 %; tr 10 to 90 % of ID (the sheets use VDS 90 to
10 %, published too); td(off) from the gate's fall to ID at 90 %; tf 90 to 10 %. Eon and Eoff from the
inductive deck. A step whose drain never fell below 10 % of VDD did not switch, and is reported by how far
it got.

**Outputs.**

- `td_on@{id},{vdd},{rg},{von}` (s), `tr@…` (s), `td_off@…` (s), `tf@…` (s)
- `on@…`: how far the drain fell, 1.0 = fully on
- `eon@{id},{rg}` (J), `eoff@{id},{rg}` (J): clamped inductive at 30 V

Curves: `VDS(t), ID={id}, VDD={vdd}, RG={rg}` (vds against t, lin); `td(on), tr, td(off), tf vs ID` (t against id, log, at each VDD, RG); `t vs RG, ID=1A`; `Eon, Eoff vs ID`. Shown first: VDS(t), ID = 1 A, VDD = 30 V, RG = 10 Ω.

**Card parameters that drive it:** CGSO, CGDO, Cgdmax, Cgdmin, a, RG, VTO, KP, RD.

**A high value.** tr that does not shrink when RG falls from 25 to 4.7 Ω is a card with a large internal RG
or a drain-side time constant.

**A low value.** tr and tf of nanoseconds at 10 A with RG = 25 Ω is a card with no Crss: its switching
loss will be understated by an order of magnitude.

**What it cannot tell.** The times with the sheet's own fixture, package inductance, the driver's own
impedance; transients differ by up to 1 % between simulators.

**Standard.** resembles the resistive switching time method of JEDEC JESD24-x and the clamped inductive fixture of converter data sheets, simplified

#### The body diode — forward drop, third-quadrant conduction and reverse recovery (`mos-body-diode`)

Group `body-diode` · analysis `dc` · engines qspice, ngspice, ltspice · symbols VSD, IS, trr, Qrr.

Every vertical MOSFET carries a diode from source to drain. Its forward drop (0.7 to 1.2 V) is the
voltage the freewheeling current costs in a bridge, and with the channel also on (VGS = 10 V) the
current splits between channel and diode — the third quadrant, which the sheets of modern parts draw as
IS against VSD at several VGS and which is where a class-AB output stage's idle current crosses over.
Its reverse recovery, trr and Qrr, is the loss and the ringing of every hard-switched bridge; the sheets
quote them at IF = IS and di/dt = 100 A/µs and draw them against di/dt. In a card the diode is the
`IS`/`N`/`RS` of the MOS body junction (level 1/3), or a separate diode with `TT` in a `VDMOS` card or a
subcircuit; a card without `TT` has a diode that recovers in zero time, which no silicon diode does.

**Circuit.** Forward: the drain current forced negative (source to drain) by the behavioural dial from
1 µA to 100 A at VGS = 0, VSD read; copies at VGS = 4.5 and 10 V for the third quadrant. Recovery: a
transient with the diode carrying IF from an inductor, then commutated by an ideal switch at a di/dt set
by a series inductor and a 30 V supply; three di/dt values.

Drawing: DUT reversed; forced source current; voltmeter source to drain (forward). Inductor, 30 V, ideal switch (recovery).

**Conditions.** {is_sweep: {from: 1e-06, to: 100, per_decade: 20, unit: A}, vgs: [0, 4.5, 10], is_ladder: [0.001, 0.01, 0.1, 1, 10, 50, 100], recovery: {if: [1, 10], didt_a_per_us: [100, 200, 400], vr: 30}, temp_c: 25}

**The deck (QSPICE), line by line.**

- `BS 0 s I=exp(2.302585092994046*V(x))` — the source current forced
- `MD 0 g s s DUT` / `VG g s 0` — the transistor with its drain grounded, the gate at the source
- `.dc VX -6 2 0.05` — 1 µA to 100 A
- recovery deck: `L1 vr s {l}` / `SW s 0 ctrl 0 SWIDEAL` / `VR vr 0 30` — the current steered through the diode and commutated

**Extraction.** VSD at each ladder current and VGS; the diode's IS and n fitted between 1 mA and 100 mA at
VGS = 0; the current at which the channel carries half the total at VGS = 10 V (the crossover). From the
recovery deck: trr (from the zero crossing to 10 % of Irrm on the recovery), Qrr (the integral), Irrm, and
the softness factor; "absent" when the recovery current never exceeds 1 % of IF (no TT).

**Outputs.**

- `vsd@{is},{vgs}` (V)
- `is_diode` (A), `n_diode`
- `is_crossover@10V` (A): the current where channel and diode share equally
- `trr@{if},{didt}` (s), `qrr@…` (C), `irrm@…` (A), `softness@…`

Curves: `IS vs VSD, VGS={vgs}` (is against vsd, log); `trr, Qrr, Irrm vs di/dt, IF={if}`; `I(t) recovery, IF={if}, di/dt={didt}`. Shown first: IS vs VSD, VGS = 0.

**Card parameters that drive it:** IS, N, RS, Rb, Cjo, TT (VDMOS/diode), JS, PB.

**A high value.** VSD above 1.3 V at 10 A is a large Rb; Qrr in microcoulombs is a TT set for a
standard-recovery diode.

**A low value.** A recovery that is absent is TT = 0, the usual case in level 1/3 cards; VSD of a plain
junction at 100 A with no series resistance is Rb = 0.

**What it cannot tell.** The recovery's temperature dependence (the diode's TT does not scale in SPICE),
and the snappiness the real part shows, which depends on the doping profile no card carries.

**Standard.** resembles the source-drain diode forward voltage and reverse recovery methods of JEDEC JESD24-x

#### Threshold, RDS(on), gfs and the body diode at −55 to 175 °C, and the zero-TC point (`mos-temperature`)

Group `temperature` · analysis `dc` · engines qspice, ngspice, ltspice · symbols dVth/dT, RDS(on)(T), VGS(0TC).

Three drifts. The threshold falls by 4 to 7 mV/K, which raises the current at a fixed gate voltage; the
mobility falls, which lowers it and nearly doubles RDS(on) between 25 and 150 °C (the positive temperature
coefficient that lets MOSFETs share current when paralleled as switches); the body diode's drop falls by
about 2 mV/K. The first two cancel at one current, the zero-temperature-coefficient point, below which a
MOSFET's current rises with heat (thermal runaway in linear mode, the reason class-AB stages biased below
it need compensation) and above which it falls. The sheets draw Vth against T and RDS(on) against T
normalised; none draws the zero-TC point, though every output-stage designer bisects it from the
transfer family. In a card the threshold drift is `TCV`/`VTOTC` or the physics of level 3; the mobility
drift is `BEX`/`KPTC` or absent, in which case the model has no positive RDS(on) coefficient and no
zero-TC point.

**Circuit.** The transfer deck (VDS = 15 V and the diode-connected copy), the RDS(on) deck at VGS = 10
and 4.5 V, and the body-diode deck at VGS = 0, run at −55, 25, 100, 125, 150 and 175 °C.

Drawing: DUT; the three fixtures; a thermometer symbol.

**Conditions.** {temps_c: [-55, 25, 100, 125, 150, 175], vds: 15, vth_currents: [2e-05, 0.00025, 0.001], rdson_vgs: [4.5, 10], rdson_id: [1, 10], vsd_is: [1, 10]}

**The deck (QSPICE), line by line.**

- `.temp -55` — the first deck; then 100, 125, 150, 175; 25 °C from the base decks
- the transfer, RDS(on) and body-diode copies as above

**Extraction.** Vth (1 mA, diode-connected) at each temperature and its slope between −55 and 175 °C;
RDS(on) at 10 V and 1 A at each temperature over 25 °C, and the exponent of its power-law fit against
absolute temperature; gfs at 1 A at each temperature over 25 °C; VSD at 1 A and its slope. The zero-TC
point is where the 25 and 150 °C transfer curves cross, as gate voltage and drain current; "absent" when
they do not cross (no mobility drift in the card).

**Outputs.**

- `vth@1mA,{T}` (V), `dvth_dt` (V/K)
- `rdson_{T}_over_25@10V,1A`, `rdson_t_exponent`
- `gfs_{T}_over_25@1A`
- `vsd@1A,{T}` (V), `dvsd_dt` (V/K)
- `vgs_0tc` (V), `id_0tc` (A): the zero-temperature-coefficient point, or absent

Curves: `ID, {T}°C` (id against vgs, lin and log); `RDS(on) normalised` (ratio against T, lin); `Vth` (vth against T, lin); `IS vs VSD, {T}°C`. Shown first: ID, T = all.

**Card parameters that drive it:** TCV, VTOTC, BEX, KPTC, UO, XTI, EG, IS (diode), level-3 physics (TOX, NSUB, UO).

**A high value.** RDS(on) at 150 °C more than 2.2 times its 25 °C value is a BEX set too negative; a Vth
slope above 8 mV/K is a TCV copied from a different process.

**A low value.** RDS(on) ratio of exactly 1.000 is a card without mobility drift: paralleled switches
will share perfectly in simulation and a linear-mode stage will not run away. Code "absent" for the
zero-TC point.

**What it cannot tell.** Self-heating; the sheets' RDS(on) at 150 °C is a pulsed junction temperature, and
a real switch at rated current is hotter than its case.

**Standard.** resembles the VGS(th) vs Tj and normalised RDS(on) vs Tj charts of every power MOSFET sheet; IEC 60747-8

#### Voltage noise, the 1/f corner and NF (`mos-noise`)

Group `noise` · analysis `noise` · engines qspice, ngspice · symbols en, NF.

A MOSFET's noise is the channel's thermal noise through gfs, as a JFET's is, plus a 1/f part that in an
oxide-gated device is larger and reaches further up (corners of kilohertz to tens of kilohertz are
normal), which is why MOSFETs are rarely first stages and why the few audio MOSFET sheets (lateral
2SK1058, the small-signal 2N7000 family) do not print noise. The current noise is negligible (no gate
current). The measurement exists for the small-signal and lateral parts, and in a card depends on KF and
AF, which nearly every power MOSFET card leaves at zero.

**Circuit.** As `jfet-noise`, at VDS = 10 V, the gate biased for 1, 10, 100 mA and 1 A; RG = 0 for en;
a run at 100 mA with RG = 1 kΩ for NF.

**Conditions.** {vds: 10, id_ladder: [0.001, 0.01, 0.1, 1], rg: [0], nf: {id: 0.1, rg: 1000, f: 1000}, f_points: [10, 100, 1000, 10000, 100000], noise_sweep: {from: 1, to: 1e+06, per_decade: 20, unit: Hz}, audio_band: [20, 20000], temp_c: 25}

**The deck (QSPICE), line by line.**

- `VSENSE d dd 0` / `VD dd 0 10` / `VGB gb 0 {vgs}` / `RG in g 0.001` / `M1 d g 0 0 DUT` / `H1 out 0 VSENSE 1000` / `RLOAD out 0 1meg`
- `.noise V(out) VIN dec 20 1 1000000`

**Extraction.** en at each frequency and current; the corner; NF at 1 kHz, 100 mA, 1 kΩ; the 20 Hz to
20 kHz integrated noise, flat and A-weighted.

**Outputs.**

- `en@{f},{id}` (V/√Hz), `en_corner@{id}` (Hz), `nf@1kHz,100mA,1k` (dB), `vn_20_20k@{id}` (V), `vn_a_weighted@{id}` (V)

Curves: `en, ID={id}` (en against f, log); `en at {f}` (en against id, log). Shown first: en, ID = 100 mA.

**Card parameters that drive it:** KF, AF, KP, RS, RG, NLEV.

**A high value.** A corner above 100 kHz is a KF set for a submicron CMOS process in a discrete card.

**A low value.** A flat spectrum is KF = 0: code "absent" for the corner.

**What it cannot tell.** The part's noise: makers do not measure it on power parts, and the lateral audio
parts' sheets are silent.

**Standard.** resembles the spot noise method (MIL-STD-750-3); few MOSFET sheets print it

#### Is there any breakdown, and what leaks (`mos-breakdown`)

Group `breakdown` · analysis `dc` · engines qspice, ngspice, ltspice · symbols V(BR)DSS, IDSS, IGSS.

A level 1 or 3 card has no drain breakdown; a `VDMOS` card has `BV`/`IBV`/`NBV` and a subcircuit often a
zener across the body diode, so the absence is less universal than in bipolar cards. The gate oxide's
breakdown and leakage are in no card at all. IDSS, the off-state leakage the sheets quote at the rated
voltage (1 µA, 10 µA at 125 °C), is the body diode's reverse current in the card and far below the part's.

**Circuit.** Drain to source 0 to 1000 V (power MOSFETs are rated to 900 V) with the gate tied to the
source; the current read. Gate to source ±30 V with the drain tied to the source; the gate current read.

Drawing: DUT; swept source; ammeter.

**Conditions.** {vds_sweep: {from: 0, to: 1000, step: 1, unit: V}, vgs_sweep: {from: -30, to: 30, step: 0.1, unit: V}, breakdown_current: 0.001, leakage_points: {idss: [25, 100, 300], igss: 20}, temp_c: 25}

**The deck (QSPICE), line by line.**

- `VA sw da 0` / `MA da 0 0 0 DUT` / `.dc VSW 0 1000 1` — drain-source, gate grounded
- `VB sw gb 0` / `MB 0 gb 0 0 DUT` / `.dc VSW -30 30 0.1` — gate-source, drain grounded

**Extraction.** V(BR)DSS as the first voltage at which ID passes 1 mA, else "absent" with the voltage
reached; IDSS at 25, 100 and 300 V; IGSS at ±20 V, with the gmin note below 10 pA.

**Outputs.**

- `vbr_dss` (V), or absent
- `idss@{v}` (A), `igss@20V` (A), `igss@-20V` (A)

**Card parameters that drive it:** BV, IBV, NBV (VDMOS), JS, IS, subcircuit zeners.

**A low value.** A breakdown that appears is a VDMOS or subcircuit card; the figure is then worth
comparing with the sheet, and `V(BR)DSS` against temperature belongs in `mos-temperature` for such cards.

**What it cannot tell.** The part's breakdown when absent; gate oxide rupture, never.

**Standard.** resembles the V(BR)DSS, IDSS and IGSS methods of JEDEC JESD24-x and MIL-STD-750-3

#### Two reference stages' harmonic distortion (model against model only) (`mos-distortion`)

Group `distortion` · analysis `tran` · engines qspice, ngspice · symbols THD, HD2, HD3.

What the audio user wants and no sheet gives. Two fixed stages, because a MOSFET is used two ways in
audio: as a common-source gain stage (small-signal and lateral parts) and as a source follower in an
output stage (lateral and vertical power parts). In the follower the distortion comes from the
transconductance's curvature against the load current, from the Crss(VDS) modulation at high frequency,
and in class-AB from the crossover; here a single-ended follower into a resistive load at a fixed bias
shows the first two. The common-source stage shows the power law directly.

**Circuit.** Common source: VDD = 20 V, ID = 10 mA from an ideal source under a 100 Ω source resistor
bypassed to ground, drain load 1 kΩ, driven from 1 kΩ; 1 V peak out at 1 kHz. Follower: VDD = 25 V, ID =
100 mA from an ideal sink, load 100 Ω AC-coupled, driven from 100 Ω and from 1 kΩ (the Crss figure); 1 V
peak out at 1 kHz and at 20 kHz.

Drawing: DUT; current source; RS bypassed; RL; VDD; sine source through RS_in; probe.

**Conditions.** {cs: {vdd: 20, id: 0.01, rs: 100, rl: 1000, rs_in: 1000, f: 1000}, sf: {vdd: 25, id: 0.1, rl: 100, rs_in: [100, 1000], f: [1000, 20000]}, vout_peak: 1, cycles: 10, analysed_cycles: 4, steps_per_cycle: 4096}

**The deck (QSPICE), line by line.**

- `VDD vdd 0 20` / `RL vdd d 1000` / `RS s x 100` / `CS x 0 1000u` / `IS x vss 0.01` / `VSS vss 0 -5` / `RIN in g 1000` / `VIN in 0 SIN(0 {amp} 1000)` / `M1 d g s s DUT` — the common-source stage
- follower deck: `M1 vdd g s s DUT` / `IS s vss 0.1` / `CL s l 1000u` / `RL l 0 100`
- `.tran 2.44140625e-07 0.01 0 2.44140625e-07` — ten cycles of 1 kHz (0.5 ms at 20 kHz)

**Extraction.** As in the bipolar bench: harmonics 2 to 10 by Goertzel; THD, HD2, HD3 per stage, drive
impedance and frequency; the ratio of follower THD at 20 kHz with 1 kΩ drive over 100 Ω drive, which is
the Crss modulation figure.

**Outputs.**

- `thd_cs`, `hd2_cs`, `hd3_cs`
- `thd_sf@{rs_in},{f}`, `hd2_sf@…`, `hd3_sf@…`
- `crss_distortion_ratio`: follower THD at 20 kHz, 1 kΩ drive over 100 Ω drive

**Card parameters that drive it:** KP, VTO, THETA, LAMBDA, RS, Cgdmax/Cgdmin/a (or CGDO), CGSO.

**A high value.** Only against another model of the same part. A Crss ratio near 1 is a constant Miller
capacitance (level 1).

**What it cannot tell.** The distortion of any real circuit; it is a comparison between models.

**Standard.** none

#### Do the three simulators agree? (`mos-agreement`)

Group `dc` · analysis `derived` · engines qspice, ngspice, ltspice.

As `bjt-agreement`. MOSFET cards disagree most on the `VDMOS` extensions (ngspice's reading of
`Cgdmax/a`, `mtriode`, `Ksubthres` lags LTspice's), on level 3 parameters QSPICE treats differently
(`THETA`, `KAPPA`), and on subcircuit elements with vendor-specific syntax (PSpice `TABLE`, `VALUE` and
`IF` expressions in behavioural capacitors). The disagreeing ids say which group.

**Conditions.** {tolerances: [0.01, 0.05], floors: {F: 1e-16, s: 1e-12, A: 1e-14, C: 1e-15}}

**Outputs.** `agree_1pct`, `agree_5pct`, `odd_engine`, `disagreeing`.

**Standard.** none

## What the field-effect benches do not measure

As for the bipolar bench: self-heating (so no PD vs T, SOA, Zth, ID vs Tc, EAS or IAS vs tAV; a card with
a thermal pin — Nexperia's precision electrothermal models, Infineon's level-3 subcircuits — would allow
them and is a later catalogue version), dv/dt ruggedness, avalanche energy, gate-oxide breakdown, burst
noise, package parasitics beyond what the card carries. SiC and GaN cards, IGBTs and BSIM cards are recorded
by family and not run. Dual JFETs (LSK389, 2SK389) are run as two single devices when the subcircuit's pins
can be traced, with their matching read as the difference of the two IDSS and VGS(off) values.

## Mapping to data-sheet charts

For the comparison step (not this bench), the measurements above cover every FET chart type found in the
survey of 66 data sheets except the thermal ones: ID vs VDS (tracer), ID vs VGS and the subthreshold view
(transfer), gfs vs ID / vs VGS / vs VGS(off) and gos vs VDS (gm), IDSS vs VGS(off) (transfer), RDS(on) vs
ID / VGS / T (rdson, temperature), rDS(on) vs VGS (ohmic), VGS(th) vs T and V(BR)DSS vs T (temperature,
breakdown), IG vs VDS and IGSS vs T (gate, temperature), Ciss/Coss/Crss vs VDS and vs VGS, Eoss and Qoss
(capacitance), VGS vs Qg (gate-charge), t vs ID / RG / T and E vs ID / RG / T (switching), IS vs VSD, VSD
vs VGS, trr/Qrr/Irrm vs di/dt (body-diode), en vs f, en vs ID, NF vs RS (noise), ID(typ) vs T (temperature).
Thermal charts (PD vs T, SOA, Zth vs tp, ID vs Tc, EAS, IAS vs tAV) have no measurement, by design.
