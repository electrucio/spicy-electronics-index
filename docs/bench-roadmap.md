# The bench beyond bipolar transistors: what is done, what is pending

The bipolar bench ([model-characterisation.md](model-characterisation.md)) runs end to end: catalogue
entries, decks in the three pinned simulator images, records per model hash, the site. The JFET, MOSFET
and op-amp benches are specified and previewed, not yet run through that pipeline. This page is the
checklist; every session that touches the bench starts here and ticks what it finished.

## Done (October 2026)

- [x] **The op-amp survey.** `sei datasheets survey --kind opamp` reads what the makers' sheets measure: 73
      sheets of eight makers, 2,149 figure titles mapped to tests and to the `opamp-*` measurements
      ([opamp-characterisation.md](opamp-characterisation.md), `data/datasheets/survey/opamp/`). Sheets a
      person opened in a browser are handed in with `--deliver`.
- [x] **The three benches specified and previewed**: 13 `jfet-*`, 14 `mosfet-*` and 26 `opamp-*`
      measurements, every one run once on ngspice as a preview
      ([bench-preview-2026-10.md](bench-preview-2026-10.md), `make bench-preview`).
- [x] **The catalogue entries** (`data/bench/measurements.yaml`, version `m-13`), rendered into
      [fet-characterisation.md](fet-characterisation.md) and [opamp-characterisation.md](opamp-characterisation.md)
      by `make bench-methods` as the bipolar ones are.
- [x] **The decks in the simulator images**: `docker/sim/bench/decks_jfet.py` (40 decks per model),
      `decks_mos.py` (39) and `decks_opamp.py` (98), in the shape of `decks_bjt.py`, quoted verbatim by the
      catalogue and checked by `tests/bench/test_character_decks_kinds.py`. The image runner maps a
      subcircuit's pins for every kind; a `.model` MOSFET gets its bulk tied to the source.
- [x] **The job builder**: JFET and MOSFET cards and subcircuits (pins traced through gate resistors), op-amp
      subcircuits (pins from the PSpice PARTS header or the pin names), and `sei bench character --here`,
      which runs the image's script on a machine with ngspice on the PATH and no Docker.
- [x] **Nine models characterised and published** on ngspice 42 here: J201, 2N5457, 2N3819 (Central
      Semiconductor), 2N7000 (Zetex), BS170P (Diodes), IRF510 (level 3), TL072, RC4558 (TI PARTS), NE5532
      (TI PARTS, via LTwiki). A cloud session cannot create a GitHub release, so their nine records sit in
      the tracked supplement (`data/verification/models/supplement/`, `make bench-character-supplement`),
      which the site build lays over the released asset's records; the next `make bench-character-release`
      on the maintainer's machine packs them into the `character-m-13` asset, after which the folder is
      emptied.
- [x] **The site shows them**: the characterisation pane is on, the method page lists the four kinds, each
      kind has its default curve and its groups' labels.
- [x] **The drawings** of all 52 JFET, MOSFET and op-amp measurements, in the bipolar drawings' style
      (blue for what the bench sets, red for what it measures, a circled A or V for a current or a voltage
      read, green node names): `docker/circuitikz/benches_fet.py` and `benches_opamp.py`,
      [bench-drawings.md](bench-drawings.md).

- [x] **The tube bench specified** ([tube-characterisation.md](tube-characterisation.md)): the survey of 50 tube
      sheets read page by page (`data/datasheets/survey/tube/`, 237 graphs and 5,074 table rows, each mapped to
      the measurement that reproduces it), 41 `tube-*`, `triode-*`, `pentode-*`, `rectifier-*`, `diode-*`
      (and `heptode-`, `indicator-`) measurements in two layers (universal ladders, and every sheet row and graph as conditions), their 29
      drawings (`docker/circuitikz/benches_tube.py`), and a preview of them on ngspice over every curated model of
      45 surveyed parts (`docker/sim/preview/tube_preview.py`). The triode's first nine entries are in the
      catalogue (kind `tube`, with the single-ended output stage), and the 12AX7's and 300B's curated models are
      measured with them on their part pages, made on this machine by `docker/sim/preview/tube_records.py` and
      kept in the records' supplement.

## Pending, in the order that unblocks the rest

1. **QSPICE and LTspice runs on the maintainer's machine** (`make bench-character KIND=jfet|mosfet|amplifier
   ENGINE=qspice`, then `ngspice` and `ltspice` in the pinned images) for every priority-1 part of
   `data/models/wanted.yaml`; `character-publish`, `character-release`. The `*-agreement` measurements
   exist only then; today's nine records are one engine, on the host's ngspice 42 rather than the image's.
   Hours of simulation per engine for the transients.
2. **`opamp-card`** in `models/cards.py`: the family (Boyle/PARTS, the ADI and TI PSpice generations,
   behavioural, encrypted), whether the text carries noise sources, temperature terms, a supply-current
   model, input protection, a current limit; `sei models cards` over the amplifier group, so that every
   `absent` names its cause. The bench already reads the pins. One session.
3. **Dual and quad subcircuits**: `opamp-separation` measured (onsemi's fixture), the bench running each
   amplifier of a package. One session.
4. **The survey for transistors**: `data/datasheets/survey/jfet.yaml` and `mosfet.yaml` with the makers'
   sheets and a `TESTS` table per kind. One session.
5. **Sheets beside the numbers**: the figure boxes located (`sei datasheets figures` over the survey's
   `figures.csv`) and cropped (`make datasheets-crops`), for every kind. One session.
6. **The survey's missing sheets**: Analog Devices, ST, Rohm and Intersil from the Internet Archive when it
   can be reached from the machine that runs it, and more sheets opened by hand where robots.txt says no
   (Nisshinbo, Microchip). Renesas answered 403.

7. **The tubes through the pipeline**: the rest of the catalogue entries, `decks_tube.py` on the shape of
   `tube_preview.py`'s decks (the dialect search and parameter declaration of `tube-runs`, the secant-solved
   ideal bypasses and transformers), the `tube-card` reader in `models/cards.py`, the SVGs of the drawings
   (`make bench-drawings-all`), QSPICE and LTspice runs, and the sheet layer reading
   `data/datasheets/survey/tube/`. Two to three sessions.
8. **The tube survey's missing sheets and curves**: the 6SJ7's and 12AY7's resistance-coupled charts the
   sheets refer to and do not contain, the 6AU6's and 6BA6's screen rating charts; digitising the static
   curves so that `tube-sheet-figures` can be scored, not only laid over the crops. One session.

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
