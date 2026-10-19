"""Credit pacing: spread the Higgsfield balance evenly across the billing cycle."""

import math
from datetime import date


def days_until_renewal(today, renews_on_day):
    """Days left in the cycle, counting today (>= 1)."""
    if today.day < renews_on_day:
        nxt = date(today.year, today.month, min(renews_on_day, 28))
    else:
        year, month = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
        nxt = date(year, month, min(renews_on_day, 28))
    return max(1, (nxt - today).days)


def video_cost(tier, words, blocks):
    motion_blocks = blocks if tier["motion"]["blocks"] == "all" else len(tier["motion"]["blocks"])
    return round(
        blocks * tier["keyframe"]["credits"]
        + motion_blocks * tier["motion"]["credits"]
        + words / 100 * tier["voice"]["credits_per_100_words"],
        2,
    )


def videos_today(balance, cost, reserve, days_left, days_since_last, max_per_day):
    """How many videos to make today without running out before the credits renew.

    Affordable videos are spaced evenly over the days left: daily when the budget covers
    every day, otherwise every Nth day based on when the last video was made.
    """
    affordable = math.floor((balance - reserve) / cost) if cost > 0 else 0
    if affordable <= 0:
        return 0
    interval = days_left / affordable
    if interval <= 1:
        return min(max_per_day, max(1, affordable // days_left))
    if days_since_last is None or days_since_last >= math.floor(interval):
        return 1
    return 0


def plan_today(prod_cfg, balance, today, days_since_last, words=170, blocks=8):
    tier_name = prod_cfg["tier"]
    tier = prod_cfg["tiers"][tier_name]
    # A shot-list tier pays per picture, not per block: it states its typical video.
    typical = tier.get("typical") or {}
    cost = video_cost(tier, typical.get("words", words), typical.get("pictures", blocks))
    days_left = days_until_renewal(today, prod_cfg["plan"]["renews_on_day"])
    n = videos_today(balance, cost, prod_cfg["plan"]["reserve_credits"], days_left,
                     days_since_last, prod_cfg["cadence"]["max_videos_per_day"])
    return {
        "tier": tier_name,
        "est_cost_per_video": cost,
        "balance": balance,
        "reserve": prod_cfg["plan"]["reserve_credits"],
        "days_left_in_cycle": days_left,
        "videos_today": n,
        "est_videos_left_this_cycle": max(0, math.floor((balance - prod_cfg["plan"]["reserve_credits"]) / cost)),
    }
