# Characterising the op-amp SPICE models

The op-amp bench, specified before it is built: a catalogue of measurements at universal conditions, the
same for every macromodel, drawn from what the makers' own data sheets measure. It follows the transistor
bench ([model-characterisation.md](model-characterisation.md)) in its principles and its format, and it
differs where a macromodel differs from a transistor card: a macromodel is a subcircuit with five or more
pins that often has no noise sources, no temperature terms and an idealised output stage, so the bench has
to report what a model *cannot* do as a finding, the way `bjt-breakdown` does.

Status: this page is the specification and the evidence behind it. The entries of
`data/bench/measurements.yaml` (kind `opamp`), the decks, the drawings and the runs are the next step; until
then [model-characterisation.md](model-characterisation.md) lists op-amp macromodels under "What is not
measured".

## Principles

The transistor bench's five principles hold unchanged — behaviour only, intrinsic ladders, numbers not
opinions, explained once per measurement, reproducible — with three additions:

- **Absences are results.** Most macromodels give one offset voltage whatever the temperature, no noise,
  no input current change with common mode and no distortion beyond slew and clipping. Each measurement
  says which of its numbers can come out `absent` and from what in the card (`opamp-card` reads it), so a
  reader sees "this model has no noise" and not a simulator default.
- **Every maker's condition is run, not one chosen.** The sheets fix the same quantity at different
  supplies (±15 V, ±5 V, 36 V single), loads (600 Ω, 2 kΩ, 10 kΩ), capacitive loads (20 pF, 100 pF) and
  levels (1, 3, 6 Vrms); a model is measured at all of them, and the one a sheet quotes is read off the
  ladder. The ladders below come from the survey, not from a preferred sheet.
- **Model against model where no sheet gives a number.** Distortion, settling and channel separation are
  published for comparison between models of a part; the sheet's own figure, when the sheet has one, is
  shown beside it with its conditions.

## What the makers' sheets measure

The survey (`make datasheets-survey`, `sei datasheets survey --kind opamp`) reads a set of sheets chosen
from the top of the index's usage list and widened across makers — TI's four formats (Burr-Brown, National,
legacy and post-2015), onsemi's Motorola and Fairchild sheets, and two Chinese makers' readings of the same
parts, UMW's (which keep the format of the maker each part is named after) and 3PEAK's own designs — and
publishes every figure's title, the
test it draws and the conditions printed beside it (`data/datasheets/survey/opamp/`). The registry
`data/datasheets/survey/opamp.yaml` says how each sheet is reached, and which are not: Nisshinbo's
robots.txt disallows every PDF and Microchip's the whole site to scripts, so those sheets are linked and not
read; ST, Analog Devices and Rohm refuse scripts and are read from the Internet Archive's capture of their
own address when the archive can be reached. A sheet a person opened in a browser is handed to the survey
with `--deliver id=file` and read like any other, its link and checksum published and the copy noted as
"by hand": the OP27 (Analog Devices), the TL072 (ST), the BA4558 (Rohm) and the NJM2068 (Nisshinbo) came
that way.

<!-- survey:start -->

Survey of 73 sheets read by `sei datasheets survey --kind opamp` (reader `survey-1`), 2149 figure titles, 1814 mapped to a test; the tables `data/datasheets/survey/opamp/{sheets,figures,matrix,conditions}.csv` hold every row.

| sheet | maker | document | revision | date | pages | figures | mapped | read from |
|---|---|---|---|---|---|---|---|---|
| [TL072](https://www.ti.com/lit/ds/symlink/tl072.pdf) | ti | SLOS080W | W | JULY 2025 | 89 | 72 | 60 | maker's site |
| [TL082](https://www.ti.com/lit/ds/symlink/tl082.pdf) | ti | SLOS081O | O | SEPTEMBER 2025 | 78 | 51 | 39 | maker's site |
| [TL062](https://www.ti.com/lit/ds/symlink/tl062.pdf) | ti | SLOS078N | N | AUGUST 2023 | 58 | 36 | 18 | maker's site |
| [NE5532](https://www.ti.com/lit/ds/symlink/ne5532.pdf) | ti | SLOS075K | K | DECEMBER 2025 | 23 | 10 | 6 | maker's site |
| [NE5534](https://www.ti.com/lit/ds/symlink/ne5534.pdf) | ti | SLOS070D | D | September 2004 | 27 | 16 | 12 | maker's site |
| [LM324](https://www.ti.com/lit/ds/symlink/lm324.pdf) | ti | SLOS066AE | AE | SEPTEMBER 2025 | 65 | 49 | 42 | maker's site |
| [LM358](https://www.ti.com/lit/ds/symlink/lm358.pdf) | ti | SLOS068AB | AB | OCTOBER 2024 | 68 | 57 | 51 | maker's site |
| [LM833](https://www.ti.com/lit/ds/symlink/lm833.pdf) | ti | SLOS481B | B | July 2010 | 36 | 47 | 43 | maker's site |
| [LF353](https://www.ti.com/lit/ds/symlink/lf353.pdf) | ti | SLOS012C | C | August 1994 | 21 | 8 | 5 | maker's site |
| [LF356](https://www.ti.com/lit/ds/symlink/lf356.pdf) | ti | SNOSBH0D | D | March 2013 | 47 | 62 | 38 | maker's site |
| [LF411](https://www.ti.com/lit/ds/symlink/lf411.pdf) | ti | SLOS011D | D | OCTOBER 2025 | 16 | 0 |  | maker's site |
| [LM741](https://www.ti.com/lit/ds/symlink/lm741.pdf) | ti |  | D | March 2013 | 17 | 3 | 0 | maker's site |
| [RC4558](https://www.ti.com/lit/ds/symlink/rc4558.pdf) | ti | SLOS073H | H | OCTOBER 2024 | 37 | 35 | 31 | maker's site |
| [MC33078](https://www.ti.com/lit/ds/symlink/mc33078.pdf) | ti | SLLS633C | C | NOVEMBER 2006 | 27 | 32 | 31 | maker's site |
| [LM4562](https://www.ti.com/lit/ds/symlink/lm4562.pdf) | ti | SNAS326K | K | DECEMBER 2013 | 43 | 90 | 70 | maker's site |
| [LME49720](https://www.ti.com/lit/ds/symlink/lme49720.pdf) | ti | SNAS393D | D | April 2013 | 49 | 134 | 113 | maker's site |
| [OPA134](https://www.ti.com/lit/ds/symlink/opa134.pdf) | ti | SBOS058B | B | NOVEMBER 2024 | 35 | 33 | 27 | maker's site |
| [OPA604](https://www.ti.com/lit/ds/symlink/opa604.pdf) | ti | SBOS019A | A | SEPTEMBER 2003 | 21 | 21 | 12 | maker's site |
| [OPA627](https://www.ti.com/lit/ds/symlink/opa627.pdf) | ti | SBOS165C | C | JANUARY 2025 | 46 | 47 | 36 | maker's site |
| [OPA1612](https://www.ti.com/lit/ds/symlink/opa1612.pdf) | ti | SBOS450C | C | August 2009 | 34 | 36 | 31 | maker's site |
| [OPA1642](https://www.ti.com/lit/ds/symlink/opa1642.pdf) | ti | SBOS484D | D | April 2010 | 50 | 44 | 38 | maker's site |
| [OPA1656](https://www.ti.com/lit/ds/symlink/opa1656.pdf) | ti | SBOS901C | C | SEPTEMBER 2022 | 42 | 61 | 49 | maker's site |
| [OPA1678](https://www.ti.com/lit/ds/symlink/opa1678.pdf) | ti | SBOS855E | E | DECEMBER 2022 | 57 | 48 | 34 | maker's site |
| [OPA277](https://www.ti.com/lit/ds/symlink/opa277.pdf) | ti | SBOS079C | C | FEBRUARY 2023 | 43 | 38 | 27 | maker's site |
| [OP27](https://www.ti.com/lit/ds/symlink/op27.pdf) | ti | SLOS100E | E | FEBRUARY 2010 | 25 | 31 | 29 | maker's site |
| [LM318](https://www.ti.com/lit/ds/symlink/lm318.pdf) | ti | SLOS063B | B | DECEMBER 2002 | 16 | 1 | 1 | maker's site |
| [TLC272](https://www.ti.com/lit/ds/symlink/tlc272.pdf) | ti | SLOS091F | F | JANUARY 2026 | 36 | 27 | 21 | maker's site |
| [LM3900](https://www.ti.com/lit/ds/symlink/lm3900.pdf) | ti | SLOS059 |  | SEPTEMBER 1990 | 17 | 14 | 12 | maker's site |
| [MC33078](https://www.onsemi.com/download/data-sheet/pdf/mc33078-d.pdf) | onsemi | MC33078/D | 10 | July, 2025 | 19 | 36 | 34 | maker's site |
| [MC33178](https://www.onsemi.com/download/data-sheet/pdf/mc33178-d.pdf) | onsemi | MC33178/D | 7 | October, 2006 | 19 | 38 | 35 | maker's site |
| [LM358](https://www.onsemi.com/download/data-sheet/pdf/lm358-d.pdf) | onsemi | LM358/D | 36 | September, 2024 | 16 | 15 | 7 | maker's site |
| [LM324](https://www.onsemi.com/download/data-sheet/pdf/lm324-d.pdf) | onsemi | LM324/D | 31 | October, 2021 | 15 | 16 | 7 | maker's site |
| [NE5532](https://www.onsemi.com/download/data-sheet/pdf/ne5532-d.pdf) | onsemi | NE5532/D | 2 | September, 2013 | 11 | 11 | 9 | maker's site |
| [LM833](https://www.onsemi.com/download/data-sheet/pdf/lm833-d.pdf) | onsemi | LM833/D | 8 | July, 2025 | 11 | 24 | 23 | maker's site |
| [MC34071](https://www.onsemi.com/download/data-sheet/pdf/mc34071-d.pdf) | onsemi | MC34071/D | 24 | October, 2021 | 26 | 64 | 36 | maker's site |
| [MC33272A](https://www.onsemi.com/download/data-sheet/pdf/mc33272a-d.pdf) | onsemi | MC33272A/D | 15 | July, 2025 | 21 | 36 | 36 | maker's site |
| [NCS20071](https://www.onsemi.com/download/data-sheet/pdf/ncs20071-d.pdf) | onsemi | NCS20071/D | 15 | February, 2026 | 29 | 30 | 27 | maker's site |
| [LM2902A](https://www.onsemi.com/download/data-sheet/pdf/lm2902a-d.pdf) | onsemi |  | 1.0 |  | 14 | 12 | 12 | maker's site |
| [LM301A](https://www.onsemi.com/download/data-sheet/pdf/lm301a-d.pdf) | onsemi | LM301A/D | 12 | July, 2025 | 11 | 15 | 13 | maker's site |
| [MC1458](https://www.onsemi.com/download/data-sheet/pdf/mc1458-d.pdf) | onsemi | MC1458/D | 2 | March, 2001 | 9 | 15 | 13 | maker's site |
| [MC33077](https://www.onsemi.com/download/data-sheet/pdf/mc33077-d.pdf) | onsemi | MC33077/D | 6 | July, 2025 | 17 | 38 | 36 | maker's site |
| [MC33171](https://www.onsemi.com/download/data-sheet/pdf/mc33171-d.pdf) | onsemi | MC33171/D | 14 | July, 2025 | 20 | 15 | 9 | maker's site |
| [MC33201](https://www.onsemi.com/download/data-sheet/pdf/mc33201-d.pdf) | onsemi | MC33201/D | 19 | October, 2021 | 16 | 29 | 27 | maker's site |
| [MC33501](https://www.onsemi.com/download/data-sheet/pdf/mc33501-d.pdf) | onsemi | MC33501/D | 10 | July, 2006 | 15 | 36 | 30 | maker's site |
| [MC4558](https://www.onsemi.com/download/data-sheet/pdf/mc4558-d.pdf) | onsemi |  | 5 |  | 9 | 11 | 11 | maker's site |
| [NE5534](https://www.onsemi.com/download/data-sheet/pdf/ne5534-d.pdf) | onsemi | NE5534/D | 4 | December, 2024 | 12 | 17 | 14 | maker's site |
| [OP27](https://www.analog.com/media/en/technical-documentation/data-sheets/OP27.pdf) | adi |  | H |  | 21 | 48 | 35 | opened by a person |
| [OP37](https://www.analog.com/media/en/technical-documentation/data-sheets/OP37.pdf) | adi |  |  |  |  |  |  | not fetched yet |
| [OP07](https://www.analog.com/media/en/technical-documentation/data-sheets/OP07.pdf) | adi |  |  |  |  |  |  | not fetched yet |
| [OP275](https://www.analog.com/media/en/technical-documentation/data-sheets/OP275.pdf) | adi |  |  |  |  |  |  | not fetched yet |
| [AD797](https://www.analog.com/media/en/technical-documentation/data-sheets/AD797.pdf) | adi |  |  |  |  |  |  | not fetched yet |
| [AD712](https://www.analog.com/media/en/technical-documentation/data-sheets/AD712.pdf) | adi |  |  |  |  |  |  | not fetched yet |
| [AD8597](https://www.analog.com/media/en/technical-documentation/data-sheets/AD8597_8599.pdf) | adi |  |  |  |  |  |  | not fetched yet |
| [AD825](https://www.analog.com/media/en/technical-documentation/data-sheets/AD825.pdf) | adi |  |  |  |  |  |  | not fetched yet |
| [ADA4898](https://www.analog.com/media/en/technical-documentation/data-sheets/ADA4898-1_4898-2.pdf) | adi |  |  |  |  |  |  | not fetched yet |
| LT1028 | adi |  |  |  |  |  |  | not fetched yet |
| LT1115 | adi |  |  |  |  |  |  | not fetched yet |
| [TL072](https://www.st.com/resource/en/datasheet/tl072.pdf) | st |  | 8 | June 2014 | 16 | 21 | 18 | opened by a person |
| [NE5532](https://www.st.com/resource/en/datasheet/ne5532.pdf) | st |  |  |  |  |  |  | not fetched yet |
| [LM358](https://www.st.com/resource/en/datasheet/lm358.pdf) | st |  |  |  |  |  |  | not fetched yet |
| [TS922](https://www.st.com/resource/en/datasheet/ts922.pdf) | st |  |  |  |  |  |  | not fetched yet |
| [LM833](https://www.st.com/resource/en/datasheet/lm833.pdf) | st |  |  |  |  |  |  | not fetched yet |
| [TL084](https://www.st.com/resource/en/datasheet/tl084.pdf) | st |  |  |  |  |  |  | not fetched yet |
| [BA4558](https://fscdn.rohm.com/en/products/databook/datasheet/ic/amp_linear/opamp/ba4558xxx-e.pdf) | rohm |  | 003 |  | 29 | 44 | 44 | opened by a person |
| BA15218 | rohm |  |  |  |  |  |  | not fetched yet |
| BA10358 | rohm |  |  |  |  |  |  | not fetched yet |
| BA4560 | rohm |  |  |  |  |  |  | not fetched yet |
| [CA3140](https://www.renesas.com/us/en/document/dst/ca3140-ca3140a-datasheet) | renesas |  |  |  |  |  |  | not read: HTTP 403 |
| [CA3130](https://www.renesas.com/us/en/document/dst/ca3130-ca3130a-datasheet) | renesas |  |  |  |  |  |  | not read: HTTP 403 |
| CA3140 | renesas |  |  |  |  |  |  | not fetched yet |
| CA3130 | renesas |  |  |  |  |  |  | not fetched yet |
| [NJM4580](https://www.umw-ic.com/static/pdf/3fb7399a74ea65a686b0dd3b99ab915e.pdf) | umw |  |  |  | 8 | 6 | 6 | maker's site |
| [LM358](https://www.umw-ic.com/static/pdf/989d9d9c30a14e30242b4cc708213fdf.pdf) | umw |  |  |  | 11 | 6 | 6 | maker's site |
| [LM2904](https://www.umw-ic.com/static/pdf/9311660af74322a9f7f261a5abc03f5f.pdf) | umw |  |  |  | 9 | 13 | 13 | maker's site |
| [LM2902](https://www.umw-ic.com/static/pdf/749d36fe6f677a887addd4ac20f10a46.pdf) | umw |  |  |  | 13 | 8 | 8 | maker's site |
| [OPA277](https://www.umw-ic.com/static/pdf/d27508c041995d9cc3a342089caba6ea.pdf) | umw |  |  |  | 15 | 23 | 23 | maker's site |
| [TLC2272](https://www.umw-ic.com/static/pdf/29f67d21a27790ec1689d6fa18cddd16.pdf) | umw |  |  |  | 30 | 57 | 57 | maker's site |
| [MCP6002](https://www.umw-ic.com/static/pdf/f93fc427e29bccb5282e7f18e746b7b1.pdf) | umw |  |  |  | 17 | 21 | 21 | maker's site |
| [AD8542](https://www.umw-ic.com/static/pdf/b36119e8c620dbec3fbb2c16b1913e60.pdf) | umw |  |  |  | 24 | 8 | 8 | maker's site |
| [OP2177](https://www.umw-ic.com/static/pdf/927224c365e0f3cb1db31b04c8cdae58.pdf) | umw |  |  |  | 17 | 44 | 44 | maker's site |
| [TSV912](https://www.umw-ic.com/static/pdf/85b4d26c12c9d2898d845ba3190223ed.pdf) | umw |  |  |  | 26 | 29 | 27 | maker's site |
| [TSZ122](https://www.umw-ic.com/static/pdf/42d1b690a778470622f39134b72d817e.pdf) | umw |  |  |  | 21 | 35 | 35 | maker's site |
| [OPA348](https://www.umw-ic.com/static/pdf/51ae346b884632fd3756b4003d788601.pdf) | umw |  |  |  | 15 | 18 | 18 | maker's site |
| [TP07A](https://static.3peak.com/res/doc/ds/Datasheet_TP07A.pdf) | 3peak |  |  |  | 14 | 16 | 16 | maker's site |
| [TP27](https://static.3peak.com/res/doc/ds/Datasheet_TP27.pdf) | 3peak |  |  |  | 14 | 16 | 16 | maker's site |
| [TP2272](https://static.3peak.com/res/doc/ds/Datasheet_TP2271-TP2272-TP2274.pdf) | 3peak |  |  |  | 24 | 22 | 20 | maker's site |
| [TP5532](https://static.3peak.com/res/doc/ds/Datasheet_TP5531-TP5532-TP5534.pdf) | 3peak |  |  |  | 30 | 22 | 19 | maker's site |
| [TP5552](https://static.3peak.com/res/doc/ds/Datasheet_TP5551-TP5552-TP5554.pdf) | 3peak |  | B |  | 22 | 9 | 8 | maker's site |
| [TP5592](https://static.3peak.com/res/doc/ds/Datasheet_TP5591-TP5592-TP5594.pdf) | 3peak |  |  |  | 26 | 14 | 11 | maker's site |
| [TP6002](https://static.3peak.com/res/doc/ds/Datasheet_TP6001-TP6002-TP6004.pdf) | 3peak |  |  |  | 26 | 20 | 18 | maker's site |
| [TP2302](https://static.3peak.com/res/doc/ds/Datasheet_TP2301-TP2302-TP2304.pdf) | 3peak |  |  |  | 22 | 19 | 19 | maker's site |
| [TP1242](https://static.3peak.com/res/doc/ds/Datasheet_TP1241L1-TP1242L1.pdf) | 3peak |  |  |  | 18 | 18 | 18 | maker's site |
| [LM358A](https://static.3peak.com/res/doc/ds/Datasheet_LM321A-LM358A-LM324A.pdf) | 3peak |  |  |  | 24 | 15 | 15 | maker's site |
| [LM2904A](https://static.3peak.com/res/doc/ds/Datasheet_LM2904A-LM2902A.pdf) | 3peak |  |  |  | 18 | 10 | 10 | maker's site |
| [TP2582](https://static.3peak.com/res/doc/ds/Datasheet_TP2581-TP2582-TP2584.pdf) | 3peak |  | A |  | 18 | 16 | 16 | maker's site |
| [NJM2068](https://www.nisshinbo-microdevices.co.jp/en/pdf/datasheet/NJM2068_E.pdf) | nisshinbo |  | 20260727 |  | 5 | 10 | 10 | opened by a person |
| [NJM4558](https://www.nisshinbo-microdevices.co.jp/en/pdf/datasheet/NJM4558_E.pdf) | nisshinbo |  |  |  |  |  |  | not read: robots.txt disallows *.pdf to every agent |
| [NJM4580](https://www.nisshinbo-microdevices.co.jp/en/pdf/datasheet/NJM4580_E.pdf) | nisshinbo |  |  |  |  |  |  | not read: robots.txt disallows *.pdf to every agent |
| [NJM5532](https://www.nisshinbo-microdevices.co.jp/en/pdf/datasheet/NJM5532_E.pdf) | nisshinbo |  |  |  |  |  |  | not read: robots.txt disallows *.pdf to every agent |
| [MCP6001](https://ww1.microchip.com/downloads/en/DeviceDoc/21733j.pdf) | microchip |  |  |  |  |  |  | not read: robots.txt disallows the whole site to every agent |

Tests by category: how many of the 73 sheets draw each, in all and per maker (3peak 12, adi 1, nisshinbo 1, onsemi 18, rohm 1, st 1, ti 27, umw 12); `bench` is the measurement that draws the same graph for a model.

| test | bench | sheets | 3peak | adi | nisshinbo | onsemi | rohm | st | ti | umw |
|---|---|---|---|---|---|---|---|---|---|---|
| **A supply** | | |  |  |  |  |  |  |  |  |
| `iq_vs_vs` | `opamp-iq` | 44 | 7 | 1 | 1 | 11 | 1 |  | 15 | 8 |
| `iq_vs_t` | `opamp-iq` | 36 | 9 |  | 1 | 3 | 1 | 1 | 16 | 5 |
| `pd_vs_t` | `none` | 12 |  |  |  | 7 | 1 | 1 | 3 |  |
| `pd_vs_vs` | `none` | 1 |  |  |  |  |  |  | 1 |  |
| `vs_range` | `opamp-runs` | 1 |  |  |  | 1 |  |  |  |  |
| **B input DC** | | |  |  |  |  |  |  |  |  |
| `vos_distribution` | `opamp-offset` | 19 | 4 |  |  | 2 |  |  | 7 | 6 |
| `vos_drift_distribution` | `opamp-offset` | 3 |  |  |  |  |  |  |  | 3 |
| `vos_warmup` | `opamp-offset` | 6 |  | 1 |  |  |  |  | 3 | 2 |
| `vos_longterm` | `opamp-offset` | 5 |  | 1 |  |  |  | 1 | 3 |  |
| `vos_thermal_shock` | `opamp-offset` | 1 |  | 1 |  |  |  |  |  |  |
| `vos_vs_t` | `opamp-offset` | 30 | 7 | 1 | 1 | 6 | 1 |  | 11 | 3 |
| `vos_vs_vcm` | `opamp-offset` | 21 | 10 |  |  | 1 | 1 |  | 6 | 3 |
| `vos_vs_vs` | `opamp-offset` | 10 |  |  |  | 1 | 1 |  | 6 | 2 |
| `vos_adjust` | `none` | 11 |  | 1 |  | 3 |  |  | 7 |  |
| `ib_vs_t` | `opamp-bias` | 40 | 4 | 1 | 1 | 8 | 1 | 1 | 18 | 6 |
| `ib_vs_vcm` | `opamp-bias` | 23 | 1 |  |  | 7 |  |  | 13 | 2 |
| `ib_vs_vs` | `opamp-bias` | 11 |  |  |  | 5 | 1 |  | 4 | 1 |
| `ios_vs_t` | `opamp-bias` | 4 |  | 1 |  |  | 1 |  | 2 |  |
| `ios_vs_vcm` | `opamp-bias` | 1 |  |  |  |  |  |  | 1 |  |
| `ios_vs_vs` | `opamp-bias` | 1 |  |  |  |  | 1 |  |  |  |
| **C range and rejection** | | |  |  |  |  |  |  |  |  |
| `vicr_vs_t` | `opamp-offset` | 7 |  |  |  | 6 |  |  |  | 1 |
| `vicr_vs_vs` | `opamp-offset` | 4 |  | 1 |  | 1 |  |  | 1 | 1 |
| `cmrr_vs_f` | `opamp-cmrr-f` | 47 | 12 | 1 |  | 9 |  |  | 18 | 7 |
| `cmrr_vs_t` | `opamp-offset` | 21 | 3 |  |  |  | 1 | 1 | 11 | 5 |
| `cmrr_vs_vcm` | `opamp-offset` | 1 |  |  |  |  |  |  | 1 |  |
| `psrr_vs_f` | `opamp-psrr-f` | 31 | 9 | 1 |  | 9 |  |  | 9 | 3 |
| `psrr_vs_t` | `opamp-offset` | 15 | 3 |  |  | 1 | 1 |  | 7 | 3 |
| `psrr_vs_vs` | `opamp-offset` | 1 |  |  |  |  |  |  | 1 |  |
| `emirr_vs_f` | `opamp-emirr` | 19 | 9 |  |  |  |  |  | 9 | 1 |
| **D gain and frequency** | | |  |  |  |  |  |  |  |  |
| `aol_phase_vs_f` | `opamp-aol` | 61 | 10 | 1 |  | 17 | 1 | 1 | 23 | 8 |
| `closed_loop_gain_vs_f` | `opamp-closed-loop` | 21 |  |  | 1 | 6 |  |  | 11 | 3 |
| `aol_vs_t` | `opamp-aol` | 24 | 1 |  |  | 8 |  | 1 | 13 | 1 |
| `aol_vs_vs` | `opamp-aol-swing` | 13 |  | 1 |  | 6 |  |  | 5 | 1 |
| `aol_vs_rl` | `opamp-aol-swing` | 3 |  | 1 |  |  |  |  | 1 | 1 |
| `aol_vs_vo` | `opamp-aol-swing` | 1 |  |  |  |  |  |  |  | 1 |
| `gbw_vs_vs` | `opamp-aol` | 7 |  |  |  | 3 |  |  | 3 | 1 |
| `gbw_vs_t` | `opamp-aol` | 18 | 1 | 1 |  | 9 |  |  | 6 | 1 |
| `phase_margin_vs_cl` | `opamp-stability` | 11 |  |  |  | 3 |  |  | 6 | 2 |
| `phase_margin_vs_rs` | `opamp-stability` | 5 |  |  |  | 5 |  |  |  |  |
| `phase_margin_vs_t` | `opamp-aol` | 3 |  |  |  | 3 |  |  |  |  |
| `gain_vs_f_comp` | `opamp-aol` | 3 |  |  |  | 3 |  |  |  |  |
| **E output** | | |  |  |  |  |  |  |  |  |
| `vout_vs_f` | `opamp-max-vo-f` | 45 | 2 | 1 | 1 | 10 | 1 | 1 | 22 | 7 |
| `vout_vs_iout` | `opamp-swing` | 34 | 4 |  | 1 | 8 | 1 |  | 11 | 9 |
| `vout_vs_rl` | `opamp-swing` | 23 | 3 | 1 | 1 | 7 | 1 | 1 | 8 | 1 |
| `vout_vs_vs` | `opamp-swing` | 17 |  |  | 1 | 8 | 1 | 1 | 6 |  |
| `vout_vs_t` | `opamp-swing` | 8 |  |  | 1 | 1 | 1 | 1 | 3 | 1 |
| `isc_vs_t` | `opamp-isc` | 27 | 2 |  |  | 8 |  |  | 13 | 4 |
| `isc_vs_time` | `opamp-isc` | 1 |  | 1 |  |  |  |  |  |  |
| `isc_vs_vs` | `opamp-isc` | 4 |  |  |  |  |  |  | 1 | 3 |
| `zout_vs_f` | `opamp-zout` | 24 |  |  |  | 6 |  |  | 13 | 5 |
| **F large signal** | | |  |  |  |  |  |  |  |  |
| `slew_vs_t` | `opamp-slew` | 16 |  |  |  | 9 |  |  | 5 | 2 |
| `slew_vs_vs` | `opamp-slew` | 7 |  |  |  | 3 | 1 |  | 2 | 1 |
| `slew_vs_cl` | `opamp-slew` | 1 |  |  |  |  |  |  |  | 1 |
| `large_step` | `opamp-slew` | 43 | 2 | 1 |  | 14 |  | 1 | 15 | 10 |
| `settling` | `opamp-settling` | 10 | 1 |  |  | 2 |  |  | 5 | 2 |
| `overload_recovery` | `opamp-overload` | 19 | 10 |  |  |  |  |  | 7 | 2 |
| `phase_reversal` | `opamp-phase-reversal` | 8 |  |  |  |  |  |  | 5 | 3 |
| `input_overvoltage` | `opamp-phase-reversal` | 4 |  |  |  |  |  |  | 3 | 1 |
| **G small signal** | | |  |  |  |  |  |  |  |  |
| `small_step` | `opamp-step` | 40 | 10 | 1 |  | 7 |  |  | 16 | 6 |
| `overshoot_vs_cl` | `opamp-stability` | 23 |  | 1 |  | 6 |  |  | 12 | 4 |
| **I distortion** | | |  |  |  |  |  |  |  |  |
| `thd_vs_f` | `opamp-thd-f` | 31 | 3 |  |  | 9 |  | 1 | 16 | 2 |
| `thd_vs_level` | `opamp-thd-level` | 17 |  |  |  | 4 | 1 |  | 12 |  |
| `imd` | `opamp-imd` | 2 |  |  |  |  |  |  | 2 |  |
| `spectrum` | `opamp-thd-f` | 2 |  |  |  |  |  |  | 2 |  |
| `thd_other` | `opamp-thd-f` | 1 |  |  |  |  |  |  | 1 |  |
| **H noise** | | |  |  |  |  |  |  |  |  |
| `noise_0p1_10` | `opamp-noise` | 22 | 2 | 1 |  | 3 |  |  | 11 | 5 |
| `en_vs_vs` | `opamp-noise` | 2 |  | 1 |  |  |  |  | 1 |  |
| `en_vs_t` | `opamp-noise` | 3 |  | 1 |  |  |  |  | 1 | 1 |
| `noise_vs_rs` | `opamp-noise-rs` | 14 |  | 1 |  | 5 |  |  | 8 |  |
| `noise_vs_bandwidth` | `opamp-noise` | 4 |  | 1 |  |  |  |  | 2 | 1 |
| `in_vs_f` | `opamp-noise` | 15 |  | 1 |  | 5 |  |  | 8 | 1 |
| `en_vs_f` | `opamp-noise` | 47 | 12 | 1 |  | 12 | 1 | 1 | 14 | 6 |
| **J multichannel** | | |  |  |  |  |  |  |  |  |
| `channel_separation_vs_f` | `opamp-separation` | 28 | 1 |  |  | 8 |  |  | 15 | 4 |
| **K test circuits** | | |  |  |  |  |  |  |  |  |
| `test_circuit` | `none` | 36 | 2 | 1 |  | 9 |  | 1 | 21 | 2 |
| **C range and rejection** | | |  |  |  |  |  |  |  |  |
| `vicr_other` | `opamp-offset` | 9 |  |  |  | 5 |  |  | 3 | 1 |
| **E output** | | |  |  |  |  |  |  |  |  |
| `vout_other` | `opamp-swing` | 9 |  |  |  | 5 |  |  | 2 | 2 |
| `isc_other` | `opamp-isc` | 7 |  |  |  | 2 |  |  | 3 | 2 |
| `zout_other` | `opamp-zout` | 2 |  |  |  | 1 |  |  | 1 |  |
| **D gain and frequency** | | |  |  |  |  |  |  |  |  |
| `aol_other` | `opamp-aol` | 5 |  |  |  | 2 |  |  | 2 | 1 |
| `gbw_other` | `opamp-aol` | 1 |  |  |  |  |  |  | 1 |  |
| **F large signal** | | |  |  |  |  |  |  |  |  |
| `slew_other` | `opamp-slew` | 3 |  |  |  | 1 |  |  | 2 |  |
| **B input DC** | | |  |  |  |  |  |  |  |  |
| `ib_other` | `opamp-bias` | 7 |  |  |  | 2 |  |  | 1 | 4 |
| `ios_other` | `opamp-bias` | 2 | 2 |  |  |  |  |  |  |  |
| `vos_other` | `opamp-offset` | 2 |  |  |  |  |  |  |  | 2 |
| **A supply** | | |  |  |  |  |  |  |  |  |
| `iq_other` | `opamp-iq` | 7 | 2 |  |  | 3 |  |  | 1 | 1 |
| **C range and rejection** | | |  |  |  |  |  |  |  |  |
| `cmrr_other` | `opamp-cmrr-f` | 5 | 1 |  |  | 1 |  |  | 2 | 1 |
| `psrr_other` | `opamp-psrr-f` | 2 | 1 |  |  |  |  |  | 1 |  |
| **H noise** | | |  |  |  |  |  |  |  |  |
| `noise_other` | `opamp-noise` | 9 |  | 1 |  | 2 |  |  | 6 |  |
| **N Norton amplifiers** | | |  |  |  |  |  |  |  |  |
| `norton` | `none` | 11 | 5 |  |  | 2 |  |  | 2 | 2 |

Titles no rule maps: 24 (listed in `figures.csv` with an empty `test`).

Conditions named most often, over all sheets read (value, mentions):

- **supply**: 15V (102), 5 V (84), 15 V (74), 5V (71), 30 V (62), ±15 V (58), ±15V (56), 36 V (52), 12V (50), 17V (50), 2.5V (46), 5.0 V (43)
- **rl**: 10kΩ (145), 2 kΩ (105), 2kΩ (88), 2kΩ (69), 10 kΩ (67), 2 kΩ (67), 10 kΩ (57), 10kΩ (52), 600Ω (50), 600Ω (33), 1kΩ (19), 1MΩ (17)
- **cl**: 100 pF (133), 100pF (64), 20 pF (37), 0 pF (32), 20pF (23), 300 pF (19), 10 pF (14), 25 pF (13), 500 pF (7), 30pF (6), 1500pF (6), 10pF (5)
- **vo**: 0 V (115), 0V (64), 3VRMS (41), 1.4V (34), ±10 V (30), 3 VRMS (21), 10VRMS (18), 1V (14), 2.5V (14), 1.4 V (14), 6 VRMS (11), 1 V (11)
- **f**: 1 kHz (129), 1kHz (91), 200kHz (49), 10 kHz (29), 100 kHz (27), 10kHz (26), 1.0 kHz (25), 0.1Hz (23), 10 Hz (22), 0.1 Hz (20), 20 Hz (16), 10Hz (14)
- **gain**: 1 (222), +1 (105), 10 (56), +1.0 (49), 0dB (44), 100 (43), –1 (40), +10 (22), 1.0 (20), 1000 (19), 1 V/V (14), –10 (13)
- **temp**: 25°C (671), –40°C (131), –55°C (46), -40°C (44), 125°C (33), –25°C (33), 0°C (25), -55°C (6), 85°C (4), 70°C (3), 27°C (3)
- **rs**: 50Ω (46), 50 Ω (24), 50 Ω (16), 20 Ω (15), 0Ω (9), 100Ω (8), 10 kΩ (7), 10 kΩ (6), 10kΩ (6), 10 Ω (4), 20 Ω (3), 100Ω (3)
- **vcm**: 0 V (82), 0V (66), VS / 2 (45), 0 (40), 0 V) (15), VOUT = midsupply (un (14), VICRmin (12), 2.5V (11), 2.5 V (11), VOUT = midsupply (9), VOUT = mid-supply un (9), VSS (9)
- **band**: 0.1 Hz to 10 Hz (45), 0.1Hz to 10Hz (24), 80kHz (21), 80 kHz (20), 20 Hz to 20 kHz (19), 20Hz to 20kHz (5), 30kHz (4), 10 Hz to 10 kHz (2), 30 kHz (2), 0.1Hz TO 10Hz (1)
<!-- survey:end -->

### Two layers, and what varies between makers

Every sheet has the **electrical characteristics table** — min/typ/max at fixed conditions, 25 °C and a
temperature range, which is what production tests — and the **typical characteristics**, curves of the same
quantities against frequency, temperature, supply, load, common-mode voltage, time or capacitive load.
The families of curves are the same from the 6 figures of a short sheet to the 134 of a long one; the long
sheets add axes per quantity and temperature as a parameter. What differs is the conditions, and the
conditions differ by maker more than by device:

- **Supply reference.** ±15 V with ground (legacy TI, onsemi, Nisshinbo, Analog Devices; "VEE = −15 V"
  beside most onsemi figures) against one supply of 36 V or 40 V with VS/2 as the reference (TI since about
  2015: "VCM = VS / 2", "VOUT = midsupply"). The same quantity is quoted as ±V of swing or as mV of headroom
  from a rail; the curves use different axes.
- **Load.** 2 kΩ is in every sheet; 10 kΩ for open-loop gain and for TI's new tables; 600 Ω on the audio
  parts (NE5532, LM833, LM4562, LME49720, OPA16xx, MC33078, NJM2068).
- **Capacitive load.** 100 pF in 47 of the 69 sheets read (legacy TI, onsemi, Analog Devices, the Chinese
  makers); 20 pF in TI's new format (8 sheets); onsemi gives its phase and gain margins at 0 and 100 pF; the audio sheets print overshoot
  and margin from 10 pF to 1 nF, OPA1656 with 0, 25 and 50 Ω of isolation resistor.
- **Distortion level.** 1 Vrms (onsemi's curve), 3 Vrms (onsemi's table, NE5532, LM4562, LME49720), 5 V at
  20 dB gain (NJM2068), 6 Vrms (TL07x), 10 Vrms (OPA1656); analyser bandwidth 80 kHz (TI, Analog Devices),
  30 kHz (NJM2068's RIAA figure), 22 kHz on some JRC sheets; at G = +1 or −1.
- **Noise.** A spot density at 1 kHz everywhere, 10 kHz in TI, 10 Hz in Analog Devices; density against
  frequency on all but Nisshinbo; 0.1–10 Hz peak-to-peak with a 10 s record in TI's new format, onsemi and
  Analog Devices (onsemi prints the band-pass test circuit); total noise against source resistance in
  onsemi and Analog Devices; a weighted integrated µVrms (FLAT + JIS-A at RS = 300 Ω, RIAA at 2.2 kΩ) only in
  Nisshinbo; noise against supply voltage only in the OP27.
- **Gain-bandwidth.** Read at 100 kHz (onsemi), at 10 kHz and 100 kHz plus a unity-gain frequency
  (NJM2068: 27, 19 and 5.5 MHz for one device, so a GBW without its frequency is meaningless for a two-pole
  part), or extrapolated (TI).
- **Temperature.** Three curves at −55/25/125 °C (onsemi, Analog Devices, legacy TI), −40/25/125 °C (TI new,
  3PEAK; −40 °C is named in 20 sheets, 125 °C in 11, −55 °C in 10), 25 °C only in the Japanese tables.
- **Source resistance for VOS.** 10 Ω (onsemi), 20 or 50 Ω (TI), up to 10 kΩ (Nisshinbo, which folds IB·RS
  into the offset).
- **Tests one maker prints and the others do not.** EMIRR, no-phase-reversal and overload-recovery
  oscillograms (TI new); phase and gain margin against differential source resistance, and the input
  common-mode range against temperature (onsemi); warm-up, long-term and thermal-shock offset (OP27);
  the input's current when driven beyond the rails (NE5534, NE5532); weighted and RIAA noise (NJM2068).
  Only the Norton amplifier (LM3900: mirror gain, pull-down current) has tests of its own kind, and is
  not an op-amp for this bench.

## Universal conditions

The ladders every `opa-*` measurement draws from. Each is the union of what the sheets fix, ordered by
how many sheets name the value, so a sheet's own number is on the ladder and models can be laid over one
another.

| ladder | values | what the sheets say |
|---|---|---|
| supplies | ±15 V first; then ±5 V, ±2.5 V, ±9 V, ±18 V; single 5 V, 30 V, 36 V and 40 V with VS/2 as the reference | 5 V named in 26 sheets, ±15 V in 20 and 15 V in 19, 30 V in 18, 36 V in 12, ±5 V in 7, ±2.5 V in 6 (the audio sheets' CMRR and PSRR); 36/40 V in TI's new tables; 5 V and 30 V in the single-supply parts (LM358, LM324, MC34071, NCS20071, TSZ122) |
| loads | 2 kΩ, 10 kΩ, 600 Ω, open; 100 Ω–10 kΩ sweep for swing and THD | 10 kΩ named in 44 sheets and 2 kΩ in 39, 600 Ω in 10 (the audio parts), 100 kΩ in 6 |
| capacitive loads | 0, 20, 100 pF; 10 pF–10 nF sweep for stability; isolation resistor 0, 25, 50 Ω | 100 pF (47 sheets), 10 pF (11), 0 pF (9), 20 pF (8, TI new), 300 pF (6), 500 pF (5), 1500 pF as single points |
| gains | +1, −1, +10, −10, +100, +1000 | G = 1 printed on 60 sheets (as "1" or "+1"), 10 on 35, 100 on 28, −1 on 16, 1000 on 13, −10 on 8 |
| output levels | 1, 3, 6, 10 Vrms; ±10 V and 0.3 V / 1.2 V from the rails for AOL; 10 mV, 100 mV, 2 V, 10 V, 20 V steps | 3 Vrms on most THD figures (10 sheets; 6 Vrms on 8, 1 Vrms on 6), ±10 V on AOL in 18 sheets, 10 mV small-signal and 10 V large-signal steps |
| source resistances | 0, 10, 20, 50, 100 Ω, 1 kΩ, 10 kΩ, 100 kΩ, 1 MΩ, 10 MΩ | 50 Ω (9 sheets), 20 Ω (8), 100 Ω (6), 10 kΩ (6; Nisshinbo folds it into VOS), 1 kΩ and 10 Ω (3 each), 300 Ω and 2.2 kΩ (weighted noise) |
| temperatures | −55, −40, 0, 25, 70, 85, 125 °C | 25 °C everywhere; −40 (20 sheets), 125 (11), −55 (10), 0 (6), 85 (3), 70 (2) |
| frequencies | 1 Hz–100 MHz at 20 points per decade; spot values 10 Hz, 100 Hz, 1 kHz, 10 kHz, 100 kHz, 1 MHz | 1 kHz on 49 sheets, 10 kHz on 24, 10 Hz on 18, 100 kHz on 15, 1 MHz on 12, 100 Hz on 11 |
| bands | 0.1–10 Hz; 20 Hz–20 kHz; 10 Hz–10 kHz; analyser low-pass 22, 30 and 80 kHz | 0.1–10 Hz on 33 sheets, 20 Hz–20 kHz on 14, 80 kHz on 10, 30 kHz on 3 |
| common mode | 0 (VS/2), the rails ±0.5 V, swept across | "VCM = 0 V" on 34 sheets, "VS / 2" on 8 and "VDD / 2" on 6, VICR(min) on 6 |

Sampling and tolerances as the transistor bench: `reltol = 1e-4`, 20 points per decade in DC and AC, a
transient is one deck per step, decimated curves. Every DC quantity is measured at every supply of the
ladder; curves are shown at ±15 V first.

## The measurements

Format as the transistor catalogue: group, analysis, engines, the circuit, conditions, what is read, the
outputs and curves, the card parameters or subcircuit features that drive it, and what comes out `absent`.
`sheets` names the survey's test ids the measurement covers (`data/datasheets/survey/opamp/matrix.csv` says
how many sheets draw each).

### Supply

#### Does the model load, and at what operating point (`opamp-runs`)

Group `dc` · analysis `op` · engines qspice, ngspice, ltspice · sheets `vs_range`.

Whether each simulator reads the subcircuit and finds one operating point as a unity-gain follower with the
input at the reference (ground at ±VS, VS/2 on a single supply), at every supply of the ladder: the first
fact about a macromodel, and the error class when it fails (dialect, convergence, timeout). The pins are
taken from `opamp-card`; a model whose pins cannot be traced is not run. What is read: that it runs, the
supply current per amplifier, the output voltage (the offset, uncorrected), and the lowest supply at which
the output still sits at the reference, which is the model's own idea of its supply range.

Outputs: `runs@±15V` … `runs@5V` (code per supply), `iq@±15V` (A), `vout@±15V` (V), `vs_min` (V).
Absent: nothing; `n/a` for a supply the model will not run at.

#### Supply current against supply and temperature, and turn-on (`opamp-iq`)

Group `supply` · analysis `dc`, `tran` · engines qspice, ngspice, ltspice · sheets `iq_vs_vs`, `iq_vs_t`,
`turn_on`, `pd_vs_t` (not measured: a package figure).

The quiescent current as a follower with no load, swept from 0 to 40 V total supply (0 to ±20 V), at each
temperature of the ladder; and the output's time to settle at the reference after a supply ramp of 0.3 V/µs
(TI's turn-on condition). Macromodels of the Boyle family draw a current fixed by their current sources
and ignore the supply; behavioural ones follow it.

Outputs: `iq@±15V,25C`, `iq@±5V,25C`, `iq@36V,25C` (A); `iq_slope` (A/V, 10 to 36 V); `iq_ratio@125C/25C`;
`turn_on@36V` (s). Curves: IQ against VS at each T; IQ against T at ±15 V.
Absent: `iq_ratio` when the model has no temperature terms (every current source is a constant).

### Input

#### Offset: its value, and how it moves with common mode, supply and temperature (`opamp-offset`)

Group `input` · analysis `dc` · engines qspice, ngspice, ltspice · sheets `vos_vs_t`, `vos_vs_vcm`,
`vos_vs_vs`, `vos_vs_rs`, `vos_distribution` (one number: a model has no distribution), `cmrr_vs_t`,
`psrr_vs_t`, `psrr_vs_vs`, `cmrr_vs_vcm`, `rejection_vs_t`, `vicr_vs_t`, `vicr_vs_vs`, `vos_warmup`,
`vos_longterm`, `vos_thermal_shock` (not simulable: recorded as not measured).

VOS by a servo loop (an integrator holding the output at the reference, the input voltage read): at each
supply of the ladder; against the common-mode voltage swept from 0.5 V beyond the negative rail to 0.5 V
beyond the positive one, at −40, 25 and 125 °C; against the supply from the minimum to the maximum; against
temperature from −55 to 125 °C; and with the source resistances of the ladder, which folds IB·RS in as
Nisshinbo's table does. From the VCM sweep: the DC CMRR as the slope, the input range as where VOS leaves
its mid-range value by more than 1 mV, and whether the output's sign reverses beyond it (the flag
`opamp-phase-reversal` confirms in time domain). From the supply sweep: the DC PSRR.

Outputs: `vos@±15V` (V), `vos@36V`, `dvos/dt` (V/°C, −40 to 125), `cmrr_dc@±15V` (dB), `psrr_dc` (dB),
`vicr_low@±15V`, `vicr_high@±15V` (V, from the rail), `vos@rs=10k` (V). Curves: VOS against VCM at three
temperatures and each supply; VOS against VS; VOS against T; VICR against T.
Absent: `dvos/dt` and `vicr` against T when the model has no temperature terms; `cmrr_dc` when the model's
common-mode gain is zero by construction (reported as `> 200 dB`, which is the finding).

#### Bias and offset currents, and the input impedance (`opamp-bias`)

Group `input` · analysis `dc`, `ac` · engines qspice, ngspice, ltspice · sheets `ib_vs_t`, `ib_vs_vcm`,
`ib_vs_vs`, `ios_vs_t`, `ios_vs_vcm`, `zin_vs_f`.

The two input currents at the reference, each supply, −55 to 125 °C (a JFET input's IB doubling every 10 K
is what the sheets draw) and across the common-mode range; the differential and common-mode input
impedances by AC injection at 1 kHz and 1 MHz as R ‖ C. A Boyle model's IB is the base current of its
input pair and does move with temperature; a behavioural model's is often a constant source or nothing.

Outputs: `ib@±15V,25C`, `ios@±15V,25C` (A), `ib_ratio@125C/25C`, `ib@vcm=+13V` (A), `rid` (Ω), `cid` (F),
`ricm` (Ω), `cicm` (F). Curves: IB and IOS against T; IB against VCM; IB against VS.
Absent: `ib_ratio` without temperature terms; `ib` itself when the inputs are ideal (reported as zero and
flagged, since no amplifier has it).

### Range and rejection

#### CMRR against frequency (`opamp-cmrr-f`)

Group `rejection` · analysis `ac` · engines qspice, ngspice, ltspice · sheets `cmrr_vs_f`, `cmrr_other`.

The G = 1 difference amplifier with matched resistors, the common mode driven by the AC source, 1 Hz to
100 MHz, at VCM = 0 and at 1.5 V from each rail (onsemi's two curves), at ±15 V, ±2.5 V (the audio sheets)
and 36 V. Read: CMRR at 10 Hz, 1 kHz, 10 kHz, 100 kHz, 1 MHz, and the corner where it starts to fall.

Outputs: `cmrr@1kHz,±15V`, `cmrr@100kHz,±15V` (dB), `cmrr_corner` (Hz). Curves: CMRR against f per VCM and
supply.
Absent: a model with no common-mode path reports infinity; the number is replaced by `absent`.

#### PSRR against frequency, each rail alone and both together (`opamp-psrr-f`)

Group `rejection` · analysis `ac` · engines qspice, ngspice, ltspice · sheets `psrr_vs_f`, `psrr_other`.

The follower with 200 mV of ripple on the positive rail, on the negative, and on both in antiphase (onsemi
varies them simultaneously, the audio sheets each alone), 1 Hz to 100 MHz. Read at 10 Hz, 1 kHz, 10 kHz,
100 kHz, 1 MHz; the corner.

Outputs: `psrr+@1kHz`, `psrr−@1kHz`, `psrr+@100kHz`, `psrr−@100kHz` (dB), `psrr_corner` (Hz). Curves: +PSRR,
−PSRR, both against f.
Absent: a model whose internal references are ideal reports infinity on one or both rails.

#### Rejection of an RF carrier at the input (`opamp-emirr`)

Group `rejection` · analysis `tran` · engines qspice, ngspice · sheets `emirr_vs_f` (TI's new format only,
nine sheets).

A 100 mVp carrier at 10 MHz, 100 MHz, 400 MHz, 1 GHz, 2.4 GHz and 6 GHz on the non-inverting input of a
follower, the DC shift of the output read after it settles, EMIRR = 20·log(VRF_peak/ΔVOS). Nearly every
macromodel has no input filter and rectifies nothing: the result is a shift of zero and the code
`absent`, which is what a reader needs to know before trusting a model near a transmitter.

Outputs: `emirr@1GHz` (dB) or `absent`. Curve: EMIRR against f.

### Gain and frequency

#### Open-loop gain and phase, GBW and the margins (`opamp-aol`)

Group `gain` · analysis `ac` · engines qspice, ngspice, ltspice · sheets `aol_phase_vs_f`, `aol_vs_t`,
`gbw_vs_t`, `gbw_vs_rl`, `phase_margin_vs_t`, `phase_vs_vs`, `gain_vs_f_comp`, `aol_other`, `gbw_other`.

The DC-servo method: an integrator holds the output at the reference, the AC signal enters at the input, the
open-loop gain is the output over the input, 1 Hz to 100 MHz at 20 points per decade, at RL = 600 Ω, 2 kΩ,
10 kΩ and open, CL = 0, 20 and 100 pF, −55, 25 and 125 °C, each supply. Read: AOL at DC, GBW at 10 kHz and
at 100 kHz and as the extrapolated unity-gain product (Nisshinbo's three numbers), the unity-gain
frequency, phase and gain margin at CL = 0 and 100 pF, the dominant pole and the second pole. A part with an
external compensation pin (NE5534, LM308) is run at the sheet's compensation values (0, 22, 47 pF).

Outputs: `aol_dc@2k,±15V` (dB), `gbw@10kHz`, `gbw@100kHz`, `gbw_ext`, `f_unity` (Hz), `pm@0pF`, `pm@100pF` (°),
`gm@100pF` (dB), `f_p1`, `f_p2` (Hz), `aol_ratio@125C/25C`, `gbw_ratio@125C/25C`. Curves: gain and phase
against f per RL, CL, T and supply.
Absent: the temperature ratios without temperature terms; `f_p2` when the model is single-pole (reported,
since no amplifier is).

#### Open-loop gain against output swing, supply and load (`opamp-aol-swing`)

Group `gain` · analysis `dc` · engines qspice, ngspice, ltspice · sheets `aol_vs_vs`, `aol_vs_rl`,
`aol_vs_vo`.

The large-signal gain the tables quote: ΔVOUT/ΔVIN with the output swept ±10 V into 2 kΩ (every legacy
table), and 0.3 V from the rails into 10 kΩ and 1.2 V from the rails into 2 kΩ (TI's new table), at each
supply and load; AOL against the supply at VO = 2/3 VS (onsemi).

Outputs: `aol@±10V,2k` (V/V and dB), `aol@0.3V,10k`, `aol@1.2V,2k`, `aol@600Ω`. Curves: AOL against VO; AOL
against VS; AOL against RL.

#### Closed-loop gain against frequency (`opamp-closed-loop`)

Group `gain` · analysis `ac` · engines qspice, ngspice, ltspice · sheets `closed_loop_gain_vs_f`.

The non-inverting amplifier at G = +1, +10, +100, +1000 and the inverter at −1 and −10 (feedback 1 kΩ to
the ladder's gain, the feedback network's RT recorded), 1 Hz to 100 MHz, CL = 20 pF and 100 pF. Read: the
−3 dB bandwidth and the peaking at each gain.

Outputs: `bw@G=1`, `bw@G=10`, `bw@G=100`, `bw@G=1000` (Hz), `peak@G=1` (dB). Curves: gain against f per G.

#### Stability against capacitive load and source resistance (`opamp-stability`)

Group `gain` · analysis `ac`, `tran` · engines qspice, ngspice, ltspice · sheets `phase_margin_vs_cl`,
`phase_margin_vs_rs`, `overshoot_vs_cl`, `cl_drive`.

Phase and gain margin from the open-loop deck with CL swept 1 pF to 10 nF at G = +1 and +10, with 0, 25 and
50 Ω of isolation resistor (OPA1656's figure); margin against the differential source resistance
RT = R1 + R2 at G = +100 from 10 Ω to 100 kΩ (onsemi's figure); and in time domain the overshoot of a 100 mV
step at G = +1 and a 25 mV step at G = −1 into each CL of the sweep (the audio sheets' figures). Read: the
largest CL at which the margin stays above 45° and the overshoot below 30 %.

Outputs: `cl_max@45deg,G=1` (F), `overshoot@100pF,G=1`, `overshoot@1nF,G=1` (%), `pm@rt=10k,G=100` (°).
Curves: PM against CL per G and RISO; overshoot against CL per G; PM against RT.

### Output

#### Output swing and headroom against load, current, supply and temperature (`opamp-swing`)

Group `output` · analysis `dc` · engines qspice, ngspice, ltspice · sheets `vout_vs_rl`, `vout_vs_iout`,
`vout_vs_vs`, `vout_vs_t`, `vout_other`.

The amplifier driven 1 V into saturation (onsemi's VID = 1 V), the output read against a load from 10 Ω to
100 kΩ to ground, to each rail (MC33272A's figures) and to VS/2, sourcing and sinking, at −55, 25 and
125 °C and each supply; and against the output current from 0 to 80 mA (Nisshinbo's axis), which is the same
measurement read the other way. Published both as ±V (legacy tables) and as mV from the rail (TI's new
tables) at 600 Ω, 2 kΩ and 10 kΩ.

Outputs: `vom+@2k,±15V`, `vom−@2k,±15V` (V), `headroom+@10k,36V`, `headroom−@10k,36V`,
`headroom+@2k,36V`, `headroom−@2k,36V` (V), `vom@600Ω` (V), `vol@sink=1mA,5V` (V, the single-supply
parts' figure). Curves: VOUT against RL (sourcing, sinking, per T); VOUT against IOUT; VOM against VS; VOM
against T.
Absent: the temperature family without temperature terms.

#### Short-circuit current (`opamp-isc`)

Group `output` · analysis `dc`, `tran` · engines qspice, ngspice, ltspice · sheets `isc_vs_t`, `isc_vs_time`,
`isc_vs_vs`, `isc_other`.

The output shorted to the reference with the input 1 V into saturation each way, at −55, 25 and 125 °C and
each supply; and against time for 10 s (the OP27 draws it, since a real part heats). Macromodels limit the
current with a clamp or not at all.

Outputs: `isc+@±15V,25C`, `isc−@±15V,25C` (A), `isc_ratio@125C/25C`. Curves: ISC against T; ISC against VS.
Absent: a model with no current limit reports the load line's number and the flag `no limit`.

#### Output impedance, open- and closed-loop (`opamp-zout`)

Group `output` · analysis `ac` · engines qspice, ngspice, ltspice · sheets `zout_vs_f`, `zout_other`.

Current injected into the output, the voltage read: open-loop (the servo deck), 1 Hz to 100 MHz; closed-loop
at G = +1, +10, +100, +1000 (onsemi's family); at IOUT = 0 and 5 mA of DC load (TI's two curves).

Outputs: `zo_ol@1MHz` (Ω, TI's table), `zo_ol@9MHz` (onsemi's), `zo_cl@1kHz,G=1` (Ω). Curves: ZO against f
open-loop and per G.

#### Maximum output voltage against frequency (`opamp-max-vo-f`)

Group `output` · analysis `tran` · engines qspice, ngspice, ltspice · sheets `vout_vs_f`.

A sine stepped in amplitude at each frequency from 1 kHz to 10 MHz until the output's THD passes 1 %
(onsemi's criterion; TI's legacy figure is the same information drawn), into 2 kΩ and 10 kΩ, at each supply.
Read: the full-power bandwidth, and the swing at 20 kHz and 100 kHz.

Outputs: `fpbw@2k,±15V` (Hz), `vopp@20kHz,2k`, `vopp@100kHz,2k` (V). Curves: VO(pp) against f per RL and VS.

### Large signal

#### Slew rate, and the large-signal step (`opamp-slew`)

Group `large-signal` · analysis `tran` · engines qspice, ngspice, ltspice · sheets `slew_vs_t`, `slew_vs_vs`,
`slew_vs_cl`, `slew_vs_gain`, `large_step`, `slew_other`.

Steps of 2, 10 and 20 V at G = +1 and G = −1, RL = 2 kΩ, CL = 20 pF and 100 pF (the two fixtures the sheets
differ by: 20 to 50 % of the figure), each supply, −55 to 125 °C; the rising and falling slopes between 10 %
and 90 %, and the waveforms kept at 80 points as the sheets print their oscillograms (5 V/div, 2 µs/div).

Outputs: `sr+@10V,100pF,G=1`, `sr−@10V,100pF,G=1`, `sr+@10V,20pF,G=1`, `sr+@G=−1` (V/s), `sr_ratio@125C/25C`.
Curves: SR against VS; SR against T; the step waveforms per fixture.
Absent: the temperature ratio without temperature terms.

#### Settling time (`opamp-settling`)

Group `large-signal` · analysis `tran` · engines qspice, ngspice, ltspice · sheets `settling`.

Time from the step's edge to the output staying within 1 %, 0.1 % and 0.01 % of its final value, for 2 V
and 10 V steps at G = +1, −1 and −4 (NE5534's figure), CL = 20 pF and 100 pF.

Outputs: `ts@0.1%,10V,G=1`, `ts@0.01%,10V,G=1`, `ts@0.1%,2V,G=−1` (s). Curves: error against time per step.

#### Overload recovery (`opamp-overload`)

Group `large-signal` · analysis `tran` · engines qspice, ngspice, ltspice · sheets `overload_recovery`.

The inverter at G = −10 driven to 1.2 times the supply each way, the time from the input's return to the
output's return within 1 % of linear (TI's 300 ns), positive and negative.

Outputs: `trec+@G=−10`, `trec−@G=−10` (s). Curves: the two oscillograms.

#### Phase reversal, and the input driven beyond the rails (`opamp-phase-reversal`)

Group `large-signal` · analysis `tran`, `dc` · engines qspice, ngspice, ltspice · sheets `phase_reversal`,
`input_overvoltage`.

The follower with the input swept 2 V beyond each rail: whether the output's polarity reverses (TI's
no-phase-reversal figure), and the current the input draws against the input voltage (NE5534's and
NE5532's figures), which says whether the model has the protection diodes.

Outputs: `reversal` (flag), `iin@vcc+1V` (A). Curves: VOUT against VIN; IIN against VIN.
Absent: `iin` when the input is ideal.

### Small signal

#### Small-signal step response (`opamp-step`)

Group `small-signal` · analysis `tran` · engines qspice, ngspice, ltspice · sheets `small_step`.

A 10 mV step at G = +1 and G = −1 into CL = 20 pF and 100 pF (TI's and the legacy fixtures), RL = 2 kΩ: rise
time 10–90 %, overshoot, ringing frequency, the waveforms rising and falling kept at 80 points.

Outputs: `tr@20pF,G=1`, `tr@100pF,G=1` (s), `overshoot@100pF,G=1` (%), `f_ring` (Hz). Curves: the four
waveforms.

### Noise

#### Voltage and current noise against frequency, the 1/f corner and 0.1–10 Hz (`opamp-noise`)

Group `noise` · analysis `noise`, `tran` · engines qspice, ngspice · sheets `en_vs_f`, `in_vs_f`,
`noise_0p1_10`, `en_vs_vs`, `en_vs_t`, `noise_vs_bandwidth`, `noise_other`.

`.noise` at G = +100 with RS = 0 (en) and RS = 100 kΩ, 10 MΩ for a JFET or CMOS input (in), 0.1 Hz to 1 MHz;
spot values at 10 Hz, 100 Hz, 1 kHz and 10 kHz; the 1/f corner; the integrated rms over 10 Hz–10 kHz
(legacy TL07x), 20 Hz–20 kHz and 0.1–10 Hz; the 0.1–10 Hz peak-to-peak from a 10 s transient through onsemi's
band-pass (gain 50 000, 0.1 Hz high-pass, 10 Hz low-pass) when the model has noise sources, or from
integration; en against the supply (OP27's figure). A macromodel with no noise sources (most) gives the
resistors' thermal noise only: the result is `absent`, and `opamp-card` says why.

Outputs: `en@10Hz`, `en@1kHz`, `en@10kHz` (V/√Hz), `in@1kHz` (A/√Hz), `f_corner_en`, `f_corner_in` (Hz),
`en_rms@20Hz-20kHz` (V), `en_pp@0.1-10Hz` (V). Curves: en and in against f; en against VS.
Absent: all of them when the card has no noise sources beyond resistors.

#### Total noise against source resistance, noise figure and the weighted figures (`opamp-noise-rs`)

Group `noise` · analysis `noise` · engines qspice, ngspice · sheets `noise_vs_rs`; and the NJM2068's
weighted figures.

Total input-referred noise VT = √(en² + (in·RS)² + 4kT·RS) at 1 kHz and 10 Hz against RS from 10 Ω to 10 MΩ
(onsemi's and Analog Devices' figures), the noise figure against RS, and the integrated 20 Hz–20 kHz noise
flat, A-weighted (which stands for JIS-A) and RIAA-weighted through a 40 dB stage with a 30 kHz low-pass, at
RS = 300 Ω and 2.2 kΩ — the Nisshinbo figures, the one test specific to the Japanese audio sheets.

Outputs: `vt@1kHz,rs=1k` (V/√Hz), `nf@rs=1k` (dB), `en_a@rs=300` (V), `en_riaa@rs=2.2k` (V). Curves: VT
against RS at 1 kHz and 10 Hz; NF against RS; weighted noise against RS.
Absent: as `opamp-noise`.

### Distortion (model against model)

#### THD against frequency (`opamp-thd-f`)

Group `distortion` · analysis `tran` · engines qspice, ngspice, ltspice · sheets `thd_vs_f`, `thd_vs_gain`,
`spectrum`, `thd_other`.

A sine from 20 Hz to 100 kHz at 1 Vrms and 3 Vrms (and 6 and 10 Vrms where the swing allows), G = +1, +10,
+100 and +1000 (onsemi's family) and −1, RL = 2 kΩ and 600 Ω, each supply; harmonics 2 to 10 by Goertzel as
`bjt-distortion` does, an 80 kHz analyser band, and the spectrum of a 1 kHz and a 10 kHz tone kept
(OPA1656's FFT figures). Published for comparison between models: a macromodel's distortion is its slew,
its clipping and whatever its output stage does, not the die's.

Outputs: `thd@1kHz,3Vrms,2k,G=1`, `thd@20kHz,3Vrms,2k,G=1`, `thd@1kHz,3Vrms,600Ω,G=1`, `thd@1kHz,G=10`
(ratio). Curves: THD against f per level, gain and load; the spectra.

#### THD against output level (`opamp-thd-level`)

Group `distortion` · analysis `tran` · engines qspice, ngspice, ltspice · sheets `thd_vs_level`.

At 1 kHz and 2 kHz (onsemi), the level stepped from 10 mVrms to 10 Vrms, G = +1 and −1, 2 kΩ and 600 Ω, each
supply: where the distortion turns up at the clipping end, and the noise floor at the low end for a model
with noise.

Outputs: `thd@1kHz,1Vrms`, `thd@1kHz,6Vrms` (ratio), `v_clip@1%` (V). Curves: THD against level per gain,
load and supply.

#### Intermodulation (`opamp-imd`)

Group `distortion` · analysis `tran` · engines qspice, ngspice, ltspice · sheets `imd` (two sheets; the
audio sheets' CCIF figure).

SMPTE (60 Hz + 7 kHz, 4:1) and CCIF (19 + 20 kHz, 1:1) at 3 Vrms into 2 kΩ and 600 Ω, G = +1.

Outputs: `imd_smpte@3Vrms`, `imd_ccif@3Vrms` (ratio).

#### THD against load (`opamp-thd-load`)

Group `distortion` · analysis `tran` · engines qspice, ngspice, ltspice · sheets `thd_vs_rl` (OPA1656's figure).

At 1 kHz, 3 Vrms, G = +1, RL from 100 Ω to 10 kΩ: how a model's output stage behaves into a heavy load.

Outputs: `thd@1kHz,3Vrms,100Ω`, `thd@1kHz,3Vrms,10k` (ratio). Curve: THD against RL.

### Multichannel

#### Channel separation (`opamp-separation`)

Group `multichannel` · analysis `ac`, `tran` · engines qspice, ngspice, ltspice · sheets
`channel_separation_vs_f`.

For a subcircuit with two or four amplifiers: onsemi's fixture, the driven channel at G = +1 with 20 Vpp
(3 V and 10 V on the TI audio sheets) into 2 kΩ, 600 Ω and 10 kΩ, the measured channel at G = +100 with its
inputs grounded, 10 Hz to 100 kHz; the DC separation as ΔVOS per ΔVO (TI's table). A macromodel of one
amplifier in a package of two shares nothing: the result is infinity and the code `absent`, which is the
finding.

Outputs: `sep@1kHz,2k`, `sep@10kHz,2k`, `sep@100kHz,2k` (dB), `sep_dc` (V/V). Curves: separation against f
per RL.
Absent: a single-amplifier subcircuit, or one with no supply or substrate coupling between its copies.

### Model facts

#### What the card says it can do (`opamp-card`)

Group `facts` · no simulation · sheets none.

Read from the subcircuit's text by `sei models cards`: the pins and their roles; the macromodel family
(Boyle 1974 and its descendants, the PSpice generations of Analog Devices and Burr-Brown/TI, a behavioural
model, an encrypted one); whether it carries noise sources, temperature terms, a supply-current model, a
common-mode path, input protection, an output current limit, and what kind of output stage. These feed the
`absent` codes above, so that every absence names its cause.

Outputs: `family`, `pins`, `noise_sources`, `temperature_terms`, `supply_current_model`,
`common_mode_path`, `input_protection`, `current_limit`, `output_stage` (codes).

#### Do the three simulators agree? (`opamp-agreement`)

Group `facts` · every analysis · engines qspice, ngspice, ltspice.

As `bjt-agreement`: per output, the spread between engines, and the engine whose curve is published.

## Which groups matter for which use

| use | groups | look at |
|---|---|---|
| Audio preamplifier or mixer stage | noise, distortion, gain, input | en at 10 Hz–1 kHz and the 1/f corner (or `absent`), THD against f at 3 Vrms, GBW and the margins at 100 pF, VOS at RS = 10 kΩ. |
| Line driver, headphone stage | output, distortion, large-signal | swing into 600 Ω, ISC, THD against load, full-power bandwidth, SR. |
| Active filter, tone control | gain, output, small-signal | closed-loop bandwidth at the gain used, ZO against f, overshoot against CL. |
| Single-supply pedal or synth circuit | supply, input, output | runs at 5 V and 9 V, VICR to the negative rail, VOL at 1 mA sink, IQ, phase reversal. |
| Precision DC, servo, reference buffer | input, rejection | VOS and its drift (or `absent`), IB and IOS against T, CMRR and PSRR at DC and 100 Hz. |

## What is not measured

Package thermal derating (`pd_vs_t`, `pd_vs_vs`), long-term and thermal-shock offset, ESD and latch-up: not
simulable in a macromodel. The offset-null network and the test circuits (`vos_adjust`, `test_circuit`) are
fixtures, not quantities. Norton amplifiers (LM3900) are another kind of part. A subcircuit whose pins
cannot be traced is not run.

## Next steps

Every measurement above was run once on ngspice, one model per part, for TL072, NE5532 and RC4558
([bench-preview-2026-10.md](bench-preview-2026-10.md)); the numbers say what a Boyle-family macromodel can
and cannot do. What remains to carry the op-amps through the pipeline that the bipolar bench runs (catalogue
entries, decks in the simulator images, records, the site) is the checklist of
[bench-roadmap.md](bench-roadmap.md).
