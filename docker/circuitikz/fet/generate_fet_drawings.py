"""Writes docker/circuitikz/fet/<id>.tex for every field-effect bench drawing (docs/fet-bench-drawings.md): a
proposal in its own style, to be folded into benches.py and bench.sty with the bipolar drawings once the
measurements enter data/bench/measurements.yaml. Run from the repository root; `pdflatex` then `pdftocairo -svg`
(the circuitikz image) renders each into data/bench/drawings/<id>.svg."""
import os

OUT = "docker/circuitikz/fet"
PRE = r"""\documentclass[border=8pt]{standalone}
\usepackage[siunitx,RPvoltages,european]{circuitikz}
\ctikzset{bipoles/length=0.9cm, label/align=straight, inductors/scale=0.8}
\ctikzset{inductor=american}
\usepackage{amsmath}
\begin{document}
\begin{circuitikz}[font=\footnotesize, line width=0.5pt]
"""
POST = r"""\end{circuitikz}
\end{document}
"""

import re


def brace_labels(body):
    res=''; i=0
    while True:
        j=body.find('to[', i)
        if j<0: res+=body[i:]; break
        res+=body[i:j+3]; k=j+3; depth=1
        while depth>0:
            c=body[k]
            if c=='[': depth+=1
            elif c==']': depth-=1
            k+=1
        opts=body[j+3:k-1]
        m=re.match(r'^(.*?)(\bl_?=)(.*?)(, invert)?$', opts, re.S)
        if m and not m.group(3).startswith('{'):
            lab=m.group(3)
            if '\\\\' in lab:
                side='[r]' if m.group(2)=='l_=' else '[l]'
                lab='\\shortstack'+side+'{'+lab+'}'
            opts=m.group(1)+m.group(2)+'{'+lab+'}'+(m.group(4) or '')
        res+=opts+']'
        i=k
    return res

def write(mid, deck_lines, body, title=None):
    body = brace_labels(body)
    hdr = "%% Drawing for measurement `%s`\n%% Stands for the deck lines:\n" % mid
    hdr += "".join("%%   %s\n" % l for l in deck_lines)
    with open(os.path.join(OUT, mid + ".tex"), "w") as f:
        f.write(hdr + PRE + body + POST)

def dut(kind, at="(0,0)", name="Q"):
    sym = "njfet" if kind == "jfet" else "nmos"
    s = r"\draw %s node[%s](%s){};" % (at, sym, name) + "\n"
    s += r"\node[anchor=west] at ($(%s.D)!0.5!(%s.S) + (0.55,0)$) {DUT};" % (name, name) + "\n"
    return s

# anchors: Q.D top, Q.S bottom, Q.G left (circuitikz: D is top for n-devices)
def thermo(x, y, text):
    return r"\node[draw, rounded corners, inner sep=3pt] at (%g,%g) {\textbf{T} %s};" % (x, y, text) + "\n"

def note(x, y, text, anchor="west"):
    return r"\node[anchor=%s, align=left] at (%g,%g) {%s};" % (anchor, x, y, text) + "\n"

# --- Topology A: gate voltage source (left), drain supply (right), ammeter in drain
def topoA(kind, gate_lbl, drain_lbl, gate_meter=False, drain_meter=True, gate_kind="V", drain_kind="V",
          swept_gate=False, swept_drain=False, extra="", name="Q", origin=(0,0), vm_gs=False, show_ds=True):
    ox, oy = origin
    s = dut(kind, "(%g,%g)" % (ox, oy), name)
    s += r"\draw (%s.S) to[short] ++(0,-0.5) node[ground]{};" % name + "\n"
    # drain
    dm = "to[rmeter, t=A, l=$I_D$] ++(0,1.4)" if drain_meter else "to[short] ++(0,1.4)"
    dsrc = {"V": "vsource", "Vac": "vsourcesin", "Vsq": "vsourcesquare"}[drain_kind]
    s += r"\draw (%s.D) to[short] ++(0,0.3) %s to[short] ++(2.0,0) to[%s, l=%s, invert] ++(0,-2.4) node[ground]{};" % (
        name, dm, dsrc, drain_lbl) + "\n"
    if swept_drain:
        s += note(ox+2.3, oy+2.1, r"$\rightarrow$ swept")
    # gate
    gm = "to[rmeter, t=A, l=$I_G$] ++(-1.4,0)" if gate_meter else "to[short] ++(-1.4,0)"
    gsrc = {"V": "vsource", "Vac": "vsourcesin", "Vsq": "vsourcesquare", "I": "isource"}[gate_kind]
    s += r"\draw (%s.G) to[short] ++(-0.5,0) %s to[short] ++(-0.5,0) coordinate(gl) to[%s, l_=%s, invert] ++(0,-1.9) node[ground]{};" % (
        name, gm, gsrc, gate_lbl) + "\n"
    if swept_gate:
        s += note(ox-4.6, oy+0.5, r"$\rightarrow$ swept", anchor="east")
    s += extra
    return s

J = "jfet"; M = "mos"

# ---------------- JFET ----------------
write("jfet-runs", ["VD d 0 10", "VG g 0 0", "J1 d g 0 DUT", ".op"],
      topoA(J, r"$V_{GS}=0$", r"$V_{DS}=\SI{10}{V}$", gate_meter=True))

write("jfet-tracer", ["VK1 sw dk1 0", "VGK1 gk1 0 {-k*step}", "JK1 dk1 gk1 0 DUT", "VSW sw 0 0", ".dc VSW 0 25 0.02"],
      topoA(J, r"$V_{GS}=-k\cdot\text{step}$\\ $k=0\dots5$", r"$V_{DS}$ $0\to\SI{25}{V}$", swept_drain=True)
      + note(-4.6, -3.6, r"one copy per step; drawn as one\\ step: auto ($V_{GS(\mathrm{off})}/5$) or 0.05\dots\SI{3}{V}", anchor="west"))

write("jfet-transfer", ["VT1 dt1 0 10", "VGS g 0 0", "JT1 dt1 g 0 DUT", ".dc VGS -10 0.6 0.005"],
      topoA(J, r"$V_{GS}$ $-10\to+\SI{0.6}{V}$", r"$V_{DS}$ 5, 10,\\ 15, \SI{20}{V}", gate_meter=True, swept_gate=True)
      + note(-4.6, -3.6, r"four copies, one per $V_{DS}$; drawn as one", anchor="west"))

gm_body = topoA(J, r"$V_{GS}$ bias\\ $+\SI{1}{V}$ AC", r"$V_{DS}=\SI{10}{V}$", gate_kind="Vac", name="Q")
gm_body += topoA(J, r"$V_{GS}$ bias", r"$V_{DS}=\SI{10}{V}$\\ $+\SI{1}{V}$ AC", drain_kind="Vac", name="R", origin=(8,0))
gm_body += note(-4.6, -3.6, r"copy A ($g_{fs}$): AC on the gate, $i_d$ read\\ copy B ($g_{os}$): AC on the drain, gate held\\ one pair per ladder current; read at \SI{1}{kHz}", anchor="west")
write("jfet-gm", ["VD0 d0 0 10", "VG0 g0 0 DC {vgs} AC 1", "JM0 d0 g0 0 DUT", "VDO0 do0 0 DC 10 AC 1", ".ac dec 10 100 10000"], gm_body)

ohm = dut(J, "(0,0)", "Q")
ohm += r"\draw (Q.S) to[short] ++(0,-0.5) node[ground]{};" + "\n"
ohm += r"\draw (Q.D) to[short] ++(0,0.3) to[rmeter, t=A, l=$I_D$] ++(0,1.4) to[short] ++(2,0) to[vsource, l=$V_{DS}=\pm\SI{50}{mV}$\\ (or $\pm\SI{0.5}{V}$ swept), invert] ++(0,-2.4) node[ground]{};" + "\n"
ohm += r"\draw (Q.G) to[short] ++(-1.9,0) to[vsource, l_=$V_{GS}$ stepped\\ $0\to V_{GS(\mathrm{off})}$, invert] ++(0,-1.9) node[ground]{};" + "\n"
# feedback copy
ohm += dut(J, "(8,0)", "R")
ohm += r"\draw (R.S) to[short] ++(0,-0.5) node[ground]{};" + "\n"
ohm += r"\draw (R.D) to[short] ++(0,0.3) coordinate(rd) to[rmeter, t=A, l=$I_D$] ++(0,1.4) to[short] ++(2,0) to[vsource, l=$V_{DS}$ swept $\pm\SI{0.5}{V}$, invert] ++(0,-2.4) node[ground]{};" + "\n"
ohm += r"\draw (R.G) to[short] ++(-0.6,0) coordinate(rg) to[R, l_=\SI{1}{M\ohm}] ++(-1.8,0) to[vsource, l_=$V_{GS}$ bias, invert] ++(0,-1.9) node[ground]{};" + "\n"
ohm += r"\draw (rg) to[R, l=\SI{1}{M\ohm}] ++(0,1.3) -| (rd);" + "\n"
ohm += note(-4.6, -3.6, r"left: $r_{DS}$ against $V_{GS}$ and linearity\\ right: the same with $V_{DS}/2$ fed back to the gate", anchor="west")
write("jfet-ohmic", ["VDR dr 0 0.05", "VGR gr 0 {vgs}", "JR dr gr 0 DUT", "RF1 dl gl 1e6", "RF2 gb gl 1e6"], ohm)

gate = dut(J, "(0,0)", "Q")
gate += r"\draw (Q.S) to[short] ++(0,-0.5) node[ground]{};" + "\n"
gate += r"\draw (Q.D) to[short] ++(0,0.4) to[short] ++(0,0.3) node[ground, rotate=180]{};" + "\n"
gate += r"\draw (Q.G) to[short] ++(-0.5,0) to[rmeter, t=A, l=$I_G$] ++(-1.4,0) to[short] ++(-0.5,0) to[vsource, l_=$V_{GS}$ swept\\ $0\to+\SI{0.9}{V}$ (forward)\\ $0\to-\SI{40}{V}$ (reverse), invert] ++(0,-1.9) node[ground]{};" + "\n"
gate += note(-4.6, 0.9, r"$\rightarrow$ swept", anchor="east")
gate += dut(J, "(8,0)", "R")
gate += r"\draw (R.S) to[short] ++(0,-0.5) node[ground]{};" + "\n"
gate += r"\draw (R.D) to[short] ++(0,0.3) to[rmeter, t=A, l=$I_D$] ++(0,1.4) to[short] ++(2,0) to[vsource, l=$V_{DS}$ $0\to\SI{25}{V}$, invert] ++(0,-2.4) node[ground]{};" + "\n"
gate += r"\draw (R.G) to[short] ++(-0.5,0) to[rmeter, t=A, l=$I_G$] ++(-1.4,0) to[short] ++(-0.5,0) to[vsource, l_=$V_{GS}$ bias\\ for $I_D$ 0.1\dots\SI{10}{mA}, invert] ++(0,-1.9) node[ground]{};" + "\n"
gate += note(-4.6, -3.6, r"left: the gate diode, drain and source grounded\\ right: $I_G$ against $V_{DG}$ at fixed drain current", anchor="west")
write("jfet-gate", ["VGF gf 0 0 / .dc VGF 0 0.9 0.005", "JF 0 gf 0 DUT", "VDF df 0 0 / .dc VDF 0 25 0.1", "VGB gb 0 {vgs}", "JD df gb 0 DUT"], gate)

def cap_copy(kind, at, name, drive_on, held, open_term, lbl_v):
    # drive_on: 'G' or 'D'; held: dict of terminal->label for DC; open_term: 'S' etc with 1 GOhm
    x,y = at
    s = dut(kind, "(%g,%g)" % (x,y), name)
    # source
    if open_term == "S":
        s += r"\draw (%s.S) to[R, l_=\SI{1}{G\ohm}] ++(0,-1.6) node[ground]{};" % name + "\n"
    else:
        s += r"\draw (%s.S) to[short] ++(0,-0.5) node[ground]{};" % name + "\n"
    # drain
    if drive_on == "D":
        s += r"\draw (%s.D) to[short] ++(0,0.3) to[rmeter, t=A, l=$i$] ++(0,1.3) to[short] ++(1.8,0) to[vsourcesin, l=%s\\ $+\SI{1}{V}$ AC, invert] ++(0,-2.3) node[ground]{};" % (name, lbl_v) + "\n"
        s += r"\draw (%s.G) to[short] ++(-0.8,0) node[ground]{};" % name + "\n"
    elif drive_on == "G":
        if open_term == "D":
            s += r"\draw (%s.D) to[short] ++(0,0.3) to[R, l=\SI{1}{G\ohm}] ++(0,1.4) node[ground, rotate=180]{};" % name + "\n"
        elif held.get("D") == "tie":
            s += r"\draw (%s.D) to[short] ++(0,0.3) to[short] ++(1.6,0) |- ($(%s.S)+(0,-0.3)$);" % (name, name) + "\n"
        else:
            s += r"\draw (%s.D) to[short] ++(0,0.3) to[rmeter, t=A, l=$i_d$] ++(0,1.3) to[short] ++(1.8,0) to[vsource, l=%s, invert] ++(0,-2.3) node[ground]{};" % (name, held["D"]) + "\n"
        s += r"\draw (%s.G) to[short] ++(-0.5,0) to[rmeter, t=A, l=$i_g$] ++(-1.4,0) to[short] ++(-0.4,0) to[vsourcesin, l_=%s\\ $+\SI{1}{V}$ AC, invert] ++(0,-1.9) node[ground]{};" % (name, lbl_v) + "\n"
    return s

jc = cap_copy(J, (0,0), "A", "G", {"D":"tie"}, None, r"$-V_R$")
jc += note(0.3, 3.3, r"$C_{iss}$: drain tied to source", anchor="west")
jc += cap_copy(J, (8,0), "B", "G", {"D": r"$V_{DS}=V_R$"}, None, r"$V_{GS}=0$")
jc += note(8.3, 3.3, r"$C_{rss}$: $i_d/\omega$", anchor="west")
jc += cap_copy(J, (16,0), "C", "G", {}, "D", r"$-V_R$")
jc += note(16.3, 3.3, r"$C_{gs}$: drain open ($C_{gd}$: source open)", anchor="west")
jc += note(-4.6, -3.6, r"one set per reverse voltage 0.1\dots\SI{30}{V}; $C=\mathrm{Im}(i)/2\pi f$ at \SI{1}{MHz}, series-equivalent", anchor="west")
write("jfet-capacitance", ["VGC gc 0 DC {-v} AC 1", "JC 0 gc 0 DUT", "VDX dx 0 {v} / VGX gx 0 AC 1 / JX dx gx 0 DUT", "RGD gd 0 1e9"], jc)

def cs_stage(kind, at, name, vdd, rd, rs, bypass, rin, out="drain", load=None, sink=None):
    x,y = at
    s = dut(kind, "(%g,%g)" % (x,y), name)
    if sink and rs:
        s += r"\draw (%s.S) to[short] ++(0,-0.3) coordinate(%ss) to[R, l_=%s] ++(0,-1.3) coordinate(%sx) to[isource, l_=%s] ++(0,-1.5) to[short] ++(0,-0.2) node[vee]{};" % (name, name, rs, name, sink) + "\n"
        if bypass:
            s += r"\draw (%sx) to[short] ++(1.2,0) to[C, l=%s] ++(0,-1.5) node[ground]{};" % (name, bypass) + "\n"
    elif sink:
        s += r"\draw (%s.S) to[short] ++(0,-0.3) coordinate(%ss) to[isource, l_=%s] ++(0,-1.6) to[short] ++(0,-0.3) node[vee]{};" % (name, name, sink) + "\n"
    elif rs:
        s += r"\draw (%s.S) to[short] ++(0,-0.3) coordinate(%ss) to[R, l_=%s] ++(0,-1.6) node[ground]{};" % (name, name, rs) + "\n"
        if bypass:
            s += r"\draw (%ss) to[short] ++(1.2,0) to[C, l=%s] ++(0,-1.6) node[ground]{};" % (name, bypass) + "\n"
    if rd:
        s += r"\draw (%s.D) to[short] ++(0,0.3) coordinate(%sd) to[R, l=%s] ++(0,1.5) node[vcc]{%s};" % (name, name, rd, vdd) + "\n"
    else:
        s += r"\draw (%s.D) to[short] ++(0,0.5) node[vcc]{%s};" % (name, vdd) + "\n"
    s += r"\draw (%s.G) to[short] ++(-0.4,0) to[R, l_=%s] ++(-1.6,0) to[short] ++(-0.4,0) to[vsourcesin, l_=$v_{in}$, invert] ++(0,-1.9) node[ground]{};" % (name, rin) + "\n"
    if out == "drain":
        s += r"\draw (%sd) to[short, -o] ++(1.2,0) node[right]{$v_{out}$};" % name + "\n"
    else:
        if load:
            s += r"\draw (%ss) to[short] ++(0.7,0) to[C, l=%s] ++(1.4,0) coordinate(%sl) to[R, l=%s] ++(0,-1.6) node[ground]{};" % (name, load[0], name, load[1]) + "\n"
            s += r"\draw (%sl) to[short, -o] ++(0.9,0) node[right]{$v_{out}$};" % name + "\n"
        else:
            s += r"\draw (%ss) to[short, -o] ++(1.2,0) node[right]{$v_{out}$};" % name + "\n"
    return s

fq = topoA(J, r"$V_{GS}$ bias\\ $+\SI{1}{V}$ AC", r"$V_{DS}=\SI{10}{V}$", gate_kind="Vac")
fq += note(-4.6, 3.3, r"$|y_{fs}|$ copy, one per ladder current, \SI{1}{kHz}\dots\SI{1}{GHz}", anchor="west")
fq += cs_stage(J, (9,0), "S", r"\SI{18}{V}", r"$R_D$\\ ($V_{DS}=\SI{9}{V}$)", r"$R_S$ ($I_D=I_{DSS}/3$)", r"\SI{1000}{\micro F}", r"\SI{1}{k\ohm}")
fq += note(6.5, 3.3, r"reference common-source stage, \SI{1}{Hz}\dots\SI{10}{MHz}", anchor="west")
write("jfet-frequency", ["VD0 d0 0 10 / VG0 g0 0 DC {vgs} AC 1 / JY0 d0 g0 0 DUT", ".ac dec 20 1000 1e9", "VDD vdd 0 18 / RD vdd dc {rd} / RS s 0 {rs} / CS s 0 1000u / RIN in g 1000 / VIN in 0 AC 1 / JS dc g s DUT"], fq)

def noise_body(kind, vds, rgs, bias):
    s = dut(kind, "(0,0)", "Q")
    s += r"\draw (Q.S) to[short] ++(0,-0.5) node[ground]{};" + "\n"
    s += r"\draw (Q.D) to[short] ++(0,0.3) to[rmeter, t=A, l=sense] ++(0,1.4) to[short] ++(2,0) to[vsource, l=%s, invert] ++(0,-2.4) node[ground]{};" % vds + "\n"
    s += r"\draw (Q.G) to[short] ++(-0.4,0) to[R, l_=$R_G$ %s] ++(-1.6,0) to[short] ++(-0.3,0) to[vsourcesin, l_=$v_{in}$ (noise\\ reference), invert] ++(0,-1.0) to[vsource, l_=%s, invert] ++(0,-1.2) node[ground]{};" % (rgs, bias) + "\n"
    s += note(-4.6, -3.6, r"H1: the sensed $i_d$ as a voltage, \SI{1000}{V/A}, into \SI{1}{M\ohm}; \texttt{.noise V(out) VIN}\\ one deck per bias current and $R_G$", anchor="west")
    return s
write("jfet-noise", ["VSENSE d dd 0 / VD dd 0 10", "VGB gb 0 {vgs}", "RG in g {0 | 1e7 | 1e6}", "J1 d g 0 DUT", "H1 out 0 VSENSE 1000 / RLOAD out 0 1meg", ".noise V(out) VIN dec 20 1 1000000"],
      noise_body(J, r"$V_{DS}=\SI{10}{V}$", r"0, \SI{10}{M\ohm}, \SI{1}{M\ohm}", r"$V_{GS}$ bias\\ for $I_D$"))

write("jfet-temperature", [".temp -55 | 100 | 125 | 150", "VT dt 0 10 / VGS g 0 0 / JT dt g 0 DUT", ".dc VGS -10 0.6 0.005"],
      topoA(J, r"$V_{GS}$ $-10\to+\SI{0.6}{V}$", r"$V_{DS}=\SI{10}{V}$", swept_gate=True) + thermo(3.4, -2.6, r"$-55$, 25, 100, 125, \SI{150}{\celsius}"))

sw = r"\draw (0,0) node[njfet](Q){};" + "\n"
sw += r"\node[anchor=west] at ($(Q.D)!0.5!(Q.S) + (0.55,0)$) {DUT};" + "\n"
sw += r"\draw (Q.S) to[short] ++(0,-0.3) to[rmeter, t=A, l=$i_s$] ++(0,-1.4) to[vsource, l=$v_s$ 0 or \SI{1}{V}, invert] ++(0,-1.4) node[ground]{};" + "\n"
sw += r"\draw (Q.D) to[short] ++(0,0.4) to[short] ++(2.4,0) coordinate(l) to[R, l=$R_L$ \SI{1}{k\ohm} / \SI{10}{k\ohm}] ++(0,-3.2) node[ground]{};" + "\n"
sw += r"\draw (l) to[short, -o] ++(1,0) node[right]{$v_{load}$};" + "\n"
sw += r"\draw (Q.G) to[short] ++(-0.4,0) to[R, l=$R_G$ \SI{1}{k\ohm}] ++(-1.6,0) to[short] ++(-0.8,0) to[vsourcesquare, l_=$0\to-\SI{10}{V}$\\ (or $2V_{GS(\mathrm{off})}$)\\ \SI{10}{ns} edges, invert] ++(0,-1.9) node[ground]{};" + "\n"
write("jfet-switch", ["VS s 0 0", "JW l g s DUT", "RL l 0 1000", "RG in g 1000 / VIN in 0 PWL(...)", ".tran 1e-10 4.2e-6"], sw)

dist = cs_stage(J, (0,0), "A", r"\SI{18}{V}", r"$R_D$ ($V_{DS}=\SI{9}{V}$)", r"$R_S$ ($I_D=I_{DSS}/3$)", None, r"\SI{10}{k\ohm}")
dist += note(-4.6, 3.3, r"common source, unbypassed, 1 and \SI{3}{V} peak out", anchor="west")
dist += cs_stage(J, (9,0), "B", r"\SI{18}{V}", None, r"$R_S$ ($I_D=I_{DSS}/3$)", None, r"\SI{10}{k\ohm}", out="source", load=(r"\SI{100}{\micro F}", r"\SI{10}{k\ohm}"))
dist += note(6.5, 3.3, r"source follower, \SI{1}{V} peak out", anchor="west")
write("jfet-distortion", ["VDD vdd 0 18 / RD vdd d {rd} / RS s 0 {rs}", "RIN in g 10000 / VIN in 0 SIN(0 {amp} 1000)", "J1 d g s DUT", ".tran ... ten cycles"], dist)

bd = dut(J, "(0,0)", "A")
bd += r"\draw (A.S) to[short] ++(0,-0.5) node[ground]{};" + "\n"
bd += r"\draw (A.D) to[short] ++(0,0.3) to[R, l=\SI{1}{G\ohm}] ++(0,1.4) node[ground, rotate=180]{};" + "\n"
bd += r"\draw (A.G) to[short] ++(-0.5,0) to[rmeter, t=A, l=$I$] ++(-1.4,0) to[short] ++(-0.5,0) to[vsource, l_=$V_{GS}$ $0\to-\SI{100}{V}$, invert] ++(0,-1.9) node[ground]{};" + "\n"
bd += note(-4.6, 3.3, r"gate--source, drain open", anchor="west")
bd += dut(J, "(8,0)", "B")
bd += r"\draw (B.S) to[R, l_=\SI{1}{G\ohm}] ++(0,-1.6) node[ground]{};" + "\n"
bd += r"\draw (B.D) to[short] ++(0,0.3) to[rmeter, t=A, l=$I$] ++(0,1.4) to[short] ++(2,0) to[vsource, l=$V_{DG}$ $0\to\SI{300}{V}$, invert] ++(0,-2.4) node[ground]{};" + "\n"
bd += r"\draw (B.G) to[short] ++(-0.8,0) node[ground]{};" + "\n"
bd += note(6.5, 3.3, r"drain--gate, source open", anchor="west")
bd += dut(J, "(16,0)", "C")
bd += r"\draw (C.S) to[short] ++(0,-0.5) node[ground]{};" + "\n"
bd += r"\draw (C.D) to[short] ++(0,0.3) to[rmeter, t=A, l=$I_{D(\mathrm{off})}$] ++(0,1.4) to[short] ++(2,0) to[vsource, l=$V_{DS}$ $0\to\SI{300}{V}$, invert] ++(0,-2.4) node[ground]{};" + "\n"
bd += r"\draw (C.G) to[short] ++(-1.9,0) to[vsource, l_=$V_{GS}=2V_{GS(\mathrm{off})}$, invert] ++(0,-1.9) node[ground]{};" + "\n"
bd += note(14.5, 3.3, r"drain--source, gate off", anchor="west")
write("jfet-breakdown", ["VA sw ga 0 / RDA da 0 1e9 / JA da ga 0 DUT", "VB sw db 0 / RSB sb 0 1e9 / JB db 0 sb DUT", "VC sw dc 0 / VGC gc 0 {2*vgs_off} / JC dc gc 0 DUT"], bd)

# ---------------- MOSFET ----------------
mr = topoA(M, r"$V_{GS}=\SI{10}{V}$\\ (copy 2: \SI{4.5}{V})", r"$V_{DS}=\SI{1}{V}$")
mr += dut(M, "(8,0)", "R")
mr += r"\draw (R.S) to[short] ++(0,-0.5) node[ground]{};" + "\n"
mr += r"\draw (R.D) to[short] ++(0,0.3) to[rmeter, t=A, l=$I_S$] ++(0,1.4) to[short] ++(2,0) to[vsource, l=$V_{DS}=-\SI{1}{V}$\\ (body diode), invert] ++(0,-2.4) node[ground]{};" + "\n"
mr += r"\draw (R.G) to[short] ++(-0.8,0) node[ground]{};" + "\n"
write("mosfet-runs", ["VD d 0 1 / VG g 0 10 / M1 d g 0 0 DUT", "VD2 d2 0 1 / VG2 g2 0 4.5 / M2 d2 g2 0 0 DUT", "VD3 d3 0 -1 / M3 d3 0 0 0 DUT", ".op"], mr)

write("mosfet-tracer", ["VK1 sw dk1 0", "VGK1 gk1 0 {vgs_k}", "MK1 dk1 gk1 0 0 DUT", "VSW sw 0 0 / .dc VSW 0 10 0.01 (and 0 30 0.05)"],
      topoA(M, r"$V_{GS}$ step\\ 2\dots\SI{15}{V} or auto", r"$V_{DS}$ $0\to10$ / \SI{30}{V}", swept_drain=True)
      + note(-4.6, -3.6, r"one copy per gate step; drawn as one\\ auto steps: $V_{GS}$ for 10, 30, 100, 300 mA, \SI{1}{A} at \SI{5}{V}", anchor="west"))

tr = topoA(M, r"$V_{GS}$ $-2\to\SI{15}{V}$", r"$V_{DS}$ 1, 6,\\ 15, \SI{25}{V}", swept_gate=True)
tr += dut(M, "(8,0)", "R")
tr += r"\draw (R.S) to[short] ++(0,-0.5) node[ground]{};" + "\n"
tr += r"\draw (R.D) to[short] ++(0,0.3) to[rmeter, t=A, l=$I_D$] ++(0,1.4) -| ($(R.G)+(-0.8,0)$) coordinate(rg) -- (R.G);" + "\n"
tr += r"\draw (rg) to[short] ++(-1.0,0) to[vsource, l_=$V_{GS}$ swept, invert] ++(0,-1.9) node[ground]{};" + "\n"
tr += note(6.5, 3.3, r"diode-connected copy: $V_{th}$ at 20, 250 \si{\micro A}, \SI{1}{mA}", anchor="west")
tr += note(-4.6, -3.6, r"four copies, one per $V_{DS}$; drawn as one", anchor="west")
write("mosfet-transfer", ["VT1 dt1 0 15 / VGS g 0 0 / .dc VGS -2 15 0.01", "MT1 dt1 g 0 0 DUT", "VTD dtd g 0 / MTD dtd g 0 0 DUT"], tr)

def forced_current(kind, at, name, gate_lbl, dial_lbl, clamp_v, reversed_=False, vm_lbl=r"$V_{DS}$"):
    x,y = at
    s = dut(kind, "(%g,%g)" % (x,y), name)
    s += r"\draw (%s.S) to[short] ++(0,-0.5) node[ground]{};" % name + "\n"
    s += r"\draw (%s.D) to[short] ++(0,0.3) coordinate(%sd) to[isource, l=%s] ++(0,1.8) node[ground, rotate=180]{};" % (name, name, dial_lbl) + "\n"
    s += r"\draw (%sd) to[short] ++(1.6,0) to[D, l=clamp] ++(0,1.4) to[short] ++(0,0.2) node[vcc]{%s};" % (name, clamp_v) + "\n"
    s += r"\draw (%sd) to[short] ++(3.4,0) to[rmeter, t=V, l=%s] ++(0,-2.0) node[ground]{};" % (name, vm_lbl) + "\n"
    s += r"\draw (%s.G) to[short] ++(-2.2,0) to[vsource, l_=%s, invert] ++(0,-1.9) node[ground]{};" % (name, gate_lbl) + "\n"
    return s

rd = forced_current(M, (0,0), "Q", r"$V_{GS}$ step\\ 2.5\dots\SI{15}{V}", r"$I_D=10^{V(x)}$\\ \SI{1}{mA}\dots\SI{100}{A}", r"\SI{30}{V}")
rd += note(-4.6, -3.6, r"the drain current is forced by the behavioural dial;\\ the clamp catches a copy that cannot pass it; $R_{DS(\mathrm{on})}=V_{DS}/I_D$\\ second deck: $I_D$ held at 0.1, 1, \SI{10}{A}, gate swept $0\to\SI{15}{V}$", anchor="west")
write("mosfet-rdson", ["BR0 0 dr0 I=exp(2.302585092994046*V(x))", "DCL0 dr0 cl0 DCLMP / VCL0 cl0 0 30", "VGR0 gr0 0 10", "MR0 dr0 gr0 0 0 DUT", ".dc VX -3 2 0.05"], rd)

gmm = topoA(M, r"$V_{GS}$ bias\\ $+\SI{1}{V}$ AC", r"$V_{DS}=\SI{15}{V}$", gate_kind="Vac", name="Q")
gmm += topoA(M, r"$V_{GS}$ bias", r"$V_{DS}=\SI{15}{V}$\\ $+\SI{1}{V}$ AC", drain_kind="Vac", name="R", origin=(8,0))
gmm += note(-4.6, -3.6, r"copy A ($g_{fs}$), copy B ($g_{os}$); one pair per ladder current;\\ $V_{DS}$ 6 and \SI{15}{V}; read at \SI{1}{kHz}", anchor="west")
write("mosfet-gm", ["VD0 d0 0 15 / VG0 g0 0 DC {vgs} AC 1 / MG0 d0 g0 0 0 DUT", "VDO0 do0 0 DC 15 AC 1", ".ac dec 10 100 10000"], gmm)

mc = dut(M, "(0,0)", "A")
mc += r"\draw (A.S) to[short] ++(0,-0.5) node[ground]{};" + "\n"
mc += r"\draw (A.D) to[short] ++(0,0.3) to[L, l=\SI{1}{H}] ++(0,1.4) to[short] ++(1.8,0) to[vsource, l=$V_{DS}$, invert] ++(0,-2.3) node[ground]{};" + "\n"
mc += r"\draw (A.G) to[short] ++(-0.5,0) to[rmeter, t=A, l=$i_g$] ++(-1.4,0) to[short] ++(-0.4,0) to[vsourcesin, l_=\SI{1}{V} AC, invert] ++(0,-1.9) node[ground]{};" + "\n"
mc += note(-4.6, 3.3, r"$C_{iss}$: gate driven, drain AC-open through \SI{1}{H}", anchor="west")
mc += cap_copy(M, (8,0), "B", "D", {}, None, r"$V_{DS}$")
mc += note(6.5, 3.3, r"$C_{oss}$: drain driven, gate grounded", anchor="west")
mc += cap_copy(M, (16,0), "C", "G", {"D": r"$V_{DS}$"}, None, r"$V_{GS}=0$")
mc += note(14.5, 3.3, r"$C_{rss}$: $i_d/\omega$ with the gate driven", anchor="west")
mc += note(-4.6, -3.6, r"one set per drain voltage 0.1\dots\SI{300}{V}; a second deck at $V_{DS}=0$ steps $V_{GS}$ 0\dots\SI{10}{V}; read at \SI{1}{MHz}", anchor="west")
write("mosfet-capacitance", ["VDI di 0 {v} / LDI di dio 1 / VGI gi 0 AC 1 / MI dio gi 0 0 DUT", "VDO do 0 DC {v} AC 1 / MO do 0 0 0 DUT", "VDR dr 0 {v} / VGR gr 0 AC 1 / MR dr gr 0 0 DUT", ".ac dec 10 100000 10000000"], mc)

gc = dut(M, "(0,0)", "Q")
gc += r"\draw (Q.S) to[short] ++(0,-0.5) node[ground]{};" + "\n"
gc += r"\draw (Q.D) to[short] ++(0,0.3) coordinate(qd) to[isource, l=$I_L$ 0.1, 1, 10, \SI{50}{A}] ++(0,1.8) to[short] ++(0,0.2) node[vcc]{$V_{DD}$ 10, 30, 100, \SI{300}{V}};" + "\n"
gc += r"\draw (qd) to[short] ++(2.0,0) to[D, l=clamp] ++(0,1.8) -| ($(qd)+(0,2.0)$);" + "\n"
gc += r"\draw (qd) to[short, -o] ++(-0.8,0.6) node[left]{$V_{DS}$};" + "\n"
gc += r"\draw (Q.G) to[short] ++(-1.1,0) coordinate(qg) to[short] ++(-0.7,0) to[isource, l_=$I_G$ 1 or \SI{10}{mA}, invert] ++(0,-1.9) node[ground]{};" + "\n"
gc += r"\draw (qg) to[short, -o] ++(0,0.7) node[above left]{$V_{GS}(t)$};" + "\n"
gc += note(-4.6, -3.6, r"$Q = I_G\cdot t$; the drain sits at $V_{DD}$ until the transistor takes $I_L$\\ one deck per load current and supply", anchor="west")
write("mosfet-gate-charge", ["IG 0 g 0.001", "IL vdd d 1 / DCL d vdd DCLMP / VDD vdd 0 30", "M1 d g 0 0 DUT", ".tran 1e-9 ..."], gc)

ms = dut(M, "(0,0)", "Q")
ms += r"\draw (Q.S) to[short] ++(0,-0.5) node[ground]{};" + "\n"
ms += r"\draw (Q.D) to[short] ++(0,0.3) coordinate(qd) to[R, l=$R_L=V_{DD}/I_D$] ++(0,1.8) to[short] ++(0,0.2) node[vcc]{$V_{DD}$ 10 / \SI{30}{V}};" + "\n"
ms += r"\draw (qd) to[short, -o] ++(1.0,0) node[right]{$V_{DS}(t)$};" + "\n"
ms += r"\draw (Q.G) to[short] ++(-0.4,0) to[R, l_=$R_G$ 4.7, 10, \SI{25}{\ohm}] ++(-1.6,0) to[short] ++(-0.4,0) to[vsourcesquare, l_=$0\to10$ (or 4.5) V\\ \SI{2}{ns} edges, \SI{2}{\micro s}, invert] ++(0,-1.9) node[ground]{};" + "\n"
ms += note(-4.6, 3.9, r"resistive load, one deck per $I_D$ (10 mA\dots\SI{10}{A}), $V_{DD}$, $R_G$, drive", anchor="west")
ms += dut(M, "(9,0)", "R")
ms += r"\draw (R.S) to[short] ++(0,-0.5) node[ground]{};" + "\n"
ms += r"\draw (R.D) to[short] ++(0,0.3) coordinate(rd) to[L, l=$L$ \SI{1}{mH}] ++(0,1.8) to[short] ++(0,0.2) node[vcc]{$V_{DD}$ \SI{30}{V}};" + "\n"
ms += r"\draw (rd) to[short] ++(1.6,0) to[D, l=ideal] ++(0,1.8) -| ($(rd)+(0,2.0)$);" + "\n"
ms += r"\draw (R.G) to[short] ++(-0.4,0) to[R, l_=$R_G$ \SI{10}{\ohm}] ++(-1.6,0) to[short] ++(-0.4,0) to[vsourcesquare, l_=two pulses, invert] ++(0,-1.9) node[ground]{};" + "\n"
ms += note(6.5, 3.9, r"clamped inductive: $E_{on}$, $E_{off}$ on the second pulse", anchor="west")
write("mosfet-switching", ["VDD vdd 0 30 / RL vdd d {rl}", "VIN in 0 PULSE(0 10 1e-7 2e-9 2e-9 2e-6 1) / RG in g 10", "M1 d g 0 0 DUT", "L1 vdd d 1m / DFW d vdd DIDEAL (inductive deck)"], ms)

bdd = r"\draw (0,0) node[nmos](Q){};" + "\n"
bdd += r"\node[anchor=west] at ($(Q.D)!0.5!(Q.S) + (0.55,0)$) {DUT};" + "\n"
bdd += r"\draw (Q.D) to[short] ++(0,0.3) to[short] ++(0,0.3) node[ground, rotate=180]{};" + "\n"
bdd += r"\draw (Q.S) to[short] ++(0,-0.5) coordinate(qs) to[isource, l_=$I_S=10^{V(x)}$\\ \SI{1}{\micro A}\dots\SI{100}{A}] ++(0,-1.9) node[ground]{};" + "\n"
bdd += r"\draw (qs) to[short] ++(1.8,0) to[rmeter, t=V, l=$V_{SD}$] ++(0,-1.9) node[ground]{};" + "\n"
bdd += r"\draw (Q.G) to[short] ++(-2.2,0) coordinate(gl) to[vsource, l_=$V_{GS}$ 0, 4.5, \SI{10}{V}\\ (to the source), invert] (gl |- qs) to[short] (qs);" + "\n"
bdd += note(-4.6, 3.3, r"forward: the source current forced into the body diode, drain grounded", anchor="west")
# recovery
bdd += r"\draw (9,0) node[nmos](R){};" + "\n"
bdd += r"\node[anchor=west] at ($(R.D)!0.5!(R.S) + (0.55,0)$) {DUT};" + "\n"
bdd += r"\draw (R.G) to[short] ++(-0.6,0) |- ($(R.S)+(0,-0.3)$);" + "\n"
bdd += r"\draw (R.D) to[short] ++(0,0.3) to[short] ++(0,0.3) node[ground, rotate=180]{};" + "\n"
bdd += r"\draw (R.S) to[short] ++(0,-0.3) coordinate(rs) to[L, l_=$L_{di/dt}$] ++(0,-1.9) to[vsource, l_=$V_R$ \SI{30}{V}, invert] ++(0,-1.4) node[ground]{};" + "\n"
bdd += r"\draw (rs) to[short] ++(1.6,0) to[isource, l=$I_F$ 1, \SI{10}{A}] ++(0,-1.9) node[ground]{};" + "\n"
bdd += r"\draw (rs) to[short] ++(3.2,0) to[cute open switch, l=ideal switch] ++(0,-1.9) node[ground]{};" + "\n"
bdd += note(6.5, 3.3, r"recovery: $I_F$ through the diode, commutated at $di/dt$ = 100, 200, \SI{400}{A/\micro s}", anchor="west")
write("mosfet-body-diode", ["BS 0 s I=exp(2.302585092994046*V(x))", "MD 0 g s s DUT / VG g s 0", ".dc VX -6 2 0.05", "L1 vr s {l} / SW s 0 ctrl 0 SWIDEAL / VR vr 0 30"], bdd)

mt = topoA(M, r"$V_{GS}$ swept", r"$V_{DS}=\SI{15}{V}$", swept_gate=True)
mt += thermo(3.4, -2.6, r"$-55$, 25, 100, 125, 150, \SI{175}{\celsius}")
mt += note(-4.6, -3.6, r"the transfer, $R_{DS(\mathrm{on})}$ and body-diode decks\\ rerun at each temperature; drawn: the transfer copy", anchor="west")
write("mosfet-temperature", [".temp -55 | 100 | 125 | 150 | 175", "the transfer, rdson and body-diode copies"], mt)

write("mosfet-noise", ["VSENSE d dd 0 / VD dd 0 10 / VGB gb 0 {vgs} / RG in g {0 | 1000}", "M1 d g 0 0 DUT / H1 out 0 VSENSE 1000 / RLOAD out 0 1meg", ".noise V(out) VIN dec 20 1 1000000"],
      noise_body(M, r"$V_{DS}=\SI{10}{V}$", r"0, \SI{1}{k\ohm}", r"$V_{GS}$ bias\\ for $I_D$"))

mb = dut(M, "(0,0)", "A")
mb += r"\draw (A.S) to[short] ++(0,-0.5) node[ground]{};" + "\n"
mb += r"\draw (A.D) to[short] ++(0,0.3) to[rmeter, t=A, l=$I_{DSS}$] ++(0,1.4) to[short] ++(2,0) to[vsource, l=$V_{DS}$ $0\to\SI{1000}{V}$, invert] ++(0,-2.4) node[ground]{};" + "\n"
mb += r"\draw (A.G) to[short] ++(-0.8,0) node[ground]{};" + "\n"
mb += note(-4.6, 3.3, r"drain--source, gate to source", anchor="west")
mb += dut(M, "(8,0)", "B")
mb += r"\draw (B.S) to[short] ++(0,-0.5) node[ground]{};" + "\n"
mb += r"\draw (B.D) to[short] ++(0,0.3) to[short] ++(0,0.3) node[ground, rotate=180]{};" + "\n"
mb += r"\draw (B.G) to[short] ++(-0.5,0) to[rmeter, t=A, l=$I_{GSS}$] ++(-1.4,0) to[short] ++(-0.5,0) to[vsource, l_=$V_{GS}$ $\pm\SI{30}{V}$, invert] ++(0,-1.9) node[ground]{};" + "\n"
mb += note(6.5, 3.3, r"gate--source, drain to source", anchor="west")
write("mosfet-breakdown", ["VA sw da 0 / MA da 0 0 0 DUT / .dc VSW 0 1000 1", "VB sw gb 0 / MB 0 gb 0 0 DUT / .dc VSW -30 30 0.1"], mb)

md = cs_stage(M, (0,0), "A", r"\SI{20}{V}", r"\SI{1}{k\ohm}", r"\SI{100}{\ohm}", r"\SI{1000}{\micro F}", r"\SI{1}{k\ohm}", sink=r"\SI{10}{mA}")
md += note(-4.6, 3.3, r"common source: \SI{10}{mA}, \SI{100}{\ohm} bypassed, \SI{1}{V} peak out at \SI{1}{kHz}", anchor="west")
md += cs_stage(M, (9,0), "B", r"\SI{25}{V}", None, None, None, r"100 / \SI{1}{k\ohm}", out="source", load=(r"\SI{1000}{\micro F}", r"\SI{100}{\ohm}"), sink=r"\SI{100}{mA}")
md += note(6.5, 3.3, r"source follower: \SI{100}{mA}, \SI{1}{V} peak out at 1 and \SI{20}{kHz}", anchor="west")
write("mosfet-distortion", ["VDD vdd 0 20 / RL vdd d 1000 / RS s x 100 / CS x 0 1000u / IS x vss 0.01", "RIN in g 1000 / VIN in 0 SIN(0 {amp} 1000) / M1 d g s s DUT", "follower: M1 vdd g s s DUT / IS s vss 0.1 / CL s l 1000u / RL l 0 100"], md)
print("written", len(os.listdir(OUT)))
