# Preview of the FET and op-amp benches on ngspice

One model per part, ngspice 42 on this machine (the project's pinned image carries ngspice 47; QSPICE and LTspice were not available here). The decks are the draft of `decks_jfet`, `decks_mos` and `decks_opamp` for the measurements of `docs/fet-characterisation.md` and `docs/opamp-characterisation.md`; the numbers are what each model does, not the published characterisation, which comes through `measurements.yaml`, the pinned images and the records. 25 °C unless said; `n/a` is a point the model never reached.

Noise calibration: ngspice's `inoise_spectrum` for a 1 kΩ source resistance reads 4.07 nV/√Hz (4.07 nV/√Hz expected), so it is a density in V/√Hz.

## Models

| part | published by | address | sha256 of the file read |
|---|---|---|---|
| J201 | Central Semiconductor | https://www.centralsemi.com/docs/ENGINEERING/csm/J201.LIB | `475a4d7cd582cab1d69817e48a79281406f8b564d3c5ec723dd28eff2ae649bc` |
| 2N5457 | Central Semiconductor | https://www.centralsemi.com/docs/ENGINEERING/csm/2N5457_CSM.LIB | `80722026f6c2a2aab9f071f2ba6afef323f39248650d72672d707fb928ef2d4c` |
| 2N3819 | Central Semiconductor | https://www.centralsemi.com/docs/ENGINEERING/csm/CSM1455.LIB | `d00358ff785397bb9b0d81803849bf16e4d5d342c85d20f8083608168dada2f7` |
| 2N7000 | Zetex, 2000, via LTwiki | https://ltwiki.org/files/LTspiceIV/Vendor%20List/Zetex/2n7000.lib | `a49370129456faf00e160691eaea69e7a4092a2d97582e79c08ab219708fd7b0` |
| BS170 | Diodes Incorporated (BS170P) | https://www.diodes.com/spice/download/4537/BS170P.spice.txt | `8e240e73cb25bad46117ef4013113882bb6ba4ccccc486ebb8ac58cc97f8f9e4` |
| IRF510 | International Rectifier, 1988, via LTwiki (pwrmos.lib, the IRF510 card alone) | https://ltwiki.org/files/LTspiceIV/Vendor%20List/Spice-Models-collection/pwrmos.lib | `5ea0614db55e41407b5d00b634552e8f7a91bfe8f4ce106b92b86cb0f0a6a7e6` |
| TL072 | Texas Instruments, PSpice PARTS 1989 | https://www.ti.com/lit/zip/SLOJ067 | `74e89d558163615ac7a19f0c783101a6f8af77fb6d80bd3c20c6ab66426561cd` |
| NE5532 | Texas Instruments, PSpice PARTS 1989, via the LTwiki collection (lib/sub/NE553x.lib) | http://bordodynov.ltwiki.org/lib.zip | `0b90f4ac73ed328341114e02953781ab5106be95fb2e65cc4ff6535bd0e08564` |
| RC4558 | Texas Instruments, PSpice PARTS 1989 | https://www.ti.com/lit/zip/SLOJ053 | `6ff2f51ab04648973e87a854fc0a1ad0dc8ada7c9c3dcc6869c2ab64030246f6` |

## JFETs

Models: J201, 2N5457 and 2N3819 as Central Semiconductor publishes them (Shichman-Hodges cards with the LTspice gate-current extensions, which ngspice ignores with a warning).

### Transfer (jfet-transfer, jfet-gm, jfet-temperature)

| | jfet/J201 | jfet/2N5457 | jfet/2N3819 |
|---|---|---|---|
| IDSS at VDS = 10 V | 312 µA | 2.78 mA | 13.2 mA |
| IDSS at 5 V | 311 µA | 2.77 mA | 12.1 mA |
| IDSS at 15 V | 313 µA | 2.79 mA | 14.3 mA |
| VGS(off) at ID = 1 µA, 10 V | -471 mV | -1.44 V | -2.47 V |
| VGS(off) at 10 nA | -486 mV | -1.46 V | -2.49 V |
| gfs at VGS = 0, 10 V | 908 µS | 3.41 mS | 10.6 mS |
| gm at ID = 100 µA | 687 µS | 776 µS | 922 µS |
| gm at 1 mA | n/a | 2.23 mS | 2.91 mS |
| gm at 5 mA | n/a | 4.27 mS | 6.52 mS |
| VGS at 100 µA | -260 mV | -1.21 V | -2.28 V |
| VGS at 1 mA | n/a | -626 mV | -1.81 V |
| IDSS at −55 °C | 174 µA | 2.91 mA | 16.7 mA |
| IDSS at 125 °C | 455 µA | 2.46 mA | 9.73 mA |
| VGS(off) at −55 °C | -273 mV | -1.24 V | -2.28 V |
| VGS(off) at 125 °C | -716 mV | -1.68 V | -2.72 V |

### Output characteristics (jfet-tracer)

| | jfet/J201 | jfet/2N5457 | jfet/2N3819 |
|---|---|---|---|
| ID at 10 V, VGS = 0 | 315 µA | 2.77 mA | 13.1 mA |
| knee (90 % of ID at 15 V) | 537 mV | 1.18 V | 8.5 V |
| ro at 10 V, VGS = 0 | 5.39 MΩ | 518 kΩ | 4.57 kΩ |

- J201 traces at 10 V, VGS steps a fifth of VGS(off): +0 V → 315 µA, -0.094 V → 232 µA, -0.188 V → 156 µA, -0.282 V → 88.2 µA, -0.376 V → 33.6 µA
- 2N5457 traces at 10 V, VGS steps a fifth of VGS(off): +0 V → 2.77 mA, -0.288 V → 1.87 mA, -0.575 V → 1.12 mA, -0.863 V → 537 µA, -1.15 V → 156 µA
- 2N3819 traces at 10 V, VGS steps a fifth of VGS(off): +0 V → 13.1 mA, -0.495 V → 8.45 mA, -0.989 V → 4.8 mA, -1.48 V → 2.17 mA, -1.98 V → 571 µA

### Gate, capacitances and noise (jfet-gate, jfet-capacitance, jfet-noise)

| | jfet/J201 | jfet/2N5457 | jfet/2N3819 |
|---|---|---|---|
| IGSS at VGS = −15 V | -30 pA | -30 pA | -30 pA |
| VGS(forward) at IG = 1 mA | 965 mV | 733 mV | 994 mV |
| noise stage ID | 156 µA | 1 mA | 1 mA |
| en at 10 Hz (VDS = 10 V) | 5.04 nV/√Hz | 4.61 nV/√Hz | 4.01 nV/√Hz |
| en at 1 kHz | 4.32 nV/√Hz | 2.48 nV/√Hz | 2.08 nV/√Hz |
| en at 10 kHz | 4.32 nV/√Hz | 2.45 nV/√Hz | 2.05 nV/√Hz |
| 1/f corner | 3.67 Hz | 25.4 Hz | 28.5 Hz |

### Ohmic region, gm against frequency, the analogue switch, a stage's distortion, breakdown (jfet-ohmic, jfet-frequency, jfet-switch, jfet-distortion, jfet-breakdown)

| | jfet/J201 | jfet/2N5457 | jfet/2N3819 |
|---|---|---|---|
| rDS(on) at VGS = 0, VDS = 0 | 1.55 kΩ | 330 Ω | 114 Ω |
| gm at 1 kHz (stage current) | 775 µS | 2.22 mS | 2.91 mS |
| f where |id/ig| = 1 | 6.19 MHz | 4.21 MHz | 187 MHz |
| switch t_on 10–90 % (1 V into 10 kΩ ‖ 100 pF) | 230 ns | 5.5 ns | 37.6 ns |
| switch t_off 90–10 % | 1.24 µs | 5.38 ns | 2.21 µs |
| on level (1 V in) | 369 mV | 932 mV | 981 mV |
| stage current | 156 µA | 1 mA | 1 mA |
| stage gain (RD for VDS = 10 V) | 24.6  | 11.1  | 13.4  |
| THD, 100 mVpk at 1 kHz | 31 m | 23.6 m | 25 m |
| ID off at 30 V | 31.5 pA | 32.4 pA | 33.5 pA |
| ID off at 60 V | 61.5 pA | 62.4 pA | 63.5 pA |
| breakdown | absent (leakage flat to 60 V) | absent (leakage flat to 60 V) | absent (leakage flat to 60 V) |

**Ciss against VGS at VDS = 15 V, 1 MHz**

- J201: 0 V → 22.3 pF, -500 mV → 19.7 pF, -1 V → 17.8 pF, -2 V → 15.8 pF, -3 V → 14.7 pF, -5 V → 13.3 pF
- 2N5457: 0 V → 154 pF, -500 mV → 144 pF, -1 V → 133 pF, -2 V → 119 pF, -3 V → 116 pF, -5 V → 110 pF
- 2N3819: 0 V → 4.72 pF, -500 mV → 3.5 pF, -1 V → 3 pF, -2 V → 2.52 pF, -3 V → 2.26 pF, -5 V → 1.95 pF

**Crss against VGS at VDS = 15 V, 1 MHz**

- J201: 0 V → 20.4 pF, -500 mV → 11.1 pF, -1 V → 10.9 pF, -2 V → 10.6 pF, -3 V → 10.3 pF, -5 V → 9.76 pF
- 2N5457: 0 V → 151 pF, -500 mV → 142 pF, -1 V → 131 pF, -2 V → 117 pF, -3 V → 114 pF, -5 V → 108 pF
- 2N3819: 0 V → 1.13 pF, -500 mV → 1.11 pF, -1 V → 1.09 pF, -2 V → 1.06 pF, -3 V → 1.03 pF, -5 V → 980 fF

**Cgs (Ciss − Crss) against VGS at VDS = 15 V**

- J201: 0 V → 1.86 pF, -500 mV → 8.6 pF, -1 V → 6.88 pF, -2 V → 5.25 pF, -3 V → 4.41 pF, -5 V → 3.5 pF
- 2N5457: 0 V → 2.86 pF, -500 mV → 2.48 pF, -1 V → 2.39 pF, -2 V → 2.18 pF, -3 V → 1.83 pF, -5 V → 1.45 pF
- 2N3819: 0 V → 3.6 pF, -500 mV → 2.39 pF, -1 V → 1.91 pF, -2 V → 1.46 pF, -3 V → 1.22 pF, -5 V → 970 fF

**Cgd against VDG at VGS = 0**

- J201: 0 V → 45.5 pF, 1 V → 64.7 pF, 2 V → 48.9 pF, 5 V → 32.9 pF, 10 V → 24.3 pF, 15 V → 20.4 pF, 20 V → 18.1 pF, 25 V → 16.5 pF
- 2N5457: 0 V → 604 pF, 1 V → 431 pF, 2 V → 389 pF, 5 V → 257 pF, 10 V → 184 pF, 15 V → 151 pF, 20 V → 132 pF, 25 V → 118 pF
- 2N3819: 0 V → 7.06 pF, 1 V → 3.75 pF, 2 V → 2.86 pF, 5 V → 1.91 pF, 10 V → 1.37 pF, 15 V → 1.13 pF, 20 V → 980 fF, 25 V → 878 fF

### The rest of the JFET bench (jfet-gate, jfet-switch, jfet-distortion, jfet-temperature)

| | jfet/J201 | jfet/2N5457 | jfet/2N3819 |
|---|---|---|---|
| gate leakage: VGS, VDS, IG, drain's share, source's share | -10  / 0  / -20 p / 10 p / 10 p; -10  / 10  / -30 p / 20 p / 10 p; -15  / 0  / -30 p / 15 p / 15 p; -15  / 10  / -40 p / 25 p / 15 p | -10  / 0  / -20 p / 10 p / 10 p; -10  / 10  / -30 p / 20 p / 10 p; -15  / 0  / -30 p / 15 p / 15 p; -15  / 10  / -40 p / 25 p / 15 p | -10  / 0  / -20 p / 10 p / 10 p; -10  / 10  / -30 p / 20 p / 10 p; -15  / 0  / -30 p / 15 p / 15 p; -15  / 10  / -40 p / 25 p / 15 p |
| charge injection into 1 nF at turn-off | -35.1 pC | -694 pC | -11.8 pC |
| THD of a source follower, 1 Vpk | 473 µ | 1.64 m | 1.23 m |
| IDSS at 100 °C | 423 µA | 2.55 mA | 10.5 mA |
| IDSS at 150 °C | 484 µA | 2.37 mA | 8.99 mA |
| VGS(off) at 150 °C | -777 mV | -1.74 V | -2.78 V |
| VGS at 100 µA, −55 °C | -89.8 mV | -1.06 V | -2.12 V |
| VGS at 100 µA, 125 °C | -464 mV | -1.39 V | -2.47 V |
| zero-TC point (VGS, ID) | absent (no crossing above 1 µA) | -495 m, 1.31 m | -1.61 , 1.68 m |
| agreement | n/a (ngspice only here) | n/a (ngspice only here) | n/a (ngspice only here) |

### What the card says (jfet-card)

| | J201 | 2N5457 | 2N3819 |
|---|---|---|---|
| family | card: NJF | card: NJF | card: NJF |
| pins | (model card) | (model card) | (model card) |
| model types | NJF | NJF | NJF |
| transistors (temperature and shot noise carriers) | 0 | 0 | 0 |
| behavioural sources | 0 | 0 | 0 |
| supply resistor RP | none | none | none |
| flicker noise (KF/AF) | present | present | present |
| temperature coefficients (TC1/TC2/XTI/EG) | only the junctions' defaults | only the junctions' defaults | only the junctions' defaults |
| transit time (TT/TF) | absent | absent | absent |
| breakdown (BV) | absent | absent | absent |

## MOSFETs

Models: 2N7000 as Zetex published it in 2000 (a level-1 subcircuit with its own body diode), BS170 as Diodes Incorporated publishes BS170P (subcircuit), IRF510 as International Rectifier's 1988 level-3 card.

### Transfer and threshold (mos-transfer, mos-gm, mos-temperature)

| | mosfet/2N7000 | mosfet/BS170 | mosfet/IRF510 |
|---|---|---|---|
| Vth at ID = 250 µA, VDS = 5 V | 2.52 V | 1.89 V | 3.71 V |
| Vth at 1 mA | 2.56 V | 1.95 V | 3.72 V |
| ID at VGS = 3 V | 32.9 mA | 70.4 mA | 5.17 pA |
| ID at 4.5 V | 326 mA | 301 mA | 736 mA |
| ID at 5 V | 459 mA | 402 mA | 1.43 A |
| ID at 10 V | 1.89 A | 1.13 A | 9.05 A |
| gfs at 10 mA | 68.5 mS | 46.3 mS | 313 mS |
| gfs at 100 mA | 173 mS | 126 mS | 760 mS |
| gfs at 1 A | 336 mS | 98.2 mS | 1.38 S |
| Vth at 1 mA, −55 °C | 2.62 V | 2.01 V | 3.79 V |
| Vth at 1 mA, 125 °C | 2.48 V | 1.88 V | 3.62 V |
| ID at 10 V, −55 °C | n/a | n/a | n/a |
| ID at 10 V, 125 °C | n/a | n/a | n/a |

### On-resistance and body diode (mos-rdson, mos-body-diode)

| | mosfet/2N7000 | mosfet/BS170 | mosfet/IRF510 |
|---|---|---|---|
| RDS(on) at VGS = 4.5 V, VDS = 0.1 V | 3.41 Ω | 6.1 Ω | 681 mΩ |
| RDS(on) at VGS = 10 V, VDS = 0.1 V | 2.13 Ω | 4.01 Ω | 496 mΩ |
| VSD at 100 mA | 744 mV | 690 mV | 698 mV |
| VSD at 1 A | 876 mV | 1.23 V | 777 mV |

- 2N7000 ID at VDS = 10 V per VGS step: 2 V → 1.67 µA, 2.5 V → 101 µA, 3 V → 32.9 mA, 3.5 V → 106 mA, 4 V → 206 mA, 4.5 V → 325 mA, 5 V → 458 mA, 6 V → 756 mA, 8 V → 1.44 A, 10 V → 2.19 A
- BS170 ID at VDS = 10 V per VGS step: 2 V → 1.85 mA, 2.5 V → 25 mA, 3 V → 70 mA, 3.5 V → 133 mA, 4 V → 210 mA, 4.5 V → 300 mA, 5 V → 400 mA, 6 V → 627 mA, 8 V → 1.16 A, 10 V → 1.77 A
- IRF510 ID at VDS = 10 V per VGS step: 2 V → 10.3 pA, 2.5 V → 10.3 pA, 3 V → 10.3 pA, 3.5 V → 10.3 pA, 4 V → 170 mA, 4.5 V → 735 mA, 5 V → 1.43 A, 6 V → 3 A, 8 V → 6.45 A, 10 V → 10.1 A

### Gate charge, switching, reverse recovery, noise, distortion, breakdown (mos-gate-charge, mos-switching, mos-body-diode, mos-noise, mos-distortion, mos-breakdown)

| | mosfet/2N7000 | mosfet/BS170 | mosfet/IRF510 |
|---|---|---|---|
| conditions | VDD 10.0 V, RL 50 Ω, RG 25 Ω | VDD 10.0 V, RL 50 Ω, RG 25 Ω | VDD 25.0 V, RL 25 Ω, RG 25 Ω |
| Qg to VGS = 10 V (IG = 100 µA) | 322 pC | 337 pC | 8.58 nC |
| Qgs, to the plateau | 85.1 pC | 78.3 pC | 2.73 nC |
| Qgd, the plateau | 67.4 pC | 120 pC | 1.07 nC |
| plateau voltage | 3.49 V | 3.71 V | 4.29 V |
| td(on) | 6.83 ns | 5.73 ns | 14 ns |
| tr | 3.98 ns | 5.8 ns | 5.12 ns |
| td(off) | 17.4 ns | 13.2 ns | 26 ns |
| tf | 8.19 ns | 10.4 ns | 8.15 ns |
| IRM | -38.5 mA | -28.7 mA | -338 mA |
| trr | 385 ps | 287 ps | 338 ps |
| reverse recovery | absent (no transit time: a capacitive spike only) | absent (no transit time: a capacitive spike only) | absent (no transit time: a capacitive spike only) |
| en at 10 Hz (ID = 10 mA) | 2.42 nV/√Hz | 2.18 nV/√Hz | 193 pV/√Hz |
| en at 1 kHz | 2.42 nV/√Hz | 2.18 nV/√Hz | 193 pV/√Hz |
| 1/f | absent (no KF) | absent (no KF) | absent (no KF) |
| THD of a 10 mA stage, 100 mVpk | 75 m | 53.5 m | 305 m |
| IDSS at 60 V | 10 µA | 500 nA | 60 pA |
| IDSS at 100 V | 16.7 µA | 834 nA | 101 pA |
| breakdown | absent (leakage flat to 100 V) | absent (leakage flat to 100 V) | absent (leakage flat to 100 V) |

**Ciss against VDS (VGS = 0, 1 MHz)**

- 2N7000: 0 V → 27.9 pF, 1 V → 27.9 pF, 2 V → 27.9 pF, 5 V → 27.9 pF, 10 V → 27.9 pF, 15 V → 27.9 pF, 20 V → 27.9 pF, 25 V → 27.9 pF
- BS170: 0 V → 30.9 pF, 1 V → 30.9 pF, 2 V → 30.9 pF, 5 V → 30.9 pF, 10 V → 30.9 pF, 15 V → 30.9 pF, 20 V → 30.9 pF, 25 V → 30.9 pF
- IRF510: 0 V → 866 pF, 1 V → 866 pF, 2 V → 866 pF, 5 V → 866 pF, 10 V → 866 pF, 15 V → 866 pF, 20 V → 866 pF, 25 V → 866 pF

**Coss against VDS**

- 2N7000: 0 V → 58 pF, 1 V → 42.3 pF, 2 V → 35.4 pF, 5 V → 26.3 pF, 10 V → 20.6 pF, 15 V → 17.9 pF, 20 V → 16.2 pF, 25 V → 15 pF
- BS170: 0 V → 38 pF, 1 V → 27.7 pF, 2 V → 23.2 pF, 5 V → 17.3 pF, 10 V → 13.6 pF, 15 V → 11.7 pF, 20 V → 10.6 pF, 25 V → 9.86 pF
- IRF510: 0 V → 407 pF, 1 V → 284 pF, 2 V → 236 pF, 5 V → 176 pF, 10 V → 140 pF, 15 V → 123 pF, 20 V → 112 pF, 25 V → 105 pF

**Crss against VDS**

- 2N7000: 0 V → 4.48 pF, 1 V → 4.48 pF, 2 V → 4.48 pF, 5 V → 4.48 pF, 10 V → 4.48 pF, 15 V → 4.48 pF, 20 V → 4.48 pF, 25 V → 4.48 pF
- BS170: 0 V → 2.99 pF, 1 V → 2.99 pF, 2 V → 2.99 pF, 5 V → 2.99 pF, 10 V → 2.99 pF, 15 V → 2.99 pF, 20 V → 2.99 pF, 25 V → 2.99 pF
- IRF510: 0 V → 40.1 pF, 1 V → 40.1 pF, 2 V → 40.1 pF, 5 V → 40.1 pF, 10 V → 40.1 pF, 15 V → 40.1 pF, 20 V → 40.1 pF, 25 V → 40.1 pF

**Ciss against VGS at VDS = 0**

- 2N7000: 0 V → 27.9 pF, 2 V → 27.9 pF, 4 V → 27.9 pF, 6 V → 27.9 pF, 8 V → 27.9 pF, 10 V → 27.9 pF
- BS170: 0 V → 30.9 pF, 2 V → 30.9 pF, 4 V → 30.9 pF, 6 V → 30.9 pF, 8 V → 30.9 pF, 10 V → 30.9 pF
- IRF510: 0 V → 866 pF, 2 V → 866 pF, 4 V → 866 pF, 6 V → 866 pF, 8 V → 866 pF, 10 V → 866 pF

### RDS(on) against current and drive, third quadrant, inductive switching, follower (mos-rdson, mos-body-diode, mos-switching, mos-distortion)

| | mosfet/2N7000 | mosfet/BS170 | mosfet/IRF510 |
|---|---|---|---|
| RDS(on) vs ID at VGS = 10 V (A / Ω) | 10 m / 2.13 ; 100 m / 2.14 ; 500 m / 2.2 ; 1  / 2.29  | 10 m / 4 ; 100 m / 4.03 ; 500 m / 4.15 ; 1  / 4.38  | 10 m / 496 m; 100 m / 496 m; 500 m / 497 m; 1  / 498 m; 2  / 500 m; 4  / None |
| RDS(on) vs ID at VGS = 4.5 V | 10 m / 3.37 ; 100 m / 3.6 ; 500 m / None; 1  / None | 10 m / 6.07 ; 100 m / 6.47 ; 500 m / None; 1  / None | 10 m / 661 m; 100 m / 674 m; 500 m / 773 m; 1  / None; 2  / None; 4  / None |
| drive floor (RDS(on) < 2× its 10 V value) | 4.1 V | 3.85 V | 4.35 V |
| VSD at 100 mA with the channel on (VGS = 10 V) | 212 mV | 397 mV | 49.6 mV |
| VSD at 1 A, channel on | 850 mV | 1.2 V | 494 mV |
| inductive conditions | VDD 10.0 V, I 0.2 A (current source + freewheel diode), RG 25 Ω | VDD 10.0 V, I 0.2 A (current source + freewheel diode), RG 25 Ω | VDD 25.0 V, I 1.0 A (current source + freewheel diode), RG 25 Ω |
| Eon (clamped inductive) | 47.3 nJ | 73.1 nJ | 285 nJ |
| Eoff | 81.9 nJ | 85.2 nJ | 586 nJ |
| THD of a source follower, 1 Vpk, 10 mA | 618 µ | 936 µ | 137 µ |

### Temperature (mos-temperature)

| | mosfet/2N7000 | mosfet/BS170 | mosfet/IRF510 |
|---|---|---|---|
| Vth at 1 mA, −55 °C | 2.62 V | 2.01 V | 3.79 V |
| 100 °C | 2.5 V | 1.9 V | 3.64 V |
| 125 °C | 2.48 V | 1.88 V | 3.62 V |
| 150 °C | 2.46 V | 1.87 V | 3.6 V |
| 175 °C | 2.44 V | 1.85 V | 3.57 V |
| RDS(on) at 10 V, −55 °C | 1.96 Ω | 3.63 Ω | 487 mΩ |
| 125 °C | 2.36 Ω | 4.51 Ω | 508 mΩ |
| 175 °C | 2.49 Ω | 4.79 Ω | 515 mΩ |
| gfs at 100 mA, −55 °C | 204 mS | 152 mS | 881 mS |
| 125 °C | 148 mS | 106 mS | 656 mS |
| 175 °C | 138 mS | 98.3 mS | 615 mS |
| VSD at 100 mA, −55 °C | 868 mV | 843 mV | 832 mV |
| 125 °C | 589 mV | 499 mV | 533 mV |
| 175 °C | 507 mV | 399 mV | 446 mV |
| zero-TC point (VGS, ID) | 2.94 , 26.4 m | 2.26 , 10.8 m | 4.38 , 584 m |
| agreement | n/a (ngspice only here) | n/a (ngspice only here) | n/a (ngspice only here) |

### What the card says (mos-card)

| | 2N7000 | BS170 | IRF510 |
|---|---|---|---|
| family | subcircuit | subcircuit | card: NMOS |
| pins | 3 4 5 | 3 4 5 | (model card) |
| model types | D NMOS | D NMOS | NMOS |
| transistors (temperature and shot noise carriers) | 1 | 1 | 0 |
| behavioural sources | 0 | 0 | 0 |
| supply resistor RP | none | none | none |
| flicker noise (KF/AF) | absent | absent | absent |
| temperature coefficients (TC1/TC2/XTI/EG) | only the junctions' defaults | only the junctions' defaults | only the junctions' defaults |
| transit time (TT/TF) | absent | absent | present |
| breakdown (BV) | absent | absent | absent |

## Op-amps

Models: TL072 and RC4558 as TI publishes them (PSpice PARTS macromodels of 1989, Boyle family), NE5532 TI's PARTS macromodel of the same year as the LTwiki collection carries it. One amplifier each, ±15 V unless said, RL = 2 kΩ, CL = 100 pF for the dynamic decks.

### Supply, input and offset (opa-runs, opa-iq, opa-bias, opa-offset)

| | opamp/TL072 | opamp/NE5532 | opamp/RC4558 |
|---|---|---|---|
| IQ at ±5 V | 4.86 mA | 1.42 mA | 440 µA |
| IQ at ±9 V | 8.59 mA | 2.45 mA | 764 µA |
| IQ at ±15 V | 14.2 mA | 4 mA | 1.25 mA |
| IQ at ±18 V | 17 mA | 4.77 mA | 1.49 mA |
| VOS at ±15 V | 11 µV | 6.73 µV | -10.2 µV |
| VOS at ±5 V | 11 µV | 6.73 µV | -10.2 µV |
| IB+ | 45 pA | 498 nA | -140 nA |
| IB− | 45 pA | 498 nA | -140 nA |
| IOS | -3.5e-17 A | -70.4 pA | 31.6 pA |
| VICR− | -13.3 V | -12.8 V | -12.9 V |
| VICR+ | 13.3 V | 12.8 V | 12.9 V |
| CMRR (DC, from VOS vs VCM) | 89.9 dB | 93.9 dB | 94.3 dB |
| phase reversal within the rails | no | no | no |
| phase reversal 1 V beyond the rails | yes | yes | yes |

### Gain, bandwidth and rejection (opa-aol, opa-cmrr-f, opa-psrr-f)

| | opamp/TL072 | opamp/NE5532 | opamp/RC4558 |
|---|---|---|---|
| AOL (DC) | 106.0 dB | 99.8 dB | 109.3 dB |
| dominant pole | 16.1 Hz | 94.2 Hz | 10.7 Hz |
| GBW read at 10 kHz | 3.21 MHz | 9.21 MHz | 3.12 MHz |
| GBW read at 100 kHz | 3.21 MHz | 9.21 MHz | 3.12 MHz |
| unity-gain frequency (2 kΩ ‖ 100 pF) | 2.85 MHz | 7.98 MHz | 2.96 MHz |
| phase margin | 52.1 ° | 53.7 ° | 63 ° |
| CMRR at 100 Hz | 91.3 dB | 99.6 dB | 95.8 dB |
| CMRR at 1 kHz | 91.2 dB | 99.6 dB | 95.5 dB |
| CMRR at 100 kHz | 67.2 dB | 90.4 dB | 68.4 dB |
| PSRR+ at 100 Hz | 96.0 dB | 100.0 dB | 100.4 dB |
| PSRR+ at 10 kHz | 96.0 dB | 100.0 dB | 100.4 dB |
| PSRR− at 100 Hz | 96.0 dB | 100.0 dB | 100.4 dB |
| PSRR− at 10 kHz | 96.0 dB | 100.0 dB | 100.4 dB |

### Output (opa-swing, opa-isc, opa-zout)

| | opamp/TL072 | opamp/NE5532 | opamp/RC4558 |
|---|---|---|---|
| VOM+ into 600 Ω | 13.5 V | 13 V | 13 V |
| VOM+ into 2 kΩ | 13.5 V | 13 V | 13 V |
| VOM+ into 10 kΩ | 13.5 V | 13 V | 13 V |
| VOM− into 600 Ω | -13.5 V | -13 V | -13 V |
| VOM− into 2 kΩ | -13.5 V | -13 V | -13 V |
| ISC+ | 25.7 mA | 77.3 mA | 25.6 mA |
| ISC− | -25.7 mA | -77.3 mA | -25.6 mA |
| ZO closed-loop (G = 1) at 1 kHz | 43.5 mΩ | 2.71 mΩ | 37.7 mΩ |
| at 100 kHz | 4.35 Ω | 268 mΩ | 3.77 Ω |
| at 1 MHz | 44.1 Ω | 2.69 Ω | 37.1 Ω |
| ZO open-loop at 1 kHz | 150 Ω | 25.2 Ω | 125 Ω |
| ZO open-loop at 1 MHz | 150 Ω | 25 Ω | 125 Ω |

### Dynamics, noise and distortion (opa-slew, opa-step, opa-noise, opa-thd-f)

| | opamp/TL072 | opamp/NE5532 | opamp/RC4558 |
|---|---|---|---|
| SR rising (10 V step, G = 1) | 12.1 MV/s | 5.65 MV/s | 1.77 MV/s |
| SR falling | 12.4 MV/s | 5.52 MV/s | 1.81 MV/s |
| rise time 10–90 %, 10 mV step | 66.5 ns | 24.4 ns | 67.1 ns |
| overshoot, 10 mV step, 100 pF | 16.0 % | 14.1 % | 4.9 % |
| en at 10 Hz (RS = 0) | 12.5 nV/√Hz | 6.45 nV/√Hz | 12.3 nV/√Hz |
| en at 1 kHz | 12.5 nV/√Hz | 6.45 nV/√Hz | 12.3 nV/√Hz |
| en at 10 kHz | 12.5 nV/√Hz | 6.45 nV/√Hz | 12.3 nV/√Hz |
| THD at 1 kHz, 3 Vrms, 2 kΩ, G = 1 | 1.66 µ | 637 n | 1.96 µ |
| H2/H1 | 1.66 µ | 637 n | 1.96 µ |
| H3/H1 | 13.1 n | 6.67 n | 17.4 n |

### Large signal and settling (opa-settling, opa-overload, opa-max-vo-f, opa-thd-level, opa-aol-swing)

| | opamp/TL072 | opamp/NE5532 | opamp/RC4558 |
|---|---|---|---|
| settling to 0.1 %, 2 V step | 585 ns | 459 ns | 1.27 µs |
| to 0.01 %, 2 V | 743 ns | 519 ns | 1.38 µs |
| to 0.1 %, 10 V | 1.11 µs | 1.82 µs | 5.7 µs |
| to 0.01 %, 10 V | 1.27 µs | 1.88 µs | 5.82 µs |
| overload recovery, G = −10, 1.2·VS | 3.6 µs | 4.25 µs | 9.63 µs |
| output while overloaded | -13.5 V | -13 V | -13 V |
| full-power bandwidth from SR and VOM | 143 kHz | 69.4 kHz | 21.6 kHz |
| THD at 10 Vpk, 20 kHz | 78 µ | 30.7 µ | 280 µ |
| at 50 kHz | 201 µ | 136 µ | 119 m |
| at 100 kHz | 522 µ | 33 m | 119 m |
| output at 10 Vpk in, 100 kHz | 10 V | 9.83 V | 3.64 V |
| THD at 1 kHz, 0.1 Vrms | 55.2 n | 21.2 n | 65.3 n |
| 1 Vrms | 552 n | 212 n | 653 n |
| 6 Vrms | 3.32 µ | 1.28 µ | 3.93 µ |
| 10 Vrms (clipping) | 17.9 m | 34.1 m | 31.8 m |
| AOL over ±10 V (DC, 2 kΩ) | 199 kV/V | 97.9 kV/V | 294 kV/V |
| AOL over ±13 V | 199 kV/V | n/a | n/a |

### Closed loop, stability and the rest (opa-closed-loop, opa-stability, opa-noise-rs, opa-emirr, opa-separation)

| | opamp/TL072 | opamp/NE5532 | opamp/RC4558 |
|---|---|---|---|
| −3 dB bandwidth at G = 10 | 343 kHz | 993 kHz | 325 kHz |
| G = 100 | 32.3 kHz | 92.5 kHz | 31.3 kHz |
| G = 1000 | 3.22 kHz | 9.32 kHz | 3.13 kHz |
| G = −1 | 2.46 MHz | 6.62 MHz | 2.07 MHz |
| phase margin at CL = 10 pF | 64.1 ° | 59.9 ° | 73.7 ° |
| 100 pF | 52.1 ° | 53.7 ° | 63 ° |
| 1 nF | 18.7 ° | 23.2 ° | 27.2 ° |
| 10 nF | 5.5 ° | 5.73 ° | 8.63 ° |
| overshoot, 100 mV step, 100 pF | 15.8 % | 12.0 % | 3.7 % |
| 1 nF | 58.9 % | 46.2 % | 41.0 % |
| total noise at 1 kHz, RS = 1 kΩ | 13.2 nV/√Hz | 7.67 nV/√Hz | 13 nV/√Hz |
| RS = 10 kΩ | 18 nV/√Hz | 15.1 nV/√Hz | 18.1 nV/√Hz |
| RS = 100 kΩ | 42.6 nV/√Hz | 57.9 nV/√Hz | 48.1 nV/√Hz |
| RS = 1 MΩ | 129 nV/√Hz | 420 nV/√Hz | 249 nV/√Hz |
| in at 1 kHz, from RS = 100 kΩ | 8.42 fA/√Hz | 406 fA/√Hz | 224 fA/√Hz |
| EMIRR, 100 mVpk at 100 MHz | absent (no RF rectification in the model) | absent (no RF rectification in the model) | absent (no RF rectification in the model) |
| channel separation | absent (the subcircuit is one amplifier) | absent (the subcircuit is one amplifier) | absent (the subcircuit is one amplifier) |

### Against temperature, supply and common mode (opa-iq, opa-offset, opa-bias, opa-aol, opa-swing, opa-isc)

| | opamp/TL072 | opamp/NE5532 | opamp/RC4558 |
|---|---|---|---|
| turn-on: settled 10 mV after a ±3 → ±15 V ramp at 0.3 V/µs | 0 s | 0 s | 0 s |
| VOS at −55 °C | 11 µV | 6.96 µV | -10.7 µV |
| VOS at 125 °C | 10.9 µV | 5.81 µV | -8.46 µV |
| offset drift | absent (VOS does not move with temperature) | -6.41 nV/°C | 12.3 nV/°C |
| IB+ at −55 °C | 15.1 pA | 498 nA | -139 nA |
| IB+ at 125 °C | 1.16 µA | 499 nA | -140 nA |
| IB+ at VCM = −13 V | 32 pA | 221 nA | -169 nA |
| IB+ at VCM = +13 V | 58.1 pA | 789 nA | -110 nA |
| IQ at −55 °C | 14.2 mA | 4 mA | 1.25 mA |
| IQ at 125 °C | 14.2 mA | 4 mA | 1.25 mA |
| ZICM at 1 kHz | 498 GΩ | 200 MΩ | 713 MΩ |
| ZICM at 1 MHz | 498 GΩ | 200 MΩ | 713 MΩ |
| CICM | 3.19e-19 F | 7.96e-16 F | 2.23e-16 F |
| ZID at 1 kHz | 477 GΩ | 191 kΩ | 645 kΩ |
| ZID at 1 MHz | 480 GΩ | 191 kΩ | 645 kΩ |
| CMRR at 1 kHz, VCM = −13 V | n/a | n/a | n/a |
| VCM = +13 V | n/a | n/a | n/a |
| PSRR both rails, 100 Hz | 286.8 dB | 309.2 dB | 288.3 dB |
| 10 kHz | 247.2 dB | 271.4 dB | 248.5 dB |
| EMIRR at 10 MHz | absent | absent | absent |
| 400 MHz | absent | absent | absent |
| 1 GHz | absent | absent | 71.2 dB |
| AOL (DC) into 600 Ω | 103.7 dB | 99.4 dB | 107.3 dB |
| into 10 kΩ | 106.9 dB | 99.9 dB | 110.1 dB |
| at ±5 V | 106.0 dB | 99.8 dB | 109.3 dB |
| at ±9 V | 106.0 dB | 99.8 dB | 109.3 dB |
| at −55 °C | 106.0 dB | 101.2 dB | 110.8 dB |
| at 125 °C | 106.0 dB | 98.4 dB | 107.9 dB |
| GBW at 100 kHz, 600 Ω | 2.76 MHz | 8.95 MHz | 2.75 MHz |
| at ±5 V | 3.21 MHz | 9.21 MHz | 3.12 MHz |
| at −55 °C | 3.21 MHz | 10.8 MHz | 3.7 MHz |
| at 125 °C | 3.21 MHz | 7.83 MHz | 2.63 MHz |
| phase margin into 600 Ω | 57.8 ° | 54.6 ° | 67.1 ° |
| at ±5 V | 52.1 ° | 53.7 ° | 63 ° |
| at 125 °C | 52 ° | 57.7 ° | 66.8 ° |
| VOM+ at ±5 V | 3.48 V | 2.97 V | 3.04 V |
| VOM− at ±5 V | -3.48 V | -2.97 V | -3.04 V |
| VOM+ at ±9 V | 7.48 V | 6.97 V | 7.04 V |
| VOM+ at −55 °C | 13.6 V | 13.1 V | 13.2 V |
| VOM+ at 125 °C | 13.3 V | 12.8 V | 12.9 V |
| ISC+ at ±5 V | 25.7 mA | 77.3 mA | 25.6 mA |
| ISC+ at −55 °C | 25.8 mA | 77.6 mA | 25.8 mA |
| ISC+ at 125 °C | 25.5 mA | 77 mA | 25.5 mA |
| VOUT vs IOUT sourcing (A / V) | 1 m / 13.5 ; 5 m / 13.5 ; 10 m / 13.5 ; 20 m / 13.5 ; 40 m / -13.6 ; 80 m / -13.6  | 1 m / 13 ; 5 m / 13 ; 10 m / 13 ; 20 m / 13 ; 40 m / 13 ; 80 m / -13  | 1 m / 13 ; 5 m / 13 ; 10 m / 13 ; 20 m / 13 ; 40 m / -13.2 ; 80 m / -13.2  |
| ZO closed loop at 1 kHz, G = 10 | 435 mΩ | 27.2 mΩ | 377 mΩ |
| G = 100 | 4.35 Ω | 272 mΩ | 3.77 Ω |
| G = 1000 | 41.7 Ω | 2.67 Ω | 36 Ω |
| at 100 kHz, G = 10 | 41.9 Ω | 2.68 Ω | 36.2 Ω |

### Dynamics, the rest (opa-stability, opa-slew, opa-settling, opa-overload, opa-phase-reversal)

| | opamp/TL072 | opamp/NE5532 | opamp/RC4558 |
|---|---|---|---|
| peaking at G = 100, RT = 100 Ω | 0.0 dB | 0.0 dB | 0.0 dB |
| RT = 1 kΩ | 0.0 dB | 0.0 dB | 0.0 dB |
| RT = 10 kΩ | 0.0 dB | 0.0 dB | 0.0 dB |
| RT = 100 kΩ | 0.0 dB | 0.0 dB | 0.0 dB |
| SR at G = −1, 100 pF | 12.2 MV/s | 5.51 MV/s | 1.78 MV/s |
| SR at G = 1, 20 pF | 12.1 MV/s | 5.65 MV/s | 1.77 MV/s |
| SR, 2 V step | 10.7 MV/s | 5.54 MV/s | 1.77 MV/s |
| SR, 20 V step | 12.1 MV/s | 5.79 MV/s | 1.77 MV/s |
| SR at ±5 V (4 V step) | 11.8 MV/s | 5.57 MV/s | 1.77 MV/s |
| SR at 125 °C | 12.2 MV/s | 5.66 MV/s | 1.77 MV/s |
| settling to 0.1 %, 10 V, G = −1 | 1.05 µs | 1.86 µs | 5.81 µs |
| to 0.01 % | 1.21 µs | 1.93 µs | 5.96 µs |
| positive overload recovery | 3.61 µs | 4.25 µs | 9.64 µs |
| input current at +16 V | 63.7 pA | 551 µA | 49.3 pA |
| at −16 V | -374 µA | -33.3 pA | -160 µA |
| at +14 V | 59.7 pA | 1.07 µA | 43.3 pA |

### Noise, weighted and integrated (opa-noise, opa-noise-rs)

| | opamp/TL072 | opamp/NE5532 | opamp/RC4558 |
|---|---|---|---|
| en rms 0.1–10 Hz | 39.4 nV | 20.3 nV | 38.7 nV |
| en p-p 0.1–10 Hz (6.6 × rms) | 260 nV | 134 nV | 255 nV |
| en rms 10 Hz–10 kHz | 1.25 µV | 645 nV | 1.23 µV |
| en rms 20 Hz–20 kHz | 1.77 µV | 912 nV | 1.74 µV |
| en at 1 kHz, ±5 V | 12.5 nV/√Hz | 6.45 nV/√Hz | 12.3 nV/√Hz |
| flat 20 Hz–20 kHz, RS = 300 Ω | 1.8 µV | 966 nV | 1.77 µV |
| A-weighted, RS = 300 Ω | 1.42 µV | 764 nV | 1.4 µV |
| RIAA-weighted (30 kHz), RS = 2.2 kΩ | 1.3 µV | 835 nV | 1.28 µV |
| A-weighted, RS = 2.2 kΩ | 1.55 µV | 999 nV | 1.54 µV |

### Distortion against frequency, load, and intermodulation (opa-thd-f, opa-thd-load, opa-imd)

| | opamp/TL072 | opamp/NE5532 | opamp/RC4558 |
|---|---|---|---|
| THD at 20 Hz, 3 Vrms, G = 1 | 175 n | 118 n | 126 n |
| 100 Hz | 238 n | 133 n | 229 n |
| 1 kHz | 1.66 µ | 637 n | 1.96 µ |
| 10 kHz | 16.5 µ | 6.27 µ | 20.1 µ |
| 20 kHz | 33 µ | 12.6 µ | 50.5 µ |
| THD at 1 kHz, 1 Vrms, G = 1 | 552 n | 212 n | 653 n |
| 20 kHz, 1 Vrms, G = 1 | 11 µ | 4.18 µ | 13.5 µ |
| THD at 1 kHz, 3 Vrms, G = 10 | 1.67 µ | 631 n | 1.98 µ |
| 10 kHz, G = 10 | 16.7 µ | 6.39 µ | 41.6 µ |
| 20 kHz, G = 10 | 33.4 µ | 15.6 µ | 306 µ |
| 20 Hz, G = 10 | 53.4 n | 66.2 n | 50.3 n |
| THD at 1 kHz, 3 Vrms into 100 Ω | 182 m | 786 n | 183 m |
| output into 100 Ω (3 Vrms in) | 3.06 V | 4.24 V | 3.05 V |
| into 300 Ω | 2.31 µ | 682 n | 2.61 µ |
| into 600 Ω | 1.92 µ | 656 n | 2.23 µ |
| into 10 kΩ | 1.57 µ | 631 n | 1.87 µ |
| IMD SMPTE (60 Hz + 7 kHz 4:1, 3 Vrms) | 13.1 µ | 4.97 µ | 15.5 µ |
| IMD CCIF (19 + 20 kHz, 3 Vrms) | 747 n | 840 n | 21.1 µ |

### What the model text says (opa-card)

| | TL072 | NE5532 | RC4558 |
|---|---|---|---|
| family | subcircuit | Boyle macromodel (PSpice PARTS) | Boyle macromodel (PSpice PARTS) |
| pins | 1 2 3 4 5 | 1 2 3 4 50 | 1 2 3 4 5 |
| model types | D PJF | D NPN | D PNP |
| transistors (temperature and shot noise carriers) | 2 | 2 | 2 |
| behavioural sources | 5 | 7 | 5 |
| supply resistor RP | 2.143E3 | 7.757E3 | 24.67E3 |
| flicker noise (KF/AF) | absent | absent | absent |
| temperature coefficients (TC1/TC2/XTI/EG) | only the junctions' defaults | only the junctions' defaults | only the junctions' defaults |
| transit time (TT/TF) | absent | absent | absent |
| breakdown (BV) | absent | absent | absent |

## What the models cannot do, as the numbers say it

- The three JFET cards have no 1/f noise term (KF): en is flat to 10 Hz and the corner the bench finds is the card's thermal floor meeting its own flat value, not a 1/f corner. Their gate leakage at −15 V is the card's IS (30 pA), not a measured IGSS. The 2N3819 card has LAMBDA = 0.02 and draws the Early slope; the J201 card's LAMBDA gives ro of megohms.
- The MOSFET cards' Ciss and Crss do not move with VDS (level 1 and 3 give Cgs and Cgd as constants per width); only Coss, which is the body-diode junction, falls with voltage. None recovers in reverse: the body diode's current collapses in a capacitive spike, because a level-3 card's TT is not read and the Zetex and Diodes subcircuits give their diode none. None breaks down: the current at 100 V is the leakage at 60 V scaled by the card's RDS or IS. The 2N7000 subcircuit leaks 10 µA at 60 V through a resistor across the channel.
- The op-amp macromodels (Boyle family, 1989) give one VOS whatever the supply or common mode, bias currents equal on both inputs, PSRR flat with frequency (the supply enters only through the output stage's clamps), an output swing that does not depend on the load (13.5 V into 600 Ω as into 10 kΩ), no distortion beyond slew and clipping (THD of a few parts per million at 3 Vrms), and a white noise density only. The TL072 model's supply current scales with the supply through its RP resistor: 14 mA at ±15 V where the sheet's amplifier draws 1.4 mA, which is a known trait of the PARTS macromodels and the first thing a reader of the page should see.
- All three op-amp models reverse the output's phase when the input goes 1 V beyond a rail, and none within the rails. With both rails modulated in antiphase the PSRR reads above 240 dB: the macromodel's supply paths are symmetric and cancel, which no real part does. The gain peaking against the feedback network's resistance (RT) is zero at every RT because the model has no input capacitance to speak of (CICM below a femtofarad).
- The clamped-inductive switching deck is the fixture with the inductor replaced by a current source and a freewheel diode; the 2N7000 and BS170 subcircuits' Eon/Eoff are what their level-1 channel plus a constant Cgd give.

## Next

The same decks in QSPICE and LTspice on the maintainer's machine, through `measurements.yaml` entries so the numbers carry their conditions and the catalogue version; the transients of the FET benches (switching, gate charge, reverse recovery), the op-amps' settling, overload, max VO vs f and channel separation; and the datasheet figures of the survey beside each number.
