"""The tube bench drawings, with the blocks of benches.py (which runs this): the tube at (4,3) anode up, its
cathode at y = 1.6 and to ground (or to its cathode resistor), the anode ammeter up to the rail and the anode
supply to the right; the control grid's source at the left, through an ammeter where the deck reads the grid
current; a pentode's screen out to the right, through its ammeter to its own supply under the anode's. A
second or third copy sits at x = 11 and x = 18. Blue is what the bench sets, red what it measures (a circled A
reads a current, a circled V a voltage), green the deck's node names. Every drawing is the set-up a person would
wire, semantically the deck's: a 0 V source is an ammeter, an ideal bypass (the cathode or screen held at the
value the iteration finds) is drawn as the source it is, an ideal output transformer as a transformer, and the
copies a deck packs are one circuit with the list of its conditions. The model's own pin order is put in by
the job builder; the drawing shows anode, screen, grid and cathode."""
from benches import D
from benches_fet import voltmeter

MU = r"\textmu "
VA_LADDER = r"12, 25, 50, 90, 100, 150, 180, 200, 250, 300, 350, 400, 450, 500 V"
VG2_LADDER = r"50, 100, 150, 175, 200, 225, 250, 300, 350, 400, 450 V"
GRID_LADDER = (r"$V_{g1} = 0$ to $-10$ V in 0.25 V steps, to $-30$ V in 0.5 V, to $-60$ V in 1 V, to $-150$ V in 2.5 V, "
               r"to $-300$ V in 5 V, one copy each:\\[2pt]\quad every family a sheet prints is a subset of these copies")
PENTODE_NOTE = r"the suppressor at the cathode in every deck (most models have no suppressor pin); the beam tetrodes' beam plates the same"


# ------------------------------------------------------------------------ the blocks, for the copy named n
def tube(d, kind, n="", x=4, y=3.0, label="DUT", mirror=False):
    """a triode, a pentode or a vacuum diode, anode up; circuitikz draws every grid of a pentode on its left, the
    control grid lowest, then the screen, then the suppressor, left unwired: it is at the cathode in every deck
    (most models have no suppressor pin), and the definitions say so"""
    sym, scale = {"triode": ("triode", 1.35), "pentode": ("pentode", 1.6), "diode": ("diodetube", 1.35)}[kind]
    d.add(f"% the {kind}" + (", mirrored (its grids on the right)" if mirror else ""),
          rf"\node[{sym}, scale={scale}{', xscale=-1' if mirror else ''}] (T{n}) at ({x},{y}) {{}};",
          rf"\node[anchor=west, font=\small, align=left] at ($(T{n}.anode)!0.62!(T{n}.cathode)+({0.95 if kind == 'pentode' else 0.75},0)$) {{{label}}};")


def cathode_ground(d, n=""):
    d.add("% the cathode to ground", rf"\draw (T{n}.cathode) -- (T{n}.cathode |- 0,\gnd) node[ground]{{}};")
    d.nodename("west", rf"$(T{n}.cathode)+(0.1,-0.35)$", "0")


def anode(d, n="", label="$I_a$", node=None, up=1.6):
    """an ammeter from the anode straight up to ({n}top), the rail's end"""
    d.add("% the ammeter in the anode, up to the rail", rf"\coordinate ({n}top) at ($(T{n}.anode)+(0,{up})$);",
          rf"\ammeter{{T{n}.anode}}{{{n}top}}{{{label}}}")
    if node:
        d.nodename("west", rf"$(T{n}.anode)+(0.1,0.25)$", node)


def supply(d, n="", label="$V_a$", dx=2.6, node=None, frm=None):
    """the rail from ({n}top) to the right, then a voltage source down to ground, + up"""
    frm = frm or f"{n}top"
    d.add("% the anode supply at the right, + up, - to ground", rf"\coordinate ({n}vtop) at ($({frm})+({dx},0)$);",
          rf"\draw ({frm}) -- ({n}vtop);",
          rf"\draw[set] ({n}vtop) to[V, l={{{label}}}] ({n}vtop |- 0,\gnd) node[ground, black]{{}};")
    if node:
        d.nodename("south", rf"$({frm})+({dx / 2},0.05)$", node)


def screen(d, n="", label="$V_{g2}$", ammeter="$I_{g2}$", node=None, resistor=None, left=6.4, rise=1.25):
    """the screen: out to the left and up, clear of the grid's circuit, then along to the far left, through its
    resistor and ammeter, and down through its own supply to ground"""
    d.add("% the screen, out to the left above the grid's circuit, to its own supply",
          rf"\draw (T{n}.screen) -- ++(-0.3,0) -- ++(0,{rise}) -- ++(-0.8,0) coordinate ({n}s);",
          rf"\coordinate ({n}send) at ($(T{n}.anode |- {n}s)+(-{left},0)$);")
    at = f"{n}s"
    if resistor:
        d.add(rf"\draw ({at}) to[R, l_={{{resistor}}}] ++(-1.8,0) coordinate ({n}sr);")
        at = f"{n}sr"
    if ammeter:
        d.add(rf"\coordinate ({n}sam) at ($({at})+(-1.6,0)$);", rf"\ammeterh{{{n}sam}}{{{at}}}{{{ammeter}}}")
        at = f"{n}sam"
    d.add(rf"\draw ({at}) -- ({n}send);")
    if label:
        d.add(rf"\draw[set] ({n}send) to[V, l_={{{label}}}] ({n}send |- 0,\gnd) node[ground, black]{{}};")
    if node:
        d.nodename("south", rf"$({n}s)+(-0.35,0.05)$", node)


def screen_strapped(d, n="", via=None):
    """a pentode strapped as a triode: the screen up to the anode (through 100 Ω where the sheet says so)"""
    d.add("% the screen strapped to the anode", rf"\draw (T{n}.screen) -- ++(-0.3,0) -- ++(0,1.25) coordinate ({n}sx);")
    if via:
        d.add(rf"\draw ({n}sx) to[R, l={{{via}}}] ({n}sx -| T{n}.anode);")
    else:
        d.add(rf"\draw ({n}sx) -- ({n}sx -| T{n}.anode);")
    d.add(rf"\fill ({n}sx -| T{n}.anode) circle (0.05);")


def grid(d, n="", label="$V_{g1}$", node="g", dx=-1.4, ammeter=None):
    """the control grid: a source from ground up into the grid wire, through an ammeter when Ig is read"""
    d.gate(label, node, dx, "V", ammeter, terminal=f"T{n}.control", name=f"{n}g")


def two(d, kind, labels, xs=(4, 11)):
    for n, x, label in zip(("A", "B", "C"), xs, labels):
        tube(d, kind, n, x, label=label)
        cathode_ground(d, n)


# ------------------------------------------------------------------------ the shared drawings
def tube_runs():
    d = D("tube-runs", "Does the model load", """
VA0 a0 0 250, VG10 g10 0 0, XT0 a0 g10 0 DUT         copy A, a triode at 250 V and 0 V   -> sources V_a, V_g1 (set), ammeters I_a, I_g (measured)
VA0 a0 0 250, VG20 g20 0 250, VG10 g10 0 0, XT0 …    copy B, a pentode, the screen at 250 V -> source V_g2 (set), ammeter I_g2 (measured)
VA0 a0 0 10, XT0 a0 0 DUT                            copy C, a diode at 10 V               -> source V_a (set), ammeter I_a (measured)
.op, in each dialect of the engine in turn; the parameters a caller passes are declared on the .SUBCKT line when needed""",
          top=7.4, twin=False)
    tube(d, "triode", "A", 4, label="A"); cathode_ground(d, "A")
    anode(d, "A", node="a0"); supply(d, "A", dx=2.0); grid(d, "A", node="g10", ammeter="$I_g$", dx=-1.0)
    tube(d, "pentode", "B", 14, label="B"); cathode_ground(d, "B")
    anode(d, "B", node="a0"); supply(d, "B", dx=2.0); grid(d, "B", node="g10", dx=-1.0); screen(d, "B", node="g20", left=5.4)
    tube(d, "diode", "C", 20.4, label="C"); cathode_ground(d, "C"); anode(d, "C", node="a0"); supply(d, "C", dx=1.8)
    d.definitions([r"A: $V_a = 100$ and 250 V, $V_{g1} = 0$, $-2$ and $-10$ V;\quad B: $V_a = 100$ and 250 V, $V_{g2} = 250$ V, $V_{g1} = 0$ and $-10$ V;\quad C: $V_a = 10$ and 50 V",
                   r"one operating point in ngspice as it comes, then with its PSpice (psa), LTspice (lta) and both (ltpsa) compatibilities, then again with the undeclared parameters declared",
                   r"read the first dialect that settles, and $I_a$, $I_{g2}$, $I_g$ there: the model's own scale ($I_a$ at 250 V and 0 V) sets which ladder steps are shown first"])
    d.write()


def tube_capacitance():
    d = D("tube-capacitance", "Interelectrode capacitances", """
VG1g g1g 0 DC <vg> AC 1, VAg ag 0 250, VKg kg 0 0, XCg …   copy A: the grid driven, every other electrode at AC ground through its ammeter
VAa aa 0 DC 250 AC 1, …, XCa …                              copy B: the anode driven
(pentode) VG2s g2s 0 DC 250 AC 1, …, XCs …                  copy C: the screen driven
.ac at 1 MHz; C between two electrodes = Im(i) / (2 pi f) of the current into the undriven one""", top=8.0, twin=False)
    for n, x, what, drv in (("A", 4, "grid driven", "g"), ("B", 13.4, "anode driven", "a"), ("C", 22.8, "screen driven", "s")):
        tube(d, "pentode", n, x, label=n)
        d.add(rf"\node[font=\small] at ($(T{n}.anode)+(-1.0,1.9)$) {{{what}}};")
        d.add(f"% copy {n}: the cathode through its ammeter to ground", rf"\coordinate ({n}kb) at ($(T{n}.cathode)+(0,-1.4)$);",
              rf"\ammeter{{{n}kb}}{{T{n}.cathode}}{{$i_k$}}", rf"\draw ({n}kb) -- ({n}kb |- 0,\gnd) node[ground]{{}};")
        anode(d, n, "$i_a$" if drv != "a" else "$i$", up=1.5)
        supply(d, n, "$V_a$" if drv != "a" else "$V_a + v$", dx=2.6)
        grid(d, n, "$V_{g1}$" if drv != "g" else "$V_{g1} + v$", node=None, ammeter="$i_g$" if drv != "g" else "$i$", dx=-0.9)
        screen(d, n, "$V_{g2}$" if drv != "s" else "$V_{g2} + v$", ammeter="$i_{g2}$" if drv != "s" else "$i$", left=5.0)
    d.definitions([r"$V_a = 250$ V, $V_{g2} = 250$ V, $V_{g1}$ at the model's cut-off (the tube cold, as the sheets measure it), and again at $I_a = I_0/4$ (hot);\quad $v = 1$ V of AC at $f = 1$ MHz",
                   r"$C = \mathrm{Im}(i)/(2\pi f)$ of each undriven electrode's current: $C_{g1k}$, $C_{g1a}$, $C_{ak}$, $C_{g1g2}$, $C_{g2k}$, $C_{ag2}$;\quad a triode is copies A and B without the screen",
                   r"the sheets' input and output capacitances: $C_{in} = C_{g1k} + C_{g1g2}$ (+ $C_{g1a}$ with the anode at AC ground), $C_{out} = C_{ak} + C_{ag2}$;\quad the Miller input $C_{g1k} + (1 + A)\,C_{g1a}$ at the gain $A$ of the RC chart's cells"])
    d.write()


# ------------------------------------------------------------------------ the triode drawings
def triode_anode():
    d = D("triode-anode", "Anode characteristics", """
VAk sw ak 0       a 0 V source from the swept node to the anode of copy k   -> ammeter I_a (measured)
VGk gk 0 <vg>     the grid of copy k, held                                  -> source V_g1 (set), ammeter I_g (measured)
XTk ak gk 0 DUT   copy k, cathode grounded                                  -> triode
VSW sw 0, .dc     the swept anode supply, shared by every copy              -> source V_a (set)
The nine copies (one per step of the model's own family) are drawn as one triode with a stepped grid.""", twin=False)
    tube(d, "triode"); cathode_ground(d); anode(d, node="ak"); supply(d, node="sw"); grid(d, node="gk", ammeter="$I_g$")
    d.definitions([r"$V_{g1} = -k \cdot$ step, $k = 0, \dots, 8$: nine traces, one copy each;\quad the step the model's own, its cut-off at 250 V ($I_a = 10$ " + MU + r"A) over 8, on the 1-2-2.5-5 series (0.5 V for a 12AX7)",
                   r"$V_a$ swept 0 to 600 V in 1 V steps;\quad read $I_a(V_a)$ per trace, drawn up to where $V_a I_a$ passes $250\ \mathrm{V} \times I_0$, the model's own zero-bias power",
                   r"the whole ladder (0 to $-300$ V, and the positive-grid traces) is the specification's; the catalogue runs the model's own family"])
    d.write()


def triode_positive_grid():
    d = D("triode-positive-grid", "Positive-grid characteristics", """
VAk sw ak 0, VGk gk 0 <+vg>, XTk ak gk 0 DUT   a copy per positive grid voltage   -> source V_g1 (set), ammeters I_a and I_g (measured)
VSW sw 0, .dc                                    the swept anode supply             -> source V_a (set)
Ten copies drawn as one.""", twin=False)
    tube(d, "triode"); cathode_ground(d); anode(d, node="ak"); supply(d, node="sw"); grid(d, "", "$+V_{g1}$", node="gk", ammeter="$I_g$")
    d.definitions([r"$V_{g1} = 0$, +0.5, 1, 2, 5, 10, 15, 20, 30, 40, 50 V;\quad $V_a$ swept 0 to 600 V in 1 V steps (0.1 V below 50 V)",
                   r"read $I_a$ and $I_g$ against $V_a$: the grid's share of the cathode current $I_g/(I_a + I_g)$, largest where $V_a$ is low (class A2 and AB2, the 300B, 2A3 and 6C33C sheets)"])
    d.write()


def triode_transfer():
    d = D("triode-transfer", "Transfer characteristics and cut-off", """
VAk ak 0 <va>        the anode of copy k, held; its current is Ia              -> source V_a (set) + ammeter I_a (measured)
VGKk g gk 0          a 0 V source from the grid drive into the grid of copy k  -> ammeter I_g (measured)
XTk ak gk 0 DUT      copy k, cathode grounded                                  -> triode
VG g 0, .dc          the grid drive, swept, shared by every copy               -> source V_g1 (set)
Six copies, one per anode voltage; the drawing shows one.""", twin=False)
    tube(d, "triode"); cathode_ground(d); anode(d, node="ak"); supply(d); grid(d, node="g", ammeter="$I_g$")
    d.definitions([r"$V_{g1}$ swept $-300$ V to $+5$ V in 20 mV steps;\quad $V_a = 100$, 150, 200, 250, 300 and 400 V, one copy each",
                   r"read $I_a(V_{g1})$;\quad cut-off: $V_{g1}$ at $I_a = 10$ " + MU + r"A (the GE, RCA and Sylvania condition);\quad $I_a$ at $V_{g1} = 0$",
                   r"a model whose equations fail before $-300$ V is swept from the deepest start it can be evaluated at, which is published"])
    d.write()


def triode_params():
    d = D("triode-params", "Amplification factor, transconductance, anode resistance", """
VAg0 ag0 0 <va>, VGg0 gg0 0 DC <vg> AC 1, XTg0 ag0 gg0 0   copy A: AC on the grid, the anode held   -> gm = i_a / v_g
VAa0 aa0 0 DC <va> AC 1, VGa0 ga0 0 <vg>, XTa0 aa0 ga0 0   copy B: AC on the anode, the grid held   -> 1/ra = i_a / v_a
.ac lin 1 1k 1k; mu = gm ra
One pair per (Va, Ia) of the ladders, the grid voltage for each from the transfer sweep.""", twin=False)
    two(d, "triode", ("A", "B"))
    anode(d, "A", "$I_a + i_a$", node="ag0"); supply(d, "A", "$V_a$"); grid(d, "A", "$V_{g1} + v_g$", node="gg0")
    anode(d, "B", "$I_a + i_a$", node="aa0"); supply(d, "B", "$V_a + v_a$"); grid(d, "B", "$V_{g1}$", node="ga0")
    d.definitions([r"$V_a = 100$, 250 and 400 V;\quad $I_a = 10$ " + MU + r"A to 1 A on a 1-2-5 series;\quad $V_{g1}$ for each from the transfer sweep, a current not reached below zero bias left out",
                   r"A: $g_m = i_a / v_g$;\quad B: $r_a = v_a / i_a$;\quad $\mu = g_m r_a$, at $f = 1$ kHz, $v = 1$ V of AC (the simulator's unit signal)"])
    d.write()


def triode_grid_current():
    d = D("triode-grid-current", "Grid current: onset, contact potential and input resistance", """
VAk ak 0 <va>, VGKk g gk 0, XTk ak gk 0 DUT   copy k at its anode voltage; the grid's current through the 0 V source -> ammeter I_g (measured)
VG g 0, .dc                                   the grid drive, swept through zero                                    -> source V_g1 (set)""",
          twin=False)
    tube(d, "triode"); cathode_ground(d); anode(d, node="ak"); supply(d); grid(d, node="g", ammeter="$I_g$")
    d.definitions([r"$V_{g1}$ swept $-5$ V to $+5$ V in 20 mV steps (the transfer sweep's grid ammeters);\quad $V_a = 100$, 250 and 400 V",
                   r"read $I_g(V_{g1})$: the onset $V_{g1}$ at $I_g = +0.3$ " + MU + r"A (Mullard's and Philips's condition) and 1 " + MU + r"A;\quad $I_g$ at $-0.5$, 0, +1, +5 V",
                   r"the input resistance $dV_{g1}/dI_g$ at +1 V;\quad no grid current up to +1 V: `absent'"])
    d.write()


def stage(d, n, x, kind, rp="$R_p$", rk="$R_k$", ideal=True, cc="$C_c$", rs="$R_s$", rg1="$R_{g1}$", rsrc=None,
          cl=None, vb="$E_{bb}$", rg2=None, vout="$v_{out}$", label="DUT", src="$v_{in}$", node_a="a", bypass=None, y=3.8):
    """a resistance-coupled stage: Ebb through Rp to the anode, the cathode on its bias (an ideal bypass: the source
    the iteration sets to Rk times the mean current under signal; or Rk with its bypass capacitor), the output
    through Cc into the next grid's Rs (and CL); the input from a source (through Rsrc) with the stage's own grid
    resistor Rg1 to ground; a pentode's screen through Rg2 from Ebb, ideally decoupled."""
    tube(d, kind, n, x, y=y, label=label)
    t = f"T{n}"
    d.add(f"% copy {n}: the anode resistor up to the rail, the anode ammeter under it",
          rf"\coordinate ({n}am) at ($({t}.anode)+(0,1.1)$);", rf"\ammeter{{{t}.anode}}{{{n}am}}{{$I_a$}}",
          rf"\draw ({n}am) to[R, l_={{{rp}}}] ++(0,1.6) coordinate ({n}top);")
    d.add(rf"\coordinate ({n}vtop) at ($({n}top)+(6.6,0)$);", rf"\draw ({n}top) -- ({n}vtop);",
          rf"\draw[set] ({n}vtop) to[V, l={{{vb}}}] ({n}vtop |- 0,\gnd) node[ground, black]{{}};")
    d.nodename("south", rf"$({n}top)+(1.0,0.05)$", "bb")
    d.nodename("east", rf"$({n}am)+(-0.15,0.15)$", node_a)
    if ideal:
        d.add("% the cathode on an ideal bypass: a source set to Rk times the mean current",
              rf"\draw[set] ({t}.cathode) to[V, l={{{rk}\,$\bar I_k$}}] ({t}.cathode |- 0,\gnd) node[ground, black]{{}};")
    else:
        d.add("% the cathode resistor, and its bypass", rf"\draw ({t}.cathode) to[R, l={{{rk}}}] ({t}.cathode |- 0,\gnd) node[ground]{{}};")
        if bypass:
            d.add(rf"\draw ({t}.cathode) -- ++(1.2,0) coordinate ({n}ck) to[C, l={{{bypass}}}] ({n}ck |- 0,\gnd) node[ground]{{}};")
    d.nodename("east", rf"$({t}.cathode)+(-0.1,-0.25)$", "k")
    d.add("% the grid: its resistor to ground and the source", rf"\coordinate ({n}g) at ({t}.control);",
          rf"\draw ({n}g) -- ++(-0.6,0) coordinate ({n}gj);",
          rf"\draw ({n}gj) to[R, l_={{{rg1}}}] ({n}gj |- 0,\gnd) node[ground]{{}};")
    if isinstance(rsrc, (list, tuple)):     # a chain of parts from the grid back to the source, e.g. the stopper and Cin
        d.add(rf"\draw ({n}gj) -- ++(-0.3,0) coordinate ({n}c0);")
        for i, (part, lab) in enumerate(rsrc):
            d.add(rf"\draw ({n}c{i}) to[{part}, l_={{{lab}}}] ++(-1.6,0) coordinate ({n}c{i + 1});")
        d.add(rf"\coordinate ({n}vin) at ({n}c{len(rsrc)});")
    elif rsrc:
        d.add(rf"\draw ({n}gj) -- ++(-0.3,0) to[R, l_={{{rsrc}}}] ++(-1.8,0) coordinate ({n}vin);")
    else:
        d.add(rf"\draw ({n}gj) -- ++(-1.4,0) coordinate ({n}vin);")
    d.add(rf"\draw[set] ({n}vin) to[V, l_={{{src}}}] ({n}vin |- 0,\gnd) node[ground, black]{{}};")
    d.nodename("south", rf"$({n}g)+(-0.2,0.05)$", "g"); d.nodename("south east", rf"$({n}vin)+(-0.05,0.05)$", "in")
    if kind == "pentode":
        d.add("% the screen: up and to the left, through Rg2 from the rail (carried over to it), decoupled by Cg2",
              rf"\draw ({t}.screen) -- ++(-0.3,0) -- ++(0,1.25) coordinate ({n}s1);",
              rf"\coordinate ({n}sc) at ($({t}.anode |- {n}s1)+(-4.4,0)$);", rf"\draw ({n}s1) -- ({n}sc);",
              rf"\draw ({n}sc) to[R, l={{{rg2}}}] ({n}sc |- {n}top) -- ({n}top);",
              rf"\draw ({n}sc) -- ++(-1.3,0) coordinate ({n}cs) to[C, l_={{$C_{{g2}}$}}] ({n}cs |- 0,\gnd) node[ground]{{}};")
        d.nodename("south", rf"$({n}s1)+(-0.6,0.05)$", "s")
    d.add("% the output: through Cc into the next grid's resistor", rf"\coordinate ({n}oj) at ($({n}am)+(0,0.0)$);",
          rf"\draw ({n}am) -- ++(1.6,0) to[C, l={{{cc}}}] ++(1.4,0) coordinate ({n}o);",
          rf"\draw ({n}o) to[R, l_={{{rs}}}] ({n}o |- 0,\gnd) node[ground]{{}};")
    d.nodename("south", rf"$({n}o)+(0.3,0.05)$", "o")
    last = f"{n}o"
    if cl:
        d.add(rf"\draw ({n}o) -- ++(1.1,0) coordinate ({n}cl) to[C, l={{{cl}}}] ({n}cl |- 0,\gnd) node[ground]{{}};")
        last = f"{n}cl"
    if vout:
        voltmeter(d, last, 1.2, vout, f"{n}vo")


RC_HEADER = """
VBBi bbi 0 <ebb>, RPi bbi ami <rp>, VAMi ami ai 0   the supply, the plate resistor, the anode ammeter   -> source E_bb (set), resistor R_p, ammeter I_a (measured)
VKi ki 0 <vk>                                       the cathode on an ideal bypass: Rk times the mean cathode current, iterated -> source (set)
VINi ini 0 SIN(0 <drive> 1k), RG1i ini 0 <rg1>, VGMi ini gi 0   the drive, the grid resistor, the grid ammeter -> source v_in (set)
CCi ami oi 10u, RSi oi 0 <rs>                       the coupling capacitor and the next grid's resistor  -> voltmeter v_out (measured)
XTi ai gi ki DUT; .tran 30 periods, the last ten read; a quiescent .op with the real Rk starts the iteration
Fifteen copies, one per drive level (half-octave steps from the drive that gives 2 V rms out), drawn as one."""


def triode_rc():
    d = D("triode-rc-amplifier", "The resistance-coupled amplifier chart", RC_HEADER, top=8.6, gnd=1.0, twin=False)
    stage(d, "", 4, "triode")
    d.definitions([r"every cell of the part's own chart: $E_{bb}$, $R_p$, $R_s$ (the next stage's grid resistor), $R_{g1}$ and $R_k$ as printed (GE's 12AX7: $E_{bb} = 90$, 180, 300 V; $R_p = 0.1$, 0.24, 0.51 M\ohm)",
                   r"gain $= v_{out}/v_{in}$ at 2.0 V rms out (GE's condition);\quad $E_o$: the largest $v_{out}$ (rms) at 5\,\% THD, interpolated on the drive ladder",
                   r"also the quiescent $I_a$ and $V_k$, the drive at which grid current starts;\quad THD, H2, H3 against $v_{out}$ for the cell 300 V, 0.24 M\ohm, 0.51 M\ohm"], y=-0.3)
    d.write()


def triode_distortion():
    d = D("triode-distortion", "Harmonics against level, load and bias", RC_HEADER, top=8.6, gnd=1.0, twin=False)
    stage(d, "", 4, "triode", ideal=False, bypass="$C_k$", rsrc="$R_{src}$")
    d.definitions([r"the chart's middle cell, and a ladder around it: $v_{out} = 0.1$, 0.3, 1, 2, 3, 5, 10, 20, 30, 50 V rms;\quad $R_p$ and $R_k$ each $\times\,0.5$, 1, 2",
                   r"$C_k$: bypassed (ideal), 25 " + MU + r"F, and none (local feedback);\quad $R_{src} = 0$, 10 k, 100 k\ohm",
                   r"read $v_{out}$ over the last ten periods: THD, H2 to H5 by Goertzel, the sign of H2 (the phase of the second harmonic against the fundamental)",
                   r"model against model: the sheets print distortion only for output stages and the RC chart's 5\,\% point"], y=-0.3)
    d.write()


def triode_overload():
    d = D("triode-overload", "Grid-current clipping, blocking and recovery", """
VIN in 0 PWL(<burst>), CIN in x <cin>, RSTOP x gj <rstop>, RGL gj 0 1meg, VGM gj g 0   the burst through the coupling capacitor and the stopper; the grid leak at the grid
the rest of the stage as the RC chart's middle cell, Rk with its bypass capacitor
.tran over the burst and 200 ms after it""", top=8.6, gnd=1.0, twin=False)
    stage(d, "", 5.6, "triode", ideal=False, bypass="$C_k$", rg1="$R_{gl}$", rsrc=[("R", "$R_{stop}$"), ("C", "$C_{in}$")])
    d.definitions([r"a 1 kHz burst of 20 periods at 1, 3, 10 and 30 times the drive at which grid current starts, then 1/10 of that drive",
                   r"$C_{in} = 22$ nF;\quad $R_{gl} = 1$ M\ohm;\quad $R_{stop} = 0$, 1 k, 68 k\ohm;\quad $C_k = 25$ " + MU + r"F",
                   r"read the grid's mean voltage during and after the burst (the bias the grid current charges $C_{in}$ to), the gain after it, and the time for the gain to come back within 10\,\%",
                   r"a model without grid current neither clips at the grid nor blocks: `absent', and the guitar-amplifier behaviour it stands for with it"], y=-0.3)
    d.write()


def triode_frequency():
    d = D("triode-frequency", "Response with source resistance and load capacitance", RC_HEADER.replace("SIN(0 <drive> 1k)", "AC 1").replace(
        ".tran 30 periods, the last ten read", ".ac 1 Hz to 10 MHz"), top=8.6, gnd=1.0, twin=False)
    stage(d, "", 4, "triode", rsrc="$R_{src}$", cl="$C_L$")
    d.definitions([r"the chart's cells;\quad $R_{src} = 0$, 1 k, 10 k, 47 k, 100 k, 470 k\ohm, 1 M\ohm;\quad $C_L = 0$, 10, 47, 100 pF (the next stage's Miller input and the wiring)",
                   r"read $|v_{out}/v_{in}|$ from 1 Hz to 10 MHz: the upper $-3$ dB frequency, set by $R_{src}$ against the Miller input $C_{g1k} + (1+A)\,C_{g1a}$, and by $r_a \parallel R_p \parallel R_s$ against $C_{ak} + C_L$",
                   r"a model without capacitances has no upper corner: `absent'"], y=-0.3)
    d.write()


def triode_follower():
    d = D("triode-cathode-follower", "Cathode follower and cathodyne", """
VBB bb 0 <ebb>, XT bb g k DUT, RK k kx <rk>, RB kx 0 <rb>, RG g kx 1meg   copy A: the follower, the grid returned to the tap
VBB, RP bb a <rl>, XT a g k, RK k 0 <rl>                                  copy B: the cathodyne, equal loads in anode and cathode
VIN in 0 SIN(…) / AC 1; read v(k) (A), v(a) and v(k) (B)""", top=9.0, gnd=0.6, twin=False)
    tube(d, "triode", "A", 4, y=4.6, label="A")
    d.add("% copy A: the anode on the rail, the cathode through Rk and Rb to ground, the grid returned between them",
          r"\draw (TA.anode) -- ++(0,2.2) coordinate (Atop);", r"\coordinate (Avtop) at ($(Atop)+(3.6,0)$);", r"\draw (Atop) -- (Avtop);",
          r"\draw[set] (Avtop) to[V, l={$E_{bb}$}] (Avtop |- 0,\gnd) node[ground, black]{};",
          r"\draw (TA.cathode) to[R, l={$R_k$}] ++(0,-1.5) coordinate (Akx) to[R, l={$R_b$}] (Akx |- 0,\gnd) node[ground]{};",
          r"\draw (TA.control) -- ++(-0.9,0) coordinate (Agj) to[R, l_={$R_{g}$}] (Agj |- Akx) -- (Akx);",
          r"\draw (Agj) -- ++(-1.3,0) coordinate (Ain);", r"\draw[set] (Ain) to[V, l_={$v_{in}$}] (Ain |- 0,\gnd) node[ground, black]{};")
    d.add(r"\coordinate (Akm) at ($(TA.cathode)+(0,-0.3)$);")
    voltmeter(d, "Akm", 2.0, "$v_k$", "Avk")
    d.nodename("east", r"$(TA.cathode)+(-0.1,-0.25)$", "k"); d.nodename("south", r"$(Agj)+(-0.2,0.05)$", "g")
    tube(d, "triode", "B", 14.4, y=4.6, label="B")
    d.add("% copy B: equal loads in the anode and the cathode",
          r"\draw (TB.anode) -- ++(0,0.5) coordinate (Baj) to[R, l_={$R_L$}] ++(0,1.7) coordinate (Btop);",
          r"\coordinate (Bvtop) at ($(Btop)+(4.8,0)$);", r"\draw (Btop) -- (Bvtop);",
          r"\draw[set] (Bvtop) to[V, l={$E_{bb}$}] (Bvtop |- 0,\gnd) node[ground, black]{};",
          r"\draw (TB.cathode) to[R, l={$R_L$}] (TB.cathode |- 0,\gnd) node[ground]{};",
          r"\draw (TB.control) -- ++(-1.4,0) coordinate (Bin);", r"\draw[set] (Bin) to[V, l_={$V_{bias} + v_{in}$}] (Bin |- 0,\gnd) node[ground, black]{};")
    voltmeter(d, "Baj", 2.4, "$v_a$", "Bva")
    d.add(r"\coordinate (Bkm) at ($(TB.cathode)+(0,-0.3)$);")
    voltmeter(d, "Bkm", 3.6, "$v_k$", "Bvk")
    d.definitions([r"A: $E_{bb} = 250$ and 300 V;\quad $I_a = I_0/8$, $I_0/4$, $I_0/2$ ($I_0$ the model's current at 250 V and 0 V), $R_k$ for the bias, $R_b$ for the current;\quad $R_g = 1$ M\ohm",
                   r"read the gain $v_k/v_{in}$, the output resistance (a 1 mA AC current pushed into the cathode), and the largest swing at 1\,\% and 5\,\% THD",
                   r"B: $R_L = 22$, 47, 100 k\ohm{} in each;\quad the balance $|v_a| / |v_k|$ and the two outputs' resistances (unequal: the cathodyne's known asymmetry)"], y=-0.6)
    d.write()


def power_se(name, kind, title, extra):
    d = D(name, title, f"""
VB b 0 <vb>                         the supply (B+)                                                   -> source V_b (set)
BH an b V=-RL*(i(VA)-<mean>)        the ideal transformer: the load reflected, no DC drop            -> transformer, R_L
VA an at 0                          the anode ammeter                                                 -> ammeter I_a (measured)
VK k 0 <Rk*mean Ik> or 0            the cathode: on the ideal bypass, or grounded (fixed bias)        -> source (set)
VG g 0 DC <vg> SIN(<vg> <drive> 1k) the grid: the bias and the drive straight in                      -> source V_g1 + v_in (set), ammeter I_g (measured)
{extra}
.tran 6 periods, the last four read; the mean anode current, the cathode and screen voltages found by the secant method
One copy per (load, drive); the drawing shows one.""", top=9.4, gnd=0.8, twin=False)
    tube(d, kind, "", 4)
    d.add("% the anode ammeter, then the primary of the ideal transformer up to the supply",
          r"\coordinate (am) at ($(T.anode)+(0,1.1)$);", r"\ammeter{T.anode}{am}{$I_a$}",
          r"\draw (am) -- ++(0,0.3) coordinate (p1);", r"\draw (p1) to[L] ++(0,1.5) coordinate (p2);",
          r"\coordinate (s1) at ($(p1)+(1.0,0)$);", r"\coordinate (s2) at ($(p2)+(1.0,0)$);",
          r"\draw (s1) to[L, mirror] (s2);",
          r"\draw[thick] ($(p1)!0.45!(s1)+(0,0.15)$) -- ($(p2)!0.45!(s2)+(0,-0.15)$) ($(p1)!0.55!(s1)+(0,0.15)$) -- ($(p2)!0.55!(s2)+(0,-0.15)$);",
          r"\draw (s2) -- ++(1.0,0) coordinate (r2);", r"\draw (r2) to[R, l_={$R_L$}] (r2 |- s1) -- (s1);",
          r"\coordinate (vo) at ($(r2)+(2.4,0)$);", r"\draw (r2) -- (vo);", r"\voltmeter{vo |- s1}{vo}{$v_{out}$}", r"\draw (vo |- s1) -- (r2 |- s1);",
          r"\draw (p2) -- ++(0,0.5) coordinate (vtop) -- ++(6.6,0) coordinate (vb);",
          r"\draw[set] (vb) to[V, l={$V_b$}] (vb |- 0,\gnd) node[ground, black]{};")
    d.nodename("east", r"$(T.anode)+(-0.1,0.25)$", "at"); d.nodename("east", r"$(p1)+(-0.1,0)$", "an"); d.nodename("south", r"$(vtop)+(4.6,0.05)$", "b")
    d.add("% the cathode on its bias",
          r"\draw[set] (T.cathode) to[V, l={$R_k \bar I_k$}] (T.cathode |- 0,\gnd) node[ground, black]{};")
    d.nodename("east", r"$(T.cathode)+(-0.1,-0.25)$", "k")
    grid(d, "", "$V_{g1} + v_{in}$", node="g", ammeter="$I_g$")
    if kind == "pentode":
        screen(d, "", "$V_{g2}$", ammeter="$I_{g2}$", node="sg", resistor="$R_{g2}$", left=8.2)
    return d


def triode_power_se():
    d = power_se("triode-power-se", "triode", "Single-ended output stage", "")
    d.definitions([r"every column of the part's sheets (the 300B, 2A3, 6B4G, 6C33C tables; a pentode's triode-connected ones), and around each: $R_L \times 0.25$ to 4 in half-octaves",
                   r"$v_{in}$ from 0 to 1.25 times the sheet's drive in 5\,\% steps (to the grid-current onset, and past it for class A2);\quad fixed bias ($V_k = 0$) or cathode bias ($R_k$, ideal bypass)",
                   r"read $P_{out} = v_{out,1}^2/R_L$ (the fundamental), THD, D2, D3; $\bar I_a$ at zero and full signal; the peak grid current; the output resistance from two loads",
                   r"a part with no sheet table: the model's own point, $V_b = 250$ V, $I_a = I_0/3$, $R_L = 2\,r_a$, driven to the grid-current onset"], y=-0.6)
    d.write()


def power_pp(name, kind, title, extra, defs):
    d = D(name, title, f"""
VB b 0 <vb>                                         the supply at the centre tap                          -> source V_b (set)
BH0 an0 b V=-Raa/4*((i(VA0)+x i(VS0))-(i(VA1)+x i(VS1)))   the ideal centre-tapped primary, one half each    -> transformer, R_aa
BH1 an1 b V=+Raa/4*(…)
VA0 an0 at0 0, VA1 an1 at1 0                        the anode ammeters                                     -> ammeters I_a1, I_a2 (measured)
VG0 g0 0 DC <vg> SIN(<vg> <drive> 1k), VG1 … -<drive>   the grids driven in antiphase                     -> sources (set), ammeters I_g (measured)
VK k 0 <Rk*(Ik1+Ik2)> or per valve                  the cathodes on the ideal bypass, or grounded         -> source (set)
{extra}
.tran 6 periods, the last four read; one copy per (load, drive)""", top=10.8, gnd=0.6, twin=False)
    tube(d, kind, "A", 3.6, y=3.8, label="")
    tube(d, kind, "B", 11.4, y=3.8, label="", mirror=True)
    d.add("% the two anodes through their ammeters to the ends of the centre-tapped primary",
          r"\coordinate (Aam) at ($(TA.anode)+(0,1.1)$);", r"\ammeter{TA.anode}{Aam}{$I_{a1}$}",
          r"\coordinate (Bam) at ($(TB.anode)+(0,1.1)$);", r"\ammeter{TB.anode}{Bam}{$I_{a2}$}",
          r"\coordinate (pl) at ($(Aam)+(0,0.9)$);", r"\coordinate (pr) at ($(Bam)+(0,0.9)$);",
          r"\coordinate (ct) at ($(pl)!0.5!(pr)$);",
          r"\draw (Aam) -- (pl) to[L] (ct) to[L] (pr) -- (Bam);",
          r"\draw[thick] ($(pl)+(0.3,0.42)$) -- ($(pr)+(-0.3,0.42)$) ($(pl)+(0.3,0.52)$) -- ($(pr)+(-0.3,0.52)$);",
          r"\coordinate (sl) at ($(pl)+(1.4,0.95)$);", r"\coordinate (sr) at ($(pr)+(-1.4,0.95)$);",
          r"\draw (sl) to[L, mirror] (sr);",
          r"\draw (sl) -- ++(0,0.9) coordinate (rlA) to[R, l={$R_L$}] (rlA -| sr) -- (sr);",
          r"\draw (ct) -- ++(0,-0.7) coordinate (ctb) -- ++(2.2,0) coordinate (vbx);")
    d.add(r"\coordinate (vbs) at ($(TB.anode)+(5.0,0.8)$);", r"\draw (vbx) -| (vbs);",
          r"\draw[set] (vbs) to[V, l={$V_b$}] (vbs |- 0,\gnd) node[ground, black]{};")
    d.nodename("south", r"$(ct)+(0.3,-0.7)$", "b")
    d.add("% the cathodes joined, on their bias",
          r"\draw (TA.cathode) -- ++(0,-0.75) coordinate (Ak) -| ($(TB.cathode)+(0,-0.75)$) -- (TB.cathode);",
          r"\coordinate (kc) at ($(Ak)!0.5!(TB.cathode |- Ak)$);",
          r"\draw[set] (kc) to[V, l={$R_k \bar I_k$}] (kc |- 0,\gnd) node[ground, black]{};")
    d.nodename("south", r"$(kc)+(0.4,0.05)$", "k")
    d.gate("$V_{g1} + v_{in}$", "g0", -1.2, "V", "$I_{g1}$", terminal="TA.control", name="Ag")
    d.add("% the second grid, driven in antiphase, at the right of the mirrored tube",
          r"\coordinate (Bg) at (TB.control);", r"\draw (Bg) -- ++(1.4,0) coordinate (Bgs);",
          r"\draw[set] (Bgs) to[V, l={$V_{g1} - v_{in}$}] (Bgs |- 0,\gnd) node[ground, black]{};")
    d.nodename("south", r"$(Bg)+(0.5,0.02)$", "g1")
    if kind == "pentode":
        d.add("% the screens: on their supply through Rg2, or on the ultralinear taps (in the definitions)",
              r"\draw (TA.screen) -- ++(-0.25,0) -- ++(0,0.9) node[above, font=\scriptsize, inner sep=1pt] {$g_2$};",
              r"\draw (TB.screen) -- ++(0.25,0) -- ++(0,0.9) node[above, font=\scriptsize, inner sep=1pt] {$g_2$};")
    d.definitions(defs, y=-0.4)
    d.write()


def triode_power_pp():
    power_pp("triode-power-pp", "triode", "Push-pull output stage", "", [
        r"$R_{aa} = 4\,(N_{half}/N_s)^2 R_L$, the anode-to-anode load;\quad every push-pull column of the part's sheets (class A1, AB1, AB2), and around each: $R_{aa} \times 0.25$ to 4 in half-octaves",
        r"$v_{in}$ per grid from 0 to 1.25 times the sheet's drive (a grid-to-grid drive is halved, an rms one $\times\sqrt 2$);\quad fixed bias, or cathode bias common or per valve",
        r"read $P_{out}$ from the half-primary voltage $v$: $4 v_1^2 / R_{aa}$; THD, D3, D5; $\bar I_a$ per valve at zero and full signal; the peak grid current",
        r"the output resistance from two loads; intermodulation by the KT88 sheet's method (50 Hz and 6 kHz, 4:1)"])


def triode_noise():
    d = D("triode-noise", "Noise", """
VIN in 0 DC 0 AC 1, RSN in g <rs>       the source resistance, the noise input       -> resistor R_src, source v_in (set)
VBB bb 0 <ebb>, RL bb a <rl>            the supply and the plate resistor            -> source E_bb (set), resistor R_p
RK k 0 <rk>, CK k 0 1                   the cathode, bypassed                        -> resistor R_k, capacitor C_k
XN a g k DUT; .noise v(a) VIN dec 10 1 100k, with the noise of every element listed""", top=8.8, gnd=1.0, twin=False)
    tube(d, "triode", "", 4, y=3.8)
    d.add("% the plate resistor up to the rail", r"\draw (T.anode) -- ++(0,0.5) coordinate (aj) to[R, l_={$R_p$}] ++(0,1.6) coordinate (top);",
          r"\coordinate (vtop) at ($(top)+(4.2,0)$);", r"\draw (top) -- (vtop);",
          r"\draw[set] (vtop) to[V, l={$E_{bb}$}] (vtop |- 0,\gnd) node[ground, black]{};",
          r"\draw (T.cathode) to[R, l={$R_k$}] (T.cathode |- 0,\gnd) node[ground]{};",
          r"\draw (T.cathode) -- ++(1.2,0) coordinate (ck) to[C, l={$C_k$}] (ck |- 0,\gnd) node[ground]{};",
          r"\draw (T.control) -- ++(-0.3,0) to[R, l_={$R_{src}$}] ++(-1.8,0) coordinate (vin);",
          r"\draw[set] (vin) to[V, l_={$v_{in}$}] (vin |- 0,\gnd) node[ground, black]{};")
    voltmeter(d, "aj", 2.6, "$e_{out}$", "vo")
    d.definitions([r"$E_{bb} = 250$ V, $R_p = 100$ k\ohm, $R_k = 1.5$ k\ohm{} bypassed by $C_k = 1$ F;\quad $R_{src} = 1$ k\ohm;\quad $f = 1$ Hz to 100 kHz",
                   r"read the noise referred to the input, $e_n$ at 10 Hz, 1 kHz, 10 kHz, and the share of the output noise from inside the model (every element of the subcircuit)",
                   r"$R_{eq} = e_n^2/(4kT) - R_{src}$, beside the ECC88's 300 \ohm;\quad a model whose share is zero has no anode noise: `absent'"])
    d.write()


# ------------------------------------------------------------------------ the pentode drawings
def pentode_anode():
    d = D("pentode-anode", "Anode and screen characteristics", """
VAk sw ak 0          a 0 V source from the swept node to the anode of copy k   -> ammeter I_a (measured)
VGk gk 0 <vg1>       the control grid of copy k                                -> source V_g1 (set)
VSk sk 0 <vg2>       the screen of copy k, through its 0 V source              -> source V_g2 (set), ammeter I_g2 (measured)
XTk ak sk gk 0 DUT   copy k, suppressor to cathode                             -> pentode
VSW sw 0, .dc        the swept anode supply                                    -> source V_a (set)
One copy per (Vg2, Vg1); drawn as one pentode.""", twin=False)
    tube(d, "pentode"); cathode_ground(d); anode(d, node="ak"); supply(d, node="sw")
    grid(d, node="gk", ammeter="$I_{g1}$"); screen(d, node="sk")
    d.definitions([r"$V_a$ swept 0 to 1000 V in 1 V steps (0.1 V below 50 V);\quad $V_{g2}$ = " + VG2_LADDER, GRID_LADDER,
                   r"read $I_a(V_a)$ and $I_{g2}(V_a)$ per trace: the knee (the $V_a$ where $I_a$ is 90\,\% of its value at $V_a = V_{g2}$), $r_a$ above it, and the screen current's rise below it",
                   r"$I_{g2}(50\ \mathrm{V}) / I_{g2}(V_{g2})$: well above 1 in a real pentode; exactly 1 is a screen equation without the anode in it", PENTODE_NOTE])
    d.write()


def pentode_transfer():
    d = D("pentode-transfer", "Transfer characteristics, cut-off and remote cut-off", """
VAk ak 0 <va>, VSk sk 0 <vg2> (or through Rg2 from a supply), VGKk g gk 0, XTk …   copy k   -> ammeters I_a, I_g2, I_g1 (measured)
VG g 0, .dc   the control-grid drive, swept                                                 -> source V_g1 (set)""", twin=False)
    tube(d, "pentode"); cathode_ground(d); anode(d, node="ak"); supply(d); grid(d, node="g", ammeter="$I_{g1}$")
    screen(d, node="sk", resistor="$R_{g2}$", left=8.2)
    d.definitions([r"$V_{g1}$ swept $-150$ V to $+5$ V in 10 mV steps;\quad $V_a = 100$, 250, 300, 400, 500 V;\quad $V_{g2}$ = " + VG2_LADDER + r", direct ($R_{g2} = 0$)",
                   r"and the remote-cut-off connection: the screen through 33 k\ohm{} from 250 V (6BA6) and 250 k\ohm{} from 300 V (6SJ7)",
                   r"read $I_a$, $I_{g2}$ against $V_{g1}$, lin and log;\quad cut-off at $I_a = 10$ " + MU + r"A;\quad $g_m = dI_a/dV_{g1}$ and $V_{g1}$ where it falls to 2, 10, 40, 100 " + MU + r"mho (the 6K7, 6BA6 conditions)"])
    d.write()


def pentode_params():
    d = D("pentode-params", "Transconductance, anode resistance and the screen's amplification factor", """
copy A: AC on the control grid   -> g_m = i_a / v_g1
copy B: AC on the anode          -> 1/r_a = i_a / v_a
copy C: AC on the screen         -> g_m2 = i_a / v_g2;  mu(g1-g2) = g_m / g_m2
.ac lin 1 1k 1k; one set per (Vg2, Ia) of the ladders""", twin=False)
    for n, x, lab, (va, vg, vs) in (("A", 4, "A", ("$V_a$", "$V_{g1} + v$", "$V_{g2}$")), ("B", 13.4, "B", ("$V_a + v$", "$V_{g1}$", "$V_{g2}$")),
                                    ("C", 22.8, "C", ("$V_a$", "$V_{g1}$", "$V_{g2} + v$"))):
        tube(d, "pentode", n, x, label=lab); cathode_ground(d, n)
        anode(d, n, "$I_a + i_a$"); supply(d, n, va, dx=2.6); grid(d, n, vg, node=None, dx=-1.1); screen(d, n, vs, ammeter=None, left=5.0)
    d.definitions([r"$V_a = V_{g2} = 250$ V (and $V_a = 100$, 400 V);\quad $V_{g2}$ = " + VG2_LADDER + r";\quad $I_a = 10$ " + MU + r"A to 500 mA, 1-2-5;\quad $v = 1$ V of AC at 1 kHz",
                   r"A: $g_m$;\quad B: $r_a$;\quad C: $g_{m2}$;\quad $\mu_{g1g2} = g_m / g_{m2}$, the amplification factor a pentode's sheet prints (11 for the EL34), not $g_m r_a$",
                   r"and at the sheets' own points, at the sheet's grid voltage and at the sheet's anode current"])
    d.write()


def pentode_triode():
    d = D("pentode-triode", "Strapped as a triode", """
the triode battery (anode, transfer, params, grid current) with the screen tied to the anode: XTk ak ak gk 0 DUT""", twin=False)
    tube(d, "pentode"); cathode_ground(d); anode(d, node="ak"); supply(d, node="sw"); grid(d, node="gk", ammeter="$I_g$")
    screen_strapped(d)
    d.definitions([r"the screen to the anode (the sheets' `g2 connected to a'; through 100 \ohm{} where a sheet says so), the suppressor to the cathode",
                   r"every triode measurement over again: $I_a(V_a)$ per grid step, $I_a(V_{g1})$, $\mu$, $g_m$, $r_a$ against $I_a$, the grid current;\quad laid over the sheets' triode-connected curves and tables"])
    d.write()


def pentode_ultralinear():
    d = D("pentode-ultralinear", "Ultralinear characteristics", """
BSk sk 0 V=<V0>+x*(V(ak)-<V0>)   the screen at a fraction x of the way from the quiescent point to the anode   -> source (set)
VSk …, VGk gk 0 <vg1>, VAk sw ak 0, XTk ak sk gk 0                                                          -> ammeters I_a, I_g2 (measured)
VSW sw 0, .dc""", twin=False)
    tube(d, "pentode"); cathode_ground(d); anode(d, node="ak"); supply(d, node="sw"); grid(d, node="gk")
    screen(d, "", r"$V_0 + x\,(V_a - V_0)$", node="sk")
    d.definitions([r"$x = 0.2$, 0.4, 0.43, 0.5 (the sheets' taps: Mullard 20\,\% and 43\,\%, Genalex 40\,\%, Tung-Sol 43\,\% and 40\,\%);\quad $V_0$ = the sheet's quiescent point (400, 425, 450 V) and 250 to 450 V in 50 V steps",
                   r"$V_a$ swept 0 to 800 V;\quad $V_{g1}$ in the sheets' steps;\quad read $I_a$ and $I_{g2}$ against $V_a$, and $r_a$ at the quiescent point"])
    d.write()


def pentode_rc():
    d = D("pentode-rc-amplifier", "The resistance-coupled amplifier chart, pentode", RC_HEADER + "\nRG2i bbi si <rg2>, the screen ideally decoupled (held at Ebb - Rg2 times its mean current)", top=8.6, gnd=1.0, twin=False)
    stage(d, "", 4, "pentode", rg2="$R_{g2}$")
    d.definitions([r"each cell of the sheet's chart (6J7: 120 cells; EF86: tables A to C, and the triode-connected tables): $E_{bb}$, $R_p$, $R_{g2}$, $R_s$, $R_k$ as printed",
                   r"the zero-bias rows ($R_{g1} = 10$ M\ohm, no $R_k$) need the grid's initial-velocity current to bias: a model without it runs at $V_{g1} = 0$, and says so",
                   r"gain at 2.0 V rms out and at small signal;\quad $E_o$ at 5\,\% THD; for the EF86's triode-connected tables, $v_{out}$ and THD at the onset of grid current"], y=-0.3)
    d.write()


def pentode_power_se():
    d = power_se("pentode-power-se", "pentode", "Single-ended output stage, pentode",
                 "VSS sn 0 <Vg2 - Rg2*mean Ig2>, VS sn sg 0   the screen on its ideal decoupling -> source V_g2 (set), ammeter I_g2 (measured)")
    d.definitions([r"every single-ended column of the part's sheets, pentode, ultralinear and triode-connected;\quad around each: $R_L \times 0.25$ to 4, $V_{g2} \pm 50$ V, drive 0 to 1.25 times the sheet's",
                   r"the screen through $R_{g2}$ ideally decoupled, or straight on its supply;\quad Mullard's sensitivity: the drive for $P_{out} = 50$ mW",
                   r"read $P_{out}$, THD, D2, D3; $\bar I_a$, $\bar I_{g2}$ at zero and full signal; the peak $I_{g1}$; the output resistance from two loads"], y=-0.6)
    d.write()


def pentode_power_pp():
    power_pp("pentode-power-pp", "pentode", "Push-pull output stage, pentode and ultralinear",
             "screens on their supply through Rg2 (per valve or common), ideally decoupled; or on the taps BU = b -/+ x Raa/4 (...), through Rg2", [
                 r"$R_{aa} = 4\,(N_{half}/N_s)^2 R_L$;\quad every push-pull column of the part's sheets: pentode with fixed or cathode bias, ultralinear at the sheet's tap, triode-connected; the continuous-sine-wave tables too",
                 r"around each: $R_{aa} \times 0.25$ to 4, drive 0 to 1.25 times the sheet's, $V_b \pm 10\,\%$;\quad the screen through $R_{g2}$, common to both valves or per valve, as printed",
                 r"read $P_{out}$, THD, D3, D5; $\bar I_a$, $\bar I_{g2}$ per valve at zero and full signal; the peak $I_{g1}$; output resistance; IMD (50 Hz + 6 kHz, 4:1)",
                 r"a model whose equations fail past cut-off (the Koren screen's logarithm) cannot be driven into class AB: `failed', error class domain"])


def pentode_noise():
    d = D("pentode-noise", "Noise, pentode", """
the triode noise deck with the screen through Rg2 from Ebb, decoupled to the cathode: .noise v(a) VIN dec 10 1 100k""", top=8.8, gnd=1.0, twin=False)
    tube(d, "pentode", "", 4, y=3.8)
    d.add(r"\draw (T.anode) -- ++(0,0.5) coordinate (aj) to[R, l_={$R_p$}] ++(0,1.6) coordinate (top);",
          r"\coordinate (vtop) at ($(top)+(4.6,0)$);", r"\draw (top) -- (vtop);",
          r"\draw[set] (vtop) to[V, l={$E_{bb}$}] (vtop |- 0,\gnd) node[ground, black]{};",
          r"\draw (T.screen) -- ++(-0.3,0) -- ++(0,1.25) coordinate (s1);", r"\coordinate (sc) at ($(T.anode |- s1)+(-4.4,0)$);",
          r"\draw (s1) -- (sc) to[R, l={$R_{g2}$}] (sc |- top) -- (top);",
          r"\draw (sc) -- ++(-1.3,0) coordinate (cs) to[C, l_={$C_{g2}$}] (cs |- 0,\gnd) node[ground]{};",
          r"\draw (T.cathode) to[R, l={$R_k$}] (T.cathode |- 0,\gnd) node[ground]{};",
          r"\draw (T.cathode) -- ++(1.2,0) coordinate (ck) to[C, l={$C_k$}] (ck |- 0,\gnd) node[ground]{};",
          r"\draw (T.control) -- ++(-0.3,0) to[R, l_={$R_{src}$}] ++(-1.8,0) coordinate (vin);",
          r"\draw[set] (vin) to[V, l_={$v_{in}$}] (vin |- 0,\gnd) node[ground, black]{};")
    voltmeter(d, "aj", 2.8, "$e_{out}$", "vo")
    d.definitions([r"$E_{bb} = 250$ V, $R_p = 100$ k\ohm, $R_{g2} = 390$ k\ohm, $R_k = 1.5$ k\ohm{} (the EF86's noise condition: $V_b = 250$ V, $R_a = 100$ k\ohm)",
                   r"read $e_n$ referred to the grid, and integrated from 25 Hz to 10 kHz beside the EF86's 2 " + MU + r"V;\quad the share from inside the model: zero is `absent' (no shot or partition noise)"])
    d.write()


# ------------------------------------------------------------------------ the rectifier and diode drawings
def rectifier_drop():
    d = D("rectifier-drop", "Tube voltage drop", """
VA a 0, .dc VA -5 300 0.05   the anode driven from below zero to past any rated current   -> source V_a (set) + ammeter I_a (measured)
XD a 0 DUT (each plate alone, the other at the cathode)""", twin=False)
    tube(d, "diode"); cathode_ground(d); anode(d, node="a"); supply(d)
    d.definitions([r"$V_a$ swept $-5$ V to $+300$ V in 50 mV steps, each plate alone",
                   r"read $I_a(V_a)$: the drop at the sheets' currents (to 440 mA for the 5Y3), the exponent and perveance of $I_a = k V_a^n$ between 10 and 100 V,",
                   r"and the current at $V_a = 0$ and $-1$ V (a real diode's initial-velocity current, which the 6AL5 and 6H6 sheets plot)"])
    d.write()


def rectifier_regulation():
    d = D("rectifier-regulation", "Full-wave rectifier: regulation, ripple and peak current", """
VPi pi 0 SIN(0 <√2 Vac> <f>), RSPi pi pai <Rs>, VMAi pai tai 0   one half of the secondary, its supply resistance, the plate ammeter -> source (set), ammeter I_a (measured)
VNi ni 0 SIN(0 -<√2 Vac> <f>), RSNi …, VMBi …                    the other half, in antiphase
XTi tai tbi ci DUT                                                the twin diode
C1i ci 0 <C1>, ILi ci 0 <Idc>  (capacitor input)  or  L1i ci lmi <L>, RLCi …, C2i oi 0 <C2>, ILi oi 0 <Idc>  (choke input)
.tran 40 mains periods, the last five read; one copy per (Vac, Idc)""", top=8.4, gnd=0.8, twin=False)
    d.add("% the two halves of the secondary, each with its supply resistance and the plate ammeter",
          r"\coordinate (pt) at (1.0,5.0);", r"\coordinate (pb) at (1.0,1.6);",
          r"\draw[set] (pt) to[sV, l_={$\sqrt 2\,V_{ac}\sin\omega t$}] (1.0,3.3) coordinate (ctap);",
          r"\draw[set] (ctap) to[sV, l_={$-\sqrt 2\,V_{ac}\sin\omega t$}] (pb);",
          r"\draw (ctap) -- ++(-0.6,0) node[ground, rotate=-90]{};",
          r"\draw (pt) to[R, l={$R_s$}] ++(2.2,0) coordinate (pa);", r"\coordinate (pam) at ($(pa)+(1.6,0)$);", r"\ammeterh{pa}{pam}{$I_{a1}$}",
          r"\draw (pb) to[R, l_={$R_s$}] ++(2.2,0) coordinate (pbx);", r"\coordinate (pbm) at ($(pbx)+(1.6,0)$);", r"\ammeterh{pbx}{pbm}{$I_{a2}$}",
          r"\node[diodetube, rotate=90] (D1) at ($(pam)+(1.3,0)$) {};", r"\node[diodetube, rotate=90] (D2) at ($(pbm)+(1.3,0)$) {};",
          r"\draw (pam) -- (D1.anode); \draw (pbm) -- (D2.anode);",
          r"\draw (D1.cathode) -- ++(0.5,0) coordinate (k1); \draw (D2.cathode) -- ++(0.5,0) coordinate (k2);",
          r"\draw (k1) -- (k2);", r"\coordinate (c) at ($(k1)!0.5!(k2)+(1.0,0)$);", r"\draw ($(k1)!0.5!(k2)$) -- (c);",
          r"\node[font=\small, align=center] at ($(D1)!0.5!(D2)$) {DUT\\(twin diode)};",
          r"\draw (c) to[C, l={$C_1$}] (c |- 0,\gnd) node[ground]{};",
          r"\draw (c) to[L, l={$L$, $R_L$}] ++(2.6,0) coordinate (o);",
          r"\draw (o) to[C, l={$C_2$}] (o |- 0,\gnd) node[ground]{};",
          r"\draw (o) -- ++(1.4,0) coordinate (il);", r"\draw[set] (il) to[I, l={$I_{dc}$}] (il |- 0,\gnd) node[ground, black]{};")
    voltmeter(d, "il", 2.4, "$V_{dc}$", "vdc")
    d.nodename("south", r"$(c)+(0.3,0.05)$", "c"); d.nodename("south", r"$(o)+(0.3,0.05)$", "o")
    d.definitions([r"capacitor input: $C_1$ straight to the load ($L$ shorted, no $C_2$);\quad choke input: no $C_1$, $L$ then $C_2$;\quad the load a constant current $I_{dc}$, 0 to 300 mA in 10 mA steps",
                   r"$V_{ac}$ per plate = 150 to 550 V in 50 V steps (the sheets' curve families);\quad $R_s$ per plate = 0, 25, 50, 75, 100, 135, 150, 200 \ohm;\quad $C_1 = 4$, 8, 10, 16, 20, 32, 40, 60 " + MU + r"F",
                   r"$L = 5$, 10, 20, 40 H and `infinite' (the 6X4 chart's solid curves);\quad $C_2 = 10$, 40 " + MU + r"F;\quad 50 and 60 Hz;\quad and every curve the sheets draw, with their own $C$, $L$ and $R_s$",
                   r"read $V_{dc}$ (the mean at the filter's input), the ripple, the steady peak plate current per plate, and the rectification efficiency $V_{dc}/(\sqrt 2 V_{ac})$ (GE's definition)"], y=-0.5)
    d.write()


def rectifier_surge():
    d = D("rectifier-surge", "Switch-on surge", """
the regulation deck with every capacitor discharged at t = 0 (uic), the cathode already hot; read the plate currents over the first two mains periods""",
          top=8.4, gnd=0.8, twin=False)
    d.add(r"\coordinate (pt) at (1.0,5.0);", r"\coordinate (pb) at (1.0,1.6);",
          r"\draw[set] (pt) to[sV, l_={$\sqrt 2\,V_{ac}\sin(\omega t + \phi)$}] (1.0,3.3) coordinate (ctap);",
          r"\draw[set] (ctap) to[sV, l_={antiphase}] (pb);", r"\draw (ctap) -- ++(-0.6,0) node[ground, rotate=-90]{};",
          r"\draw (pt) to[R, l={$R_s$}] ++(2.2,0) coordinate (pa);", r"\coordinate (pam) at ($(pa)+(1.6,0)$);", r"\ammeterh{pa}{pam}{$i_{a1}(t)$}",
          r"\draw (pb) to[R, l_={$R_s$}] ++(2.2,0) coordinate (pbx);", r"\coordinate (pbm) at ($(pbx)+(1.6,0)$);", r"\ammeterh{pbx}{pbm}{$i_{a2}(t)$}",
          r"\node[diodetube, rotate=90] (D1) at ($(pam)+(1.3,0)$) {};", r"\node[diodetube, rotate=90] (D2) at ($(pbm)+(1.3,0)$) {};",
          r"\draw (pam) -- (D1.anode); \draw (pbm) -- (D2.anode);",
          r"\draw (D1.cathode) -- ++(0.5,0) coordinate (k1); \draw (D2.cathode) -- ++(0.5,0) coordinate (k2);", r"\draw (k1) -- (k2);",
          r"\coordinate (c) at ($(k1)!0.5!(k2)+(1.0,0)$);", r"\draw ($(k1)!0.5!(k2)$) -- (c);",
          r"\draw (c) to[C, l={$C_1$, discharged}] (c |- 0,\gnd) node[ground]{};",
          r"\draw (c) -- ++(3.4,0) coordinate (il);", r"\draw[set] (il) to[I, l={$I_{dc}$}] (il |- 0,\gnd) node[ground, black]{};",
          r"\node[font=\small, align=center] at ($(D1)!0.5!(D2)$) {DUT\\(twin diode)};")
    d.definitions([r"$\phi = 0$ and $90^\circ$ (switched at the zero crossing and at the peak);\quad $C_1$ and $R_s$ as in the regulation deck;\quad $V_{ac}$ per plate as the sheets' rating charts",
                   r"read the first peak plate current per plate, beside the hot-switching ratings (2.5 A for the 5Y3, 1 A for the 6X4) and the minimum $R_s$ of GE's Rating Chart III",
                   r"what it cannot show: a directly heated cathode's warm-up, which delays and softens the surge (no model has a heater)"])
    d.write()


def diode_signal():
    d = D("diode-signal", "Signal diode: initial-velocity current and detection", """
copy A: VA a 0, .dc VA -3 20 0.01; XD a 0 DUT                              -> source V_a (set), ammeter I_a (measured)
copy B: VIN in 0 SIN(0 <√2 Vin> <f>), XD in o DUT, RL o 0 <RL>, CL o 0 <CL>   -> source v_in (set), voltmeter V_dc (measured)""", twin=False)
    tube(d, "diode", "A", 4, label="A"); cathode_ground(d, "A"); anode(d, "A", node="a"); supply(d, "A")
    d.add("% copy B: the detector, the vacuum diode in series and the RC load",
          r"\node[diodetube, rotate=90] (DB) at (13.2,3.6) {};",
          r"\draw (DB.anode) -- ++(-1.6,0) coordinate (bin);",
          r"\draw[set] (bin) to[sV, l_={$v_{in}$}] (bin |- 0,\gnd) node[ground, black]{};",
          r"\draw (DB.cathode) -- ++(0.8,0) coordinate (bo);",
          r"\draw (bo) to[R, l_={$R_L$}] (bo |- 0,\gnd) node[ground]{};",
          r"\draw (bo) -- ++(1.4,0) coordinate (bc) to[C, l_={$C_L$}] (bc |- 0,\gnd) node[ground]{};",
          r"\node[font=\small] at ($(DB)+(0,0.85)$) {B: DUT};")
    voltmeter(d, "bc", 2.0, "$V_{dc}$", "bv")
    d.definitions([r"A: $V_a$ swept $-3$ V to $+20$ V in 10 mV steps;\quad read $I_a$ on a log scale: the current at $V_a = 0$ and $-1$ V, and $V_a$ at 10 " + MU + r"A",
                   r"B: $v_{in} = 1$ to 100 V rms at 1 kHz and 455 kHz;\quad $R_L = 0.1$, 0.25, 0.5, 1 M\ohm;\quad $C_L = 100$ pF;\quad read $V_{dc}$ (the 6AL5 and 6H6 operation characteristics)"])
    d.write()


def heptode_conversion():
    d = D("heptode-conversion", "Frequency converter: conversion transconductance", """
VOSC osc 0 SIN(0 <Vosc> <f_osc>), CO osc g1 …, RG1 g1 0 20k   the oscillator grid, grid-leak biased   -> source (set), ammeter I_g1 (measured)
VSIG g3 0 DC <vg3> SIN(…)                                      the signal grid                         -> source (set)
VS g2 0 <vg2>, VA a 0 <va>, XT a g3 g2 g1 0 DUT                the screen and the anode                -> ammeter I_a (measured)
.tran; the anode current's component at |f_osc - f_sig| over the signal amplitude""", twin=False)
    tube(d, "pentode", "", 6.4, label="DUT\\\\(heptode)")
    cathode_ground(d); anode(d, node="a"); supply(d, dx=4.2)
    d.add("% the signal grid and the screen as labelled leads (their sources in the definitions)",
          r"\draw (T.suppressor) -- ++(-0.3,0) -- ++(0,1.3) node[above left, set, font=\small, inner sep=1pt] {$g_3$: $V_{g3} + v_{sig}$};",
          r"\draw (T.screen) -- ++(-1.6,0) -- ++(0,1.0) node[above, set, font=\small, inner sep=1pt] {$g_2$: $V_{g2}$};",
          "% the oscillator grid: its 20 k leak to ground, the ammeter, the coupling capacitor and the oscillator",
          r"\coordinate (g) at (T.control);", r"\draw (g) -- ++(-0.6,0) coordinate (gj);",
          r"\draw (gj) to[R, l={20 k\ohm}] (gj |- 0,\gnd) node[ground]{};",
          r"\coordinate (gam) at ($(gj)+(-1.7,0)$);", r"\ammeterh{gam}{gj}{$I_{g1}$}",
          r"\draw (gam) to[C, l_={$C$}] ++(-1.4,0) coordinate (osc);",
          r"\draw[set] (osc) to[sV, l_={$v_{osc}$}] (osc |- 0,\gnd) node[ground, black]{};")
    d.nodename("south", r"$(g)+(-0.3,0.02)$", "g1")
    d.definitions([r"$V_a = V_{g2} = 250$ V (the 6BE6 sheet's columns);\quad the oscillator set for $I_{g1} = 0.5$ mA (10 V rms into 20 k\ohm);\quad $V_{g3} = -1.5$ to $-30$ V",
                   r"read the conversion transconductance $g_c$ against $V_{g3}$ and against the oscillator grid current;\quad only for a model with a separate signal grid (Reefman's heptode)"])
    d.write()


def main():
    for f in (tube_runs, tube_capacitance, triode_anode, triode_positive_grid, triode_transfer, triode_params, triode_grid_current,
              triode_rc, triode_distortion, triode_overload, triode_frequency, triode_follower, triode_power_se, triode_power_pp,
              triode_noise, pentode_anode, pentode_transfer, pentode_params, pentode_triode, pentode_ultralinear, pentode_rc,
              pentode_power_se, pentode_power_pp, pentode_noise, rectifier_drop, rectifier_regulation, rectifier_surge,
              diode_signal, heptode_conversion):
        f()
    print("29 tube drawings written")


if __name__ == "__main__":
    main()
