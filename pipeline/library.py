"""The script library: ready-to-produce scripts in library/scripts/<script_id>.json.

A script is used once; a run manifest records its script_id. The picker spreads a day's
videos across the best-scoring niches and varies structure within a niche.
"""

import json

from .config import ROOT

LIBRARY_DIR = ROOT / "library" / "scripts"

STRUCTURES = ("comparison", "myth-vs-fact", "mistake", "how-it-works", "story", "countdown")


def load_scripts(library_dir=LIBRARY_DIR):
    scripts = []
    for path in sorted(library_dir.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            script = json.load(f)
        if script.get("id") != path.stem:
            raise ValueError(f"{path.name}: 'id' must equal the file name")
        scripts.append(script)
    return scripts


def used_ids(manifests):
    return {m["script_id"] for m in manifests if m.get("script_id")}


def pick(scripts, scored_niches, manifests, count, max_per_niche=1):
    """Choose up to `count` unused scripts, best niche first.

    Takes at most `max_per_niche` from one niche per pass, so a day's batch covers several
    niches; later passes fill remaining slots if the library runs thin. Within a niche it
    prefers a structure that niche has not used recently.
    """
    used = used_ids(manifests)
    unused = [s for s in scripts if s["id"] not in used]
    recent_structures = {}
    for m in sorted(manifests, key=lambda m: m["created_at"]):
        if m.get("structure"):
            recent_structures[m["niche_id"]] = m["structure"]

    chosen = []
    while len(chosen) < count:
        added = False
        for niche in scored_niches:
            pool = [s for s in unused if s["niche_id"] == niche["id"] and s not in chosen]
            taken = sum(1 for s in chosen if s["niche_id"] == niche["id"])
            if not pool or taken >= max_per_niche:
                continue
            last = recent_structures.get(niche["id"])
            pool.sort(key=lambda s: (s.get("structure") == last, s["id"]))
            chosen.append(pool[0])
            recent_structures[niche["id"]] = pool[0].get("structure")
            added = True
            if len(chosen) == count:
                break
        if not added:
            if max_per_niche >= count:
                break
            max_per_niche += 1
    return chosen


def stock(scripts, manifests):
    """Unused scripts per niche, so the autopilot knows when to write more."""
    used = used_ids(manifests)
    counts = {}
    for s in scripts:
        if s["id"] not in used:
            counts[s["niche_id"]] = counts.get(s["niche_id"], 0) + 1
    return counts
