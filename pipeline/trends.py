"""Daily trend snapshots and niche scoring.

Each morning the autopilot researches what is moving in each niche and writes
data/trends/<date>.json (format below). Scoring blends that with each niche's
monetization profile from config/niches.yaml:

    score = rpm_tier * w_rpm + view_tier * w_views + trend_boost * w_trend
            - saturation * w_saturation - recency_penalty

Snapshot format:
{
  "date": "2026-10-18",
  "niches": {
    "<niche_id>": {
      "trend_boost": 0.0-3.0,          # how hot the niche is today
      "saturation": 0.0-1.0,           # how crowded the current hot topics are
      "signals": ["what was seen, with source"],
      "topic_ideas": [{"topic": "...", "angle": "...", "why_now": "...", "sources": ["https://..."]}]
    }
  },
  "program_changes": ["monetization rule changes seen today"],
  "policy_notes": ["platform policy news that affects what we publish"]
}
"""

import json
from datetime import date, datetime

from .config import ROOT

TRENDS_DIR = ROOT / "data" / "trends"

DEFAULT_WEIGHTS = {"w_rpm": 1.0, "w_views": 0.7, "w_trend": 1.0, "w_saturation": 1.0,
                   "recency_days": 2, "recency_penalty": 1.5}


def snapshot_path(day, trends_dir=TRENDS_DIR):
    return trends_dir / f"{day}.json"


def template(niches, day):
    return {
        "date": str(day),
        "niches": {n["id"]: {"trend_boost": 0.0, "saturation": 0.0, "signals": [], "topic_ideas": []}
                   for n in niches},
        "program_changes": [],
        "policy_notes": [],
    }


def load_latest(trends_dir=TRENDS_DIR, on_or_before=None):
    """Newest snapshot on or before the given date, or None."""
    on_or_before = str(on_or_before or date.today())
    files = sorted(p for p in trends_dir.glob("*.json") if p.stem <= on_or_before)
    if not files:
        return None
    with open(files[-1], encoding="utf-8") as f:
        return json.load(f)


def validate(doc, niches):
    errors = []
    ids = {n["id"] for n in niches}
    try:
        date.fromisoformat(doc.get("date", ""))
    except ValueError:
        errors.append("'date' must be YYYY-MM-DD")
    entries = doc.get("niches")
    if not isinstance(entries, dict) or not entries:
        return errors + ["'niches' must map niche ids to entries"]
    for nid, e in entries.items():
        if nid not in ids:
            errors.append(f"unknown niche '{nid}'")
            continue
        if not 0 <= e.get("trend_boost", -1) <= 3:
            errors.append(f"{nid}: trend_boost must be 0-3")
        if not 0 <= e.get("saturation", -1) <= 1:
            errors.append(f"{nid}: saturation must be 0-1")
        for idea in e.get("topic_ideas", []):
            if not idea.get("topic"):
                errors.append(f"{nid}: every topic idea needs a 'topic'")
            if not any(str(u).startswith("http") for u in idea.get("sources", [])):
                errors.append(f"{nid}: topic '{idea.get('topic', '?')}' needs a source URL")
    return errors


def score_niches(niches, snapshot, manifests, now, weights=None):
    """Return [{'id', 'score', 'parts'}] sorted best first."""
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    trend = (snapshot or {}).get("niches", {})
    last_post = {}
    for m in manifests:
        ts = datetime.fromisoformat(m["created_at"].replace("Z", "+00:00"))
        last_post[m["niche_id"]] = max(ts, last_post.get(m["niche_id"], ts))

    scored = []
    for n in niches:
        t = trend.get(n["id"], {})
        parts = {
            "rpm": n.get("rpm_tier", 3) * w["w_rpm"],
            "views": n.get("view_tier", 3) * w["w_views"],
            "trend": t.get("trend_boost", 0.0) * w["w_trend"],
            "saturation": -t.get("saturation", 0.0) * w["w_saturation"],
            "recency": 0.0,
        }
        if n["id"] in last_post:
            days = (now - last_post[n["id"]]).total_seconds() / 86400
            if days < w["recency_days"]:
                parts["recency"] = -w["recency_penalty"]
        scored.append({"id": n["id"], "score": round(sum(parts.values()), 2),
                       "parts": {k: round(v, 2) for k, v in parts.items()}})
    scored.sort(key=lambda s: s["score"], reverse=True)
    return scored
