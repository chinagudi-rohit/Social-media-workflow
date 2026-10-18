"""Reach experiments: many varied videos in a short window, measured often.

config/experiment.yaml names the test, its window, its credit cap and the variables under
test. Each video gets one value per variable (its `arms`), assigned so that every value
appears about equally often and pairs of values keep changing. Stats come from Metricool's
per-video connectors (YouTube "videos published in range", Instagram and Facebook "reels").
Each pull is kept as a snapshot under data/experiments/<id>/snapshots/ and merged into the
run's posts, so `insights` and the post-time learning see it too.

Two days of a dozen videos give a direction, not proof: Shorts views are noisy. The report
says how many videos each value rests on.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

from .config import ROOT
from .insights import lift

EXP_DIR = ROOT / "data" / "experiments"

# Metricool field ids per platform, in the order the autopilot requests them. The answer's
# rows hold the values in the same order.
METRICS = {
    "youtube": ["YTVP04", "YTVP02", "YTVP06", "YTVP08", "YTVP09", "YTVP11", "YTVP12", "YTVP07", "YTVP17"],
    "instagram": ["IGRE06", "IGRE02", "IGRE23", "IGRE24", "IGRE10", "IGRE07", "IGRE21", "IGRE11", "IGRE12",
                  "IGRE27", "IGRE28"],
    "facebook": ["FBRE06", "FBRE02", "FBRE10", "FBRE13", "FBRE08", "FBRE07", "FBRE11"],
}
FIELDS = {
    "youtube": ["key", "published", "views", "avg_view_seconds", "likes", "comments", "shares", "watch_minutes",
                "title"],
    "instagram": ["key", "published", "views", "avg_view_seconds", "likes", "comments", "shares", "reach", "saves",
                  "retention_pct", "view_rate_pct"],
    "facebook": ["key", "published", "views", "avg_view_seconds", "likes", "actions", "reach"],
}
NUMERIC = {"views", "avg_view_seconds", "likes", "comments", "shares", "watch_minutes", "reach", "saves",
           "retention_pct", "view_rate_pct", "actions"}


def active(cfg, today):
    """True while today is inside the experiment's production window."""
    return bool(cfg.get("active")) and str(cfg["start"]) <= str(today) <= str(cfg["end"])


def assign(variables, n, start=0):
    """n arm dicts. Each variable cycles through its values; the cycle shifts by the
    variable's position every round, so values stay balanced and pairs keep changing."""
    out = []
    for i in range(start, start + n):
        arms = {}
        for k, (name, values) in enumerate(variables.items()):
            size = len(values)
            arms[name] = values[(i + (i // size) * k) % size]
        out.append(arms)
    return out


def runs_in(manifests, exp_id):
    return [m for m in manifests if (m.get("experiment") or {}).get("id") == exp_id]


def credits_spent(manifests, exp_id):
    return round(sum(float((m.get("video") or {}).get("credits_spent") or 0) for m in runs_in(manifests, exp_id)), 2)


def post_key(platform, url):
    """The id Metricool's per-video rows carry, read from a post's public link."""
    if not url:
        return None
    if platform == "youtube":
        m = re.search(r"(?:shorts/|v=|youtu\.be/)([\w-]{6,})", url)
    elif platform == "instagram":
        m = re.search(r"/(?:reel|p)/([\w-]+)", url)
    else:
        m = re.search(r"(\d{8,})", url)
    return m.group(1) if m else None


def parse_rows(platform, answer):
    """Metricool's answer ({"rows": [[...], ...]}) as dicts keyed by FIELDS, keyed by post id."""
    a = json.loads(answer) if isinstance(answer, str) else answer
    out = {}
    for row in (a or {}).get("rows") or []:
        rec = {}
        for name, value in zip(FIELDS[platform], row):
            if name in NUMERIC:
                rec[name] = None if value in (None, "") else float(value)
            else:
                rec[name] = value
        key = rec["key"] if platform == "youtube" else post_key(platform, rec["key"])
        if key:
            out[key] = rec
    return out


def merge(manifests, platform, stats, now):
    """Copy stats onto matching posts. Returns [(run_id, record)] for the posts updated."""
    updated = []
    for m in manifests:
        post = (m.get("posts") or {}).get(platform) or {}
        key = post_key(platform, post.get("url"))
        if not key or key not in stats or not post.get("at"):
            continue
        rec = stats[key]
        age = (now - datetime.fromisoformat(post["at"].replace("Z", "+00:00"))).total_seconds() / 3600
        fields = {k: rec.get(k) for k in ("views", "avg_view_seconds", "likes", "comments", "shares", "reach",
                                           "saves", "retention_pct", "view_rate_pct") if rec.get(k) is not None}
        if "views" in fields:
            fields["views"] = int(fields["views"])
        fields.update(views_age_hours=round(age, 1), stats_at=now.isoformat(timespec="seconds"))
        updated.append((m["run_id"], fields))
    return updated


def snapshot_path(exp_id, now, platform):
    return EXP_DIR / exp_id / "snapshots" / f"{now.strftime('%Y-%m-%dT%H%M')}-{platform}.json"


def video_rows(manifests, exp_id):
    """One row per experiment video: its arms and its latest stats summed over platforms."""
    rows = []
    for m in runs_in(manifests, exp_id):
        posts = {p: v for p, v in (m.get("posts") or {}).items() if v.get("views") is not None}
        if not posts:
            continue
        duration = (m.get("video") or {}).get("duration_seconds")
        views = sum(v["views"] for v in posts.values())
        ages = [v["views_age_hours"] for v in posts.values() if v.get("views_age_hours")]
        yt = posts.get("youtube") or {}
        inter = sum((v.get("likes") or 0) + (v.get("comments") or 0) + (v.get("shares") or 0) for v in posts.values())
        rows.append({
            "run_id": m["run_id"], "topic": m.get("topic"), **(m["experiment"].get("arms") or {}),
            "views": views, "youtube_views": yt.get("views"),
            "views_per_hour": round(views / max(1.0, median(ages)), 2) if ages else None,
            "youtube_retention": round(yt["avg_view_seconds"] / duration, 3)
            if yt.get("avg_view_seconds") and duration else None,
            "engagement": round(inter / views, 4) if views else None,
            "by_platform": {p: v["views"] for p, v in posts.items()},
        })
    return rows


def report(manifests, cfg, shrink=2):
    """{videos, by_variable: [{variable, value, videos, median_views, ...lift}], best, worst}."""
    rows = video_rows(manifests, cfg["id"])
    by_variable = []
    scored = [r for r in rows if r["views_per_hour"] is not None]
    overall = median(r["views_per_hour"] for r in scored) if scored else 0
    for name in cfg["variables"]:
        groups = {}
        for r in scored:
            groups.setdefault(r.get(name), []).append(r)
        for value, rs in groups.items():
            if value is None:
                continue
            ret = [r["youtube_retention"] for r in rs if r["youtube_retention"] is not None]
            by_variable.append({
                "variable": name, "value": value, "videos": len(rs),
                "median_views": median(r["views"] for r in rs),
                "median_views_per_hour": round(median(r["views_per_hour"] for r in rs), 2),
                "median_youtube_retention": round(median(ret), 3) if ret else None,
                "lift": lift([r["views_per_hour"] for r in rs], overall, shrink),
            })
    by_variable.sort(key=lambda r: (list(cfg["variables"]).index(r["variable"]), -r["lift"]))
    ranked = sorted(rows, key=lambda r: -(r["views_per_hour"] or 0))
    return {"experiment": cfg["id"], "videos": len(rows), "credits_spent": credits_spent(manifests, cfg["id"]),
            "by_variable": by_variable, "best": ranked[:3], "worst": ranked[-3:][::-1], "videos_detail": ranked}


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, default=str) + "\n", encoding="utf-8")
    return path


def now_utc():
    return datetime.now(timezone.utc)
