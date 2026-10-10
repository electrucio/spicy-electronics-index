"""How a recipe model becomes the card a bench job carries: renamed DUT, cleaned of what one simulator
refuses, with each change named so it can be published beside the result.

Used by `sei bench character` and by `sei bench deck`: one copy of the rules, so a card is prepared the
same way for the bench and for a reader regenerating a deck.
"""
from __future__ import annotations

import re

from spicy_electronics_index.models import cards as C
from spicy_electronics_index.models import found as F

POLARITY = {"NPN": "npn", "PNP": "pnp", "NJF": "n", "PJF": "p", "NMOS": "n", "PMOS": "p", "VDMOS": "n"}
CATALOGUE = re.compile(r"\b(?:" + "|".join(C.CATALOGUE) + r")\s*=\s*[^\s)]+", re.I)
# Each change made to a card before it is simulated, published with the result so it can be repeated.
CHANGES = {
    "renamed": "the .model renamed DUT, the name the bench's netlists use",
    "catalogue-fields": "LTspice's catalogue fields (mfg=, Vceo=, …) removed: ngspice refuses them, the others ignore them",
    "unit-a": "for ngspice, the A after a number removed (IKF=10A): ngspice reads it as atto",
    "ako-resolved": "a PSpice AKO card (\"a kind of\" another) written out in full: its base card's parameters, its own on top",
    "ends-added": "the .ENDS a subcircuit's file left out, or wrote as .ENDL, put in: not every simulator reads a subcircuit without its end",
}
RX_SUBCKT_HEAD = re.compile(r"^(\s*\.subckt\s+)(\S+)", re.I | re.M)
RX_ENDL = re.compile(r"^\s*\.endl\b[^\n]*", re.I | re.M)
RX_AKO = re.compile(r"^\.MODEL\s+\S+\s+AKO:\s*(\S+)", re.I)


def card_for(files: F.Files, file: str, name: str, engine: str) -> tuple[str, list[str]] | None:
    """The card as the bench is given it, and the changes made to it; None when the definition is not a
    plain `.model` card (a subcircuit, or a name the file no longer holds) or an AKO card whose base the
    file does not hold."""
    return prepare(F.closure(files.get(file)[0], name), engine)


def resolve_ako(chain: list) -> str | None:
    """An AKO card ("a kind of" another, PSpice's `.model X AKO:Y NPN (BF=…)`) written out in full, as one
    plain `.model DUT`: the base card's parameters, and the card's own on top of them, following a chain
    of AKO cards to the first plain one. None when a base is not in the closure, or the chain loops. The
    simulators do not all read AKO, and a card written out is the same card for all three."""
    defs = {name.lower(): (kind, body) for kind, name, body in chain}
    kind_type = None
    layers: list[dict[str, str]] = []
    body, seen = chain[-1][2], set()
    while True:
        parsed = C.card_params(body)
        if parsed is None:
            return None
        typ, ako, params = parsed
        kind_type = kind_type or typ                     # the card's own type: the base must agree with it
        if typ != kind_type:
            return None
        layers.append(params)
        if not ako:
            break
        m = RX_AKO.match(F.code_lines(body)[0])
        base = m.group(1).lower() if m else ""
        if not base or base in seen or defs.get(base, ("",))[0] != "model":
            return None
        seen.add(base)
        body = defs[base][1]
    merged: dict[str, str] = {}
    for params in reversed(layers):                       # the base first, each card's own on top
        merged.update(params)
    return f".model DUT {kind_type} (" + " ".join(f"{k}={v}" for k, v in merged.items()) + ")"


def prepare(chain: list, engine: str) -> tuple[str, list[str]] | None:
    """The same, from a definition's closure (`found.closure`): also how a reader's own file is read."""
    if not chain or chain[-1][0] != "model":
        return None
    if RX_AKO.match(F.code_lines(chain[-1][2])[0] if F.code_lines(chain[-1][2]) else ""):
        card = resolve_ako(chain)
        if card is None:
            return None
        changes = ["renamed", "ako-resolved"]
    else:
        card = re.sub(r"^(\s*\.model\s+)(\S+)", lambda m: m[1] + "DUT", chain[-1][2], count=1, flags=re.I)
        changes = ["renamed"]
    stripped = CATALOGUE.sub("", card)
    if stripped != card:
        card, changes = stripped, changes + ["catalogue-fields"]
    if engine == "ngspice":
        fixed = C.AMPERE_UNIT.sub("", card)
        if fixed != card:
            card, changes = fixed, changes + ["unit-a"]
    return card, changes


# ---------------------------------------------------------------------------------------------- subcircuits
# A subcircuit is measured through its pins, so the bench must know which pin is the collector, the base
# and the emitter. The order is not a convention: most files write "1 2 3" for C B E, onsemi's ThermalTrak
# parts B E C, an NXP-style SOT-223 B C E. So the roles are traced through the subcircuit's own netlist —
# which pin reaches which terminal of the transistors inside, through lead inductances, ammeters and
# resistances of an ohm or less — and, where the author's comments name the pins too, the two must agree.
# A pin no terminal reaches (a ThermalTrak diode's anode) is left open; a second pin on the collector (a
# SOT-223 tab) is tied to it. Whatever cannot be told for sure is not measured, with the reason.
SUBCKT_PINS = (3, 4, 5)
RX_TERMINALS = re.compile(r"TERMINALS?\s*[:=]?\s*([CBE])\s+([CBE])\s+([CBE])\b", re.I)
RX_NODE_ROLE = re.compile(r"NODE\s+(\S+)\s*-+>\s*(COLLECT|BASE|EMIT)", re.I)
ROLE_WORD = {"COLLECT": "c", "BASE": "b", "EMIT": "e", "COLLECTOR": "c", "EMITTER": "e"}


class _Nodes:
    """Nodes joined by what is a wire to the bench: a union-find over node names."""

    def __init__(self):
        self.up: dict[str, str] = {}

    def find(self, a: str) -> str:
        self.up.setdefault(a, a)
        while self.up[a] != a:
            self.up[a] = self.up[self.up[a]]
            a = self.up[a]
        return a

    def join(self, a: str, b: str) -> None:
        self.up[self.find(a)] = self.find(b)


def _pins(head: str) -> list[str]:
    toks = head.split()[2:]
    out = []
    for t in toks:
        if t.upper().startswith("PARAMS") or "=" in t:
            break
        out.append(t)
    return out


def _wire(t: list[str]) -> bool:
    """A two-terminal element the bench reads as a wire: an inductance, a source of 0 V, an ohm or less."""
    if len(t) < 3:
        return False
    if t[0][0] == "L":
        return True
    if t[0][0] == "V":
        vals = [x for x in t[3:] if x not in ("DC",)]
        return not vals or (C.number(vals[0]) == 0)
    if t[0][0] == "R" and len(t) >= 4:
        v = C.number(t[3].split("=")[-1])
        return v is not None and abs(v) <= 1.0
    return False


def subckt_roles(chain: list, name: str | None = None, depth: int = 0) -> tuple[list[str] | None, str]:
    """The role of each pin of a subcircuit (c, b, e, or nc for one no transistor terminal reaches), traced
    through its netlist and its nested subcircuits; (None, why) when it cannot be told for sure."""
    defs = {n.lower(): (k, b) for k, n, b in chain}
    key = (name or chain[-1][1]).lower()
    if key not in defs or defs[key][0] != "subckt" or depth > 4:
        return None, "a nested subcircuit the file does not hold"
    lines = F.code_lines(defs[key][1])
    pins = _pins(lines[0]) if lines else []
    nodes, terminals = _Nodes(), []
    for line in lines[1:]:
        t = line.split()
        if not t or t[0].startswith("."):
            continue
        if _wire(t):
            nodes.join(t[1], t[2])
        elif t[0][0] == "Q" and len(t) >= 5:
            terminals += list(zip(t[1:4], "cbe"))
        elif t[0][0] == "X":
            sub = next((x for x in reversed(t[1:]) if "=" not in x and defs.get(x.lower(), ("",))[0] == "subckt"), None)
            if sub is None:
                return None, "a nested subcircuit the file does not hold"
            inner, why = subckt_roles(chain, sub, depth + 1)
            if inner is None:
                return None, why
            terminals += [(node, r) for node, r in zip(t[1:1 + len(inner)], inner) if r != "nc"]
    roles = []
    for p in pins:
        got = {r for node, r in terminals if nodes.find(node) == nodes.find(p)}
        if len(got) > 1:
            return None, f"pin {p} reaches the transistor's {' and '.join(sorted(got))} at once"
        roles.append(got.pop() if got else "nc")
    if not {"c", "b", "e"} <= set(roles):
        return None, "no pin reaches one of the collector, base and emitter"
    if depth == 0:
        said = comment_roles(defs[key][1], pins)
        clash = [p for p, r in zip(pins, roles) if said.get(p) not in (None, r)]
        if clash:
            return None, "the author's comments and the circuit disagree on the pins"
    return roles, ""


def comment_roles(body: str, pins: list[str]) -> dict[str, str]:
    """What the author's comments say each pin is, where they say it: "TERMINALS: C B E", "Node 1 -> Collect",
    or a row of names over a "node:" row of pin numbers."""
    comments = [line.lstrip("*").strip() for line in body.splitlines() if line.lstrip().startswith("*")]
    out: dict[str, str] = {}
    for c in comments:
        m = RX_TERMINALS.search(c)
        if m and len(pins) >= 3:
            out.update({pins[i]: m.group(i + 1).lower() for i in range(3)})
        for n, w in RX_NODE_ROLE.findall(c):
            out[n.upper()] = ROLE_WORD[w.upper()]
    for a, b in zip(comments, comments[1:]):
        words = [w.upper() for w in a.split()]
        if b.lower().startswith("node") and sum(w in ROLE_WORD for w in words) >= 2:
            nums = b.split(":", 1)[-1].split()
            for w, n in zip(words, nums):
                if w in ROLE_WORD:
                    out[n.upper()] = ROLE_WORD[w]
    return {p: r for p, r in out.items() if p in pins}


def _local_models(body: str) -> dict[str, str]:
    """The cards a subcircuit defines inside its own block, by upper-case name (a model local to it)."""
    out = {}
    for line in F.code_lines(body)[1:]:
        if line.startswith(".MODEL"):
            t = line.split()
            if len(t) > 1:
                out[t[1]] = line
    return out


def _uses(body: str, defs: dict, local: dict) -> list[tuple[str, str]]:
    """What a subcircuit's elements use, in order: ("model", name) for a transistor's or a diode's card,
    ("subckt", name) for a nested instance; only names its own block or the file defines."""
    out = []
    for line in F.code_lines(body)[1:]:
        t = line.split()
        if not t or t[0].startswith("."):
            continue
        k = t[0][0]
        if k in "QJM" and len(t) >= 5:
            cand = [x for x in t[4:6] if x in local or defs.get(x.lower(), ("",))[0] == "model"]
            out += [("model", cand[0])] if cand else []
        elif k == "D" and len(t) >= 4 and (t[3] in local or defs.get(t[3].lower(), ("",))[0] == "model"):
            out.append(("model", t[3]))
        elif k == "X":
            sub = next((x for x in reversed(t[1:]) if "=" not in x and defs.get(x.lower(), ("",))[0] == "subckt"), None)
            if sub:
                out.append(("subckt", sub))
    return out


def subckt_parts(chain: list) -> tuple[list[tuple[str, str, str]], list[str]]:
    """The definitions a subcircuit really uses, deps first and itself last (a file's other cards whose name
    an element happens to share are left out), and the types of the transistor cards inside it."""
    defs = {n.lower(): (k, n, b) for k, n, b in chain}
    order, seen, types = [], set(), []

    def visit(name: str):
        k, n, body = defs[name.lower()]
        local = _local_models(body) if k == "subckt" else {}
        for kind, used in (_uses(body, defs, local) if k == "subckt" else []):
            if kind == "model" and used in local:
                parsed = C.card_params(local[used])
                types.append(parsed[0] if parsed else "")
                continue
            key = used.lower()
            if kind == "model":
                parsed = C.card_params(defs[key][2])
                types.append(parsed[0] if parsed else "")
            if key not in seen:
                seen.add(key)
                visit(used)
        order.append(defs[name.lower()])

    visit(chain[-1][1])
    return order, [t for t in types if t in ("NPN", "PNP", "D", "")] if types else []


def subckt_card(chain: list, engine: str) -> tuple[dict | None, str]:
    """A subcircuit as the bench is given it: its text with the subcircuit renamed DUT and every name inside
    it suffixed _DUT (packed copies must not share an inner `QPWR`), the role of each pin, its polarity
    and the changes made; (None, why) when it cannot be measured."""
    if not chain or chain[-1][0] != "subckt":
        return None, "not a subcircuit, or a card of the same name hides it"
    pins = _pins(F.code_lines(chain[-1][2])[0])
    if len(pins) not in SUBCKT_PINS:
        return None, f"{len(pins)} pins"
    roles, why = subckt_roles(chain)
    if roles is None:
        return None, why
    parts, types = subckt_parts(chain)
    bjt = {t for t in types if t in ("NPN", "PNP")}
    if not bjt:
        return None, "no transistor card inside"
    if len(bjt) > 1:
        return None, "transistors of both polarities inside"
    polarity = POLARITY[bjt.pop()]
    # every name the subcircuit uses becomes <name>_DUT, then its own header becomes DUT: a card inside it
    # may carry the subcircuit's own name (ltwiki's BC847BM holds `.MODEL BC847BM`), and must keep its own
    names = {n.lower(): f"{n}_DUT" for _, n, _ in parts}
    for _, _, body in parts:
        names.update({m.lower(): f"{m}_DUT" for m in _local_models(body) if m.lower() not in names})
    rx = re.compile(r"(?<![\w$#.\-+])(" + "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True)) + r")(?![\w$#.\-+])", re.I)
    main = chain[-1][1].lower()
    changes = ["renamed"]
    texts = []
    for _, n, body in parts:
        text = rx.sub(lambda m: names[m.group(1).lower()], body)
        if RX_SUBCKT_HEAD.match(text):
            if n.lower() == main:
                text = RX_SUBCKT_HEAD.sub(lambda m: m.group(1) + "DUT", text, count=1)
            if not any(line.startswith(".ENDS") for line in F.code_lines(text)):
                # onsemi's 2SC6144SG closes its subcircuit with `.ENDL <name>`, a library's terminator: QSPICE
                # reads it as the end, ngspice and LTspice refuse it
                ended = RX_ENDL.sub(".ENDS", text, count=1)
                text = ended if ended != text else text.rstrip() + "\n.ENDS"
                changes = changes + ["ends-added"] if "ends-added" not in changes else changes
        texts.append(text)
    card = "\n".join(texts)
    stripped = CATALOGUE.sub("", card)
    if stripped != card:
        card, changes = stripped, changes + ["catalogue-fields"]
    if engine == "ngspice":
        fixed = C.AMPERE_UNIT.sub("", card)
        if fixed != card:
            card, changes = fixed, changes + ["unit-a"]
    return {"card": card, "changes": changes, "pins": roles, "polarity": polarity}, ""


def subckt_for(files: F.Files, file: str, name: str, engine: str) -> tuple[dict | None, str]:
    return subckt_card(F.closure(files.get(file)[0], name), engine)
