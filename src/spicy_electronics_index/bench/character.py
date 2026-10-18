"""Characterise every recipe transistor model: the catalogue's measurements at universal conditions, in
one pinned simulator image, for every distinct card the recipes list.

    sei bench character [--engine qspice] [--kind bjt] [--part 2N3904 ...] [--workers 40] [--pack 10]
                         [--limit N] [--force]

A job is one distinct model (one code hash, however many parts list it) whose card the plan of its kind
reads today: a plain Gummel-Poon `.model` for bipolars. The card is prepared as the rows bench prepares
it (`bench.jobs`), and the jobs go, with the catalogue rendered to JSON, into a run folder under
`config.character_runs(<engine>)/<date>/`; N containers of the engine's image share the job list
through a claims directory (docker/sim/bench/character.py) and write `results-<i>.jsonl`. The folder
is private, because the jobs carry the cards; `sei bench character-publish` publishes everything
else, per model hash, and stamps the ledger that this command reads to skip what is done.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

from spicy_electronics_index.bench import catalogue, record
from spicy_electronics_index.bench.jobs import card_for, polarity_of, subckt_for
from spicy_electronics_index.core.config import (
    REPO_ROOT,
    character_runs,
    character_state,
    require,
    sim_bench,
    spice_models_root,
    spice_recipe_locations,
)
from spicy_electronics_index.core.ledger import (
    CHARACTER_FIELDS,
    CHARACTER_STAGES,
    CHARACTER_VERSIONED,
    Ledger,
)
from spicy_electronics_index.models import behaviours
from spicy_electronics_index.models import found as F
from spicy_electronics_index.models.cards import card_params, family

VERSION = "character-1"
PRIMARY = "qspice"
ENGINES = ("qspice", "ngspice", "ltspice")
# kind → the card families the image's plan handles today (docker/sim/bench/decks_<kind>.py); an op-amp is always
# a subcircuit, measured through its five pins
PLANNED = {"bjt": ("gummel-poon",), "jfet": ("jfet",), "mosfet": ("vdmos", "mos-level-1", "mos-level-2", "mos-level-3"),
           "amplifier": ()}
# the recipe kinds of a group the bench runs: a comparator or an OTA shares the amplifier group and is not an op-amp
PLANNED_KINDS = {"amplifier": ("opamp",)}
WORKERS = {"qspice": 40, "ngspice": 40, "ltspice": 20}
CPUS = {"qspice": 1, "ngspice": 1, "ltspice": 2}
IN_IMAGE = ("python3", "/sim/bench/character.py", "--jobs", "/io/jobs.jsonl", "--catalogue", "/io/catalogue.json", "--out", "/io")


def image_id(engine: str) -> str:
    out = subprocess.run(["docker", "image", "inspect", f"spicy-electronics-index-{engine}", "--format", "{{.Id}}"],
                         capture_output=True, text=True)
    return out.stdout.strip()


def revision(path: Path) -> dict:
    """The commit the bench code was last changed in, and whether the working copy differs from it."""
    rel = str(path.relative_to(REPO_ROOT))
    commit = subprocess.run(["git", "log", "-1", "--format=%H", "--", rel], cwd=REPO_ROOT,
                            capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", rel], cwd=REPO_ROOT,
                           capture_output=True, text=True).stdout.strip()
    return {"commit": commit, "clean": not dirty}


def ledger() -> Ledger:
    return Ledger(character_state(), stages=CHARACTER_STAGES, fields=CHARACTER_FIELDS, versioned=CHARACTER_VERSIONED)


def input_digest() -> str:
    """What a result depends on besides the card: the catalogue's conditions. (The hash is the card.)"""
    return record.digest([catalogue.bench_digest(), catalogue.version()])


def fresh_for(led: Ledger, model_hash: str, engine: str, dig: str) -> bool:
    row = led.get(model_hash)
    return bool(row) and led.fresh(model_hash, "character", VERSION, dig) and engine in (row.get("engines") or "").split(",")


def catalogue_json() -> dict:
    doc = catalogue.load()
    return {"version": doc["version"], "measurements": {m["id"]: m for m in doc["measurements"]}}


def build_jobs(engine: str, kinds: tuple[str, ...] | None = None, parts: set[str] | None = None, force: bool = False,
               limit: int = 0, hashes: tuple[str, ...] | None = None) -> tuple[list[dict], Counter]:
    """One job per distinct recipe model the plan reads, with every part that lists it."""
    locations = json.loads(require(spice_recipe_locations(), "the recipes' models").read_text(encoding="utf-8"))
    files = F.Files(spice_models_root())
    led = ledger()
    dig = input_digest()
    c: Counter = Counter()
    jobs: dict[str, dict] = {}
    for key, models in sorted(locations.items()):
        kind, part = key.split("/", 1)
        grp = behaviours.group(kind)
        if grp not in PLANNED or (kinds and grp not in kinds) or (parts and part not in parts) \
                or (grp in PLANNED_KINDS and kind not in PLANNED_KINDS[grp]):
            continue
        cards = record.load(kind, part).get("cards", {})
        for m in models:
            h = m["hash"]
            if not h or not m["file"].startswith("sources/") or (hashes and not h.startswith(hashes)):
                continue
            if h in jobs:
                jobs[h]["parts"].append(key)
                continue
            info = cards.get(h, {})
            fam = info.get("family") or ("subckt" if grp == "amplifier" else None)   # `models cards` reads transistors only
            # an AKO card is measured written out in full (`jobs.resolve_ako`), when it is a kind of a planned card;
            # a subcircuit through its pins (`jobs.subckt_card`), when they can be told for sure
            if fam not in PLANNED[grp] and fam not in ("ako", "subckt"):
                c[f"skipped: {fam or 'no card record'}"] += 1
                continue
            if fam == "subckt":
                if not force and fresh_for(led, h, engine, dig):
                    c["fresh"] += 1
                    continue
                sub, why = subckt_for(files, m["file"], m["name"], engine, grp)
                if not sub:
                    c[f"skipped: subckt, {why}"] += 1
                    continue
                jobs[h] = {"id": h, "kind": grp, "family": "subckt", "polarity": sub["polarity"], "card": sub["card"],
                           "model": "DUT", "changes": sub["changes"], "pins": sub["pins"], "measurements": None,
                           "class": None, "parts": [key]}
                c["jobs"] += 1
                if limit and len(jobs) >= limit:
                    return list(jobs.values()), c
                continue
            if not force and fresh_for(led, h, engine, dig):
                c["fresh"] += 1
                continue
            got = card_for(files, m["file"], m["name"], engine)
            if not got:
                c["skipped: ako without its base" if fam == "ako" else "skipped: card not found"] += 1
                continue
            card, changes = got
            if fam == "ako":
                parsed = card_params(card)
                resolved = family(*parsed[::2]) if parsed else None
                if resolved not in PLANNED[grp]:
                    c[f"skipped: ako of {resolved}"] += 1
                    continue
            pol = polarity_of(info["type"], card)
            if not pol:
                c[f"skipped: polarity of {info['type']}"] += 1
                continue
            # a `.model` MOSFET of the integrated levels has four terminals; the decks write three and the image ties the bulk to the source
            pins = ["d", "g", "s", "b"] if info["family"].startswith("mos-level") else None
            jobs[h] = {"id": h, "kind": grp, "family": info["family"], "polarity": pol, "card": card,
                       "model": "DUT", "changes": changes, "measurements": None, "class": None, "parts": [key], **({"pins": pins} if pins else {})}
            c["jobs"] += 1
            if limit and len(jobs) >= limit:
                return list(jobs.values()), c
    return list(jobs.values()), c


def new_run_dir(engine: str) -> Path:
    base = character_runs(engine)
    for k in range(1, 100):
        d = base / (date.today().isoformat() + (f"-{k}" if k > 1 else ""))
        if not d.exists():
            d.mkdir(parents=True)
            return d
    raise RuntimeError("a hundred runs in one day")


def launch_here(engine: str, run_dir: Path, workers: int, pack: int) -> None:
    """The same jobs run on this machine, the bench's own script in-process (ngspice on the PATH): for a machine
    without Docker, or to try a deck. The record says so in its `image`."""
    env = {**os.environ, "SIM_ENGINE": engine, "SIM_NO_DISPLAY": "1"}
    work = run_dir / "work"
    procs = [subprocess.Popen([sys.executable, str(sim_bench() / "character.py"), "--jobs", str(run_dir / "jobs.jsonl"),
                               "--catalogue", str(run_dir / "catalogue.json"), "--out", str(run_dir), "--shard", f"{i}/{workers}",
                               "--pack", str(pack), "--work", str(work / f"w{i}")], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
             for i in range(workers)]
    for i, pr in enumerate(procs):
        out, _ = pr.communicate()
        (run_dir / f"worker-{i}.log").write_text(out or "", encoding="utf-8")
    shutil.rmtree(work, ignore_errors=True)


def host_engine(engine: str) -> str:
    """What runs the decks on this machine, for the record: the engine's own version string."""
    exe = {"ngspice": ["ngspice", "-v"]}.get(engine)
    if not exe or not shutil.which(exe[0]):
        return f"host:{engine}:not found"
    out = subprocess.run(exe, capture_output=True, text=True).stdout
    line = next((ln.strip("* \t") for ln in out.splitlines() if engine in ln.lower() and any(ch.isdigit() for ch in ln)), engine)
    return f"host:{line.strip()}"


def launch(engine: str, run_dir: Path, workers: int, pack: int, cpus: float) -> None:
    names = [f"character-{engine}-{i}" for i in range(workers)]
    for i, name in enumerate(names):
        # a run that was killed leaves its containers behind under these names; they would block this one
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, text=True)
        cmd = ["docker", "run", "-d", "--name", name, "--cpus", str(cpus), "--memory", "4g", "--tmpfs", "/tmp/character",
               "-v", f"{sim_bench()}:/sim/bench:ro", "-v", f"{run_dir}:/io", f"spicy-electronics-index-{engine}",
               *IN_IMAGE, "--shard", f"{i}/{workers}", "--pack", str(pack)]
        subprocess.run(cmd, check=True, capture_output=True, text=True)

    def finish(name: str) -> None:
        subprocess.run(["docker", "wait", name], capture_output=True, text=True)
        log = subprocess.run(["docker", "logs", name], capture_output=True, text=True)
        (run_dir / f"{name.rsplit('-', 1)[-1].join(['worker-', '.log'])}").write_text(log.stdout + log.stderr, encoding="utf-8")
        subprocess.run(["docker", "rm", name], capture_output=True, text=True)

    with ThreadPoolExecutor(max(1, workers)) as ex:
        list(ex.map(finish, names))


def run(engine: str, kinds: tuple[str, ...] | None, parts: set[str] | None, workers: int | None, pack: int,
        force: bool, limit: int, hashes: tuple[str, ...] | None = None, here: bool = False) -> dict:
    jobs, c = build_jobs(engine, kinds, parts, force, limit, hashes)
    workers = workers or WORKERS[engine]
    workers = max(1, min(workers, (len(jobs) + pack - 1) // pack or 1))
    run_dir = new_run_dir(engine)
    (run_dir / "jobs.jsonl").write_text("".join(json.dumps(j) + "\n" for j in jobs), encoding="utf-8")
    (run_dir / "catalogue.json").write_text(json.dumps(catalogue_json()), encoding="utf-8")
    t0 = time.perf_counter()
    if jobs and here:
        launch_here(engine, run_dir, workers, pack)
    elif jobs:
        launch(engine, run_dir, workers, pack, CPUS[engine])
    summaries = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(run_dir.glob("worker-*.json"))]
    results = sum(1 for p in run_dir.glob("results-*.jsonl") for _ in p.read_text(encoding="utf-8").splitlines())
    info = {"engine": engine, "version": VERSION, "on": date.today().isoformat(), "image": host_engine(engine) if here else image_id(engine),
            "bench": revision(sim_bench()), "catalogue": {"version": catalogue.version(), "sha256": catalogue.digest()},
            "workers": workers, "pack": pack, "cpus": CPUS[engine], "jobs": len(jobs), "results": results,
            "ok": sum(s["ok"] for s in summaries), "failed": sum(s["failed"] for s in summaries),
            "wall_s": round(time.perf_counter() - t0, 1), "worker_cpu_s": round(sum(s["container_cpu_s"] for s in summaries), 1),
            "skipped": dict(c),
            "command": (f"docker run --rm --cpus {CPUS[engine]} --tmpfs /tmp/character -v docker/sim/bench:/sim/bench:ro "
                        f"-v <run>:/io spicy-electronics-index-{engine} " + " ".join(IN_IMAGE) + f" --pack {pack}")}
    (run_dir / "run.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    return info


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--engine", default=PRIMARY, choices=ENGINES)
    ap.add_argument("--kind", action="append", help="only this kind (repeatable)")
    ap.add_argument("--part", action="append", help="only models of this part (repeatable)")
    ap.add_argument("--workers", type=int)
    ap.add_argument("--pack", type=int, default=10)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true", help="run models already published at this version too")
    ap.add_argument("--hash", action="append", help="only the model whose hash starts so (repeatable)")
    ap.add_argument("--here", action="store_true", help="run on this machine with the engine on the PATH, not in its image")
    a = ap.parse_args(argv)
    info = run(a.engine, tuple(a.kind) if a.kind else None, set(a.part) if a.part else None, a.workers, a.pack,
               a.force, a.limit, tuple(a.hash) if a.hash else None, here=a.here)
    print(f"{info['ok']:,} of {info['jobs']:,} models characterised with {a.engine} in {info['wall_s']} s "
          f"({info['workers']} workers; image {info['image'][:19]}, bench {info['bench']['commit'][:10]}"
          f"{'' if info['bench']['clean'] else ' + uncommitted changes'}); skipped {info['skipped']}")
    return 0 if info["failed"] == 0 and info["results"] == info["jobs"] else 1


if __name__ == "__main__":
    sys.exit(main())
