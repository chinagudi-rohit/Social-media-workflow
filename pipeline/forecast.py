"""The dashboard's Prediction card: days until each payout program unlocks and until total
ad earnings pass each milestone (config/forecast.yaml).

Each platform's daily views grow from today's pace at a weekly rate that halves every
`half_life_days`; followers grow with views. A program unlocks when followers and the
rolling views (or watch minutes) meet its rule on that day; ad earnings start
`review_days` later at the scenario's RPM. Three scenarios give the range.
"""

from collections import deque
from datetime import timedelta

SCENARIOS = ("cautious", "expected", "strong")


def clean(daily, today):
    """Complete days before `today`, oldest first, with followers carried forward."""
    rows, last = [], None
    for r in sorted(daily or [], key=lambda r: r["day"]):
        if r["day"] >= str(today):
            continue
        last = r["followers"] if r.get("followers") is not None else last
        rows.append({"day": r["day"], "followers": last, "views": r.get("views")})
    return rows


def pace(daily, followers, cfg, platform):
    """Today's views per day, weekly growth and followers per 1,000 views, each with what
    it rests on: "measured" from the daily series, else "assumed" from config."""
    seen = [r for r in daily if r["views"] is not None]
    recent = seen[-cfg["window_days"]:]
    views = sum(r["views"] for r in recent)
    g = cfg["growth"]
    out = {"days": len(seen), "views_per_day": None, "views_basis": "no data",
           "weekly_growth": g["assumed"], "growth_basis": "assumed",
           "followers": followers, "followers_per_1k": cfg["followers_per_1k"].get(platform, 1.0),
           "followers_basis": "assumed"}
    if len(seen) >= cfg["min_days"] and views > 0:
        out["views_per_day"], out["views_basis"] = views / len(recent), "measured"
    if len(seen) >= cfg["growth_days"]:
        last = sum(r["views"] for r in seen[-7:]) / 7
        prev = sum(r["views"] for r in seen[-14:-7]) / 7
        if prev > 0:
            out["weekly_growth"] = min(g["max"], max(g["min"], last / prev - 1))
            out["growth_basis"] = "measured"
    known = [r for r in recent if r["followers"] is not None]
    if len(known) >= 2:
        gained = known[-1]["followers"] - known[0]["followers"]
        after = sum(r["views"] for r in recent if r["day"] > known[0]["day"])
        if gained >= cfg["min_followers"] and after > 0:
            out["followers_per_1k"], out["followers_basis"] = gained / after * 1000, "measured"
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


def simulate(paces, history, cfg, today, scenario):
    """({platform: days until its program unlocks}, {milestone usd: days}) for one scenario;
    a missing key means not within `horizon_days`."""
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
                    "win": deque([r["views"] or 0 for r in history.get(p, [])][-win:], maxlen=win)}
    eligible, hits, total = {}, {}, 0.0
    milestones = sorted(cfg["milestones_usd"])
    for t in range(1, cfg["horizon_days"] + 1):
        day = today + timedelta(days=t)
        decay = 0.5 ** (t / g["half_life_days"])
        for p, st in state.items():
            st["v"] *= 1 + st["r0"] * decay
            st["f"] += st["v"] * st["fpk"] / 1000
            st["win"].append(st["v"])
            if st["prog"] and p not in eligible and unlocked(rule_on(st["prog"], day), st["f"], st["win"]):
                eligible[p] = t
            if p in eligible and t > eligible[p] + st["prog"].get("review_days", 0):
                total += st["v"] * st["rpm"] / 1000
        while len(hits) < len(milestones) and total >= milestones[len(hits)]:
            hits[milestones[len(hits)]] = t
        if len(hits) == len(milestones) and all(p in eligible for p, st in state.items() if st["prog"]):
            break
    return eligible, hits


def rows(series, followers, cfg, today, platforms):
    """Dataset rows: one `meta`, one `pace` per platform, one `program` per payout program,
    one `earnings` per milestone. `days` is the expected scenario; `days_low` the strong one
    and `days_high` the cautious one; None means beyond `horizon_days`."""
    history = {p: clean(series.get(p), today) for p in platforms}
    paces = {p: pace(history[p], followers.get(p), cfg, p) for p in platforms}
    measured = [pc["views_per_day"] for pc in paces.values() if pc["views_basis"] == "measured"]
    for pc in paces.values():
        if pc["views_per_day"] is None and measured:
            # No views reported yet (YouTube lags): borrow the other platforms' average pace.
            pc["views_per_day"], pc["views_basis"] = sum(measured) / len(measured), "proxy"
    runs = {s: simulate(paces, history, cfg, today, s) for s in SCENARIOS}
    when = lambda d: None if d is None else str(today + timedelta(days=d))  # noqa: E731
    out = [{"key": "meta", "kind": "meta", "date": str(today), "days_of_data": max((pc["days"] for pc in paces.values()), default=0),
            "growth_days": cfg["growth_days"], "horizon_days": cfg["horizon_days"],
            "half_life_days": cfg["growth"]["half_life_days"]}]
    for p in platforms:
        pc = paces[p]
        out.append({"key": f"pace:{p}", "kind": "pace", "platform": p,
                    "views_per_day": None if pc["views_per_day"] is None else round(pc["views_per_day"]),
                    "views_basis": pc["views_basis"], "weekly_growth": round(pc["weekly_growth"], 3),
                    "growth_basis": pc["growth_basis"], "followers": pc["followers"],
                    "followers_per_1k": round(pc["followers_per_1k"], 2), "followers_basis": pc["followers_basis"]})
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
        out.append({"key": f"usd:{usd}", "kind": "earnings", "usd": usd, "days": days, "date": when(days),
                    "days_low": runs["strong"][1].get(usd), "days_high": runs["cautious"][1].get(usd)})
    return out
