# MyElecParts: what its data looks like

A survey of [MyElecParts](https://myelecparts.hu/), a freeware Windows inventory program for electronics
hobbyists by "Majkimester" (Hungary), read on 2026-10-17 to see whether it carries a parts database worth
indexing. **It does not**: the inventory is empty until the user fills it, and the program's "meta search"
scrapes the data-sheet aggregators listed in `sources.csv` at run time. What it does ship is a tidy
taxonomy and two reference libraries, transcribed here as lists for future reference.

Read from `MyElecParts_1.81.zip` (92 784 004 bytes, sha256
`a33c522b41a70765f96a889019ac17b56f23ed3c79edecb916cb63fb007a5525`, dated 2026-07-05 on the server),
downloaded from `https://myelecparts.hu/download/MyElecParts_1.81.zip`. The program is distributed under
CC BY-NC-ND 4.0 (the licence its executable names); nothing from the archive is copied here except names,
numbers and file names. The images, the two example PDFs and the marking-code file stay out of the
repository (CLAUDE.md rule 1).

## Files

| file | rows | what |
|---|---|---|
| `packages.csv` | 464 | every package the program knows: name, aliases (JEDEC names, maker series), body size L x W x H in mm, description, and the two PNG file names it ships for each (a photo and a dimensioned drawing, 927 files under `Data/Package/`) |
| `manufacturers.csv` | 149 | every manufacturer it knows: name, description, home page, and its two PNG file names (a logo and the mark printed on the chip, 295 files under `Data/Manufacturer/`) |
| `part_categories.csv` | 326 | the 77 part categories in their groups, each with its typed parameters (249 in all), as the program's `DbTexts_en.xaml` names and describes them |
| `sources.csv` | 29 | every web site the executable queries: data-sheet aggregators for the meta search, SMD marking-code sites, Hungarian distributors |

## How the lists were read

The package and manufacturer tables are seeded from code, not from a data file, so they were read from
the executable's .NET user-string heap (strings in the order the compiler emitted them), cross-checked
against the PNG file names under `Data/`, and the descriptions resolved through `DbTexts_en.xaml`. The heap
stores each distinct string once, which limits what can be attributed safely:

- `dimensions_mm` is given only when the size string immediately precedes the package name (363 of 464);
  a package whose size equals an earlier one's shows blank rather than a guessed value.
- `description` is given only when its key sits in the package's own record (91 of 464); the program
  shares one description across a family (all TO metal cans, for instance), and the shared key is
  emitted once, so the rest are blank, not different.
- The package *category* (TO plastic, SOIC, MLCC ...) could not be attributed per package for the same
  reason and is left out. The category names are: Bridge, Capacitor, Capacitor pol., Decawatt, Display,
  CDIP, DIP, DO, Inductor SMD, Inductor TH, LED, Opto, PLCC, Potmeter, Resistor, Quartz, SIP, SOD, SOIC,
  SOJ, MSOP, SOP, SOT, Stud, TO Plastic, TO Metal, TQFP, Transformer, TSSOP.
- Five manufacturer URLs (Diodes, Infineon, Kemet, Teapo, Vishay) were emitted earlier in the heap, away
  from their record, and were attached because exactly one URL's host name contains the maker's name; the
  `note` column says so. The ten left blank are defunct makers (GI, RCA, Tungsram, MEV ...) the program
  itself gives no URL for.

## What else is in the archive

- `Data/Other/Marking.dat` (16 MB): the offline SMD marking-code table added in v1.60, a container with the
  magic `MEPD` holding six CSVs (`ELECTRONICA_PT`, `HOTENDA`, `KYTELABS`, `REPAIRCOMPANION`, `SMANUALS`,
  `YOONEEDONE`) with the columns source, marking, part number, manufacturer, package, pins, description.
  The payload is encrypted or otherwise obfuscated (byte entropy 8.0, no compression header); it was not
  opened, and being scraped third-party tables it would not be reused anyway.
- `Data/Part/BC182 (1)/`: the single example part, with two data sheets (Fairchild, ON Semi) and a pinout.
- `Customization/*_en.xaml`, `*_hu.xaml`: the English and Hungarian UI and database texts.
- The database schema is created by Entity Framework at first start (MSSQL LocalDB by default, SQL Server
  or PostgreSQL by configuration). A part record holds: part number, description, manufacturer, package,
  mounting (THT/SMD), marking, category with its parameters, storage location, stock, minimum stock,
  condition, attachments. Parts export and import as XLSX or JSON.

## Why it matters here

Nothing to index, but three lists are reusable as vocabularies: the package aliases (JEDEC TO-226AA for
TO-92 and the like) for the part catalogue, the manufacturer home pages as a check against
`data/parts/makers.yaml`, and the data-sheet aggregators and SMD marking sites as candidate sources for the
`datasheets/` pillar, with their known manners noted (Alltransistors' human check, Datasheet Archive's
per-network limit, DigChip's consent cookie).
