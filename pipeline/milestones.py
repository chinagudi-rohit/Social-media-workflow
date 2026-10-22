"""Monetization ladder (config/monetization.yaml): which steps a platform has reached.

`check` returns the steps reached by the latest stats that were not announced before, in
ladder order, and the next step per platform, so the daily report can tell the owner what
to switch on and what is coming.
"""

import json

from .config import ROOT

STATE = ROOT / "data" / "milestones.json"


def key(platform, step):
    return f"{platform}:{step['metric']}:{step['at']}:{step['do'][:24]}"


def check(ladder, stats, announced=()):
    """stats: {platform: {"followers": n, "views_90d": n}}; missing stats count as 0."""
    announced, new, upcoming = set(announced), [], {}
    for platform, steps in ladder.items():
        have = stats.get(platform) or {}
        for step in sorted(steps, key=lambda s: (s["metric"] != "followers", s["at"])):
            value = have.get(step["metric"]) or 0
            if value >= step["at"]:
                if key(platform, step) not in announced:
                    new.append({"platform": platform, **step, "value": value})
            elif platform not in upcoming:
                upcoming[platform] = {**step, "value": value, "to_go": step["at"] - value}
    return new, upcoming


def load_announced(path=STATE):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def save_announced(keys, path=STATE):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(set(keys)), indent=1) + "\n", encoding="utf-8")
