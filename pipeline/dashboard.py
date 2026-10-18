"""Dataset files for the Creator Earnings dashboard (one JSON array of rows each).

The autopilot writes these to data/dashboard/ every day and uploads the ones that changed
to the dashboard, which reads them as its sources.
"""

from .budget import days_until_renewal, video_cost

PROGRAMS = [
    # Monetization program entry bars (research/monetization-2026.md). Updated when the
    # daily research finds a rule change.
    {"platform": "youtube", "program": "YouTube Partner Program (Shorts)", "followers_needed": 1000,
     "views_needed": 10_000_000, "views_window_days": 90,
     "rule": "1,000 subscribers + 10M Shorts views in 90 days (or 4,000 watch hours)"},
    {"platform": "tiktok", "program": "Creator Rewards Program", "followers_needed": 10_000,
     "views_needed": 100_000, "views_window_days": 30,
     "rule": "10k followers + 100k views in 30 days; videos over 1 minute"},
    {"platform": "facebook", "program": "Content Monetization", "followers_needed": 5000,
     "views_needed": 600_000, "views_window_days": 60,
     "rule": "Invite-based; reported 5-10k followers and 60k-600k watch minutes in 60 days"},
    {"platform": "twitter", "program": "X Original Content Rewards", "followers_needed": 500,
     "views_needed": 500_000, "views_window_days": 90,
     "rule": "X Premium + 500 verified followers + 500k Home timeline views from verified users in 90 days; "
             "pays on Premium users' views of original posts"},
    {"platform": "instagram", "program": "No ad revenue share", "followers_needed": 10_000,
     "views_needed": 0, "views_window_days": 30,
     "rule": "No view payouts; earnings come from affiliates, bonuses by invite and brand deals"},
]

PLATFORM_ORDER = ("youtube", "tiktok", "instagram", "facebook", "twitter")


def _order(targets):
    return [p for p in PLATFORM_ORDER if targets is None or p in targets]


def earnings_daily_rows(snap, targets=None):
    """One row per platform per day with earnings. With nothing recorded yet, a $0 row per
    platform for the snapshot's day, so the dashboard shows zero rather than a failed source."""
    sources = snap.get("earnings_sources", {})
    rows = []
    for day in snap.get("earnings_daily", []):
        for platform, usd in day.items():
            if platform != "date":
                rows.append({"date": day["date"], "platform": platform, "usd": round(float(usd), 2),
                             "source": sources.get(platform, "Logged by hand")})
    return rows or [{"date": snap["date"], "platform": p, "usd": 0.0, "source": "Nothing recorded yet"}
                    for p in _order(targets)]


def platform_rows(snap, targets=None):
    """Every platform, signed in or not, with its audience counters and earnings source.

    `linked` in the snapshot lists networks connected through Metricool (getBrandSettings)."""
    rows = []
    linked = set(snap.get("linked", []))
    for platform in _order(targets):
        stats = snap.get("platforms", {}).get(platform) or {}
        rows.append({
            "platform": platform,
            "account": "Connected" if stats or platform in linked else "Not signed in",
            "followers": stats.get("followers"),
            "views": stats.get("views"),
            "likes": stats.get("likes"),
            "comments": stats.get("comments"),
            "shares": stats.get("shares"),
            "earnings_30d": snap.get("earnings_30d", {}).get(platform, 0.0),
            "earnings_source": snap.get("earnings_sources", {}).get(platform) or "Not connected",
        })
    return rows


def post_time_rows(plan, tz_name="America/New_York"):
    """Next post time per platform from `timing.plan`, with what it rests on."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    rows = []
    for platform in PLATFORM_ORDER:
        entry = plan.get(platform)
        if not entry:
            continue
        at = datetime.fromisoformat(entry["at"]).astimezone(ZoneInfo(tz_name))
        rows.append({
            "platform": platform,
            "at": entry["at"],
            "day": at.strftime("%a %b %-d"),
            "time": at.strftime("%-I:%M %p ") + at.tzname(),
            "basis": " + ".join(b[0].upper() + b[1:] for b in entry["basis"]),
        })
    return rows


def video_rows(snap, targets=None):
    rows = []
    for v in sorted(snap.get("videos", []), key=lambda v: v["date"], reverse=True):
        posts = v.get("posts", {})
        rows.append({
            "run_id": v["run_id"],
            "date": v["date"],
            "niche": v["niche"],
            "topic": v["topic"],
            "credits": v.get("credits"),
            **{p: (posts.get(p) or {}).get("status") or "not posted" for p in _order(targets)},
        })
    return rows


def credit_rows(snap, prod_cfg, today):
    tier = prod_cfg["tiers"][prod_cfg["tier"]]
    cost = video_cost(tier, 170, 8)
    balance = snap.get("credits", {}).get("balance")
    reserve = prod_cfg["plan"]["reserve_credits"]
    return [{
        "date": str(today),
        "plan": prod_cfg["plan"]["name"],
        "monthly_credits": prod_cfg["plan"]["monthly_credits"],
        "balance": balance,
        "spent_30d": snap.get("credits", {}).get("spent_30d", 0),
        "tier": prod_cfg["tier"],
        "cost_per_video": cost,
        "videos_left": None if balance is None else max(0, int((balance - reserve) // cost)),
        "days_to_renewal": days_until_renewal(today, prod_cfg["plan"]["renews_on_day"]),
    }]


def niche_rows(scored, niches):
    names = {n["id"]: n for n in niches}
    return [
        {
            "niche": s["id"],
            "name": names[s["id"]]["name"],
            "score": s["score"],
            "rpm_tier": names[s["id"]].get("rpm_tier"),
            "view_tier": names[s["id"]].get("view_tier"),
            "trend": s["parts"]["trend"],
            "results": s["parts"].get("results", 0.0),
            "explore": s["parts"].get("explore", 0.0),
        }
        for s in scored
    ]


def insight_rows(summary, niches):
    """What is working, for the dashboard: one row per dimension value, with a readable label.
    Before there are enough videos with stats, one row says so."""
    names = {n["id"]: n["name"] for n in niches}
    labels = {"niche": "Niche", "structure": "Structure", "voice": "Voice", "hour": "Post time (ET)",
              "length": "Length"}
    rows = [{"key": f"{r['dimension']}:{r['value']}", "dimension": labels[r["dimension"]],
             "value": names.get(r["value"], r["value"]) if r["dimension"] == "niche" else r["value"],
             "videos": r["videos"], "views_per_hour": r["views_per_hour"], "retention": r["retention"],
             "lift": r["lift"]} for r in summary]
    return rows or [{"key": "none", "dimension": "Waiting for data", "value": "Needs 3 videos with 2-day stats",
                     "videos": 0, "views_per_hour": None, "retention": None, "lift": 0.0}]


def datasets(snap, prod_cfg, scored, niches, today, plan=None, tz_name="America/New_York", targets=None):
    """Every dataset file; `targets` limits the per-platform ones to the platforms in use."""
    return {
        "earnings_daily": earnings_daily_rows(snap, targets),
        "platforms": platform_rows(snap, targets),
        "post_times": post_time_rows(plan or {}, tz_name),
        "videos": video_rows(snap, targets),
        "credits": credit_rows(snap, prod_cfg, today),
        "niches": niche_rows(scored, niches),
        "programs": PROGRAMS,
    }
