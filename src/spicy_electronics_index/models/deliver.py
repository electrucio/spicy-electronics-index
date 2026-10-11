"""Turn a collection gathered by hand in a browser into the deliveries `sei models ingest` takes.

    sei models deliver <collection-root> [--into DIR] [--source ID ...] [--dry]
    make models-deliver COLLECTION=<folder> [INTO=DIR] [SOURCE='a b'] [DRY=1]

The collection is the maintainer's browser round of 2026-10-10: one folder per vendor, holding the
vendor's own archives or a tar the round packed its downloads into, a `MANIFEST.tsv` saying what came
from which address, a `FUENTE.txt` inside each packed tar, and a few vendor indices. Nothing here
fetches anything. For each source this knows, it reads what the round brought, keeps the files the index
can read, works out each file's public address from the vendor's own URL pattern (the one the round
followed, which the existing ledger rows of the same source already use), and writes one delivery per
source: the files under a folder named after the source, the log `ingest` reads, and a note of what was
taken and what was left. `ingest` then does what it does for any delivery: copies, unpacks, records the
manifest and the ledger, and registers the source if it is new.

What a vendor publishes that the index has no use for stays in the collection: thermal networks,
IBIS, S-parameters, symbols for other simulators, documents, executables. A download that turned out
to be a web page is recorded as not published, with the address, so nobody asks for it again. A file
the source already holds, by address or by checksum, is not delivered twice.

The vendor libraries of passive parts are taken whole, with their own checksums, and opened only for a
handful of exemplary parts: the index has no use for thirty thousand capacitors, and one real example
per family is what lets the site say which makers publish models of that kind.
"""
from __future__ import annotations

import argparse
import csv
import fnmatch
import hashlib
import io
import re
import shutil
import sys
import tarfile
import zipfile
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import date
from functools import cached_property
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urlparse

import yaml

from spicy_electronics_index.core.config import deliveries, model_wanted, models_dir, wanted_parts
from spicy_electronics_index.models.fetch import already_have, inspect
from spicy_electronics_index.models.ingest import PRIVATE_QUERY, held_checksums
from spicy_electronics_index.models.match import keys_of, norm

LOG_NAME = "descargas.csv"
LOG_COLUMNS = ("source_id", "pieza", "fichero", "url_descarga", "url_pagina", "fecha", "estado", "notas", "miembros")
NOTE_NAME = "DELIVERY.md"

# Names and kinds of file no model ever comes in, or that the indexer could not read anyway.
JUNK_NAMES = {".DS_Store", "Thumbs.db", "FUENTE.txt", "FALLIDOS.txt", "INDICE.txt", "INDICE.tsv", "desktop.ini"}
JUNK_DIRS = {"__MACOSX"}
JUNK_SUFFIXES = {".ibs", ".pdf", ".stl", ".olb", ".opj", ".dsn", ".tsm", ".tsc", ".dwg", ".ppt", ".pptx", ".xlsx",
                 ".xlsm", ".doc", ".docx", ".v", ".vhd", ".s2p", ".s4p", ".ini", ".lnk", ".htm", ".html", ".mht",
                 ".encr", ".wxsch", ".step", ".stp", ".exe", ".msi", ".dll", ".bat", ".cmd", ".sym", ".7z", ".rar",
                 ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".url", ".json", ".xml", ".csv", ".md"}
# What `inspect` may say of a body that is worth keeping. A page or nothing is not a model; a binary is
# a simulator's own format the indexer cannot read.
KEEP_VERDICTS = {"model", "zip", "encrypted", "text_no_model", "zip_no_model"}


def stem_of(member: str) -> str:
    name = PurePosixPath(member).name
    return name[:-len("".join(PurePosixPath(name).suffixes))] if PurePosixPath(name).suffixes else name


def part_of(member: str) -> str:
    """The part a vendor's file name is about: the name before the first tag a vendor glues on."""
    s = stem_of(member)
    s = re.sub(r"(?i)[_-](spice|pspice|ltspice|simetrix|eldo|hspice|model|macromodel|ps|lt|p|l|rev\w*|v\d+)\b.*$", "", s)
    return (re.split(r"[_\s]", s)[0] or s).upper()


# --- what each source's folder holds, and how its files are addressed ------------------------------
@dataclass(frozen=True)
class Spec:
    source: str
    about: str                                   # one line for the delivery note
    archives: tuple[str, ...]                    # relative to the collection root: a tar, a zip or a folder
    page: str                                    # where the vendor offers the files (the log's url_pagina)
    hosts: tuple[str, ...]                       # every file URL must sit on one of these
    pattern: str = ""                            # the URL pattern, in words, for the delivery note
    select: Callable[[str], bool] = lambda m: True
    url: Callable[[str, "Context"], str | None] = lambda m, c: None
    rel: Callable[[str], str] = lambda m: m      # member -> path under the source's raw/
    part: Callable[[str], str] = part_of
    members: Callable[[str], list[str] | None] = lambda m: None   # archive -> the members to open it for
    page_only: bool = False                      # the files have no address of their own, only the page
    page_of: Callable[[str], str] | None = None  # the page a particular file is offered on, when it is not `page`
    left_out: str = ""                           # what of the folder is deliberately not delivered


def _strip(prefix: str) -> Callable[[str], str]:
    return lambda m: m[len(prefix):] if m.startswith(prefix) else m


def _rx(pattern: str) -> Callable[[str], bool]:
    r = re.compile(pattern)
    return lambda m: bool(r.search(m))


def _manifest_url(m: str, c: Context) -> str | None:
    return c.url_of(m)


def _exemplars(table: dict[str, list[str]]) -> Callable[[str], list[str] | None]:
    """Member patterns per archive, matched on the archive's own name."""
    def f(archive: str) -> list[str] | None:
        name = PurePosixPath(archive).name
        return next((pats for key, pats in table.items() if fnmatch.fnmatchcase(name, key)), None)
    return f


# The parts of TI's catalogue an analogue-audio index could want, by the families their numbers name:
# op amps, audio amplifiers, comparators, linear regulators and references, timers, the CMOS logic
# pedals use. TI titles its models "<part> PSpice Model", so the number is what says what a part is.
# ADCs, DC/DC controllers, drivers for motors and LEDs, interfaces and the rest stay in the collection.
TI_ANALOG = re.compile(r"(?i)^(OPA|OPT1|TL0[5-8]|TLE2|TLC2[0-9]|TLV2|TLV4|TLV6|TLV9|TLV27|LM[1-9]\d{2}[A-Z]{0,2}$|LME|LMH"
                       r"|LMV|LMC6|LMP|LF[34]\d|NE5[35]|SA5[35]|SE5[35]|RC4|MC1458|MC4558|INA|THS|TPA|LM386|LM48|TAS"
                       r"|DRV13[45]|PGA|VCA|LM311|LM339|LM393|LM2901|LM2903|TLV3|TLC3[0-9]|LM78|LM79|LM317|LM337|TPS7"
                       r"|LP29|LP38|UA7|TL43|TLV431|LM404|REF[0-9]|NE555|LM555|TLC555|LMC555|SE555|CD4|MC33|MC34"
                       r"|UA741|LM741|LM13700|LM833|LM4562|LM49|LM3886|LM1875|LM1876|LM4766|LM3875|LM4780|TDA|LM394"
                       r"|LM3900|LM3915|LM3916|LM3914|XTR|ISO1|AMC1|SN74HC(?:00|02|04|08|14|32|74|86|4066|4051|4052|4053)"
                       r"|CD74HC(?:00|02|04|08|14|32|74|86|4066|4051|4052|4053)|TS5A|TS3A|SN74LVC1G|DAC8[0-9]{2}\b)")
TI_NOT = re.compile(r"(?i)(TINA|IBIS|S-?param|reference design|HSPICE|SIMPLIS|Verilog|thermal|package|EVM)")


def _ti_wanted(member: str, c: Context) -> bool:
    name = PurePosixPath(member).name
    if not name.lower().endswith(".zip"):
        return False
    entry = c.ti_index.get(name) or c.ti_index.get(stem_of(member).split("__")[0].upper())
    if not entry:
        return False
    product, title = entry
    if TI_NOT.search(title):
        return False
    return bool(keys_of(product) & c.wanted) or bool(TI_ANALOG.search(product))


TI_LIT = re.compile(r"^[A-Z]{3,5}[0-9]{2,4}[A-Z]?$")


def _ti_url(member: str, c: Context) -> str | None:
    """`pspice/<PN>__<lit>.zip` is addressed by the index's LIT code; a newer product's `<LIT>.zip` by its
    own name. Both are `https://www.ti.com/lit/zip/<LIT>`, upper case, as the ledger keys them."""
    name = PurePosixPath(member).name
    lit = c.ti_lit.get(name) or (stem_of(member).upper() if TI_LIT.match(stem_of(member).upper()) else None)
    return f"https://www.ti.com/lit/zip/{lit}" if lit else None


def _ti_rel(member: str) -> str:
    # pspice/<PN>__<lit>.zip stays; TI_productos_nuevos/<PN>/<LIT>.zip -> new/<PN>/<LIT>.zip
    return "new/" + member.split("/", 1)[1] if member.startswith("TI_productos_nuevos/") else member


def _onsemi_dir(member: str) -> str:
    return _strip("onsemi_extra/")(member)


def _nexperia(member: str) -> str:
    """The second tar of the round carries its own top folder; below it the layout is the first tar's."""
    return _strip("Nexperia_extra/")(member)


def _nexperia_url(member: str, c: Context) -> str | None:
    """Nexperia's asset store answers for the .txt and .zip model files by name (checked: same bytes);
    the .prm and .lib files the documentation centre hands out are not there under any spelling tried,
    so they carry no address of their own and the recipe sends a reader to the product page."""
    name = PurePosixPath(member).name
    if name.lower().endswith((".txt", ".zip")):
        return f"https://assets.nexperia.com/documents/spice-model/{name}"
    return None


def _nexperia_page(member: str) -> str:
    return f"https://www.nexperia.com/product/{stem_of(member).upper().split('_')[0]}"


ONSEMI_DIRS = {"lib", "mod", "sp2", "sp3", "sin", "inc", "zip", "txt", "cir", "scs"}

SPECS: dict[str, Spec] = {}


def spec(s: Spec) -> Spec:
    SPECS[s.source] = s
    return s


spec(Spec("central-semi", "Central Semiconductor's complete Spice Model Listing, one .LIB per part",
          ("44_Central_Semi/Central_Semi_SPICE_models.tar",),
          "https://my.centralsemi.com/content/engineering/spicemodels/index.php", ("www.centralsemi.com",),
          pattern="https://www.centralsemi.com/docs/ENGINEERING/csm/<PART>.LIB",
          select=_rx(r"(?i)^Central_Semi/.+\.lib$"),
          url=lambda m, c: f"https://www.centralsemi.com/docs/ENGINEERING/csm/{PurePosixPath(m).name}",
          rel=_strip("Central_Semi/")))
spec(Spec("mcc", "Micro Commercial Components' SPICE models, one zip per part",
          ("49_MCC/MCC_SPICE_models.tar",), "https://www.mccsemi.com/", ("www.mccsemi.com",),
          pattern="https://www.mccsemi.com/diodespicemodel/<PART>.zip",
          select=_rx(r"(?i)^MCC/.+\.zip$"),
          url=lambda m, c: f"https://www.mccsemi.com/diodespicemodel/{PurePosixPath(m).name}",
          rel=_strip("MCC/")))
spec(Spec("nexperia", "Nexperia's documentation centre, sub-category model: the SPICE models",
          ("42_Nexperia/Nexperia_SPICE_models_parcial.tar", "42_Nexperia/Nexperia_SPICE_y_termicos_resto.tar"),
          "https://www.nexperia.com/support/simulation-and-modeling/spice-models", ("assets.nexperia.com", "www.nexperia.com"),
          pattern="https://assets.nexperia.com/documents/spice-model/<file> for .txt and .zip; the product page for .prm and .lib",
          select=lambda m: bool(re.match(r"^SPICE_model/[^/]+$", _nexperia(m))),
          url=_nexperia_url, page_of=_nexperia_page,
          rel=lambda m: _strip("SPICE_model/")(_nexperia(m)), part=lambda m: stem_of(m).upper(),
          left_out="Thermal_model/ and Thermal_design/ (RC thermal networks, not models of the device)"))
spec(Spec("diodes-inc", "Diodes Incorporated's SPICE models, one text file per part",
          ("20_Diodes/Diodes_SPICE_models_all.tar",), "https://www.diodes.com/design/tools/spice-models",
          ("www.diodes.com",), pattern="https://www.diodes.com/spice/download/<id>/<PART>.spice.txt",
          select=_rx(r"^parts/\d+_[^/]+\.spice\.txt$"),
          url=lambda m, c: "https://www.diodes.com/spice/download/{}/{}".format(*PurePosixPath(m).name.split("_", 1)),
          rel=_strip("parts/"), part=lambda m: PurePosixPath(m).name.split("_", 1)[1].split(".")[0].upper(),
          left_out="other/ (twenty zips of IC models with no address of their own)"))
spec(Spec("vishay", "Vishay's design-tool downloads, SPICE Model section: discrete semiconductors",
          ("16_Vishay/Vishay_SPICE_thermal_models.tar",), "https://www.vishay.com/en/how/design-support-tools/",
          ("www.vishay.com",), pattern="https://www.vishay.com/docs/<docid>/<file>",
          select=_rx(r"^SPICE_Model/(?!MOSFETs_Automotive/|Silicon_Carbide/|Power_Modules/|MOSFETs_Medical/)[^/]+/\d+_[^/]+$"),
          url=lambda m, c: "https://www.vishay.com/docs/{}/{}".format(*PurePosixPath(m).name.split("_", 1)),
          rel=_strip("SPICE_Model/"),
          part=lambda m: part_of(PurePosixPath(m).name.split("_", 1)[1]),
          left_out="RC_Thermal_Model/, Software_Model/, S-Parameters/, and the automotive, silicon-carbide, "
                   "power-module and medical MOSFET lines"))
spec(Spec("stmicro", "STMicroelectronics' product pages: SPICE and Eldo models",
          tuple(f"50_STMicroelectronics/ST_SPICE_models_parte{p}.tar" for p in ("1", "2a", "2b", "2c")),
          "https://www.st.com/", ("www.st.com",), pattern="https://www.st.com/resource/en/<type>_model/<file>",
          select=_rx(r"^ST/(?!space-products/)[^/]+/(spice|eldo)_model/[^/]+\.(?!7z$)[^./]+$"),
          url=lambda m, c: "https://www.st.com/resource/en/{}/{}".format(*m.split("/")[2:4]),
          rel=_strip("ST/"), part=lambda m: re.split(r"[_\-]", stem_of(m))[0].upper(),
          left_out="orcad_model/ (symbols), simetrix_model/, space-products/, and archives in 7z"))
spec(Spec("onsemi", "onsemi's technical documentation, type Models: the simulation model files",
          ("34_onsemi/onsemi_simulation_models.tar", "34_onsemi/onsemi_simulation_models_extra.tar"),
          "https://www.onsemi.com/design/technical-documentation/simulation-spice-models", ("www.onsemi.com",),
          pattern="https://www.onsemi.com/download/models/<dir>/<file>",
          select=lambda m: _onsemi_dir(m).split("/")[0] in ONSEMI_DIRS and _onsemi_dir(m).count("/") == 1,
          url=lambda m, c: "https://www.onsemi.com/download/models/" + quote(_onsemi_dir(m)),
          rel=_onsemi_dir, part=lambda m: part_of(m.split(".")[0]),
          left_out="IBIS, OLB, drawings, presentations, Verilog, S-parameters, and the SIMPLIS archive"))
spec(Spec("ti", "Texas Instruments' product pages: the PSpice models of analogue parts and of parts looked for",
          ("28_TI/TI_PSpice_models_5351.tar", "28_TI/TI_modelos_productos_nuevos_2021-2026.tar"),
          "https://www.ti.com/", ("www.ti.com",), pattern="https://www.ti.com/lit/zip/<LIT>",
          select=lambda m: False,          # decided with the index in hand: see _ti_wanted
          url=_ti_url, rel=_ti_rel, part=lambda m: stem_of(m).split("__")[0].upper() if "__" in m else m.split("/")[1].upper(),
          left_out="data converters, power controllers, drivers and everything else not analogue; TINA, "
                   "HSPICE, IBIS and S-parameter files"))
spec(Spec("renesas", "Renesas' document search: the public SPICE and iSim models, one by one",
          ("39_Renesas/modelos",), "https://www.renesas.com/en/support/document-search", ("www.renesas.com",),
          pattern="the document's own address, as the search listed it",
          select=lambda m: True, url=lambda m, c: c.renesas.get(PurePosixPath(m).name),
          left_out="files the search did not list (duplicates and a schematic), and the ~810 documents "
                   "MyRenesas keeps behind a login"))
spec(Spec("toshiba", "Toshiba's PSpice model archive did=800, published after the one already held",
          ("11_Toshiba/PSpice/PSpice_files_20260927.zip",),
          "https://toshiba.semicon-storage.com/ap-en/semiconductor/design-development/eda-cad-lib/ltspice-library.html",
          ("toshiba.semicon-storage.com",), pattern="the archive's address", url=_manifest_url,
          left_out="did=100, a newer revision of an archive already held; the LTspice archive, identical to the one held"))
spec(Spec("rohm", "ROHM's document search, SPICE and LTspice models of transistors and diodes",
          ("30_ROHM/ROHM_SPICE_y_LTspice_pasada1.tar", "30_ROHM/ROHM_SPICE_y_LTspice_pasada2.tar"),
          "https://www.rohm.com/search/application-notes?DocType=SPICE%20Model", ("fscdn.rohm.com",),
          pattern="https://fscdn.rohm.com/en/products/library/<path>",
          select=_rx(r"^(spice|ltspice)/discrete/(transistor|diode)/.+\.zip$"),
          url=lambda m, c: "https://fscdn.rohm.com/en/products/library/" + quote(m),
          left_out="IGBT, SiC, GaN, ICs, LEDs, thermal models and the data book"))
spec(Spec("taiwan-semi", "Taiwan Semiconductor's resources page: the SPICE models",
          ("48_Taiwan_Semi/TaiwanSemi_SPICE_y_Thermal_models.tar",), "https://www.taiwansemi.com/en/resources/tools/",
          ("www.taiwansemi.com",), pattern="no address of their own: the page lists them",
          select=_rx(r"(?i)^TaiwanSemi/SPICE/[^/]+\.txt$"), rel=_strip("TaiwanSemi/"), page_only=True,
          part=lambda m: stem_of(m).upper(), left_out="Thermal/"))
spec(Spec("panjit", "PANJIT's official archive of every SPICE model", ("45_PANJIT/PANJIT_SPICE_Models.zip",),
          "https://www.panjit.com.tw/en/Support?filter=34", ("www.panjit.com.tw",),
          pattern="no address of its own: the support page offers the archive", page_only=True))
spec(Spec("fotoelektronika", "Fotoelektronika's SPICE and TINA models of opto parts, valves and ICs",
          ("33_Fotoelektronika/Fotoelektronika_SPICE_models.tar",), "https://fotoelektronika.com/spice-models/",
          ("fotoelektronika.com",), pattern="https://fotoelektronika.com/wp-content/uploads/<yyyy>/<mm>/<file>",
          select=_rx(r"^\d{4}/\d{2}/[^/]+\.zip$"),
          url=lambda m, c: "https://fotoelektronika.com/wp-content/uploads/" + quote(m),
          left_out="the PDFs"))
spec(Spec("tdsl-cigna", "Duncan's Tube Data Sheet Locator: the valve models of Piazza and Munro, 2000",
          ("17_Valvulas_Audio/TDSL_Cigna/tdsl_tubes_spice.zip",), "http://tdsl.duncanamps.com/dcigna/tubes/spice/",
          ("tdsl.duncanamps.com",), pattern="the archive's address", url=_manifest_url))

# Passives: the maker's library whole, opened for one or two exemplary parts each.
spec(Spec("murata", "Murata's LTspice and PSpice libraries: MLCC and NTC thermistors",
          ("02_Murata/LTspice/murata-lib-ltspice-s-mlcc-2606.zip", "02_Murata/LTspice/murata-lib-ltspice-d-mlcc-2606.zip",
           "02_Murata/LTspice/murata-lib-ltspice-s-ntc-2508.zip", "02_Murata/pspice/murata-lib-pspice-ntc-thermistor-2508.zip"),
          "https://www.murata.com/en-global/tool/library/ltspice", ("www.murata.com",),
          pattern="the archive's address", url=_manifest_url,
          members=_exemplars({
              "murata-lib-ltspice-s-mlcc-*": ["*/sub/Murata_static/MLCC/GRM.lib", "*/sub/Murata_static/MLCC/GR4.lib",
                                               "*/sym/Murata_static/MLCC/GRM188R71H104KA93.asy",
                                               "*/sym/Murata_static/MLCC/GRM21BR61E106KA73.asy"],
              "murata-lib-ltspice-d-mlcc-*": ["*GRM188R71H104KA93_*", "*GRM21BR61E106KA73_*"],
              "murata-lib-ltspice-s-ntc-*": ["*/NCP18.lib", "*NCP18XH103F03RB*"],
          }),
          left_out="every other series and part: the libraries are held whole and opened for the exemplars"))
spec(Spec("samsung-electro-mechanics", "Samsung Electro-Mechanics' static MLCC libraries for LTspice and PSpice",
          ("12_Samsung_SEM/Samsung_LTSPICE_Static_Library.zip", "12_Samsung_SEM/Samsung_PSPICE_Static_Library.zip"),
          "https://weblib.samsungsem.com/", ("weblib.samsungsem.com",), pattern="the archive's address", url=_manifest_url,
          members=_exemplars({"Samsung_*": ["*CL10B104KB8NFN_*", "*CL21A106KACLRN_*"]}),
          left_out="every other part: the libraries are held whole and opened for the exemplars"))
spec(Spec("tdk", "TDK's TVCL library: the C1608 commercial MLCC series for LTspice and PSpice",
          ("25_TDK_Corp_TVCL/TDK_TVCL_SPICE_y_Sparam_all.tar",), "https://product.tdk.com/en/technicalsupport/tvcl/",
          ("product.tdk.com",), pattern="no address of their own: the TVCL page offers the archives",
          select=_rx(r"^tvcl/(ltspice|pspice)/capacitor_mlcc_com_general_c1608_(ltspice|pspice)\.zip$"),
          rel=_strip("tvcl/"), page_only=True,
          members=_exemplars({"capacitor_mlcc_com_general_c1608_*": ["*C1608X7R1H104K080AA*"]}),
          left_out="every other series, S-parameters and HSPICE/Spectre forms"))
spec(Spec("taiyo-yuden", "Taiyo Yuden's temperature- and bias-dependent MLCC libraries for LTspice and PSpice",
          ("07_TaiyoYuden/LTspice_TempDC/LT_TY31.zip", "07_TaiyoYuden/PSpice_TempDC/PS_TY31.zip"),
          "https://www.yuden.co.jp/en/product/support/", ("www.yuden.co.jp",), pattern="the archive's address",
          url=_manifest_url, members=_exemplars({"*_TY31.zip": ["*MAASE168SB7104*"]}),
          left_out="every other part: the libraries are held whole and opened for the exemplar"))
spec(Spec("wurth", "Würth Elektronik's LTspice library on GitHub: the WE-CBF ferrites and WE-PD inductors",
          ("08_Wurth/GitHub/WurthElektronik-LTspice-Library.zip",), "https://github.com/WurthElektronik/LTspice-Library",
          ("github.com",), pattern="https://github.com/WurthElektronik/LTspice-Library/archive/<commit>.zip",
          url=lambda m, c: c.github_archive_url(m, "https://github.com/WurthElektronik/LTspice-Library"),
          members=_exemplars({"WurthElektronik-LTspice-Library.zip": ["*/sub/WE-CBF.lib", "*/sub/WE-PD.lib",
                                                                         "*/sym/*WE-CBF*", "*/sym/*WE-PD*"]}),
          left_out="the other families: the library is held whole and opened for two"))
spec(Spec("coilcraft", "Coilcraft's LTspice library: the MSS1260 power inductors",
          ("09_Coilcraft/CoilcraftLTAdvLib.zip",), "https://www.coilcraft.com/en-us/models/spice/", ("www.coilcraft.com",),
          pattern="the archive's address", url=_manifest_url,
          members=_exemplars({"CoilcraftLTAdvLib.zip": ["*MSS1260.lib", "*MSS1260*.asy"]}),
          left_out="the other families: the library is held whole and opened for one"))
spec(Spec("nichicon", "Nichicon's conductive-polymer capacitor models: the GYB series",
          ("24_Nichicon/Nichicon_SPICE_models_all.tar",), "https://www.nichicon.co.jp/english/products/spice/",
          ("www.nichicon.co.jp", "www.nichicon.com"), pattern="no address of their own: the SPICE page offers the archives",
          select=_rx(r"^GYB\.zip$"), page_only=True,
          members=_exemplars({"GYB.zip": ["*GYB1E101MCQ1GS*"]}),
          left_out="the other series"))


# --- what the collection knows about itself ----------------------------------------------------------
class Context:
    def __init__(self, root: Path):
        self.root = root

    @cached_property
    def manifest(self) -> list[dict]:
        p = self.root / "MANIFEST.tsv"
        if not p.exists():
            return []
        with open(p, encoding="utf-8", newline="") as f:
            return [r for r in csv.DictReader(f, delimiter="\t") if r.get("archivo")]

    def _row(self, archive: str) -> dict | None:
        folder, name = str(PurePosixPath(archive).parent), PurePosixPath(archive).name
        return next((r for r in self.manifest if r["carpeta"].strip("/") == folder and r["archivo"] == name), None)

    def url_of(self, archive: str) -> str | None:
        r = self._row(archive)
        u = (r or {}).get("url", "").strip()
        return u if u.startswith("http") else None

    def date_of(self, archive: str) -> str:
        """When the archive was downloaded; for a folder the round did not list, the round's own day."""
        r = self._row(archive)
        d = (r or {}).get("fecha", "")
        if re.match(r"\d{4}-\d{2}-\d{2}", d):
            return d[:10]
        days = sorted(x["fecha"][:10] for x in self.manifest if re.match(r"\d{4}-\d{2}-\d{2}", x.get("fecha", "")))
        return days[-1] if days else date.today().isoformat()

    @cached_property
    def wanted(self) -> set[str]:
        """Every name the index looks for, normalised: the hand-written list with its aliases and
        complements, the generated list, and the parts that already have a recipe."""
        out: set[str] = set()
        stack = [yaml.safe_load(model_wanted().read_text(encoding="utf-8")) or {}]
        while stack:
            x = stack.pop()
            if isinstance(x, dict):
                if "part" in x:
                    for k in ("part", "complement"):
                        if x.get(k):
                            out.add(norm(str(x[k])))
                    out.update(norm(str(a)) for a in x.get("aliases") or [])
                else:
                    stack.extend(x.values())
            elif isinstance(x, list):
                stack.extend(x)
        if wanted_parts().exists():
            with open(wanted_parts(), encoding="utf-8", newline="") as f:
                out.update(norm(r["part"]) for r in csv.DictReader(f) if r.get("part"))
        out.update(norm(p.stem) for p in (models_dir() / "parts").glob("*/*.yaml"))
        return out

    @cached_property
    def ti_index(self) -> dict[str, tuple[str, str]]:
        """file name or LIT -> (product, title), from the two indices the round wrote."""
        out: dict[str, tuple[str, str]] = {}
        for line in self._member_text("28_TI/TI_PSpice_models_5351.tar", "pspice/INDICE.txt").splitlines():
            cells = line.split("\t")
            if len(cells) >= 3 and cells[0].startswith("pspice/"):
                name = PurePosixPath(cells[0]).name
                out[name] = (stem_of(name).split("__")[0], cells[2])
        text = self._member_text("28_TI/TI_modelos_productos_nuevos_2021-2026.tar", "TI_productos_nuevos/INDICE.tsv")
        for r in csv.DictReader(text.splitlines(), delimiter="\t"):
            if r.get("codigo"):
                out[r["codigo"].upper()] = (r.get("producto", ""), f"{r.get('titulo', '')} {r.get('descripcion', '')}")
        return out

    @cached_property
    def ti_lit(self) -> dict[str, str]:
        """file name -> LIT code, upper case as the ledger keys it."""
        out: dict[str, str] = {}
        for line in self._member_text("28_TI/TI_PSpice_models_5351.tar", "pspice/INDICE.txt").splitlines():
            cells = line.split("\t")
            if len(cells) >= 2 and cells[0].startswith("pspice/"):
                out[PurePosixPath(cells[0]).name] = cells[1].strip().upper()
        return out

    @cached_property
    def renesas(self) -> dict[str, str]:
        """file name -> the document URL the search listed."""
        p = self.root / "39_Renesas/Renesas_modelos_URLs.tsv"
        out: dict[str, str] = {}
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                cells = line.split("\t")
                if len(cells) >= 3 and cells[0].startswith("http"):
                    out[cells[2].strip()] = cells[0].strip()
        return out

    @cached_property
    def insecure(self) -> set[str]:
        """The checksums SEGURIDAD.md lists: executables and documents with macros, never delivered."""
        p = self.root / "SEGURIDAD.md"
        return set(re.findall(r"`([0-9a-f]{64})`", p.read_text(encoding="utf-8"))) if p.exists() else set()

    def _member_text(self, archive: str, member: str) -> str:
        p = self.root / archive
        if not p.exists():
            return ""
        with tarfile.open(p) as t:
            try:
                f = t.extractfile(member)
            except KeyError:
                return ""
            return f.read().decode("utf-8", "replace") if f else ""

    def fuente(self, archive: str) -> str:
        """The round's own note inside a packed tar, when there is one."""
        p = self.root / archive
        if not p.is_file() or not tarfile.is_tarfile(p):
            return ""
        with tarfile.open(p) as t:
            for m in t.getmembers():
                if m.isfile() and PurePosixPath(m.name).name == "FUENTE.txt":
                    f = t.extractfile(m)
                    return f.read().decode("utf-8", "replace") if f else ""
        return ""

    def github_archive_url(self, archive: str, repo: str) -> str | None:
        """A GitHub zip names its commit in its top folder: `<repo>-<sha>/`. That is the archive's address."""
        p = self.root / archive
        if not p.exists():
            return None
        with zipfile.ZipFile(p) as z:
            top = next((n.split("/")[0] for n in z.namelist() if "/" in n), "")
        m = re.search(r"-([0-9a-f]{40})$", top)
        return f"{repo}/archive/{m.group(1)}.zip" if m else None


# --- the walk ---------------------------------------------------------------------------------------
def safe(member: str) -> bool:
    """A member path that stays inside the folder it is unpacked into."""
    p = PurePosixPath(member)
    return bool(member) and not p.is_absolute() and ".." not in p.parts and not member.startswith("/")


def walk(root: Path, archive: str) -> Iterator[tuple[str, bytes]]:
    """(member, bytes) for everything an archive of the collection holds: a tar's files, a folder's
    files, or the one file a zip is. Never writes; never follows a link."""
    p = root / archive
    if not p.exists():
        return
    if p.is_dir():
        for f in sorted(p.rglob("*")):
            if f.is_file() and not f.is_symlink():
                yield f.relative_to(p).as_posix(), f.read_bytes()
    elif tarfile.is_tarfile(p):
        with tarfile.open(p) as t:
            for m in t:
                if m.isfile() and safe(m.name):
                    f = t.extractfile(m)
                    if f:
                        yield m.name, f.read()
    else:
        yield p.name, p.read_bytes()


def junk(member: str) -> bool:
    p = PurePosixPath(member)
    return (p.name in JUNK_NAMES or bool(JUNK_DIRS & set(p.parts)) or p.suffix.lower() in JUNK_SUFFIXES
            or p.name.startswith("._"))


@dataclass
class Outcome:
    rows: list[dict] = field(default_factory=list)
    files: dict[str, bytes] = field(default_factory=dict)      # rel -> bytes
    counts: dict[str, int] = field(default_factory=dict)
    archives: list[str] = field(default_factory=list)

    def count(self, what: str, n: int = 1) -> None:
        self.counts[what] = self.counts.get(what, 0) + n


def cited_by_recipes() -> set[str]:
    """Every checksum the published recipes cite: a model's file, the archive it came in, its symbol, and
    each copy's. A delivery kept to these holds exactly what the index can point a reader at."""
    keep: set[str] = set()
    def take(g: dict) -> None:
        for k in ("sha256", "archive_sha256"):
            if g.get(k):
                keep.add(g[k])
        if g.get("symbol"):
            take(g["symbol"])
    for f in (models_dir() / "parts").glob("*/*.yaml"):
        for m in (yaml.safe_load(f.read_text(encoding="utf-8")) or {}).get("models") or []:
            take(m.get("get") or {})
            for copy in m.get("copies") or []:
                take(copy.get("get") or {})
    return keep


def cited_members(data: bytes, keep: set[str]) -> list[str]:
    """The members of an archive whose checksum a recipe cites, as patterns `unpack` takes."""
    out = []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for i in z.infolist():
            if not i.is_dir() and hashlib.sha256(z.read(i)).hexdigest() in keep:
                out.append(i.filename.replace("[", "[[]"))
    return out


def deliver_source(s: Spec, c: Context, keep: set[str] | None = None) -> Outcome:
    """`keep`: deliver only files (and archive members) whose checksum is in it — what the recipes cite —
    and nothing else; an archive is then kept whole, with its own checksum, and opened for those members."""
    out = Outcome()
    seen_urls: set[str] = set()
    seen_sha: set[str] = set()
    held = held_checksums(s.source)
    for archive in s.archives:
        if not (c.root / archive).exists():
            out.count("archive_missing")
            continue
        out.archives.append(archive)
        is_whole = not (c.root / archive).is_dir() and not tarfile.is_tarfile(c.root / archive)
        for member, data in walk(c.root, archive):
            if not is_whole:
                if junk(member):
                    out.count("left:junk")
                    continue
                selected = _ti_wanted(member, c) if s.source == "ti" else s.select(member)
                if not selected:
                    out.count("left:not_selected")
                    continue
            sha = hashlib.sha256(data).hexdigest()
            if sha in c.insecure:
                out.count("left:insecure")
                continue
            verdict = inspect(data)[0]
            url = None if s.page_only else (s.url(member, c) if not is_whole else (s.url(archive, c) or c.url_of(archive)))
            if url and (PRIVATE_QUERY.search(url) or urlparse(url).netloc not in s.hosts):
                raise ValueError(f"{s.source}: {member}: not an address the ledger may hold: {url}")
            part = s.part(member) if not is_whole else ""
            page = s.page_of(member) if (s.page_of and not is_whole) else s.page
            if verdict in ("html", "empty"):
                out.count("not_published")
                if url or part:
                    out.rows.append(dict(source_id=s.source, pieza=part, fichero="", url_descarga=url or "",
                                         url_pagina=page, fecha=c.date_of(archive), estado="no_publicado",
                                         notas=f"a page, not a file: {archive}", miembros=""))
                continue
            if verdict not in KEEP_VERDICTS:
                out.count(f"left:{verdict}")
                continue
            # A page is recorded above whatever the recipes cite: that a vendor has nothing is worth keeping.
            cited: list[str] | None = None
            if keep is not None and sha not in keep:
                cited = cited_members(data, keep) if data[:2] == b"PK" else []
                if not cited:
                    out.count("left:not_cited")
                    continue
            if (url and url in seen_urls) or sha in seen_sha:
                out.count("left:duplicate_in_collection")
                continue
            if (url and already_have(s.source, url)) or sha in held:
                out.count("held_already")
                continue
            seen_urls.add(url or "")
            seen_sha.add(sha)
            rel = s.rel(member) if not is_whole else member
            if rel in out.files:
                rel = f"{PurePosixPath(member).parent.name}__{PurePosixPath(rel).name}"   # two of one name
            out.files[rel] = data
            out.count("files")
            members = cited if cited else (s.members(member if not is_whole else archive) if data[:2] == b"PK" else None)
            out.rows.append(dict(source_id=s.source, pieza=part, fichero=rel, url_descarga=url or "",
                                 url_pagina=page, fecha=c.date_of(archive), estado="encontrado",
                                 notas=f"from {archive}", miembros=";".join(members) if members else ""))
    # the same zip stem twice would unpack into one folder: name the second after its own folder
    stems: dict[str, str] = {}
    for rel in list(out.files):
        if rel.lower().endswith(".zip"):
            stem = PurePosixPath(rel).stem.lower()
            if stem in stems:
                new = f"{PurePosixPath(rel).parent.name}__{PurePosixPath(rel).name}"
                out.files[new] = out.files.pop(rel)
                for r in out.rows:
                    if r["fichero"] == rel:
                        r["fichero"] = new
                out.count("renamed_for_stem")
            else:
                stems[stem] = rel
    return out


def note(s: Spec, c: Context, out: Outcome) -> str:
    lines = [f"# {s.source} — delivery from the maintainer's browser round",
             "",
             f"Made by `sei models deliver` on {date.today().isoformat()} from the collection's folder(s) "
             f"{', '.join('`' + a + '`' for a in out.archives) or '(none found)'}.",
             "",
             f"- **What:** {s.about}.",
             f"- **Offered at:** {s.page}",
             f"- **Each file's address:** {s.pattern or 'the page above'}"
             + (" — the files have no address of their own; the ledger keys them by path and the recipe says "
                "the link leads to the page." if s.page_only else ""),
             f"- **Left in the collection:** {s.left_out or 'nothing of what the folder holds'}.",
             "- **Counts:** " + ", ".join(f"{k} {v}" for k, v in sorted(out.counts.items())) + ".",
             ""]
    for a in out.archives:
        text = c.fuente(a)
        if text:
            head = "\n".join(text.splitlines()[:6])
            lines += [f"## The round's own note in `{a}` (FUENTE.txt, first lines, as written)", "", "```", head, "```", ""]
    return "\n".join(lines)


def write(s: Spec, c: Context, out: Outcome, into: Path) -> Path:
    home = into / s.source
    if home.exists():
        shutil.rmtree(home)
    (home / s.source).mkdir(parents=True)
    for rel, data in out.files.items():
        target = home / s.source / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    with open(home / LOG_NAME, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LOG_COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(out.rows)
    (home / NOTE_NAME).write_text(note(s, c, out), encoding="utf-8")
    return home


def check_public(out: Outcome, root: Path) -> None:
    """Nothing that goes into the public ledger may name this machine or the collection."""
    for r in out.rows:
        for k in ("url_descarga", "url_pagina", "pieza"):
            v = r[k]
            if str(root) in v or "/Users/" in v or "/home/" in v:
                raise ValueError(f"a local path in the log: {v}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("collection", help="the folder the browser round left: tars, zips, MANIFEST.tsv")
    ap.add_argument("--into", help="where to write the deliveries (default: the private deliveries folder, dated)")
    ap.add_argument("--source", action="append", help="only these sources (repeatable); default: every one known")
    ap.add_argument("--dry", action="store_true", help="count what would be delivered and write nothing")
    ap.add_argument("--list", action="store_true", help="name the sources this knows and stop")
    ap.add_argument("--cited", action="store_true", help="only the files and archive members the recipes cite")
    a = ap.parse_args(argv)
    if a.list:
        for s in SPECS.values():
            print(f"{s.source:28s} {s.about}")
        return 0
    root = Path(a.collection).expanduser()
    if not root.is_dir():
        print(f"{root} is not a folder", file=sys.stderr)
        return 1
    into = Path(a.into).expanduser() if a.into else deliveries() / date.today().isoformat()
    c = Context(root)
    wanted = a.source or list(SPECS)
    unknown = [s for s in wanted if s not in SPECS]
    if unknown:
        print(f"no delivery is known for: {', '.join(unknown)} (see --list)", file=sys.stderr)
        return 1
    keep = cited_by_recipes() if a.cited else None
    for name in wanted:
        s = SPECS[name]
        out = deliver_source(s, c, keep)
        check_public(out, root)
        size = sum(len(b) for b in out.files.values())
        where = "" if a.dry else f" -> {write(s, c, out, into)}"
        print(f"{s.source:28s} {out.counts.get('files', 0):6d} files {size / 1e6:8.1f} MB  "
              + ", ".join(f"{k}={v}" for k, v in sorted(out.counts.items()) if k != "files") + where)
    if not a.dry:
        print(f"\nthen, per source: make models-ingest FROM={into}/<source> DRY=1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
