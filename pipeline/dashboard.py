"""Dataset files for the Creator Earnings dashboard (one JSON array of rows each).

The autopilot writes these to data/dashboard/ every day and uploads the ones that changed
to the dashboard, which reads them as its sources.
"""

from . import expenses
from .budget import days_left, video_cost

PROGRAMS = [
    # Monetization program entry bars (research/monetization-2026.md). Updated when the
    # daily research finds a rule change.
    {"platform": "youtube", "program": "YouTube Partner Program (Shorts)", "followers_needed": 1000,
     "views_needed": 10_000_000, "views_window_days": 90,
     "rule": "1,000 subscribers + 10M Shorts views in 90 days (or 4,000 watch hours)"},
    {"platform": "facebook", "program": "Content Monetization", "followers_needed": 5000,
     "views_needed": 600_000, "views_window_days": 60,
     "rule": "Invite-based; on the waitlist since 2026-10-21. Meta benchmarks average watch time "
             "(ours 8.1 s, similar earners 15.4 s); reported 5-10k followers and 60k-600k watch minutes in 60 days"},
    {"platform": "twitter", "program": "X Original Content Rewards", "followers_needed": 500,
     "views_needed": 500_000, "views_window_days": 90,
     "rule": "X Premium + 500 verified followers + 500k Home timeline views from verified users in 90 days; "
             "pays on Premium users' views of original posts"},
    {"platform": "instagram", "program": "Gifts, then Creator Marketplace and Subscriptions", "followers_needed": 500,
     "views_needed": 0, "views_window_days": 30,
     "rule": "No pay per view. Gifts (Stars, $0.01 each) at 500 followers, India eligible; Creator Marketplace "
             "brand deals from 1,000; Subscriptions at 10,000; cross-posted Reels count toward Facebook"},
]

PLATFORM_ORDER = ("youtube", "instagram", "facebook", "twitter")


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


def not_earning_label(platform, stats, ladder):
    """What a platform without an earnings feed is waiting for: its next paid step."""
    for step in (ladder or {}).get(platform, []):
        if step.get("owner") and step.get("name") and (stats.get(step["metric"]) or 0) < step["at"]:
            unit = "views in 90 days" if step["metric"] == "views_90d" else (
                "subscribers" if platform == "youtube" else "followers")
            return f"Not earning yet · {step['name']} at {step['at']:,} {unit}"
    return "Not earning yet"


def platform_rows(snap, targets=None, ladder=None):
    """Every platform, signed in or not, with its audience counters and earnings source.

    `linked` in the snapshot lists networks connected through Metricool (getBrandSettings).
    A platform with no earnings feed shows its next paid step from `ladder`
    (config/monetization.yaml): there is no revenue to read until that step."""
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
            "earnings_source": snap.get("earnings_sources", {}).get(platform)
            or not_earning_label(platform, {**stats, "views_90d": stats.get("views_90d", stats.get("views"))}, ladder),
        })
    return rows


def post_time_rows(plan, tz_name="America/New_York", owner_tz=None, owner_label=None):
    """Next post time per platform from `timing.plan`, with what it rests on. Slots are
    chosen in US Eastern (`day`, `time`); `local_day` and `local_time` are the same moment
    in the owner's time zone."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    rows = []
    for platform in PLATFORM_ORDER:
        entry = plan.get(platform)
        if not entry:
            continue
        moment = datetime.fromisoformat(entry["at"])
        at = moment.astimezone(ZoneInfo(tz_name))
        local = moment.astimezone(ZoneInfo(owner_tz or tz_name))
        rows.append({
            "platform": platform,
            "at": entry["at"],
            "day": at.strftime("%a %b %-d"),
            "time": at.strftime("%-I:%M %p ") + at.tzname(),
            "local_day": local.strftime("%a %b %-d"),
            "local_time": local.strftime("%-I:%M %p ") + (owner_label or local.tzname()),
            "basis": " + ".join(b[0].upper() + b[1:] for b in entry["basis"]),
        })
    return rows


def video_rows(snap, targets=None):
    """One row per run; a run shelved on purpose (a test or a draft, `shelved` in its manifest)
    reads "shelved" on every platform it never went to, not "not posted"."""
    rows = []
    for v in sorted(snap.get("videos", []), key=lambda v: v["date"], reverse=True):
        posts = v.get("posts", {})
        missing = "shelved" if v.get("shelved") else "not posted"
        rows.append({
            "run_id": v["run_id"],
            "date": v["date"],
            "niche": v["niche"],
            "topic": v["topic"],
            "credits": v.get("credits"),
            **{p: (posts.get(p) or {}).get("status") or missing for p in _order(targets)},
        })
    return rows


def credit_rows(snap, prod_cfg, today):
    tier = prod_cfg["tiers"][prod_cfg["tier"]]
    cost = video_cost(tier, 170, 8)
    balance = snap.get("credits", {}).get("balance")
    reserve = prod_cfg["plan"]["reserve_credits"]
    # Runway (music library, the odd Gen-4.5 opening shot): balance from `whoami`.
    rw, rcfg = snap.get("runway") or {}, prod_cfg.get("runway") or {}
    hero = rcfg.get("hero_shot") or {}
    rw_balance = rw.get("balance")
    return [{
        "date": str(today),
        "plan": prod_cfg["plan"]["name"],
        "monthly_credits": prod_cfg["plan"]["monthly_credits"],
        "balance": balance,
        "spent_30d": snap.get("credits", {}).get("spent_30d", 0),
        "tier": prod_cfg["tier"],
        "cost_per_video": cost,
        "videos_left": None if balance is None else max(0, int((balance - reserve) // cost)),
        "days_to_renewal": days_left(today, prod_cfg["plan"]),
        "runway_balance": rw_balance,
        "runway_plan_credits": rcfg.get("plan_credits"),
        "runway_used": None if rw.get("plan_left") is None or not rcfg else rcfg["plan_credits"] - rw["plan_left"],
        "hero_shots_left": None if rw_balance is None or not hero
        else max(0, int((rw_balance - hero["min_balance"]) // hero["credits"])),
        "music_beds": len((prod_cfg.get("render", {}).get("audio") or {}).get("music") or {}),
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
    labels = {"niche": "Niche", "format": "Format", "structure": "Structure", "voice": "Voice", "hour": "Post time (ET)",
              "length": "Length"}
    rows = [{"key": f"{r['dimension']}:{r['value']}", "dimension": labels[r["dimension"]],
             "value": names.get(r["value"], r["value"]) if r["dimension"] == "niche" else r["value"],
             "videos": r["videos"], "views_per_hour": r["views_per_hour"], "retention": r["retention"],
             "lift": r["lift"]} for r in summary]
    return rows or [{"key": "none", "dimension": "Waiting for data", "value": "Needs 3 videos with 2-day stats",
                     "videos": 0, "views_per_hour": None, "retention": None, "lift": 0.0}]


def locale_rows(locale):
    """The owner's time zone and currency, and the rate the page converts USD amounts at."""
    return [{k: locale.get(k) for k in ("timezone", "zone_label", "currency", "usd_rate", "rate_date")}]


def datasets(snap, prod_cfg, scored, niches, today, plan=None, tz_name="America/New_York", targets=None,
             ladder=None, locale=None, ledger=()):
    """Every dataset file; `targets` limits the per-platform ones to the platforms in use,
    `ladder` (config/monetization.yaml) names each unpaid platform's next paid step, and
    `locale` (config/dashboard.yaml) with the spend `ledger` adds the owner's currency,
    time zone and spending."""
    files = {
        "earnings_daily": earnings_daily_rows(snap, targets),
        "platforms": platform_rows(snap, targets, ladder),
        "post_times": post_time_rows(plan or {}, tz_name, (locale or {}).get("timezone"),
                                     (locale or {}).get("zone_label")),
        "videos": video_rows(snap, targets),
        "credits": credit_rows(snap, prod_cfg, today),
        "niches": niche_rows(scored, niches),
        "programs": PROGRAMS,
    }
    if locale:
        files["locale"] = locale_rows(locale)
        files["expenses"] = expenses.rows(ledger, locale)
        files["spending"] = expenses.summary(ledger, locale, today, snap.get("earnings_total_30d", 0.0),
                                             [v["date"] for v in snap.get("videos", [])])
    return files
