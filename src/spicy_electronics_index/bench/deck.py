"""Regenerate the exact deck behind a published number from a reader's own copy of the card, and read a
waveform the way the bench reads it.

    sei bench deck <measurement-id> --card model.lib --name 2N3904 [--engine ngspice] [--polarity npn]
                    [--hash <published hash>] [--out .]
    sei bench read <deck>.raw --measurement <id> --deck <deck name> [--engine ngspice] [--polarity npn]
                    [--hash <published hash>]

`deck` writes `model.lib` (the card prepared as the bench prepares it: renamed DUT, LTspice's catalogue
fields out, the A unit out for ngspice) and one `.cir` per deck that serves the measurement, and prints
each deck's sha256; with `--hash` it compares them with the published digests and takes the model's
derived values (the base currents of the ladder) from the published record, because the decks after the
first depend on them. `read` applies the same extraction to the waveform the reader produced with
`docker run --rm -v "$PWD":/w spicy-electronics-index-<engine> simrun /w/<deck>.cir`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from spicy_electronics_index.bench import catalogue
from spicy_electronics_index.bench.jobs import POLARITY, prepare, subckt_card
from spicy_electronics_index.core.config import character, sim_bench
from spicy_electronics_index.models import cards as C
from spicy_electronics_index.models import found as F

SIGN = {"npn": 1, "pnp": -1, "n": 1, "p": -1}


def image_bench(engine: str):
    """The image's own bench modules, imported from the checkout: the decks are written once, there."""
    os.environ["SIM_ENGINE"] = engine
    root = str(sim_bench().parent)
    if root not in sys.path:
        sys.path.insert(0, root)
    from bench import character as incar  # noqa: PLC0415
    from bench import raw  # noqa: PLC0415
    return incar, raw


def card_from_file(path: Path, name: str, engine: str) -> tuple[str, list[str], str, list[str] | None]:
    """(prepared card, changes, device type, pin roles) of the named card in a reader's file: a `.model` card
    (an AKO one written out in full), or a subcircuit with the role of each of its pins."""
    text = path.read_text(encoding="utf-8", errors="replace")
    chain = F.closure(F.blocks(text), name)
    got = prepare(chain, engine)
    if got:
        parsed = C.card_params(got[0])
        return got[0], got[1], parsed[0] if parsed else "", None
    sub, why = subckt_card(chain, engine)
    if not sub:
        from spicy_electronics_index.bench.jobs import header_comments  # noqa: PLC0415
        sub, why2 = subckt_card(chain, engine, "amplifier", header_comments(text, name))
        why = why if not sub else ""
    if not sub:
        raise SystemExit(f"{name} in {path} cannot be measured: {why or 'not a .model card or a subcircuit'}")
    return sub["card"], sub["changes"], sub["polarity"].upper(), sub["pins"]


def published(model_hash: str | None) -> dict:
    if not model_hash:
        return {}
    p = character(model_hash)
    if not p.exists():
        raise SystemExit(f"no published record for {model_hash}")
    return json.loads(p.read_text(encoding="utf-8"))


# derived points any model gives: what the decks after the first need to be written (the lines a catalogue
# entry quotes never carry one of these numbers)
EXAMPLE_DERIVED = {"ib@30µA": 1.4e-7, "ib@300µA": 1.3e-6, "ib@3mA": 1.3e-5, "vbe@10µA": 0.5, "vbe@30µA": 0.53, "vbe@300µA": 0.65, "vbe@3mA": 0.71, "ib@1µA": 1e-8, "ib@10µA": 5e-8, "ib@100µA": 4.4e-07, "ib@1mA": 4.4e-06, "ib@10mA": 4.6e-05,
                   "ib@100mA": 1e-3, "ib@1A": 0.1, "ib@10A": 1.0, "vbe@100µA": 0.62, "vbe@1mA": 0.68, "vbe@10mA": 0.74,
                   "ic_at_hfe_peak": 0.02, "ic_max_converged": 1.0, "thd_gain": 17.0}


def pnp_directives(m: dict, engine: str = "qspice") -> list[str]:
    """A catalogue entry's quoted deck lines as the PNP deck writes them: each deck that serves the measurement
    is written for an NPN and for a PNP copy, line for line the same structure, and every quoted line is
    replaced by the PNP line in its place. Comments are kept; a line no deck writes is kept as it is."""
    incar, _ = image_bench(engine)
    swap: dict[str, str] = {}
    for deck in decks_for(m["id"], engine, incar):
        a = incar.deck_text(deck, [("DUT", 1, "", EXAMPLE_DERIVED)], "model.lib", engine).splitlines()
        b = incar.deck_text(deck, [("DUT", -1, "", EXAMPLE_DERIVED)], "model.lib", engine).splitlines()
        if len(a) != len(b):
            continue
        for x, y in zip(a, b):
            swap.setdefault(x, y)
    return [line if line.startswith("*") else swap.get(line, line) for line in m.get("directives") or []]


def decks_for(measurement: str, engine: str, incar) -> list:
    cat = {m["id"]: m for m in catalogue.measurements()}
    kind = measurement.split("-", 1)[0]
    if kind not in incar.PLANS:
        raise SystemExit(f"no decks for {kind} yet")
    return [d for d in incar.PLANS[kind].plan(cat, engine) if measurement in d.ids]


def write_decks(measurement: str, card: str, engine: str, polarity: str, derived: dict, out: Path, rec: dict,
                pins: list[str] | None = None) -> list[dict]:
    incar, _ = image_bench(engine)
    out.mkdir(parents=True, exist_ok=True)
    (out / "model.lib").write_text(card + "\n", encoding="utf-8")
    rows = []
    for deck in decks_for(measurement, engine, incar):
        if not deck.ready(derived):
            rows.append({"deck": deck.name, "status": "needs the model's derived values (run the dc deck first, or give --hash)"})
            continue
        text = incar.deck_text(deck, [("DUT", SIGN[polarity], "", derived, pins)], "model.lib", engine)
        path = out / f"{deck.name}.cir"
        path.write_text(text, encoding="utf-8")
        dig = hashlib.sha256(text.encode("utf-8")).hexdigest()
        pub = ((rec.get("decks") or {}).get(deck.name) or {}).get(engine, {}).get("digest")
        rows.append({"deck": deck.name, "file": str(path), "sha256": dig,
                     "status": "matches the published deck" if pub and dig.startswith(pub) else ("differs from the published deck" if pub else "")})
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("measurement")
    ap.add_argument("--card", required=True, type=Path)
    ap.add_argument("--name", required=True)
    ap.add_argument("--engine", default="ngspice", choices=("qspice", "ngspice", "ltspice"))
    ap.add_argument("--polarity", choices=sorted(SIGN))
    ap.add_argument("--hash")
    ap.add_argument("--out", type=Path, default=Path("."))
    a = ap.parse_args(argv)
    card, changes, dev, pins = card_from_file(a.card, a.name, a.engine)
    polarity = a.polarity or POLARITY.get(dev)
    if not polarity:
        raise SystemExit(f"give --polarity: the card's type {dev!r} does not say")
    rec = published(a.hash)
    rows = write_decks(a.measurement, card, a.engine, polarity, rec.get("derived") or {}, a.out, rec, pins)
    print(f"model.lib written ({', '.join(changes)})" + (f"; a subcircuit, its pins {' '.join(pins)}" if pins else ""))
    for r in rows:
        print(f"{r['deck']}: {r.get('sha256', '')} {r['status']}".rstrip())
    return 0


def read_main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="apply the bench's extraction to a waveform")
    ap.add_argument("raw", type=Path)
    ap.add_argument("--measurement", required=True)
    ap.add_argument("--deck", required=True)
    ap.add_argument("--engine", default="ngspice", choices=("qspice", "ngspice", "ltspice"))
    ap.add_argument("--polarity", default="npn", choices=sorted(SIGN))
    ap.add_argument("--hash")
    a = ap.parse_args(argv)
    incar, raw = image_bench(a.engine)
    rec = published(a.hash)
    derived = dict(rec.get("derived") or {})
    deck = next((d for d in decks_for(a.measurement, a.engine, incar) if d.name == a.deck), None)
    if deck is None:
        raise SystemExit(f"no deck {a.deck} serves {a.measurement}")
    plot = incar.pick_plot(raw.read(a.raw), deck.analysis)
    derived["_plot_name"] = plot["name"]
    values, curves, codes, _ = deck.measure(plot["data"], SIGN[a.polarity], "", derived)
    print(json.dumps({"values": values, "codes": codes, "curves": {m: sorted(c) for m, c in curves.items()}}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
