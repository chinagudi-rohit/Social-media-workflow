"""Money spent running the channel: subscriptions and credit top-ups, one row per charge.

data/expenses.csv keeps each charge as billed (amount and currency) plus the rupees the card
was actually charged when the receipt or bank alert shows it. The Claude subscription is
left out (owner's choice, 2026-10-19). The dashboard shows spending in the owner's currency
(`locale` in config/dashboard.yaml); a charge with no billed local amount is converted at
`usd_rate` and marked as an estimate (card forex fees not included).
"""

import csv
from datetime import date, timedelta
from pathlib import Path

from .config import ROOT

LEDGER = ROOT / "data" / "expenses.csv"
FIELDS = ["date", "service", "item", "amount", "currency", "local_amount", "recurring", "source"]


def load(path=LEDGER):
    if not Path(path).exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r.get("date") and r.get("amount")]


def add(row, path=LEDGER):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in FIELDS})


def local_amount(row, locale):
    """(amount in the owner's currency, estimated?) for one charge."""
    if row.get("local_amount"):
        return round(float(row["local_amount"]), 2), False
    amount = float(row["amount"])
    if row["currency"] == locale["currency"]:
        return round(amount, 2), False
    if row["currency"] == "USD":
        return round(amount * locale["usd_rate"], 2), True
    raise ValueError(f"no rate for {row['currency']} -> {locale['currency']}")


def rows(ledger, locale):
    """Every charge, newest first, with its amount in the owner's currency."""
    out = []
    for r in sorted(ledger, key=lambda r: r["date"], reverse=True):
        amount, est = local_amount(r, locale)
        out.append({"key": f"{r['date']}:{r['service']}:{r['item']}", "date": r["date"], "service": r["service"],
                    "item": r["item"], "billed": f"{float(r['amount']):.2f} {r['currency']}",
                    "amount": amount, "estimated": est, "recurring": r.get("recurring") or "one-off"})
    return out


def summary(ledger, locale, today, earnings_usd_30d, video_dates):
    """This month's and the last 30 days' spend, the monthly run-rate of the subscriptions
    (each service's latest recurring charge, yearly ones spread over 12 months),
    spend per video made in the last 30 days, and 30-day earnings minus spend."""
    since = str(today - timedelta(days=29))
    month = str(today.replace(day=1))
    charged = [(r, *local_amount(r, locale)) for r in ledger]
    # No upper bound: a charge dated in the owner's zone can be a day ahead of `today`.
    in_month = sum(a for r, a, _ in charged if month <= r["date"])
    in_30d = sum(a for r, a, _ in charged if since <= r["date"])
    latest = {}
    for r, a, _ in sorted(charged, key=lambda c: c[0]["date"]):
        if r.get("recurring") in ("monthly", "yearly"):
            latest[r["service"]] = a if r["recurring"] == "monthly" else a / 12
    videos = sum(1 for d in video_dates if since <= d)
    earned = earnings_usd_30d * locale["usd_rate"]
    return [{
        "currency": locale["currency"],
        "month": today.strftime("%B %Y"),
        "spent_month": round(in_month, 2),
        "spent_30d": round(in_30d, 2),
        "run_rate": round(sum(latest.values()), 2),
        "services": len(latest),
        "videos_30d": videos,
        "per_video": round(in_30d / videos, 2) if videos else None,
        "earned_30d": round(earned, 2),
        "net_30d": round(earned - in_30d, 2),
        "estimated": any(e for r, _, e in charged if since <= r["date"]),
    }]


def default_today(locale):
    """Today in the owner's time zone."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo(locale["timezone"])).date() if locale.get("timezone") else date.today()
