# How each field-effect measurement circuit is assembled

Companion to [fet-characterisation.md](fet-characterisation.md). For every measurement it says what is on the bench, how it is
wired, what is read where, what is stepped or swept, and how the drawing is laid out, so that the circuit
can be drawn (the `.tex` files in `docker/circuitikz/fet/` are circuitikz, one per measurement id, each with a
header listing the deck lines it stands for, as `benches.py` writes them for the bipolar bench; the
`.svg` files in `data/bench/drawings/` are their rendering) or redrawn in xcircuit or any other tool. A "copy" is one more instance
of the transistor in the same deck; the drawing shows one and says how many there are.

## Drawing conventions (the same as the bipolar bench)

- **DUT** in the middle, drawn as an N-channel JFET or an N-channel enhancement MOSFET with the body
  tied to the source, labelled `DUT`. A P-channel card is run with every source reversed; the drawing is
  the same.
- **Source grounded** unless the measurement says otherwise (the body diode and the forced-current
  decks put something in the source lead).
- **Drain supply** on the right, a DC source to ground, with an **ammeter in the drain** (a 0 V source
  in the deck; drawn as a circled A). The supply's label gives the fixed voltage or, for a sweep, the range
  with "→ swept".
- **Gate drive** on the left: a voltage source to ground, a current source where the gate is fed a
  current (gate charge), a pulse source for transients, a sine source for AC. An ammeter in the gate
  lead where the gate current is read.
- **Forced drain current**: a current source pulling the drain current out of the drain (the
  behavioural dial `10^V(x)` in the deck), a clamp diode from the drain to a rail (30 V) and a
  **voltmeter** drain to source (a circled V).
- **Stepped copies** are drawn once with the step written on the stepping source ("k = 0…5", "2…15 V
  or auto"). A note under the drawing says how many copies there are.
- **Opens** are 1 GΩ resistors to ground; a drain made AC-open is a 1 H inductor.
- **Temperature** is a boxed thermometer symbol with the list of temperatures.
- **Notes** under the drawing carry what differs from the netlist and the ladder values.

The layout grid is: DUT at (0, 0); drain lead up 0.3 then the ammeter (1.4 long) then 2.0 right to the
supply (2.4 long, down to ground); gate lead 0.5 left, ammeter 1.4 or a wire, 0.5 more, then the gate
source (1.9 long, down to ground); a second copy at x = 8, a third at x = 16; titles at y = 3.3, notes at
y = −3.6.

---

## JFET

### `jfet-runs` — does the card load?
- **Parts.** DUT; DC source 10 V on the drain; 0 V source (ammeter) in the drain; 0 V source (ammeter)
  from gate to ground.
- **Wiring.** Source to ground. Drain → ammeter → 10 V source → ground. Gate → ammeter → ground.
- **Read.** IDSS through the drain ammeter; IG through the gate ammeter, both at `.op`.
- **Drawing.** The basic layout, gate source replaced by the ammeter to ground (VGS = 0).

### `jfet-tracer` — output characteristics
- **Parts.** One DUT per gate step (5 auto steps, 9 universal × 5); one shared swept drain source; a 0 V
  ammeter in each drain; one DC gate source per copy at −k × step.
- **Wiring.** All sources to ground; every drain through its own ammeter to the one swept node; every
  gate to its own fixed source.
- **Read.** Each copy's drain current against the swept voltage, 0 → 25 V in 20 mV; the same data cut at
  2 V for the ohmic view.
- **Stepped.** VGS: auto = VGS(off)/5 from `jfet-transfer`, or 0.05, 0.1, 0.2, 0.25, 0.5, 1, 1.5, 2, 3 V.
- **Drawing.** Basic layout; drain source labelled "0 → 25 V, swept"; gate source "−k·step, k = 0…5";
  note: one copy per step, drawn as one.

### `jfet-transfer` — ID against VGS
- **Parts.** Four DUTs; DC drain sources 5, 10, 15, 20 V; one shared swept gate source; ammeters in each
  drain and one in the gate lead.
- **Wiring.** Sources to ground; drains through ammeters to their supplies; all gates to the swept source
  through the gate ammeter.
- **Read.** ID per copy and IG against VGS, −10 → +0.6 V in 5 mV.
- **Drawing.** Basic layout with gate ammeter; drain source labelled with the four voltages; "→ swept" at
  the gate; note: four copies, drawn as one.

### `jfet-gm` — gfs, gos
- **Parts.** Copy A: DUT, drain DC 10 V (and 15 V), gate DC bias + 1 V AC. Copy B: DUT, gate DC bias only,
  drain DC 10 V + 1 V AC. One pair per ladder current. A third deck: four copies at fixed gate bias with a
  swept drain source, 0 → 25 V (gos against VDS).
- **Wiring.** As the basic layout; the AC rides on the gate source (A) or the drain source (B).
- **Read.** A: AC drain current → gfs. B: AC drain current → gos. All at 1 kHz.
- **Drawing.** Two basic layouts side by side (x = 0 and x = 8), the sine symbol on the gate in A and on
  the drain in B; note: one pair per ladder current.

### `jfet-ohmic` — rDS(on) against VGS, VCR linearity
- **Parts.** Left: DUT, drain source ±50 mV (or swept ±0.5 V), ammeter in the drain, stepped gate source
  0 → VGS(off) in 20 steps. Right: DUT, drain swept ±0.5 V, ammeter, gate bias source through 1 MΩ, and a
  second 1 MΩ from the drain node to the gate node (VDS/2 feedback).
- **Wiring.** Left as the basic layout. Right: gate node = junction of the two 1 MΩ; one to the bias
  source, one up and across to the drain node (below the ammeter).
- **Read.** rDS = VDS/ID at each gate step; ID(VDS) fitted to a cubic, with and without feedback.
- **Drawing.** Two layouts side by side; the feedback resistor drawn vertically from the gate node and
  joining the drain wire with a `-|` corner.

### `jfet-gate` — the gate diode
- **Parts.** Left: DUT with drain and source grounded, swept gate source through an ammeter (forward 0 →
  +0.9 V; reverse 0 → −40 V). Right: DUT, swept drain source 0 → 25 V with ammeter, gate bias source
  (for ID 0.1, 1, 3, 10 mA) through an ammeter; one copy per current.
- **Read.** Left: IG against VGS. Right: IG against VDG at fixed ID.
- **Drawing.** Left: basic layout with the drain lead ending in a ground symbol pointing up (drain
  grounded). Right: basic layout with gate ammeter; "0 → 25 V" on the drain.

### `jfet-capacitance` — Ciss, Crss, Cgs, Cgd
- **Parts.** Copy A (Ciss): gate driven by −VR DC + 1 V AC through an ammeter; drain tied to source and
  grounded. Copy B (Crss): drain held at VR by a DC source with ammeter; gate at 0 V DC + 1 V AC with
  ammeter; source grounded. Copy C (Cgs): gate driven as A, drain open through 1 GΩ; (Cgd): the same with
  source open. One set per voltage 0.1 … 30 V.
- **Read.** C = Im(i)/2πf at 1 MHz, series-equivalent: A reads ig, B reads id, C reads ig.
- **Drawing.** Three layouts at x = 0, 8, 16; the tie in A drawn as a loop from the drain lead round to
  the source lead; the 1 GΩ in C upward from the drain to a ground.

### `jfet-frequency` — |yfs| against f, reference stage
- **Parts.** Left: the gfs copy of `jfet-gm` (gate bias + 1 V AC, drain 10 V), swept 1 kHz → 1 GHz.
  Right: common-source stage: VDD 18 V; RD from VDD to drain (chosen for VDS = 9 V); RS from source to
  ground (chosen for ID = IDSS/3) bypassed by 1000 µF; 1 kΩ from a 1 V AC source to the gate; output at
  the drain.
- **Drawing.** Left: basic layout. Right: stage drawn with VDD as an upward rail symbol, RD and RS
  vertical, the bypass capacitor beside RS, input resistor horizontal on the left, output terminal on the
  drain.

### `jfet-noise` — en, in, NF
- **Parts.** DUT; drain 10 V through a 0 V sense source; gate: a DC bias source (for the ladder current)
  in series with the noise reference source VIN, in series with RG (0, 10 MΩ, 1 MΩ) to the gate. In the
  deck, H1 (1000 V/A) turns the sensed current into a voltage across 1 MΩ, which `.noise` refers to VIN.
- **Drawing.** Basic layout; the gate branch shows RG, the sine source labelled "noise reference" and the
  bias source stacked below it; the sense ammeter in the drain; H1 and the load are described in a note
  (not drawn), as the bipolar drawing does.

### `jfet-temperature`
- **Parts.** The transfer copy at VDS = 10 V (swept gate, ammeter in the drain).
- **Drawing.** Basic layout with "→ swept" at the gate and the thermometer box: −55, 25, 100, 125, 150 °C.

### `jfet-switch` — analogue switch
- **Parts.** DUT in series: signal source vs (0 or 1 V) → ammeter → source terminal; drain → RL (1 kΩ or
  10 kΩ) to ground, output across RL; gate ← RG 1 kΩ ← pulse source 0 → −10 V (or 2·VGS(off)), 10 ns edges.
- **Drawing.** DUT with the signal source and ammeter straight below the source terminal, RL to the right
  of the drain, the pulse source and RG on the left.

### `jfet-distortion` — reference stages
- **Parts.** Left: common-source stage, VDD 18 V, RD (VDS = 9 V), RS (ID = IDSS/3) unbypassed, 10 kΩ from
  the sine source to the gate, output at the drain. Right: source follower, drain to VDD 18 V, RS (ID =
  IDSS/3) to ground, output through 100 µF into 10 kΩ, 10 kΩ from the sine source to the gate.
- **Drawing.** Two stages side by side as in `jfet-frequency`, the follower with its coupling capacitor
  and load to the right of the source.

### `jfet-breakdown`
- **Parts.** Copy A: gate ← swept source 0 → −100 V through an ammeter; drain open (1 GΩ up to ground);
  source grounded. Copy B: drain ← swept 0 → 300 V through an ammeter; gate grounded; source open (1 GΩ
  down). Copy C: drain ← swept 0 → 300 V through an ammeter; gate at 2·VGS(off); source grounded.
- **Drawing.** Three layouts at x = 0, 8, 16; the open terminal of each marked with its 1 GΩ.

---

## MOSFET

### `mos-runs`
- **Parts.** Copy 1: gate 10 V, drain 1 V through an ammeter. Copy 2: gate 4.5 V, same. Copy 3: gate
  grounded, drain −1 V through an ammeter (the body diode forward).
- **Drawing.** Two basic layouts side by side: the on-state copy (gate source labelled "10 V (copy 2:
  4.5 V)") and the diode copy with the gate grounded and "VDS = −1 V".

### `mos-tracer`
- **Parts.** One DUT per gate step (universal 2 … 15 V, plus five auto); shared swept drain source 0 → 10 V
  in 10 mV (second deck 0 → 30 V in 50 mV); ammeter in each drain.
- **Drawing.** Basic layout; "0 → 10 / 30 V, swept" on the drain; "VGS step" on the gate; note: auto
  steps are the gate voltages for 10 mA … 1 A at 5 V from `mos-transfer`.

### `mos-transfer`
- **Parts.** Four DUTs with drains at 1, 6, 15, 25 V through ammeters, gates on one swept source −2 → 15 V
  in 10 mV. A fifth, diode-connected: drain tied to gate through the ammeter, the gate node driven by the
  swept source.
- **Drawing.** Left: basic layout, "1, 6, 15, 25 V" on the drain. Right: the diode-connected copy, the
  drain lead going up through the ammeter and back down to the gate node with a `-|` corner, the swept
  source on the left of that node.

### `mos-rdson`
- **Parts.** One DUT per gate step (2.5 … 15 V): gate DC source; drain current pulled by the behavioural
  current source (1 mA → 100 A); clamp diode from the drain node to a 30 V rail; voltmeter drain to source.
  Second deck: current held at 0.1, 1, 10 A, gate swept 0 → 15 V.
- **Drawing.** Current source upward from the drain node to a ground symbol (it pulls current out); the
  clamp diode to the right of it, pointing up to the 30 V rail; the voltmeter further right, down to
  ground; the gate source on the left. Note explains the clamp.

### `mos-gm`
- As `jfet-gm` with VDS = 6 and 15 V; two layouts side by side.

### `mos-capacitance`
- **Parts.** Copy A (Ciss): drain held at VDS through a 1 H inductor from a DC source; gate 1 V AC through
  an ammeter; source grounded. Copy B (Coss): drain driven by VDS DC + 1 V AC through an ammeter; gate
  grounded. Copy C (Crss): drain held at VDS through a DC source with ammeter; gate 0 V DC + 1 V AC. One
  set per VDS 0.1 … 300 V; a second deck at VDS = 0 steps the gate 0 … 10 V.
- **Drawing.** Three layouts at x = 0, 8, 16; the inductor vertical in A's drain lead.

### `mos-gate-charge`
- **Parts.** DUT; gate fed by a constant current source IG (1 or 10 mA) from ground; drain: load current
  source IL (0.1, 1, 10, 50 A) from VDD (10, 30, 100, 300 V) into the drain node, with a clamp diode from
  the drain node up to VDD; probes on VGS(t) and VDS(t).
- **Drawing.** Current source vertical above the drain node to the VDD rail; the clamp to its right, also
  to the rail; the gate current source on the left pointing into the gate; two probe terminals.

### `mos-switching`
- **Parts.** Resistive deck: VDD (10 or 30 V) → RL = VDD/ID → drain; gate ← RG (4.7, 10, 25 Ω) ← pulse
  0 → 10 V (or 4.5 V), 2 ns edges, 2 µs; probe on the drain. Inductive deck: VDD 30 V → L 1 mH → drain,
  ideal diode across L (cathode at VDD), RG 10 Ω, two pulses.
- **Drawing.** Two stages side by side: RL vertical to the rail on the left one; L vertical with the
  freewheeling diode beside it on the right one.

### `mos-body-diode`
- **Parts.** Forward: DUT with its drain grounded; current forced into the source node by the behavioural
  source (1 µA → 100 A); gate source (0, 4.5, 10 V) referred to the source node; voltmeter source to drain.
  Recovery: DUT, gate tied to source; inductor from VR (30 V) to the source node; current source IF (1,
  10 A) into the source node; ideal switch from the source node to ground, closed to commutate at di/dt =
  100, 200, 400 A/µs.
- **Drawing.** Forward copy: drain lead ending in an upward ground, current source and voltmeter below
  the source node, the gate source on the left returning to the source node (not to ground). Recovery
  copy: inductor and VR below the source node, IF and the switch to its right.

### `mos-temperature`
- The transfer copy (VDS = 15 V) with the thermometer box: −55, 25, 100, 125, 150, 175 °C; the RDS(on) and
  body-diode decks are rerun too, as the note says.

### `mos-noise`
- As `jfet-noise` with RG = 0 and 1 kΩ, bias for 1 mA … 1 A.

### `mos-breakdown`
- **Parts.** Copy A: drain ← swept 0 → 1000 V through an ammeter, gate grounded. Copy B: gate ← swept
  ±30 V through an ammeter, drain grounded (ground symbol pointing up on the drain lead).
- **Drawing.** Two layouts side by side.

### `mos-distortion`
- **Parts.** Left: common source, VDD 20 V, RL 1 kΩ, source → 100 Ω → node x, 10 mA current sink from x to
  −VSS, 1000 µF from x to ground, 1 kΩ from the sine source to the gate, output at the drain. Right:
  source follower, drain to VDD 25 V, 100 mA current sink under the source, output through 1000 µF into
  100 Ω, 100 Ω / 1 kΩ from the sine source to the gate.
- **Drawing.** Two stages side by side; the current sinks drawn as current sources to a −VSS rail symbol.

### `jfet-agreement`, `mos-agreement`
- No circuit, no drawing.

---

## Rendering

Each `.tex` is a `standalone` document using `circuitikz` with the `european` option (rectangular
resistors, as the bipolar drawings) and `inductor=american`. `pdflatex <id>.tex && pdftocairo -svg <id>.pdf
<id>.svg` gives the SVG; `docker/circuitikz/fet/generate_fet_drawings.py` writes all 26 `.tex` files and is the place to change a
label or a value once for every drawing (the layout helper `topoA` draws the basic layout; `forced_current`,
`cap_copy`, `cs_stage`, `noise_body` the other recurring ones).
