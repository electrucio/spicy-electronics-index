"""What each recipe model's card can and cannot represent, read from the parameters it carries and the
values they hold.

    sei models cards [--kind bjt]

A Gummel-Poon card without CJC has no collector capacitance: simulated, its Cob is zero, and a data
sheet's "Cob ≤ 4 pF" would be met by a model that does not model it. So each card is read for the
parameters that carry the behaviours a data sheet specifies or the bench measures, and the part's record
says, per model, which of them are absent. Absent means missing **or ineffective**: a zero, which SPICE
reads as "none" or as "infinite"; a VAF of a million volts, which is no Early effect; a base resistance
of a microohm. `why` says which value made a present parameter count as absent, and `default` names the
parameters left at a default that nobody fitted (a reverse gain BR of 1). The page then shows
`n.m. card: CJC` where a value would otherwise stand, and lists what each card lacks.

MOSFET cards are read by family — LTspice's VDMOS, the level 1 to 3 integrated models, BSIM, EKV — and
a level 1 to 3 card is marked `geometry: default`, because the channel width and length that decide
its currents are the instance's, not the card's. A subcircuit's header is read for its pins: which are
collector/base/emitter or drain/gate/source, which is a thermal node (an electro-thermal model), and
what device models it holds inside; nothing else is claimed about it.

It also notes what one simulator reads differently from the others (`DIALECT`), from what the three
were seen to do on the whole bipolar population (docker/sim/README.md).

Only which parameters are absent, present or at a default is published, never a parameter's value
(CLAUDE.md rule 2). Cards built on another (`AKO:`) are recorded by family alone.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter

from spicy_electronics_index.bench import record
from spicy_electronics_index.core.config import require, spice_models_root, spice_recipe_locations
from spicy_electronics_index.models import behaviours
from spicy_electronics_index.models import found as F

VERSION = "cards-4"

# The parameters looked for, by family, in the order the page lists them.
CHECKED = {
    "gummel-poon": ("TF", "XTF", "CJE", "CJC", "TR", "VAF", "IKF", "ISE", "RB", "RE", "RC", "KF", "XTB"),
    "jfet": ("CGS", "CGD", "LAMBDA", "RS", "RD", "KF", "VTOTC", "BETATCE"),
    "diode": ("CJO", "TT", "BV", "RS", "KF"),
    "vdmos": ("CGDMAX", "CGDMIN", "CGS", "CJO", "TT", "BV", "RG", "RDS", "KSUBTHRES", "TEXP0", "TRD1", "TCVTH", "KF"),
    "mos-level-1": ("LAMBDA", "CGSO", "CGDO", "CBD", "IS", "RD", "RS", "KF"),
    "mos-level-2": ("LAMBDA", "CGSO", "CGDO", "CBD", "IS", "RD", "RS", "KF"),
    "mos-level-3": ("LAMBDA", "CGSO", "CGDO", "CBD", "IS", "RD", "RS", "KF"),
}
# When a value that is there still does nothing. Anything not listed is effective unless it is zero.
EFFECTIVE = {
    "VAF": (lambda v: 0 < v < 1e4, ">= 1e4 V: no Early effect"),
    "VAR": (lambda v: 0 < v < 1e4, ">= 1e4 V: no reverse Early effect"),
    "RB": (lambda v: v > 1e-3, "<= 1 mΩ"),
    "RE": (lambda v: v > 1e-3, "<= 1 mΩ"),
    "RC": (lambda v: v > 1e-3, "<= 1 mΩ"),
    "RS": (lambda v: v > 1e-3, "<= 1 mΩ"),
    "RD": (lambda v: v > 1e-3, "<= 1 mΩ"),
    "RG": (lambda v: v > 1e-3, "<= 1 mΩ"),
}
# Parameters whose SPICE default is a value nobody fitted: present and equal to it, or missing, is "default".
DEFAULTS = {"gummel-poon": {"BR": 1.0, "NF": 1.0, "NE": 1.5}, "jfet": {}, "diode": {"N": 1.0}, "vdmos": {},
            "mos-level-1": {}, "mos-level-2": {}, "mos-level-3": {}}
# Extensions some libraries write and some simulators read, beyond the family's own physics.
EXTENSIONS = {
    "gummel-poon": {"breakdown": re.compile(r"^BV"), "quasi-saturation": re.compile(r"^(RCO|VO|GAMMA|QUASIMOD)$")},
    "jfet": {"gate-leakage": re.compile(r"^(ISR|NR|ALPHA|VK)$"), "doping-tail": re.compile(r"^B$")},
    "vdmos": {"thermal": re.compile(r"^(RTHJC|RTHCA|CTHJ)$")},
}
# A data sheet's row (by canonical symbol) that a card of the family cannot represent unless one of these
# parameters is there. An empty tuple: the family has no parameter for it at all — a Gummel-Poon card
# models no breakdown (unless it carries a BV… extension) and a level-1 JFET none.
NEEDS: dict[str, dict[str, tuple[str, ...]]] = {
    "gummel-poon": {
        "cob": ("CJC",), "cib": ("CJE",), "ft": ("TF", "CJE", "CJC"),
        # the output admittance and the voltage feedback ratio are the Early effect seen at 1 kHz
        "hoe": ("VAF",), "hre": ("VAF",),
        "td": ("TF", "TR", "CJE", "CJC"), "tr": ("TF", "TR", "CJE", "CJC"),
        "ts": ("TF", "TR", "CJE", "CJC"), "tf": ("TF", "TR", "CJE", "CJC"),
        "vbrceo": (), "vbrcbo": (), "vbrebo": (),
    },
    "jfet": {
        "ciss": ("CGS", "CGD"), "crss": ("CGD",), "coss": ("CGD",), "gos": ("LAMBDA",),
        "vbrgss": (), "vbrgds": (),
    },
    "diode": {"cd": ("CJO",), "trr": ("TT",), "vbr": ("BV",)},
    "vdmos": {
        "ciss": ("CGS", "CGDMAX"), "coss": ("CJO", "CGDMAX"), "crss": ("CGDMAX",),
        "qg": ("CGS", "CGDMAX"), "qgs": ("CGS",), "qgd": ("CGDMAX",),
        "trr": ("TT",), "vbrdss": ("BV",),
    },
    "mos-level-1": {"ciss": ("CGSO", "CGDO"), "crss": ("CGDO",), "coss": ("CBD", "CGDO"), "trr": (), "vbrdss": ()},
}
NEEDS["mos-level-2"] = NEEDS["mos-level-3"] = NEEDS["mos-level-1"]
MOS_LEVELS = {None: "mos-level-1", 1.0: "mos-level-1", 2.0: "mos-level-2", 3.0: "mos-level-3", 8.0: "bsim3",
              49.0: "bsim3", 14.0: "bsim4", 54.0: "bsim4", 44.0: "ekv", 2026.0: "qspice-2026"}

# What one simulator reads differently from the other two, and what gives it away in a card.
AMPERE_UNIT = re.compile(r"(?<=[\d.])A(?:MPS?)?(?=[\s),]|$)", re.I)       # IKF=10A: ngspice reads atto
CATALOGUE = ("MFG", "VCEO", "ICRATING", "IAVE", "VPK", "IPK", "TYPE", "VDS", "QG")   # LTspice's; ngspice refuses
RATINGS = ("VCEO", "ICRATING", "VDS", "IAVE", "VPK", "IPK", "MFG")                 # those that state a limit, and the maker
JFET_EXTENSIONS = ("ISR", "NR", "ALPHA", "VK")                             # LTspice's; ngspice ignores
LTSPICE_DIODE = ("RON", "ROFF", "VFWD", "VREV", "ILIMIT", "REVILIMIT", "EPSILON", "REVEPSILON")
DIALECT = {
    "unit-a": "a unit after a number (IKF=10A): ngspice reads the A as atto",
    "catalogue-fields": "LTspice's catalogue fields (mfg=, Vceo=, …): ngspice refuses the card",
    "nk-above-1": "NK above 1: ngspice clamps it to 1",
    "nr-above-nf": "NR above NF: the model is not reciprocal, and in saturation its VCE goes negative at low current in every simulator",
    "jfet-extensions": "LTspice's JFET extensions (isr, nr, alpha, vk): ngspice ignores them",
    "ltspice-diode": "LTspice's ideal-diode parameters (Ron, Roff, Vfwd…): only LTspice reads them",
    "level-garbled": "a LEVEL no simulator has (a Micro-Cap binary library converted to text): each simulator falls back to its own",
}

RX_HEAD = re.compile(r"^\.MODEL\s+\S+\s+(AKO:\s*\S+\s+)?([A-Z]+)\s*(.*)$", re.S)
RX_PARAM = re.compile(r"([A-Z_][A-Z0-9_]*)\s*=\s*(\{[^}]*\}|\S+)")
RX_SUBCKT = re.compile(r"^\.SUBCKT\s+(\S+)\s+(.*)$", re.S)
# Pin names a subcircuit header may use for a transistor's three terminals, and for a thermal node.
PIN_NAMES = {
    "c": {"C", "COLLECTOR", "COL", "NC", "COLL"}, "b": {"B", "BASE", "NB"}, "e": {"E", "EMITTER", "EMIT", "NE"},
    "d": {"D", "DRAIN", "DR", "ND", "NDRAIN"}, "g": {"G", "GATE", "NG", "NGATE"}, "s": {"S", "SOURCE", "SRC", "NS", "NSOURCE"},
}
THERMAL_PINS = re.compile(r"^(TJ|TC|TH|TL|TEMP|TCASE|TAMB|TJUNC(TION)?|T_?J|T_?C|THERMAL|TJ_?OUT|TCASE_?IN)$")
DEVICE_TYPES = ("NPN", "PNP", "NJF", "PJF", "NMOS", "PMOS", "VDMOS", "D")


def card_params(body: str) -> tuple[str, bool, dict[str, str]] | None:
    """(device type, built on another card, parameters as written) of a `.model` statement."""
    lines = F.code_lines(body)
    if len(lines) != 1:
        return None
    m = RX_HEAD.match(lines[0])
    if not m:
        return None
    text = m.group(3).replace("(", " ").replace(")", " ").replace(",", " ")
    return m.group(2), bool(m.group(1)), dict(RX_PARAM.findall(text))


def number(v: str) -> float | None:
    """A parameter's value as a number, or None when it is an expression or a name."""
    x = F.value(AMPERE_UNIT.sub("", v))
    try:
        return float(x)
    except ValueError:
        return None


def family(kind_type: str, params: dict[str, str]) -> str:
    """The model family a card selects: its device type, and LEVEL where the type has several."""
    level = params.get("LEVEL")
    lv = number(level) if level is not None else None
    first = level is None or lv == 1.0
    if kind_type in ("NPN", "PNP"):
        return "gummel-poon" if first else f"bjt-level-{level.lower()}"
    if kind_type in ("NJF", "PJF"):
        return "jfet" if first else f"jfet-level-{level.lower()}"
    if kind_type == "D":
        return "ltspice-ideal-diode" if any(p in params for p in ("RON", "ROFF", "VFWD")) else "diode"
    if kind_type == "VDMOS":
        return "vdmos"
    if kind_type in ("NMOS", "PMOS"):
        if level is not None and (lv is None or lv != int(lv) or lv > 2026):
            return "mos-level-unknown"
        return MOS_LEVELS.get(lv, f"mos-level-{level.lower()}" if level else "mos-level-1")
    return kind_type.lower()


def read(kind: str, body: str) -> dict:
    """What one card lacks and how the simulators differ on it; a subcircuit's pins."""
    if kind != "model":
        return read_subckt(body) if kind == "subckt" else {"family": kind}
    parsed = card_params(body)
    if parsed is None:
        return {"family": "unknown"}
    kind_type, ako, params = parsed
    fam = family(kind_type, params)
    out: dict = {"family": fam, "type": kind_type}
    if ako:
        out["family"] = "ako"
        return out
    if fam in CHECKED:
        absent, unknown, present, why = [], [], [], {}
        for p in CHECKED[fam]:
            if p not in params:
                absent.append(p)
                continue
            v = number(params[p])
            if v is None:
                unknown.append(p)
            elif v == 0:
                absent.append(p)
            elif p in EFFECTIVE and not EFFECTIVE[p][0](v):
                absent.append(p)
                why[p] = EFFECTIVE[p][1]
            else:
                present.append(p)
        out["absent"] = absent
        out["present"] = present
        if unknown:
            out["unknown"] = unknown
        if why:
            out["why"] = why
        default = [p for p, dv in DEFAULTS.get(fam, {}).items() if p not in params or number(params[p]) == dv]
        if default:
            out["default"] = default
        ext = [name for name, rx in EXTENSIONS.get(fam, {}).items() if any(rx.match(p) for p in params)]
        if ext:
            out["extensions"] = ext
        if "breakdown" in ext:
            out["breakdown"] = True               # an extension some libraries write and some simulators read
        if fam.startswith("mos-level-"):
            out["geometry"] = "default"           # W and L are the instance's; a bare card has the simulator's
    dialect = []
    if any(AMPERE_UNIT.search(v) for v in params.values()):
        dialect.append("unit-a")
    if any(p in params for p in CATALOGUE):
        dialect.append("catalogue-fields")
    if (number(params.get("NK", "")) or 0) > 1:
        dialect.append("nk-above-1")
    if kind_type in ("NPN", "PNP", "LPNP") and (number(params.get("NR", "")) or 1.0) > (number(params.get("NF", "")) or 1.0) + 0.02:
        dialect.append("nr-above-nf")
    if kind_type in ("NJF", "PJF") and any(p in params for p in JFET_EXTENSIONS):
        dialect.append("jfet-extensions")
    if kind_type == "D" and any(p in params for p in LTSPICE_DIODE):
        dialect.append("ltspice-diode")
    if fam == "mos-level-unknown":
        dialect.append("level-garbled")
    if dialect:
        out["dialect"] = dialect
    # what the card declares of the part's ratings (LTspice's catalogue fields): no simulator uses them, but
    # they are the card author's statement of the limits, and the charts draw them
    ratings = {}
    for p in RATINGS:
        if p in params:
            v = params[p].strip('"')
            ratings[p.lower()] = v if p == "MFG" else number(v)
    ratings = {k: v for k, v in ratings.items() if v not in (None, "")}
    if ratings:
        out["ratings"] = ratings
    return out


def read_subckt(body: str, inner: list[str] | None = None) -> dict:
    """A subcircuit: its pins as the header names them, which of them are a transistor's terminals or a
    thermal node, and the device types of the model cards it holds inside (given by the caller)."""
    lines = F.code_lines(body)
    m = RX_SUBCKT.match(lines[0]) if lines else None
    out: dict = {"family": "subckt"}
    if not m:
        return out
    pins = []
    for tok in m.group(2).split():
        if tok.startswith("PARAMS") or "=" in tok:
            break
        pins.append(tok)
    has_device = any(line[0] in "QMJX" for line in lines[1:])
    mapped: dict[str, int] = {}
    for i, p in enumerate(pins):
        for role, names in PIN_NAMES.items():
            if p in names and role not in mapped:
                mapped[role] = i
    thermal = [i for i, p in enumerate(pins) if THERMAL_PINS.match(p)] if has_device else []
    sets = ({"c", "b", "e"}, {"d", "g", "s"})
    full = next((s for s in sets if s <= set(mapped)), None)
    out["pins"] = {"order": pins, "mapped": {k: mapped[k] for k in sorted(full)} if full else {}, "thermal": thermal}
    if thermal:
        out["thermal_pin"] = True
    if inner:
        out["inner"] = sorted(set(inner))
    return out


def read_chain(chain: list) -> dict:
    """A definition with everything it references (`found.closure`): the card itself, or the subcircuit
    with the device types of the cards inside it."""
    kind_def, _, body = chain[-1]
    if kind_def != "subckt":
        return read(kind_def, body)
    inner = []
    for k, _, b in chain[:-1]:
        if k == "model":
            parsed = card_params(b)
            if parsed and parsed[0] in DEVICE_TYPES:
                inner.append(parsed[0])
    return read_subckt(body, inner)


def cannot(card: dict, symbol: str) -> tuple[str, ...] | None:
    """The parameters whose absence keeps this card from representing a sheet's row: None when the card
    can (or when nothing is known), an empty tuple when its family has no parameter for it at all."""
    needs = NEEDS.get(card.get("family", ""), {}).get(symbol)
    if needs is None or "absent" not in card:
        return None
    if not needs:
        return None if card.get("breakdown") else ()
    if set(needs) <= set(card["absent"]):
        return needs
    return None


def run(only_kind: str | None = None, only_part: str | None = None, force: bool = False) -> Counter:
    locations = json.loads(require(spice_recipe_locations(), "reading the recipes' cards").read_text(encoding="utf-8"))
    files = F.Files(spice_models_root())
    led = record.ledger()
    c: Counter = Counter()
    for key, models in sorted(locations.items()):
        kind, part = key.split("/", 1)
        if behaviours.group(kind) not in ("bjt", "jfet", "diode", "mosfet") or (only_kind and kind != only_kind) \
                or (only_part and part != only_part):
            continue
        todo = {m["hash"]: m for m in models if m["hash"] and m["file"].startswith("sources/")}
        dig = record.digest(sorted(todo))
        if not force and led.fresh(key, "cards", VERSION, dig):
            c["fresh"] += 1
            continue
        out = {}
        for h, m in sorted(todo.items()):
            try:
                chain = F.closure(files.get(m["file"])[0], m["name"])
            except OSError:
                c["unreadable"] += 1
                continue
            if not chain:
                c["not found in its file"] += 1
                continue
            out[h] = read_chain(chain)
            c[f"family {out[h]['family']}"] += 1
            for p in out[h].get("absent", []):
                c[f"no {p}"] += 1
            for d in out[h].get("dialect", []):
                c[d] += 1
            if out[h].get("thermal_pin"):
                c["thermal pin"] += 1
            if out[h].get("pins", {}).get("mapped"):
                c["pins mapped"] += 1
        c["written" if record.write_section(kind, part, "cards", out) else "unchanged"] += 1
        led.stamp(key, "cards", version=VERSION, cards_in=dig)
    led.save()
    return c


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--kind", help="only one kind (bjt, jfet, mosfet, diode, …)")
    ap.add_argument("--part", help="only one part")
    ap.add_argument("--force", action="store_true", help="read every card again, fresh or not")
    a = ap.parse_args(argv)
    c = run(a.kind, a.part, a.force)
    print(f"{c['written']:,} parts written, {c['unchanged']:,} unchanged, {c['fresh']:,} already done")
    fams = sorted(((k[7:], n) for k, n in c.items() if k.startswith("family ")), key=lambda x: -x[1])
    print("cards by family: " + ", ".join(f"{k} {n:,}" for k, n in fams))
    gaps = sorted(((k[3:], n) for k, n in c.items() if k.startswith("no ")), key=lambda x: -x[1])
    print("absent: " + ", ".join(f"{k} {n:,}" for k, n in gaps))
    print("dialect: " + ", ".join(f"{d} {c[d]:,}" for d in DIALECT if c[d]))
    print(f"subcircuits with their pins mapped: {c['pins mapped']:,}; with a thermal pin: {c['thermal pin']:,}")
    for k in ("unreadable", "not found in its file"):
        if c[k]:
            print(f"{k}: {c[k]:,}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
