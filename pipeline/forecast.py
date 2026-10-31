"""The dashboard's Prediction card: days until each payout program unlocks and until total
ad earnings pass each milestone (config/forecast.yaml).

It starts from each platform's current pace and its growth history: a weighted fit of log
daily views over every day on record, blended with a prior that fades as history builds.
Projected daily views grow at that weekly rate, slowing as the channel matures; followers
grow with views. A program unlocks when followers and the rolling views (or watch minutes)
meet its rule on that day; ad earnings start `review_days` later at the scenario's RPM.
Three scenarios give the range.
"""

import math
from collections import deque
from datetime import date, timedelta

SCENARIOS = ("cautious", "expected", "strong")


def history(stats_files):
    """Every platform's daily rows merged across stats files, oldest file first: a later
    file's value wins for a day, but a null never erases a known one."""
    days = {}
    for stats in stats_files:
        for platform, counters in (stats or {}).items():
            for r in (counters or {}).get("daily") or []:
                known = days.setdefault(platform, {}).get(r["day"], {})
                days[platform][r["day"]] = {
                    "day": r["day"],
                    "followers": r.get("followers") if r.get("followers") is not None else known.get("followers"),
                    "views": r.get("views") if r.get("views") is not None else known.get("views")}
    return {p: sorted(d.values(), key=lambda r: r["day"]) for p, d in days.items()}


def clean(daily, today):
    """Complete days before `today`, oldest first, with followers carried forward."""
    rows, last = [], None
    for r in sorted(daily or [], key=lambda r: r["day"]):
        if r["day"] >= str(today):
            continue
        last = r["followers"] if r.get("followers") is not None else last
        rows.append({"day": r["day"], "followers": last, "views": r.get("views")})
    return rows


def fit_growth(seen, half_life):
    """Weekly growth of daily views from a weighted least-squares line through log(1 + views)
    over every day with views; recent days weigh more. None below two distinct days."""
    if len(seen) < 2:
        return None
    first = date.fromisoformat(seen[0]["day"])
    xs = [(date.fromisoformat(r["day"]) - first).days for r in seen]
    ys = [math.log1p(max(0.0, float(r["views"]))) for r in seen]
    ws = [0.5 ** ((xs[-1] - x) / half_life) for x in xs]
    total = sum(ws)
    mx = sum(w * x for w, x in zip(ws, xs)) / total
    my = sum(w * y for w, y in zip(ws, ys)) / total
    var = sum(w * (x - mx) ** 2 for w, x in zip(ws, xs))
    if var == 0:
        return None
    slope = sum(w * (x - mx) * (y - my) for w, x, y in zip(ws, xs, ys)) / var
    return math.exp(7 * slope) - 1


def pace(daily, followers, cfg, platform, proxy_views=None, period=None):
    """Current views a day, weekly growth and followers per 1,000 views, each with what it
    rests on and how much of it comes from this platform's own history (its weight).
    `period` is a total over a span of days read elsewhere (YouTube Studio's views while
    Metricool reports none): {"from", "to", "views", "source"}; daily views win over it."""
    g = cfg["growth"]
    seen = [r for r in daily if r["views"] is not None]
    recent = seen[-cfg["recent_days"]:]
    out = {"days": len(seen), "followers": followers, "views_per_day": None, "views_basis": "no data", "views_source": None,
           "weekly_growth": g["assumed"], "growth_measured": None, "growth_weight": 0.0, "growth_basis": "assumed",
           "followers_per_1k": cfg["followers_per_1k"].get(platform, 1.0), "followers_measured": None,
           "followers_weight": 0.0, "followers_basis": "assumed"}
    span = (date.fromisoformat(period["to"]) - date.fromisoformat(period["from"])).days + 1 if period else 0
    if recent and sum(r["views"] for r in recent) > 0:
        out["views_per_day"], out["views_basis"] = sum(r["views"] for r in recent) / len(recent), "measured"
    elif span > 0 and (period.get("views") or 0) > 0:
        out.update(views_per_day=period["views"] / span, views_basis="period", views_source=period.get("source"))
    elif proxy_views is not None:
        out["views_per_day"], out["views_basis"] = proxy_views, "proxy"
    if len(seen) >= g["min_days"]:
        measured = fit_growth(seen, g["fit_half_life_days"])
        if measured is not None:
            measured = min(g["max"], max(g["min"], measured))
            w = len(seen) / (len(seen) + g["prior_days"])
            out.update(growth_measured=measured, growth_weight=w, growth_basis="history",
                       weekly_growth=w * measured + (1 - w) * g["assumed"])
    known = [r for r in daily if r["followers"] is not None]
    if len(known) >= 2 and out["views_per_day"]:
        gained = known[-1]["followers"] - known[0]["followers"]
        later = [r for r in daily if known[0]["day"] < r["day"] <= known[-1]["day"]]
        own = sum(r["views"] or 0 for r in later)
        views = own if out["views_basis"] == "measured" and own > 0 else out["views_per_day"] * len(later)
        if gained and views > 0:
            measured = max(0.0, gained) / views * 1000
            w = abs(gained) / (abs(gained) + cfg["prior_followers"])
            out.update(followers_measured=measured, followers_weight=w, followers_basis="history",
                       followers_per_1k=w * measured + (1 - w) * out["followers_per_1k"])
    return out


def rule_on(prog, day):
    """The program's rule in force on `day` (later `from` dates override earlier ones)."""
    rule = {k: v for k, v in prog.items() if k != "from"}
    for start, change in sorted((prog.get("from") or {}).items()):
        if str(day) >= start:
            rule.update(change)
    return rule


def views_needed(rule):
    """Average views per day over the window that the rule asks for (0 when it has none)."""
    if rule.get("minutes"):
        return rule["minutes"] / rule["minutes_per_view"] / rule["window_days"]
    return rule.get("views", 0) / rule["window_days"]


def unlocked(rule, followers, window):
    if followers < rule.get("followers", 0):
        return False
    if rule.get("minutes"):
        return sum(window) * rule["minutes_per_view"] >= rule["minutes"]
    return sum(window) >= rule.get("views", 0)


def simulate(paces, past, cfg, today, scenario, path_days=0):
    """({platform: days until its program unlocks}, {milestone usd: days}, {platform: views a
    day for each of the next `path_days` days}) for one scenario; a missing key means not
    within `horizon_days`. `past` seeds each program's rolling window with real days."""
    s = cfg["scenarios"][scenario]
    g = cfg["growth"]
    state = {}
    for p, pc in paces.items():
        if pc["views_per_day"] is None:
            continue
        prog = cfg["programs"].get(p) or {}
        weekly = min(g["max"], max(g["min"], pc["weekly_growth"] + s["growth"]))
        win = prog.get("window_days", 90)
        state[p] = {"v": pc["views_per_day"], "f": float(pc["followers"] or 0), "fpk": pc["followers_per_1k"],
                    "r0": (1 + weekly) ** (1 / 7) - 1, "prog": prog,
                    "rpm": (prog.get("rpm_usd") or [0, 0, 0])[s["rpm"]],
                    "win": deque([r["views"] or 0 for r in past.get(p, [])][-win:], maxlen=win)}
    eligible, hits, path, total = {}, {}, {p: [] for p in state}, 0.0
    milestones = sorted(cfg["milestones_usd"])
    for t in range(1, cfg["horizon_days"] + 1):
        day = today + timedelta(days=t)
        decay = 0.5 ** (t / g["half_life_days"])
        for p, st in state.items():
            st["v"] *= 1 + st["r0"] * decay
            st["f"] += st["v"] * st["fpk"] / 1000
            st["win"].append(st["v"])
            if t <= path_days:
                path[p].append(st["v"])
            if st["prog"] and p not in eligible and unlocked(rule_on(st["prog"], day), st["f"], st["win"]):
                eligible[p] = t
            if p in eligible and t > eligible[p] + st["prog"].get("review_days", 0):
                total += st["v"] * st["rpm"] / 1000
        while len(hits) < len(milestones) and total >= milestones[len(hits)]:
            hits[milestones[len(hits)]] = t
        if t >= path_days and len(hits) == len(milestones) and all(p in eligible for p, st in state.items() if st["prog"]):
            break
    return eligible, hits, path


def rows(series, followers, cfg, today, platforms, periods=None):
    """Dataset rows: one `meta`; per platform one `pace`, a `history` row per day on record
    and a `path` row per projected day (expected case); one `program` per payout program;
    one `earnings` per milestone. `days` is the expected scenario, `days_low` the strong one
    and `days_high` the cautious one; None means beyond `horizon_days`."""
    past = {p: clean(series.get(p), today) for p in platforms}
    periods = periods or {}
    paces = {p: pace(past[p], followers.get(p), cfg, p, period=periods.get(p)) for p in platforms}
    measured = [pc["views_per_day"] for pc in paces.values() if pc["views_basis"] in ("measured", "period")]
    if measured:
        # No views reported yet (YouTube lags): borrow the other platforms' average pace.
        proxy = sum(measured) / len(measured)
        paces = {p: pc if pc["views_per_day"] is not None else pace(past[p], followers.get(p), cfg, p, proxy)
                 for p, pc in paces.items()}
    runs = {s: simulate(paces, past, cfg, today, s, cfg["path_days"] if s == "expected" else 0) for s in SCENARIOS}
    when = lambda d: None if d is None else str(today + timedelta(days=d))  # noqa: E731
    r = lambda v, n=3: None if v is None else round(v, n)  # noqa: E731
    g = cfg["growth"]
    out = [{"key": "meta", "kind": "meta", "date": str(today),
            "days_of_data": max((pc["days"] for pc in paces.values()), default=0),
            "growth_min_days": g["min_days"], "prior_growth": g["assumed"], "prior_days": g["prior_days"],
            "horizon_days": cfg["horizon_days"], "half_life_days": g["half_life_days"]}]
    for p in platforms:
        pc = paces[p]
        out.append({"key": f"pace:{p}", "kind": "pace", "platform": p, "days": pc["days"],
                    "views_per_day": None if pc["views_per_day"] is None else round(pc["views_per_day"]),
                    "views_basis": pc["views_basis"], "views_source": pc["views_source"],
                    "weekly_growth": r(pc["weekly_growth"]),
                    "growth_measured": r(pc["growth_measured"]), "growth_weight": r(pc["growth_weight"], 2),
                    "growth_basis": pc["growth_basis"], "followers": pc["followers"],
                    "followers_per_1k": r(pc["followers_per_1k"], 2), "followers_measured": r(pc["followers_measured"], 2),
                    "followers_weight": r(pc["followers_weight"], 2), "followers_basis": pc["followers_basis"]})
        out += [{"key": f"history:{p}:{d['day']}", "kind": "history", "platform": p, "date": d["day"],
                 "views": d["views"], "followers": d["followers"]} for d in past[p]]
        out += [{"key": f"path:{p}:{t + 1}", "kind": "path", "platform": p, "date": when(t + 1), "views": round(v)}
                for t, v in enumerate(runs["expected"][2].get(p, []))]
    for p in platforms:
        prog = cfg["programs"].get(p)
        if not prog:
            continue
        days = runs["expected"][0].get(p)
        rule = rule_on(prog, today + timedelta(days=days if days is not None else cfg["horizon_days"]))
        out.append({"key": f"program:{p}", "kind": "program", "platform": p, "label": prog["name"],
                    "pays": bool(prog.get("rpm_usd") and prog["rpm_usd"][1] > 0), "rpm_usd": prog.get("rpm_usd"),
                    "days": days, "date": when(days),
                    "days_low": runs["strong"][0].get(p), "days_high": runs["cautious"][0].get(p),
                    "followers_needed": rule.get("followers", 0),
                    "views_per_day_needed": round(views_needed(rule))})
    for usd in sorted(cfg["milestones_usd"]):
        days = runs["expected"][1].get(usd)
        out.append({"key": f"usd:{usd}", "kind": "earnings", "label": f"${usd:,} earned in total", "usd": usd,
                    "days": days, "date": when(days),
                    "days_low": runs["strong"][1].get(usd), "days_high": runs["cautious"][1].get(usd)})
    return out
