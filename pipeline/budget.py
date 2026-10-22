"""Credit pacing: spread the Higgsfield balance evenly across the window it must last."""

import math
from datetime import date, timedelta


def days_until_renewal(today, renews_on_day):
    """Days left in the cycle, counting today (>= 1)."""
    if today.day < renews_on_day:
        nxt = date(today.year, today.month, min(renews_on_day, 28))
    else:
        year, month = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
        nxt = date(year, month, min(renews_on_day, 28))
    return max(1, (nxt - today).days)


def days_left(today, plan):
    """Days left in the window the balance must last, counting today (>= 1). With a `quota`
    the owner's windows apply: `first_days` from `start`, then `then_days` each. Without
    one, the billing cycle does."""
    quota = plan.get("quota")
    if not quota:
        return days_until_renewal(today, plan["renews_on_day"])
    end = date.fromisoformat(str(quota["start"])) + timedelta(days=quota["first_days"])
    while end <= today:
        end += timedelta(days=quota["then_days"])
    return (end - today).days


def video_cost(tier, words, blocks, clip_seconds=None):
    """A video's credits: `blocks` pictures, its motion, its voice. A tier priced per clip
    second (the H3 tier) pays for `clip_seconds`, else the narration's length."""
    motion = tier["motion"]
    if motion.get("credits_per_second"):
        seconds = clip_seconds or words / motion.get("words_per_second", 2.8)
        moving = seconds * motion["credits_per_second"]
    else:
        moving = (blocks if motion["blocks"] == "all" else len(motion["blocks"])) * motion["credits"]
    return round(blocks * tier["keyframe"]["credits"] + moving + words / 100 * tier["voice"]["credits_per_100_words"], 2)


def videos_today(balance, cost, reserve, days_left, days_since_last, max_per_day):
    """How many videos to make today without running out before the window ends.

    Affordable videos are spaced evenly over the days left: daily when the budget covers
    every day (rounded up, so the spare ones come early and teach sooner), otherwise every
    Nth day based on when the last video was made.
    """
    affordable = math.floor((balance - reserve) / cost) if cost > 0 else 0
    if affordable <= 0:
        return 0
    interval = days_left / affordable
    if interval <= 1:
        return min(max_per_day, math.ceil(affordable / days_left))
    if days_since_last is None or days_since_last >= math.floor(interval):
        return 1
    return 0


def plan_today(prod_cfg, balance, today, days_since_last, words=170, blocks=8):
    tier_name = prod_cfg["tier"]
    tier = prod_cfg["tiers"][tier_name]
    # A shot-list tier pays per picture, not per block: it states its typical video.
    typical = tier.get("typical") or {}
    cost = video_cost(tier, typical.get("words", words), typical.get("pictures", blocks), typical.get("clip_seconds"))
    left = days_left(today, prod_cfg["plan"])
    n = videos_today(balance, cost, prod_cfg["plan"]["reserve_credits"], left,
                     days_since_last, prod_cfg["cadence"]["max_videos_per_day"])
    return {
        "tier": tier_name,
        "est_cost_per_video": cost,
        "balance": balance,
        "reserve": prod_cfg["plan"]["reserve_credits"],
        "days_left_in_window": left,
        "videos_today": n,
        "est_videos_left_this_window": max(0, math.floor((balance - prod_cfg["plan"]["reserve_credits"]) / cost)),
    }
