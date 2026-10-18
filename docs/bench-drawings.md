# The bench drawings: how every measurement circuit is drawn

Companion to [model-characterisation.md](model-characterisation.md), [fet-characterisation.md](fet-characterisation.md)
and [opamp-characterisation.md](opamp-characterisation.md). Every measurement of `data/bench/measurements.yaml`
whose `circuit` is simulated has a drawing, `data/bench/drawings/<id>.svg`, shown on the method page beside the
deck lines it stands for. The drawings are typeset by LaTeX and circuitikz from `docker/circuitikz/drawings/<id>.tex`,
which `docker/circuitikz/benches.py` writes (the building blocks and the bipolar benches), with
`benches_fet.py` (JFET and MOSFET) and `benches_opamp.py` (op-amps) alongside it; `make bench-drawings-all`
rewrites and typesets every one, `make bench-drawings NAME=<id>` one, in the TeX Live image
(`make circuitikz-image`) or, with `LOCAL=1`, with the machine's own TeX Live. The style is `bench.sty`.

## One style for every kind

- **Colours.** Blue is what the bench sets: every source, the supply rails, the thermometer. Red is what the
  bench measures: the meters and the quantities they read. Green, in small monospace, is the deck's own node
  name at that point, so that a deck line can be found in the drawing. Black is the rest: the device under
  test, the passive parts and the wires. The colour key sits under the title of every drawing.
- **Meters.** A current is read by a circled **A** with the wire running straight through it (a 0 V source in
  the deck); a voltage by a circled **V** whose two leads stop short inside the circle (a node the deck reads).
  An AC reading is written in lower case ($i_d$, $v_{out}$), a DC one in capitals.
- **Sources.** A voltage source is a circle with + and −, the + where the deck's first node is; a current
  source a circle with an arrow in the direction of the deck's current. A behavioural source (the dial
  $10^{V(x)}$) is drawn as the current source it is, and the definitions under the circuit give the sweep
  mathematically ($I_B = 10^k$ A, $k = -9 \dots 0$).
- **Copies.** A deck that packs copies of one circuit (one per collector voltage, per ladder current, per
  gate step) is drawn once, with the list of conditions in the definitions; a measurement made of two
  different circuits shows both, lettered A and B. `drawing.differs_from_netlist` in the catalogue says
  what the drawing simplifies.
- **Opens** are the deck's 1 GΩ to ground, drawn as a short lead and the word; the **thermometer** stands
  for `.temp`; an amplifier's **rails** are short arrows with the voltages beside them.
- Every drawing is the set-up a person would wire, semantically the deck's: the deck lines each one stands
  for are listed in the header of its `.tex`.

## The layouts

- **Transistors** (bipolar, JFET, MOSFET): the device at the centre, emitter or source grounded; the
  collector or drain ammeter straight up to the rail and the supply at the right, + up; the base or gate
  source at the left, through an ammeter where the gate current is read, with its voltmeter further left.
  A forced current comes down into the terminal from a grounded rail, with the clamp diode and the
  voltmeter beside it; a device run backwards is drawn upside down and says so.
- **Bipolar twins.** Each bipolar drawing has a `-pnp` twin: the symbol mirrored, every source reversed, the
  values written as magnitudes. FETs and amplifiers have none: a P-channel card runs with every source
  reversed and the drawing is the same.
- **Amplifiers**: the op-amp with its non-inverting input up (down for the inverting fixtures, whose
  feedback then runs over the top), the input source at the left, the output node at the right with the
  voltmeter, the load resistor and the load capacitor down to ground, the feedback around the bottom. The
  model's own pin order is put in by the job builder; the drawing shows in+, in−, V+, V−, out.
