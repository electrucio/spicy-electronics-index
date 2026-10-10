# docker/sim — ngspice, LTspice and QSPICE, pinned, from the command line

Three SPICE simulators in Docker images whose every input is pinned, and the decks that characterise every
transistor model at the conditions of `data/bench/measurements.yaml`
([docs/model-characterisation.md](../../docs/model-characterisation.md)). `bench/` is standard-library
Python so it runs unchanged inside every image; the host side is `src/spicy_electronics_index/bench/`.

**Roles.** QSPICE is the default engine. ngspice is the open cross-check: anyone can rebuild its image and
repeat a number. LTspice is the compatibility check: it is what hobbyists simulate with, and it refuses
some broken cards QSPICE accepts. Choosing another model of a part changes results far more than choosing
another simulator, so a model is judged per behaviour, never by the engine that ran it.

## Pinned inputs

- Base image by digest and every Debian package by snapshot date (`ARG DEBIAN`, `SNAPSHOT` in the
  Dockerfile); ngspice by the sha256 of its source tarball.
- LTspice and QSPICE by the sha256 files in `sha256/`. Their installers may not be redistributed: they
  live in the private vendor store (`private_material/simulators/vendor/`), the images are never pushed to
  a registry, and every machine builds its own. A vendor re-publishing a file at the same URL is reported
  by `make sim-vendor`, never used; moving to a new release is a deliberate change of the sha256 file.
- Rebuilt from nothing, the images give bit-identical numbers.

## Build and run

```sh
make sim-vendor            # fetch the installers into the private store, check their sha256
make sim-qspice-capture    # once per QSPICE build: installs it under Wine and packs it (accepts Qorvo's licence)
make sim-images            # spicy-electronics-index-ngspice, -ltspice, -qspice (rebuild them whenever they are missing)

make bench-character ENGINE=qspice [PART=] [WORKERS=] [FORCE=1]   # measure; jobs come from the recipes
make bench-character-publish    # one record per model hash, and the ledger
make bench-character-release    # the records as this catalogue version's release asset; commit release.json
make bench-deck ID=bjt-ft CARD=model.lib NAME=2N3904              # the netlist behind a published number
```

Containers run with the host's uid/gid, so the files they write are yours. One simulator per core is the
parallelism that pays; none of the three can use a GPU.

## What each simulator needed

- **ngspice** — `ngspice -b -r out.raw deck.cir` with `SPICE_ASCIIRAWFILE=1`. It rejects LTspice's catalogue
  fields in cards (`mfg=…`) and reads a unit after a number as a prefix (`IKF=10A` is ten attoamperes), so
  the batch runner cleans both for ngspice alone. It clamps `NK` to 1.
- **LTspice** — `wine64 LTspice.exe -b -ascii deck.cir`. The MSI's installer hangs under Wine, so it is
  unpacked with `msiextract`. Its first launches ask questions even in batch mode: `ltspice/LTspice.ini`
  and `ltspice/firstrun.sh` answer them at build time. It needs an X display even with `-b` (an Xvfb per
  container). It starts one spinning solver thread per host CPU, so confining it with `taskset` hangs it;
  share the machine by worker count instead.
- **QSPICE** — `wine QSPICE64.exe deck.cir -ascii -r deck.qraw`. Its executables are 32-bit, so the Wine
  base carries 32- and 64-bit Wine. The installer is a downloader with a licence window:
  `qspice_capture.sh` drives it once with xdotool, screenshots the licence it accepts, and packs the
  program folder reproducibly. The licence forbids giving the software to third parties: run the capture
  only if you accept it yourself.

## Where the three differ, and what follows

The same card read the same way gives the same numbers in all three; differences come from dialect, and
`models/cards.py` (`DIALECT`) flags the cards they affect. Beyond the ngspice traps above:

- ngspice ignores LTspice's JFET extensions (`isr`, `nr`, `alpha`, `vk`), so its gate currents come out
  low; LTspice's ideal-diode parameters (`Ron`, `Roff`, `Vfwd`) only LTspice reads.
- ngspice and LTspice put gmin (10⁻¹² S) across junctions: **picoampere leakages are not trustworthy as
  simulated.**
- QSPICE gives noise in V²/Hz where the others give V/√Hz.
- LTspice is the strictest: it refuses some broken cards and some badly posed circuits that the other two
  accept silently.
- A model only one simulator opens (QSPICE's native cards, LTspice- or PSpice-encrypted subcircuits) has
  no cross-check.

**The model matters more than the simulator.** Cards for the same part differ far more than engines do,
and many miss their sheet's limits; models tend to be more optimistic than the typical device. So each
model is rated per behaviour — DC, frequency, noise, temperature, distortion — against the sheet's rows at
the sheet's conditions, never with one score. An op-amp macromodel is not a transistor model: it
reproduces the behaviours its header lists (often "distortion is not characterized") and is best run in
the environment its maker wrote it for (Analog Devices' models in LTspice).
