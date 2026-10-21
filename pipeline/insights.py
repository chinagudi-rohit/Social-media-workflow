"""What is working: this channel's own results, by niche, format, structure, voice, post hour
and length.

Each published post with stats (`python -m pipeline post-stats`) becomes one row. Reach is
views per hour over the post's first days; retention is average view duration over video
length; engagement is (likes + comments + shares) per view. A group's lift is its median
views per hour against the channel's, pulled toward "no better than average" by `shrink`
posts' worth of weight, so two lucky videos do not swing the plan.
"""

from datetime import datetime
from statistics import median
from zoneinfo import ZoneInfo

DIMENSIONS = ("niche", "format", "structure", "voice", "hour", "length", "look")
STATS_AGE_HOURS = (12, 120)
# Scripts written before the experiment's arm names named their hook type in words.
FORMAT_NAMES = {"odd-object question": "odd-object", "story teaser": "micro-story", "brain fact": "brain-fact",
                "result-first number": "money-math", "myth-bust": "myth-flip"}


def length_bucket(seconds):
    if not seconds:
        return None
    return ("under 30 s" if seconds < 30 else "30-45 s" if seconds < 45 else "45-60 s" if seconds <= 60
            else "over 60 s")


def format_of(m):
    """The video's format: its experiment arm, else its script's hook type."""
    arm = ((m.get("experiment") or {}).get("arms") or {}).get("format")
    return arm or FORMAT_NAMES.get(m.get("hook_type"), m.get("hook_type"))


def video_rows(manifests, tz_name="America/New_York"):
    tz = ZoneInfo(tz_name)
    rows = []
    for m in manifests:
        duration = (m.get("video") or {}).get("duration_seconds")
        for platform, p in (m.get("posts") or {}).items():
            views, age = p.get("views"), p.get("views_age_hours")
            if views is None or not age or not STATS_AGE_HOURS[0] <= age <= STATS_AGE_HOURS[1] or not p.get("at"):
                continue
            at = datetime.fromisoformat(p["at"].replace("Z", "+00:00")).astimezone(tz)
            avg = p.get("avg_view_seconds")
            inter = sum(p.get(k) or 0 for k in ("likes", "comments", "shares"))
            rows.append({
                "run_id": m["run_id"], "platform": platform, "niche": m.get("niche_id"), "format": format_of(m),
                "structure": m.get("structure"), "voice": m.get("voice"), "hour": f"{at.hour:02d}:00",
                "length": length_bucket(duration), "look": "style key" if m.get("style_key") else "no style key",
                "views": views, "views_per_hour": views / age,
                "retention": round(avg / duration, 3) if avg and duration else None,
                "engagement": round(inter / views, 4) if views else None,
            })
    return rows


def lift(group, overall, shrink):
    """-1..1: how much better this group's median is than the channel's, shrunk by size."""
    if not group or overall <= 0:
        return 0.0
    n = len(group)
    shrunk = (n * (median(group) / overall) + shrink) / (n + shrink)
    return round(max(-1.0, min(1.0, shrunk - 1.0)), 3)


def summarize(rows, shrink=3, min_rows=3):
    """[{dimension, value, videos, views_per_hour, retention, engagement, lift}] best first."""
    if len(rows) < min_rows:
        return []
    overall = median(r["views_per_hour"] for r in rows)
    out = []
    for dim in DIMENSIONS:
        groups = {}
        for r in rows:
            if r[dim] is not None:
                groups.setdefault(r[dim], []).append(r)
        for value, rs in groups.items():
            ret = [r["retention"] for r in rs if r["retention"] is not None]
            eng = [r["engagement"] for r in rs if r["engagement"] is not None]
            out.append({
                "dimension": dim, "value": value, "videos": len(rs),
                "views_per_hour": round(median(r["views_per_hour"] for r in rs), 2),
                "retention": round(median(ret), 3) if ret else None,
                "engagement": round(median(eng), 4) if eng else None,
                "lift": lift([r["views_per_hour"] for r in rs], overall, shrink),
            })
    out.sort(key=lambda r: (DIMENSIONS.index(r["dimension"]), -r["lift"], r["value"]))
    return out


def niche_results(manifests, shrink=3, min_rows=3):
    """({niche: lift}, {niche: videos posted}) for the niche ranking."""
    rows = video_rows(manifests)
    posted = {}
    for m in manifests:
        if any(p.get("status") == "published" for p in (m.get("posts") or {}).values()):
            posted[m["niche_id"]] = posted.get(m["niche_id"], 0) + 1
    lifts = {r["value"]: r["lift"] for r in summarize(rows, shrink, min_rows) if r["dimension"] == "niche"}
    return lifts, posted
