# The bench beyond bipolar transistors: what is done, what is pending

The bipolar bench ([model-characterisation.md](model-characterisation.md)) runs end to end: catalogue
entries, decks in the three pinned simulator images, records per model hash, the site. The JFET, MOSFET
and op-amp benches are specified and previewed, not yet run through that pipeline. This page is the
checklist; every session that touches the bench starts here and ticks what it finished.

## Done (October 2026)

- [x] **The op-amp survey.** `sei datasheets survey --kind opamp` reads what the makers' sheets measure: 73
      sheets of eight makers, 2,149 figure titles mapped to tests and to the `opa-*` measurements
      ([opamp-characterisation.md](opamp-characterisation.md), `data/datasheets/survey/opamp/`). Sheets a
      person opened in a browser are handed in with `--deliver`.
- [x] **The op-amp bench specified**: 28 `opa-*` measurements in the bipolar catalogue's format, the universal
      ladders drawn from the survey, the absences a macromodel must declare.
- [x] **The JFET and MOSFET benches specified**: 13 `jfet-*` and 15 `mos-*` measurements
      ([fet-characterisation.md](fet-characterisation.md)), the assembly of each circuit
      ([fet-bench-drawings.md](fet-bench-drawings.md)), 26 drawings in `docker/circuitikz/fet/` and
      `data/bench/drawings/`.
- [x] **Every measurement previewed on ngspice**, one model per part, nine parts (J201, 2N5457, 2N3819; 2N7000,
      BS170, IRF510; TL072, NE5532, RC4558): 512 decks, 1,032 numbers, the models' absences found
      ([bench-preview-2026-10.md](bench-preview-2026-10.md), `make bench-preview`). The decks of
      `docker/sim/preview/bench_preview.py` are the draft of the pipeline's.

## Pending, in the order that unblocks the rest

1. **Pins and absences of a macromodel** (`opamp-card`, in `models/cards.py`): the five pins of an op-amp
   subcircuit mapped by role; the family (Boyle/PARTS, the ADI and TI PSpice generations, behavioural,
   encrypted); whether the text carries noise sources, temperature terms, a supply-current model, input
   protection, a current limit. The preview's `card_facts` is the sketch. A model whose pins cannot be
   traced is not run. Estimate: one session.
2. **Catalogue entries**: `data/bench/measurements.yaml` grows the kinds `jfet`, `mosfet` and `opamp`, one
   entry per measurement with conditions, grid, outputs, curves and the `directives` a test checks against
   the deck; `make bench-methods` copies them into the two documents (their `measurements:start` blocks).
   Two sessions.
3. **Decks in the images**: `docker/sim/bench/decks_jfet.py`, `decks_mos.py`, `decks_opamp.py` in the shape
   of `decks_bjt.py` (body, saves, tail, measure, finalize), `PLANS` in `character.py`, `PLANNED` in
   `bench/character.py`, the extraction shared through `num.py` (Goertzel, margins, slopes, weighted noise).
   What the preview learnt: the forced drain current needs the dial with a clamp diode; the inductive
   switching fixture is a current source with a freewheel diode and a snubber; a stage's drive scales with
   gfs; `.noise` output is a density in V/√Hz; a macromodel's supply ramp needs a non-zero start. Three to
   four sessions.
4. **Runs on the maintainer's machine**: `make bench-character KIND=jfet|mosfet|opamp ENGINE=qspice`, then
   ngspice and LTspice, for the priority-1 parts of `data/models/wanted.yaml` first; `character-publish`,
   `character-release`, catalogue version `m-13`. Hours of simulation per engine for the transients and the
   noise decks; the `*-agreement` measurements exist only then.
5. **Drawings in one style**: the 26 FET drawings moved from their own preamble into `benches.py` and
   `bench.sty`, and the 28 op-amp drawings made; `make bench-drawings-all`. Two sessions.
6. **The survey for transistors**: `data/datasheets/survey/jfet.yaml` and `mosfet.yaml` with the makers'
   sheets and a `TESTS` table per kind, so the figures of a JFET or MOSFET sheet map to `jfet-*` and `mos-*`
   as the op-amps' do. One session.
7. **Sheets beside the numbers**: the figure boxes located (`sei datasheets figures` over the survey's
   `figures.csv`) and cropped (`make datasheets-crops`), for every kind. One session.
8. **The site**: groups and uses per kind in `web/src/behaviours.ts` and `methods.tsx`. The characterisation
   pane itself is shown since October 2026 (`CHARACTERIZATION` in `features.ts`), with the bipolar records.
   One session.
9. **The survey's missing sheets**: Analog Devices, ST, Rohm and Intersil from the Internet Archive when it
   can be reached from the machine that runs it (it could not from the cloud session), and more sheets
   opened by hand where robots.txt says no (Nisshinbo, Microchip). Renesas answered 403.

## What the preview says the pipeline must handle

- Op-amp macromodels of the Boyle family give one VOS at every supply, common mode and temperature; equal
  bias currents on both inputs; PSRR flat with frequency; a swing that ignores the load; distortion of
  parts per million; white noise only; no RF rectification; a supply current set by a resistor between the
  rails (14 mA for TI's TL072 model where the part draws 1.4 mA). Each is a result to publish as
  `absent` or as the number, never a default to hide.
- JFET and MOSFET cards have no 1/f noise, no breakdown, no reverse recovery; level-1 and level-3 MOSFET cards
  give Ciss and Crss as constants. The preview reports them; the catalogue needs the codes.
- Single-amplifier subcircuits have no channel separation; dual and quad subcircuits will.

## Not in scope

Thermal derating, long-term drift, ESD and latch-up (not simulable in these models); Norton amplifiers
(LM3900) are another kind of part; BSIM cards are recorded by family and not run.
