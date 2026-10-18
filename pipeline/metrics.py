"""Daily monetization snapshot: views, followers and earnings per platform.

Sources:
  - Upload-Post analytics: followers, views, likes, comments, shares per platform.
  - YouTube Analytics API: estimatedRevenue by day (needs the yt-analytics-monetary scope).
  - Facebook Graph API: content_monetization_earnings by day (Content Monetization pages).
  - data/earnings_manual.csv: everything without an API (TikTok Creator Rewards payouts,
    Instagram bonuses, affiliate commissions). Columns: date,platform,amount_usd,source,note
  - data/metricool/<date>.json: counters and revenue an agent read through the Metricool MCP
    (the Hermes publisher writes it; see `load_external`).

Snapshots land in data/metrics/<date>.json; pipeline/dashboard.py turns them into the
dashboard's dataset files in data/dashboard/.
"""

import csv
import json
from datetime import date, timedelta
from pathlib import Path

from .config import ROOT

METRICS_DIR = ROOT / "data" / "metrics"
EXTERNAL_DIR = ROOT / "data" / "metricool"
MANUAL_EARNINGS = ROOT / "data" / "earnings_manual.csv"
YT_REPORTS = "https://youtubeanalytics.googleapis.com/v2/reports"
COUNTERS = ("followers", "views", "likes", "comments", "shares", "saves", "watch_time_minutes")


def normalize_uploadpost(body):
    """Keep the counters the dashboard uses from an Upload-Post analytics response."""
    out = {}
    for platform, data in body.items():
        if not isinstance(data, dict) or data.get("error") or data.get("message"):
            continue
        out[platform] = {k: data.get(k) for k in COUNTERS if data.get(k) is not None}
    return out


def validate_external(doc):
    """Shape check for a data/metricool/<date>.json file."""
    errors = []
    if not isinstance(doc, dict):
        return ["not a JSON object"]
    for key in ("date", "source", "platforms"):
        if key not in doc:
            errors.append(f"missing {key}")
    for platform, counters in (doc.get("platforms") or {}).items():
        if platform not in ("tiktok", "instagram", "youtube", "facebook"):
            errors.append(f"unknown platform {platform}")
        elif not isinstance(counters, dict) or any(
                k not in COUNTERS or not isinstance(v, (int, float)) for k, v in counters.items()):
            errors.append(f"{platform}: counters must be numbers named {', '.join(COUNTERS)}")
    for key, field in (("youtube_revenue", "estimatedRevenue"), ("facebook_earnings", "earnings")):
        for row in doc.get(key) or []:
            if not isinstance(row, dict) or "day" not in row or not isinstance(row.get(field), (int, float)):
                errors.append(f"{key} rows need day and a numeric {field}")
                break
    return errors


def load_external(day, max_age_days=2, directory=EXTERNAL_DIR):
    """The newest data/metricool/<date>.json at most max_age_days before `day`, or None.

    Shape: {"date", "source": "metricool", "platforms": {<platform>: {<counter>: n}},
    "youtube_revenue": [{"day", "estimatedRevenue"}], "facebook_earnings": [{"day", "earnings"}]}.
    """
    for back in range(max_age_days + 1):
        path = Path(directory) / f"{day - timedelta(days=back)}.json"
        if path.exists():
            doc = json.loads(path.read_text(encoding="utf-8"))
            errors = validate_external(doc)
            if errors:
                raise ValueError(f"{path.name}: " + "; ".join(errors))
            return doc
    return None


def youtube_revenue(session, token, start, end):
    """Daily views, minutes and estimated revenue (USD) for the authorized channel."""
    resp = session.get(
        YT_REPORTS,
        headers={"Authorization": f"Bearer {token}"},
        params={
            "ids": "channel==MINE",
            "startDate": str(start),
            "endDate": str(end),
            "metrics": "views,estimatedMinutesWatched,estimatedRevenue,cpm",
            "dimensions": "day",
            "sort": "day",
        },
        timeout=60,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"YouTube Analytics failed ({resp.status_code}): {resp.text[:300]}")
    body = resp.json()
    cols = [c["name"] for c in body.get("columnHeaders", [])]
    return [dict(zip(cols, row)) for row in body.get("rows", [])]


def facebook_earnings(session, base_url, page_id, token, start, end):
    """Daily Content Monetization earnings for a Page, best effort."""
    resp = session.get(
        f"{base_url}/{page_id}/insights",
        params={"metric": "content_monetization_earnings", "period": "day",
                "since": str(start), "until": str(end + timedelta(days=1)), "access_token": token},
        timeout=60,
    )
    if resp.status_code >= 400:
        try:
            msg = resp.json()["error"]["message"]
        except (ValueError, KeyError, TypeError):
            msg = resp.text[:300]
        raise RuntimeError(f"Facebook earnings failed ({resp.status_code}): {msg}")
    rows = []
    for metric in resp.json().get("data", []):
        for v in metric.get("values", []):
            value = v.get("value")
            amount = value.get("amount", 0) if isinstance(value, dict) else value
            rows.append({"day": v.get("end_time", "")[:10], "earnings": float(amount or 0)})
    return rows


def manual_earnings(path=MANUAL_EARNINGS):
    if not Path(path).exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return [
            {**r, "amount_usd": float(r["amount_usd"])}
            for r in csv.DictReader(f)
            if r.get("date") and r.get("amount_usd")
        ]


def earnings_by_platform(youtube_rows, facebook_rows, manual_rows, start, end):
    """Total earnings per platform in [start, end]."""
    totals = {}

    def add(platform, day, amount):
        if str(start) <= day <= str(end):
            totals[platform] = round(totals.get(platform, 0.0) + amount, 2)

    for r in youtube_rows:
        add("youtube", r["day"], float(r.get("estimatedRevenue") or 0))
    for r in facebook_rows:
        add("facebook", r["day"], r["earnings"])
    for r in manual_rows:
        add(r["platform"], r["date"], r["amount_usd"])
    return totals


def snapshot(day, platform_stats, earnings_30d, earnings_daily, runs, credits):
    return {
        "date": str(day),
        "platforms": platform_stats,
        "earnings_30d": earnings_30d,
        "earnings_total_30d": round(sum(earnings_30d.values()), 2),
        "earnings_daily": earnings_daily,
        "videos": runs,
        "credits": credits,
    }


def default_window(today, days=30):
    return today - timedelta(days=days - 1), today


def today():
    return date.today()
