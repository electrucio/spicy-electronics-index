"""Characterise every model of a job list in whichever simulator this image is: every deck of the kind's
plan, packed where the deck allows it, with the measurements of data/bench/measurements.yaml.

    python3 /sim/bench/character.py --jobs /io/jobs.jsonl --catalogue /io/catalogue.json --out /io/run
                                    [--shard i/n] [--pack 10]

JOB (one per line): {"id": <hash>, "kind": "bjt", "family": "gummel-poon", "polarity": "npn"|"pnp",
                     "card": ".model DUT ...", "model": "DUT", "measurements": null | [ids], "class": null}
CATALOGUE: {"version": "m-1", "measurements": {id: entry}} — the YAML rendered to JSON by the caller,
because the image has the standard library alone.

RESULT (one per model): {"id", "engine", "version", "catalogue", "values": {id: {key: value}},
    "codes": {id: ok|absent|n/a|failed|suspect}, "errors": {id: text}, "derived": {...},
    "curves": {id: {name: points}}, "decks": {deck: {"ids", "analysis", "pack", "digest", "wall_s",
    "cpu_s", "returncode"}}, "error": null}

`digest` is the sha256 of the deck as it would be written for this model alone (`model.lib`, the card
named DUT): what `sei bench deck` regenerates and a reader compares. A packed deck is the same circuit
with the copies renamed; the pilot checks the two agree. Several workers share one job list through a
claims directory, as batch.py does; waveforms are deleted once measured.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bench import decks_bjt, decks_jfet, engines, raw  # noqa: E402
from bench.num import n  # noqa: E402

ENGINE = engines.engine_name()
PLANS = {"bjt": decks_bjt, "jfet": decks_jfet}
POLARITY_SIGN = {"npn": 1, "pnp": -1, "n": 1, "p": -1}
# the terminals a deck's device line names, by its first letter, in the order the line writes them
TERMINALS = {"Q": "cbe", "J": "dgs", "M": "dgs", "X": ("inp", "inn", "vp", "vn", "out")}
CARD_NAME = re.compile(r"^(\s*\.model\s+)(\S+)", re.I | re.M)
SUBCKT_DUT = re.compile(r"^\s*\.subckt\s+DUT\s", re.I | re.M)
DUT_WORD = re.compile(r"(?<![\w$#.\-+])DUT(?![\w$#.\-+])")
DUT_SUFFIX = re.compile(r"_DUT(?![\w$#.\-+])")
TIMEOUT = (60, 10)   # seconds per deck, plus per model in it
# A waveform the bench does not read: a deck writes 1 or 2 MB, and a model that drives the simulator to
# picosecond steps through a 100 µs pulse writes hundreds (a 571 MB file once), which take minutes and
# gigabytes to parse. Such a deck is a failure of that model at that condition, with its size said.
RAW_LIMIT = 50e6
PLOT_KEYS = {"dc": ("dc",), "ac": ("ac",), "tran": ("tran",), "noise": ("spectral", "noise"), "op": ("op",)}


def as_device(lines, m, pins):
    """A deck's device lines for a subcircuit: each `Q<name> c b e <m>` (or `J d g s`, `M d g s`, an op-amp's
    `X inp inn vp vn out`) becomes `X<name>` with the nodes in the subcircuit's own pin order (`pins`: a role per
    pin, or nc, from bench.jobs on the host). A pin no terminal reaches gets a node of its own, held at ground
    through 1 GΩ so that no node floats; a second pin on one terminal (a tab on the collector) shares that
    terminal's node. A `.model` MOSFET card's lines get the bulk tied to the source (`pins` of d, g, s, b);
    every other card's lines pass as they are."""
    if not pins:
        return lines
    out = []
    for line in lines:
        t = line.split()
        kind = t[0][:1].upper() if t else ""
        roles = TERMINALS.get(kind)
        if roles and len(t) == len(roles) + 2 and t[-1] == m:
            node = dict(zip(roles, t[1:-1]))
            if kind == "M" and pins == ["d", "g", "s", "b"]:
                out.append(" ".join([t[0], node["d"], node["g"], node["s"], node["s"], m]))
                continue
            nodes, extra = [], []
            for i, role in enumerate(pins):
                if role in node:
                    nodes.append(node[role])
                else:
                    nodes.append(f"nc{i}{t[0]}")
                    extra.append(f"RNC{i}{t[0]} nc{i}{t[0]} 0 1e9")
            out += [" ".join(["X" + t[0][1:] if kind != "X" else t[0], *nodes, m])] + extra
        else:
            out.append(line)
    return out


def deck_text(deck, copies, lib, engine=None):
    """The netlist of a deck for the given copies: (model name, sign, node suffix, derived) each, and for a
    subcircuit its pin roles fifth."""
    head = [f"* character {deck.name}", f'.include "{lib}"', engines.header(engine or ENGINE), ".options reltol=1e-4",
            f".temp {n(deck.temp)}"]
    body, saves = [], []
    for cp in copies:
        m, s, sfx, derived = cp[:4]
        body += as_device(deck.body(m, s, sfx, derived), m, cp[4] if len(cp) > 4 else None)
        sv = deck.saves(sfx)
        if sv:
            saves.append(".save " + " ".join(sv))
    lines = head + body + saves + deck.tail(copies[0][1]) + [".end"]
    return "\n".join(line for line in lines if line) + "\n"


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def error_class(cost):
    if cost.get("timed_out"):
        return "timeout"
    try:
        log = Path(cost["log"]).read_text(errors="replace").lower()
    except OSError:
        return "unknown"
    if any(w in log for w in ("syntax", "unknown parameter", "unrecognized", "could not find", "undefined", "not found")):
        return "syntax"
    if any(w in log for w in ("singular", "convergence", "timestep too small", "gmin", "failed to converge")):
        return "convergence"
    return "unknown"


def pick_plot(plots, analysis):
    for p in plots:
        if any(k in p["name"].lower() for k in PLOT_KEYS.get(analysis, ())):
            return p
    return plots[0]


class Model:
    def __init__(self, job, k):
        self.job = job
        self.k = k
        self.s = POLARITY_SIGN[job["polarity"]]
        self.values, self.curves, self.codes, self.errors, self.derived, self.decks = {}, {}, {}, {}, {}, {}

    def merge(self, values, curves, codes, derived):
        for mid, v in values.items():
            self.values.setdefault(mid, {}).update(v)
        for mid, c in curves.items():
            self.curves.setdefault(mid, {}).update(c)
        for mid, c in codes.items():
            if c == "ok" or mid not in self.codes:
                self.codes[mid] = c
        # derived values enter later decks' text, and are published at four significant figures: the
        # decks must see the same rounded numbers, so that a reader regenerates the same text
        self.derived.update({k: (float(f"{v:.4g}") if isinstance(v, float) else v) for k, v in derived.items()})

    def fail(self, deck, why):
        for mid in deck.ids:
            if mid not in self.values or not self.values[mid]:
                self.codes[mid] = "failed"
            self.errors[mid] = (self.errors.get(mid, "") + f"{deck.name}: {why}; ")[:300]

    def result(self, version, catalogue):
        derived = {k: v for k, v in self.derived.items() if not k.startswith("_")}
        for mid, vals in self.values.items():
            code = vals.pop("_code", None)
            if code and (mid not in self.codes or self.codes[mid] != "failed"):
                self.codes[mid] = code
        return {"id": self.job["id"], "engine": ENGINE, "version": version, "catalogue": catalogue,
                "values": self.values, "codes": self.codes, "errors": self.errors, "derived": derived,
                "curves": self.curves, "decks": self.decks, "error": None}


def rename(card, name):
    """A card's copy for a packed deck: `.model DUT` renamed; a subcircuit's DUT, and every `<inner>_DUT` the
    host suffixed inside it, renamed after the copy."""
    if SUBCKT_DUT.search(card):
        return DUT_SUFFIX.sub("_" + name, DUT_WORD.sub(name, card))
    return CARD_NAME.sub(lambda m: m.group(1) + name, card, count=1)


def run_deck(deck, models, workdir, lib_name, tag, runs_out):
    """One netlist for these models (one copy each); returns the plot data per model, or None when it
    did not run, and records the cost per model."""
    packed = len(models) > 1
    copies = [(f"DUT{mo.k}" if packed else "DUT", mo.s, f"_{mo.k}" if packed else "", mo.derived, mo.job.get("pins")) for mo in models]
    text = deck_text(deck, copies, lib_name)
    net = workdir / f"{tag}.cir"
    net.write_text(text)
    cost = engines.run(net, ENGINE, timeout=TIMEOUT[0] + TIMEOUT[1] * len(models))
    cost.update({"deck": deck.name, "models": [mo.job["id"] for mo in models]})
    runs_out.write(json.dumps(cost) + "\n")
    runs_out.flush()
    share = {"wall_s": round(cost["wall_s"] / len(models), 4),
             "cpu_s": round((cost["cpu_user_s"] + cost["cpu_sys_s"]) / len(models), 4), "returncode": cost["returncode"]}
    for mo in models:
        single = deck_text(deck, [("DUT", mo.s, "", mo.derived, mo.job.get("pins"))], "model.lib")
        mo.decks[deck.name] = {"ids": list(deck.ids), "analysis": deck.analysis, "pack": len(models),
                               "digest": digest(single), **share}
    plot = None
    size = Path(cost["raw"]).stat().st_size if cost["raw"] and Path(cost["raw"]).exists() else 0
    if size > RAW_LIMIT:
        cost["error"] = f"a waveform of {size / 1e6:.0f} MB, beyond the {RAW_LIMIT / 1e6:.0f} MB the bench reads"
        Path(cost["raw"]).unlink(missing_ok=True)
    elif cost["raw"]:
        try:
            plot = pick_plot(raw.read(cost["raw"]), deck.analysis)
            if not any(len(v) for v in plot["data"].values()):
                plot, cost["error"] = None, "empty waveform"       # the sweep stopped before its first point
        except Exception as exc:  # noqa: BLE001
            cost["error"] = f"read: {exc}"
        Path(cost["raw"]).unlink(missing_ok=True)
    # whatever the simulator left of this netlist goes too, read or not: a transient that timed out can have
    # written gigabytes into the work directory, which lives in the container's memory
    for left in workdir.glob(f"{net.stem}.*"):
        if left.suffix in (".raw", ".qraw", ".log", ".out") or left.name.endswith(".op.raw"):
            left.unlink(missing_ok=True)
    if plot is None:
        return None, error_class(cost) if not cost.get("error") else cost["error"]
    return plot, None


def measure_all(deck, models, plot, copies_sfx):
    """Measure each copy; the models whose copy could not be read come back, to be run alone."""
    unread = []
    for mo, sfx in zip(models, copies_sfx):
        try:
            mo.derived["_plot_name"] = plot["name"]
            values, curves, codes, derived = deck.measure(plot["data"], mo.s, sfx, mo.derived)
            mo.merge(values, curves, codes, derived)
        except Exception as exc:  # noqa: BLE001
            if len(models) > 1:
                unread.append(mo)
            else:
                mo.fail(deck, f"{type(exc).__name__}: {exc}")
    return unread


def characterise(pack, cat, work, runs_out):
    """Every deck of the plan over one pack of models of one kind and polarity."""
    kind = pack[0].job["kind"]
    work.mkdir(parents=True, exist_ok=True)
    lib = work / "models.lib"
    lib.write_text("\n".join(rename(mo.job["card"], f"DUT{mo.k}") for mo in pack) + "\n")
    for mo in pack:
        d = work / f"m{mo.k}"
        d.mkdir(exist_ok=True)
        (d / "model.lib").write_text(mo.job["card"] + "\n")
    for deck in PLANS[kind].plan(cat, ENGINE):
        ready = [mo for mo in pack if deck.ready(mo.derived)]
        for mo in pack:
            if mo not in ready:
                for mid in deck.ids:
                    if mid not in mo.values:
                        mo.codes.setdefault(mid, "n/a")
        if not ready:
            continue
        if deck.pack and len(ready) > 1:
            # a deck with many copies per model packs fewer models (`pack_limit`): 850 transistors in one
            # LTspice deck outgrow the container's memory
            limit = getattr(deck, "pack_limit", 0) or len(ready)
            left = []
            for i in range(0, len(ready), limit):
                group = ready[i:i + limit]
                if len(group) == 1:
                    left += group
                    continue
                plot, why = run_deck(deck, group, work, "models.lib", deck.name, runs_out)
                left += measure_all(deck, group, plot, [f"_{mo.k}" for mo in group]) if plot is not None else group
            ready = left
            # the pack failed, or a copy in it could not be read: those models alone, so that the card
            # at fault pays and the others do not
        for mo in ready:
            d = work / f"m{mo.k}"
            plot, why = run_deck(deck, [mo], d, "model.lib", deck.name, runs_out)
            if plot is None:
                mo.fail(deck, why)
            else:
                measure_all(deck, [mo], plot, [""])
    for mo in pack:
        try:
            PLANS[kind].finalize(cat, mo.values, mo.curves, mo.derived)
        except Exception as exc:  # noqa: BLE001
            mo.errors["finalize"] = f"{type(exc).__name__}: {exc}"[:200]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--jobs", required=True)
    ap.add_argument("--catalogue", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--pack", type=int, default=10)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--work", default="/tmp/character", help="the scratch directory (the image's tmpfs; a host run names its own)")
    a = ap.parse_args(argv)
    cat_doc = json.loads(Path(a.catalogue).read_text())
    cat = cat_doc["measurements"]
    jobs = [json.loads(line) for line in Path(a.jobs).read_text().splitlines() if line.strip()]
    if a.limit:
        jobs = jobs[:a.limit]
    # packs are homogeneous in kind and polarity: a shared swept source has one sign
    groups = {}
    for j in jobs:
        groups.setdefault((j["kind"], j["polarity"]), []).append(j)
    packs = []
    for key in sorted(groups):
        g = groups[key]
        packs += [g[i:i + a.pack] for i in range(0, len(g), a.pack)]
    i = int(a.shard.split("/")[0])
    out = Path(a.out)
    claims = out / "claims"
    claims.mkdir(parents=True, exist_ok=True)
    work = Path(a.work)
    version = engines.version()
    t0 = time.perf_counter()
    cg0 = engines._cgroup_cpu_s()
    done = failed = mine = 0
    with open(out / f"results-{i}.jsonl", "w") as res_out, open(out / f"runs-{i}.jsonl", "w") as runs_out:
        for pi, pack_jobs in enumerate(packs):
            try:
                os.close(os.open(claims / str(pi), os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            except FileExistsError:
                continue
            mine += 1
            if pack_jobs[0]["kind"] not in PLANS:
                for j in pack_jobs:
                    res_out.write(json.dumps({"id": j["id"], "engine": ENGINE, "error": f"no plan for {j['kind']}"}) + "\n")
                    failed += 1
                continue
            pack = [Model(j, k) for k, j in enumerate(pack_jobs)]
            try:
                characterise(pack, cat, work / f"p{pi}", runs_out)
            except Exception as exc:  # noqa: BLE001
                for mo in pack:
                    res_out.write(json.dumps({"id": mo.job["id"], "engine": ENGINE, "error": f"{type(exc).__name__}: {exc}"[:300]}) + "\n")
                    failed += 1
                continue
            for mo in pack:
                r = mo.result(version, cat_doc["version"])
                res_out.write(json.dumps(r) + "\n")
                done += 1
            res_out.flush()
    summary = {"engine": ENGINE, "shard": a.shard, "pack": a.pack, "packs": mine, "models": done + failed, "ok": done,
               "failed": failed, "wall_s": round(time.perf_counter() - t0, 3),
               "container_cpu_s": round((engines._cgroup_cpu_s() or 0) - (cg0 or 0), 3),
               "container_mem_peak_mb": engines._cgroup_mem_peak_mb()}
    (out / f"worker-{i}.json").write_text(json.dumps(summary))
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
