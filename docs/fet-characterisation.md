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

<!-- measurements:start -->
Catalogue version `m-13`; the codes and the uses table are in [model-characterisation.md](model-characterisation.md).

### JFETs

#### Does the card load, and what is IDSS (`jfet-runs`)

Group `dc` · analysis `dc` · engines qspice, ngspice, ltspice · symbols IDSS, IG.

The first fact about a model: whether the simulator reads the card and finds an operating point. The point is the one every JFET sheet starts from, the gate tied to the source and the drain at 10 V, so that the drain current read is IDSS itself; the gate current at that point is read too, the quickest sign that the card carries a gate diode (IS) at all.

**Circuit.** The 10 V copy of the transfer sweep, read where the gate passes through 0 V: source grounded, the gate fed through a 0 V source (an ammeter), the drain held at 10 V.

Drawing: DUT; VDS source 10 V; gate to ground through an ammeter; ammeter in the drain. Differs from the netlist: the point is read from the transfer sweep rather than from a separate operating-point deck.

**Conditions.** {vds: 10, vgs: 0, temp_c: 25}

**The deck (QSPICE), line by line.**

- `VT1 dt1 0 10` — the 10 V copy of the transfer deck: its drain supply, whose current is ID
- `VIG1 g gi1 0` — its gate fed from the swept gate node through a 0 V source: reads the gate current
- `JT1 dt1 gi1 0 DUT` — the transistor, source grounded
- `.dc VGS -10 0.6 0.005` — read at the point of the sweep where the gate passes through 0 V

**Extraction.** Exit status and log give the error class as in the bipolar bench; when it runs, the drain and gate currents of the 10 V copy at VGS = 0, interpolated on the sweep.

**Outputs.**

- `runs`: true when the simulator returned a solution
- `error_class`: syntax, convergence, timeout or empty when it ran
- `idss_op` (A): drain current at VGS = 0, VDS = 10 V
- `ig_op` (A): gate current at the same point: the gate diode's reverse saturation current, or the simulator's floor

**Card parameters that drive it:** BETA, VTO, IS.

**A low value.** An IDSS of zero or below is a card the simulator read as something else: the code is suspect.

**What it cannot tell.** That the model is right; QSPICE accepts cards the other engines reject. Agreement between engines is the stronger fact.

**Standard.** none

#### Transfer characteristic, ID against VGS at fixed VDS (`jfet-transfer`)

Group `dc` · analysis `dc` · engines qspice, ngspice, ltspice · symbols IDSS, VGS(off), gfs.

The one curve a JFET is specified by, and the one its model is fitted to: drain current against gate voltage with the drain held. Its two ends are the two headline numbers of the sheet, IDSS where the gate is at zero and VGS(off) where the current has fallen to a nanoampere or ten; everything between them is the square law ID = IDSS (1 − VGS/VP)², whose slope is the transconductance. Real devices are not exactly square (the exponent sits between 1.7 and 2.3, which is what gives a JFET stage its second-harmonic character) and the current does not stop at pinch-off but tails off below it (LTspice's B parameter and the subthreshold region), where the low-current bias of a condenser-microphone stage sits. Four drain voltages are run because the sheets fix different ones (onsemi 15 or 20 V, Toshiba and Linear Systems 10 V, Nexperia 15 V), and how much the curve moves with VDS is LAMBDA again.

**Circuit.** Four copies of the transistor, sources grounded, drains held at 5, 10, 15 and 20 V, each gate fed from one swept source through its own 0 V source. The gate goes from −10 V (below the pinch-off of any discrete JFET) to +0.6 V (into gate conduction) in 5 mV steps; each drain current is read through its supply.

Drawing: DUT; VDS source (5, 10, 15 or 20 V); swept VGS source; ammeter in the drain; ammeter in the gate. Differs from the netlist: the four VDS copies run in one deck; the drawing shows one.

**Conditions.** {vgs_sweep: {from: -10, to: 0.6, step: 0.005, unit: V}, vds: [5, 10, 15, 20], vgs_off_currents: [1e-09, 1e-08, 1e-06], id_ladder: [1e-05, 3e-05, 0.0001, 0.0003, 0.001, 0.002, 0.003, 0.005, 0.01, 0.03, 0.1], fit_window: [0.05, 0.9], temp_c: 25}

**The deck (QSPICE), line by line.**

- `VT0 dt0 0 5` — the drain supply of the 5 V copy; VT1, VT2, VT3 at 10, 15 and 20 V
- `VIG0 g gi0 0` — its gate, fed from the swept node through a 0 V source
- `JT0 dt0 gi0 0 DUT` — the 5 V copy, source grounded
- `VGS g 0 0` — the gate drive, shared by every copy
- `.dc VGS -10 0.6 0.005` — the sweep: −10 V to +0.6 V in 5 mV steps

**Extraction.** IDSS is ID at VGS = 0 at each VDS. VGS(off) is the gate voltage at which ID first reaches 1 nA, 10 nA and 1 µA coming up from the negative end (three definitions in use: Linear Systems 1 nA, onsemi 10 nA, Nexperia 1 µA), n/a where the card's current never falls that far. The square-law exponent is the slope of log ID against log (VP − VGS) between 5 % and 90 % of IDSS, VP the 10 nA VGS(off); the ratio gfs(0)·VP/IDSS, exactly 2 for a square law, is the simpler figure. VGS at each ladder current is read on the 10 V curve and kept for the decks that bias the transistor at those currents. The curve is published linear (the sheet's view) and on a log current axis (the subthreshold view).

**Outputs.**

- `idss@{vds}` (A): drain current at VGS = 0, at 5, 10, 15 and 20 V
- `vgs_off@{current},{vds}` (V): gate voltage at ID = 1 nA, 10 nA and 1 µA
- `vgs@{id},{vds}` (V): gate voltage at each ladder current
- `n_fit`: the exponent of the fitted power law
- `gfs_vp_over_idss`: gfs(0) × VP / IDSS; 2 for an exact square law
- `idss_20v_over_5v`: IDSS at 20 V over IDSS at 5 V: the output conductance, read another way

Curves: ID, VDS=5V (id against vgs, lin, at VDS = 5); ID, VDS=10V (id against vgs, lin, at VDS = 10); ID, VDS=15V (id against vgs, lin, at VDS = 15); ID, VDS=20V (id against vgs, lin, at VDS = 20); ID log, VDS=5V (id_log against vgs, log, at VDS = 5); ID log, VDS=10V (id_log against vgs, log, at VDS = 10); ID log, VDS=15V (id_log against vgs, log, at VDS = 15); ID log, VDS=20V (id_log against vgs, log, at VDS = 20). Shown first: VDS = 10.

Beside the point under the cursor: gfs (S), transconductance, the local slope dID/dVGS; P (W), power dissipated in the transistor, VDS × ID.

**Card parameters that drive it:** BETA, VTO, LAMBDA, B, RS, RD.

**A high value.** An exponent above 2.2 is a card fitted with B for a doping tail; IDSS at 20 V far above IDSS at 5 V (ratio above 1.15) is a large LAMBDA.

**A low value.** An exponent of exactly 2.00 and no current below VP is a plain Shichman-Hodges card: right in the middle of the range, and wrong at both ends where low-current and clipping behaviour live.

**What it cannot tell.** Which grade of the part the card models: a sheet gives IDSS as a range per grade (A, B, C, D), and one card is one point in it.

**Standard.** resembles the transfer characteristics every JFET sheet prints (MIL-STD-750-3 IDSS and VGS(off) methods)

#### Output characteristics, as a curve tracer draws them (`jfet-tracer`)

Group `dc` · analysis `dc` · engines qspice, ngspice, ltspice · symbols ID(VDS), VGS.

The family every JFET sheet opens with: drain current against drain-source voltage, one trace per step of gate voltage, the steps equal. Three things are read at a glance. Where each trace bends from the ohmic region into saturation, near VDS = VGS − VGS(off), so the knees march to the right as the gate is opened; a card with large RD and RS rounds the knees and pulls them right. The slope of the flat part, the output conductance, which in a card is LAMBDA alone: one number for all traces, so a model's traces all climb at the same relative rate, which real JFETs do not quite do. And the spacing of the traces, which is the square law: equal gate steps give traces that crowd together towards pinch-off and spread apart near VGS = 0.

**Circuit.** Five copies of the transistor per family, the gate of trace k held at (5 − k) steps below zero, so that the top trace is VGS = 0 and the bottom one four steps down. The step is one of five universal values (0.1, 0.25, 0.5, 1 and 2 V, which span the 50 mV steps of a 2SK170 sheet and the volt steps of a 2N4391) or "auto", a fifth of the model's own VGS(off) from the transfer sweep, so that the bottom trace runs near pinch-off whatever the model. Thirty copies share one sweep: every drain goes from 0 to 25 V in 50 mV steps and each drain current is read through a 0 V source.

Drawing: DUT; swept VDS source 0 to 25 V; gate voltage source at −k × step; ammeter in the drain. Differs from the netlist: the thirty copies are drawn as one transistor with a stepped gate.

**Conditions.** {steps: 5, vgs_steps: [0.1, 0.25, 0.5, 1, 2], auto: {from: jfet-transfer, vgs_off_at: 1e-08, divisor: 5}, vds_sweep: {from: 0, to: 25, step: 0.05, unit: V}, temp_c: 25}

**The deck (QSPICE), line by line.**

- `VGK1 gk1 0 -0.8` — the first auto copy: its gate four steps below ground; VGK2 to VGK5 at three to none
- `VK1 sw dk1 0` — a 0 V source from the swept node to the copy's drain: reads its ID
- `JK1 dk1 gk1 0 DUT` — the copy, source grounded; the universal families are copies JU11 to JU55 with VGU11 to VGU55
- `VSW sw 0 0` — the drain supply of every copy, swept
- `.dc VSW 0 25 0.05` — the sweep: 0 to 25 V in 50 mV steps

**Extraction.** Each trace is one copy's drain current on the grid, fine in the first two volts where the device is a voltage-controlled resistor and coarser along the flat part. From the top auto trace: its current at 25 V, its output resistance at 10 V (the slope between 9 and 11 V) and the knee where it first reaches 90 % of its 10 V value. The universal families are published as they come: a step too deep for a low-pinch-off part puts every trace but the top one at zero, which is itself what the chart shows.

**Outputs.**

- `vgs_step` (V): the auto step: a fifth of VGS(off); trace k sits (5 − k) steps below zero
- `id@25V,step5` (A): drain current of the top auto trace (VGS = 0) at 25 V
- `ro@10V,step5` (Ω): output resistance of the top auto trace at 10 V
- `knee@step5` (V): drain voltage where the top auto trace first reaches 90 % of its 10 V current

Curves: ID, step 1, auto (id against vds, lin, at VGS step = auto); ID, step 2, auto (id against vds, lin, at VGS step = auto); ID, step 3, auto (id against vds, lin, at VGS step = auto); ID, step 4, auto (id against vds, lin, at VGS step = auto); ID, step 5, auto (id against vds, lin, at VGS step = auto); ID, step 1, VGS step=100mV (id against vds, lin, at VGS step = 0.1); ID, step 2, VGS step=100mV (id against vds, lin, at VGS step = 0.1); ID, step 3, VGS step=100mV (id against vds, lin, at VGS step = 0.1); ID, step 4, VGS step=100mV (id against vds, lin, at VGS step = 0.1); ID, step 5, VGS step=100mV (id against vds, lin, at VGS step = 0.1); ID, step 1, VGS step=250mV (id against vds, lin, at VGS step = 0.25); ID, step 2, VGS step=250mV (id against vds, lin, at VGS step = 0.25); ID, step 3, VGS step=250mV (id against vds, lin, at VGS step = 0.25); ID, step 4, VGS step=250mV (id against vds, lin, at VGS step = 0.25); ID, step 5, VGS step=250mV (id against vds, lin, at VGS step = 0.25); ID, step 1, VGS step=500mV (id against vds, lin, at VGS step = 0.5); ID, step 2, VGS step=500mV (id against vds, lin, at VGS step = 0.5); ID, step 3, VGS step=500mV (id against vds, lin, at VGS step = 0.5); ID, step 4, VGS step=500mV (id against vds, lin, at VGS step = 0.5); ID, step 5, VGS step=500mV (id against vds, lin, at VGS step = 0.5); ID, step 1, VGS step=1V (id against vds, lin, at VGS step = 1); ID, step 2, VGS step=1V (id against vds, lin, at VGS step = 1); ID, step 3, VGS step=1V (id against vds, lin, at VGS step = 1); ID, step 4, VGS step=1V (id against vds, lin, at VGS step = 1); ID, step 5, VGS step=1V (id against vds, lin, at VGS step = 1); ID, step 1, VGS step=2V (id against vds, lin, at VGS step = 2); ID, step 2, VGS step=2V (id against vds, lin, at VGS step = 2); ID, step 3, VGS step=2V (id against vds, lin, at VGS step = 2); ID, step 4, VGS step=2V (id against vds, lin, at VGS step = 2); ID, step 5, VGS step=2V (id against vds, lin, at VGS step = 2). Drawn together, as a family: one family per gate step; the auto family's step is the model's own VGS(off) over five, published as vgs_step. Shown first: VGS step = auto.

Beside the point under the cursor: P (W), power dissipated in the transistor, VDS × ID; ro (Ω), output resistance, the local slope of the trace.

**Card parameters that drive it:** BETA, VTO, LAMBDA, RD, RS, B.

**A high value.** Traces that keep climbing (an output resistance of a few kilohms at 1 mA) are a large LAMBDA; knees far to the right are large RD and RS.

**A low value.** Perfectly flat traces are LAMBDA = 0: an infinite output resistance no JFET has, and a stage with a current-source load will simulate with more gain than it gets.

**What it cannot tell.** Breakdown (the sweep stops at 25 V and a plain card has none) and the exponent, which the transfer sweep fits.

**Standard.** resembles the output characteristics every JFET sheet prints

#### Transconductance and output conductance against drain current (`jfet-gm`)

Group `dc` · analysis `ac` · engines qspice, ngspice, ltspice · symbols gfs, gos, yfs.

The two small-signal parameters an amplifier stage is designed from. gfs (also yfs, |Yfs|) sets the gain of a common-source stage with a given drain load; it rises with the square root of the drain current for a square-law device, so doubling the bias current buys 41 % more gain, and it is highest at IDSS. gos is the output conductance, 1/ro, which limits the gain of a stage with a current-source load; its ratio to gfs is the intrinsic voltage gain of the transistor. The sheets draw gfs against ID (Toshiba, Linear Systems, onsemi), gfs against VGS (onsemi) and gos against VDS (Linear Systems).

**Circuit.** One copy per ladder current at VDS = 10 V, the gate biased by the voltage the transfer sweep found for that current with 1 V of AC on top: the AC drain current is gfs. Beside each, a copy with the gate held and 1 V of AC on the drain: its AC drain current is gos. Read at 1 kHz. A ladder current the model never reaches keeps its copy with the channel closed, and is not read.

Drawing: DUT; VDS source 10 V; gate bias source with a small AC component (gfs copy); gate bias held and AC on the drain (gos copy); AC ammeter in the drain. Differs from the netlist: one pair of copies per ladder current; the drawing shows one of each.

**Conditions.** {vds: 10, id_ladder: [1e-05, 3e-05, 0.0001, 0.0003, 0.001, 0.003, 0.01, 0.03, 0.1], f: 1000}

**The deck (QSPICE), line by line.**

- `VD0 d0 0 10` — the drain supply of the first gfs copy, 10 V; its AC current is gfs × 1 V
- `JM0 d0 g0 0 DUT` — the first copy, source grounded; one pair per ladder current
- `VDO0 do0 0 DC 10 AC 1` — a gos copy: the drain driven with 1 V of AC, the gate held
- `.ac dec 10 100 10000` — ten points per decade from 100 Hz to 10 kHz; read at 1 kHz

**Extraction.** gfs at each ladder current is the AC drain current over the 1 V of AC gate drive at 1 kHz; gos likewise from the drain-driven copy. gfs/√ID is published at every current: constant for a square law, falling where RS degenerates the device. The intrinsic gain gfs/gos and the Early-voltage equivalent ID/gos − VDS (1/LAMBDA) are kept at 1 mA, the latter absent above 10 000 V.

**Outputs.**

- `gfs@{id},{vds}` (S): transconductance at 1 kHz at each ladder current
- `gos@{id},{vds}` (S): output conductance at 1 kHz
- `gfs_over_sqrt_id@{id}` (S/√A): the square-law figure
- `av_intrinsic@1mA`: gfs/gos at 1 mA, 10 V
- `va_equiv@1mA` (V): ID/gos − 10 V, the Early-voltage equivalent (1/LAMBDA), or absent
- `gos_note`: absent when the output conductance is zero at every current (LAMBDA = 0)

Curves: gfs, VDS=10V (gfs against id, log, at VDS = 10); gos, VDS=10V (gos against id, log, at VDS = 10).

**Card parameters that drive it:** BETA, VTO, LAMBDA, RS, RD, B.

**A high value.** gfs/√ID that falls by more than 20 % between 1 mA and IDSS is a large RS; an intrinsic gain above 1000 at 1 mA is a very small LAMBDA.

**A low value.** gos of exactly zero is a card with LAMBDA = 0; an intrinsic gain below 30 is a soft device or a LAMBDA set from a sheet's gos at the wrong current.

**What it cannot tell.** The frequency dependence of either (the frequency measurement), and the 1 MHz value Toshiba quotes as |Yfs|, which the capacitances begin to touch.

**Standard.** resembles the forward transfer admittance and output admittance methods (MIL-STD-750-3, 1 kHz)

#### The ohmic region, rDS(on) against VGS and its linearity (`jfet-ohmic`)

Group `dc` · analysis `dc` · engines qspice, ngspice, ltspice · symbols rDS(on), rDS(VGS).

Below the knee a JFET is a resistor whose value the gate sets: the voltage-controlled resistor of compressors, tremolos and gain cells, and the series element of an analogue switch. rDS(on) at VGS = 0 is the lowest value, which in a card is RD + RS + the channel at full width (BETA and VTO); the resistance rises as the gate closes, to infinity at VGS(off). The gain-cell designer lives with a third thing: the resistance is not constant across the signal, because the channel narrows on the drain side as VDS grows, so the resistor distorts; the classic cure feeds half the drain signal back to the gate and cancels the second-order term. Both the raw non-linearity and the cancelled one are measured.

**Circuit.** Linearity: copies at VGS = 0, VGS(off)/4, VGS(off)/2 and 3·VGS(off)/4 (the model's own) with the drain swept −0.5 to +0.5 V, once with the gate held and once with the gate fed VGS + VDS/2 through two 1 MΩ resistors (the bias source at twice VGS, so that the divider gives VGS plus half the drain). rDS against VGS: one copy with 50 mV on the drain and the gate taken from 0 to 1.2 × VGS(off) by a behavioural source, so that the sweep runs in units of the model's own pinch-off.

Drawing: DUT; drain source swept ±0.5 V (or 50 mV); gate source stepped; two 1 MΩ resistors from the drain and from the gate bias to the gate (feedback copy); ammeter in the drain. Differs from the netlist: the four gate voltages run as eight copies in one deck; the rDS-against-VGS sweep is a second deck.

**Conditions.** {vds_small: 0.05, vgs_points: 120, lin_vds_sweep: {from: -0.5, to: 0.5, step: 0.005, unit: V}, lin_vgs_fractions: [0, 0.25, 0.5, 0.75], feedback: 0.5, temp_c: 25}

**The deck (QSPICE), line by line.**

- `VGR0 gr0 0 0` — the first linearity copy: the gate at the first fraction of VGS(off), 0 V
- `VR0 sw dr0 0` — a 0 V source from the swept node to its drain: reads ID
- `JR0 dr0 gr0 0 DUT` — the copy, source grounded; VGR1 to VGR3 at a quarter, a half and three quarters of VGS(off)
- `VGB0 gb0 0 0` — the feedback copy's bias, twice the gate fraction: the two 1 MΩ resistors halve it and add half the drain
- `RFD0 df0 gf0 1e6`
- `RFB0 gb0 gf0 1e6`
- `JF0 df0 gf0 0 DUT`
- `VSW sw 0 0` — the drain supply of every copy, swept −0.5 to +0.5 V in 5 mV steps
- `.dc VSW -0.5 0.5 0.005`
- `VDR dr 0 0.05` — the gate sweep deck: 50 mV on the drain, the gate at VGS(off) times the swept number, 0 to 1.2
- `JR dr gr 0 DUT`
- `VGSW gsw 0 0`
- `.dc VGSW 0 1.2 0.01`

**Extraction.** rDS at each gate voltage is the chord between −50 and +50 mV. From the linearity sweep the drain current is fitted to a cubic in VDS; the second- and third-order coefficients over the first are the distortion figures of the resistor, for the plain and the feedback copy; the asymmetry is rDS at +0.5 V over rDS at −0.5 V. From the gate sweep, rDS against VGS/VGS(off) and the gate voltages at which rDS has doubled and risen tenfold.

**Outputs.**

- `rds_on@0V` (Ω): rDS(on) at VGS = 0, the chord over ±50 mV
- `rds@{fraction}` (Ω): rDS at VGS = VGS(off)/4, /2, 3/4
- `vgs_rds_x2` (V): gate voltage where rDS is twice rDS(on)
- `vgs_rds_x10` (V): gate voltage where rDS is ten times rDS(on)
- `rds_hd2@{fraction}` (1/V): second-order coefficient of ID(VDS) over the first, plain gate
- `rds_hd3@{fraction}` (1/V²): third-order coefficient over the first
- `rds_hd2_fb@{fraction}` (1/V): the second-order coefficient with VDS/2 fed back to the gate
- `rds_asym@{fraction}`: rDS at +0.5 V over rDS at −0.5 V

Curves: ID vs VDS ohmic, VGS=0 (id against vds, lin, at VGS/VGS(off) = 0); ID vs VDS ohmic, VGS=0.25 (id against vds, lin, at VGS/VGS(off) = 0.25); ID vs VDS ohmic, VGS=0.5 (id against vds, lin, at VGS/VGS(off) = 0.5); ID vs VDS ohmic, VGS=0.75 (id against vds, lin, at VGS/VGS(off) = 0.75); ID vs VDS with feedback, VGS=0 (id_fb against vds, lin, at VGS/VGS(off) = 0); ID vs VDS with feedback, VGS=0.25 (id_fb against vds, lin, at VGS/VGS(off) = 0.25); ID vs VDS with feedback, VGS=0.5 (id_fb against vds, lin, at VGS/VGS(off) = 0.5); ID vs VDS with feedback, VGS=0.75 (id_fb against vds, lin, at VGS/VGS(off) = 0.75); rDS vs VGS/VGS(off) (rds against vgs_fraction, log). Shown first: VGS/VGS(off) = all.

Beside the point under the cursor: rDS (Ω), the local resistance of the channel.

**Card parameters that drive it:** BETA, VTO, RD, RS, LAMBDA, B.

**A high value.** A second-order coefficient the feedback copy does not reduce is a card whose asymmetry does not come from the channel (RD ≠ RS); an rDS(on) far above the sheet's is RD + RS set from a wrong figure.

**A low value.** rDS(on) of exactly 1/(2·BETA·|VTO|) is a card with RD = RS = 0.

**What it cannot tell.** Distortion in a real circuit, where the source impedance and the gate's capacitive loading enter; this is the resistor alone.

**Standard.** resembles the rDS(on) methods of switching-JFET sheets (Nexperia, Vishay) and the voltage-controlled-resistor notes of the J111 and 2N4391 families; no test method for linearity

#### The gate diode, forward conduction, reverse leakage and the drain's share of it (`jfet-gate`)

Group `leakage` · analysis `dc` · engines qspice, ngspice, ltspice · symbols IG, IGSS, IG(VDG).

The gate of a JFET is a diode to the channel, and it shows in three ways. Forward, it conducts at about 0.6 V: the clipping limit on the positive half of a guitar-pedal stage, and the reason a JFET input cannot be driven above its source by much; a card without IS has no forward conduction and clips symmetrically. Reverse, it leaks: IGSS, nanoamperes or picoamperes, the input current of an electrometer stage, doubling every 10 K. And with the drain high the leakage grows far beyond IGSS, because carriers accelerated in the drain-gate field ionise and the holes go to the gate; the sheets of Linear Systems and Vishay draw IG against VDG at several drain currents. A plain SPICE JFET card has no term for the third effect (LTspice adds ALPHA and VK), so most models read a flat IGSS at any drain voltage, which flatters a high-voltage low-noise stage.

**Circuit.** Three decks. Forward: the gate driven 0 to +0.9 V with the drain and source grounded, the gate current read. Reverse: the gate driven 0 to −40 V with drain and source grounded. Drain field: copies at four drain currents (the gate biased as the transfer sweep found) with the drain swept 0 to 25 V, the gate current read through its bias source.

Drawing: DUT; gate source swept (forward and reverse decks) with drain and source grounded; ammeter in the gate; drain swept with the gate biased (field deck). Differs from the netlist: three decks drawn as one.

**Conditions.** {vg_forward: {from: 0, to: 0.9, step: 0.005, unit: V}, vg_reverse: {from: 0, to: -40, step: -0.1, unit: V}, igss_points: [10, 20, 30], vdg_sweep: {from: 0, to: 25, step: 0.1, unit: V}, field_id: [0.0001, 0.001, 0.003, 0.01], field_points: [5, 10, 15, 20], temp_c: 25}

**The deck (QSPICE), line by line.**

- `VGF gf gsw 0` — the forward deck: the gate fed from the swept node through a 0 V source that reads IG
- `JF 0 gf 0 DUT` — drain and source grounded
- `VGSW gsw 0 0`
- `.dc VGSW 0 0.9 0.005`
- `VGR gr gsw 0` — the reverse deck, the same way
- `JR 0 gr 0 DUT`
- `.dc VGSW 0 -40 -0.1`
- `VF0 sw df0 0` — the field deck: a 0 V source from the swept node to the first copy's drain
- `VGB0 gb0 0 -1.5` — its gate biased for 100 µA (from the transfer sweep); its current is IG
- `JD0 df0 gb0 0 DUT`
- `VSW sw 0 0`
- `.dc VSW 0 25 0.1`

**Extraction.** Forward: the gate voltage at IG = 10 µA and 1 mA (the clipping limit), the ideality factor and IS of the gate diode fitted between 1 µA and 100 µA. Reverse: IGSS at 10, 20 and 30 V (below 10 pA it is the simulator's gmin floor). Field: IG at VDS = 5, 10, 15, 20 V at each current; the ratio IG(20 V)/IG(5 V) at 1 mA, absent when it is 1 or the current is below the 100 pA of the simulators' gmin floor (no impact ionisation in the card).

**Outputs.**

- `vg_fwd@10µA` (V): forward gate voltage at IG = 10 µA
- `vg_fwd@1mA` (V): forward gate voltage at IG = 1 mA
- `is_gate` (A): saturation current of the gate diode from the forward fit
- `n_gate`: its ideality factor
- `igss@{v}` (A): reverse gate leakage at 10, 20, 30 V
- `ig@{vds},{id}` (A): gate current at the drain voltage and drain current
- `ig_field_ratio@1mA`: IG at VDS = 20 V over IG at 5 V, or absent

Curves: IG forward (ig against vgs, log); IG reverse (igss against vgs_reverse, log); IG vs VDS, ID=100µA (ig_field against vds, log, at ID = 0.0001); IG vs VDS, ID=1mA (ig_field against vds, log, at ID = 0.001); IG vs VDS, ID=3mA (ig_field against vds, log, at ID = 0.003); IG vs VDS, ID=10mA (ig_field against vds, log, at ID = 0.01). Shown first: ID = 0.001.

**Card parameters that drive it:** IS, N, ISR, NR, ALPHA, VK, XTI.

**A high value.** A forward gate voltage above 0.75 V at 1 mA is a large N or RS; IGSS above 1 nA at 25 °C in a card is an IS set for a power device.

**A low value.** Forward current absent is a card with IS = 0 (or 1e-30): it never clips on the gate. A field ratio absent is the absence of impact ionisation, the usual case.

**What it cannot tell.** The real part's leakage, dominated by surface and package effects a card does not carry; and burst noise, which the gate diode causes in real parts.

**Standard.** resembles the IGSS and IG methods of MIL-STD-750-3 and the "IG vs VDS" charts of Linear Systems sheets

#### Ciss, Crss and the two junction capacitances against voltage (`jfet-capacitance`)

Group `capacitance` · analysis `ac` · engines qspice, ngspice, ltspice · symbols Ciss, Crss, Cgs, Cgd.

Two reverse-biased junctions, gate-source and gate-drain, both falling with voltage as the depletion layer widens. Ciss = Cgs + Cgd is the input capacitance of a common-source stage and loads a guitar pickup or a condenser capsule; Crss = Cgd is the feedback capacitance, multiplied by the gain into the Miller input capacitance, and the charge injection of a switch. The sheets quote both at VDS = 10 or 15 V, VGS = 0, 1 MHz. In a card they are CGS and CGD at zero bias with PB and M for the fall; a card without them has a JFET of infinite bandwidth and no noise penalty from a capacitive source.

**Circuit.** Per ladder voltage, three copies. Ciss and Crss: the drain at the voltage, the gate at 0 V with 1 V of AC, source grounded; the gate's AC current is Ciss, the drain's Crss. Cgs alone: the gate the voltage below the source with 1 V of AC, the drain open through 1 GΩ. Cgd alone: the drain at the voltage, AC on the gate, the source open through 1 GΩ. Twenty-four copies share one run.

Drawing: DUT; bias source with AC on the gate; the drain held and read (Ciss and Crss); third terminal open through 1 GΩ (Cgs and Cgd); AC ammeter. Differs from the netlist: the ladder runs as copies in one deck; the drawing shows one of each.

**Conditions.** {v_ladder: [0.1, 0.5, 1, 2, 5, 10, 15, 20], f: 1e+06, temp_c: 25}

**The deck (QSPICE), line by line.**

- `VDX0 dx0 0 0.1` — the Ciss/Crss copy at the first ladder voltage: the drain at 0.1 V
- `VGX0 gx0 0 DC 0 AC 1` — its gate at 0 V with 1 V of AC: the gate's AC current is Ciss, the drain's Crss
- `JX0 dx0 gx0 0 DUT`
- `VGS0 gs0 0 DC -0.1 AC 1` — the Cgs copy: the gate 0.1 V below the source with AC, the drain open through 1 GΩ
- `RDS0 ds0 0 1e9`
- `JS0 ds0 gs0 0 DUT`
- `VDG0 dg0 0 0.1` — the Cgd copy: the drain at 0.1 V, AC on the gate, the source open through 1 GΩ
- `VGG0 gg0 0 DC 0 AC 1`
- `RSG0 sg0 0 1e9`
- `JG0 dg0 gg0 sg0 DUT`
- `.ac dec 10 100000 10000000` — 100 kHz to 10 MHz; C = Im(I)/(2πf) read at 1 MHz

**Extraction.** At each voltage, the quadrature part of each copy's 1 MHz current over 2πf (a guarded meter's reading: the in-phase part is the transconductance where the drain is read). The grading coefficient is the slope of log Crss against log (V + 1) between 1 and 10 V; the ratio Ciss(1 V)/Ciss(10 V) is the simpler figure. A card without CGS and CGD reads zero: absent.

**Outputs.**

- `ciss@{v}` (F): input capacitance at VDS = v, VGS = 0
- `crss@{v}` (F): reverse transfer capacitance at VDS = v, VGS = 0
- `cgs@{v}` (F): the gate-source junction alone at reverse voltage v
- `cgd@{v}` (F): the gate-drain junction alone at reverse voltage v
- `crss_m`: grading coefficient of Crss between 1 and 10 V
- `ciss_1v_over_10v`: Ciss at 1 V over Ciss at 10 V

Curves: Ciss (ciss against v, log); Crss (crss against v, log); Cgs (cgs against v, log); Cgd (cgd against v, log).

**Card parameters that drive it:** CGS, CGD, PB, M, FC.

**A high value.** Ciss of 30 pF or more in the card of a low-noise JFET costs the stage its noise advantage with a high-impedance source.

**A low value.** Zero is a card without CGS and CGD: every frequency-dependent result of the model is then meaningless.

**What it cannot tell.** The capacitance's dependence on drain current when the channel is open (Cgs rises), which a level 1 card does not carry.

**Standard.** resembles the Ciss and Crss methods of MIL-STD-750-3 at 1 MHz, read as a meter reads a low-impedance capacitance

#### Transconductance against frequency and the gain-bandwidth figure (`jfet-frequency`)

Group `frequency` · analysis `ac` · engines qspice, ngspice, ltspice · symbols yfs(f), fT.

How far up in frequency the transconductance holds. A JFET has no transit-time parameter in SPICE; its frequency limit is set entirely by the capacitances against the transconductance, and the figure of merit gfs/2π(Cgs + Cgd) plays the role fT plays for a bipolar. Toshiba sheets draw |Yfs| against frequency; the RF-JFET sheets (BF245, J310) print the figure directly. The magnitude of the forward transfer admittance is swept to 1 GHz at each ladder current and read where it has fallen by 3 dB; a fixed common-source stage's bandwidth is read too, because that is what an audio user compares with the real circuit.

**Circuit.** The gfs copies of the transconductance measurement, swept 1 kHz to 1 GHz. A second deck is a common-source stage: VDD = 18 V, the source self-biased by a resistor for ID = IDSS/3 (from the transfer sweep) and bypassed, the drain load for VDS = 9 V, driven from 1 kΩ, swept 1 Hz to 10 MHz.

Drawing: DUT; VDS source; gate bias with AC; AC ammeter (yfs deck); common-source stage with RD and bypassed RS; 1 kΩ source resistance; probe on the drain. Differs from the netlist: two decks drawn side by side.

**Conditions.** {vds: 10, id_ladder: [0.0001, 0.001, 0.003, 0.01], ac_sweep: {from: 1000, to: 1e+09, per_decade: 20, unit: Hz}, stage: {rs_in: 1000, sweep: {from: 1, to: 1e+07, per_decade: 20}}}

**The deck (QSPICE), line by line.**

- `VD0 d0 0 10` — a yfs copy, one per ladder current: the drain at 10 V, the gate biased with 1 V of AC
- `JY0 d0 g0 0 DUT`
- `.ac dec 20 1000 1e+09` — 1 kHz to 1 GHz, twenty points per decade
- `VDD vdd 0 18` — the stage deck: 18 V, RD for VDS = 9 V and RS for ID = IDSS/3, bypassed; driven from 1 kΩ
- `CS s 0 1000u`
- `RIN in g 1000`
- `VIN in 0 AC 1`
- `JS dc g s DUT`
- `.ac dec 20 1 10000000`

**Extraction.** |yfs| against frequency at each current; the frequency at which it has fallen to 1/√2 of its 1 kHz value; the figure gfs/2π(Cgs + Cgd) from the 1 kHz gfs and the 10 V capacitances. For the stage, the gain at 1 kHz, the −3 dB frequency and the input capacitance seen at 1 kHz (the Miller figure).

**Outputs.**

- `yfs_3db@{id}` (Hz): first frequency where |yfs| departs from its 1 kHz value by 3 dB, either way: a voltage-driven level-1 card does not fall, it rises where Cgd feeds the drive through
- `ft_equiv@{id}` (Hz): gfs / 2π(Cgs + Cgd) at 10 V
- `stage_gain@1kHz`: voltage gain of the reference common-source stage
- `stage_f3db` (Hz): its −3 dB frequency
- `stage_cin@1kHz` (F): its input capacitance at 1 kHz

Curves: |yfs|, ID=100µA (yfs against f, log, at ID = 0.0001); |yfs|, ID=1mA (yfs against f, log, at ID = 0.001); |yfs|, ID=3mA (yfs against f, log, at ID = 0.003); |yfs|, ID=10mA (yfs against f, log, at ID = 0.01); stage gain (av against f, log). Shown first: ID = 0.001.

**Card parameters that drive it:** CGS, CGD, PB, M, BETA, VTO, RS, RD.

**A high value.** An fT equivalent in the gigahertz for an audio JFET is a card with no capacitances (see the capacitance measurement).

**What it cannot tell.** Package inductance and the real part's distributed gate resistance, which set the RF limit; this is the die model alone.

**Standard.** resembles the |Yfs| vs f chart of Toshiba sheets; no test method

#### Voltage noise, current noise, the 1/f corner and NF (`jfet-noise`)

Group `noise` · analysis `noise` · engines qspice, ngspice · symbols en, in, NF.

The reason JFETs are chosen for the first stage. The voltage noise is the channel's thermal noise seen through the transconductance, about √(4kT·0.67/gfs), so it falls as the bias current rises and is lowest at IDSS; the current noise is the shot noise of the gate leakage, picoamperes' worth, which is why a JFET wins against any bipolar when the source is a megohm. Below a corner the 1/f part rises, and in JFETs the corner sits anywhere from 10 Hz to 10 kHz depending on the process; a 2SK170 at 1 kHz reads under 1 nV/√Hz. In a card the voltage floor comes from BETA and the current; the 1/f part needs KF and AF, which most cards leave at zero and then say nothing about the part's low-frequency noise; the current noise needs IS.

**Circuit.** A common-source stage at VDS = 10 V, the gate biased by a voltage source (from the transfer sweep) for 100 µA, 300 µA, 1, 3 and 10 mA. The noise input is a voltage source in series with RG at the gate; the output is the drain current through a sensing source. Two runs per current, RG = 0 and RG = 10 MΩ (the current noise of a JFET needs a large resistor to show above the voltage noise). A run at 1 mA with RG = 1 MΩ gives a noise figure.

Drawing: DUT; VDS source 10 V; gate bias; noise source with RG; sensing in the drain. Differs from the netlist: the output is a current-controlled voltage source into 1 MΩ, as in the bipolar bench.

**Conditions.** {vds: 10, id_ladder: [0.0001, 0.0003, 0.001, 0.003, 0.01], rg: [0, 1e+07], nf: {id: 0.001, rg: 1e+06, f: 1000}, audio_band: [20, 20000], f_points: [10, 100, 1000, 10000, 100000], noise_sweep: {from: 1, to: 1e+06, per_decade: 20, unit: Hz}, temp_c: 25}

**The deck (QSPICE), line by line.**

- `VSENSE d dd 0` — the sensing source and the drain supply
- `VD dd 0 10`
- `RG in g 0.001` — the gate bias for the step (from the transfer sweep); VIN rides on it
- `J1 d g 0 DUT` — the transistor, source grounded
- `H1 out 0 VSENSE 1000` — the sensed current as a voltage
- `RLOAD out 0 1meg`
- `.noise V(out) VIN dec 20 1 1000000` — 1 Hz to 1 MHz, referred to VIN; a second run with RG = 10 MΩ

**Extraction.** As in the bipolar bench: en from the RG = 0 run; in from the 10 MΩ run less en² and 4kT·RG; the corner where en is √2 times its 10 kHz value, absent when flat; NF at 1 kHz with RG = 1 MΩ; the curves of NF and total noise against RS at 1 kHz. Two figures no sheet prints are added because they are what an audio user hears: the input-referred noise integrated over 20 Hz to 20 kHz in volts rms, flat and A-weighted, at each current. The ratio of en at 10 kHz at the top current over the bottom one is the square-root law check.

**Outputs.**

- `en@{f},{id}` (V/√Hz): voltage noise density
- `in@{f},{id}` (A/√Hz): current noise density
- `en_corner@{id}` (Hz): the 1/f corner, or absent
- `nf@1kHz,1mA,1MΩ` (dB): noise figure at RG = 1 MΩ
- `en_ratio_top_over_bottom`: en at 10 kHz at 10 mA over en at 100 µA
- `vn_20_20k@{id}` (V): input-referred noise, 20 Hz to 20 kHz rms, RG = 0
- `vn_a_weighted@{id}` (V): the same, A-weighted
- `one_over_f`: present when any current shows a 1/f corner, else absent (KF = 0)

Curves: en, 100µA (en against f, log, at ID = 0.0001); en, 300µA (en against f, log, at ID = 0.0003); en, 1mA (en against f, log, at ID = 0.001); en, 3mA (en against f, log, at ID = 0.003); en, 10mA (en against f, log, at ID = 0.01); in, 100µA (in against f, log, at ID = 0.0001); in, 300µA (in against f, log, at ID = 0.0003); in, 1mA (in against f, log, at ID = 0.001); in, 3mA (in against f, log, at ID = 0.003); in, 10mA (in against f, log, at ID = 0.01); en at 10Hz (en_id against id, log, at f = 10); en at 1kHz (en_id against id, log, at f = 1000); en at 10kHz (en_id against id, log, at f = 10000); NF, 1mA (nf against rs, lin, at ID = 0.001); VT, 1mA (vt against rs, log, at ID = 0.001). Shown first: ID = 0.001.

**Card parameters that drive it:** BETA, VTO, RS, IS, KF, AF, RD.

**A high value.** A corner above 1 kHz is a high KF; en above 3 nV/√Hz at 10 mA for a low-noise part is a BETA set too low or a large RS.

**A low value.** A flat spectrum to 1 Hz is KF = 0, absent for the corner; in below 1 fA/√Hz is IS at the simulator's floor.

**What it cannot tell.** Burst noise, the gate leakage's dependence on drain voltage (which raises in at high VDS in real parts) and the part's own noise, which makers measure on a few samples.

**Standard.** resembles the spot noise methods (MIL-STD-750-3) and the en/f charts of 2SK170, LSK170 and 2N5457 sheets

#### IDSS, VGS(off) and the zero-temperature-coefficient point (`jfet-temperature`)

Group `temperature` · analysis `dc` · engines qspice, ngspice, ltspice · symbols IDSS(T), VGS(off)(T), VGS(0TC).

Two opposed drifts. The pinch-off voltage falls in magnitude by about 2 mV/K (the gate junction's built-in potential), which would raise the current at a fixed gate voltage; the channel's mobility falls with temperature, which lowers it. The two cancel at one drain current, roughly where VGS(off) − VGS is 0.6 V, and a stage biased there holds its current over temperature; above it the current falls with heat, below it rises. A plain card gets both drifts from the defaults of the gate diode and nothing at all for the mobility (LTspice adds VTOTC and BETATCE; PSpice has XTI for the diode only), so most models drift one way only.

**Circuit.** The transfer deck's 10 V copy run at −55, 100, 125 and 150 °C; 25 °C comes from the transfer deck.

Drawing: DUT; VDS source 10 V; swept VGS source; ammeter in the drain; a thermometer symbol.

**Conditions.** {vds: 10, vgs_sweep: {from: -10, to: 0.6, step: 0.005, unit: V}, temps_c: [-55, 25, 100, 125, 150], vgs_points_fraction: [0, 0.25, 0.5, 0.75]}

**The deck (QSPICE), line by line.**

- `.temp -55` — the first deck, at −55 °C; then 100, 125 and 150 °C
- `VT dt 0 10` — the transfer copy at 10 V
- `JT dt g 0 DUT`
- `VGS g 0 0`
- `.dc VGS -10 0.6 0.005`

**Extraction.** IDSS and VGS(off) (10 nA) at each temperature; dVGS(off)/dT over −55 to 150 °C and the IDSS ratio 125/25 °C. The zero-TC point is the gate voltage at which the 25 and 125 °C curves cross on the grid (interpolated), and the drain current there; absent when they do not cross above 1 µA. ID against temperature at VGS = 0, VGS(off)/4, /2 and 3/4 is kept, the way the BF245 sheet draws it.

**Outputs.**

- `idss@{T}` (A): IDSS at each temperature
- `vgs_off@{T}` (V): VGS(off) at 10 nA at each temperature
- `dvgsoff_dt` (V/K): slope of VGS(off) between −55 and 150 °C
- `idss_125_over_25`: IDSS at 125 °C over IDSS at 25 °C
- `vgs_0tc` (V): gate voltage of zero temperature coefficient, or absent
- `id_0tc` (A): drain current at that point

Curves: ID, −55°C (id against vgs, lin, at T = -55); ID, 25°C (id against vgs, lin, at T = 25); ID, 100°C (id against vgs, lin, at T = 100); ID, 125°C (id against vgs, lin, at T = 125); ID, 150°C (id against vgs, lin, at T = 150); ID vs T, VGS=0 (id_t against T, lin, at VGS/VGS(off) = 0); ID vs T, VGS=0.25 (id_t against T, lin, at VGS/VGS(off) = 0.25); ID vs T, VGS=0.5 (id_t against T, lin, at VGS/VGS(off) = 0.5); ID vs T, VGS=0.75 (id_t against T, lin, at VGS/VGS(off) = 0.75). Shown first: T = all, VGS/VGS(off) = all.

**Card parameters that drive it:** VTOTC, BETATCE, XTI, EG, IS, N.

**A high value.** An IDSS that rises with temperature by more than 10 % is a card with a VTO drift and no mobility term: real JFETs at IDSS fall with heat.

**A low value.** No crossing at all, with IDSS fixed, is a card with no temperature dependence beyond the gate diode: it biases perfectly in simulation and drifts in the real circuit.

**What it cannot tell.** Self-heating, and the leakage's doubling per 10 K, which is below the simulators' floor at 25 °C and only shows above 100 °C.

**Standard.** resembles the "ID vs Tj" chart of Nexperia JFET sheets and IEC 60747-8 temperature characteristics

#### The analogue switch, turn-on, turn-off and charge injection (`jfet-switch`)

Group `switching` · analysis `tran` · engines qspice, ngspice, ltspice · symbols ton, toff, Qinj.

A JFET switch is driven from VGS = 0 (on) to below VGS(off) (off). Its times are set by how fast the gate charges Ciss through the drive resistor, and its curse is the charge that the gate step pushes through Cgd and Cgs into the signal path: the glitch a sample-and-hold or a muting circuit lives with. The switching sheets (J111, 2N4391, Nexperia BF/J series) quote ton and toff at a fixed load and drive; here one fixture serves every model so that they can be compared.

**Circuit.** Times: the transistor between a 1 V signal source and a load of 1 kΩ or 10 kΩ to ground; the gate driven from V(off) to 0 V and back through 1 kΩ with 10 ns edges, V(off) either −10 V or twice the model's own VGS(off). Charge injection: the signal at 0 V, the load a 1 nF hold capacitor, the gate stepped from 0 to V(off) once.

Drawing: DUT in series between the source and RL; gate pulse through 1 kΩ; probe on the load. Differs from the netlist: the injection deck replaces RL by a 1 nF capacitor.

**Conditions.** {rl: [1000, 10000], v_off: [-10, auto], v_signal: 1, rg: 1000, edge_s: 1e-08, t_start_s: 1e-07, t_on_s: 2e-06, t_after_s: 2e-06, max_step_s: 1e-09, c_hold: 1e-09, curve_points: 80, temp_c: 25}

**The deck (QSPICE), line by line.**

- `VS s 0 1` — the signal source, 1 V
- `JW l g s DUT` — the switch, drain to the load
- `RL l 0 1000` — the load
- `RG in g 1000` — the gate drive through 1 kΩ: off at −10 V, on for 2 µs, off
- `VIN in 0 PWL(0 -10 1e-07 -10 1.1e-07 0 2.11e-06 0 2.12e-06 -10)`
- `.tran 1e-09 4.12e-06 0 1e-09`
- `CH l 0 1e-09` — the injection deck: 0 V signal, a 1 nF hold capacitor, the gate stepped off once
- `RLK l 0 1G`

**Extraction.** ton from the gate's rising edge to the load voltage's 90 % crossing; toff from the gate's falling edge to its 10 % crossing; the on-state divider gives the switch's on-resistance (1 kΩ load, auto drive); n/a where the channel never opened. The injected charge is the hold capacitor's voltage step across the turn-off edge, times its capacitance.

**Outputs.**

- `ton@{rl},{voff}` (s): turn-on time to 90 % of the on-state load voltage
- `toff@{rl},{voff}` (s): turn-off time to 10 %
- `q_inj@{voff}` (C): charge injected into a 1 nF hold capacitor at turn-off
- `rds_on_switch` (Ω): on-resistance from the on-state divider, 1 kΩ load

Curves: Vload(t), RL=1kΩ, Voff=-10V (v against t, lin, at RL = 1000, Voff = -10); Vload(t), RL=1kΩ, Voff=auto (v against t, lin, at RL = 1000, Voff = auto); Vload(t), RL=10kΩ, Voff=-10V (v against t, lin, at RL = 10000, Voff = -10); Vload(t), RL=10kΩ, Voff=auto (v against t, lin, at RL = 10000, Voff = auto). Shown first: RL = 1000, Voff = -10.

**Card parameters that drive it:** CGS, CGD, PB, M, BETA, VTO, RD, RS.

**A high value.** Injected charge above 10 pC is a large Cgd; toff in microseconds is a card whose capacitances are far too large or whose VGS(off) is deep.

**A low value.** Zero injection is a card without capacitances.

**What it cannot tell.** The times with the sheet's own fixture.

**Standard.** resembles the switching-time fixtures of analogue-switch JFET sheets, simplified

#### A reference stage's harmonic distortion (model against model only) (`jfet-distortion`)

Group `distortion` · analysis `tran` · engines qspice, ngspice · symbols THD, HD2, HD3.

What the audio user wants from a JFET model and no sheet prints. The curvature of a JFET stage is the square law itself, nearly pure second harmonic in a common-source stage, which is the "character" pedal builders describe, tamed by source degeneration, plus the output conductance and the capacitances. Two fixed stages: a common-source stage with its source resistor unbypassed, where the square law shows, and a source follower, where it should nearly vanish and what remains is gos and the gate diode; both biased at IDSS/3, the device's own point, so that models of the same part are compared on equal footing.

**Circuit.** Common source: VDD = 18 V, the source resistor chosen from the transfer sweep for ID = IDSS/3, unbypassed, the drain resistor for VDS = 9 V, driven from 10 kΩ. Follower: the same source resistor, drain to VDD, the output across the source resistor. A probe run at 20 mV sets the input for 1 V peak out at 1 kHz (for the follower, half the quiescent drop across RS when that is less than a volt); ten cycles simulated, the last four analysed. The common-source stage is also driven to 3 V peak out to show the gate-diode clipping.

Drawing: DUT; RD and RS; VDD 18 V; 1 kHz source through 10 kΩ; probe on the drain (or the source). Differs from the netlist: the follower is a second deck.

**Conditions.** {vdd: 18, id_fraction: 0.333, vds: 9, rs_in: 10000, f: 1000, vout_peak: [1, 3], cycles: 10, analysed_cycles: 4, steps_per_cycle: 4096}

**The deck (QSPICE), line by line.**

- `VDD vdd 0 18` — the supply, and the source resistor for ID = IDSS/3 (from the transfer sweep), unbypassed
- `RIN in g 10000` — the drive, through 10 kΩ; the probe run's 20 mV, then the amplitude for 1 V and 3 V peak out
- `VIN in 0 SIN(0 0.02 1000)`
- `J1 d g s DUT` — the transistor; the follower deck has its drain at VDD and no RD
- `.tran 2.44140625e-07 0.003 0 2.44140625e-07` — three cycles for the probe, ten for the measurement, 4096 steps per cycle

**Extraction.** As in the bipolar bench: harmonics 2 to 10 by Goertzel over the last four cycles; THD, HD2, HD3 per stage and level; the stages' gains from the probe runs.

**Outputs.**

- `thd_cs@{level}`: THD of the common-source stage at 1 V and 3 V peak out
- `hd2_cs@{level}`: its second harmonic over the fundamental
- `hd3_cs@{level}`: its third harmonic over the fundamental
- `thd_sf`: THD of the source follower at 1 V peak out, or at half its quiescent source drop when that is less
- `hd2_sf`: its second harmonic
- `hd3_sf`: its third harmonic
- `vout_sf` (V): the follower's output level, peak
- `gain_cs`: the common-source stage's gain at 20 mV
- `gain_sf`: the follower's gain at 20 mV

**Card parameters that drive it:** BETA, VTO, B, LAMBDA, RS, RD, IS, CGS, CGD.

**A high value.** Only against another model of the same part. A follower above 0.1 % at 1 V is a large LAMBDA or a card that conducts at the gate early.

**A low value.** A common-source HD3 far below HD2 is the square law; HD3 above HD2 is a card with B or a wrong exponent.

**What it cannot tell.** The distortion of any real circuit; it is a comparison between models.

**Standard.** none

#### Is there any breakdown, and what leaks (`jfet-breakdown`)

Group `breakdown` · analysis `dc` · engines qspice, ngspice, ltspice · symbols V(BR)GSS, V(BR)DGO, ID(off).

A plain JFET card has no breakdown: the gate-source junction reverse-biased to 100 V passes only its saturation current, and a drain swept to 300 V with the gate below pinch-off sees nothing. The sheets quote V(BR)GSS of 25 to 40 V (BF245, J201) and up to 60 V (2N4391); a model used in a high-voltage phantom-powered or tube-hybrid stage will not fail where the part does. Documented here as an absence, as in the bipolar bench, with the leakage below pinch-off read beside it.

**Circuit.** Gate to source reversed 0 to −100 V, drain open. Drain to gate 0 to 300 V, source open. Drain to source 0 to 300 V with the gate held at twice VGS(off): the off-state leakage.

Drawing: DUT; swept source; 1 GΩ opens; ammeter. Differs from the netlist: three decks drawn as one.

**Conditions.** {vgs_sweep: {from: 0, to: -100, step: -0.1, unit: V}, vdg_sweep: {from: 0, to: 300, step: 1, unit: V}, vds_off_sweep: {from: 0, to: 300, step: 1, unit: V}, breakdown_current: 0.001, leakage_points: {igss: 20, id_off: 15}, temp_c: 25}

**The deck (QSPICE), line by line.**

- `VA sw ga 0` — gate-source, drain open through 1 GΩ: the swept node drives the gate through a 0 V source
- `RDA da 0 1e9`
- `JA da ga 0 DUT`
- `VSW sw 0 0`
- `.dc VSW 0 -100 -0.1`
- `VB sw db 0` — drain-gate, source open: the gate grounded
- `RSB sb 0 1e9`
- `JB db 0 sb DUT`
- `.dc VSW 0 300 1`
- `VC sw dc 0` — drain-source with the gate at twice VGS(off)
- `JC dc gc 0 DUT`

**Extraction.** The first voltage at which the current passes 1 mA, else absent; IGSS and the drain-gate leakage at 20 V, ID(off) at 15 V (below 10 pA they are the simulators' floor).

**Outputs.**

- `vbr_gss` (V): gate-source breakdown, or absent
- `vbr_dgo` (V): drain-gate breakdown, or absent
- `vbr_dss` (V): drain-source breakdown with the gate off, or absent
- `igss@20V` (A): gate-source leakage at 20 V, drain open
- `idgo@20V` (A): drain-gate leakage at 20 V, source open
- `id_off@15V` (A): drain current at 15 V with the gate at twice VGS(off)

**What it cannot tell.** Anything about the part's breakdown when the code is absent, which it is for every plain card.

**Standard.** resembles the V(BR)GSS and IGSS methods of MIL-STD-750-3

#### Do the three simulators agree? (`jfet-agreement`)

Group `dc` · analysis `derived` · engines qspice, ngspice, ltspice.

As the bipolar agreement, over every output above. JFET cards are where dialects bite most: M against MJ for the grading coefficient, B, VTOTC, BETATCE, ALPHA and VK, ISR and NR are each read by one or two of the three engines and silently dropped by the others, so a card that uses them agrees in DC and disagrees in capacitance, temperature or gate current. The disagreeing measurement ids say which.

**Conditions.** {tolerances: [0.01, 0.05], floors: {F: 1e-16, s: 1e-12, A: 1e-14}}

**Extraction.** For each published output, the spread (max − min over the mean) across the engines that produced it, classed as within 1 %, within 5 % or beyond; values below the floors count as zero.

**Outputs.**

- `agree_1pct`: share of outputs on which every engine agrees within 1 %
- `agree_5pct`: share within 5 %
- `odd_engine`: the engine most often alone outside 5 %, or none
- `disagreeing`: the measurement ids where the engines differ by more than 5 %

**What it cannot tell.** Which engine is right.

**Standard.** none


### MOSFETs

#### Does the card load, and what does it do when switched on (`mosfet-runs`)

Group `dc` · analysis `dc` · engines qspice, ngspice, ltspice · symbols ID(on), IS.

Whether the simulator reads the card and finds an operating point, and the first sanity figures: the drain current with the gate fully on at a low drain voltage (what a switch does), with the gate at a logic level, and the body diode's current at 1 V, the quickest sign that the card carries a diode at all. A card can fail for the three bipolar reasons and a fourth of its own: a subcircuit whose body diode or resistors use a dialect the engine lacks.

**Circuit.** The 1 V copy of the transfer sweep, read where the gate passes through 10 V and through 4.5 V; the body-diode sweep's VGS = 0 copy, read at VSD = 1 V.

Drawing: DUT; VDS source 1 V; VGS source 10 V (or 4.5 V); ammeter in the drain; a third copy reversed. Differs from the netlist: the points are read from the transfer and body-diode sweeps rather than from a separate deck.

**Conditions.** {vds: 1, vgs: [10, 4.5], diode_vsd: 1, temp_c: 25}

**The deck (QSPICE), line by line.**

- `VT0 dt0 0 1` — the 1 V copy of the transfer deck: its drain supply, whose current is ID
- `MT0 dt0 g 0 DUT` — the transistor, source grounded, the gate on the swept node
- `.dc VGS -2 15 0.01` — read where the gate passes through 10 V and 4.5 V

**Extraction.** Exit status and log give the error class; when it runs, the three currents, interpolated on their sweeps.

**Outputs.**

- `runs`: true when the simulator returned a solution
- `error_class`: syntax, convergence, timeout or empty when it ran
- `id_on@10V` (A): drain current at VGS = 10 V, VDS = 1 V (about 1 V / RDS(on))
- `id_on@4.5V` (A): drain current at VGS = 4.5 V, VDS = 1 V
- `is_diode@1V` (A): body-diode current at VSD = 1 V, or absent (no diode in the card)

**Card parameters that drive it:** VTO, KP, RD, RS, IS.

**A low value.** An on-state current of zero at 10 V is a card the simulator read as something else: the code is suspect.

**What it cannot tell.** That the model is right; agreement between engines is the stronger fact.

**Standard.** none

#### Transfer characteristic, ID against VGS at fixed VDS, and the threshold (`mosfet-transfer`)

Group `dc` · analysis `dc` · engines qspice, ngspice, ltspice · symbols Vth, gfs, ID(VGS).

The curve a MOSFET model is fitted on: drain current against gate voltage with the drain held. On a log current axis it has two parts: below threshold the current rises exponentially (60 to 100 mV per decade at 25 °C), above it as a power of (VGS − Vth), square in a long-channel device, nearer linear in a short or velocity-saturated one, which is the difference between a lateral audio MOSFET and a trench switch. Three definitions of the threshold are in use on the sheets (ID = 20 µA at Infineon, 250 µA at ST and Vishay, 1 mA at Nexperia) and a fourth in the card (VTO, the extrapolated one); all four are read. The drain voltage is fixed at the values the sheets use (6 V Infineon, 15 V most, 25 V onsemi) plus 1 V for the linear region. A level 1 card has no subthreshold current at all and simply stops at VTO; level 3 and VDMOS (Ksubthres) carry a tail.

**Circuit.** Four copies, sources grounded, drains at 1, 6, 15 and 25 V. One source sweeps every gate from −2 to +15 V in 10 mV steps; each drain current is read through its supply. A fifth copy is diode-connected (drain tied to gate through an ammeter) and swept the same way, because that is how the sheets define Vth.

Drawing: DUT; VDS source (1, 6, 15 or 25 V); swept VGS source; ammeter in the drain; a fifth copy with the drain tied to the gate. Differs from the netlist: the five copies run in one deck; the drawing shows two.

**Conditions.** {vgs_sweep: {from: -2, to: 15, step: 0.01, unit: V}, vds: [1, 6, 15, 25], vds_main: 15, vth_currents: [2e-05, 0.00025, 0.001], id_ladder: [1e-06, 1e-05, 0.0001, 0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1, 3, 10], vgs_read: [2, 2.5, 3, 4, 4.5, 5, 6, 10], sub_window: [1e-08, 1e-06], temp_c: 25}

**The deck (QSPICE), line by line.**

- `VT2 dt2 0 15` — the 15 V copy, the one the summary values come from; VT0, VT1, VT3 at 1, 6 and 25 V
- `MT2 dt2 g 0 DUT`
- `VTD dtd g 0` — the diode-connected copy: its drain tied to the gate through an ammeter
- `MTD dtd g 0 DUT`
- `VGS g 0 0` — the gate drive, shared by every copy, swept −2 to +15 V in 10 mV steps
- `.dc VGS -2 15 0.01`

**Extraction.** Vth at the three currents, diode-connected and at 15 V; the extrapolated Vth as the intercept of √ID against VGS fitted between 10 and 100 mA at 15 V (the square-law region); the subthreshold slope in volts per decade between 10 nA and 1 µA, absent where the card has no current below VTO or the slope is not a junction's (under 40 mV or over 500 mV per decade: a leakage resistor, or the square law's foot); the exponent of ID against (VGS − Vth) from 100 mA to the top current. ID at each read gate voltage and VGS at each ladder current, at every VDS; the 15 V values are kept for the decks that bias the transistor at those currents.

**Outputs.**

- `vth@{current},diode` (V): threshold at 20 µA, 250 µA and 1 mA, diode-connected
- `vth@{current},15V` (V): the same at VDS = 15 V
- `vth_extrapolated` (V): the intercept of √ID against VGS between 10 and 100 mA
- `sub_slope` (V/decade): the subthreshold slope between 10 nA and 1 µA, or absent
- `n_fit`: exponent of the power law above threshold
- `id@{vgs},{vds}` (A): drain current at each read gate voltage
- `vgs@{id},{vds}` (V): gate voltage at each ladder current
- `id_25v_over_6v@1A`: ID at 25 V over ID at 6 V at the gate voltage for 1 A (LAMBDA read another way)

Curves: ID, VDS=1V (id against vgs, lin, at VDS = 1); ID, VDS=6V (id against vgs, lin, at VDS = 6); ID, VDS=15V (id against vgs, lin, at VDS = 15); ID, VDS=25V (id against vgs, lin, at VDS = 25); ID log, VDS=1V (id_log against vgs, log, at VDS = 1); ID log, VDS=6V (id_log against vgs, log, at VDS = 6); ID log, VDS=15V (id_log against vgs, log, at VDS = 15); ID log, VDS=25V (id_log against vgs, log, at VDS = 25); ID diode-connected (id_diode against vgs, log). Shown first: VDS = 15.

Beside the point under the cursor: gfs (S), transconductance, the local slope dID/dVGS; P (W), power dissipated in the transistor, VDS × ID.

**Card parameters that drive it:** VTO, KP, GAMMA, PHI, THETA, KSUBTHRES, LAMBDA, RS, RD, NFS.

**A high value.** An exponent near 2 in a model of a trench power MOSFET is a long-channel fit: its gfs at high current will be too high. A subthreshold slope above 120 mV per decade is a card fitted for a soft turn-on.

**A low value.** No subthreshold current at all is a level 1 card: a switch that turns off exactly at VTO, and a class-AB stage whose crossover region does not exist.

**What it cannot tell.** Where the part's threshold sits in its production spread (1 to 3 V on most sheets); the card is one point.

**Standard.** resembles the transfer characteristics and VGS(th) methods of every MOSFET sheet (JEDEC JESD24, MIL-STD-750-3)

#### Output characteristics, as a curve tracer draws them (`mosfet-tracer`)

Group `dc` · analysis `dc` · engines qspice, ngspice, ltspice · symbols ID(VDS), VGS.

Drain current against drain-source voltage, one trace per gate voltage. For a power MOSFET the traces are nearly vertical at the origin (the on-resistance) and bend into saturation at VDS = VGS − Vth; every maker prints this family to 5 or 10 V with gate steps of half a volt near threshold and of volts above. Read at a glance: the slope at the origin, which is RDS(on) at that gate voltage; where the knee sits; the spacing, which is the transconductance and its rise with gate drive; and the slope of the flat part, the channel-length modulation LAMBDA. A VDMOS card has a separate parameter for the triode region's shape (mtriode), and the knee is where cards fitted from headline numbers go wrong.

**Circuit.** Copies of the transistor at the universal gate ladder (2, 2.5, 3, 3.5, 4, 4.5, 5, 6, 8, 10, 15 V) and at five "auto" gate voltages, the ones that gave 10 mA, 30 mA, 100 mA, 300 mA and 1 A at 15 V in the transfer sweep, so that the family spans two decades of current whatever the model's threshold. One source sweeps every drain from 0 to 10 V in 20 mV steps.

Drawing: DUT; swept VDS source; gate voltage source at the step; ammeter in the drain. Differs from the netlist: the sixteen copies are drawn as one transistor with a stepped gate.

**Conditions.** {vgs_ladder: [2, 2.5, 3, 3.5, 4, 4.5, 5, 6, 8, 10, 15], auto: {from: mosfet-transfer, id: [0.01, 0.03, 0.1, 0.3, 1], vds: 15}, vds_sweep: {from: 0, to: 10, step: 0.02, unit: V}, rds_chord_vds: 0.1, temp_c: 25}

**The deck (QSPICE), line by line.**

- `VGK1 gk1 0 2.2` — the first auto copy: its gate at the voltage that gave 10 mA at 15 V in the transfer sweep
- `VK1 sw dk1 0` — a 0 V source from the swept node to its drain: reads its ID
- `MK1 dk1 gk1 0 DUT`
- `VGU1 gu1 0 2` — the first universal copy, its gate at 2 V; VGU2 to VGU11 at 2.5 to 15 V
- `VU1 sw du1 0`
- `MU1 du1 gu1 0 DUT`
- `VSW sw 0 0` — the drain supply of every copy, swept 0 to 10 V in 20 mV steps
- `.dc VSW 0 10 0.02`

**Extraction.** Each trace on the grid. The chord resistance at VDS = 0.1 V of each universal trace (an RDS(on) reading at low current), the knee of each auto trace (where it reaches 90 % of its 10 V value), the slope of the flat part between 5 and 10 V as output conductance.

**Outputs.**

- `vgs_auto@{k}` (V): the five auto gate voltages
- `rds_chord@100mV,{vgs}` (Ω): VDS/ID at 0.1 V for each universal step, or n/a below threshold
- `vds_knee@auto{k}` (V): drain voltage where the auto trace reaches 90 % of its 10 V current
- `gos_flat@auto{k}` (S): dID/dVDS between 5 and 10 V

Curves: ID, auto 1 (id against vds, lin, at VGS = auto); ID, auto 2 (id against vds, lin, at VGS = auto); ID, auto 3 (id against vds, lin, at VGS = auto); ID, auto 4 (id against vds, lin, at VGS = auto); ID, auto 5 (id against vds, lin, at VGS = auto); ID, VGS=2V (id against vds, lin, at VGS = 2); ID, VGS=2.5V (id against vds, lin, at VGS = 2.5); ID, VGS=3V (id against vds, lin, at VGS = 3); ID, VGS=3.5V (id against vds, lin, at VGS = 3.5); ID, VGS=4V (id against vds, lin, at VGS = 4); ID, VGS=4.5V (id against vds, lin, at VGS = 4.5); ID, VGS=5V (id against vds, lin, at VGS = 5); ID, VGS=6V (id against vds, lin, at VGS = 6); ID, VGS=8V (id against vds, lin, at VGS = 8); ID, VGS=10V (id against vds, lin, at VGS = 10); ID, VGS=15V (id against vds, lin, at VGS = 15). Shown first: VGS = auto.

Beside the point under the cursor: P (W), power dissipated in the transistor, VDS × ID; rDS (Ω), the chord VDS/ID; ro (Ω), output resistance, the local slope of the trace.

**Card parameters that drive it:** VTO, KP, LAMBDA, RD, RS, MTRIODE, KSUBTHRES, THETA, GAMMA.

**A high value.** A flat part that climbs steeply is a large LAMBDA: normal in a small-signal part, wrong in a model of a 100 A switch. A knee that sits at several volts at modest current is a large RD.

**A low value.** Perfectly flat traces are LAMBDA = 0 and an infinite output resistance.

**What it cannot tell.** Thermal droop and breakdown; the traces beyond the part's rating are the model's, not a transistor's.

**Standard.** resembles the output characteristics every MOSFET sheet prints; no test method

#### On-resistance against drain current, gate voltage and the drive floor (`mosfet-rdson`)

Group `high-current` · analysis `dc` · engines qspice, ngspice, ltspice · symbols RDS(on).

The headline number of a power MOSFET, and the one a card is most often fitted to at exactly one point. It is not one number: it rises with current (the channel leaves the linear region as ID approaches the saturation current for that VGS), falls as the gate is driven harder towards a floor set by the ohmic parts (RD + RS + the fully open channel), and nearly doubles between 25 and 150 °C. The sheets draw it against ID at two or three gate voltages (Infineon, Nexperia) and against VGS at one current (Nexperia, Fairchild). Here the drain current is forced and the drain voltage read, so that the curve reaches the rated current and beyond.

**Circuit.** One copy per gate voltage of the ladder (2.5, 3, 4, 4.5, 5, 6, 8, 10, 15 V), the gate held; the drain current forced by the behavioural dial from 1 mA to 100 A with a clamp diode to a 30 V rail, so that a copy that cannot pass the current is caught; VDS read. A second deck holds the current at 100 mA, 1 A and 10 A in three copies and sweeps their gates 0 to 15 V.

Drawing: DUT; forced drain current with a clamp to 30 V; gate source at the step; voltmeter drain to source. Differs from the netlist: the nine gate steps run as copies in one deck; the gate sweep is a second deck.

**Conditions.** {vgs_ladder: [2.5, 3, 4, 4.5, 5, 6, 8, 10, 15], id_sweep: {from: 0.001, to: 100, per_decade: 20, unit: A}, id_ladder: [0.001, 0.01, 0.1, 1, 2, 5, 10, 20, 50, 100], clamp_v: 30, linear_fraction: 0.3, vgs_sweep_at_id: [0.1, 1, 10], vgs_sweep: {from: 0, to: 15, step: 0.05, unit: V}, temp_c: 25}

**The deck (QSPICE), line by line.**

- `BR0 0 dr0 I=exp(2.302585092994046*V(x))` — the drain drive of the first copy: 10 to the power of the dial, pushed into the drain
- `DCL0 dr0 cl0 DCLMP` — the clamp: what the transistor cannot pass goes to 30 V
- `VCL0 cl0 0 30`
- `VGR0 gr0 0 2.5` — the gate at the first step, 2.5 V; one copy per step
- `MR0 dr0 gr0 0 DUT`
- `.dc VX -3 2 0.05` — the dial: 1 mA to 100 A at twenty points per decade
- `IH0 0 dh0 0.1` — the gate sweep deck: the current held at 100 mA in the first copy, 1 A and 10 A in the others
- `MH0 dh0 gsw 0 DUT`
- `VGSW gsw 0 0`
- `.dc VGSW 0 15 0.05`

**Extraction.** RDS(on) at each ladder current and gate voltage where the copy sat below the clamp and in its linear region (VDS below 0.3 × (VGS − Vth)); n/a where it saturated. The floor is RDS(on) at 10 V and 1 mA; the slope with current is RDS(on) at the highest ladder current that still conducts at 10 V over the floor. From the gate sweep, RDS(on) against VGS at three currents and the gate voltage at which it is within 10 % of its 15 V value.

**Outputs.**

- `rdson@{id},{vgs}` (Ω): on-resistance at the ladder current and gate voltage
- `rdson_floor@10V` (Ω): at 10 V and 1 mA: RD + RS + the open channel
- `rdson_slope@10V`: RDS(on) at the top conducting current over the floor
- `id_top_conducting@10V` (A): the highest ladder current the copy at 10 V passed in its linear region
- `rdson_4v5_over_10v@1A`: the logic-level penalty
- `vgs_rdson_110pct@{id}` (V): gate voltage where RDS(on) is 1.1 × its 15 V value

Curves: RDS(on), VGS=2.5V (rdson against id, log, at VGS = 2.5); RDS(on), VGS=3V (rdson against id, log, at VGS = 3); RDS(on), VGS=4V (rdson against id, log, at VGS = 4); RDS(on), VGS=4.5V (rdson against id, log, at VGS = 4.5); RDS(on), VGS=5V (rdson against id, log, at VGS = 5); RDS(on), VGS=6V (rdson against id, log, at VGS = 6); RDS(on), VGS=8V (rdson against id, log, at VGS = 8); RDS(on), VGS=10V (rdson against id, log, at VGS = 10); RDS(on), VGS=15V (rdson against id, log, at VGS = 15); RDS(on) vs VGS, ID=100mA (rdson_vgs against vgs, log, at ID = 0.1); RDS(on) vs VGS, ID=1A (rdson_vgs against vgs, log, at ID = 1); RDS(on) vs VGS, ID=10A (rdson_vgs against vgs, log, at ID = 10). Shown first: VGS = 10, ID = 1.

Beside the point under the cursor: VDS (V), the on-state drop, RDS(on) × ID.

**Card parameters that drive it:** RD, RS, KP, VTO, THETA, RDS, MTRIODE.

**A high value.** A slope above 1.5 at 10 V is a card whose channel saturates near the rated current (KP too small); a 4.5 V/10 V ratio above 2 is a threshold set high or a small KP.

**A low value.** A floor of zero is a card with RD = RS = 0 and a very large KP: its switch dissipates nothing. A slope of exactly 1 to 100 A is the same card.

**What it cannot tell.** The temperature rise at the current, which doubles the real figure; see the temperature measurement.

**Standard.** resembles the RDS(on) methods of JEDEC JESD24 and MIL-STD-750-3, pulsed

#### Transconductance and output conductance against drain current (`mosfet-gm`)

Group `dc` · analysis `ac` · engines qspice, ngspice, ltspice · symbols gfs, gos.

gfs sets the gain of a stage and, in a switch, how fast the current follows the gate during a transition; the sheets draw it against ID at VDS = 15 V (ST, Vishay) and quote one value at the rated current. For a square-law device it rises with √ID; in a real power MOSFET it goes nearly linear with ID at low current (subthreshold) and saturates at high current (mobility degradation, THETA), which is where a model fitted at one point misleads. gos is the output conductance, read as for the JFET, and is what a MOSFET current source or cascode is limited by.

**Circuit.** As the JFET measurement: copies at the ladder currents with the gate biased from the transfer sweep and 1 V of AC, VDS = 15 V, read at 1 kHz; gos from drain-driven copies beside them. A ladder current the model never reaches keeps its copy with the gate at 0 V, and is not read.

Drawing: DUT; VDS source; gate bias with AC; AC ammeter in the drain; gos copies. Differs from the netlist: one pair of copies per ladder current; the drawing shows one of each.

**Conditions.** {vds: 15, id_ladder: [0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1, 3, 10], f: 1000}

**The deck (QSPICE), line by line.**

- `VD0 d0 0 15` — the drain supply of the first gfs copy, 15 V; its AC current is gfs × 1 V
- `MG0 d0 g0 0 DUT`
- `VDO0 do0 0 DC 15 AC 1` — a gos copy: the drain driven with 1 V of AC, the gate held
- `MO0 do0 go0 0 DUT`
- `.ac dec 10 100 10000` — read at 1 kHz

**Extraction.** gfs and gos at each ladder current; gfs/√ID at every current (its fall is THETA at work); the intrinsic gain gfs/gos at 100 mA; the equivalent Early voltage ID/gos − VDS at 100 mA, absent above 10 000 V.

**Outputs.**

- `gfs@{id},{vds}` (S): transconductance at 1 kHz
- `gos@{id},{vds}` (S): output conductance at 1 kHz
- `gfs_over_sqrt_id@{id}` (S/√A): the square-law figure
- `av_intrinsic@100mA`: gfs/gos at 100 mA
- `va_equiv@100mA` (V): ID/gos − 15 V, or absent
- `gos_note`: absent when gos is zero at every current (LAMBDA = 0)

Curves: gfs, VDS=15V (gfs against id, log, at VDS = 15); gos, VDS=15V (gos against id, log, at VDS = 15).

**Card parameters that drive it:** KP, VTO, THETA, LAMBDA, RS, KSUBTHRES.

**A high value.** gfs still rising as √ID at 10 A is a card without THETA (level 1): it overstates the gain and the switching speed at rated current.

**A low value.** gos of zero is LAMBDA = 0.

**What it cannot tell.** gfs at the sheet's pulsed, self-heated condition; and the 1 MHz value.

**Standard.** resembles the forward transconductance method (JEDEC JESD24, MIL-STD-750-3) at 1 kHz

#### Ciss, Coss, Crss against drain voltage, and against gate voltage (`mosfet-capacitance`)

Group `capacitance` · analysis `ac` · engines qspice, ngspice, ltspice · symbols Ciss, Coss, Crss.

The three capacitances every MOSFET sheet draws against VDS at VGS = 0, 1 MHz, on a log axis from 0.1 V to the rating. Ciss = Cgs + Cgd is nearly flat (the oxide); Coss = Cds + Cgd and Crss = Cgd fall by one to two decades as the drain depletes, and the shape of that fall decides switching loss, the Miller plateau and, in a follower output stage, the distortion at 20 kHz. Nexperia also draws Ciss and Crss against VGS at low VDS, where the gate oxide takes over as the channel forms. A level 1 or 3 card has only the overlap terms (CGSO, CGDO, CGBO) and the body-diode junction (CBD): its Crss is constant with voltage, which is wrong by a decade; a VDMOS card has the Cgdmax/Cgdmin/a law for Crss and gets it right; subcircuit models add a voltage-dependent capacitor.

**Circuit.** Per drain voltage, two copies. Ciss and Crss: the drain held at the voltage, the gate at 0 V with 1 V of AC, source grounded; the gate's AC current is Ciss, the drain's Crss. Coss: the drain driven with AC at the voltage, gate and source grounded. Twelve voltages share one run. For the VGS view, a second deck's copies sit at VDS = 0 with the gate biased 0 to 10 V and driven with AC.

Drawing: DUT; bias and AC sources; AC ammeters; two copies per voltage. Differs from the netlist: the copies run in one deck; the VGS view is a second deck.

**Conditions.** {vds_ladder: [0.1, 0.5, 1, 2, 5, 10, 15, 20, 25, 30, 50, 100], vgs_ladder_at_vds0: [0, 1, 2, 3, 4, 5, 6, 8, 10], f: 1e+06, qoss_at: [25, 100], temp_c: 25}

**The deck (QSPICE), line by line.**

- `VDI0 di0 0 0.1` — the Ciss/Crss copy at the first ladder voltage: the drain held at 0.1 V, the gate at 0 V with 1 V of AC
- `VGI0 gi0 0 DC 0 AC 1`
- `MI0 di0 gi0 0 DUT`
- `VDO0 do0 0 DC 0.1 AC 1` — the Coss copy: the drain driven, gate grounded
- `MO0 do0 0 0 DUT`
- `.ac dec 10 100000 10000000` — 100 kHz to 10 MHz; C = Im(I)/(2πf) read at 1 MHz
- `VDG0 dg0 0 0` — the VGS deck: VDS = 0, the gate at each ladder voltage with AC
- `VGG0 gg0 0 DC 0 AC 1`
- `MG0 dg0 gg0 0 DUT`

**Extraction.** The quadrature part of each copy's 1 MHz current over 2πf at each voltage (the in-phase part is the transconductance, left out as a guarded meter leaves it). Crss(1 V)/Crss(25 V) and Coss(1 V)/Coss(25 V) as the shape figures; Qoss and Eoss at 25 V and at 100 V by integrating Coss over voltage on the ladder (the sheets of superjunction and GaN parts print both); the Miller ratio Crss/Ciss at 25 V. From the VGS view, Ciss at VGS = 10 V over Ciss at 0 V (the oxide step).

**Outputs.**

- `ciss@{v}` (F): input capacitance at VDS = v, VGS = 0
- `coss@{v}` (F): output capacitance
- `crss@{v}` (F): reverse transfer capacitance
- `crss_1v_over_25v`: the shape of the Crss fall
- `coss_1v_over_25v`: the shape of the Coss fall
- `qoss@{v}` (C): Coss integrated over voltage, at 25 and 100 V
- `eoss@{v}` (J): the energy stored in Coss, at 25 and 100 V
- `miller_ratio@25V`: Crss/Ciss at 25 V
- `ciss_10v_over_0v@vds0`: the gate-voltage dependence of Ciss at VDS = 0

Curves: Ciss (ciss against vds, log); Coss (coss against vds, log); Crss (crss against vds, log); Eoss (eoss against vds, log); Ciss vs VGS (ciss_vgs against vgs, lin); Crss vs VGS (crss_vgs against vgs, lin).

**Card parameters that drive it:** CGSO, CGDO, CGBO, CBD, CBS, PB, MJ, CGDMAX, CGDMIN, A, CGS, CJO, M, VJ, TOX.

**A high value.** Crss(1 V)/Crss(25 V) near 1 is a constant Miller capacitance: a level 1 card, whose switching waveforms and plateau will be wrong.

**A low value.** Zero everywhere is a card with no capacitance (absent); a Coss that does not fall is a missing CBD.

**What it cannot tell.** Capacitances with the channel conducting (the sheets take them at VGS = 0), and the non-quasi-static effects at the switching edge.

**Standard.** resembles the Ciss/Coss/Crss methods of JEDEC JESD24 at 1 MHz, read as a meter reads a low-impedance capacitance

#### Gate charge, VGS against Qg at constant gate current (`mosfet-gate-charge`)

Group `capacitance` · analysis `tran` · engines qspice, ngspice, ltspice · symbols Qg, Qgs, Qgd, Vplateau.

The curve a gate driver is sized from. A constant current into the gate makes the gate voltage climb; it climbs to the threshold (Qgs(th)), on to the plateau (Qgs) where the drain starts to fall, holds there while Cgd is discharged by the whole drain swing (Qgd, the Miller charge), and climbs again to the drive voltage (Qg total). The plateau voltage is Vth plus what the transconductance needs for the load current. The sheets fix the load current near the rating and the supply at a fraction of the rating that differs by maker; here three universal points are run so that any sheet's point is bracketed. Qgd/Qgs(th) is kept as the parasitic-turn-on figure of a half-bridge.

**Circuit.** A constant current into the gate (1 mA; 10 mA for the 10 A point), the gate caught at 15 V by a diode to a rail; the drain fed the load current by an ideal source with a clamp diode to the supply, so that the drain sits at the rail until the transistor takes the current and then falls; source grounded. The gate voltage against time is the charge curve (Q = IG × t from the current's start). Three points: 100 mA at 10 V, 1 A at 30 V, 10 A at 100 V.

Drawing: DUT; gate current source; load current source with a clamp diode to VDD; probe on the gate and the drain. Differs from the netlist: the gate's own clamp at 15 V is not drawn.

**Conditions.** {points: [{id: 0.1, vdd: 10, ig: 0.001}, {id: 1, vdd: 30, ig: 0.001}, {id: 10, vdd: 100, ig: 0.01}], vgs_clamp: 15, vgs_read: [4.5, 10], t_start_s: 1e-07, t_end_s: 5e-05, max_step_s: 1e-08, curve_points: 80, temp_c: 25}

**The deck (QSPICE), line by line.**

- `IG 0 g PULSE(0 0.001 1e-07 1e-09 1e-09 1 2)` — the gate current, 1 mA from 100 ns on
- `RGL g 0 1e9` — a path to ground for the operating point, 1 GΩ
- `IL vdd d 1` — the load: 1 A pushed into the drain, caught at 30 V until the transistor conducts
- `DCL d cl DCLMP`
- `VCL cl 0 30`
- `VDD vdd 0 30`
- `DCLG g clG DCLMP` — the gate caught at 15 V
- `VCLG clG 0 15`
- `M1 d g 0 DUT`
- `.tran 1e-08 5e-05 0 1e-08` — 50 µs, long enough for the gate to reach its clamp

**Extraction.** From VGS(t) and VDS(t): Qgs(th) at the threshold (1 mA, diode-connected, from the transfer sweep), Qgs where the drain has fallen by 10 % (the plateau's start), Qgd to where it has fallen by 90 % (the plateau's length), Qg at 4.5 and at 10 V, Vplateau as the gate voltage at the plateau's middle, Qsw = Qgs − Qgs(th) + Qgd. A deck whose drain never fell (the current is above what the card can pass) is n/a.

**Outputs.**

- `qgs_th@{id},{vdd}` (C): gate charge to the threshold
- `qgs@{id},{vdd}` (C): gate charge to the plateau
- `qgd@{id},{vdd}` (C): the Miller charge, the plateau's length
- `qg@4.5V,{id},{vdd}` (C): total gate charge to 4.5 V
- `qg@10V,{id},{vdd}` (C): total gate charge to 10 V
- `vplateau@{id},{vdd}` (V): the plateau voltage
- `qsw@{id},{vdd}` (C): Qgs − Qgs(th) + Qgd, the switching charge
- `qgd_over_qgsth@{id},{vdd}`: the parasitic-turn-on ratio

Curves: VGS vs Qg, ID=100mA, VDD=10V (vgs against q, lin, at ID = 0.1, VDD = 10); VGS vs Qg, ID=1A, VDD=30V (vgs against q, lin, at ID = 1, VDD = 30); VGS vs Qg, ID=10A, VDD=100V (vgs against q, lin, at ID = 10, VDD = 100). Shown first: ID = 1, VDD = 30.

**Card parameters that drive it:** CGSO, CGDO, CGDMAX, CGDMIN, A, CGS, VTO, KP, RG.

**A high value.** A Qgd/Qgs(th) above 1.5 is a part prone to parasitic turn-on in a half-bridge; a plateau of 7 V is a high threshold or a low gfs.

**A low value.** No plateau at all is a card with constant Cgd (level 1): the curve is a straight line and the Miller charge does not exist.

**What it cannot tell.** The gate charge with the real driver's impedance and loop inductance.

**Standard.** resembles the gate charge method of JEDEC JESD24-2 at constant gate current

#### td(on), tr, td(off) and tf in a resistive-load switch, and Eon/Eoff clamped-inductive (`mosfet-switching`)

Group `switching` · analysis `tran` · engines qspice, ngspice, ltspice · symbols td(on), tr, td(off), tf, Eon, Eoff.

The four times every MOSFET sheet quotes at one point (VDD, ID, RG, VGS) and draws against ID or RG. In a MOSFET there is no stored charge, so the times are the gate charging through RG: td(on) to threshold, tr across the plateau (the Miller charge against RG), td(off) back to the plateau, tf across it again. A model with the wrong Crss shape gets tr and tf wrong by the same factor. A second fixture, the clamped inductive load that converter sheets use, gives the switching energies Eon and Eoff, which are what a designer actually loses.

**Circuit.** Resistive: 30 V through RL = VDD/ID, the gate driven 0 to 10 V through RG = 10 Ω with 2 ns edges, 2 µs on, at 100 mA, 1 A and 10 A; at 1 A also through 25 Ω, and with a 4.5 V drive. Clamped inductive: the load current from an ideal source with a freewheeling diode to the supply (the inductor as the current source it is over the edges), a 10 Ω / 1 nF snubber on the drain, two gate pulses; the current is established by the first and the switching read on the second; Eon and Eoff as the integral of VDS × ID over the edges, at 1 A and 10 A.

Drawing: DUT; VDD; RL; gate pulse through RG; probe on the drain (resistive); inductor with a freewheeling diode to VDD (inductive). Differs from the netlist: the inductive deck's inductor is a current source with the diode across it, and a snubber.

**Conditions.** {vdd: 30, id_ladder: [0.1, 1, 10], rg: [10, 25], v_on: [10, 4.5], variants_id: 1, t_start_s: 1e-07, edge_s: 2e-09, t_on_s: 2e-06, t_after_s: 2e-06, max_step_s: 5e-10, curve_points: 80, inductive: {vdd: 30, id: [1, 10], rg: 10, t_on_s: 5e-06, gap_s: 5e-06, edge_s: 2e-08, r_fw: 0.02, r_snub: 10, c_snub: 1e-09, window_s: 3e-07, max_step_s: 1e-09}, temp_c: 25}

**The deck (QSPICE), line by line.**

- `VDD vdd 0 30` — the supply and the load, 30 Ω in the 1 A deck; an ammeter in the drain
- `RL vdd dl 30`
- `VS dl d 0`
- `VIN in 0 PULSE(0 10 1e-07 2e-09 2e-09 2e-06 1)` — the gate drive through RG: 0 to 10 V, 2 ns edges, 2 µs on
- `RG in g 10`
- `M1 d g 0 DUT`
- `.tran 5e-10 4.104e-06 0 5e-10`
- `IL vdd dl 1` — the inductive deck: the load current from a source with the freewheeling diode, the snubber, two pulses
- `DFW dl dfw DFW`
- `RFW dfw vdd 0.02`
- `VIDM dl d 0`
- `RSN d sn 10`
- `CSN sn 0 1e-09`

**Extraction.** td(on) from the gate's 10 % to ID at 10 %; tr 10 to 90 % of ID; td(off) from the gate's fall (90 %) to ID at 90 %; tf 90 to 10 %. Eon over a 300 ns window around the second pulse's turn-on, Eoff around its turn-off. A step whose drain never fell below 10 % of VDD did not switch, and is reported by how far it got.

**Outputs.**

- `td_on@{id},{vdd},{rg},{von}` (s): turn-on delay
- `tr@{id},{vdd},{rg},{von}` (s): rise time of the drain current, 10 to 90 %
- `td_off@{id},{vdd},{rg},{von}` (s): turn-off delay
- `tf@{id},{vdd},{rg},{von}` (s): fall time, 90 to 10 %
- `on@{id},{vdd},{rg},{von}`: how far the drain fell, 1.0 = fully on
- `eon@{id},{rg}` (J): turn-on energy, clamped inductive at 30 V
- `eoff@{id},{rg}` (J): turn-off energy

Curves: VDS(t), ID=100mA, VDD=30V, RG=10Ω, VON=10V (vds against t, lin, at ID = 0.1, VDD = 30, RG = 10, VON = 10); VDS(t), ID=1A, VDD=30V, RG=10Ω, VON=10V (vds against t, lin, at ID = 1, VDD = 30, RG = 10, VON = 10); VDS(t), ID=10A, VDD=30V, RG=10Ω, VON=10V (vds against t, lin, at ID = 10, VDD = 30, RG = 10, VON = 10); VDS(t), ID=1A, VDD=30V, RG=25Ω, VON=10V (vds against t, lin, at ID = 1, VDD = 30, RG = 25, VON = 10); VDS(t), ID=1A, VDD=30V, RG=10Ω, VON=4.5V (vds against t, lin, at ID = 1, VDD = 30, RG = 10, VON = 4.5). Shown first: ID = 1, RG = 10, VON = 10.

**Card parameters that drive it:** CGSO, CGDO, CGDMAX, CGDMIN, A, RG, VTO, KP, RD.

**A high value.** tr that does not shrink when RG falls from 25 to 10 Ω is a card with a large internal RG or a drain-side time constant.

**A low value.** tr and tf of nanoseconds at 10 A with RG = 25 Ω is a card with no Crss: its switching loss will be understated by an order of magnitude.

**What it cannot tell.** The times with the sheet's own fixture, package inductance, the driver's own impedance; transients differ by up to 1 % between simulators.

**Standard.** resembles the resistive switching time method of JEDEC JESD24 and the clamped inductive fixture of converter data sheets, simplified

#### The body diode, forward drop, third-quadrant conduction and reverse recovery (`mosfet-body-diode`)

Group `recovery` · analysis `dc` · engines qspice, ngspice, ltspice · symbols VSD, IS, trr, Qrr.

Every vertical MOSFET carries a diode from source to drain. Its forward drop (0.7 to 1.2 V) is the voltage the freewheeling current costs in a bridge, and with the channel also on (VGS = 10 V) the current splits between channel and diode, the third quadrant, which the sheets of modern parts draw as IS against VSD at several VGS and which is where a class-AB output stage's idle current crosses over. Its reverse recovery, trr and Qrr, is the loss and the ringing of every hard-switched bridge; the sheets quote them at IF = IS and di/dt = 100 A/µs. In a card the diode is the IS/N/RS of the MOS body junction (level 1/3), or a separate diode with TT in a VDMOS card or a subcircuit; a card without TT has a diode that recovers in zero time, which no silicon diode does.

**Circuit.** Forward: the source current forced by the behavioural dial from 1 µA to 100 A with the drain grounded, a clamp at 5 V for a card without a diode, VSD read; copies at VGS = 0, 4.5 and 10 V. Recovery: a current source holds IF through the diode, then ramps to −IF at 100 A/µs; a clamp diode to ground takes the current once the body diode has recovered; the drain current is read through its ammeter.

Drawing: DUT reversed; forced source current; voltmeter source to drain (forward); current ramp and clamp (recovery). Differs from the netlist: the recovery fixture is a ramped current source, not an inductor and a switch.

**Conditions.** {is_sweep: {from: 1e-06, to: 100, per_decade: 20, unit: A}, vgs: [0, 4.5, 10], is_ladder: [0.001, 0.01, 0.1, 1, 10, 50, 100], recovery: {if: [1, 10], didt_a_per_us: [100], t_forward_s: 2e-06, t_after_s: 2e-06, present_fraction: 0.05, present_trr_s: 2e-09}, temp_c: 25}

**The deck (QSPICE), line by line.**

- `BS0 0 s0 I=exp(2.302585092994046*V(x))` — the source current forced, 10 to the power of the dial, pushed into the source of the first copy
- `DCLs0 s0 cls0 DCLMP` — the clamp at 5 V, for a card without a diode
- `VCLs0 cls0 0 5`
- `VG0 g0 s0 0` — the gate at the source (VGS = 0); the next copies at 4.5 and 10 V
- `MD0 0 g0 s0 DUT` — the transistor with its drain grounded
- `.dc VX -6 2 0.05` — 1 µA to 100 A
- `IF 0 s PULSE(1 -1 2e-06 2e-08 1 1 2)` — the recovery deck: IF then −IF at 100 A/µs into the source, the drain read, a clamp to ground
- `VDM d 0 0`
- `MR d s s DUT`
- `DCLP 0 s DCLMP`

**Extraction.** VSD at each ladder current and VGS; the diode's IS and n fitted between 1 mA and 100 mA at VGS = 0. From the recovery deck: Irrm, trr from the zero crossing to 10 % of Irrm on the recovery, Qrr as the integral, and the softness factor; absent when the recovery current never exceeds 5 % of IF or lasts under 2 ns (a junction capacitance's spike, not stored charge: no TT).

**Outputs.**

- `vsd@{is},{vgs}` (V): source-drain voltage at the ladder current and gate voltage
- `is_diode` (A): saturation current of the body diode from the forward fit
- `n_diode`: its ideality factor
- `irrm@{if},{didt}` (A): peak reverse recovery current
- `trr@{if},{didt}` (s): reverse recovery time, or absent
- `qrr@{if},{didt}` (C): reverse recovery charge
- `softness@{if},{didt}`: the recovery's tail over its rise
- `recovery@{if},{didt}`: present, or absent when the reverse current is a capacitive spike only

Curves: IS vs VSD, VGS=0V (is against vsd, log, at VGS = 0); IS vs VSD, VGS=4.5V (is against vsd, log, at VGS = 4.5); IS vs VSD, VGS=10V (is against vsd, log, at VGS = 10); I(t) recovery, IF=1A, di/dt=100A/µs (i_rec against t, lin, at IF = 1); I(t) recovery, IF=10A, di/dt=100A/µs (i_rec against t, lin, at IF = 10). Shown first: VGS = 0, IF = 1.

**Card parameters that drive it:** IS, N, RS, RB, CJO, TT, JS, PB.

**A high value.** VSD above 1.3 V at 10 A is a large RB; Qrr in microcoulombs is a TT set for a standard-recovery diode.

**A low value.** A recovery that is absent is TT = 0, the usual case in level 1/3 cards; VSD of a plain junction at 100 A with no series resistance is RB = 0.

**What it cannot tell.** The recovery's temperature dependence, and the snappiness the real part shows, which depends on a doping profile no card carries.

**Standard.** resembles the source-drain diode forward voltage and reverse recovery methods of JEDEC JESD24

#### Threshold, RDS(on), gfs at −55 to 175 °C, and the zero-TC point (`mosfet-temperature`)

Group `temperature` · analysis `dc` · engines qspice, ngspice, ltspice · symbols dVth/dT, RDS(on)(T), VGS(0TC).

Three drifts. The threshold falls by 4 to 7 mV/K, which raises the current at a fixed gate voltage; the mobility falls, which lowers it and nearly doubles RDS(on) between 25 and 150 °C (the positive temperature coefficient that lets MOSFETs share current when paralleled as switches); the body diode's drop falls by about 2 mV/K. The first two cancel at one current, the zero-temperature- coefficient point, below which a MOSFET's current rises with heat (thermal runaway in linear mode, the reason class-AB stages biased below it need compensation) and above which it falls. In a card the threshold drift is TCV/VTOTC or the physics of level 3; the mobility drift is BEX/KPTC or absent, in which case the model has no positive RDS(on) coefficient and no zero-TC point.

**Circuit.** A transfer deck per temperature (−55, 25, 100, 125, 150, 175 °C): the 15 V copy, the diode-connected copy, and a 0.1 V copy whose current at 10 V and 4.5 V on the gate gives RDS(on).

Drawing: DUT; the three copies; a thermometer symbol.

**Conditions.** {temps_c: [-55, 25, 100, 125, 150, 175], vds: 15, vds_linear: 0.1, vgs_sweep: {from: -2, to: 15, step: 0.01, unit: V}, rdson_vgs: [10, 4.5], gfs_id: 1, ztc_hot: 150, ztc_min_id: 0.0001}

**The deck (QSPICE), line by line.**

- `.temp -55` — the first deck, at −55 °C; then 25, 100, 125, 150 and 175 °C
- `VT dt 0 15` — the 15 V copy, the diode-connected copy and the 0.1 V copy
- `MT dt g 0 DUT`
- `VTD dtd g 0`
- `MTD dtd g 0 DUT`
- `VL dl 0 0.1`
- `ML dl g 0 DUT`
- `VGS g 0 0`
- `.dc VGS -2 15 0.01`

**Extraction.** Vth (1 mA, diode-connected) at each temperature and its slope between −55 and 175 °C; RDS(on) at 10 V (and 4.5 V) at each temperature over 25 °C, and the exponent of its power-law fit against absolute temperature; gfs at 1 A at each temperature over 25 °C. The zero-TC point is where the 25 and 150 °C transfer curves cross on the grid above 100 µA, as gate voltage and drain current; absent when they do not cross (no mobility drift in the card).

**Outputs.**

- `vth@1mA,{T}` (V): threshold at each temperature, diode-connected
- `dvth_dt` (V/K): slope of the threshold between −55 and 175 °C
- `rdson_t_over_25@{vgs}`: RDS(on) at each temperature t over 25 °C (rdson_m55_over_25, rdson_150_over_25), at 10 V and 4.5 V
- `rdson_t_exponent`: exponent of RDS(on) against absolute temperature, at 10 V
- `gfs_t_over_25@1A`: gfs at each temperature t over 25 °C
- `vgs_0tc` (V): gate voltage of the zero-temperature-coefficient point, or absent
- `id_0tc` (A): drain current at that point

Curves: ID, −55°C (id against vgs, lin, at T = -55); ID, 25°C (id against vgs, lin, at T = 25); ID, 100°C (id against vgs, lin, at T = 100); ID, 125°C (id against vgs, lin, at T = 125); ID, 150°C (id against vgs, lin, at T = 150); ID, 175°C (id against vgs, lin, at T = 175); Vth (vth against T, lin); RDS(on) normalised (rdson_ratio against T, lin). Shown first: T = all.

**Card parameters that drive it:** TCV, VTOTC, BEX, KPTC, UO, XTI, EG, TOX, NSUB.

**A high value.** RDS(on) at 150 °C more than 2.2 times its 25 °C value is a BEX set too negative; a Vth slope above 8 mV/K is a TCV copied from a different process.

**A low value.** An RDS(on) ratio of exactly 1.000 is a card without mobility drift: paralleled switches will share perfectly in simulation and a linear-mode stage will not run away; absent for the zero-TC point.

**What it cannot tell.** Self-heating; the sheets' RDS(on) at 150 °C is a pulsed junction temperature, and a real switch at rated current is hotter than its case.

**Standard.** resembles the VGS(th) vs Tj and normalised RDS(on) vs Tj charts of every power MOSFET sheet; IEC 60747-8

#### Voltage noise, the 1/f corner and NF (`mosfet-noise`)

Group `noise` · analysis `noise` · engines qspice, ngspice · symbols en, NF.

A MOSFET's noise is the channel's thermal noise through gfs, as a JFET's is, plus a 1/f part that in an oxide-gated device is larger and reaches further up (corners of kilohertz to tens of kilohertz are normal), which is why MOSFETs are rarely first stages and why the few audio MOSFET sheets (lateral 2SK1058, the small-signal 2N7000 family) do not print noise. The current noise is negligible (no gate current). In a card it depends on KF and AF, which nearly every power MOSFET card leaves at zero.

**Circuit.** As the JFET measurement, at VDS = 10 V, the gate biased for 1, 10, 100 mA and 1 A, RG = 0 for en; a run at 100 mA with RG = 1 kΩ for NF.

Drawing: DUT; VDS source 10 V; gate bias; noise source with RG; sensing in the drain. Differs from the netlist: the output is a current-controlled voltage source into 1 MΩ, as in the bipolar bench.

**Conditions.** {vds: 10, id_ladder: [0.001, 0.01, 0.1, 1], nf: {id: 0.1, rg: 1000, f: 1000}, f_points: [10, 100, 1000, 10000, 100000], noise_sweep: {from: 1, to: 1e+06, per_decade: 20, unit: Hz}, audio_band: [20, 20000], temp_c: 25}

**The deck (QSPICE), line by line.**

- `VSENSE d dd 0`
- `VD dd 0 10`
- `RG in g 0.001` — the gate bias for the step (from the transfer sweep); VIN rides on it
- `M1 d g 0 DUT`
- `H1 out 0 VSENSE 1000`
- `RLOAD out 0 1meg`
- `.noise V(out) VIN dec 20 1 1000000`

**Extraction.** en at each frequency and current; the corner where en is √2 times its 10 kHz value, absent when flat; NF at 1 kHz, 100 mA, 1 kΩ; the 20 Hz to 20 kHz integrated noise, flat and A-weighted.

**Outputs.**

- `en@{f},{id}` (V/√Hz): voltage noise density
- `en_corner@{id}` (Hz): the 1/f corner, or absent
- `nf@1kHz,100mA,1kΩ` (dB): noise figure at RG = 1 kΩ
- `vn_20_20k@{id}` (V): input-referred noise, 20 Hz to 20 kHz rms
- `vn_a_weighted@{id}` (V): the same, A-weighted
- `one_over_f`: present when any current shows a 1/f corner, else absent (KF = 0)

Curves: en, 1mA (en against f, log, at ID = 0.001); en, 10mA (en against f, log, at ID = 0.01); en, 100mA (en against f, log, at ID = 0.1); en, 1A (en against f, log, at ID = 1); en at 10Hz (en_id against id, log, at f = 10); en at 1kHz (en_id against id, log, at f = 1000); en at 10kHz (en_id against id, log, at f = 10000). Shown first: ID = 0.1.

**Card parameters that drive it:** KF, AF, KP, RS, RG, NLEV.

**A high value.** A corner above 100 kHz is a KF set for a submicron CMOS process in a discrete card.

**A low value.** A flat spectrum is KF = 0: absent for the corner.

**What it cannot tell.** The part's noise: makers do not measure it on power parts, and the lateral audio parts' sheets are silent.

**Standard.** resembles the spot noise method (MIL-STD-750-3); few MOSFET sheets print it

#### Is there any breakdown, and what leaks (`mosfet-breakdown`)

Group `breakdown` · analysis `dc` · engines qspice, ngspice, ltspice · symbols V(BR)DSS, IDSS, IGSS.

A level 1 or 3 card has no drain breakdown; a VDMOS card has BV/IBV/NBV and a subcircuit often a zener across the body diode, so the absence is less universal than in bipolar cards. The gate oxide's breakdown and leakage are in no card at all. IDSS, the off-state leakage the sheets quote at the rated voltage, is the body diode's reverse current in the card and far below the part's.

**Circuit.** Drain to source 0 to 1000 V with the gate tied to the source; the current read. Gate to source −30 to +30 V with the drain tied to the source; the gate current read.

Drawing: DUT; swept source; ammeter. Differs from the netlist: two decks drawn as one.

**Conditions.** {vds_sweep: {from: 0, to: 1000, step: 1, unit: V}, vgs_sweep: {from: -30, to: 30, step: 0.1, unit: V}, breakdown_current: 0.001, leakage_points: {idss: [25, 100, 300], igss: 20}, temp_c: 25}

**The deck (QSPICE), line by line.**

- `VA sw da 0` — drain-source, the gate grounded: the swept node drives the drain through a 0 V source
- `MA da 0 0 DUT`
- `VSW sw 0 0`
- `.dc VSW 0 1000 1`
- `VB sw gb 0` — gate-source, the drain grounded
- `MB 0 gb 0 DUT`
- `.dc VSW -30 30 0.1`

**Extraction.** V(BR)DSS as the first voltage at which ID passes 1 mA, else absent; IDSS at 25, 100 and 300 V; IGSS at ±20 V (below 10 pA they are the simulators' gmin floor).

**Outputs.**

- `vbr_dss` (V): drain-source breakdown with the gate grounded, or absent
- `idss@{v}` (A): off-state drain leakage at 25, 100 and 300 V
- `igss@20V` (A): gate leakage at +20 V
- `igss@-20V` (A): gate leakage at −20 V

**Card parameters that drive it:** BV, IBV, NBV, JS, IS.

**A low value.** A breakdown that appears is a VDMOS or subcircuit card; the figure is then worth comparing with the sheet.

**What it cannot tell.** The part's breakdown when absent; gate oxide rupture, never.

**Standard.** resembles the V(BR)DSS, IDSS and IGSS methods of JEDEC JESD24 and MIL-STD-750-3

#### Two reference stages' harmonic distortion (model against model only) (`mosfet-distortion`)

Group `distortion` · analysis `tran` · engines qspice, ngspice · symbols THD, HD2, HD3.

What the audio user wants and no sheet gives. Two fixed stages, because a MOSFET is used two ways in audio: as a common-source gain stage (small-signal and lateral parts) and as a source follower in an output stage (lateral and vertical power parts). In the follower the distortion comes from the transconductance's curvature against the load current and from the Crss(VDS) modulation at high frequency; a single-ended follower into a resistive load at a fixed bias shows both. The common-source stage shows the power law directly.

**Circuit.** Common source: VDD = 20 V, ID = 10 mA from an ideal sink to −10 V under a 100 Ω source resistor bypassed to ground, drain load 1 kΩ, driven from 1 kΩ with the gate at 0 V DC; 1 V peak out at 1 kHz. Follower: VDD = 25 V, ID = 100 mA from an ideal sink to −10 V, load 100 Ω AC-coupled, driven from 100 Ω at 1 kHz and 20 kHz and from 1 kΩ at 20 kHz (the Crss figure); 1 V peak out. A probe run at 20 mV sets each stage's input; ten cycles simulated, the last four analysed.

Drawing: DUT; current sink; RS bypassed; RL; VDD; sine source through RS_in; probe. Differs from the netlist: the follower is a second deck.

**Conditions.** {cs: {vdd: 20, vss: 10, id: 0.01, rs: 100, rl: 1000, rs_in: 1000, f: 1000}, sf: {vdd: 25, vss: 10, id: 0.1, rl: 100, rs_in: [100, 1000], f: [1000, 20000]}, vout_peak: 1, cycles: 10, analysed_cycles: 4, steps_per_cycle: 4096}

**The deck (QSPICE), line by line.**

- `VSS vss 0 -10` — the common-source stage: the sink's rail, the supply, the drive through 1 kΩ (20 mV for the probe run)
- `VDD vdd 0 20`
- `RIN in g 1000`
- `VIN in 0 SIN(0 0.02 1000)`
- `RL vdd d 1000`
- `RS s sx 100`
- `CS sx 0 1000u`
- `IS sx vss 0.01`
- `M1 d g s DUT`
- `.tran 2.44140625e-07 0.003 0 2.44140625e-07` — three cycles for the probe, ten for the measurement, 4096 steps per cycle
- `IS s vss 0.1` — the follower deck: the drain at VDD, the sink on the source, the load AC-coupled
- `CL s l 1000u`
- `RL l 0 100`
- `M1 vdd g s DUT`

**Extraction.** As in the bipolar bench: harmonics 2 to 10 by Goertzel over the last four cycles; THD, HD2, HD3 per stage, drive impedance and frequency; the ratio of follower THD at 20 kHz with 1 kΩ drive over 100 Ω drive, which is the Crss modulation figure.

**Outputs.**

- `thd_cs`: THD of the common-source stage at 1 V peak out, 1 kHz
- `hd2_cs`: its second harmonic over the fundamental
- `hd3_cs`: its third harmonic
- `gain_cs`: the stage's gain at 20 mV
- `thd_sf@{rs_in},{f}`: THD of the follower at 1 V peak out
- `hd2_sf@{rs_in},{f}`: its second harmonic
- `hd3_sf@{rs_in},{f}`: its third harmonic
- `gain_sf`: the follower's gain at 20 mV
- `crss_distortion_ratio`: follower THD at 20 kHz, 1 kΩ drive over 100 Ω drive

**Card parameters that drive it:** KP, VTO, THETA, LAMBDA, RS, CGDMAX, CGDMIN, A, CGDO, CGSO.

**A high value.** Only against another model of the same part. A Crss ratio near 1 is a constant Miller capacitance (level 1).

**What it cannot tell.** The distortion of any real circuit; it is a comparison between models.

**Standard.** none

#### Do the three simulators agree? (`mosfet-agreement`)

Group `dc` · analysis `derived` · engines qspice, ngspice, ltspice.

As the bipolar agreement. MOSFET cards disagree most on the VDMOS extensions (ngspice's reading of Cgdmax/a, mtriode, Ksubthres lags LTspice's), on level 3 parameters QSPICE treats differently (THETA, KAPPA), and on subcircuit elements with vendor-specific syntax (PSpice TABLE, VALUE and IF expressions in behavioural capacitors). The disagreeing ids say which group.

**Conditions.** {tolerances: [0.01, 0.05], floors: {F: 1e-16, s: 1e-12, A: 1e-14, C: 1e-15}}

**Extraction.** For each published output, the spread (max − min over the mean) across the engines that produced it, classed as within 1 %, within 5 % or beyond; values below the floors count as zero.

**Outputs.**

- `agree_1pct`: share of outputs on which every engine agrees within 1 %
- `agree_5pct`: share within 5 %
- `odd_engine`: the engine most often alone outside 5 %, or none
- `disagreeing`: the measurement ids where the engines differ by more than 5 %

**What it cannot tell.** Which engine is right.

**Standard.** none
<!-- measurements:end -->

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

## Where this stands

Every measurement above was run once on ngspice, one model per part, for J201, 2N5457, 2N3819, 2N7000,
BS170 and IRF510 ([bench-preview-2026-10.md](bench-preview-2026-10.md)). The entries in
`data/bench/measurements.yaml`, the decks in the simulator images, the records and the site's pages are
pending: [bench-roadmap.md](bench-roadmap.md) is the checklist.
