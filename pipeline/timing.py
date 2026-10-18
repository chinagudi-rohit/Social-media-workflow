"""Post times: when each platform's post goes out (config/timing.yaml).

Candidate slots for a platform and day are ranked by three inputs:

    score = w_research * research + w_audience * audience + w_results * results

  research  1.0 for the best default slot down to 0.5 for the last; 0 for a slot that only
            the audience data suggested.
  audience  this account's follower activity in that hour, 0-1 (1 = busiest hour that
            weekday). From data/timing/<date>.json, which the autopilot writes from
            Metricool's best-time data:
              {"date": "2026-10-18", "source": "metricool", "timezone": "America/New_York",
               "platforms": {"tiktok": {"mon": {"18": 412, "19": 530, ...}, ...}, ...}}
            Values are any non-negative scale; they are normalized per platform and day.
  results   how this account's own posts near that hour did: median views per hour in their
            first days, against the platform's median, shrunk toward "average" while there
            are few posts, as -1..1. From run manifests: posts[<platform>] with `at`,
            `views` and `views_age_hours` (`python -m pipeline post-stats`).

A slot must be `min_lead_minutes` away and `min_gap_hours` from any other post on that
platform that day. A fixed share of posts (`explore_rate`) goes out at the runner-up slot so
the results input keeps learning; the draw is a hash of the date, platform and run, so a
re-plan gives the same answer.
"""

import hashlib
import json
from datetime import date, datetime, time, timedelta
from statistics import median
from zoneinfo import ZoneInfo

from .config import ROOT

TIMING_DIR = ROOT / "data" / "timing"
PLATFORMS = ("tiktok", "instagram", "youtube", "facebook")
DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
AUDIENCE_HOURS = range(8, 22)      # audience-suggested slots stay between 08:00 and 21:00
STATS_AGE_HOURS = (12, 120)        # post stats outside this age are ignored


def day_kind(day):
    return {5: "saturday", 6: "sunday"}.get(day.weekday(), "weekday")


def parse_slot(slot):
    hh, mm = (int(x) for x in slot.split(":"))
    return hh, mm


def slot_datetime(day, slot, tz):
    hh, mm = parse_slot(slot)
    return datetime.combine(day, time(hh, mm), tz)


def load_audience(timing_dir=TIMING_DIR, on_or_before=None, max_age_days=30):
    """Newest audience file on or before the date and at most max_age_days old, or None."""
    on_or_before = on_or_before or date.today()
    oldest = str(on_or_before - timedelta(days=max_age_days))
    files = sorted(p for p in timing_dir.glob("*.json") if oldest <= p.stem <= str(on_or_before))
    if not files:
        return None
    with open(files[-1], encoding="utf-8") as f:
        return json.load(f)


def validate_audience(doc):
    errors = []
    try:
        date.fromisoformat(doc.get("date", ""))
    except ValueError:
        errors.append("'date' must be YYYY-MM-DD")
    try:
        ZoneInfo(doc.get("timezone") or "")
    except (KeyError, ValueError):
        errors.append("'timezone' must be an IANA name such as America/New_York")
    platforms = doc.get("platforms")
    if not isinstance(platforms, dict) or not platforms:
        return errors + ["'platforms' must map platforms to {day: {hour: activity}}"]
    for p, days in platforms.items():
        if p not in PLATFORMS:
            errors.append(f"unknown platform '{p}'")
            continue
        for d, hours in (days or {}).items():
            if d not in DAYS:
                errors.append(f"{p}: day '{d}' must be one of {', '.join(DAYS)}")
                continue
            for h, v in (hours or {}).items():
                if not str(h).isdigit() or not 0 <= int(h) <= 23:
                    errors.append(f"{p}.{d}: hour '{h}' must be 0-23")
                if not isinstance(v, (int, float)) or v < 0:
                    errors.append(f"{p}.{d}.{h}: activity must be a number >= 0")
    return errors


def audience_curve(doc, platform, day):
    """{hour: 0-1} for the platform on that weekday, or {} without data.

    Hours are in the file's timezone; callers use files written in config's timezone.
    """
    raw = (((doc or {}).get("platforms") or {}).get(platform) or {}).get(DAYS[day.weekday()]) or {}
    vals = {int(h): float(v) for h, v in raw.items()}
    top = max(vals.values(), default=0)
    return {h: v / top for h, v in vals.items()} if top > 0 else {}


def post_history(manifests, platform, tz, since):
    """[(local hour as a float, views per hour)] for this platform's posts with stats."""
    out = []
    for m in manifests:
        p = (m.get("posts") or {}).get(platform) or {}
        at, views, age = p.get("at"), p.get("views"), p.get("views_age_hours")
        if not at or views is None or not age or not STATS_AGE_HOURS[0] <= age <= STATS_AGE_HOURS[1]:
            continue
        t = datetime.fromisoformat(at.replace("Z", "+00:00")).astimezone(tz)
        if t >= since:
            out.append((t.hour + t.minute / 60, float(views) / float(age)))
    return out


def results_lift(history, hour, rcfg):
    """(-1..1 lift for posts near this hour, how many posts that rests on)."""
    if len(history) < rcfg["min_posts"]:
        return 0.0, 0
    overall = median(v for _, v in history)
    near = [v for h, v in history if abs(h - hour) <= rcfg["hour_radius"]]
    if not near or overall <= 0:
        return 0.0, len(near)
    k = rcfg["shrink"]
    shrunk = (len(near) * (median(near) / overall) + k) / (len(near) + k)
    return max(-1.0, min(1.0, shrunk - 1.0)), len(near)


def rank_slots(cfg, platform, day, audience=None, history=()):
    """Candidate slots for the day, best first: [{slot, score, parts, posts}]."""
    research = cfg["slots"][platform][day_kind(day)]
    curve = audience_curve(audience, platform, day)
    candidates = list(research)
    for h in sorted(curve, key=lambda h: (-curve[h], h)):
        slot = f"{h:02d}:00"
        if h in AUDIENCE_HOURS and slot not in candidates:
            candidates.append(slot)
        if len(candidates) >= len(research) + 2:
            break
    w = cfg["weights"]
    ranked = []
    for slot in candidates:
        hh, mm = parse_slot(slot)
        lift, n = results_lift(history, hh + mm / 60, cfg["results"])
        parts = {
            "research": 1.0 - 0.5 * research.index(slot) / max(1, len(research) - 1) if slot in research else 0.0,
            "audience": curve.get(hh, 0.0),
            "results": lift,
        }
        ranked.append({
            "slot": slot,
            "score": round(sum(w[k] * v for k, v in parts.items()), 3),
            "parts": {k: round(v, 3) for k, v in parts.items()},
            "posts": n,
        })
    ranked.sort(key=lambda r: (-r["score"], r["slot"]))
    return ranked


def booked(manifests, platform, day, tz, exclude_run=None):
    """When this platform already has posts going out that day (other runs)."""
    out = []
    for m in manifests:
        if m.get("run_id") == exclude_run:
            continue
        p = (m.get("posts") or {}).get(platform) or {}
        if p.get("at") and p.get("status") in ("scheduled", "published", "processing"):
            t = datetime.fromisoformat(p["at"].replace("Z", "+00:00")).astimezone(tz)
            if t.date() == day:
                out.append(t)
    return out


def _draw(*key):
    return int(hashlib.sha256(":".join(map(str, key)).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def plan(cfg, day, now, manifests=(), audience=None, platforms=PLATFORMS, run_id=""):
    """{platform: {at, local, slot, explore, basis, ranked}} for one video posted on `day`."""
    tz = ZoneInfo(cfg["timezone"])
    lead = timedelta(minutes=cfg["min_lead_minutes"])
    gap = timedelta(hours=cfg["min_gap_hours"])
    since = now - timedelta(days=cfg["results"]["window_days"])
    out = {}
    for p in platforms:
        history = post_history(manifests, p, tz, since)
        busy = booked(manifests, p, day, tz, exclude_run=run_id)
        ranked = rank_slots(cfg, p, day, audience, history)
        when = None
        for target in (day, day + timedelta(days=1)):
            options = ranked if target == day else rank_slots(cfg, p, target, audience, history)
            fits = [r for r in options
                    if slot_datetime(target, r["slot"], tz) >= now + lead
                    and all(abs(slot_datetime(target, r["slot"], tz) - b) >= gap for b in busy)]
            if fits:
                explore = target == day and len(fits) > 1 and _draw(day, p, run_id) < cfg["explore_rate"]
                pick = fits[1] if explore else fits[0]
                when = slot_datetime(target, pick["slot"], tz)
                break
            busy = booked(manifests, p, target + timedelta(days=1), tz, exclude_run=run_id)
        if when is None:  # every slot today and tomorrow is taken: go out as soon as allowed
            pick, explore = ranked[0], False
            when = (now + lead).astimezone(tz).replace(second=0, microsecond=0)
        basis = ["research"]
        if audience_curve(audience, p, day):
            basis.append("audience")
        if len(history) >= cfg["results"]["min_posts"]:
            basis.append(f"results ({len(history)} posts)")
        out[p] = {
            "at": when.isoformat(),
            "local": when.strftime("%a %b %d %H:%M %Z"),
            "slot": pick["slot"],
            "explore": explore,
            "basis": basis,
            "ranked": ranked[:4],
        }
    return out


def groups(plan_by_platform):
    """Platforms that share a post time, as [(at, [platforms])] in time order."""
    by_time = {}
    for p, entry in plan_by_platform.items():
        by_time.setdefault(entry["at"], []).append(p)
    return sorted(by_time.items())
