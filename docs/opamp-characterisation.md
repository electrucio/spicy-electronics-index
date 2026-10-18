# Characterising the op-amp SPICE models

The op-amp bench, specified before it is built: a catalogue of measurements at universal conditions, the
same for every macromodel, drawn from what the makers' own data sheets measure. It follows the transistor
bench ([model-characterisation.md](model-characterisation.md)) in its principles and its format, and it
differs where a macromodel differs from a transistor card: a macromodel is a subcircuit with five or more
pins that often has no noise sources, no temperature terms and an idealised output stage, so the bench has
to report what a model *cannot* do as a finding, the way `bjt-breakdown` does.

Status: this page is the specification and the evidence behind it. The entries of
`data/bench/measurements.yaml` (kind `opamp`), the decks, the drawings ([bench-drawings.md](bench-drawings.md))
and the first runs exist; what is still pending is in [bench-roadmap.md](bench-roadmap.md).

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

<!-- measurements:start -->
Catalogue version `m-13`; the codes and the uses table are in [model-characterisation.md](model-characterisation.md).

### Op-amps

#### Does the model load, and at what operating point (`opamp-runs`)

Group `supply` · analysis `op` · engines qspice, ngspice, ltspice · symbols IQ, VOS.

Whether the simulator reads the subcircuit and finds an operating point as a unity-gain follower with its input at the reference, at every supply of the ladder: the first fact about a macromodel, and the error class when it fails (dialect, convergence, timeout). The pins are read from the author's header (the PSpice PARTS connections block, or named pins); a model whose pins cannot be told is not run. Read: that it runs, the supply current per amplifier, the output voltage (the offset, uncorrected), and the lowest supply at which the output still sits at the reference, the model's own idea of its supply range.

**Circuit.** Five followers, one per supply (±15, ±5, ±2.5, ±9, ±18 V), each loaded with 2 kΩ to the reference, the input at the reference; one operating point.

Drawing: DUT as a follower; split supply; 2 kΩ load; input at the reference. Differs from the netlist: five copies run in one deck.

**Conditions.** {supplies: [[15, -15], [5, -5], [2.5, -2.5], [9, -9], [18, -18]], rl: 2000}

**The deck (QSPICE), line by line.**

- `VP0 vp0 0 15` — the first follower's rails, ±15 V; the next copies at ±5, ±2.5, ±9 and ±18 V
- `VN0 vn0 0 -15`
- `VI0 in0 0 0` — its input at the reference
- `XR0 in0 o0 vp0 vn0 o0 DUT` — the amplifier as a follower: in+, in−, V+, V−, out (the model's own pin order is put in)
- `RL0 o0 0 2000`
- `.op`

**Extraction.** Exit status and log give the error class; when it runs, the positive rail's current and the output voltage per supply; a supply at which the output sits within 0.1 V of the reference counts as run, and the lowest total supply that did is published.

**Outputs.**

- `runs`: true when the simulator returned a solution
- `error_class`: syntax, convergence, timeout or empty when it ran
- `runs@{vs}`: whether the follower sat at the reference at that supply
- `iq@{vs}` (A): the positive rail's current at each supply
- `vos@{vs}` (V): the follower's output less the reference: the uncorrected offset
- `vs_min` (V): the lowest total supply of the ladder the model ran at

**What it cannot tell.** That the model is right; agreement between engines is the stronger fact.

**Standard.** none

#### Supply current against supply and temperature, and turn-on (`opamp-iq`)

Group `supply` · analysis `dc` · engines qspice, ngspice, ltspice · symbols IQ, IQ(VS), IQ(T).

The quiescent current as a follower with no load, swept from 4 to 40 V total supply (the negative rail mirroring the positive), and at the temperatures of the ladder; and the output's time to settle at the reference after both rails ramp from ±3 to ±15 V at 0.3 V/µs (TI's turn-on condition). Macromodels of the Boyle family draw a current fixed by a resistor between the rails and ignore the temperature; behavioural ones follow it.

**Circuit.** A follower with no load, the positive rail swept by a source and the negative rail a controlled copy of it with the sign reversed; the bias deck at −55, 25 and 125 °C; a transient with both rails as piecewise-linear ramps.

Drawing: DUT as a follower; swept split supply with the negative rail mirroring the positive one; ammeter in the positive rail.

**Conditions.** {vs_sweep: {from: 4, to: 40, step: 0.25, unit: V}, vs_points: [10, 18, 30, 36], turn_on: {v_start: 3, v_end: 15, ramp_s: 4e-05, rl: 2000, settle_v: 0.01, max_step_s: 5e-08, t_end_s: 0.0002}}

**The deck (QSPICE), line by line.**

- `VP vp 0 0` — the positive rail, swept; the negative rail mirrors it
- `EN vn 0 vp 0 -1`
- `VIN in 0 0`
- `XQ in out vp vn out DUT`
- `.dc VP 2 20 0.125` — 4 to 40 V of total supply in 250 mV steps
- `VP vp 0 PWL(0 3 4e-05 15 1 15)` — the turn-on deck: both rails ramped from ±3 V to ±15 V over 40 µs
- `VN vn 0 PWL(0 -3 4e-05 -15 1 -15)`
- `XU in out vp vn out DUT`

**Extraction.** The positive rail's current at the points of the supply ladder and its slope between 10 and 36 V; the current at each temperature over 25 °C (absent when it does not move); the last time the follower's output is more than 10 mV from the offset after the ramp.

**Outputs.**

- `iq@{vs}` (A): supply current at the total supply
- `iq_slope` (A/V): the current's slope with the supply, 10 to 36 V
- `iq@{T}` (A): supply current at ±15 V at each temperature
- `iq_ratio@125°C/25°C`: supply current at 125 °C over 25 °C
- `iq_temperature_note`: absent when the current does not move with temperature
- `turn_on@15V` (s): time to settle within 10 mV after the ramp to ±15 V

Curves: IQ vs VS (iq against vs, lin); turn-on (vout against t, lin).

**A low value.** A current that is the same at every supply and temperature is the Boyle family's resistor between the rails, not the part's bias.

**What it cannot tell.** The current of a dual or quad package as a whole; this is one amplifier.

**Standard.** none

#### Offset, and how it moves with common mode, supply and temperature (`opamp-offset`)

Group `dc` · analysis `dc` · engines qspice, ngspice, ltspice · symbols VOS, CMRR(DC), VICR.

The offset at each supply of the ladder; against the common-mode voltage swept 1 V beyond each rail; against the supply; at −55, 25 and 125 °C; and with 10 kΩ in the non-inverting input, which folds IB × RS in as Nisshinbo's table does. From the common-mode sweep: the DC CMRR as the slope, the input range as where the offset leaves its mid-range value by more than 1 mV, and whether the output's sign reverses beyond it. A Boyle macromodel's offset is one number: the same at every supply, common mode and temperature, which is the finding.

**Circuit.** A follower with 10 kΩ to the reference, its input swept from 1 V below the negative rail to 1 V above the positive one; the offset read as the output less the input. The supply sweep and the bias decks at temperature and with the source resistance give the other views.

Drawing: DUT as a follower; swept input; 10 kΩ load. Differs from the netlist: the supply sweep and the bias decks are separate.

**Conditions.** {supply: [15, -15], rl: 10000, vcm_beyond: 1, vcm_step: 0.02}

**The deck (QSPICE), line by line.**

- `VP vp 0 15`
- `VN vn 0 -15`
- `VIN in 0 0` — the follower's input, swept 1 V beyond each rail
- `XV in out vp vn out DUT`
- `RL out 0 10000`
- `.dc VIN -16 16 0.02`

**Extraction.** VOS(VCM) = VOUT − VIN. The common-mode range is the span over which VOS stays within 1 mV of its value at 0 V, published as the distance from each rail; the DC CMRR is the span (2 V inside each end) over the offset's change across it, absent when the offset does not move. The drift is the offset at 125 °C less at −55 °C over 180 K, absent below a nanovolt per kelvin.

**Outputs.**

- `vos@{vs}` (V): offset at each supply of the ladder, from the runs deck and the supply sweep
- `vos@{T}` (V): offset at ±15 V at each temperature
- `vos@vcm={v}` (V): offset with the inputs at −13 and +13 V
- `vos@rs=10kΩ` (V): offset with 10 kΩ in the non-inverting input: VOS + IB × RS
- `dvos_dt` (V/K): the drift, −55 to 125 °C
- `drift_note`: absent when the offset does not move with temperature
- `vicr_low` (V): the input range's distance from the negative rail
- `vicr_high` (V): its distance from the positive rail
- `cmrr_dc` (dB): the DC common-mode rejection, from the offset's slope with VCM
- `cmrr_dc_note`: absent when the offset does not move with the common mode

Curves: VOS vs VCM (vos against vcm, lin); VOS vs VS (vos_vs against vs, lin).

**A high value.** A drift above 10 µV/K is a model with a deliberately mismatched input pair; an input range that reaches the rails is a rail-to-rail input, or a model that ignores the rails.

**A low value.** A CMRR above 200 dB and a drift of zero are the Boyle family's fixed offset: the sheet's figures are not in the model.

**What it cannot tell.** The part's distribution of offsets (a model is one sample), warm-up, long-term drift.

**Standard.** none

#### Bias and offset currents, and the input impedance (`opamp-bias`)

Group `dc` · analysis `op` · engines qspice, ngspice, ltspice · symbols IB, IOS, ZIN.

The two input currents with the inputs at the reference, at −55, 25 and 125 °C (a JFET input's IB doubling every 10 K is what the sheets draw) and at the ends of the common-mode range; the differential and common-mode input impedances by AC injection at 1 kHz and 1 MHz, as a resistance and a capacitance. A Boyle model's IB is the base current of its input pair and does move with temperature; a behavioural model's is often a constant source, or nothing.

**Circuit.** A follower with an ammeter in each input, the non-inverting input at the reference (or at ±13 V, or fed through 10 kΩ), 2 kΩ load. Impedances: both inputs driven together with 1 V of AC (common mode); one input driven with the other held by the open-loop servo (differential).

Drawing: DUT as a follower; ammeters in both inputs. Differs from the netlist: the impedance decks are separate.

**Conditions.** {supply: [15, -15], rl: 2000, temps_c: [-55, 25, 125], vcm: [-13, 13], rs: 10000, zin_sweep: {from: 1000, to: 1e+06, per_decade: 10, unit: Hz}}

**The deck (QSPICE), line by line.**

- `VP vp 0 15`
- `VN vn 0 -15`
- `VI in 0 0` — the input at the reference, through an ammeter into the non-inverting input
- `VIP in inp 0`
- `VNN out inn 0` — the feedback through an ammeter into the inverting input
- `XB inp inn vp vn out DUT`
- `RL out 0 2000`
- `.op`
- `VCM cm 0 DC 0 AC 1` — the common-mode impedance deck: both inputs driven together
- `VA cm inp 0`
- `VB cm inn 0`
- `.ac dec 10 1000 1000000`

**Extraction.** IB as the mean of the two input currents, IOS as their difference, at each temperature and common mode; the ratio at 125 °C over 25 °C; the real part of the input admittance at 1 kHz as a resistance and the quadrature part at 1 MHz as a capacitance.

**Outputs.**

- `ib@{T}` (A): the mean input current at each temperature
- `ibp@25°C` (A): the non-inverting input's current
- `ibn@25°C` (A): the inverting input's current
- `ios@{T}` (A): the difference of the two
- `ib@vcm={v}` (A): the mean input current with the inputs at −13 and +13 V
- `ib_ratio@125°C/25°C`: IB at 125 °C over 25 °C
- `rid` (Ω): differential input resistance at 1 kHz
- `cid` (F): differential input capacitance at 1 MHz
- `ricm` (Ω): common-mode input resistance at 1 kHz
- `cicm` (F): common-mode input capacitance at 1 MHz

**A low value.** An IB of exactly zero is an ideal input: no amplifier has it. A ratio of exactly 1 is a current source with no temperature term.

**What it cannot tell.** The input current's noise, which is the noise measurement's.

**Standard.** none

#### CMRR against frequency (`opamp-cmrr-f`)

Group `dc` · analysis `ac` · engines qspice, ngspice, ltspice · symbols CMRR(f).

The G = 1 difference amplifier with matched 10 kΩ resistors, the common mode driven by the AC source, 1 Hz to 10 MHz, at VCM = 0 and 2 V from each rail (onsemi's curves). Read at 10 Hz, 1 kHz, 10 kHz, 100 kHz and 1 MHz, and the corner where it starts to fall. A model with no common-mode path reports a rejection beyond 200 dB: absent.

**Circuit.** Three copies of the difference amplifier in one deck, each with four 10 kΩ resistors and a 2 kΩ load, the common-mode source at 0, −13 and +13 V DC with 1 V of AC.

Drawing: DUT as a difference amplifier; four 10 kΩ resistors; common-mode source. Differs from the netlist: three copies run in one deck.

**Conditions.** {supply: [15, -15], vcm: [0, -13, 13], r: 10000, rl: 2000, sweep: {from: 1, to: 1e+07, per_decade: 20, unit: Hz}, f_points: [10, 1000, 10000, 100000, 1000000]}

**The deck (QSPICE), line by line.**

- `VCM0 vcm0 0 DC 0 AC 1` — the first copy, at VCM = 0: the common-mode source with 1 V of AC
- `R1_0 vcm0 inn0 10000`
- `R2_0 inn0 out0 10000`
- `R3_0 vcm0 inp0 10000`
- `R4_0 inp0 0 10000`
- `XC0 inp0 inn0 vp vn out0 DUT`
- `RL0 out0 0 2000`
- `.ac dec 20 1 10000000`

**Extraction.** CMRR = −20 log |VOUT| for 1 V of common mode; the corner is where it has fallen 3 dB below its 1 Hz value; absent above 200 dB.

**Outputs.**

- `cmrr@{f},vcm={v}` (dB): common-mode rejection at the spot frequencies and common-mode voltages
- `cmrr_corner` (Hz): where the rejection at VCM = 0 has fallen by 3 dB
- `cmrr_note`: absent when the model has no common-mode path

Curves: CMRR, VCM=0V (cmrr against f, lin, at VCM = 0); CMRR, VCM=-13V (cmrr against f, lin, at VCM = -13); CMRR, VCM=13V (cmrr against f, lin, at VCM = 13). Shown first: VCM = 0.

**A high value.** Above 200 dB: no common-mode path in the model.

**What it cannot tell.** The resistors' mismatch, which limits the real measurement; these are exact.

**Standard.** none

#### PSRR against frequency, each rail alone and both together (`opamp-psrr-f`)

Group `supply` · analysis `ac` · engines qspice, ngspice, ltspice · symbols PSRR(f).

The follower with 1 V of AC on the positive rail, on the negative, and on both in antiphase (onsemi varies them together, the audio sheets each alone), 1 Hz to 10 MHz. Read at 10 Hz, 1 kHz, 10 kHz, 100 kHz and 1 MHz; the corner. A model whose internal references are ideal reports a rejection beyond 200 dB on one or both rails: absent.

**Circuit.** Three decks, the follower with the AC on the rail (or rails) named, 2 kΩ load, the input at the reference.

Drawing: DUT as a follower; AC on a rail. Differs from the netlist: three decks drawn as one.

**Conditions.** {supply: [15, -15], rl: 2000, sweep: {from: 1, to: 1e+07, per_decade: 20, unit: Hz}, f_points: [10, 1000, 10000, 100000, 1000000]}

**The deck (QSPICE), line by line.**

- `VP vp 0 DC 15 AC 1` — the positive rail with 1 V of AC; the next decks put it on the negative rail, and on both in antiphase
- `VN vn 0 DC -15`
- `VIN in 0 0`
- `XP in out vp vn out DUT`
- `RL out 0 2000`
- `.ac dec 20 1 10000000`

**Extraction.** PSRR = −20 log |VOUT| for 1 V of ripple; the corner from the positive rail's curve.

**Outputs.**

- `psrr_pos@{f}` (dB): rejection of ripple on the positive rail
- `psrr_neg@{f}` (dB): on the negative rail
- `psrr_both@{f}` (dB): on both in antiphase
- `psrr_corner` (Hz): where the positive rail's rejection has fallen by 3 dB
- `psrr_pos_note`: absent beyond 200 dB
- `psrr_neg_note`: absent beyond 200 dB
- `psrr_both_note`: absent beyond 200 dB

Curves: PSRR pos (psrr against f, lin); PSRR neg (psrr against f, lin); PSRR both (psrr against f, lin).

**A high value.** Beyond 200 dB on both rails together is a model whose two rails cancel by symmetry.

**What it cannot tell.** The rejection with the part's decoupling; this is the bare pin.

**Standard.** none

#### Rejection of an RF carrier at the input (`opamp-emirr`)

Group `dc` · analysis `tran` · engines qspice, ngspice · symbols EMIRR.

A 100 mV peak carrier at 10 MHz, 100 MHz, 400 MHz and 1 GHz on the non-inverting input of a follower, the DC shift of the output read after it settles, EMIRR = 20 log (VRF / ΔVOS) (TI's new sheets print it). Nearly every macromodel has no input filter and rectifies nothing: the shift is zero and the result absent, which is what a reader needs to know before trusting a model near a transmitter.

**Circuit.** The follower with 2 kΩ, the carrier on its input; two hundred cycles, the mean of the last hundred.

Drawing: DUT as a follower; RF source on the input. Differs from the netlist: one deck per carrier.

**Conditions.** {supply: [15, -15], rl: 2000, amplitude: 0.1, carriers: [1e+07, 1e+08, 4e+08, 1e+09], cycles: 200, steps_per_cycle: 20}

**The deck (QSPICE), line by line.**

- `VP vp 0 15`
- `VN vn 0 -15`
- `VIN in 0 SIN(0 0.1 10000000)` — the carrier: 100 mV peak at 10 MHz; then 100 MHz, 400 MHz and 1 GHz
- `XE in out vp vn out DUT`
- `RL out 0 2000`

**Extraction.** The mean output over the last hundred cycles less the offset; a shift below 50 µV is the simulator's noise, and the rejection absent.

**Outputs.**

- `emirr@{f}` (dB): the carrier over the offset shift it causes, or absent
- `vos_shift@{f}` (V): the shift itself

**What it cannot tell.** The real part's rectification, which lives in the input stage's junctions and the package.

**Standard.** none

#### Open-loop gain and phase, GBW and the margins (`opamp-aol`)

Group `frequency` · analysis `ac` · engines qspice, ngspice, ltspice · symbols AOL, GBW, PM.

The open loop by the inductor/capacitor trick: a 1 GH inductor in the feedback and a 1 GF capacitor to ground hold the DC operating point and open the loop above a microhertz. The output over the input is the open-loop gain, 1 Hz to 100 MHz at 20 points per decade, with 2 kΩ and 100 pF on the output. Read: AOL at DC, the gain-bandwidth product at 10 kHz and 100 kHz (Nisshinbo's two numbers), the unity-gain frequency, the phase and gain margins, the dominant pole and the second pole (reported absent when the model is single-pole, since no amplifier is). Variants at 600 Ω and 10 kΩ, at ±5 and ±9 V, at −55 and 125 °C.

**Circuit.** The amplifier with the AC source on its non-inverting input, the inverting input tied to the output through 1 GH and to ground through 1 GF, 2 kΩ and 100 pF on the output.

Drawing: DUT; 1 GH feedback inductor; 1 GF capacitor to ground; AC source; 2 kΩ and 100 pF load. Differs from the netlist: one deck per variant.

**Conditions.** {supply: [15, -15], rl: 2000, cl: 1e-10, sweep: {from: 1, to: 1e+08, per_decade: 20, unit: Hz}, rl_variants: [600, 10000], supply_variants: [[5, -5], [9, -9]], temps_c: [-55, 125]}

**The deck (QSPICE), line by line.**

- `VP vp 0 15`
- `VN vn 0 -15`
- `VIN inp 0 DC 0 AC 1` — the AC source on the non-inverting input
- `L1 out inn 1G` — the loop: closed at DC through 1 GH, open above a microhertz; 1 GF holds the inverting input
- `C1 inn 0 1G`
- `XA inp inn vp vn out DUT`
- `RL out 0 2000`
- `CL out 0 1e-10`
- `.ac dec 20 1 100000000` — 1 Hz to 100 MHz, twenty points per decade

**Extraction.** |AOL| and its phase (unwrapped, the DC phase as zero); GBW as |AOL| × f at 10 kHz and 100 kHz; the unity-gain frequency where |AOL| passes 1; the phase margin as 180° plus the phase there; the gain margin as −|AOL| in dB where the phase passes −180°; f_p1 where the gain has fallen 3 dB; f_p2 where the phase passes −135°. The ratios of the DC gain and the GBW at 125 °C over 25 °C.

**Outputs.**

- `aol_dc` (dB): open-loop gain at DC, 2 kΩ, ±15 V
- `gbw@10kHz` (Hz): gain × frequency at 10 kHz
- `gbw@100kHz` (Hz): gain × frequency at 100 kHz
- `f_unity` (Hz): where the open-loop gain passes 1
- `pm` (°): phase margin at 2 kΩ and 100 pF
- `gain_margin` (dB): gain margin, where the phase passes −180°
- `f_p1` (Hz): the dominant pole
- `f_p2` (Hz): the second pole, where the phase passes −135°
- `f_p2_note`: absent when the model is single-pole
- `aol_dc@{tag}` (dB): the DC gain at the other loads, supplies and temperatures
- `gbw@100kHz,{tag}` (Hz): the GBW at the other loads, supplies and temperatures
- `pm@{tag}` (°): the phase margin at the other loads, supplies and temperatures
- `aol_ratio@125°C/25°C`: DC gain at 125 °C over 25 °C
- `gbw_ratio@125°C/25°C`: GBW at 125 °C over 25 °C

Curves: gain (gain against f, log, at RL = 2000, VS = 30, T = 25); phase (phase against f, lin); gain, 600Ω (gain against f, log, at RL = 600, VS = 30, T = 25); gain, 10kΩ (gain against f, log, at RL = 10000, VS = 30, T = 25); gain, ±5V (gain against f, log, at RL = 2000, VS = 10, T = 25); gain, ±9V (gain against f, log, at RL = 2000, VS = 18, T = 25); gain, -55°C (gain against f, log, at RL = 2000, VS = 30, T = -55); gain, 125°C (gain against f, log, at RL = 2000, VS = 30, T = 125). Shown first: RL = 2000, VS = 30, T = 25.

**A high value.** A GBW that does not move with temperature or supply is a macromodel with fixed poles.

**A low value.** A second pole absent is a single-pole model: its phase margin is 90° whatever the load, and a stability figure means nothing.

**What it cannot tell.** The gain with an external compensation pin; a part with one is run as its model's own default.

**Standard.** none

#### Open-loop gain against output swing and load (`opamp-aol-swing`)

Group `dc` · analysis `dc` · engines qspice, ngspice, ltspice · symbols AVD.

The large-signal gain the tables quote: ΔVOUT/ΔVIN with the output swept ±10 V and ±13 V into 2 kΩ, 600 Ω and 10 kΩ (every legacy table's AVD), from a fine DC sweep of the input around the model's own offset; and the output's range in open loop.

**Circuit.** Three open-loop copies, one per load, their non-inverting inputs on a source swept ±300 µV in 250 nV steps on top of the offset the runs deck found, inverting inputs grounded.

Drawing: DUT open loop; fine input sweep riding on the offset source; load. Differs from the netlist: three copies run in one deck.

**Conditions.** {supply: [15, -15], rl: [2000, 600, 10000], vin_span: 0.0003, vin_step: 2.5e-07, swings: [10, 13]}

**The deck (QSPICE), line by line.**

- `VP vp 0 15`
- `VN vn 0 -15`
- `VIN inb 0 0` — the input sweep, riding on the model's own offset (VOFF, from the runs deck)
- `XL0 inp 0 vp vn out0 DUT` — the 2 kΩ copy, open loop; XL1 and XL2 into 600 Ω and 10 kΩ
- `RL0 out0 0 2000`
- `.dc VIN -0.0003 0.0003 2.5e-07` — ±300 µV in 250 nV steps

**Extraction.** For each load, the input voltage where the output passes −10 V and +10 V (and ±13 V); the gain is the output span over the input span between them; the output's extremes over the sweep.

**Outputs.**

- `aol@±10V,{rl}` (V/V): the large-signal gain over ±10 V of output
- `aol@±13V,{rl}` (V/V): over ±13 V
- `aol_db@±10V` (dB): the ±10 V gain into 2 kΩ, in decibels
- `vout_min@{rl}` (V): the output's lowest value in open loop
- `vout_max@{rl}` (V): its highest

Curves: VOUT vs VIN, RL=2kΩ (vout against vin, lin, at RL = 2000); VOUT vs VIN, RL=600Ω (vout against vin, lin, at RL = 600); VOUT vs VIN, RL=10kΩ (vout against vin, lin, at RL = 10000). Shown first: RL = 2000.

**A low value.** A gain that does not fall into 600 Ω is an output stage with no resistance in the model.

**What it cannot tell.** The gain's dependence on the common mode, which the offset measurement reads.

**Standard.** none

#### Closed-loop gain against frequency (`opamp-closed-loop`)

Group `frequency` · analysis `ac` · engines qspice, ngspice, ltspice · symbols BW(G).

The non-inverting amplifier at G = +1, +10, +100 and +1000 (1 kΩ to ground, the feedback resistor for the gain) and the inverter at −1 (10 kΩ and 10 kΩ), 10 Hz to 100 MHz, 2 kΩ and 100 pF on the output. Read: the −3 dB bandwidth and the peaking at each gain, the family every sheet prints.

**Circuit.** Five copies in one deck sharing the AC source, each with its own feedback network and load.

Drawing: DUT with feedback network; AC source; 2 kΩ and 100 pF load. Differs from the netlist: five copies run in one deck.

**Conditions.** {supply: [15, -15], gains: [1, 10, 100, 1000, -1], r1: 1000, r_inv: 10000, rl: 2000, cl: 1e-10, sweep: {from: 10, to: 1e+08, per_decade: 20, unit: Hz}}

**The deck (QSPICE), line by line.**

- `VP vp 0 15`
- `VN vn 0 -15`
- `VIN in 0 DC 0 AC 1` — the AC source, shared
- `XG0 in out0 vp vn out0 DUT` — the G = 1 copy; then G = 10, 100, 1000 with 1 kΩ to ground and the feedback for the gain, and the inverter at −1
- `RL0 out0 0 2000`
- `CL0 out0 0 1e-10`
- `R1_1 inn1 0 1000`
- `R2_1 out1 inn1 9000`
- `XG1 in inn1 vp vn out1 DUT`
- `.ac dec 20 10 100000000`

**Extraction.** The bandwidth where the gain has fallen to 1/√2 of its 10 Hz value; the peaking as the gain's maximum over its 10 Hz value, in dB; the curves normalised to the 10 Hz gain.

**Outputs.**

- `bw@G={g}` (Hz): the −3 dB bandwidth at each gain
- `peak@G={g}` (dB): the peaking at each gain

Curves: gain, G=1 (gain_cl against f, log, at G = 1); gain, G=10 (gain_cl against f, log, at G = 10); gain, G=100 (gain_cl against f, log, at G = 100); gain, G=1000 (gain_cl against f, log, at G = 1000); gain, G=-1 (gain_cl against f, log, at G = -1). Shown first: G = all.

**A high value.** Peaking above 3 dB at G = 1 into 100 pF is a model near instability there, as some parts are.

**What it cannot tell.** The bandwidth with the real feedback network's stray capacitance.

**Standard.** none

#### Stability against capacitive load and source resistance (`opamp-stability`)

Group `frequency` · analysis `ac` · engines qspice, ngspice, ltspice · symbols PM(CL), overshoot.

The phase margin from the open-loop deck with 10 pF, 100 pF, 1 nF and 10 nF on the output; the peaking at G = +100 with the feedback network's total resistance stepped from 100 Ω to 100 kΩ (onsemi's figure); and in time domain the overshoot of a 100 mV step at G = +1 into 100 pF and 1 nF (the audio sheets' figures). Read: the largest load of the ladder at which the margin stays above 45°.

**Circuit.** The open-loop deck per capacitive load; the non-inverting amplifier at G = 100 with four feedback networks in one deck; the follower with a 100 mV step into each load.

Drawing: DUT open loop with CL; DUT at G = 100 with RT; DUT as a follower with a step. Differs from the netlist: several decks drawn as one.

**Conditions.** {supply: [15, -15], rl: 2000, cl: [1e-11, 1e-09, 1e-08], cl_overshoot: [1e-10, 1e-09], step_v: 0.1, rt: [100, 1000, 10000, 100000], rt_gain: 100, cl_rt: 1e-10, sweep: {from: 10, to: 1e+08, per_decade: 20, unit: Hz}, r1: 1000, r_inv: 10000, t_start_s: 1e-07, edge_s: 1e-09, width_s: 2e-05, max_step_s: 1e-09, t_end_s: 2e-05, curve_points: 80}

**The deck (QSPICE), line by line.**

- `R1_0 inn0 0 1` — the G = 100 deck: the first copy with RT = 100 Ω (1 Ω to ground, 99 Ω feedback); RT = 1 kΩ, 10 kΩ, 100 kΩ follow
- `R2_0 out0 inn0 99`
- `XT0 in inn0 vp vn out0 DUT`
- `RL0 out0 0 2000`
- `CL0 out0 0 1e-10`
- `.ac dec 20 10 100000000`
- `VIN in 0 PULSE(0 0.1 1e-07 1e-09 1e-09 2e-05 4e-05)` — the overshoot deck: a 100 mV step into the follower with 100 pF, then 1 nF
- `XS in out vp vn out DUT`
- `RL out 0 2000`
- `CL out 0 1e-10`
- `.tran 1e-09 2e-05 0 1e-09`

**Extraction.** The phase margin per load as in the open-loop measurement; the largest load with 45° or more (the smallest load that falls below it, when one does); the peaking per RT as the closed-loop gain's maximum over its 10 Hz value; the overshoot as the step response's maximum over the step.

**Outputs.**

- `pm@{cl}` (°): phase margin at each capacitive load (the 100 pF one from the open-loop measurement)
- `cl_max@45deg` (F): the largest load of the ladder with 45° of margin
- `overshoot@{cl},G=1` (%): overshoot of a 100 mV step at G = 1
- `peak@G=100,rt={rt}` (dB): peaking at G = 100 with the feedback network's total resistance

Curves: PM vs CL (pm against cl, lin); peaking vs RT, G=100 (peak against rt, lin); step, 100pF,G=1 (vout against t, lin, at CL = 1e-10); step, 1nF,G=1 (vout against t, lin, at CL = 1e-09).

**A high value.** No peaking at any RT is a model whose input capacitance is zero.

**A low value.** A margin that does not fall with 10 nF is a model with no output resistance or a single pole.

**What it cannot tell.** Stability with the real layout's strays.

**Standard.** none

#### Output swing and headroom against load, current, supply and temperature (`opamp-swing`)

Group `output` · analysis `op` · engines qspice, ngspice, ltspice · symbols VOM, VOH, VOL.

The amplifier driven 1 V into saturation each way (onsemi's VID = 1 V), the output read into 2 kΩ, 600 Ω and 10 kΩ to the reference at ±15 V, into 2 kΩ at ±5 and ±9 V and at −55 and 125 °C; and against the output current from 0 to 80 mA (Nisshinbo's axis), sourcing and sinking. Published as ±V (the legacy tables) and as the distance from the rail (TI's new tables). A Boyle model's swing comes from two clamp diodes and ignores the load, which is the finding.

**Circuit.** Open-loop copies with +1 V and −1 V between the inputs, one pair per load, and two shorted to the reference through an ammeter for the short-circuit current; one operating point. For the current, the saturated amplifier into a swept current source.

Drawing: DUT open loop driven into saturation; load to the reference; ammeter on a shorted copy. Differs from the netlist: the copies run in one deck.

**Conditions.** {supply: [15, -15], rl: [2000, 600, 10000], drive_v: 1, supply_variants: [[5, -5], [9, -9]], temps_c: [-55, 125], io_sweep: {to: 0.08, step: 0.001, unit: A}, io_points: [0.001, 0.005, 0.01, 0.02, 0.04, 0.08]}

**The deck (QSPICE), line by line.**

- `VP vp 0 15`
- `VN vn 0 -15`
- `VIp0 ip0 0 1` — the first copy driven positive, into 2 kΩ; a copy driven negative beside it; then 600 Ω and 10 kΩ
- `XSp0 ip0 0 vp vn op0 DUT`
- `RLp0 op0 0 2000`
- `VIn0 in0 0 -1`
- `XSn0 in0 0 vp vn on0 DUT`
- `RLn0 on0 0 2000`
- `VIsp isp 0 1` — the shorted copies: the output to the reference through an ammeter
- `XIp isp 0 vp vn osp DUT`
- `VSCp osp 0 0`
- `.op`
- `IL op 0 0` — the current sweep: the saturated amplifier sourcing into a current sink, 0 to 80 mA
- `.dc IL 0 0.08 0.001`

**Extraction.** The saturated output per load; the headroom as the rail less the output; the output against the load current from the sweep.

**Outputs.**

- `vom_hi@{rl}` (V): the positive swing into each load at ±15 V
- `vom_lo@{rl}` (V): the negative swing
- `headroom_hi@{rl}` (V): the positive rail less the positive swing
- `headroom_lo@{rl}` (V): the negative swing less the negative rail
- `vom_hi@2kΩ,{tag}` (V): the positive swing into 2 kΩ at the other supplies and temperatures
- `vom_lo@2kΩ,{tag}` (V): the negative swing there
- `vout_hi@io={i}` (V): the saturated output while sourcing the current

Curves: VOUT vs IOUT, sourcing (vout against io, lin); VOUT vs IOUT, sinking (vout against io, lin).

**A low value.** A swing that is the same into 600 Ω and 10 kΩ is a clamp, not an output stage.

**What it cannot tell.** The swing with the part's own output stage heating.

**Standard.** none

#### Short-circuit current (`opamp-isc`)

Group `output` · analysis `op` · engines qspice, ngspice, ltspice · symbols ISC.

The output shorted to the reference with the input 1 V into saturation each way, at ±15 V and at the other supplies, at −55, 25 and 125 °C. Macromodels limit the current with a clamp or not at all; a current far above the sheet's is the load line, not a limit.

**Circuit.** The swing deck's shorted copies.

Drawing: DUT driven into saturation; ammeter to the reference.

**Conditions.** {from: opamp-swing}

**The deck (QSPICE), line by line.**

- `VIsp isp 0 1` — the swing deck's shorted copy, sourcing
- `XIp isp 0 vp vn osp DUT`
- `VSCp osp 0 0`
- `VIsn isn 0 -1` — and sinking
- `XIn isn 0 vp vn osn DUT`
- `VSCn osn 0 0`

**Extraction.** The ammeter's current, sourcing and sinking, per supply and temperature; the ratio at 125 °C over 25 °C.

**Outputs.**

- `isc_pos` (A): short-circuit current, sourcing, at ±15 V
- `isc_neg` (A): sinking
- `isc_pos@{tag}` (A): sourcing at the other supplies and temperatures
- `isc_neg@{tag}` (A): sinking there
- `isc_ratio@125°C/25°C`: sourcing current at 125 °C over 25 °C

**A high value.** A current of amperes is a model without a limit: the number is the clamp diode's load line.

**What it cannot tell.** The current's fall as the real part heats.

**Standard.** none

#### Output impedance, open- and closed-loop (`opamp-zout`)

Group `output` · analysis `ac` · engines qspice, ngspice, ltspice · symbols ZO.

Current injected into the output, the voltage read: open loop (the servo deck), 10 Hz to 100 MHz; and closed loop at G = +1, +10, +100 and +1000 (onsemi's family). TI's tables quote the open-loop value at 1 MHz, onsemi's at 9 MHz.

**Circuit.** The open-loop servo with 1 A of AC injected into the output; four closed-loop copies in one deck, each with its own injection.

Drawing: DUT; AC current into the output; voltmeter. Differs from the netlist: the closed-loop copies run in one deck.

**Conditions.** {supply: [15, -15], gains: [1, 10, 100, 1000], r1: 1000, sweep: {from: 10, to: 1e+08, per_decade: 20, unit: Hz}, f_points: [1000, 1e+06, 9e+06], f_points_cl: [1000, 100000]}

**The deck (QSPICE), line by line.**

- `L1 out inn 1G` — open loop: the servo, 1 A of AC into the output
- `C1 inn 0 1G`
- `XZO inp inn vp vn out DUT`
- `IINJ 0 out AC 1`
- `.ac dec 20 10 100000000`

**Extraction.** |VOUT| for 1 A injected, at the spot frequencies.

**Outputs.**

- `zo_ol@{f}` (Ω): open-loop output impedance
- `zo_cl@{f},G={g}` (Ω): closed-loop output impedance at each gain

Curves: ZO open loop (zo against f, log, at G = open loop); ZO, G=1 (zo against f, log, at G = 1); ZO, G=10 (zo against f, log, at G = 10); ZO, G=100 (zo against f, log, at G = 100); ZO, G=1000 (zo against f, log, at G = 1000). Shown first: G = open loop.

**A low value.** An open-loop impedance that is one resistor at every frequency is the Boyle output stage.

**What it cannot tell.** The impedance with a DC load current; the injection is around the operating point at zero current.

**Standard.** none

#### Maximum output voltage against frequency (`opamp-max-vo-f`)

Group `slew` · analysis `tran` · engines qspice, ngspice, ltspice · symbols FPBW, VO(f).

A 10 V peak sine at 20, 50 and 100 kHz through the follower into 2 kΩ: the output's peak and its distortion, where the slew limit bites; and the full-power bandwidth from the slew rate over 2π times the swing, the figure the legacy sheets draw as the output voltage against frequency.

**Circuit.** The follower with 2 kΩ, twelve cycles, the last eight analysed.

Drawing: DUT as a follower; 10 V peak sine; 2 kΩ load. Differs from the netlist: one deck per frequency.

**Conditions.** {supply: [15, -15], amplitude: 10, f: [20000, 50000, 100000], rl: 2000, cycles: 12, analysed_cycles: 8, steps_per_cycle: 200}

**The deck (QSPICE), line by line.**

- `VP vp 0 15`
- `VN vn 0 -15`
- `VIN in 0 SIN(0 10 20000)` — 10 V peak at 20 kHz; then 50 and 100 kHz
- `XD in out vp vn out DUT`
- `RL out 0 2000`

**Extraction.** The fundamental's amplitude and the THD by Goertzel over the last eight cycles; FPBW = SR / (2π VOM).

**Outputs.**

- `vopk@{f}` (V): the output's fundamental at each frequency for 10 V peak in
- `thd@{f}`: the distortion there
- `fpbw` (Hz): the full-power bandwidth, SR over 2π VOM

Curves: VO peak vs f (vopk against f, lin).

**What it cannot tell.** The swing at the frequencies between the three points; the full-power bandwidth is the figure for those.

**Standard.** none

#### Slew rate, and the large-signal step (`opamp-slew`)

Group `slew` · analysis `tran` · engines qspice, ngspice, ltspice · symbols SR.

Steps of 10 V at G = +1 and G = −1 into 2 kΩ and 100 pF (and 20 pF), of 2 V and 20 V, at ±5 V and at 125 °C: the rising and falling slopes between 10 % and 90 % (the two fixtures the sheets differ by: 20 to 50 % of the figure), and the main waveform kept at 80 points as the sheets print their oscillograms.

**Circuit.** The follower (or the inverter with 10 kΩ and 10 kΩ) with a pulse source, 2 kΩ and the capacitive load; one deck per fixture.

Drawing: DUT as a follower; pulse source; 2 kΩ and 100 pF load. Differs from the netlist: one deck per fixture.

**Conditions.** {supply: [15, -15], rl: 2000, cl: 1e-10, r1: 1000, r_inv: 10000, t_start_s: 1e-06, edge_s: 1e-08, width_s: 4e-05, max_step_s: 5e-09, t_end_s: 8e-05, curve_points: 80, main: 10V,100pF,G=1, fixtures: [{key: 10V,100pF,G=1, step: 10}, {key: 10V,100pF,G=-1, step: 10, gain: -1}, {key: 10V,20pF,G=1, step: 10, cl: 2e-11}, {key: 2V,100pF,G=1, step: 2}, {key: 20V,100pF,G=1, step: 20}, {key: 4V,±5V, step: 4, supply: [5, -5]}, {key: 10V,125°C, step: 10, temp: 125}]}

**The deck (QSPICE), line by line.**

- `VP vp 0 15`
- `VN vn 0 -15`
- `VIN in 0 PULSE(-5 5 1e-06 1e-08 1e-08 4e-05 8e-05)` — the main fixture: a 10 V step into the follower
- `XS in out vp vn out DUT`
- `RL out 0 2000`
- `CL out 0 1e-10`
- `.tran 5e-09 8e-05 0 5e-09`

**Extraction.** The slope between the 10 % and 90 % crossings of the rising edge (and of the falling edge in the main fixture); the ratio at 125 °C over 25 °C.

**Outputs.**

- `sr_pos@{fixture}` (V/s): the rising slew rate in each fixture
- `sr_neg@10V,100pF,G=1` (V/s): the falling slew rate in the main fixture
- `sr_ratio@125°C/25°C`: the rising slew rate at 125 °C over 25 °C

Curves: step, 10V,100pF,G=1 (vout against t, lin).

**A low value.** A slew rate that is the same at 2 V and 20 V and at every temperature is a Boyle model's single current limit on its compensation capacitor.

**What it cannot tell.** The slew with the real part's input stage overdriven differently; this is a hard step.

**Standard.** none

#### Settling time (`opamp-settling`)

Group `slew` · analysis `tran` · engines qspice, ngspice, ltspice · symbols ts.

Time from the step's edge to the output staying within 0.1 % and 0.01 % of its final value, for 10 V and 2 V steps at G = +1 and a 10 V step at G = −1, 100 pF on the output.

**Circuit.** The slew fixtures with a finer time step, the error against time kept.

Drawing: DUT as a follower; pulse source; 2 kΩ and 100 pF load. Differs from the netlist: one deck per fixture.

**Conditions.** {supply: [15, -15], rl: 2000, cl: 1e-10, r1: 1000, r_inv: 10000, t_start_s: 1e-06, edge_s: 1e-08, width_s: 4e-05, max_step_s: 2e-09, t_end_s: 4.1e-05, bands: [0.001, 0.0001], curve_points: 80, fixtures: [{key: 10V,G=1, step: 10}, {key: 2V,G=1, step: 2}, {key: 10V,G=-1, step: 10, gain: -1}]}

**The deck (QSPICE), line by line.**

- `VIN in 0 PULSE(-5 5 1e-06 1e-08 1e-08 4e-05 8e-05)` — the 10 V step at G = 1
- `XS in out vp vn out DUT`
- `CL out 0 1e-10`
- `.tran 2e-09 4.1e-05 0 2e-09`

**Extraction.** The last time the output is outside the band around its final value, from the step's start.

**Outputs.**

- `ts@0.1%,{fixture}` (s): settling to 0.1 %
- `ts@0.01%,{fixture}` (s): settling to 0.01 %

Curves: error, 10V,G=1 (error against t, lin); error, 2V,G=1 (error against t, lin); error, 10V,G=-1 (error against t, lin).

**What it cannot tell.** Thermal settling, which the real part shows in the first milliseconds.

**Standard.** none

#### Overload recovery (`opamp-overload`)

Group `output` · analysis `tran` · engines qspice, ngspice, ltspice · symbols trec.

The inverter at G = −10 driven to 1.2 times the supply each way, and the time from the input's return to the output's return within 100 mV of the reference (TI's figure), positive and negative.

**Circuit.** The inverter with 1 kΩ and 10 kΩ, a 1.8 V pulse on the input (18 V demanded of the output), 2 kΩ load.

Drawing: DUT as an inverter; pulse source; 2 kΩ load. Differs from the netlist: one deck per polarity.

**Conditions.** {supply: [15, -15], rl: 2000, cl: 1e-12, gain: -10, drive_v: 1.8, r_inv: 1000, r1: 1000, t_start_s: 1e-06, edge_s: 1e-08, width_s: 2e-05, max_step_s: 2e-09, t_end_s: 4e-05, after_s: 1e-08, recovered_v: 0.1, curve_points: 80}

**The deck (QSPICE), line by line.**

- `VIN in 0 PULSE(0 1.8 1e-06 1e-08 1e-08 2e-05 4e-05)` — the inverter at G = −10, driven 1.8 V: 18 V demanded of the output
- `R1 in inn 1000`
- `R2 out inn 10000`
- `XS 0 inn vp vn out DUT`
- `RL out 0 2000`

**Extraction.** The last time after the pulse's end at which the output is more than 100 mV from the reference.

**Outputs.**

- `trec_pos` (s): recovery from a positive overload
- `trec_neg` (s): from a negative one
- `vout_overloaded_pos` (V): the output while overloaded positive
- `vout_overloaded_neg` (V): while overloaded negative

Curves: recovery pos (vout against t, lin); recovery neg (vout against t, lin).

**A high value.** A recovery of microseconds is a model whose input stage saturates and holds charge, as a few do.

**Standard.** none

#### Phase reversal, and the input driven beyond the rails (`opamp-phase-reversal`)

Group `dc` · analysis `dc` · engines qspice, ngspice, ltspice · symbols reversal, IIN.

From the follower's common-mode sweep: whether the output's polarity reverses within 2 V of a rail or beyond it (TI's no-phase-reversal figure); and the current the input draws against the input voltage, swept 2 V beyond each rail (the NE5534's and NE5532's figures), which says whether the model has the input protection diodes.

**Circuit.** The follower with its input swept 2 V beyond each rail through an ammeter, 10 kΩ load.

Drawing: DUT as a follower; swept input through an ammeter; 10 kΩ load. Differs from the netlist: the reversal flags come from the offset measurement's sweep.

**Conditions.** {supply: [15, -15], rl: 10000, beyond: 2, step: 0.1, iin_points: [-16, 14, 16]}

**The deck (QSPICE), line by line.**

- `VP vp 0 15`
- `VN vn 0 -15`
- `VIN in 0 0` — the input swept 2 V beyond each rail, through an ammeter
- `VIM in inp 0`
- `XV inp out vp vn out DUT`
- `RL out 0 10000`
- `.dc VIN -17 17 0.1`

**Extraction.** The flags from the offset sweep (an output of the opposite sign while the input is within 2 V of a rail, or beyond it); the input current at 14 V, +16 V and −16 V; protection present when the current a volt beyond either rail is above a microampere.

**Outputs.**

- `reversal_within_rails`: true when the output reverses with the input inside the rails
- `reversal_beyond_rails`: true when it reverses beyond them
- `iin@+14V` (A): input current with the input at +14 V
- `iin@+16V` (A): at +16 V, a volt beyond the positive rail
- `iin@-16V` (A): at −16 V
- `input_protection`: present when the input conducts a volt beyond either rail, else absent

Curves: VOUT vs VIN (vout against vin, lin); IIN vs VIN (iin against vin, lin).

**What it cannot tell.** Latch-up.

**Standard.** none

#### Small-signal step response (`opamp-step`)

Group `frequency` · analysis `tran` · engines qspice, ngspice, ltspice · symbols tr, overshoot.

A 10 mV step into the follower with 20 pF and 100 pF (TI's and the legacy fixtures), 2 kΩ load; the rise time 10 to 90 %, the overshoot, the waveforms kept at 80 points.

**Circuit.** The follower with a 10 mV pulse, 2 kΩ and the capacitive load.

Drawing: DUT as a follower; 10 mV pulse; 2 kΩ and CL. Differs from the netlist: one deck per load.

**Conditions.** {supply: [15, -15], rl: 2000, cl: [2e-11, 1e-10], step_v: 0.01, r1: 1000, r_inv: 10000, t_start_s: 1e-07, edge_s: 1e-09, width_s: 2e-05, max_step_s: 1e-09, t_end_s: 2e-05, curve_points: 80}

**The deck (QSPICE), line by line.**

- `VIN in 0 PULSE(0 0.01 1e-07 1e-09 1e-09 2e-05 4e-05)` — a 10 mV step into the follower with 20 pF; then 100 pF
- `XS in out vp vn out DUT`
- `RL out 0 2000`
- `CL out 0 2e-11`
- `.tran 1e-09 2e-05 0 1e-09`

**Extraction.** The 10 % and 90 % crossings of the rising edge; the overshoot as the maximum over the step.

**Outputs.**

- `tr@{cl},G=1` (s): rise time 10 to 90 % into each load
- `overshoot@{cl},G=1` (%): the overshoot

Curves: step, 20pF,G=1 (vout against t, lin, at CL = 2e-11); step, 100pF,G=1 (vout against t, lin, at CL = 1e-10).

**Standard.** none

#### Voltage and current noise against frequency, the 1/f corner and 0.1–10 Hz (`opamp-noise`)

Group `noise` · analysis `noise` · engines qspice, ngspice · symbols en, in.

The follower's input-referred noise by .noise with RS = 0 (en) and with 100 kΩ (in, by subtraction), 0.1 Hz to 1 MHz; spot values at 10 Hz, 100 Hz, 1 kHz and 10 kHz; the 1/f corner; the integrated rms over 0.1–10 Hz, 10 Hz–10 kHz (the legacy TL07x figure) and 20 Hz–20 kHz; the 0.1–10 Hz peak-to-peak as 6.6 times the rms; en at 1 kHz at ±5 V. A macromodel with no noise sources (most) gives its resistors' thermal noise only: the finding is absent.

**Circuit.** The follower with 2 kΩ, the noise source at its input, with or without the source resistance.

Drawing: DUT as a follower; noise source; RS. Differs from the netlist: one deck per source resistance.

**Conditions.** {supply: [15, -15], rl: 2000, sweep: {from: 0.1, to: 1e+06, per_decade: 20, unit: Hz}, spot_sweep: {from: 1000, to: 1000, per_decade: 2, unit: Hz}, f_points: [10, 100, 1000, 10000], bands: [[0.1, 10], [10, 10000], [20, 20000]], rs_in: 100000, supply_variant: [5, -5]}

**The deck (QSPICE), line by line.**

- `VP vp 0 15`
- `VN vn 0 -15`
- `VIN in 0 DC 0 AC 1` — the noise source at the follower's input, RS = 0; a second run with 100 kΩ
- `XN in out vp vn out DUT`
- `RL out 0 2000`
- `.noise V(out) VIN dec 20 0.1 1000000`

**Extraction.** en from the RS = 0 run; in from the 100 kΩ run less en² and the resistor's 4kT·RS; the corner where en is √2 times its 10 kHz value, absent when flat; the bands by trapezoids on the sweep's points. Noise sources absent when en at 1 kHz is below 0.1 nV/√Hz.

**Outputs.**

- `en@{f}` (V/√Hz): voltage noise density at the spot frequencies
- `f_corner_en` (Hz): the 1/f corner of en, or absent
- `en_rms@{band}` (V): the integrated noise over each band
- `en_pp@0.1-10Hz` (V): 6.6 times the 0.1–10 Hz rms
- `in@1kHz` (A/√Hz): current noise density at 1 kHz
- `in_note`: absent when the current noise is below the floor
- `en@1kHz,±5V` (V/√Hz): en at 1 kHz at ±5 V
- `noise_sources`: present, or absent when the model carries none

Curves: en (en against f, log); in (in against f, log).

**A low value.** An en of picovolts is the thermal noise of the model's resistors: no noise sources.

**What it cannot tell.** Burst noise, and the part's own noise, which makers measure on a few samples.

**Standard.** none

#### Total noise against source resistance, noise figure and the weighted figures (`opamp-noise-rs`)

Group `noise` · analysis `noise` · engines qspice, ngspice · symbols VT, NF.

The total input-referred noise at 1 kHz with 1 kΩ, 10 kΩ, 100 kΩ and 1 MΩ in the input (onsemi's and Analog Devices' figures), the noise figure from it, and the integrated 20 Hz–20 kHz noise flat, A-weighted (which stands for JIS-A) and RIAA-weighted through a 30 kHz low-pass, at RS = 300 Ω and 2.2 kΩ: the Nisshinbo figures, the one test specific to the Japanese audio sheets.

**Circuit.** The follower with the source resistance in its input; one deck per resistance.

Drawing: DUT as a follower; noise source; RS. Differs from the netlist: one deck per source resistance.

**Conditions.** {rs_ladder: [1000, 10000, 100000, 1000000], rs_weighted: [300, 2200], spot_sweep: {from: 1000, to: 1000, per_decade: 2, unit: Hz}, weighted_sweep: {from: 10, to: 100000, per_decade: 20, unit: Hz}}

**The deck (QSPICE), line by line.**

- `RS in inr 1000` — the follower with 1 kΩ in its input; then 10 kΩ, 100 kΩ, 1 MΩ, and 300 Ω and 2.2 kΩ for the weighted figures
- `XN inr out vp vn out DUT`
- `.noise V(out) VIN dec 2 1000 1000`

**Extraction.** The input-referred density at 1 kHz per resistance; NF = 10 log (VT² / 4kT RS); the weighted figures as trapezoids on the density times the weighting.

**Outputs.**

- `vt@1kHz,rs={r}` (V/√Hz): total input-referred noise at 1 kHz
- `nf@rs={r}` (dB): noise figure
- `en_flat@rs={r}` (V): 20 Hz to 20 kHz rms, flat
- `en_a@rs={r}` (V): A-weighted
- `en_riaa@rs={r}` (V): RIAA-weighted, 30 kHz low-pass

Curves: VT vs RS (vt against rs, log).

**What it cannot tell.** As the noise measurement: nothing beyond the model's sources.

**Standard.** none

#### THD against frequency (model against model) (`opamp-thd-f`)

Group `distortion` · analysis `tran` · engines qspice, ngspice, ltspice · symbols THD(f).

A sine at 20 Hz, 100 Hz, 1 kHz, 10 kHz and 20 kHz at 1 Vrms and 3 Vrms through the follower and at 3 Vrms at G = +10 (1 kΩ and 9 kΩ), into 2 kΩ, harmonics 2 to 10 by Goertzel over the last eight of twelve cycles. Published for comparison between models: a macromodel's distortion is its slew, its clipping and whatever its output stage does, not the die's.

**Circuit.** The follower (or the non-inverting amplifier) with 2 kΩ, the sine on its input; one deck per point.

Drawing: DUT; sine source; 2 kΩ load. Differs from the netlist: one deck per frequency, level and gain.

**Conditions.** {supply: [15, -15], rl: 2000, r1: 1000, r_inv: 10000, f: [20, 100, 1000, 10000, 20000], vrms: [1, 3], gain2: 10, cycles: 12, analysed_cycles: 8, steps_per_cycle: 4096}

**The deck (QSPICE), line by line.**

- `VP vp 0 15`
- `VN vn 0 -15`
- `VIN in 0 SIN(0 1.41421356 20)` — 1 Vrms (1.414 V peak) at 20 Hz into the follower; the ladder follows
- `XD in out vp vn out DUT`
- `RL out 0 2000`

**Extraction.** THD as the root of the sum of the squares of harmonics 2 to 10 over the fundamental; the second and third harmonics at 1 kHz, 3 Vrms, G = 1.

**Outputs.**

- `thd@{f},{level},{gain}`: THD at each frequency, level and gain
- `hd2@1kHz,3Vrms,G=1`: second harmonic over the fundamental
- `hd3@1kHz,3Vrms,G=1`: third harmonic over the fundamental

Curves: THD vs f, 1Vrms, G=1 (thd against f, log, at G = 1); THD vs f, 3Vrms, G=1 (thd against f, log, at G = 1); THD vs f, 3Vrms, G=10 (thd against f, log, at G = 10).

**A high value.** Only against another model of the same part.

**A low value.** Parts per million at every frequency is a model with no non-linearity but its clamps.

**What it cannot tell.** The distortion of the part; the sheets' figures come from the die.

**Standard.** none

#### THD against output level (model against model) (`opamp-thd-level`)

Group `distortion` · analysis `tran` · engines qspice, ngspice, ltspice · symbols THD(level).

At 1 kHz through the follower into 2 kΩ, the level stepped from 100 mVrms to 10 Vrms, where the distortion turns up at the clipping end; the level at which it passes 1 %.

**Circuit.** The follower with 2 kΩ; one deck per level.

Drawing: DUT as a follower; sine source; 2 kΩ load. Differs from the netlist: one deck per level.

**Conditions.** {supply: [15, -15], rl: 2000, f: 1000, vrms: [0.1, 1, 3, 6, 10], cycles: 12, analysed_cycles: 8, steps_per_cycle: 4096}

**The deck (QSPICE), line by line.**

- `VIN in 0 SIN(0 0.141421356 1000)` — 100 mVrms at 1 kHz; then 1, 3, 6 and 10 Vrms
- `XD in out vp vn out DUT`
- `RL out 0 2000`

**Extraction.** THD per level; the fundamental's amplitude; the level where THD passes 1 %, interpolated.

**Outputs.**

- `thd@1kHz,{level}`: THD at each level
- `vout@{level}` (V): the fundamental's peak at each level
- `v_clip@1%` (V): the input level (rms) at which THD passes 1 %

Curves: THD vs level (thd against vrms, log).

**What it cannot tell.** The noise floor at the low end for a model without noise.

**Standard.** none

#### Intermodulation (model against model) (`opamp-imd`)

Group `distortion` · analysis `tran` · engines qspice, ngspice, ltspice · symbols IMD.

SMPTE (60 Hz + 7 kHz, 4:1) and CCIF (19 kHz + 20 kHz, 1:1) at 3 Vrms in all through the follower into 2 kΩ.

**Circuit.** Two sine sources in series on the follower's input, 2 kΩ load.

Drawing: DUT as a follower; two sine sources; 2 kΩ load. Differs from the netlist: one deck per method.

**Conditions.** {supply: [15, -15], rl: 2000, smpte: {f1: 60, f2: 7000, a1: 3.394, a2: 0.8485, step_s: 1e-06, t_end_s: 0.15, t_from_s: 0.1, samples: 16384}, ccif: {f1: 19000, f2: 20000, a1: 2.1213, a2: 2.1213, step_s: 1e-07, t_end_s: 0.014, t_from_s: 0.004, samples: 32768}}

**The deck (QSPICE), line by line.**

- `VIN in mid SIN(0 3.394 60)` — SMPTE: 60 Hz and 7 kHz in series, four to one
- `VIN2 mid 0 SIN(0 0.8485 7000)`
- `XD in out vp vn out DUT`
- `RL out 0 2000`

**Extraction.** SMPTE as the 7 kHz sidebands at ±60 and ±120 Hz over the 7 kHz carrier; CCIF as the 1 kHz difference tone and the 18 and 21 kHz products over the two tones; Goertzel over the last 50 ms (10 ms).

**Outputs.**

- `imd_smpte`: SMPTE intermodulation, 60 Hz + 7 kHz 4:1, 3 Vrms
- `imd_ccif`: CCIF intermodulation, 19 + 20 kHz, 3 Vrms

**Standard.** none

#### THD against load (model against model) (`opamp-thd-load`)

Group `distortion` · analysis `tran` · engines qspice, ngspice, ltspice · symbols THD(RL).

At 1 kHz, 3 Vrms through the follower, the load from 100 Ω to 10 kΩ, how a model's output stage behaves into a heavy load; the fundamental's amplitude says whether the swing holds.

**Circuit.** The follower with the load; one deck per load.

Drawing: DUT as a follower; sine source; load. Differs from the netlist: one deck per load.

**Conditions.** {supply: [15, -15], f: 1000, vrms: 3, rl: [100, 300, 600, 2000, 10000], cycles: 12, analysed_cycles: 8, steps_per_cycle: 4096}

**The deck (QSPICE), line by line.**

- `VIN in 0 SIN(0 4.24264069 1000)` — 3 Vrms at 1 kHz into 100 Ω; then 300 Ω, 600 Ω, 2 kΩ and 10 kΩ
- `XD in out vp vn out DUT`
- `RL out 0 100`

**Extraction.** THD and the fundamental per load.

**Outputs.**

- `thd@{rl}`: THD into each load
- `vout@{rl}` (V): the fundamental's peak into each load

Curves: THD vs RL (thd against rl, log).

**Standard.** none

#### Channel separation (`opamp-separation`)

Group `supply` · analysis `derived` · engines qspice, ngspice, ltspice · symbols separation.

For a subcircuit with two or four amplifiers, the crosstalk from a driven channel to a quiet one. A macromodel of one amplifier in a package of two shares nothing: the result is absent, which is the finding. The fixture for dual subcircuits (onsemi's, the driven channel at G = +1 with 20 Vpp into 2 kΩ, the measured one at G = +100) is the next catalogue version's.

**Conditions.** {}

**Extraction.** Absent for every single-amplifier subcircuit, which every model run today is.

**Outputs.**

- `separation`: absent: one amplifier in the subcircuit

**What it cannot tell.** Anything, until dual subcircuits are run.

**Standard.** none

#### Do the three simulators agree? (`opamp-agreement`)

Group `dc` · analysis `derived` · engines qspice, ngspice, ltspice.

As the bipolar agreement, over every output above. Macromodels disagree between simulators on behavioural sources (PSpice TABLE and VALUE expressions, LTspice's own functions), on the convergence of their clamps, and on noise analysis; the disagreeing ids say which.

**Conditions.** {tolerances: [0.01, 0.05], floors: {F: 1e-16, s: 1e-12, A: 1e-14}}

**Extraction.** For each published output, the spread (max − min over the mean) across the engines that produced it, classed as within 1 %, within 5 % or beyond; values below the floors count as zero.

**Outputs.**

- `agree_1pct`: share of outputs on which every engine agrees within 1 %
- `agree_5pct`: share within 5 %
- `odd_engine`: the engine most often alone outside 5 %, or none
- `disagreeing`: the measurement ids where the engines differ by more than 5 %

**What it cannot tell.** Which engine is right.

**Standard.** none
<!-- measurements:end -->

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
