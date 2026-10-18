"""Writes docker/circuitikz/drawings/<id>.tex for every bench, in the house style; run it from the repository
root after editing, then `make bench-drawings NAME=<id>` for each (or `make bench-drawings-all`). This file
holds the building blocks and the bipolar benches; benches_fet.py and benches_opamp.py draw the JFET, MOSFET
and op-amp ones with the same blocks and are run from here.

The style (bench.sty): one sans typeface, LaTeX mathematics for the quantities and their definitions; a title
top-left and the colour key under it; the circuit in the middle with every quantity named beside its symbol;
the definitions under the grounds, mathematical where the deck is (I_B = 10^k A, k = -9 ... 0); the deck's node
names in small green monospace. Blue is what the bench sets, red what it measures. Each drawing is the set-up a
person would wire, semantically the deck's: the dial V(x) is not drawn, a behavioural source is a current source,
and the copies of one circuit a deck packs are one circuit with the list of its conditions.

Coordinates are centimetres. The transistor sits at (4,3), its emitter ground at y = 1; the collector lead goes
up 1.7 to the rail, the supply hangs 2.6 to the right of it, the base source sits 1.4 to the left of the base
and the base voltmeter 3.2.
"""
import re
from pathlib import Path

OUT = Path("docker/circuitikz/drawings")
LOG = r"$I_B = 10^{k}\,\mathrm{A}$, $k = -9,\,-8.95,\,\dots,\,0$ \quad (20 points per decade, 1 nA to 1 A)"


class D:
    def __init__(self, name, title, header, top=7.0, gnd=1.0, twin=True):
        """twin: also write the PNP twin (the bipolar benches; a FET or an amplifier has none)"""
        self.name, self.title, self.header, self.top, self.gnd, self.twin = name, title, header, top, gnd, twin
        self.lines = []

    def add(self, *lines):
        self.lines.extend(lines)

    def nodename(self, anchor, at, name):
        self.add(rf"\nodename{{anchor={anchor}}}{{{at}}}{{{name}}}")

    # ---------------------------------------------------------------- the building blocks
    def transistor(self, x=4, y=3, flip=None, label="DUT", label_at=r"$(Q.C)+(0.15,-0.55)$", anchor="west"):
        opt = "npn" + (f", {flip}" if flip else "")
        self.add("% the transistor", rf"\node[{opt}] (Q) at ({x},{y}) {{}};",
                 rf"\node[anchor={anchor}, font=\small, align=left] at ({label_at}) {{{label}}};")

    def emitter_ground(self, terminal="Q.E"):
        self.ground(terminal, "emitter")

    def ground(self, terminal="Q.S", what="source"):
        """a terminal straight down to ground"""
        self.add(f"% {what} to ground", rf"\draw ({terminal}) -- ({terminal} |- 0,\gnd) node[ground]{{}};")
        self.nodename("west", rf"$({terminal})+(0.1,-0.3)$", "0")

    # ---------------------------------------------------------------- the field-effect and amplifier blocks
    def fet(self, kind, x=4, y=3, label="DUT", name="Q", flip=None, label_at=None):
        """an N-channel JFET or MOSFET, drain up, gate left; a P-channel card runs with every source reversed"""
        opt = ("njfet" if kind == "jfet" else "nmos") + (f", {flip}" if flip else "")
        label_at = label_at or rf"$({name}.D)+(0.15,-0.55)$"
        self.add("% the transistor", rf"\node[{opt}] ({name}) at ({x},{y}) {{}};",
                 rf"\node[anchor=west, font=\small, align=left] at ({label_at}) {{{label}}};")

    def gate(self, label="$V_{GS}$", node="g", dx=-1.4, kind="V", ammeter=None, terminal="Q.G", name="g"):
        """the gate: a source from ground up into the gate wire, through an ammeter when the gate current is read"""
        self.add(f"% the gate: a {'current' if kind == 'I' else 'voltage'} source from ground"
                 + (", through an ammeter" if ammeter else ""),
                 rf"\coordinate ({name}) at ({terminal});")
        src = f"{name}src"
        if ammeter:
            self.add(rf"\coordinate ({name}am) at ($({name})+(-1.7,0)$);", rf"\ammeterh{{{name}am}}{{{name}}}{{{ammeter}}}",
                     rf"\coordinate ({src}) at ($({name}am)+({dx},0)$);", rf"\draw ({name}am) -- ({src});")
        else:
            self.add(rf"\coordinate ({src}) at ($({name})+({dx},0)$);", rf"\draw ({name}) -- ({src});")
        if label is not None and kind == "I":
            self.add(rf"\draw[set] ({src} |- 0,\gnd) node[ground, black]{{}} to[I, l_={{{label}}}] ({src});")
        elif label is not None:
            self.add(rf"\draw[set] ({src}) to[V, l_={{{label}}}] ({src} |- 0,\gnd) node[ground, black]{{}};")
        else:
            self.add(rf"\draw ({src}) -- ({src} |- 0,\gnd) node[ground]{{}};")
        if node and ammeter:
            self.nodename("south", rf"$({name}am)+(-0.4,0.02)$", node)
        elif node:
            self.nodename("south", rf"$({name})+(-0.45,0.02)$", node)

    def thermometer(self, at=r"$(vtop)+(1.7,-2.6)$", label="$T$"):
        self.add("% the thermometer: the temperature is a simulator setting", rf"\thermometer{{{at}}}{{{label}}}")

    def ammeter(self, terminal="Q.C", label="$I_C$", node="ch", up=1.7, top="ctop"):
        """an ammeter from a terminal straight up to a new coordinate (the rail's end)"""
        self.add("% the ammeter in the collector, up to the rail", rf"\coordinate ({top}) at ($({terminal})+(0,{up})$);",
                 rf"\ammeter{{{terminal}}}{{{top}}}{{{label}}}")
        if node:
            self.nodename("west", rf"$({terminal})+(0.1,0.25)$", node)

    def supply(self, label="$V_{CE}$", dx=2.6, frm="ctop", node=None):
        """the rail from (frm) to the right, then a voltage source down to ground, + up"""
        self.add("% the supply at the right, + up, - to ground", rf"\coordinate (vtop) at ($({frm})+({dx},0)$);",
                 rf"\draw ({frm}) -- (vtop);", rf"\draw[set] (vtop) to[V, l={label}] (vtop |- 0,\gnd) node[ground, black]{{}};")
        if node:
            self.nodename("south", rf"$({frm})+({dx / 2},0.05)$", node)

    def base_source(self, label="$I_B$", node="bh", dx=-1.4):
        """a current source from ground up into the base node"""
        self.add("% the base: a current source from ground", r"\coordinate (b) at (Q.B);",
                 rf"\coordinate (bsrc) at ($(b)+({dx},0)$);", r"\draw (b) -- (bsrc);",
                 rf"\draw[set] (bsrc |- 0,\gnd) node[ground, black]{{}} to[I, l_={label}] (bsrc);")
        self.nodename("south", r"$(b)+(-0.5,0.02)$", node)

    def base_voltmeter(self, dx=-3.2):
        """a voltmeter from the base wire to ground at the far left"""
        self.add("% the voltmeter from the base wire to ground", rf"\coordinate (bvm) at ($(b)+({dx},0)$);",
                 r"\draw (b) -- (bvm);", r"\voltmeter{bvm |- 0,\gnd}{bvm}{$V_{BE}$}", r"\draw (bvm |- 0,\gnd) node[ground]{};")

    def definitions(self, lines, y=-0.1, x=0):
        body = "\\\\[2pt]\n  ".join(lines)
        self.add("% the definitions", f"\\definitions{{{x},{y}}}{{%\n  {body}%ENDDEFS\n}}")

    def write(self):
        head = [f"% {self.title} ({self.name}): the set-up a person would wire, semantically the deck's."]
        head += ["%   " + l for l in self.header.strip("\n").split("\n")]
        text = "\n".join(head + [r"\documentclass[tikz, border=10pt]{standalone}", r"\usepackage{bench}",
                                 r"\begin{document}", r"\begin{tikzpicture}",
                                 rf"\benchtitle{{0,{self.top}}}{{{self.title}}}", rf"\def\gnd{{{self.gnd}}}"]
                         + self.lines + [r"\end{tikzpicture}", r"\end{document}"]) + "\n"
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / f"{self.name}.tex").write_text(text, encoding="utf-8")
        if self.twin:
            (OUT / f"{self.name}-pnp.tex").write_text(pnp(text), encoding="utf-8")


def pnp(text):
    """The same bench for a PNP: the transistor symbol mirrored to keep its collector where the NPN's is, every
    source and the clamp diode reversed, and a note that the values are written as magnitudes."""
    text = text.replace(r"\node[npn, yscale=-1]", r"\node[PNPFLAT]").replace(r"\node[npn]", r"\node[pnp, yscale=-1]")
    text = text.replace(r"\node[PNPFLAT]", r"\node[pnp]")
    text = re.sub(r"to\[(V|I|D), ", r"to[\1, invert, ", text)
    text = re.sub(r"(\\benchtitle\{[^}]*\}\{)([^}]*)\}", r"\1\2, PNP}", text, count=1)
    note = r"\\[2pt]" + "\n  PNP: every source reversed; values written as magnitudes"
    return text.replace("%ENDDEFS", note + "%ENDDEFS", 1)


# ------------------------------------------------------------------------ the drawings
def hfe_ic():
    d = D("bjt-hfe-ic", "DC current gain", """
BH1 0 bh1 I=10^V(x)   the base drive, a log sweep              -> current source I_B (set)
VH1 ch1 0 5           the collector supply; its current is IC  -> source V_CE (set) + ammeter I_C (measured)
QH1 ch1 bh1 0 DUT     the transistor, emitter grounded         -> npn
V(bh1) read: VBE                                                -> voltmeter V_BE (measured)
Six copies run in the deck, one per VCE; the drawing shows one.""")
    d.transistor(); d.emitter_ground(); d.ammeter(); d.supply(); d.base_source(); d.base_voltmeter()
    d.definitions([LOG, r"$V_{CE} = 1$, 2, 4, 5, 6 and 10 V, one copy of the circuit each",
                   r"read $I_C$ and $V_{BE}$ at each $I_B$;\quad $h_{FE} = I_C / I_B$"])
    d.write()


def runs():
    d = D("bjt-runs", "Operating point", """
BH1 0 bh1 I=…   the base drive, read where it is 10 µA     -> current source I_B (set)
VH1 ch1 0 5     the collector supply; its current is IC    -> source V_CE (set) + ammeter I_C (measured)
QH1 ch1 bh1 0   the transistor, emitter grounded           -> npn
V(bh1) read: VBE                                           -> voltmeter V_BE (measured)
One point of the hFE sweep: does the card load and solve?""")
    d.transistor(); d.emitter_ground(); d.ammeter(); d.supply(); d.base_source(); d.base_voltmeter()
    d.definitions([r"$I_B = 10$ \textmu A,\quad $V_{CE} = 5$ V",
                   r"read $I_C$ and $V_{BE}$: does the card load, and does the solver settle?"])
    d.write()


def tracer():
    d = D("bjt-tracer", "Curve tracer", """
IK 0 bk <k x step>   a current source from ground into the base       -> current source I_B (set)
VK sw ck 0           a 0 V source from the swept node to the collector -> ammeter I_C (measured)
QK ck bk 0 DUT       the transistor, emitter grounded                  -> npn
VSW sw 0, .dc 0..10  the swept supply, + at sw, - to ground            -> source V_CE (set)
IU.. 0 bu.. <k x step>  the same for each universal step, 1 µA to 100 mA
The 85 copies of the deck are drawn as one transistor with k = 1 to 5.""")
    d.transistor(); d.emitter_ground(); d.ammeter(node="ck"); d.supply(node="sw"); d.base_source(node="bk")
    d.definitions([r"$I_B = k \cdot I_{step}$, $k = 1, \dots, 5$;\quad $I_{step} = 1$, 2, 5, 10, 20 \textmu A $\dots$ 100 mA, one family each",
                   r"or auto: $I_{step} = I_B(I_C = 10\ \mathrm{mA},\, V_{CE} = 5\ \mathrm{V}) \,/\, 5$, the model's own",
                   r"$V_{CE}$ swept 0 to 10 V in 20 mV steps;\quad read $I_C(V_{CE})$ for each $k$"])
    d.write()


def early():
    d = D("bjt-early", "Output characteristics, h-parameters", """
IE0 0 be0 <ib>        a fixed base current per copy                                 -> current source I_B (set)
VE0 sw ce0 0          a 0 V source from the swept node to the collector: reads IC   -> ammeter I_C (measured)
VSW sw 0 0, .dc       the collector supply, swept                                   -> source V_CE (set)
QE0 ce0 be0 0         the transistor, emitter grounded                              -> npn
The four copies of that deck are drawn as one transistor. The h-parameter deck (1 kHz) is the second row:
IBA 0 ba DC <ib> AC 1  copy A: the base bias for 1 mA with 1 A of AC on top        -> current source I_B + i_b (set)
VCA ca 0 5             copy A's collector supply; its AC current is i_c            -> source V_CE (set) + ammeter I_C + i_c (measured)
V(ba) read: v_be       hie = v_be / i_b, hfe = i_c / i_b                           -> voltmeter v_be (measured)
IBB 0 bb DC <ib>       copy B: the base bias for 1 mA, DC only                     -> current source I_B (set)
VCB cb 0 DC 5 AC 1     copy B's collector supply with 1 V of AC: the output driven -> source V_CE + v_ce (set) + ammeter I_C + i_c (measured)
V(bb) read: v_be       hre = v_be / v_ce, hoe = i_c / v_ce                         -> voltmeter v_be (measured)""")
    d.transistor(); d.emitter_ground(); d.ammeter(node="ce"); d.supply(node="sw"); d.base_source(node="be")
    d.add("% the second row: the two copies of the h-parameter deck, read at 1 kHz",
          r"\node[anchor=west, font=\small] at (0,-0.7) {$h$-parameters at 1 kHz: copy A, the input driven; copy B, the output driven};",
          r"\def\gndb{-5.4}")
    for tag, x, src, sup in (("A", 4.4, "$I_B + i_b$", "$V_{CE}$"), ("B", 12.4, "$I_B$", "$V_{CE} + v_{ce}$")):
        t = tag.lower()
        d.add(f"% copy {tag}",
              rf"\node[npn] (Q{tag}) at ({x},-3.4) {{}};",
              rf"\node[anchor=west, font=\small] at ($(Q{tag}.C)+(0.15,-0.55)$) {{{tag}}};",
              rf"\draw (Q{tag}.E) -- (Q{tag}.E |- 0,\gndb) node[ground]{{}};",
              rf"\coordinate ({t}ctop) at ($(Q{tag}.C)+(0,1.7)$);", rf"\ammeter{{Q{tag}.C}}{{{t}ctop}}{{$I_C + i_c$}}",
              rf"\coordinate ({t}vtop) at ($({t}ctop)+(2.4,0)$);", rf"\draw ({t}ctop) -- ({t}vtop);",
              rf"\draw[set] ({t}vtop) to[V, l={{{sup}}}] ({t}vtop |- 0,\gndb) node[ground, black]{{}};",
              rf"\coordinate ({t}b) at (Q{tag}.B);", rf"\coordinate ({t}bsrc) at ($({t}b)+(-1.3,0)$);",
              rf"\coordinate ({t}bvm) at ($({t}b)+(-2.4,0)$);", rf"\draw ({t}b) -- ({t}bvm);",
              rf"\draw[set] ({t}bsrc |- 0,\gndb) node[ground, black]{{}} to[I, l_={{{src}}}] ({t}bsrc);",
              rf"\voltmeter{{{t}bvm |- 0,\gndb}}{{{t}bvm}}{{$v_{{be}}$}}", rf"\draw ({t}bvm |- 0,\gndb) node[ground]{{}};")
        d.nodename("west", rf"$(Q{tag}.C)+(0.1,0.25)$", f"c{t}"); d.nodename("south", rf"$({t}b)+(-0.45,0.02)$", f"b{t}")
        d.nodename("west", rf"$(Q{tag}.E)+(0.1,-0.3)$", "0")
    d.definitions([r"$I_B$ fixed per copy: the $I_B$ that gave $I_C = 100$ \textmu A, 1 mA, 10 mA and 100 mA at $V_{CE} = 5$ V",
                   r"$V_{CE}$ swept 0 to 30 V in 50 mV steps;\quad read $I_C(V_{CE})$;\quad $V_A = I_C \,/\, (dI_C/dV_{CE}) - V_{CE}$, the slope taken between 5 and 10 V",
                   r"$h$-parameters at $f = 1$ kHz, $I_C = 1$ mA, $V_{CE} = 5$ V.\quad A: $i_b = 1$ A of AC;\quad $h_{ie} = v_{be} \,/\, i_b$, $h_{fe} = i_c \,/\, i_b$",
                   r"B: $v_{ce} = 1$ V of AC;\quad $h_{re} = v_{be} \,/\, v_{ce}$, $h_{oe} = i_c \,/\, v_{ce}$;\quad the AC drives are the simulator's unit signals, not real amplitudes"],
                  y=-6.3)
    d.write()


def gummel():
    d = D("bjt-gummel", "Gummel plot", """
BG 0 bg I=10^V(x)   the drive, a log sweep into the base node               -> current source I_source (set)
VG cg bg 0          a 0 V source from collector to base: VCB = 0, reads IC  -> ammeter I_C (measured)
QG cg bg 0 DUT      the transistor, emitter grounded                        -> npn
V(bg) read: VBE                                                             -> voltmeter V_BE (measured)
The dial V(x) is the deck's way of sweeping; the drawing names the current it sets.""")
    d.transistor(); d.emitter_ground(); d.ammeter(node="cg")
    d.base_source(label="$I_{source}$", node="bg"); d.base_voltmeter()
    d.add("% the loop from the ammeter back to the base node: VCB = 0",
          r"\coordinate (bj) at ($(b)+(-0.9,0)$);", r"\draw (ctop) -| (bj);")
    d.definitions([r"$I_{source} = 10^{k}\,\mathrm{A}$, $k = -9,\,-8.95,\,\dots,\,0$ \quad (20 points per decade, 1 nA to 1 A)",
                   r"$V_{CB} = 0$: the ammeter drops nothing, so $V_{CE} = V_{BE}$",
                   r"read $I_C$ and $V_{BE}$;\quad $I_B = I_{source} - I_C$;\quad $h_{FE} = I_C / I_B$"])
    d.write()


def ac_gain(name, title, last, header):
    d = D(name, title, header)
    d.transistor(); d.emitter_ground(); d.ammeter(label="$I_C + i_c$", node="ct"); d.supply()
    d.base_source(label="$I_B + i_b$", node="bt")
    d.definitions([r"$I_B$: the DC bias for $I_C = 100$ \textmu A, 1 mA, 10 mA, 100 mA, 1 A, 10 A (one copy each)",
                   r"$V_{CE} = 5$ and 10 V;\quad $i_b = 1$ A of AC, the simulator's unit signal, not a real amplitude", *last])
    d.write()


AC_HEADER = """
IBT0 0 bt0 DC <ib> AC 1   the base bias for the ladder current with AC on top -> current source I_B + i_b (set)
VCT0 ct0 0 5              the collector supply, 5 V; its current is IC + ic  -> source V_CE (set) + ammeter I_C + i_c (measured: the AC part)
QT0 ct0 bt0 0 DUT         the transistor, emitter grounded                   -> npn
One copy per ladder current and collector voltage (5 and 10 V) in the deck; the drawing shows one."""


def temperature():
    d = D("bjt-temperature", "Temperature", """
BT 0 bt I=…   the base drive, a log sweep               -> current source I_B (set)
VT ct 0 5     the collector supply; its current is IC   -> source V_CE (set) + ammeter I_C (measured)
QT ct bt 0    the transistor, emitter grounded          -> npn
.temp -55 / 100 / 125 / 150 (and 25 from the hFE deck) -> the thermometer (set)
The forced-ratio saturation copy (IC = 10 IB) rides in each deck; it is drawn in the saturation bench.""")
    d.transistor(); d.emitter_ground(); d.ammeter(node="ct"); d.supply(); d.base_source(node="bt"); d.base_voltmeter()
    d.thermometer()
    d.definitions([LOG, r"$V_{CE} = 5$ V;\quad $T = -55$, 25, 100, 125 and 150 \textdegree C, one deck each",
                   r"read $h_{FE}$, $V_{BE}$, and with the saturation copy ($I_C = 10\,I_B$) $V_{CE}(sat)$, $V_{BE}(sat)$, against $I_C$ at each $T$",
                   r"$dV_{BE}/dT$ against $I_C$ over each span between neighbouring temperatures"])
    d.write()


def breakdown():
    d = D("bjt-breakdown", "Breakdown and leakage", """
RBA ba 0 1e6     the base tied to the emitter through 1 MΩ                     -> resistor R_BA
VA sw ca 0       a 0 V source from the swept node to the collector: reads I   -> ammeter I (measured)
VSW sw 0 0, .dc  the collector supply, swept                                   -> source V_CE (set)
QA ca ba 0       the transistor, emitter grounded                              -> npn
The collector-emitter deck is drawn; collector-base and emitter-base are two more.""")
    d.transistor(); d.emitter_ground(); d.ammeter(label="$I$", node="ca"); d.supply(node="sw")
    d.add("% the base tied to the emitter through a resistor", r"\coordinate (b) at (Q.B);",
          r"\coordinate (bsrc) at ($(b)+(-1.4,0)$);", r"\draw (b) -- (bsrc);",
          r"\draw (bsrc) to[R, l_=$R_{BA}$] (bsrc |- 0,\gnd) node[ground]{};")
    d.nodename("south", r"$(b)+(-0.5,0.02)$", "ba")
    d.definitions([r"$V_{CE}$ swept 0 to 300 V in 1 V steps;\quad $R_{BA} = 1$ M\ohm",
                   r"read $I$;\quad $V_{(BR)CEO}$ = the $V_{CE}$ at which $I$ passes 1 mA, else absent;\quad $I_{CEO} = I$ at 10 V",
                   r"collector-base (emitter open) and emitter-base (collector open): two more decks"])
    d.write()


def reverse():
    d = D("bjt-reverse", "Reverse gain", """
VR er 0 1      the emitter held at 1 V; its current is the reverse collector current -> source V_E (set) + ammeter I_E (measured)
BR 0 br I=…    the base drive, a log sweep                                          -> current source I_B (set)
QR 0 br er     the transistor, collector grounded, emitter at 1 V                   -> npn drawn upside down""")
    d.transistor(flip="yscale=-1", label=r"DUT\\upside down", label_at=r"$(Q.E)+(0.15,-0.55)$")
    d.add("% collector to ground", r"\draw (Q.C) -- (Q.C |- 0,\gnd) node[ground]{};")
    d.nodename("west", r"$(Q.C)+(0.1,-0.3)$", "0")
    d.ammeter(terminal="Q.E", label="$I_E$", node="er"); d.supply(label="$V_E$", dx=3.0); d.base_source(node="br")
    d.definitions([LOG, r"$V_E = 1$ V, collector grounded: the transistor runs backwards",
                   r"read $I_E$, the collector current of the reversed transistor;\quad $h_{FE,reverse} = I_E / I_B$ at 1 mA"])
    d.write()


def saturation():
    d = D("bjt-saturation", "Saturation", """
BSB 0 bs I=…      the base drive, a log sweep                    -> current source I_B into the base (set)
BSC 0 cs I=10*…   ten times that, driven into the collector      -> current source I_C into the collector (set)
DCL cs cl, VCL    a clamp diode from the collector node to 30 V  -> diode + source 30 V
QS cs bs 0        the transistor, emitter grounded               -> npn
V(cs), V(bs) read: VCE(sat), VBE(sat)                            -> two voltmeters (measured)""")
    d.transistor(); d.emitter_ground(); d.base_source(node="bs"); d.base_voltmeter()
    d.add("% the collector drive: ten times the base current, pushed into the collector from a grounded rail",
          r"\coordinate (ctop) at ($(Q.C)+(0,2.0)$);",
          r"\draw[set] (ctop) to[I, l={$I_C = n\,I_B$}] (Q.C);",
          r"\coordinate (rail) at ($(ctop)+(5.2,0)$);", r"\draw (ctop) -- (rail) -- (rail |- 0,\gnd) node[ground]{};")
    d.nodename("east", r"$(Q.C)+(-0.45,0.8)$", "cs")
    d.add("% the clamp: a diode from the collector node to 30 V, and the voltmeter on that node",
          r"\coordinate (cj) at ($(Q.C)+(0,0.3)$);", r"\coordinate (vm) at ($(cj)+(1.4,0)$);",
          r"\coordinate (dj) at ($(cj)+(2.2,0)$);", r"\coordinate (cl) at ($(dj)+(1.6,0)$);",
          r"\draw (cj) -- (dj) to[D, l=clamp] (cl);",
          r"\draw[set] (cl) to[V, l=$30$ V] (cl |- 0,\gnd) node[ground, black]{};",
          r"\voltmeter{vm |- 0,\gnd}{vm}{$V_{CE}$}", r"\draw (vm |- 0,\gnd) node[ground]{};")
    d.nodename("south west", r"$(cl)+(0.05,0.05)$", "cl")
    d.definitions([LOG, r"$I_C = n\,I_B$ forced, $n = 10$, 20 and 50, one copy each;\quad the clamp takes what the transistor cannot pass",
                   r"a step where the clamp conducts, or $V_{CE} \geq V_{BE}$, is not saturated;\quad read $V_{CE}(sat)$, $V_{BE}(sat)$ at each $I_C$",
                   r"$r_{CE,sat} = dV_{CE}(sat) / dI_C$ between 100 mA and 1 A, at $n = 10$"])
    d.write()


def vce_ib():
    d = D("bjt-vce-ib", "Saturation region", """
IV0 0 cv0 0.001     the collector drive, fixed per copy                -> current source I_C (set)
DCV0 cv0 cl0, VCV0  a clamp diode from the collector node to 30 V      -> diode + source 30 V
BV0 0 bv0 I=…       the base drive, a log sweep                        -> current source I_B (set)
QV0 cv0 bv0 0       the transistor, emitter grounded                   -> npn
V(cv0) read: VCE                                                       -> voltmeter V_CE (measured)
One copy per collector current, 1 mA to 10 A; the drawing shows one.""")
    d.transistor(); d.emitter_ground(); d.base_source(node="bv")
    d.add("% the collector drive: a fixed current pushed into the collector from a grounded rail",
          r"\coordinate (ctop) at ($(Q.C)+(0,2.0)$);",
          r"\draw[set] (ctop) to[I, l={$I_C$}] (Q.C);",
          r"\coordinate (rail) at ($(ctop)+(5.2,0)$);", r"\draw (ctop) -- (rail) -- (rail |- 0,\gnd) node[ground]{};")
    d.nodename("east", r"$(Q.C)+(-0.45,0.8)$", "cv")
    d.add("% the clamp to 30 V, and the voltmeter on the collector",
          r"\coordinate (cj) at ($(Q.C)+(0,0.3)$);", r"\coordinate (vm) at ($(cj)+(1.4,0)$);",
          r"\coordinate (dj) at ($(cj)+(2.2,0)$);", r"\coordinate (cl) at ($(dj)+(1.6,0)$);",
          r"\draw (cj) -- (dj) to[D, l=clamp] (cl);",
          r"\draw[set] (cl) to[V, l=$30$ V] (cl |- 0,\gnd) node[ground, black]{};",
          r"\voltmeter{vm |- 0,\gnd}{vm}{$V_{CE}$}", r"\draw (vm |- 0,\gnd) node[ground]{};")
    d.nodename("south west", r"$(cl)+(0.05,0.05)$", "cl")
    d.definitions([r"$I_C = 1$, 10, 100 mA, 1, 2, 5 and 10 A, one copy each", LOG,
                   r"read $V_{CE}$ against $I_B$ where the clamp is off;\quad $I_{B,edge}$: the $I_B$ at which $V_{CE}$ falls to 1 V"])
    d.write()


def switching():
    d = D("bjt-switching", "Switching times", """
VIN in 0 PWL(…)   the drive pulse                            -> source V_in (set)
RB in b           the base resistor, 100 V / IC              -> resistor R_B
VCC vcc 0 10      the supply, 10 or 30 V                     -> source V_CC (set)
RL vcc cs         the load, VCC / IC                         -> resistor R_L
VS cs c 0         a 0 V source in the collector: reads IC    -> ammeter I_C (measured)
Q1 c b 0          the transistor, emitter grounded           -> npn
One deck per switched current (1-2-5, 10 mA to 10 A) and supply.""", top=8.2)
    d.transistor(); d.emitter_ground(); d.ammeter(label="$I_C(t)$", node="c", up=1.6)
    d.nodename("west", r"$(ctop)+(0.1,0.2)$", "cs")
    d.add("% the load up to the rail", r"\draw (ctop) to[R, l_=$R_L$] ++(0,1.6) coordinate (rtop);")
    d.supply(label="$V_{CC}$", frm="rtop")
    d.nodename("south", r"$(rtop)+(1.3,0.05)$", "vcc")
    d.add("% the base resistor and the pulse source", r"\coordinate (b) at (Q.B);",
          r"\draw (b) -- ++(-0.3,0) coordinate (bj) to[R, l_=$R_B$] ++(-1.8,0) coordinate (vin);",
          r"\draw[set] (vin) to[V, l_=$V_{in}$] (vin |- 0,\gnd) node[ground, black]{};")
    d.nodename("south", r"$(b)+(-0.15,0.05)$", "b"); d.nodename("south east", r"$(vin)+(-0.05,0.05)$", "in")
    d.definitions([r"$V_{in}$: $-9.3$ V, then $+10.7$ V from 100 ns to 3.1 \textmu s, then $-9.3$ V;\quad 2 ns edges",
                   r"$R_B = 100\ \mathrm{V} / I_C$, so $I_B = +I_C/10$ on and $-I_C/10$ off past a 0.7 V $V_{BE}$",
                   r"$R_L = V_{CC} / I_C$;\quad $V_{CC} = 10$ and 30 V;\quad $I_C = 10$, 20, 50, 100 mA $\dots$ 10 A (1-2-5), one deck each",
                   r"read $I_C(t)$: $t_d$, $t_r$, $t_s$, $t_f$ between the 10\,\% and 90\,\% levels"])
    d.write()


def noise():
    d = D("bjt-noise", "Noise", """
VIN in 0 DC <vbe> AC 1   the noise input, with the VBE for the step as its DC value -> source v_in (set)
RG in b                  the source resistance                                     -> resistor R_G
IB 0 b DC <ib>           the base bias for the step                                -> current source I_B (set)
VC cc 0 5, VSENSE c cc   the collector supply and the 0 V sensing source           -> source V_C (set) + ammeter I_C + i_c (measured: the noise part)
Q1 c b 0                 the transistor, emitter grounded                          -> npn
H1, RLOAD, .noise        the sensed current is the noise output, referred to v_in  -> the ammeter's reading""")
    d.transistor(); d.emitter_ground(); d.ammeter(label="$I_C + i_c$", node="c"); d.supply(label="$V_C$")
    d.nodename("south west", r"$(ctop)+(0.15,0.05)$", "cc")
    d.base_source(node="b")
    d.add("% the source resistance and the noise input at the far left",
          r"\draw (bsrc) to[R, l_=$R_G$] ++(-1.8,0) coordinate (vin);",
          r"\draw[set] (vin) to[V, l_=$v_{in}$] (vin |- 0,\gnd) node[ground, black]{};")
    d.nodename("south east", r"$(vin)+(-0.05,0.05)$", "in")
    d.definitions([r"$I_B$: the DC bias for $I_C = 10$, 30, 100, 300 \textmu A, 1, 3 and 10 mA, one deck each",
                   r"$V_C = 5$ V;\quad $f = 1$ Hz to 1 MHz, 20 points per decade",
                   r"$R_G = 0$ gives $e_n$;\quad $R_G = 100$ k\ohm{} gives $e_n^2 + i_n^2 R_G^2 + 4kTR_G$, from which $i_n$",
                   r"$R_G = 1$ k\ohm{} at 1 mA gives NF;\quad read $i_c$, the noise part of the collector current, referred to $v_{in}$",
                   r"NF and $V_T$ against $R_S$ from $e_n$ and $i_n$: spot at 1 kHz, and over 10 Hz to 15.7 kHz"])
    d.write()


def capacitance():
    d = D("bjt-capacitance", "Capacitances", """
VO0 ao0 0 DC <VR> AC 1, VBO0 bo0 0 0, REO0 eo0 0 1e9, QO0   Cob: collector driven, base grounded, emitter open -> left
VI0 ai0 0 DC <VR> AC 1, VBI0 bi0 0 0, RCI0 ci0 0 1e9, QI0   Cib: emitter driven, base grounded, collector open -> right, emitter up
.ac, C = Im(I) / (2 pi f) at 1 MHz                                                                        -> the AC ammeters (measured)
One copy per reverse voltage in the deck; the drawing shows one of each.""")
    d.add("% Cob, left: the collector driven, the base grounded, the emitter open",
          r"\node[npn] (Q) at (2.6,3) {};", r"\node[anchor=west, font=\small] at ($(Q.C)+(0.15,-0.55)$) {DUT};",
          r"\draw (Q.B) -- ++(-0.8,0) coordinate (bo) -- (bo |- 0,\gnd) node[ground]{};",
          r"\draw (Q.E) -- ++(0,-0.4) coordinate (eo);", r"\node[anchor=west, font=\scriptsize] at ($(eo)+(0.08,0)$) {open};",
          r"\coordinate (ctop) at ($(Q.C)+(0,1.7)$);", r"\ammeter{Q.C}{ctop}{$i$}",
          r"\coordinate (vtop) at ($(ctop)+(1.9,0)$);", r"\draw (ctop) -- (vtop);",
          r"\draw[set] (vtop) to[V, l=$V_R + v$] (vtop |- 0,\gnd) node[ground, black]{};",
          r"\node[font=\small] at ($(ctop)+(-0.8,0.35)$) {$C_{ob}$};")
    d.nodename("west", r"$(Q.C)+(0.1,0.25)$", "ao"); d.nodename("south", r"$(bo)+(0.4,0.03)$", "bo")
    d.nodename("west", r"$(Q.E)+(0.1,-0.1)$", "eo")
    d.add("% Cib, right, flipped so the emitter is up: the emitter driven, the base grounded, the collector open",
          r"\node[npn, yscale=-1] (R) at (8.4,3) {};", r"\node[anchor=west, font=\small] at ($(R.E)+(0.15,-0.55)$) {DUT};",
          r"\draw (R.B) -- ++(-0.8,0) coordinate (bi) -- (bi |- 0,\gnd) node[ground]{};",
          r"\draw (R.C) -- ++(0,-0.4) coordinate (ci);", r"\node[anchor=west, font=\scriptsize] at ($(ci)+(0.08,0)$) {open};",
          r"\coordinate (rtop) at ($(R.E)+(0,1.7)$);", r"\ammeter{R.E}{rtop}{$i$}",
          r"\coordinate (wtop) at ($(rtop)+(1.9,0)$);", r"\draw (rtop) -- (wtop);",
          r"\draw[set] (wtop) to[V, l=$V_R + v$] (wtop |- 0,\gnd) node[ground, black]{};",
          r"\node[font=\small] at ($(rtop)+(-0.8,0.35)$) {$C_{ib}$};")
    d.nodename("west", r"$(R.E)+(0.1,0.25)$", "ai"); d.nodename("south", r"$(bi)+(0.4,0.03)$", "bi")
    d.nodename("west", r"$(R.C)+(0.1,-0.1)$", "ci")
    d.definitions([r"$V_R = 0.1$, 0.5, 1, 2, 5, 10, 20 and 30 V, one copy each;\quad $v = 1$ V of AC",
                   r"$C_{ob}$ also at 50, 100, 200 and 300 V, for high-voltage parts",
                   r"open = 1 G\ohm{} to ground;\quad $C = \mathrm{Im}(i) \,/\, (2\pi f)$ at $f = 1$ MHz",
                   r"$C_{ob}$: collector to base, emitter open;\quad $C_{ib}$: emitter to base, collector open"])
    d.write()


def distortion():
    d = D("bjt-distortion", "Distortion", """
VIN in 0 SIN(…), RS in b 1000   a 1 kHz sine through 1 kΩ into the base          -> source v_in (set) + resistor R_S
RL vcc c 5000, VCC vcc 0 10     5 kΩ load to the 10 V supply                      -> resistor R_L + source V_CC (set)
RE e x 260, CX x 0 1            260 Ω of degeneration to a node held at AC ground -> resistor R_E + capacitor C_X
IE x vee 0.001, VEE vee 0 -5    1 mA bias from a current source to -5 V           -> current source I_E (set) + source V_EE (set)
Q1 c b e                        the transistor                                    -> npn
V(c) read                       the output                                        -> voltmeter v_out (measured)
The gain-finding probe run is not drawn.""", top=7.8, gnd=2.0)
    d.transistor(y=4.2)
    d.add("% the collector: the load up to the rail, the output voltmeter beside it",
          r"\draw (Q.C) -- ++(0,0.4) coordinate (cj) to[R, l_=$R_L$] ++(0,1.6) coordinate (rtop);",
          r"\coordinate (vo) at ($(cj)+(2.0,0)$);", r"\draw (cj) -- (vo);",
          r"\voltmeter{vo |- 0,\gnd}{vo}{$v_{out}$}", r"\draw (vo |- 0,\gnd) node[ground]{};")
    d.nodename("east", r"$(Q.C)+(-0.15,0.2)$", "c")
    d.supply(label="$V_{CC}$", dx=3.4, frm="rtop"); d.nodename("south", r"$(rtop)+(1.0,0.05)$", "vcc")
    d.add("% the base: the source resistance and the signal source", r"\coordinate (b) at (Q.B);",
          r"\draw (b) -- ++(-0.3,0) coordinate (bj) to[R, l_=$R_S$] ++(-1.8,0) coordinate (vin);",
          r"\draw[set] (vin) to[V, l_=$v_{in}$] (vin |- 0,\gnd) node[ground, black]{};")
    d.nodename("south", r"$(b)+(-0.15,0.05)$", "b"); d.nodename("south east", r"$(vin)+(-0.05,0.05)$", "in")
    d.add("% the emitter: degeneration to node x, held at AC ground by CX, biased by IE from the negative rail",
          r"\draw (Q.E) to[R, l=$R_E$] ++(0,-1.5) coordinate (x);",
          r"\draw (x) -- ++(-1.3,0) coordinate (cx) to[C, l_=$C_X$] (cx |- 0,-0.9) node[ground]{};",
          r"\draw[set] (x) to[I, l=$I_E$] ++(0,-1.5) coordinate (vee);",
          r"\draw[set] (vee) to[V, l=$V_{EE}$] ++(0,-1.5) coordinate (bot) node[ground, black]{};")
    d.nodename("east", r"$(Q.E)+(-0.1,-0.2)$", "e"); d.nodename("south west", r"$(x)+(0.1,0.05)$", "x")
    d.nodename("south west", r"$(vee)+(0.1,0.05)$", "vee"); d.nodename("west", r"$(bot)+(0.3,0.1)$", "0")
    d.definitions([r"$v_{in}$ = 1 kHz sine, its level set for 1 V peak at the collector",
                   r"$R_S = 1$ k\ohm;\quad $R_L = 5$ k\ohm;\quad $V_{CC} = 10$ V;\quad $I_E = 1$ mA;\quad $V_{EE} = -5$ V",
                   r"$R_E = 260$ \ohm, so $g_m R_E = 10$;\quad $C_X = 1$ F holds node x at AC ground",
                   r"read $v_{out}$ over the last four of ten cycles: THD, HD2, HD3 by Goertzel"], y=-1.8)
    d.write()


def main():
    """every bipolar drawing, each with its PNP twin"""
    for f in (hfe_ic, runs, tracer, early, gummel, temperature, breakdown, reverse, saturation, vce_ib, switching, noise,
              capacitance, distortion):
        f()
    ac_gain("bjt-hfe-ac", "AC current gain", [r"read $i_c$, the AC part of the collector current;\quad $h_{fe} = i_c / i_b$ at $f = 1$ kHz"], AC_HEADER)
    ac_gain("bjt-ft", "Transition frequency",
            [r"read $i_c(f)$, the AC part of the collector current, $f = 1$ kHz to 100 GHz;\quad $|h_{21}| = i_c / i_b$;\quad $f_T$: $|h_{21}| = 1$",
             r"also $f_T = |h_{21}| \cdot f$ at $f = 1$, 20 and 100 MHz, where $f$ is above $f_\beta$ and $|h_{21}| \geq 1.5$"], AC_HEADER)
    print("16 bipolar drawings written, each with its PNP twin")


if __name__ == "__main__":
    import benches_fet
    import benches_opamp

    main()
    benches_fet.main()
    benches_opamp.main()
