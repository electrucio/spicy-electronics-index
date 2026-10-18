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
RX_PCHAN = re.compile(r"\bPCHAN\b", re.I)


def polarity_of(kind_type: str, card: str = "") -> str | None:
    """The sign a card is run with: a VDMOS card is a P-channel when its text says `pchan`."""
    if kind_type == "VDMOS" and RX_PCHAN.search(card):
        return "p"
    return POLARITY.get(kind_type)
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
# the terminal letters of a device line, by its first letter: a MOSFET's bulk is not a terminal the bench drives
DEVICE_ROLES = {"Q": "cbe", "J": "dgs", "M": "dgs"}
GROUP_ROLES = {"bjt": set("cbe"), "jfet": set("dgs"), "mosfet": set("dgs")}
GROUP_TYPES = {"bjt": {"NPN", "PNP"}, "jfet": {"NJF", "PJF"}, "mosfet": {"NMOS", "PMOS", "VDMOS"}}
RX_TERMINALS = re.compile(r"TERMINALS?\s*[:=]?\s*([CBE])\s+([CBE])\s+([CBE])\b", re.I)
RX_NODES_DGS = re.compile(r"NODES?\s*[:=]?\s*([DGS])\s+([DGS])\s+([DGS])\b", re.I)
# an op-amp's five pins, by the words a PSpice PARTS header lists them in ("CONNECTIONS:" then one role per line)
# or by the names a header gives them
OPAMP_ROLES = ("inp", "inn", "vp", "vn", "out")
OPAMP_WORDS = {"NON-INVERTING INPUT": "inp", "NONINVERTING INPUT": "inp", "INVERTING INPUT": "inn", "POSITIVE POWER SUPPLY": "vp",
               "NEGATIVE POWER SUPPLY": "vn", "OUTPUT": "out"}
OPAMP_NAMES = {"inp": {"IN+", "+IN", "INP", "NINV", "VINP", "VIN+", "IN_P", "INPOS", "PLUS", "+"},
               "inn": {"IN-", "-IN", "INN", "INV", "VINN", "VIN-", "IN_N", "INNEG", "MINUS", "-"},
               "vp": {"V+", "VCC", "VDD", "VP", "VS+", "+V", "+VS", "VPOS", "VCC+"},
               "vn": {"V-", "VEE", "VSS", "VN", "VS-", "-V", "-VS", "VNEG", "VEE-"},
               "out": {"OUT", "VOUT", "OUTPUT", "O", "VO"}}
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


WIRE_OHMS = {"bjt": 1.0, "jfet": 1000.0, "mosfet": 1000.0}    # a FET's gate resistor (a few hundred ohms) is in series with nothing


def _wire(t: list[str], group: str = "bjt") -> bool:
    """A two-terminal element the bench reads as a wire: an inductance, a source of 0 V, a resistance of an ohm
    or less (a kilohm for a FET, whose gate resistor carries no current)."""
    if len(t) < 3:
        return False
    if t[0][0] == "L":
        return True
    if t[0][0] == "V":
        vals = [x for x in t[3:] if x not in ("DC",)]
        return not vals or (C.number(vals[0]) == 0)
    if t[0][0] == "R" and len(t) >= 4:
        v = C.number(t[3].split("=")[-1])
        return v is not None and abs(v) <= WIRE_OHMS.get(group, 1.0)
    return False


def subckt_roles(chain: list, name: str | None = None, depth: int = 0, group: str = "bjt") -> tuple[list[str] | None, str]:
    """The role of each pin of a subcircuit (c, b, e for a bipolar, d, g, s for a FET, or nc for one no
    terminal reaches), traced through its netlist and its nested subcircuits; (None, why) when it cannot be
    told for sure."""
    want = GROUP_ROLES[group]
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
        if _wire(t, group):
            nodes.join(t[1], t[2])
        elif t[0][0] in DEVICE_ROLES and len(t) >= 5 and DEVICE_ROLES[t[0][0]][0] in want:
            terminals += list(zip(t[1:4], DEVICE_ROLES[t[0][0]]))
        elif t[0][0] == "X":
            sub = next((x for x in reversed(t[1:]) if "=" not in x and defs.get(x.lower(), ("",))[0] == "subckt"), None)
            if sub is None:
                return None, "a nested subcircuit the file does not hold"
            inner, why = subckt_roles(chain, sub, depth + 1, group)
            if inner is None:
                return None, why
            terminals += [(node, r) for node, r in zip(t[1:1 + len(inner)], inner) if r != "nc"]
    roles = []
    for p in pins:
        got = {r for node, r in terminals if nodes.find(node) == nodes.find(p)}
        if len(got) > 1:
            return None, f"pin {p} reaches the transistor's {' and '.join(sorted(got))} at once"
        roles.append(got.pop() if got else "nc")
    if not want <= set(roles):
        return None, "no pin reaches one of the " + ("collector, base and emitter" if group == "bjt" else "drain, gate and source")
    if depth == 0:
        said = comment_roles(defs[key][1], pins, group)
        clash = [p for p, r in zip(pins, roles) if said.get(p) not in (None, r)]
        if clash:
            return None, "the author's comments and the circuit disagree on the pins"
    return roles, ""


def comment_roles(body: str, pins: list[str], group: str = "bjt") -> dict[str, str]:
    """What the author's comments say each pin is, where they say it: "TERMINALS: C B E", "Nodes D G S",
    "Node 1 -> Collect", or a row of names over a "node:" row of pin numbers."""
    comments = [line.lstrip("*").strip() for line in body.splitlines() if line.lstrip().startswith("*")]
    out: dict[str, str] = {}
    for c in comments:
        m = RX_TERMINALS.search(c) if group == "bjt" else RX_NODES_DGS.search(c)
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
    return order, [t for t in types if t in ("NPN", "PNP", "NJF", "PJF", "NMOS", "PMOS", "VDMOS", "D", "")] if types else []


def header_comments(text: str, name: str) -> str:
    """The comment lines just above a subcircuit's `.SUBCKT` line in its file: where a PSpice PARTS header
    says which pin is which."""
    lines = text.splitlines()
    rx = re.compile(r"^\s*\.subckt\s+" + re.escape(name) + r"\b", re.I)
    for i, line in enumerate(lines):
        if rx.match(line):
            j = i
            while j > 0 and (lines[j - 1].lstrip().startswith("*") or not lines[j - 1].strip()):
                j -= 1
            return "\n".join(lines[j:i])
    return ""


def opamp_pins(body: str, pins: list[str], header: str = "") -> tuple[list[str] | None, str]:
    """An op-amp subcircuit's five pins by role: the PSpice PARTS header ("CONNECTIONS:" and one role per
    comment line, in pin order, above or inside the subcircuit), else the names the header gives the pins;
    (None, why) when neither says."""
    if len(pins) != 5:
        return None, f"{len(pins)} pins: not a plain five-pin op-amp"
    lines = [line.lstrip("*").strip().lstrip("| ").strip() for line in (header + "\n" + body).splitlines() if line.lstrip().startswith("*")]
    roles: list[str] = []
    started = False
    for c in lines:
        up = c.upper()
        if "CONNECTIONS:" in up:
            started = True
            up = up.split("CONNECTIONS:", 1)[1].strip()
        if not started:
            continue
        word = up.strip("| ").strip()
        if not word:
            if roles:
                break
            continue
        if word in OPAMP_WORDS:
            roles.append(OPAMP_WORDS[word])
        elif roles:
            break
    if len(roles) == 5 and sorted(roles) == sorted(OPAMP_ROLES):
        return roles, ""
    by_name = []
    for p in pins:
        role = next((r for r, names in OPAMP_NAMES.items() if p.upper() in names), None)
        by_name.append(role)
    if all(by_name) and sorted(by_name) == sorted(OPAMP_ROLES):
        return by_name, ""
    return None, "the header does not say which pin is which (no PARTS connections block, no pin names)"


def subckt_card(chain: list, engine: str, group: str = "bjt", header: str = "") -> tuple[dict | None, str]:
    """A subcircuit as the bench is given it: its text with the subcircuit renamed DUT and every name inside
    it suffixed _DUT (packed copies must not share an inner `QPWR`), the role of each pin, its polarity
    and the changes made; (None, why) when it cannot be measured. `group` is the bench the subcircuit goes
    to: a transistor's pins are traced to its terminals, an op-amp's read from its header."""
    if not chain or chain[-1][0] != "subckt":
        return None, "not a subcircuit, or a card of the same name hides it"
    pins = _pins(F.code_lines(chain[-1][2])[0])
    if group == "amplifier":
        roles, why = opamp_pins(chain[-1][2], pins, header)
        if roles is None:
            return None, why
        parts, _ = subckt_parts(chain)
        polarity = "n"
    else:
        if len(pins) not in SUBCKT_PINS:
            return None, f"{len(pins)} pins"
        roles, why = subckt_roles(chain, group=group)
        if roles is None:
            return None, why
        parts, types = subckt_parts(chain)
        own = {t for t in types if t in GROUP_TYPES[group]}
        if not own:
            return None, "no transistor card inside"
        pol = {polarity_of(t, "\n".join(b for _, _, b in parts)) for t in own}
        if len(pol) > 1:
            return None, "transistors of both polarities inside"
        polarity = pol.pop()
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


def subckt_for(files: F.Files, file: str, name: str, engine: str, group: str = "bjt") -> tuple[dict | None, str]:
    header = ""
    if group == "amplifier":
        header = header_comments(F.model_text((files.root / file).read_bytes(), file), name)
    return subckt_card(F.closure(files.get(file)[0], name), engine, group, header)
