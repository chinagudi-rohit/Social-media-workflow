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
    {"platform": "instagram", "program": "No ad revenue share", "followers_needed": 10_000,
     "views_needed": 0, "views_window_days": 30,
     "rule": "No view payouts; earnings come from affiliates, bonuses by invite and brand deals"},
]

PLATFORM_ORDER = ("youtube", "tiktok", "instagram", "facebook")


def earnings_daily_rows(snap):
    rows = []
    for day in snap.get("earnings_daily", []):
        for platform, usd in day.items():
            if platform != "date":
                rows.append({"date": day["date"], "platform": platform, "usd": round(float(usd), 2)})
    return rows


def platform_rows(snap):
    rows = []
    for platform in PLATFORM_ORDER:
        stats = snap.get("platforms", {}).get(platform)
        if stats is None and platform not in snap.get("earnings_30d", {}):
            continue
        stats = stats or {}
        rows.append({
            "platform": platform,
            "followers": stats.get("followers"),
            "views": stats.get("views"),
            "likes": stats.get("likes"),
            "comments": stats.get("comments"),
            "shares": stats.get("shares"),
            "earnings_30d": snap.get("earnings_30d", {}).get(platform, 0.0),
        })
    return rows


def video_rows(snap):
    rows = []
    for v in sorted(snap.get("videos", []), key=lambda v: v["date"], reverse=True):
        posts = v.get("posts", {})
        rows.append({
            "run_id": v["run_id"],
            "date": v["date"],
            "niche": v["niche"],
            "topic": v["topic"],
            "credits": v.get("credits"),
            **{p: (posts.get(p) or {}).get("status") or "not posted" for p in PLATFORM_ORDER},
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
        }
        for s in scored
    ]


def datasets(snap, prod_cfg, scored, niches, today):
    return {
        "earnings_daily": earnings_daily_rows(snap),
        "platforms": platform_rows(snap),
        "videos": video_rows(snap),
        "credits": credit_rows(snap, prod_cfg, today),
        "niches": niche_rows(scored, niches),
        "programs": PROGRAMS,
    }
