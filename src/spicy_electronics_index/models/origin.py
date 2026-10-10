"""Who probably made a model, read from where its file sits.

The source is who we fetched a file from; the origin is who wrote the models in it. For a maker's own
site the two coincide. For a collection they do not: Bordodynov's lib.zip re-hosts vendor and third-party
files under their own names, the Spice Model CD is OrCAD's 1990s vendor set sorted by maker, Micro-Cap's
library names the maker in the file name, KiCad-Spice-Library bundles whole collections. The rules below
read those names; a file no rule names is credited to its source. The class says how far from the author
the file is, and the lowest class among the copies of one model picks the copy a reader is sent to.
"""
import re

VENDOR = 10         # the maker's own file, from the maker's site
VENDOR_REDIST = 20  # a maker's file as another party distributes it, named after the maker
SIMULATOR = 25      # a simulator's own library: ADI's for LTspice, Qorvo's for QSPICE, Spectrum's for Micro-Cap
MODELLER = 30       # a person who fits models and publishes them under their own name
FORUM = 35          # a person's model posted on a forum
COMPILATION = 40    # a community's compiled library: the LTspice group's standard.bjt
COLLECTION = 45     # one person's collection of other people's files
AGGREGATE = 50      # an aggregate of collections

# the short name a recipe carries for the class, and what it means (the page prints the meaning)
HOW = {
    VENDOR: "maker",
    VENDOR_REDIST: "maker-redistributed",
    SIMULATOR: "simulator-library",
    MODELLER: "modeller",
    FORUM: "forum",
    COMPILATION: "compilation",
    COLLECTION: "collection",
    AGGREGATE: "aggregate",
}
TEXT = {
    "maker": "the maker's own file",
    "maker-redistributed": "the maker's file as another party distributes it",
    "simulator-library": "a simulator's own library",
    "modeller": "a modeller's own file",
    "forum": "posted on a forum",
    "compilation": "a community compilation",
    "collection": "a collection of other people's files",
    "aggregate": "an aggregate of collections",
}

HOW_CLASS = {v: k for k, v in HOW.items()}

# the class of a source's files when no rule names the author of one of them
SOURCE_CLASS = {
    **dict.fromkeys(("onsemi", "nexperia", "nxp", "ti", "infineon", "vishay", "rohm", "toshiba", "diodes-inc",
                     "central-semi", "linear-systems", "interfet", "stmicro", "exicon", "microchip", "renesas",
                     "nisshinbo", "sanken", "onsemi-ic", "adi", "nichia", "thatcorp", "littelfuse", "aos",
                     "broadcom", "coilcraft", "kemet", "mps", "murata", "nichicon", "panasonic", "richtek",
                     "tdk", "torex", "wurth", "advanced-photonix"), VENDOR),
    **dict.fromkeys(("ltspice-native", "qspice", "microcap12"), SIMULATOR),
    **dict.fromkeys(("cordell", "reefman", "ayumi", "duncanamps", "koren", "suusi-tubes", "germaniumbjts",
                     "hagtech", "andyc", "viva-analog", "cohen-helie", "dempwolf", "tedyapo-led-modeling",
                     "z101-led-spice-model", "germanium-apm", "immler", "kurtblum", "electrucio", "tamivox",
                     "robrobinette", "electrucio-updates"), MODELLER),
    **dict.fromkeys(("diyaudio", "diyaudio-germanio", "diyaudio-tubos-valvulas", "diyaudio-chips",
                     "diyaudio-autores", "diystompboxes", "groups-io", "spiceypedals", "gist-chanmix51",
                     "freestompboxes", "electrosmash", "preamp-org", "audio-effects-ltspice",
                     "ltspice-guitar-pedals", "pnp-fuzz-simulation", "distorque-audio", "community-index",
                     "loosweb-relay"), FORUM),
    "groupsio-ltspice": COMPILATION,
    "spice-model-cd": COLLECTION, "ltwiki": COLLECTION, "bordodynov": COLLECTION, "bordodynov-qspice": COLLECTION,
    "kicad-spice-library": AGGREGATE,
}

B = frozenset({"bordodynov", "ltwiki", "kicad-spice-library"})   # Bordodynov's archives, wherever they were fetched from
K = frozenset({"kicad-spice-library"})
L = frozenset({"ltwiki"})
Q = frozenset({"bordodynov-qspice"})
CD = frozenset({"spice-model-cd"})
MC = frozenset({"microcap12"})

# (sources, pattern over the path below sources/<source>/ with a leading extracted/ dropped, who, class);
# the first rule that matches wins, so a named file comes before the folder that holds it
RULES: list[tuple[frozenset, str, str, int]] = [
    # --- files inside Bordodynov's lib.zip, cmp.zip and example.zip
    (B, r"/sub/Zener_DiodesInc\.", "diodes-inc", VENDOR_REDIST),
    (B, r"/sub/(texas|OpAmp_TI)\.", "ti", VENDOR_REDIST),
    (B, r"/sub/(OpAmp_AD|ADI1)\.", "adi", VENDOR_REDIST),
    (B, r"/sub/(OpAmp_NSC|ns_models|NSTimer)\.", "national", VENDOR_REDIST),
    (B, r"/sub/on_amp\.", "onsemi", VENDOR_REDIST),
    (B, r"/sub/transil_ST\.", "stmicro", VENDOR_REDIST),
    (B, r"/sub/OpAmp_BB\.", "burr-brown", VENDOR_REDIST),
    (B, r"/sub/(Koren_Tubes|Tubes_Koren|nk_triode|nk_pentode)\.", "koren", MODELLER),
    (B, r"/sub/(Triode|Pentode|Diode)_Ayumi\.", "ayumi", MODELLER),
    (B, r"/sub/Rydel_tubes\.", "rydel", MODELLER),
    (B, r"/sub/OpAmp_Nazar_Shtybel\.", "nazar-shtybel", MODELLER),
    (B, r"/cmp/Original/", "ltspice-native", SIMULATOR),       # LTspice's own standard.* as shipped
    (B, r"/cmp/Standard/", "ltspice-group", COMPILATION),      # the group's "standard library replacement"
    (B, r"examples/Cordell_Spice_Tutorial/", "cordell", MODELLER),
    (B, r"examples/LtSpicePlus/", "ltspiceplus", COLLECTION),
    (B, r"examples/Basso/", "basso", MODELLER),
    (B, r"examples/Robertugo/", "robertugo", MODELLER),
    (L, r"^(raw/bordodynov/|lib/lib/|cmp/cmp/|example/examples/)", "bordodynov", COLLECTION),
    (K, r"/Bordodynovs Electronics Lib/", "bordodynov", COLLECTION),
    # --- Bordodynov's QSPICE folder
    (Q, r"Cordell", "cordell", MODELLER),
    (Q, r"Cabirio", "cabirio", FORUM),
    (Q, r"_Ayumi\.", "ayumi", MODELLER),
    (Q, r"/QSPICE/(NPN|PNP|NJF|PJF|NMOS|PMOS|Diode|Schottky|Zener)\.txt$", "qspice", SIMULATOR),
    # --- what ltwiki hosts of its own
    (L, r"^raw/Spice-Models-collection/Zetex\.", "zetex", VENDOR_REDIST),
    (L, r"^raw/Spice-Models-collection/phil_fet\.", "philips", VENDOR_REDIST),
    (L, r"^raw/Spice-Models-collection/lin_tech\.", "linear-technology", VENDOR_REDIST),
    (L, r"^raw/Spice-Models-collection/siemens\.", "siemens", VENDOR_REDIST),
    (L, r"^raw/Spice-Models-collection/harris\.", "harris", VENDOR_REDIST),
    (L, r"^raw/Spice-Models-collection/", "spice-models-collection", COLLECTION),
    (L, r"^Standard/", "ltspice-group", COMPILATION),
    (L, r"^LargeCollection/", "largecollection", COLLECTION),
    (L, r"^raw/adventures_with_analog/", "adventures-with-analog", MODELLER),
    # --- KiCad-Spice-Library's maker folders
    (K, r"/Models/Manufacturer/General Semiconductor/", "general-semiconductor", VENDOR_REDIST),
    (K, r"/Models/Manufacturer/Zetex Semiconductors/", "zetex", VENDOR_REDIST),
    (K, r"/Models/Manufacturer/Infineon Technologies/", "infineon", VENDOR_REDIST),
    (K, r"/Models/Manufacturer/Texas Instruments/", "ti", VENDOR_REDIST),
    (K, r"/Models/Manufacturer/TRT-Electronics/", "trt-electronics", VENDOR_REDIST),
    # --- the Spice Model CD: OrCAD's 1990s vendor set, one folder per maker
    (CD, r"^raw/SiMetrix/", "simetrix", SIMULATOR),
    (CD, r"^raw/Philips/", "philips", VENDOR_REDIST),
    (CD, r"^raw/Infineon/", "infineon", VENDOR_REDIST),
    (CD, r"^raw/Analog Devices_Spice_Files/", "adi", VENDOR_REDIST),
    (CD, r"^raw/Siemens/", "siemens", VENDOR_REDIST),
    (CD, r"^raw/Fairchild/", "fairchild", VENDOR_REDIST),
    (CD, r"^raw/Zetex/", "zetex", VENDOR_REDIST),
    (CD, r"^raw/STMicroelectronics/", "stmicro", VENDOR_REDIST),
    (CD, r"^raw/General_Semi/", "general-semiconductor", VENDOR_REDIST),
    (CD, r"^raw/Motorola/", "motorola", VENDOR_REDIST),
    (CD, r"^raw/National_Semiconductors/", "national", VENDOR_REDIST),
    (CD, r"^raw/LinearTech/", "linear-technology", VENDOR_REDIST),
    # --- Micro-Cap's library names the maker in the file name
    (MC, r"/DiodesInc", "diodes-inc", VENDOR_REDIST),
    (MC, r"/(On_Semi|on_diode)\.", "onsemi", VENDOR_REDIST),
    (MC, r"/nxp\.", "nxp", VENDOR_REDIST),
    (MC, r"/ti\.", "ti", VENDOR_REDIST),
    (MC, r"/zetex\.", "zetex", VENDOR_REDIST),
    (MC, r"/infineon\.", "infineon", VENDOR_REDIST),
    (MC, r"/vishaydiode\.", "vishay", VENDOR_REDIST),
    (MC, r"/linearsystems\.", "linear-systems", VENDOR_REDIST),
    (MC, r"/(irf|irpmos_lbr)\.", "international-rectifier", VENDOR_REDIST),
    (MC, r"/apex\.", "apex", VENDOR_REDIST),
    (MC, r"/Littelfuse", "littelfuse", VENDOR_REDIST),
    (MC, r"/ph_(shot|diode|bjt)\.", "philips", VENDOR_REDIST),
    (MC, r"/cs\.lib$", "central-semi", VENDOR_REDIST),
    (MC, r"/microsem_lbr\.", "microsemi", VENDOR_REDIST),
    (MC, r"/Koren\.", "koren", MODELLER),
    # --- forums and personal sites: the author when the file name keeps it
    (frozenset({"diyaudio"}), r"Cabirio", "cabirio", FORUM),
    (frozenset({"diyaudio"}), r"_ayumi\.", "ayumi", MODELLER),
    (frozenset({"diyaudio"}), r"_koren\.", "koren", MODELLER),
    (frozenset({"diyaudio"}), r"_immler\.", "immler", MODELLER),
    (frozenset({"diyaudio"}), r"_koonw\.", "koonw", FORUM),
    (frozenset({"diyaudio"}), r"Mooly", "mooly", FORUM),
    (frozenset({"diystompboxes"}), r"gert_willmann", "gert-willmann", FORUM),
    (frozenset({"groupsio-ltspice"}), r"hiromasa", "hiromasa", FORUM),
    (frozenset({"groupsio-ltspice"}), r".", "ltspice-group", COMPILATION),
    (frozenset({"robrobinette", "suusi-tubes"}), r"Koren_Tubes\.", "koren", MODELLER),
]
COMPILED = [(srcs, re.compile(rx, re.I), who, cls) for srcs, rx, who, cls in RULES]

# where a source only mirrors another party's archive: the party's own site is where a reader is sent,
# the mirror is listed among the copies
MIRRORS = [
    (L, r"^(raw/bordodynov/|lib/lib/|cmp/cmp/|example/examples/)"),   # Bordodynov's archives, as ltwiki hosts them
    (L, r"^Standard/"),                                              # the LTspice group's Standard.zip
    (K, r"/Bordodynovs Electronics Lib/"),
]
MIRRORED = [(srcs, re.compile(rx, re.I)) for srcs, rx in MIRRORS]


def registered(source: str) -> str:
    """The registry id of a source: the indexer names a folder with a manifest of its own after both."""
    return source.split("/")[0]


def below(source: str, file: str) -> str:
    """The file's path below its source's folder, with the indexer's extracted/ prefix dropped."""
    src = registered(source)
    rel = file[len(f"sources/{src}/"):] if file.startswith(f"sources/{src}/") else file
    return rel[len("extracted/"):] if rel.startswith("extracted/") else rel


def origin(source: str, file: str = "") -> dict:
    """Who probably wrote the model in this file, and how far from them the file is."""
    src = registered(source)
    rel = below(source, file)
    mirror = any(src in srcs and rx.search(rel) for srcs, rx in MIRRORED)
    for srcs, rx, who, cls in COMPILED:
        if src in srcs and rx.search(rel):
            return {"who": who, "cls": cls, "how": HOW[cls], "mirror": mirror}
    cls = SOURCE_CLASS.get(src, COLLECTION)
    return {"who": src, "cls": cls, "how": HOW[cls], "mirror": mirror}
