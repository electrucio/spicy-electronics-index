"""The op-amp bench drawings, with the blocks of benches.py (which runs this): the amplifier at (4,4.4) with its
non-inverting input up (down for the inverting fixtures, whose feedback then runs over the top), the supply pins
as short arrows with the rail voltages beside them, the input source to the left, the output node to the right
with the voltmeter, the load resistor and the load capacitor down to ground at y = 1, and the feedback around
the bottom (or the top). Blue is what the bench sets, red what it measures (a circled A reads a current, a
circled V a voltage), green the deck's node names. Every drawing is the set-up a person would wire,
semantically the deck's: a 0 V source is an ammeter, the servo's 1 GH and 1 GF are drawn as they are, and
the copies a deck packs are one circuit with the list of its conditions. The model's own pin order is put in
by the job builder; the drawing shows in+, in-, V+, V-, out."""
from benches import D
from benches_fet import voltmeter

MU = r"\textmu "
DEG = r"\textdegree "
RAILS = (r"$+15$ V", r"$-15$ V")
LOOP = 2.3   # the y of the feedback's run under the amplifier


# ------------------------------------------------------------------------ the blocks, for the amplifier named n
def amp(d, n="A", x=4, y=4.4, inv_up=False, label="DUT"):
    opt = "op amp" + ("" if inv_up else ", noinv input up")
    d.add("% the amplifier" + (", inverting input up" if inv_up else ", non-inverting input up"),
          rf"\node[{opt}, font=\small] ({n}) at ({x},{y}) {{{label}}};")


def rails(d, n="A", vp=RAILS[0], vn=RAILS[1]):
    d.add("% the supply pins: the rails are what the bench sets", rf"\rails{{{n}.up}}{{{n}.down}}{{{vp}}}{{{vn}}}")
    d.nodename("east", rf"$({n}.up)+(-0.08,0.3)$", "vp"); d.nodename("east", rf"$({n}.down)+(-0.08,-0.3)$", "vn")


def output(d, n="A", dx=0.8, node="out"):
    d.add("% the output node", rf"\draw ({n}.out) -- ++({dx},0) coordinate ({n}o);")
    if node:
        d.nodename("south", rf"$({n}o)+(-0.35,0.05)$", node)


def feedback(d, n="A", y=LOOP, element=None, ammeter=None, top=False, node="inn"):
    """from the output node around to the inverting input: under the amplifier, or over it when that input is up;
    an element (R2, L1) or an ammeter sits in the run"""
    o, pin = f"{n}o", f"{n}.-"
    d.add("% the feedback, around to the inverting input", rf"\coordinate ({n}fu) at ($({pin})+(-0.5,0)$);",
          rf"\coordinate ({n}fl) at ({n}fu |- 0,{y});", rf"\coordinate ({n}ol) at ({o} |- 0,{y});")
    if element:
        side = "l" if top else "l_"   # the run goes left: l below, l_ above; the label away from the amplifier
        d.add(rf"\draw ({o}) -- ({n}ol) to[{element[0]}, {side}={{{element[1]}}}] ({n}fl) -- ({n}fu) -- ({pin});")
    elif ammeter:
        d.add(rf"\draw ({o}) -- ({n}ol);", rf"\ammeterh{{{n}fl}}{{{n}ol}}{{{ammeter}}}", rf"\draw ({n}fl) -- ({n}fu) -- ({pin});")
    else:
        d.add(rf"\draw ({o}) -- ({n}ol) -- ({n}fl) -- ({n}fu) -- ({pin});")
    if node:
        d.nodename("south", rf"$({n}fu)+(0.25,0.03)$", node)


def source(d, label, node="in", n="A", pin="+", dx=-1.5, kind="V", ammeter=None):
    """a source from ground up into an input, through an ammeter when the input current is read"""
    d.gate(label, node, dx, kind, ammeter, terminal=f"{n}.{pin}", name=f"{n}i")


def source_through(d, r, label, node="in", n="A", pin="+", rnode=None):
    """a source through a series resistor into an input"""
    d.add("% the input: the source resistance and the source", rf"\coordinate ({n}i) at ({n}.{pin});",
          rf"\draw ({n}i) -- ++(-0.3,0) coordinate ({n}ij) to[R, l_={{{r}}}] ++(-1.8,0) coordinate ({n}isrc);",
          rf"\draw[set] ({n}isrc) to[V, l_={{{label}}}] ({n}isrc |- 0,\gnd) node[ground, black]{{}};")
    d.nodename("south east", rf"$({n}isrc)+(-0.05,0.05)$", node)
    if rnode:
        d.nodename("south", rf"$({n}i)+(-0.15,0.05)$", rnode)


def pin_ground(d, n="A", pin="-", dx=-0.6):
    d.add(f"% the {'inverting' if pin == '-' else 'non-inverting'} input grounded",
          rf"\draw ({n}.{pin}) -- ++({dx},0) coordinate ({n}pg) -- ({n}pg |- 0,\gnd) node[ground]{{}};")
    d.nodename("south", rf"$({n}.{pin})+(-0.3,0.03)$", "0")


def load(d, n="A", rl="$R_L$", cl=None, vout="$v_{out}$", vdx=1.5, rdx=2.7, cdx=1.0):
    """at the output node: the voltmeter, then RL, then CL, each down to ground"""
    o = f"{n}o"
    if vout:
        voltmeter(d, o, vdx, vout, f"{n}vm")
    if rl:
        d.add("% the load", rf"\draw ({o}) -- ++({rdx},0) coordinate ({n}rl) to[R, l={{{rl}}}] ({n}rl |- 0,\gnd) node[ground]{{}};")
    if cl:
        frm = f"{n}rl" if rl else o
        d.add(rf"\draw ({frm}) -- ++({cdx},0) coordinate ({n}cl) to[C, l={{{cl}}}] ({n}cl |- 0,\gnd) node[ground]{{}};")


def shorted(d, n="A", label="$I_{SC}$", dx=1.5):
    """the output to ground through an ammeter"""
    d.add("% the output shorted to the reference through an ammeter", rf"\coordinate ({n}sc) at ($({n}o)+({dx},0)$);",
          rf"\draw ({n}o) -- ({n}sc);", rf"\ammeter{{{n}sc |- 0,\gnd}}{{{n}sc}}{{{label}}}", rf"\draw ({n}sc |- 0,\gnd) node[ground]{{}};")


def follower(name, title, header, src, defs, rl="$R_L$", cl=None, node="in", ammeter=None, fb_ammeter=None,
             vrails=RAILS, through=None, top=7.0):
    """the follower benches: a source into the non-inverting input, the output tied to the inverting one, the
    voltmeter and the load on the output"""
    d = D(name, title, header, top=top, twin=False)
    amp(d); rails(d, vp=vrails[0], vn=vrails[1]); output(d)
    feedback(d, ammeter=fb_ammeter, node=None)
    if through:
        source_through(d, through, src, node)
    else:
        source(d, src, node, ammeter=ammeter)
    load(d, rl=rl, cl=cl)
    d.definitions(defs)
    d.write()
    return d


# ------------------------------------------------------------------------ the drawings
FOLLOWER = """
VP vp 0 15, VN vn 0 -15     the rails                                          -> the supply pins (set)
VIN in 0 …                  the source on the non-inverting input               -> source (set)
X in out vp vn out DUT      the amplifier as a follower: in+, in-, V+, V-, out  -> op amp, output to the inverting input
RL out 0 2000               the load                                           -> resistor R_L
V(out) read                                                                    -> voltmeter v_out (measured)"""


def runs():
    follower("opamp-runs", "Operating point", FOLLOWER + "\nFive copies run in one deck, one per supply; the drawing shows one.",
             "$V_{in}$", [r"$V_+ = +15$ V, $V_- = -15$ V; also $\pm 5$, $\pm 2.5$, $\pm 9$ and $\pm 18$ V, one copy each;\quad $R_L = 2$ k\ohm;\quad $V_{in} = 0$",
                          r"read $v_{out}$, the output with the input at the reference, and the rails' currents: does the model load, and does the solver settle?"],
             vrails=("$V_+$", "$V_-$"))


def iq():
    d = D("opamp-iq", "Supply current", """
VP vp 0 0, .dc VP 2 20    the positive rail, swept; its current is the supply current   -> rail +V_S (set) + ammeter I_Q (measured)
EN vn 0 vp 0 -1           the negative rail mirrors the positive one                    -> rail -V_S (set)
VIN in 0 0, XQ in out vp vn out DUT   the follower, no load                             -> op amp
The turn-on deck ramps both rails from ±3 V to ±15 V; the temperature points come from the bias deck.""", top=8.4, twin=False)
    amp(d)
    d.add("% the positive supply pin through an ammeter, the negative one mirroring it",
          r"\draw (A.up) -- ++(0,0.25) coordinate (vpp);", r"\coordinate (vpt) at ($(vpp)+(0,1.5)$);", r"\ammeter{vpp}{vpt}{$I_Q$}",
          r"\draw[set, thick] (vpt) -- ++(0,0.3) coordinate (vpa);", r"\fill[set] (vpa) -- ++(-0.09,-0.18) -- ++(0.18,0) -- cycle;",
          r"\node[set, anchor=west, inner sep=2pt] at ($(vpa)+(0.05,-0.12)$) {$+V_S$};",
          r"\draw (A.down) -- ++(0,-0.25) coordinate (vnp);", r"\draw[set, thick] (vnp) -- ++(0,-0.3) coordinate (vna);",
          r"\fill[set] (vna) -- ++(-0.09,0.18) -- ++(0.18,0) -- cycle;",
          r"\node[set, anchor=west, inner sep=2pt] at ($(vna)+(0.05,0.12)$) {$-V_S$};")
    d.nodename("east", r"$(A.up)+(-0.08,0.2)$", "vp"); d.nodename("east", r"$(A.down)+(-0.08,-0.3)$", "vn")
    output(d); feedback(d, node=None); source(d, "$V_{in}$", "in")
    d.definitions([r"$V_S$ swept 2 to 20 V in 125 mV steps (4 to 40 V of total supply);\quad $V_{in} = 0$;\quad no load",
                   r"read $I_Q$, the positive rail's current, against the total supply;\quad at $-55$, 25 and 125 " + DEG + r"C from the bias deck",
                   r"turn-on: both rails ramped from $\pm 3$ V to $\pm 15$ V over 40 " + MU + r"s with $R_L = 2$ k\ohm; read $v_{out}(t)$ for when it settles within 10 mV"])
    d.write()


def offset():
    follower("opamp-offset", "Offset against common mode", FOLLOWER.replace("RL out 0 2000", "RL out 0 10000"),
             "$V_{in}$", [r"$V_{in}$ swept $-16$ to $+16$ V in 20 mV steps, 1 V beyond each rail;\quad $R_L = 10$ k\ohm",
                          r"read $v_{out}$: $V_{OS} = v_{out} - V_{in}$ against the common-mode voltage;\quad CMRR at DC from its slope;\quad the input range where the follower follows",
                          r"against supply and temperature: the supply-current and bias decks"])


def bias():
    follower("opamp-bias", "Bias and offset currents", """
VI in 0 0, VIP in inp 0       the input at the reference, through a 0 V source   -> source V_in (set) + ammeter I_B+ (measured)
VNN out inn 0                 the feedback through a 0 V source                  -> ammeter I_B- (measured)
XB inp inn vp vn out DUT, RL  the follower and its load                          -> op amp, resistor R_L
The impedance decks (both inputs driven together; one driven, the other held by the servo) are separate.""",
             "$V_{in}$", [r"$V_{in} = 0$, or $\pm 13$ V, or through $R_S = 10$ k\ohm;\quad $R_L = 2$ k\ohm;\quad $T = -55$, 25 and 125 " + DEG + "C",
                          r"read $I_{B+}$ and $I_{B-}$: $I_B$ their mean, $I_{OS}$ their difference;\quad $V_{OS}$ with and without $R_S$",
                          r"input impedance: both inputs driven together with 1 V of AC (common mode), or one input driven and the other held (differential), 1 kHz to 1 MHz"],
             ammeter="$I_{B+}$", fb_ammeter="$I_{B-}$")


def cmrr():
    d = D("opamp-cmrr-f", "CMRR against frequency", """
VCM0 vcm0 0 DC 0 AC 1              the common-mode source                      -> source V_CM + v_cm (set)
R1_0 vcm0 inn0, R2_0 inn0 out0     the inverting side: 10 kΩ in, 10 kΩ back     -> resistors R_1, R_2
R3_0 vcm0 inp0, R4_0 inp0 0        the non-inverting side: 10 kΩ in, 10 kΩ down -> resistors R_3, R_4
XC0 inp0 inn0 vp vn out0 DUT, RL0  the difference amplifier and its load       -> op amp, resistor R_L
Three copies run in one deck, one per DC common mode; the drawing shows one.""", top=8.6, twin=False)
    amp(d, inv_up=True); rails(d); output(d)
    feedback(d, y=6.6, element=("R", "$R_2$"), top=True)
    d.add("% the inputs: R3 into the non-inverting one with R4 to ground, R1 into the inverting one, from the common-mode source",
          r"\draw (A.+) -- ++(-0.5,0) coordinate (pj) to[R, l=$R_3$] ++(-1.8,0) coordinate (vcm);",
          r"\draw (pj) to[R, l_=$R_4$] (pj |- 0,\gnd) node[ground]{};",
          r"\draw (vcm) -- (vcm |- A.-) to[R, l=$R_1$] (Afu);",
          r"\draw[set] (vcm) to[V, l_={$V_{CM} + v_{cm}$}] (vcm |- 0,\gnd) node[ground, black]{};")
    d.nodename("south", r"$(pj)+(0.2,0.03)$", "inp"); d.nodename("south east", r"$(vcm)+(-0.05,0.05)$", "vcm")
    load(d)
    d.definitions([r"$R_1 = R_2 = R_3 = R_4 = 10$ k\ohm;\quad $R_L = 2$ k\ohm;\quad $V_{CM} = 0$, $-13$ and $+13$ V, one copy each;\quad $v_{cm} = 1$ V of AC",
                   r"read $v_{out}(f)$, $f = 1$ Hz to 10 MHz, 20 points per decade;\quad CMRR $= v_{cm} / v_{out}$ (the resistors matched, so the amplifier's own)",
                   r"at 10 Hz, 1 kHz, 10 kHz, 100 kHz and 1 MHz"])
    d.write()


def psrr():
    follower("opamp-psrr-f", "PSRR against frequency", FOLLOWER.replace("VP vp 0 15, VN vn 0 -15     the rails",
                                                                       "VP vp 0 DC 15 AC 1, VN vn 0 DC -15   the rails, 1 V of AC on one")
             + "\nThree decks drawn as one: the AC on the positive rail, on the negative, and on both in antiphase.",
             "$V_{in}$", [r"$V_{in} = 0$;\quad $R_L = 2$ k\ohm;\quad $v_s = 1$ V of AC on the positive rail; a second deck puts it on the negative rail, a third on both in antiphase",
                          r"read $v_{out}(f)$, $f = 1$ Hz to 10 MHz, 20 points per decade;\quad PSRR $= v_s / v_{out}$, at 10 Hz, 1 kHz, 10 kHz, 100 kHz and 1 MHz"],
             vrails=(r"$+15$ V $+ v_s$", r"$-15$ V"))


def emirr():
    follower("opamp-emirr", "EMI rejection", FOLLOWER.replace("VIN in 0 …", "VIN in 0 SIN(0 0.1 1e7)"),
             "$v_{in}$", [r"$v_{in}$: 100 mV peak at 10 MHz; then 100 MHz, 400 MHz and 1 GHz, one deck each;\quad $R_L = 2$ k\ohm",
                          r"read $v_{out}$ over two hundred cycles: the mean of the last hundred is the rectified offset;\quad EMIRR $= 20 \log$ of $v_{in}$ over that shift"])


def aol():
    d = D("opamp-aol", "Open-loop gain and phase", """
VIN inp 0 DC 0 AC 1     the AC source on the non-inverting input                       -> source v_in (set)
L1 out inn 1G           the loop: closed at DC through 1 GH, open above a microhertz    -> inductor L_1
C1 inn 0 1G             1 GF holds the inverting input                                  -> capacitor C_1
XA inp inn vp vn out DUT, RL out 0 2000, CL out 0 1e-10   the amplifier and its load    -> op amp, R_L, C_L
V(out) read                                                                             -> voltmeter v_out (measured)
One deck per variant (load, supply, temperature).""", twin=False)
    amp(d); rails(d); output(d); feedback(d, element=("L", "$L_1$"))
    d.add("% the capacitor from the inverting input's node to ground", r"\draw (Afl) to[C, l_=$C_1$] (Afl |- 0,\gnd) node[ground]{};")
    source(d, "$v_{in}$", "inp", dx=-2.0); load(d, cl="$C_L$")
    d.definitions([r"$L_1 = 1$ GH, $C_1 = 1$ GF: the loop closed at DC, open above a microhertz;\quad $v_{in} = 1$ V of AC;\quad $R_L = 2$ k\ohm, $C_L = 100$ pF",
                   r"read $v_{out}(f) / v_{in}$, $f = 1$ Hz to 100 MHz, 20 points per decade: $A_{OL}$ and its phase;\quad GBW at 10 and 100 kHz;\quad $f_{unity}$, the phase and gain margins, the poles",
                   r"variants: $R_L = 600$ \ohm{} and 10 k\ohm;\quad $\pm 5$ and $\pm 9$ V;\quad $-55$ and 125 " + DEG + "C, one deck each"])
    d.write()


def aol_swing():
    d = D("opamp-aol-swing", "Open-loop gain against swing", """
VIN inb 0 0, .dc          the input sweep                                               -> source V_in (set)
VOFF inp inb <vos>        riding on the model's own offset, from the runs deck          -> source V_OFF (set)
XL0 inp 0 vp vn out0 DUT  the amplifier open loop, inverting input grounded             -> op amp
RL0 out0 0 2000           the load; XL1 and XL2 into 600 Ω and 10 kΩ                   -> resistor R_L
Three copies run in one deck, one per load; the drawing shows one.""", twin=False)
    amp(d); rails(d); output(d); pin_ground(d)
    d.add("% the non-inverting input: the sweep riding on the offset", r"\coordinate (Ai) at (A.+);",
          r"\coordinate (Aisrc) at ($(Ai)+(-1.5,0)$);", r"\draw (Ai) -- (Aisrc);",
          r"\draw[set] (Aisrc) to[V, l_={$V_{in}$}] ++(0,-1.3) coordinate (inb);",
          r"\draw[set] (inb) to[V, l_={$V_{OFF}$}] (inb |- 0,\gnd) node[ground, black]{};")
    d.nodename("south", r"$(Ai)+(-0.45,0.02)$", "inp"); d.nodename("east", r"$(inb)+(-0.05,0)$", "inb")
    load(d)
    d.definitions([r"$V_{OFF}$: the offset the runs deck found, so that the sweep is centred on the model's own zero;\quad $V_{in}$ swept $\pm 300$ " + MU + r"V in 250 nV steps",
                   r"$R_L = 2$ k\ohm, 600 \ohm{} and 10 k\ohm, one copy each;\quad read $v_{out}(V_{in})$: $A_{OL}$ as the slope over $\pm 10$ V and $\pm 13$ V of swing"])
    d.write()


def closed_loop():
    d = D("opamp-closed-loop", "Closed-loop gain", """
VIN in 0 DC 0 AC 1                     the AC source, shared by the copies                  -> source v_in (set)
R1_1 inn1 0 1000, R2_1 out1 inn1 9000  the feedback network of the G = 10 copy              -> resistors R_1, R_2
XG1 in inn1 vp vn out1 DUT, RL1, CL1   the amplifier and its load                           -> op amp, R_L, C_L
Five copies run in one deck (G = 1, 10, 100, 1000 and the inverter at -1); the drawing shows one.""", twin=False)
    amp(d); rails(d); output(d); feedback(d, element=("R", "$R_2$"))
    d.add("% R1 from the inverting input's node to ground",
          r"\draw (Afu) -- ++(-0.9,0) coordinate (r1) to[R, l_=$R_1$] (r1 |- 0,\gnd) node[ground]{};")
    source(d, "$v_{in}$", "in", dx=-2.8); load(d, cl="$C_L$")
    d.definitions([r"$G = 1 + R_2 / R_1 = 1$ (the follower), 10, 100 and 1000 with $R_1 = 1$ k\ohm, one copy each;\quad the inverter at $G = -1$ with 10 k\ohm{} and 10 k\ohm",
                   r"$v_{in} = 1$ V of AC;\quad $R_L = 2$ k\ohm, $C_L = 100$ pF;\quad read $v_{out}(f) / v_{in}$, $f = 10$ Hz to 100 MHz: the $-3$ dB bandwidth and the peaking at each gain"])
    d.write()


def stability():
    d = D("opamp-stability", "Stability", """
R1_0 inn0 0 1, R2_0 out0 inn0 99    the G = 100 copy with RT = R1 || R2 = 1 Ω; RT = 100 Ω, 1 kΩ, 10 kΩ follow   -> resistors R_1, R_2
XT0 in inn0 vp vn out0 DUT, RL0, CL0   the amplifier and its load                                              -> op amp, R_L, C_L
VIN in 0 PULSE(0 0.1 …), XS, CL     the overshoot deck: a 100 mV step into the follower with 100 pF, then 1 nF   -> the follower drawing
The open-loop deck per capacitive load is the open-loop gain circuit; several decks drawn as one.""", twin=False)
    amp(d); rails(d); output(d); feedback(d, element=("R", "$R_2$"))
    d.add("% R1 from the inverting input's node to ground",
          r"\draw (Afu) -- ++(-0.9,0) coordinate (r1) to[R, l_=$R_1$] (r1 |- 0,\gnd) node[ground]{};")
    source(d, "$v_{in}$", "in", dx=-2.8); load(d, cl="$C_L$")
    d.definitions([r"$G = 100$: $R_2 = 99\,R_1$ with $R_1 = 1$ \ohm, 10 \ohm, 100 \ohm{} and 1 k\ohm, one copy each, so that $R_T = R_1 \| R_2 = 1$ \ohm{} to 1 k\ohm{} loads the inverting input",
                   r"$v_{in} = 1$ V of AC;\quad $R_L = 2$ k\ohm, $C_L = 100$ pF;\quad read $v_{out}(f) / v_{in}$, 10 Hz to 100 MHz: the peaking against $R_T$",
                   r"the open-loop circuit with $C_L = 10$ pF, 1 nF and 10 nF: the phase margin against capacitive load",
                   r"the follower with a 100 mV step into $C_L = 100$ pF and 1 nF: the overshoot"])
    d.write()


def swing():
    d = D("opamp-swing", "Output swing", """
VIp0 ip0 0 1, XSp0 ip0 0 vp vn op0 DUT, RLp0   copy A: +1 V between the inputs, open loop, into the load   -> op amp saturated high
VIn0 in0 0 -1, XSn0, RLn0                      a copy driven negative beside it                           -> the same, low
VIsp isp 0 1, XIp isp 0 vp vn osp DUT, VSCp osp 0 0   copy B: the output to the reference through a 0 V source   -> ammeter I_SC (measured)
IL op 0 0, .dc IL 0 0.08                       the current sweep: the saturated amplifier into a current sink
The copies run in one deck; the drawing shows one per kind.""", twin=False)
    amp(d, "A"); rails(d, "A"); output(d, "A"); pin_ground(d, "A")
    source(d, "$V_{in}$", "ip0", "A"); load(d, "A", vout="$V_{out}$")
    amp(d, "B", x=12.5); rails(d, "B"); output(d, "B", node="osp"); pin_ground(d, "B")
    source(d, "$V_{in}$", "isp", "B"); shorted(d, "B")
    d.definitions([r"A: $V_{in} = +1$ V and $-1$ V between the inputs, one copy each: the amplifier saturated;\quad $R_L = 2$ k\ohm, 600 \ohm{} and 10 k\ohm, one pair each",
                   r"read $V_{out}$: $V_{OM}$ high and low, and the headroom to each rail;\quad also at $\pm 5$ and $\pm 9$ V, and at $-55$ and 125 " + DEG + "C",
                   r"B: the output shorted to the reference;\quad read $I_{SC}$ sourcing and sinking",
                   r"the swing against current: the saturated amplifier into a current sink, 0 to 80 mA in 1 mA steps, a second deck"])
    d.write()


def isc():
    d = D("opamp-isc", "Short-circuit current", """
VIsp isp 0 1, XIp isp 0 vp vn osp DUT   +1 V between the inputs: the amplifier saturated high   -> op amp
VSCp osp 0 0                            the output to the reference through a 0 V source        -> ammeter I_SC (measured)
VIsn, XIn, VSCn                         the same driven negative, sinking                      -> a second copy
The swing deck's shorted copies.""", twin=False)
    amp(d); rails(d); output(d, node="osp"); pin_ground(d); source(d, "$V_{in}$", "isp"); shorted(d)
    d.definitions([r"$V_{in} = +1$ V (sourcing) and $-1$ V (sinking) between the inputs, one copy each;\quad the output at the reference",
                   r"read $I_{SC}$"])
    d.write()


def zout():
    d = D("opamp-zout", "Output impedance", """
L1 out inn 1G, C1 inn 0 1G     the servo: the loop closed at DC, open above a microhertz   -> inductor L_1, capacitor C_1
XZO inp inn vp vn out DUT      the amplifier, non-inverting input at the reference         -> op amp
IINJ 0 out AC 1                1 A of AC injected into the output                          -> current source i_inj (set)
V(out) read                    the output's voltage: Z_out = v_out / i_inj                 -> voltmeter v_out (measured)
The four closed-loop copies (G = 1, 10, 100, 1000, each with its own injection) run in a second deck.""", twin=False)
    amp(d); rails(d); output(d); feedback(d, element=("L", "$L_1$"))
    d.add("% the capacitor from the inverting input's node to ground", r"\draw (Afl) to[C, l_=$C_1$] (Afl |- 0,\gnd) node[ground]{};")
    pin_ground(d, pin="+", dx=-1.5)
    d.add("% the current injected into the output, from ground", r"\coordinate (inj) at ($(Ao)+(2.9,0)$);", r"\draw (Ao) -- (inj);",
          r"\draw[set] (inj |- 0,\gnd) node[ground, black]{} to[I, l_=$i_{inj}$] (inj);")
    load(d, rl=None, vdx=1.5)
    d.definitions([r"$L_1 = 1$ GH, $C_1 = 1$ GF;\quad $i_{inj} = 1$ A of AC, the simulator's unit signal;\quad no load",
                   r"read $v_{out}(f)$, $f = 10$ Hz to 100 MHz: $Z_{out} = v_{out} / i_{inj}$, open loop;\quad at 1 kHz, 1 MHz and 9 MHz",
                   r"closed loop: the follower and the non-inverting amplifier at $G = 10$, 100 and 1000 ($R_1 = 1$ k\ohm), the injection on each output, a second deck;\quad at 1 kHz and 100 kHz"])
    d.write()


def max_vo():
    follower("opamp-max-vo-f", "Maximum output against frequency", FOLLOWER.replace("VIN in 0 …", "VIN in 0 SIN(0 10 20000)"),
             "$v_{in}$", [r"$v_{in}$: 10 V peak at 20 kHz; then 50 and 100 kHz, one deck each;\quad $R_L = 2$ k\ohm",
                          r"read $v_{out}$ over twelve cycles, the last eight analysed: the peak the output reaches, and whether the sine is still a sine"])


SLEW = FOLLOWER.replace("VIN in 0 …", "VIN in 0 PULSE(-5 5 …)").replace("RL out 0 2000               the load", "RL out 0 2000, CL out 0 1e-10   the load")


def slew():
    follower("opamp-slew", "Slew rate and large-signal step", SLEW + "\nOne deck per fixture; the inverter (10 kΩ and 10 kΩ) is one of them.",
             "$V_{in}$", [r"$V_{in}$: a 10 V step, $-5$ to $+5$ V at 1 " + MU + r"s, 10 ns edges, 40 " + MU + r"s wide;\quad $R_L = 2$ k\ohm, $C_L = 100$ pF",
                          r"read $v_{out}(t)$: the slew rate, rising and falling, between the 10\,\% and 90\,\% levels",
                          r"fixtures: 2 V and 20 V steps;\quad $C_L = 20$ pF;\quad the inverter at $G = -1$;\quad a 4 V step at $\pm 5$ V;\quad 125 " + DEG + "C"],
             cl="$C_L$")


def settling():
    follower("opamp-settling", "Settling time", SLEW + "\nThe slew fixtures with a finer time step; one deck per fixture.",
             "$V_{in}$", [r"$V_{in}$: a 10 V step (also 2 V, and 10 V into the inverter at $G = -1$), 10 ns edges;\quad $R_L = 2$ k\ohm, $C_L = 100$ pF",
                          r"read $v_{out}(t)$: the time from the step to the last excursion beyond 0.1\,\% and 0.01\,\% of the step"],
             cl="$C_L$")


def overload():
    d = D("opamp-overload", "Overload recovery", """
VIN in 0 PULSE(0 1.8 …), R1 in inn 1000   the pulse through 1 kΩ into the inverting input   -> source V_in (set) + resistor R_1
R2 out inn 10000                           the feedback                                    -> resistor R_2
XS 0 inn vp vn out DUT, RL out 0 2000      the inverter at G = -10, non-inverting input grounded   -> op amp, resistor R_L
V(out) read                                                                                -> voltmeter v_out (measured)
One deck per polarity.""", top=8.6, twin=False)
    amp(d, inv_up=True); rails(d); output(d); feedback(d, y=6.6, element=("R", "$R_2$"), top=True)
    d.add("% the inverting input: R1 from the pulse source", r"\draw (Afu) to[R, l=$R_1$] ++(-1.8,0) coordinate (vin);",
          r"\draw[set] (vin) to[V, l_=$V_{in}$] (vin |- 0,\gnd) node[ground, black]{};")
    d.nodename("south east", r"$(vin)+(-0.05,0.05)$", "in")
    pin_ground(d, pin="+"); load(d)
    d.definitions([r"$R_1 = 1$ k\ohm, $R_2 = 10$ k\ohm: $G = -10$;\quad $V_{in}$: a 1.8 V pulse at 1 " + MU + r"s, 10 ns edges, 20 " + MU + r"s wide: 18 V demanded of the output, one deck per polarity;\quad $R_L = 2$ k\ohm",
                   r"read $v_{out}(t)$: the time from the pulse's end to the output back within 100 mV of its rest"])
    d.write()


def phase_reversal():
    follower("opamp-phase-reversal", "Phase reversal", FOLLOWER.replace("VIN in 0 …", "VIN in 0 0, VIM in inp 0").replace(
        "the source on the non-inverting input               -> source (set)", "the swept source, through a 0 V source   -> source V_in (set) + ammeter I_in (measured)")
             .replace("RL out 0 2000", "RL out 0 10000"),
             "$V_{in}$", [r"$V_{in}$ swept $-17$ to $+17$ V in 0.1 V steps, 2 V beyond each rail;\quad $R_L = 10$ k\ohm",
                          r"read $v_{out}$ and $I_{in}$: whether the output reverses beyond the common-mode range, and the input current at $-16$, 14 and 16 V (the input protection)"],
             ammeter="$I_{in}$")


def step():
    follower("opamp-step", "Small-signal step", FOLLOWER.replace("VIN in 0 …", "VIN in 0 PULSE(0 0.01 …)").replace(
        "RL out 0 2000               the load", "RL out 0 2000, CL out 0 2e-11   the load"),
             "$V_{in}$", [r"$V_{in}$: a 10 mV step at 100 ns, 1 ns edges;\quad $R_L = 2$ k\ohm;\quad $C_L = 20$ pF, then 100 pF, one deck each",
                          r"read $v_{out}(t)$: rise time, overshoot and ringing"], cl="$C_L$")


NOISE = """
VP vp 0 15, VN vn 0 -15      the rails                                       -> the supply pins (set)
VIN in 0 DC 0 AC 1           the noise input on the non-inverting input       -> source v_in (set)
RS in inr <rs>               the source resistance (0 in the first deck)      -> resistor R_S
XN inr out vp vn out DUT     the follower                                    -> op amp, output to the inverting input
RL out 0 2000                the load                                        -> resistor R_L
.noise V(out) VIN            the output noise, referred to v_in              -> voltmeter v_out (measured)"""


def noise():
    follower("opamp-noise", "Noise", NOISE, "$v_{in}$",
             [r"$R_S = 0$ gives $e_n$;\quad $R_S = 100$ k\ohm{} gives $e_n^2 + i_n^2 R_S^2 + 4kTR_S$, from which $i_n$;\quad $R_L = 2$ k\ohm",
              r"$f = 0.1$ Hz to 1 MHz, 20 points per decade;\quad read the noise of $v_{out}$ referred to $v_{in}$: $e_n$ and $i_n$ at 10 Hz, 100 Hz, 1 kHz and 10 kHz, the $1/f$ corner",
              r"integrated 0.1 to 10 Hz (peak to peak), 10 Hz to 10 kHz and 20 Hz to 20 kHz;\quad also at $\pm 5$ V"], through="$R_S$")


def noise_rs():
    follower("opamp-noise-rs", "Noise against source resistance", NOISE, "$v_{in}$",
             [r"$R_S = 1$ k\ohm, 10 k\ohm, 100 k\ohm{} and 1 M\ohm, one deck each; 300 \ohm{} and 2.2 k\ohm{} for the weighted figures;\quad $R_L = 2$ k\ohm",
              r"read the noise of $v_{out}$ referred to $v_{in}$ at 1 kHz: the total noise and NF against $R_S$;\quad A-weighted and RIAA-weighted over 10 Hz to 100 kHz"],
             through="$R_S$")


THD = FOLLOWER.replace("VIN in 0 …", "VIN in 0 SIN(…)")


def thd_f():
    follower("opamp-thd-f", "THD against frequency", THD + "\nOne deck per frequency, level and gain; the non-inverting amplifier at G = 10 is the closed-loop circuit.",
             "$v_{in}$", [r"$v_{in}$: 1 Vrms (also 3 Vrms) at 20 Hz, 100 Hz, 1 kHz, 10 kHz and 20 kHz, one deck each;\quad $R_L = 2$ k\ohm;\quad also at $G = 10$ ($R_1 = 1$ k\ohm)",
                          r"read $v_{out}$ over twelve cycles, the last eight analysed: THD, HD2, HD3 by Goertzel (model against model only)"])


def thd_level():
    follower("opamp-thd-level", "THD against level", THD + "\nOne deck per level.",
             "$v_{in}$", [r"$v_{in}$: 100 mVrms, 1, 3, 6 and 10 Vrms at 1 kHz, one deck each;\quad $R_L = 2$ k\ohm",
                          r"read $v_{out}$ over twelve cycles, the last eight analysed: THD, HD2, HD3 by Goertzel (model against model only)"])


def thd_load():
    follower("opamp-thd-load", "THD against load", THD.replace("RL out 0 2000", "RL out 0 100  ") + "\nOne deck per load.",
             "$v_{in}$", [r"$v_{in}$: 3 Vrms at 1 kHz;\quad $R_L = 100$ \ohm, 300 \ohm, 600 \ohm, 2 k\ohm{} and 10 k\ohm, one deck each",
                          r"read $v_{out}$ over twelve cycles, the last eight analysed: THD, HD2, HD3 by Goertzel (model against model only)"])


def imd():
    d = D("opamp-imd", "Intermodulation", """
VIN in mid SIN(0 3.394 60), VIN2 mid 0 SIN(0 0.8485 7000)   two sine sources in series on the input   -> sources v_1, v_2 (set)
XD in out vp vn out DUT, RL out 0 2000                      the follower and its load                 -> op amp, resistor R_L
V(out) read                                                                                           -> voltmeter v_out (measured)
One deck per method (SMPTE, CCIF).""", twin=False)
    amp(d); rails(d); output(d); feedback(d, node=None)
    d.add("% the input: two sources in series", r"\coordinate (Ai) at (A.+);", r"\coordinate (Aisrc) at ($(Ai)+(-1.5,0)$);",
          r"\draw (Ai) -- (Aisrc);", r"\draw[set] (Aisrc) to[V, l_=$v_1$] ++(0,-1.3) coordinate (mid);",
          r"\draw[set] (mid) to[V, l_=$v_2$] (mid |- 0,\gnd) node[ground, black]{};")
    d.nodename("south", r"$(Ai)+(-0.45,0.02)$", "in"); d.nodename("east", r"$(mid)+(-0.05,0)$", "mid")
    load(d)
    d.definitions([r"SMPTE: $v_1 = 60$ Hz at 3.394 V peak, $v_2 = 7$ kHz at 0.8485 V peak (four to one);\quad CCIF: 19 and 20 kHz at 2.1213 V peak each;\quad $R_L = 2$ k\ohm",
                   r"read $v_{out}$ over the settled part of the run: the intermodulation products by Goertzel (model against model only)"])
    d.write()


def main():
    for f in (runs, iq, offset, bias, cmrr, psrr, emirr, aol, aol_swing, closed_loop, stability, swing, isc, zout, max_vo, slew,
              settling, overload, phase_reversal, step, noise, noise_rs, thd_f, thd_level, imd, thd_load):
        f()
    print("26 op-amp drawings written")
