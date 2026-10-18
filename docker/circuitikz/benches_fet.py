"""The JFET and MOSFET bench drawings, with the blocks of benches.py (which runs this): the transistor at (4,3)
drain up, its source grounded at y = 1, the drain ammeter up to the rail and the supply to the right, the gate
source to the left, through an ammeter where the deck reads the gate current; a second or third copy at x = 11
and x = 18. Blue is what the bench sets, red what it measures (a circled A reads a current, a circled V a
voltage), green the deck's node names. Every drawing is the set-up a person would wire, semantically the deck's:
a behavioural source is a current source, a 0 V source is an ammeter, a 1 GΩ resistor to ground is "open", and
the copies a deck packs are one circuit with the list of its conditions."""
from benches import D

MU = r"\textmu "
DEG = r"\textdegree "


# ------------------------------------------------------------------------ the blocks, for the copy named n
def fet(d, kind, n="", x=4, label="DUT", flip=None):
    d.fet(kind, x, 3, label, name=f"Q{n}", flip=flip, label_at=rf"$(Q{n}.S)+(0.15,-0.55)$" if flip else None)


def ground(d, n="", terminal="S"):
    d.ground(f"Q{n}.{terminal}")


def drain(d, n="", label="$I_D$", node=None, up=1.7):
    """an ammeter from the drain straight up to ({n}top), the rail's end"""
    d.add("% the ammeter in the drain, up to the rail", rf"\coordinate ({n}top) at ($(Q{n}.D)+(0,{up})$);",
          rf"\ammeter{{Q{n}.D}}{{{n}top}}{{{label}}}")
    if node:
        d.nodename("west", rf"$(Q{n}.D)+(0.1,0.25)$", node)


def supply(d, n="", label="$V_{DS}$", dx=2.6, node=None, frm=None):
    """the rail from ({n}top) to the right, then a voltage source down to ground, + up"""
    frm = frm or f"{n}top"
    d.add("% the drain supply at the right, + up, - to ground", rf"\coordinate ({n}vtop) at ($({frm})+({dx},0)$);",
          rf"\draw ({frm}) -- ({n}vtop);",
          rf"\draw[set] ({n}vtop) to[V, l={{{label}}}] ({n}vtop |- 0,\gnd) node[ground, black]{{}};")
    if node:
        d.nodename("south", rf"$({frm})+({dx / 2},0.05)$", node)


def gate(d, n="", label="$V_{GS}$", node="g", dx=-1.4, kind="V", ammeter=None):
    d.gate(label, node, dx, kind, ammeter, terminal=f"Q{n}.G", name=f"{n}g")


def opened(d, n="", terminal="S"):
    """a terminal left open: 1 GΩ to ground in the deck, a short lead and the word in the drawing"""
    dy = -0.4 if terminal == "S" else 0.4
    d.add(f"% the {'source' if terminal == 'S' else 'drain'} open (1 GΩ to ground in the deck)",
          rf"\draw (Q{n}.{terminal}) -- ++(0,{dy}) coordinate ({n}open);",
          rf"\node[anchor=west, font=\scriptsize] at ($({n}open)+(0.08,0)$) {{open}};")


def drain_ground(d, n=""):
    """the drain to ground: a lead up and a ground symbol turned over"""
    d.add("% the drain grounded", rf"\draw (Q{n}.D) -- ++(0,0.5) node[ground, rotate=180]{{}};")
    d.nodename("west", rf"$(Q{n}.D)+(0.1,0.25)$", "0")


def voltmeter(d, frm, dx, label, name="vm"):
    """a voltmeter from a point dx to the right of (frm) down to ground"""
    d.add(f"% the voltmeter on {frm}", rf"\coordinate ({name}) at ($({frm})+({dx},0)$);", rf"\draw ({frm}) -- ({name});",
          rf"\voltmeter{{{name} |- 0,\gnd}}{{{name}}}{{{label}}}", rf"\draw ({name} |- 0,\gnd) node[ground]{{}};")


def forced(d, n="", label="$I_D$", into="D", clamp="30", vm="$V_{DS}$", node=None, rail=5.2):
    """a current pushed into a terminal from a grounded rail above, a clamp diode from the terminal to a rail,
    and a voltmeter on the terminal (the forced-current decks)"""
    t = f"Q{n}.{into}"
    d.add(f"% the {'drain' if into == 'D' else 'source'} drive: a current pushed in from a grounded rail",
          rf"\coordinate ({n}top) at ($({t})+(0,2.0)$);", rf"\draw[set] ({n}top) to[I, l={{{label}}}] ({t});",
          rf"\coordinate ({n}rail) at ($({n}top)+({rail},0)$);",
          rf"\draw ({n}top) -- ({n}rail) -- ({n}rail |- 0,\gnd) node[ground]{{}};")
    if node:
        d.nodename("east", rf"$({t})+(-0.45,0.8)$", node)
    d.add("% the clamp: a diode from the terminal to a rail, and the voltmeter on the terminal",
          rf"\coordinate ({n}cj) at ($({t})+(0,0.3)$);", rf"\coordinate ({n}vm) at ($({n}cj)+(1.8,0)$);",
          rf"\coordinate ({n}dj) at ($({n}cj)+(2.8,0)$);", rf"\coordinate ({n}cl) at ($({n}dj)+(1.6,0)$);",
          rf"\draw ({n}cj) -- ({n}dj) to[D, l=clamp] ({n}cl);",
          rf"\draw[set] ({n}cl) to[V, l=${clamp}$ V] ({n}cl |- 0,\gnd) node[ground, black]{{}};",
          rf"\voltmeter{{{n}vm |- 0,\gnd}}{{{n}vm}}{{{vm}}}", rf"\draw ({n}vm |- 0,\gnd) node[ground]{{}};")
    d.nodename("south west", rf"$({n}cl)+(0.05,0.05)$", f"cl{n}")


def stage(d, n, kind, x, rd, rs, rin, vdd, out, bypass=None, sink=None, load=None, node_d="d", node_s="s", label="DUT"):
    """a common-source stage (out="D": RD up to the rail, the voltmeter on the drain) or a source follower
    (out="S": the drain on the rail, the voltmeter on the source); RS to ground or to a current sink"""
    fet(d, kind, n, x, label=label)
    q = f"Q{n}"
    if rd:
        d.add(f"% copy {n}: the drain load up to the rail",
              rf"\draw ({q}.D) -- ++(0,0.4) coordinate ({n}dj) to[R, l_={{{rd}}}] ++(0,1.6) coordinate ({n}top);")
    else:
        d.add(f"% copy {n}: the drain on the rail", rf"\draw ({q}.D) -- ++(0,2.0) coordinate ({n}top);")
    d.add(rf"\coordinate ({n}vtop) at ($({n}top)+({5.6 if load else 4.2},0)$);", rf"\draw ({n}top) -- ({n}vtop);",
          rf"\draw[set] ({n}vtop) to[V, l={{{vdd}}}] ({n}vtop |- 0,\gnd) node[ground, black]{{}};")
    d.nodename("south", rf"$({n}top)+(1.0,0.05)$", "vdd")
    if rd:
        d.nodename("east", rf"$({q}.D)+(-0.15,0.2)$", node_d)
    d.add("% the gate: the source resistance and the signal source", rf"\coordinate ({n}g) at ({q}.G);",
          rf"\draw ({n}g) -- ++(-0.3,0) coordinate ({n}gj) to[R, l_={{{rin}}}] ++(-1.8,0) coordinate ({n}vin);",
          rf"\draw[set] ({n}vin) to[V, l_=$v_{{in}}$] ({n}vin |- 0,\gnd) node[ground, black]{{}};")
    d.nodename("south", rf"$({n}g)+(-0.15,0.05)$", "g"); d.nodename("south east", rf"$({n}vin)+(-0.05,0.05)$", "in")
    if sink:
        d.add("% the source: the resistor and the sink to the negative rail",
              rf"\draw ({q}.S) to[R, l={{{rs}}}] ++(0,-1.2) coordinate ({n}x);" if rs else rf"\draw ({q}.S) -- ++(0,-0.5) coordinate ({n}x);",
              rf"\draw[set] ({n}x) to[I, l={{{sink}}}] ++(0,-1.3) coordinate ({n}vee);",
              rf"\draw[set] ({n}vee) to[V, l=$V_{{SS}}$] ++(0,-1.3) coordinate ({n}bot) node[ground, black]{{}};")
        d.nodename("south west", rf"$({n}vee)+(0.1,0.05)$", "vss"); d.nodename("west", rf"$({n}bot)+(0.3,0.1)$", "0")
    elif rs:
        side = "l_" if out == "S" else "l"
        d.add("% the source resistor to ground", rf"\draw ({q}.S) to[R, {side}={{{rs}}}] ({q}.S |- 0,\gnd) node[ground]{{}};")
    if out == "S":
        d.nodename("west", rf"$({q}.S)+(0.1,-0.3)$", node_s)
    else:
        d.nodename("east", rf"$({q}.S)+(-0.1,-0.2)$", node_s)
    if bypass:
        at = f"{n}x" if sink else f"{q}.S"
        d.add("% the bypass", rf"\draw ({at}) -- ++(-1.3,0) coordinate ({n}cx) to[C, l_={{{bypass}}}] ({n}cx |- 0,\gnd) node[ground]{{}};")
    if out == "D":
        voltmeter(d, f"{n}dj", 2.6, "$v_{out}$", f"{n}vo")
    elif load:
        d.add("% the load, AC-coupled", rf"\coordinate ({n}sj) at ($({q}.S)+(0,-0.5)$);",
              rf"\draw ({n}sj) -- ++(1.0,0) to[C, l={{{load[0]}}}] ++(1.6,0) coordinate ({n}lj);",
              rf"\draw ({n}lj) to[R, l_={{{load[1]}}}] ({n}lj |- 0,\gnd) node[ground]{{}};")
        voltmeter(d, f"{n}lj", 1.8, "$v_{out}$", f"{n}vo")
        d.nodename("south east", rf"$({n}lj)+(-0.1,0.05)$", "l")
    else:
        d.add(rf"\coordinate ({n}sj) at ($({q}.S)+(0,-0.5)$);")
        voltmeter(d, f"{n}sj", 2.2, "$v_{out}$", f"{n}vo")


def two(d, kind, labels):
    """two copies side by side, A and B, at x = 4 and 11"""
    for n, x, label in (("A", 4, labels[0]), ("B", 11, labels[1])):
        fet(d, kind, n, x, label=label)
        ground(d, n)


# ------------------------------------------------------------------------ the JFET drawings
def jfet_runs():
    d = D("jfet-runs", "Operating point", """
VT1 dt1 0 10   the 10 V copy's drain supply; its current is ID   -> source V_DS (set) + ammeter I_D (measured)
VIG1 g gi1 0   a 0 V source from the gate drive into the gate     -> ammeter I_G (measured)
JT1 dt1 gi1 0  the transistor, source grounded                   -> njfet
read where the transfer sweep's gate passes through 0 V: IDSS, IG""", twin=False)
    fet(d, "jfet"); ground(d); drain(d, node="dt1"); supply(d)
    gate(d, label="$V_{GS}$", node="g", ammeter="$I_G$")
    d.definitions([r"$V_{GS} = 0$, $V_{DS} = 10$ V: the point of the transfer sweep where the gate passes through 0 V",
                   r"read $I_D = I_{DSS}$ and $I_G$: does the card load, and does the solver settle?"])
    d.write()


def jfet_transfer():
    d = D("jfet-transfer", "Transfer characteristic", """
VT0 dt0 0 5    the drain supply of one copy; its current is ID     -> source V_DS (set) + ammeter I_D (measured)
VIG0 g gi0 0   a 0 V source from the gate drive into the gate       -> ammeter I_G (measured)
JT0 dt0 gi0 0  the copy, source grounded                            -> njfet
VGS g 0 0      the gate drive, swept, shared by the four copies     -> source V_GS (set)
Four copies run in the deck, one per VDS; the drawing shows one.""", twin=False)
    fet(d, "jfet"); ground(d); drain(d, node="dt0"); supply(d)
    gate(d, label="$V_{GS}$", node="g", ammeter="$I_G$")
    d.definitions([r"$V_{GS}$ swept $-10$ V to $+0.6$ V in 5 mV steps;\quad $V_{DS} = 5$, 10, 15 and 20 V, one copy of the circuit each",
                   r"read $I_D(V_{GS})$ and $I_G$;\quad $I_{DSS} = I_D$ at $V_{GS} = 0$;\quad $V_{GS(off)}$: the $V_{GS}$ at which $I_D$ reaches 1 nA, 10 nA and 1 " + MU + "A",
                   r"$V_{GS}$ at $I_D = 10$ " + MU + r"A $\dots$ 100 mA on the 10 V curve, kept for the decks that bias the transistor there"])
    d.write()


def jfet_tracer():
    d = D("jfet-tracer", "Curve tracer", """
VGK1 gk1 0 -0.8   the gate of trace k, (5 - k) steps below ground     -> source V_GS (set)
VK1 sw dk1 0      a 0 V source from the swept node to the drain       -> ammeter I_D (measured)
JK1 dk1 gk1 0     the copy, source grounded                           -> njfet
VSW sw 0, .dc     the swept drain supply, shared by every copy        -> source V_DS (set)
The thirty copies (five per family) are drawn as one transistor with a stepped gate.""", twin=False)
    fet(d, "jfet"); ground(d); drain(d, node="dk"); supply(d, node="sw"); gate(d, label="$V_{GS}$", node="gk")
    d.definitions([r"$V_{GS} = -(5 - k)\,V_{step}$, $k = 1, \dots, 5$: the top trace at 0 V, the bottom one four steps down",
                   r"$V_{step} = 0.1$, 0.25, 0.5, 1 and 2 V, one family each;\quad or auto: $V_{GS(off)} / 5$, the model's own (from the transfer sweep)",
                   r"$V_{DS}$ swept 0 to 25 V in 50 mV steps;\quad read $I_D(V_{DS})$ for each $k$"])
    d.write()


def jfet_gm():
    d = D("jfet-gm", "Transconductance and output conductance", """
VD0 d0 0 10              copy A's drain supply; its AC current is gfs            -> source V_DS (set) + ammeter I_D + i_d (measured)
VG0 g0 0 DC <vgs> AC 1   copy A's gate bias with 1 V of AC on top                 -> source V_GS + v_gs (set)
JM0 d0 g0 0 DUT          copy A, source grounded                                  -> njfet
VDO0 do0 0 DC 10 AC 1    copy B's drain supply with the AC: its current is gos    -> source V_DS + v_ds (set) + ammeter I_D + i_d (measured)
VGO0 go0 0 <vgs>         copy B's gate bias, held                                 -> source V_GS (set)
One pair of copies per ladder current in the deck; the drawing shows one pair.""", twin=False)
    two(d, "jfet", ("A", "B"))
    drain(d, "A", "$I_D + i_d$", node="d0"); supply(d, "A", "$V_{DS}$"); gate(d, "A", "$V_{GS} + v_{gs}$", node="g0")
    drain(d, "B", "$I_D + i_d$", node="do0"); supply(d, "B", "$V_{DS} + v_{ds}$"); gate(d, "B", "$V_{GS}$", node="go0")
    d.definitions([r"$V_{GS}$: the bias for $I_D = 10$ " + MU + r"A, 30 " + MU + r"A, 100 " + MU + r"A $\dots$ 100 mA (from the transfer sweep), one pair of copies each;\quad $V_{DS} = 10$ V",
                   r"A: $v_{gs} = 1$ V of AC, the simulator's unit signal, not a real amplitude;\quad $g_{fs} = i_d / v_{gs}$ at $f = 1$ kHz",
                   r"B: $v_{ds} = 1$ V of AC on the drain, the gate held;\quad $g_{os} = i_d / v_{ds}$;\quad a ladder current the model never reaches is not read"])
    d.write()


def jfet_ohmic():
    d = D("jfet-ohmic", "Ohmic region", """
VGR0 gr0 0 <vgs>         copy A's gate, held at a fraction of VGS(off)            -> source V_GS (set)
VR0 sw dr0 0             a 0 V source from the swept node to its drain            -> ammeter I_D (measured)
JR0 dr0 gr0 0 DUT        copy A, source grounded                                  -> njfet
VGB0 gb0 0 <2 vgs>       copy B's bias at twice the fraction                      -> source 2 V_GS (set)
RFD0 df0 gf0, RFB0 gb0 gf0   the two 1 MΩ resistors: the gate at VGS + VDS/2    -> resistors R_FD, R_FB
JF0 df0 gf0 0 DUT        copy B                                                   -> njfet
VSW sw 0, .dc            the swept drain supply of every copy                     -> source V_DS (set)
Four pairs of copies run in the deck, one per fraction; the drawing shows one pair. The rDS-against-VGS
deck (50 mV on the drain, the gate swept in units of VGS(off)) is copy A again, in the definitions.""", twin=False)
    fet(d, "jfet", "A", 4, label="A"); ground(d, "A"); fet(d, "jfet", "B", 12.5, label="B"); ground(d, "B")
    drain(d, "A", node="dr0"); supply(d, "A", "$V_{DS}$", node="sw"); gate(d, "A", "$V_{GS}$", node="gr0")
    drain(d, "B", node="df0"); supply(d, "B", "$V_{DS}$", node="sw")
    d.add("% copy B's gate: the bias through R_FB, and R_FD from the drain, meeting at the gate",
          r"\coordinate (Bg) at (QB.G);", r"\draw (Bg) -- ++(-0.4,0) coordinate (Bgj) to[R, l_=$R_{FB}$] ++(-1.8,0) coordinate (Bgsrc);",
          r"\draw[set] (Bgsrc) to[V, l_={$2\,V_{GS}$}] (Bgsrc |- 0,\gnd) node[ground, black]{};",
          r"\draw (Bgj) to[R, l=$R_{FD}$] (Bgj |- Btop) -- (Btop);")
    d.nodename("south", r"$(Bg)+(-0.2,0.02)$", "gf0"); d.nodename("south east", r"$(Bgsrc)+(-0.05,0.05)$", "gb0")
    d.definitions([r"$V_{GS} = 0$, $V_{GS(off)}/4$, $V_{GS(off)}/2$ and $3\,V_{GS(off)}/4$ (the model's own), one pair of copies each;\quad $V_{DS}$ swept $-0.5$ to $+0.5$ V in 5 mV steps",
                   r"B: $R_{FD} = R_{FB} = 1$ M\ohm{} and the bias at $2\,V_{GS}$, so that the gate sits at $V_{GS} + V_{DS}/2$",
                   r"read $I_D(V_{DS})$: $r_{DS}$ is the chord over $\pm 50$ mV; a cubic fit gives the second- and third-order terms, plain and with feedback",
                   r"$r_{DS}$ against $V_{GS}$: copy A with $V_{DS} = 50$ mV and $V_{GS} = V_{GS(off)} \times 0$ to 1.2, a second deck"])
    d.write()


def jfet_gate():
    d = D("jfet-gate", "Gate diode and gate leakage", """
VGF gf gsw 0     a 0 V source from the swept node into copy A's gate   -> ammeter I_G (measured)
JF 0 gf 0 DUT    copy A, drain and source grounded                     -> njfet
VGSW gsw 0, .dc  the gate drive, swept forward (and reverse)           -> source V_GS (set)
VF0 sw df0 0     a 0 V source from the swept node to copy B's drain    -> ammeter I_D (measured)
VGB0 gb0 0 -1.5  copy B's gate bias; its current is IG                 -> source V_GS (set) + ammeter I_G (measured)
JD0 df0 gb0 0    copy B, source grounded                               -> njfet
VSW sw 0, .dc    the swept drain supply                                -> source V_DS (set)
Three decks: forward and reverse are copy A with two sweeps; the field deck is copy B, four copies.""", twin=False)
    two(d, "jfet", ("A", "B"))
    drain_ground(d, "A"); gate(d, "A", "$V_{GS}$", node="gf", ammeter="$I_G$")
    drain(d, "B", node="df0"); supply(d, "B", "$V_{DS}$", node="sw"); gate(d, "B", "$V_{GS}$", node="gb0", ammeter="$I_G$")
    d.definitions([r"A: $V_{GS}$ swept 0 to $+0.9$ V in 5 mV steps (forward), and 0 to $-40$ V in 0.1 V steps (reverse), drain and source grounded;\quad read $I_G$",
                   r"B: $V_{GS}$ the bias for $I_D = 100$ " + MU + r"A, 1, 3 and 10 mA (from the transfer sweep), one copy each;\quad $V_{DS}$ swept 0 to 25 V in 0.1 V steps",
                   r"read $I_G$ against $V_{DG} = V_{DS} - V_{GS}$;\quad $I_{GSS}$ at 10, 20 and 30 V from the reverse sweep"])
    d.write()


def jfet_capacitance():
    d = D("jfet-capacitance", "Capacitances", """
VDX0 dx0 0 0.1, VGX0 gx0 0 DC 0 AC 1, JX0   copy A: the drain held, the gate at 0 V with AC   -> Ciss from i_g, Crss from i_d
VGS0 gs0 0 DC -0.1 AC 1, RDS0 ds0 0 1e9, JS0   copy B: the gate below the source with AC, the drain open   -> Cgs
VDG0 dg0 0 0.1, VGG0 gg0 0 DC 0 AC 1, RSG0 sg0 0 1e9, JG0   copy C: the drain held, AC on the gate, the source open   -> Cgd
.ac, C = Im(i) / (2 pi f) at 1 MHz                                                            -> the AC ammeters (measured)
One set of three copies per ladder voltage in the deck; the drawing shows one set.""", twin=False)
    for n, x, label in (("A", 3.4, "A"), ("B", 10.8, "B"), ("C", 17.6, "C")):
        fet(d, "jfet", n, x, label=label)
    ground(d, "A"); drain(d, "A", "$i_d$", node="dx0", up=1.5); supply(d, "A", "$V_R$", dx=2.0)
    gate(d, "A", "$0 + v$", node="gx0", ammeter="$i_g$", dx=-1.0)
    ground(d, "B"); opened(d, "B", "D"); gate(d, "B", "$-V_R + v$", node="gs0", ammeter="$i$", dx=-1.0)
    opened(d, "C", "S")
    d.add("% copy C: the drain held", r"\coordinate (Ctop) at ($(QC.D)+(0,1.5)$);", r"\draw (QC.D) -- (Ctop);")
    d.nodename("west", r"$(QC.D)+(0.1,0.25)$", "dg0")
    supply(d, "C", "$V_R$", dx=2.0); gate(d, "C", "$0 + v$", node="gg0", ammeter="$i$", dx=-1.0)
    for n, what in (("A", "$C_{iss}$, $C_{rss}$"), ("B", "$C_{gs}$"), ("C", "$C_{gd}$")):
        d.add(rf"\node[font=\small] at ($(Q{n}.D)+(-1.0,1.9)$) {{{what}}};")
    d.definitions([r"$V_R = 0.1$, 0.5, 1, 2, 5, 10, 15 and 20 V, one set of copies each;\quad $v = 1$ V of AC;\quad open = 1 G\ohm{} to ground",
                   r"$C = \mathrm{Im}(i) \,/\, (2\pi f)$ at $f = 1$ MHz:\quad A: $C_{iss}$ from $i_g$, $C_{rss}$ from $i_d$;\quad B: $C_{gs}$ alone, the drain open;\quad C: $C_{gd}$ alone, the source open"])
    d.write()


def jfet_frequency():
    d = D("jfet-frequency", "Transconductance against frequency, and a stage's bandwidth", """
VD0 d0 0 10, VG0 g0 0 DC <vgs> AC 1, JY0   copy A: a gfs copy swept to 1 GHz          -> source V_DS (set), source V_GS + v_gs (set), ammeter i_d (measured)
VDD vdd 0 18, RD vdd dc <rd>              the stage's supply and drain load            -> source V_DD (set), resistor R_D
RS s 0 <rs>, CS s 0 1000u                 the source resistor, bypassed                -> resistor R_S, capacitor C_S
RIN in g 1000, VIN in 0 AC 1              the drive through 1 kΩ                       -> resistor R_in, source v_in (set)
JS dc g s DUT, V(dc) read                 the stage; its output                        -> voltmeter v_out (measured)
Two decks drawn side by side: the yfs copy (one per ladder current) and the common-source stage.""", twin=False)
    fet(d, "jfet", "A", 4, label="A"); ground(d, "A")
    drain(d, "A", "$I_D + i_d$", node="d0"); supply(d, "A", "$V_{DS}$"); gate(d, "A", "$V_{GS} + v_{gs}$", node="g0")
    stage(d, "B", "jfet", 13, "$R_D$", "$R_S$", "$R_{in}$", "$V_{DD}$", "D", bypass="$C_S$", node_d="dc", label="B")
    d.definitions([r"A: $V_{GS}$ the bias for $I_D = 100$ " + MU + r"A, 1, 3 and 10 mA (from the transfer sweep), one copy each;\quad $V_{DS} = 10$ V;\quad $v_{gs} = 1$ V of AC",
                   r"read $|y_{fs}| = i_d / v_{gs}$, $f = 1$ kHz to 1 GHz, 20 points per decade",
                   r"B: $V_{DD} = 18$ V;\quad $R_S$ for $I_D = I_{DSS}/3$ (from the transfer sweep), bypassed by $C_S = 1000$ " + MU + r"F;\quad $R_D$ for $V_{DS} = 9$ V;\quad $R_{in} = 1$ k\ohm",
                   r"read $v_{out} / v_{in}$, $f = 1$ Hz to 10 MHz"])
    d.write()


def fet_noise(name, kind, header, lines):
    d = D(name, "Noise", header, twin=False)
    fet(d, kind); ground(d); drain(d, "", "$I_D + i_d$", node="d"); supply(d, "", "$V_D$")
    d.nodename("south west", r"$(top)+(0.15,0.05)$", "dd")
    d.add("% the gate: the source resistance, the noise input and the bias in series, at the far left",
          r"\coordinate (g) at (Q.G);", r"\draw (g) -- ++(-0.3,0) coordinate (gj) to[R, l_=$R_G$] ++(-1.8,0) coordinate (vin);",
          r"\draw[set] (vin) to[V, l_=$v_{in}$] ++(0,-1.3) coordinate (gb);",
          r"\draw[set] (gb) to[V, l_=$V_{GS}$] (gb |- 0,\gnd) node[ground, black]{};")
    d.nodename("south", r"$(g)+(-0.15,0.05)$", "g"); d.nodename("south east", r"$(vin)+(-0.05,0.05)$", "in")
    d.nodename("east", r"$(gb)+(-0.05,0)$", "gb")
    d.definitions(lines)
    d.write()


JFET_NOISE = """
VSENSE d dd 0, VD dd 0 10   the sensing source and the drain supply       -> ammeter I_D + i_d (measured: the noise part) + source V_D (set)
VGB gb 0 <vgs>              the gate bias for the step                    -> source V_GS (set)
VIN in gb DC 0 AC 1         the noise input, riding on the bias           -> source v_in (set)
RG in g                     the source resistance                         -> resistor R_G
J1 d g 0                    the transistor, source grounded               -> njfet
H1, RLOAD, .noise           the sensed current is the noise output, referred to v_in -> the ammeter's reading"""


def jfet_noise():
    fet_noise("jfet-noise", "jfet", JFET_NOISE,
              [r"$V_{GS}$: the bias for $I_D = 100$ " + MU + r"A, 300 " + MU + r"A, 1, 3 and 10 mA (from the transfer sweep), one deck each;\quad $V_D = 10$ V",
               r"$f = 1$ Hz to 1 MHz, 20 points per decade;\quad $R_G = 0$ gives $e_n$;\quad $R_G = 10$ M\ohm{} gives $e_n^2 + i_n^2 R_G^2 + 4kTR_G$, from which $i_n$",
               r"$R_G = 1$ M\ohm{} at 1 mA gives NF;\quad read $i_d$, the noise part of the drain current, referred to $v_{in}$"])


def jfet_temperature():
    d = D("jfet-temperature", "Temperature", """
VT dt 0 10      the drain supply; its current is ID        -> source V_DS (set) + ammeter I_D (measured)
VGS g 0, .dc    the gate drive, swept                      -> source V_GS (set)
JT dt g 0       the transistor, source grounded            -> njfet
.temp -55 / 100 / 125 / 150 (and 25 from the transfer deck) -> the thermometer (set)""", twin=False)
    fet(d, "jfet"); ground(d); drain(d, node="dt"); supply(d); gate(d, label="$V_{GS}$", node="g")
    d.thermometer()
    d.definitions([r"$V_{GS}$ swept $-10$ V to $+0.6$ V in 5 mV steps;\quad $V_{DS} = 10$ V;\quad $T = -55$, 100, 125 and 150 " + DEG + r"C, one deck each; 25 " + DEG + r"C from the transfer deck",
                   r"read $I_{DSS}$ and $V_{GS(off)}$ (10 nA) at each $T$;\quad $I_D$ against $T$ at $V_{GS} = 0$, $V_{GS(off)}/4$, /2 and 3/4",
                   r"the zero-TC point: where the 25 and 125 " + DEG + r"C curves cross"])
    d.write()


def jfet_switch():
    d = D("jfet-switch", "Analogue switch", """
VS s 0 1          the signal source, on the source terminal          -> source V_S (set)
JW l g s DUT      the switch, drain to the load                      -> njfet
RL l 0 1000       the load                                           -> resistor R_L
RG in g 1000, VIN in 0 PWL(…)   the gate drive through 1 kΩ          -> resistor R_G + source V_in (set)
V(l) read                       the load voltage                     -> voltmeter v_load (measured)
The charge-injection deck replaces RL by a 1 nF hold capacitor and puts the signal at 0 V.""", twin=False)
    fet(d, "jfet")
    d.add("% the source terminal on the signal source",
          r"\draw (Q.S) -- ++(0,-0.3) coordinate (sj);", r"\draw[set] (sj) to[V, l=$V_S$] (sj |- 0,\gnd) node[ground, black]{};")
    d.nodename("east", r"$(Q.S)+(-0.1,-0.2)$", "s")
    d.add("% the drain to the load node, the load down to ground, the voltmeter beside it",
          r"\draw (Q.D) -- ++(0,0.8) coordinate (l) -- ++(2.2,0) coordinate (rl);",
          r"\draw (rl) to[R, l_=$R_L$] (rl |- 0,\gnd) node[ground]{};")
    d.nodename("south", r"$(l)+(1.0,0.05)$", "l")
    voltmeter(d, "rl", 1.8, "$v_{load}$")
    d.add("% the gate resistor and the pulse source", r"\coordinate (g) at (Q.G);",
          r"\draw (g) -- ++(-0.3,0) coordinate (gj) to[R, l_=$R_G$] ++(-1.8,0) coordinate (vin);",
          r"\draw[set] (vin) to[V, l_=$V_{in}$] (vin |- 0,\gnd) node[ground, black]{};")
    d.nodename("south", r"$(g)+(-0.15,0.05)$", "g"); d.nodename("south east", r"$(vin)+(-0.05,0.05)$", "in")
    d.definitions([r"$V_S = 1$ V;\quad $R_L = 1$ k\ohm{} and 10 k\ohm, one deck each;\quad $R_G = 1$ k\ohm",
                   r"$V_{in}$: $V_{off}$, then 0 V from 100 ns to 2.11 " + MU + r"s, then $V_{off}$;\quad 10 ns edges;\quad $V_{off} = -10$ V, or twice the model's own $V_{GS(off)}$",
                   r"read $v_{load}(t)$: $t_{on}$ from the gate's rising edge to the 90\,\% crossing, $t_{off}$ from the falling edge to the 10\,\% crossing",
                   r"charge injection: $V_S = 0$, $R_L$ replaced by a 1 nF hold capacitor, the gate stepped from 0 V to $V_{off}$ once;\quad $Q = C$ times the step of $v_{load}$"])
    d.write()


def jfet_distortion():
    d = D("jfet-distortion", "Distortion", """
VDD vdd 0 18, RD vdd d <rd>       the supply and the drain load                  -> source V_DD (set) + resistor R_D
RS s 0 <rs>                       the source resistor, unbypassed                -> resistor R_S
RIN in g 10000, VIN in 0 SIN(…)   the 1 kHz sine through 10 kΩ                   -> resistor R_in + source v_in (set)
J1 d g s DUT, V(d) read           copy A, the common-source stage; its output    -> njfet, voltmeter v_out (measured)
J1 vdd g s DUT, V(s) read         copy B, the follower deck: drain on the rail   -> voltmeter v_out on the source
The follower is a second deck; the gain-finding probe run is not drawn.""", top=7.8, gnd=2.0, twin=False)
    stage(d, "A", "jfet", 4, "$R_D$", "$R_S$", "$R_{in}$", "$V_{DD}$", "D", label="A")
    stage(d, "B", "jfet", 14, None, "$R_S$", "$R_{in}$", "$V_{DD}$", "S", label="B")
    d.definitions([r"$V_{DD} = 18$ V;\quad $R_S$ for $I_D = I_{DSS}/3$ (from the transfer sweep), unbypassed;\quad $R_D$ for $V_{DS} = 9$ V;\quad $R_{in} = 10$ k\ohm",
                   r"$v_{in}$ = 1 kHz sine, its level set by a 20 mV probe run for 1 V peak at the output (and 3 V for A, into the gate diode)",
                   r"A: common source, the output on the drain;\quad B: source follower, the drain on the rail, the output across $R_S$",
                   r"read $v_{out}$ over the last four of ten cycles: THD, HD2, HD3 by Goertzel"], y=-0.1)
    d.write()


def jfet_breakdown():
    d = D("jfet-breakdown", "Breakdown and leakage", """
VA sw ga 0, RDA da 0 1e9, JA    copy A: the gate driven from the swept node, drain open       -> ammeter I (measured), source V_GS (set)
VB sw db 0, RSB sb 0 1e9, JB    copy B: the drain driven, gate grounded, source open          -> ammeter I, source V_DG
VC sw dc 0, VGC gc 0 <2 vgs_off>, JC   copy C: the drain driven, the gate at twice VGS(off)   -> ammeter I, sources V_DS and V_GS
VSW sw 0, .dc                   the swept node                                                -> the swept source
Three decks drawn as one.""", twin=False)
    for n, x in (("A", 3.6), ("B", 10.0), ("C", 16.6)):
        fet(d, "jfet", n, x, label=n)
    ground(d, "A"); opened(d, "A", "D"); gate(d, "A", "$V_{GS}$", node="ga", ammeter="$I$", dx=-1.0)
    opened(d, "B", "S"); drain(d, "B", "$I$", node="db"); supply(d, "B", "$V_{DG}$", dx=2.2, node="sw")
    gate(d, "B", None, node="0", dx=-1.0)
    ground(d, "C"); drain(d, "C", "$I$", node="dc"); supply(d, "C", "$V_{DS}$", dx=2.2, node="sw")
    gate(d, "C", r"$2\,V_{GS(off)}$", node="gc", dx=-1.0)
    d.definitions([r"A: $V_{GS}$ swept 0 to $-100$ V, drain open;\quad B: $V_{DG}$ swept 0 to 300 V, source open;\quad C: $V_{DS}$ swept 0 to 300 V with the gate at $2\,V_{GS(off)}$",
                   r"open = 1 G\ohm{} to ground;\quad read $I$: the breakdown voltage is where $I$ passes 1 mA, else absent",
                   r"$I_{GSS} = I$ at 20 V (A);\quad $I_{D(off)} = I$ at 15 V (C)"])
    d.write()


# ------------------------------------------------------------------------ the MOSFET drawings
def mos_runs():
    d = D("mosfet-runs", "Operating point", """
VT0 dt0 0 1      the 1 V copy's drain supply; its current is ID         -> source V_DS (set) + ammeter I_D (measured)
MT0 dt0 g 0 DUT  the transistor, source grounded, gate on the swept node -> nmos
VGS g 0, .dc     the gate drive                                           -> source V_GS (set)
Read where the transfer sweep's gate passes through 10 V and 4.5 V; the body diode's point comes from
the body-diode deck, not drawn here.""", twin=False)
    fet(d, "mosfet"); ground(d); drain(d, node="dt0"); supply(d); gate(d, label="$V_{GS}$", node="g")
    d.definitions([r"$V_{DS} = 1$ V;\quad $V_{GS} = 10$ V and 4.5 V: two points of the transfer sweep's 1 V copy",
                   r"read $I_D$: does the card load, and what does it pass when switched on;\quad the body diode at $V_{SD} = 1$ V from the body-diode deck"])
    d.write()


def mos_transfer():
    d = D("mosfet-transfer", "Transfer characteristic and threshold", """
VT2 dt2 0 15      copy A's drain supply (one of four: 1, 6, 15, 25 V); its current is ID   -> source V_DS (set) + ammeter I_D (measured)
MT2 dt2 g 0 DUT   copy A, source grounded                                                  -> nmos
VTD dtd g 0       copy B: the drain tied to the gate through a 0 V source                  -> ammeter I_D (measured)
MTD dtd g 0 DUT   copy B, diode-connected                                                  -> nmos
VGS g 0, .dc      the gate drive, shared by every copy                                     -> source V_GS (set)
Five copies run in one deck; the drawing shows two.""", twin=False)
    two(d, "mosfet", ("A", "B"))
    drain(d, "A", node="dt2"); supply(d, "A"); gate(d, "A", "$V_{GS}$", node="g")
    drain(d, "B", node="dtd")
    d.add("% copy B: the drain's ammeter looped back to the gate", r"\coordinate (Bg) at (QB.G);",
          r"\coordinate (Bgsrc) at ($(Bg)+(-1.4,0)$);", r"\draw (Btop) -| (Bgsrc) -- (Bg);",
          r"\draw[set] (Bgsrc) to[V, l_={$V_{GS}$}] (Bgsrc |- 0,\gnd) node[ground, black]{};")
    d.nodename("south", r"$(Bg)+(-0.45,0.02)$", "g")
    d.definitions([r"$V_{GS}$ swept $-2$ V to $+15$ V in 10 mV steps, every gate on the one source;\quad A: $V_{DS} = 1$, 6, 15 and 25 V, one copy each",
                   r"B: diode-connected, $V_{DS} = V_{GS}$, the way the sheets define $V_{th}$;\quad read $I_D(V_{GS})$ of every copy",
                   r"$V_{th}$: the $V_{GS}$ at $I_D = 20$ " + MU + r"A, 250 " + MU + r"A and 1 mA (B, and A at 15 V);\quad the subthreshold slope between 10 nA and 1 " + MU + "A",
                   r"$V_{GS}$ at $I_D = 1$ " + MU + r"A $\dots$ 10 A on the 15 V curve, kept for the decks that bias the transistor there"])
    d.write()


def mos_tracer():
    d = D("mosfet-tracer", "Curve tracer", """
VGK1 gk1 0 2.2   the gate of a copy, at its step                    -> source V_GS (set)
VK1 sw dk1 0     a 0 V source from the swept node to its drain      -> ammeter I_D (measured)
MK1 dk1 gk1 0    the copy, source grounded                          -> nmos
VSW sw 0, .dc    the swept drain supply, shared by every copy       -> source V_DS (set)
Sixteen copies run in one deck (eleven universal steps, five auto); the drawing shows one.""", twin=False)
    fet(d, "mosfet"); ground(d); drain(d, node="dk"); supply(d, node="sw"); gate(d, label="$V_{GS}$", node="gk")
    d.definitions([r"$V_{GS} = 2$, 2.5, 3, 3.5, 4, 4.5, 5, 6, 8, 10 and 15 V, one copy each (the universal ladder)",
                   r"and auto: the $V_{GS}$ that gave $I_D = 10$, 30, 100, 300 mA and 1 A at 15 V in the transfer sweep, the model's own",
                   r"$V_{DS}$ swept 0 to 10 V in 20 mV steps;\quad read $I_D(V_{DS})$ for each step;\quad $r_{DS}$ as the chord at 0.1 V"])
    d.write()


def mos_rdson():
    d = D("mosfet-rdson", "On-resistance", """
BR0 0 dr0 I=exp(…V(x))   the drain current, forced by the dial, pushed into the drain   -> current source I_D (set)
DCL0 dr0 cl0, VCL0       a clamp diode from the drain node to 30 V                      -> diode + source 30 V
VGR0 gr0 0 2.5           the gate at its step                                          -> source V_GS (set)
MR0 dr0 gr0 0 DUT        the copy, source grounded                                     -> nmos
V(dr0) read: VDS                                                                       -> voltmeter V_DS (measured)
Nine copies run in one deck, one per gate step; the gate-sweep deck (the current held) is in the definitions.""", twin=False)
    fet(d, "mosfet"); ground(d); gate(d, label="$V_{GS}$", node="gr0")
    forced(d, "", "$I_D$", "D", "30", "$V_{DS}$", node="dr0")
    d.definitions([r"$I_D = 10^{k}\,\mathrm{A}$, $k = -3,\,-2.95,\,\dots,\,2$ \quad (20 points per decade, 1 mA to 100 A);\quad the clamp takes what the transistor cannot pass",
                   r"$V_{GS} = 2.5$, 3, 4, 4.5, 5, 6, 8, 10 and 15 V, one copy each;\quad read $V_{DS}$ where the clamp is off;\quad $R_{DS(on)} = V_{DS} / I_D$",
                   r"a second deck holds $I_D = 100$ mA, 1 A and 10 A (one copy each) and sweeps $V_{GS}$ 0 to 15 V in 50 mV steps"])
    d.write()


def mos_gm():
    d = D("mosfet-gm", "Transconductance and output conductance", """
VD0 d0 0 15              copy A's drain supply; its AC current is gfs            -> source V_DS (set) + ammeter I_D + i_d (measured)
VG0 g0 0 DC <vgs> AC 1   copy A's gate bias with 1 V of AC on top                 -> source V_GS + v_gs (set)
MG0 d0 g0 0 DUT          copy A, source grounded                                  -> nmos
VDO0 do0 0 DC 15 AC 1    copy B's drain supply with the AC: its current is gos    -> source V_DS + v_ds (set) + ammeter I_D + i_d (measured)
MO0 do0 go0 0 DUT        copy B, the gate held                                    -> nmos
One pair of copies per ladder current in the deck; the drawing shows one pair.""", twin=False)
    two(d, "mosfet", ("A", "B"))
    drain(d, "A", "$I_D + i_d$", node="d0"); supply(d, "A", "$V_{DS}$"); gate(d, "A", "$V_{GS} + v_{gs}$", node="g0")
    drain(d, "B", "$I_D + i_d$", node="do0"); supply(d, "B", "$V_{DS} + v_{ds}$"); gate(d, "B", "$V_{GS}$", node="go0")
    d.definitions([r"$V_{GS}$: the bias for $I_D = 1$, 3, 10, 30, 100, 300 mA, 1, 3 and 10 A (from the transfer sweep), one pair of copies each;\quad $V_{DS} = 15$ V",
                   r"A: $v_{gs} = 1$ V of AC, the simulator's unit signal, not a real amplitude;\quad $g_{fs} = i_d / v_{gs}$ at $f = 1$ kHz",
                   r"B: $v_{ds} = 1$ V of AC on the drain, the gate held;\quad $g_{os} = i_d / v_{ds}$;\quad a ladder current the model never reaches is not read"])
    d.write()


def mos_capacitance():
    d = D("mosfet-capacitance", "Capacitances", """
VDI0 di0 0 0.1, VGI0 gi0 0 DC 0 AC 1, MI0   copy A: the drain held, the gate at 0 V with AC    -> Ciss from i_g, Crss from i_d
VDO0 do0 0 DC 0.1 AC 1, MO0 do0 0 0          copy B: the drain driven with AC, gate grounded    -> Coss from i_d
.ac, C = Im(i) / (2 pi f) at 1 MHz                                                            -> the AC ammeters (measured)
Twelve voltages run as pairs of copies in one deck; the VGS deck (VDS = 0, the gate biased with AC) is copy A again.""", twin=False)
    two(d, "mosfet", ("A", "B"))
    drain(d, "A", "$i_d$", node="di0"); supply(d, "A", "$V_{DS}$"); gate(d, "A", "$0 + v$", node="gi0", ammeter="$i_g$")
    drain(d, "B", "$i_d$", node="do0"); supply(d, "B", "$V_{DS} + v$"); gate(d, "B", None, node="0")
    for n, what in (("A", "$C_{iss}$, $C_{rss}$"), ("B", "$C_{oss}$")):
        d.add(rf"\node[font=\small] at ($(Q{n}.D)+(-1.0,2.1)$) {{{what}}};")
    d.definitions([r"$V_{DS} = 0.1$, 0.5, 1, 2, 5, 10, 15, 20, 25, 30, 50 and 100 V, one pair of copies each;\quad $v = 1$ V of AC",
                   r"$C = \mathrm{Im}(i) \,/\, (2\pi f)$ at $f = 1$ MHz:\quad A: $C_{iss}$ from $i_g$, $C_{rss}$ from $i_d$;\quad B: $C_{oss}$ from $i_d$",
                   r"the $V_{GS}$ view: copy A at $V_{DS} = 0$ with the gate at 0, 1, 2 $\dots$ 10 V and the AC, a second deck"])
    d.write()


def mos_gate_charge():
    d = D("mosfet-gate-charge", "Gate charge", """
IG 0 g PULSE(…)        the gate current, 1 mA from 100 ns on                  -> current source I_G (set)
RGL g 0 1e9            a path to ground for the operating point              -> not drawn
IL vdd d 1, VDD vdd 0 30   the load current, pushed into the drain from the rail   -> current source I_L (set) + source V_DD (set)
DCL d cl, VCL cl 0 30  the clamp: the drain caught at the rail until the transistor conducts -> diode to the rail
DCLG g clG, VCLG       the gate caught at 15 V                               -> not drawn
M1 d g 0 DUT           the transistor, source grounded                       -> nmos
V(g), V(d) read                                                              -> voltmeters V_GS(t), V_DS(t) (measured)""", twin=False)
    fet(d, "mosfet"); ground(d); gate(d, label="$I_G$", node="g", kind="I")
    d.add("% the voltmeter on the gate, at the far left", r"\coordinate (gvm) at ($(g)+(-3.2,0)$);", r"\draw (gsrc) -- (gvm);",
          r"\voltmeter{gvm |- 0,\gnd}{gvm}{$V_{GS}(t)$}", r"\draw (gvm |- 0,\gnd) node[ground]{};")
    d.add("% the drain: the load current from the rail, the clamp diode to the rail, the voltmeter on the drain",
          r"\coordinate (top) at ($(Q.D)+(0,2.0)$);", r"\draw[set] (top) to[I, l={$I_L$}] (Q.D);",
          r"\coordinate (vtop) at ($(top)+(4.6,0)$);", r"\draw (top) -- (vtop);",
          r"\draw[set] (vtop) to[V, l=$V_{DD}$] (vtop |- 0,\gnd) node[ground, black]{};",
          r"\coordinate (cj) at ($(Q.D)+(0,0.3)$);", r"\coordinate (vm) at ($(cj)+(1.8,0)$);", r"\coordinate (dj) at ($(cj)+(3.0,0)$);",
          r"\draw (cj) -- (dj) to[D, l_=clamp] (dj |- top);",
          r"\voltmeter{vm |- 0,\gnd}{vm}{$V_{DS}(t)$}", r"\draw (vm |- 0,\gnd) node[ground]{};")
    d.nodename("east", r"$(Q.D)+(-0.45,0.8)$", "d"); d.nodename("south", r"$(top)+(3.6,0.05)$", "vdd")
    d.definitions([r"$I_G = 1$ mA from $t_0 = 100$ ns on (10 mA for the 10 A point);\quad $Q = I_G\,(t - t_0)$",
                   r"$I_L = 100$ mA at $V_{DD} = 10$ V, 1 A at 30 V and 10 A at 100 V, one deck each;\quad the drain sits at $V_{DD}$ until the transistor takes $I_L$",
                   r"read $V_{GS}(t)$ and $V_{DS}(t)$: $Q_{gs}$ to the plateau's start (the drain fallen 10\,\%), $Q_{gd}$ to its end (90\,\%), $Q_g$ at 4.5 and 10 V",
                   r"the gate's own clamp at 15 V (a diode to a rail) and the 1 G\ohm{} to ground are not drawn"])
    d.write()


def mos_switching():
    d = D("mosfet-switching", "Switching times and energies", """
VDD vdd 0 30, RL vdd dl 30   copy A: the supply and the resistive load             -> source V_DD (set) + resistor R_L
VS dl d 0                     a 0 V source in the drain: reads ID                   -> ammeter I_D(t) (measured)
VIN in 0 PULSE(…), RG in g 10   the gate drive through RG                           -> source V_in (set) + resistor R_G
M1 d g 0 DUT, V(d) read       the transistor; the drain voltage                     -> nmos, voltmeter V_DS(t) (measured)
IL vdd dl 1                   copy B, the inductive deck: the load current from the rail   -> current source I_L (set)
DFW dl dfw, RFW dfw vdd 0.02  the freewheeling diode to the rail, through 20 mΩ    -> diode + resistor R_FW
VIDM dl d 0, RSN d sn 10, CSN sn 0 1n   the drain ammeter and the snubber           -> ammeter I_D(t), R_SN + C_SN
Two decks drawn side by side; the inductive one with two gate pulses.""", top=8.2, twin=False)
    for n, x in (("A", 4), ("B", 12.5)):
        fet(d, "mosfet", n, x, label=n); ground(d, n)
        d.add(f"% copy {n}: the ammeter in the drain and the voltmeter on it",
              rf"\coordinate ({n}dl) at ($(Q{n}.D)+(0,1.6)$);", rf"\ammeter{{Q{n}.D}}{{{n}dl}}{{$I_D(t)$}}",
              rf"\coordinate ({n}cj) at ($(Q{n}.D)+(0,0.3)$);")
        d.nodename("east", rf"$(Q{n}.D)+(-0.1,0.3)$", "d"); d.nodename("west", rf"$({n}dl)+(0.1,0.2)$", "dl")
        d.add(f"% copy {n}: the gate resistor and the pulse source", rf"\coordinate ({n}g) at (Q{n}.G);",
              rf"\draw ({n}g) -- ++(-0.3,0) coordinate ({n}gj) to[R, l_=$R_G$] ++(-1.8,0) coordinate ({n}vin);",
              rf"\draw[set] ({n}vin) to[V, l_=$V_{{in}}$] ({n}vin |- 0,\gnd) node[ground, black]{{}};")
        d.nodename("south", rf"$({n}g)+(-0.15,0.05)$", "g"); d.nodename("south east", rf"$({n}vin)+(-0.05,0.05)$", "in")
    d.add("% copy A: the load up to the rail, the supply at the right",
          r"\draw (Adl) to[R, l_=$R_L$] ++(0,1.6) coordinate (Atop);")
    supply(d, "A", "$V_{DD}$", dx=2.6, node="vdd")
    voltmeter(d, "Acj", 1.6, "$V_{DS}(t)$", "Avm")
    d.add("% copy B: the load current from the rail, the freewheeling diode and its resistor beside it",
          r"\coordinate (Btop) at ($(Bdl)+(0,2.0)$);", r"\draw[set] (Btop) to[I, l_={$I_L$}] (Bdl);",
          r"\draw (Bdl) -- ++(1.6,0) coordinate (Bfw) to[D, l=$D_{FW}$] ++(0,1.0) to[R, l=$R_{FW}$] (Bfw |- Btop);")
    supply(d, "B", "$V_{DD}$", dx=4.0, node="vdd")
    d.nodename("west", r"$(Bfw)+(0.1,1.1)$", "dfw")
    d.add("% copy B: the snubber on the drain",
          r"\draw (Bcj) -- ++(1.4,0) coordinate (Bsn) to[R, l=$R_{SN}$] ++(0,-0.9) to[C, l=$C_{SN}$] (Bsn |- 0,\gnd) node[ground]{};")
    d.nodename("east", r"$(Bsn)+(-0.1,-0.75)$", "sn")
    voltmeter(d, "Bsn", 1.6, "$V_{DS}(t)$", "Bvm")
    d.definitions([r"A: $V_{DD} = 30$ V;\quad $R_L = V_{DD} / I_D$;\quad $I_D = 100$ mA, 1 A and 10 A, one deck each;\quad $R_G = 10$ \ohm{} (at 1 A also 25 \ohm)",
                   r"$V_{in}$: 0 V, then 10 V (at 1 A also 4.5 V) from 100 ns for 2 " + MU + r"s, then 0 V;\quad 2 ns edges",
                   r"read $I_D(t)$ and $V_{DS}(t)$: $t_{d(on)}$, $t_r$, $t_{d(off)}$, $t_f$ between the 10\,\% and 90\,\% levels",
                   r"B: $I_L = 1$ A and 10 A;\quad $R_{FW} = 20$ m\ohm;\quad $R_{SN} = 10$ \ohm, $C_{SN} = 1$ nF;\quad two 5 " + MU + r"s pulses, 20 ns edges;\quad $E_{on}$, $E_{off}$ as $\int V_{DS} I_D\,dt$ over 300 ns windows at the second pulse's edges"],
                  y=-0.1)
    d.write()


def mos_body_diode():
    d = D("mosfet-body-diode", "Body diode", """
BS0 0 s0 I=exp(…V(x))     copy A: the source current, forced by the dial, pushed into the source  -> current source I_S (set)
DCLs0 s0 cls0, VCLs0      a clamp diode from the source node to 5 V                              -> diode + source 5 V
VG0 g0 s0 0               the gate at the source: VGS = 0 (4.5 and 10 V in the next copies)      -> source V_GS (set)
MD0 0 g0 s0 DUT           the transistor, drain grounded                                          -> nmos drawn upside down
V(s0) read: VSD                                                                                   -> voltmeter V_SD (measured)
IF 0 s PULSE(1 -1 …)      copy B, the recovery deck: IF, then -IF at 100 A/µs, into the source    -> current source I_F(t) (set)
VDM d 0 0, MR d s s DUT   the drain read through a 0 V source; the gate tied to the source        -> ammeter I_D(t) (measured)
DCLP 0 s DCLMP            a clamp from ground to the source node                                  -> diode""", twin=False)
    for n, x in (("A", 4), ("B", 12.5)):
        fet(d, "mosfet", n, x, label=n + r"\\upside down", flip="yscale=-1")
        ground(d, n, "D") if n == "A" else None
    forced(d, "A", "$I_S$", "S", "5", "$V_{SD}$", node="s0")
    d.add("% copy A's gate: a source from the gate up to the source node",
          r"\coordinate (Ag) at (QA.G);", r"\coordinate (Agsrc) at ($(Ag)+(-1.4,0)$);", r"\draw (Ag) -- (Agsrc);",
          r"\draw[set] (Agsrc) to[V, l={$V_{GS}$}] (Agsrc |- Acj) -- (Acj);")
    d.nodename("south", r"$(Ag)+(-0.45,0.02)$", "g0")
    d.add("% copy B: the drain read through an ammeter to ground, the gate tied to the source node",
          r"\coordinate (Bbot) at ($(QB.D)+(0,-1.5)$);", r"\ammeter{Bbot}{QB.D}{$I_D(t)$}", r"\draw (Bbot) node[ground]{};",
          r"\coordinate (Bg) at (QB.G);", r"\coordinate (Bcj) at ($(QB.S)+(0,0.3)$);", r"\draw (Bg) -- ++(-0.8,0) |- (Bcj);",
          r"\coordinate (Btop) at ($(QB.S)+(0,2.0)$);", r"\draw[set] (Btop) to[I, l={$I_F(t)$}] (QB.S);",
          r"\coordinate (Brail) at ($(Btop)+(3.6,0)$);", r"\draw (Btop) -- (Brail) -- (Brail |- 0,\gnd) node[ground]{};",
          r"\coordinate (Bdj) at ($(Bcj)+(2.6,0)$);", r"\draw (Bcj) -- (Bdj);",
          r"\draw (Bdj |- 0,\gnd) node[ground]{} to[D, l_=clamp] (Bdj);")
    d.nodename("west", r"$(QB.D)+(0.1,-0.3)$", "d"); d.nodename("east", r"$(QB.S)+(-0.45,0.8)$", "s")
    d.nodename("west", r"$(Bbot)+(0.3,0.1)$", "0")
    d.definitions([r"A: $I_S = 10^{k}\,\mathrm{A}$, $k = -6,\,-5.95,\,\dots,\,2$ \quad (20 points per decade, 1 " + MU + r"A to 100 A);\quad the clamp takes what a card without a diode cannot pass",
                   r"$V_{GS} = 0$, 4.5 and 10 V, one copy each;\quad read $V_{SD}$ at each ladder current;\quad the diode's $I_S$ and $n$ fitted between 1 mA and 100 mA at $V_{GS} = 0$",
                   r"B: $I_F = 1$ A and 10 A, held 2 " + MU + r"s, then ramped to $-I_F$ at 100 A/" + MU + r"s;\quad the clamp takes the current once the diode has recovered",
                   r"read $I_D(t)$: $I_{rrm}$, $t_{rr}$ (zero crossing to 10\,\% of $I_{rrm}$), $Q_{rr}$, softness"])
    d.write()


def mos_temperature():
    d = D("mosfet-temperature", "Temperature", """
VT dt 0 15, MT dt g 0     copy A: the 15 V copy of the transfer deck                -> source V_DS (set) + ammeter I_D (measured)
VTD dtd g 0, MTD dtd g 0  copy B: the diode-connected copy                           -> ammeter in the drain-gate loop
VL dl 0 0.1, ML dl g 0    copy C: the 0.1 V copy, whose current gives RDS(on)        -> source 0.1 V + ammeter
VGS g 0, .dc              the gate drive, shared                                     -> source V_GS (set)
.temp -55 / 25 / 100 / 125 / 150 / 175                                               -> the thermometer (set)""", twin=False)
    for n, x in (("A", 4), ("B", 10.6), ("C", 16.2)):
        fet(d, "mosfet", n, x, label=n); ground(d, n)
    drain(d, "A", node="dt"); supply(d, "A", "$V_{DS}$"); gate(d, "A", "$V_{GS}$", node="g")
    drain(d, "B", node="dtd")
    d.add("% copy B: the ammeter looped back to the gate", r"\coordinate (Bg) at (QB.G);",
          r"\coordinate (Bgsrc) at ($(Bg)+(-1.4,0)$);", r"\draw (Btop) -| (Bgsrc) -- (Bg);",
          r"\draw[set] (Bgsrc) to[V, l_={$V_{GS}$}] (Bgsrc |- 0,\gnd) node[ground, black]{};")
    d.nodename("south", r"$(Bg)+(-0.45,0.02)$", "g")
    drain(d, "C", node="dl"); supply(d, "C", "$0.1$ V", dx=2.2); gate(d, "C", "$V_{GS}$", node="g", dx=-1.2)
    d.thermometer(at=r"$(Cvtop)+(1.6,-2.6)$")
    d.definitions([r"$V_{GS}$ swept $-2$ V to $+15$ V in 10 mV steps, every gate on the one source;\quad $T = -55$, 25, 100, 125, 150 and 175 " + DEG + r"C, one deck each",
                   r"A: $V_{DS} = 15$ V, $g_{fs}$ at 1 A and the zero-TC point (where the 25 and 150 " + DEG + r"C curves cross);\quad B: $V_{th}$ at 1 mA, diode-connected",
                   r"C: $V_{DS} = 0.1$ V;\quad $R_{DS(on)} = 0.1\ \mathrm{V} / I_D$ at $V_{GS} = 10$ V and 4.5 V, each over its 25 " + DEG + r"C value"])
    d.write()


def mos_noise():
    fet_noise("mosfet-noise", "mosfet", JFET_NOISE.replace("J1 d g 0", "M1 d g 0").replace("-> njfet", "-> nmos"),
              [r"$V_{GS}$: the bias for $I_D = 1$, 10, 100 mA and 1 A (from the transfer sweep), one deck each;\quad $V_D = 10$ V",
               r"$f = 1$ Hz to 1 MHz, 20 points per decade;\quad $R_G = 0$ gives $e_n$ and its $1/f$ corner",
               r"$R_G = 1$ k\ohm{} at 100 mA gives NF;\quad read $i_d$, the noise part of the drain current, referred to $v_{in}$"])


def mos_breakdown():
    d = D("mosfet-breakdown", "Breakdown and leakage", """
VA sw da 0, MA da 0 0    copy A: the drain driven from the swept node, gate grounded   -> ammeter I (measured), source V_DS (set)
VB sw gb 0, MB 0 gb 0    copy B: the gate driven, drain grounded                       -> ammeter I, source V_GS
VSW sw 0, .dc            the swept node                                                -> the swept source
Two decks drawn as one.""", twin=False)
    fet(d, "mosfet", "A", 4, label="A"); ground(d, "A"); fet(d, "mosfet", "B", 12.5, label="B"); ground(d, "B")
    drain(d, "A", "$I$", node="da"); supply(d, "A", "$V_{DS}$", node="sw"); gate(d, "A", None, node="0")
    drain_ground(d, "B"); gate(d, "B", "$V_{GS}$", node="gb", ammeter="$I$")
    d.definitions([r"A: $V_{DS}$ swept 0 to 1000 V in 1 V steps, the gate at the source;\quad B: $V_{GS}$ swept $-30$ to $+30$ V in 0.1 V steps, the drain at the source",
                   r"read $I$: $V_{(BR)DSS}$ and $V_{(BR)GSS}$ where $I$ passes 1 mA, else absent;\quad $I_{DSS}$ at 25, 100 and 300 V;\quad $I_{GSS}$ at $\pm 20$ V"])
    d.write()


def mos_distortion():
    d = D("mosfet-distortion", "Distortion", """
VDD vdd 0 20, RL vdd d 1000       copy A: the supply and the drain load                     -> source V_DD (set) + resistor R_L
RS s sx 100, CS sx 0 1000u        the source resistor to a node held at AC ground            -> resistor R_S + capacitor C_S
IS sx vss 0.01, VSS vss 0 -10     the sink to the negative rail                              -> current source I_S (set) + source V_SS (set)
RIN in g 1000, VIN in 0 SIN(…)    the 1 kHz sine through 1 kΩ                                -> resistor R_in + source v_in (set)
M1 d g s DUT, V(d) read           the common-source stage; its output                       -> nmos, voltmeter v_out (measured)
M1 vdd g s, IS s vss 0.1, CL s l 1000u, RL l 0 100   copy B, the follower deck: the drain on the rail, the load AC-coupled   -> voltmeter v_out on the load
The follower is a second deck; the gain-finding probe run is not drawn.""", top=7.8, gnd=2.0, twin=False)
    stage(d, "A", "mosfet", 4, "$R_L$", "$R_S$", "$R_{in}$", "$V_{DD}$", "D", bypass="$C_S$", sink="$I_S$", node_s="s", label="A")
    d.nodename("south west", r"$(Ax)+(0.1,0.05)$", "sx")
    stage(d, "B", "mosfet", 14.5, None, None, "$R_{in}$", "$V_{DD}$", "S", sink="$I_S$", load=("$C_L$", "$R_L$"), node_s="s", label="B")
    d.definitions([r"A: $V_{DD} = 20$ V;\quad $I_S = 10$ mA to $V_{SS} = -10$ V;\quad $R_S = 100$ \ohm, bypassed by $C_S = 1000$ " + MU + r"F;\quad $R_L = 1$ k\ohm;\quad $R_{in} = 1$ k\ohm;\quad $f = 1$ kHz",
                   r"B: $V_{DD} = 25$ V;\quad $I_S = 100$ mA;\quad $R_L = 100$ \ohm{} through $C_L = 1000$ " + MU + r"F;\quad $R_{in} = 100$ \ohm{} at 1 and 20 kHz, and 1 k\ohm{} at 20 kHz",
                   r"$v_{in}$ = sine, its level set by a 20 mV probe run for 1 V peak at the output",
                   r"read $v_{out}$ over the last four of ten cycles: THD, HD2, HD3 by Goertzel"], y=-2.4)
    d.write()


def main():
    for f in (jfet_runs, jfet_transfer, jfet_tracer, jfet_gm, jfet_ohmic, jfet_gate, jfet_capacitance, jfet_frequency,
              jfet_noise, jfet_temperature, jfet_switch, jfet_distortion, jfet_breakdown,
              mos_runs, mos_transfer, mos_tracer, mos_rdson, mos_gm, mos_capacitance, mos_gate_charge, mos_switching,
              mos_body_diode, mos_temperature, mos_noise, mos_breakdown, mos_distortion):
        f()
    print("13 JFET and 13 MOSFET drawings written")
