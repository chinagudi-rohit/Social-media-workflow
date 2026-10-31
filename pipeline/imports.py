"""Per-post numbers the owner reads off YouTube Studio or Meta Business Suite, matched to the
runs they belong to (`python -m pipeline post-stats-import`). Metricool reports no
per-video YouTube views and fewer Meta fields, so these exports fill the gap.

One CSV row per post: `platform`, `title` as the export shows it (often cut short),
`published` (a local date, or date and time) and any of FIELDS. A row matches the post on
its platform whose titles share most of its words, among posts already out and published
within WINDOW_HOURS of its time (or on its date when it has no time); ties go to the
nearest time.
"""

import csv
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

FIELDS = {"views": int, "reach": int, "avg_view_seconds": float, "likes": int, "comments": int,
          "shares": int, "saves": int, "follows": int}
WINDOW_HOURS = 3


def words(text):
    return re.findall(r"[a-z0-9$]+", (text or "").lower())


def titles(run_dir):
    """The titles a run's posts went out under: YouTube's (Facebook shows it too), the
    caption's first line (Instagram's) and the on-screen hook."""
    run_dir = Path(run_dir)
    out = []
    for name, keys in (("captions.json", (("youtube", "title"), ("instagram", "caption"))),
                       ("script.json", (("youtube_title",), ("on_screen_hook",), ("hook",)))):
        try:
            data = json.loads((run_dir / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for path in keys:
            value = data
            for k in path:
                value = value.get(k) if isinstance(value, dict) else None
            if isinstance(value, str):
                out.append(value.split("\n")[0])
    return " ".join(out)


def score(title, text):
    """Share of the row title's words found in `text`; the last word may be cut short."""
    want, have = words(title), set(words(text))
    if not want:
        return 0.0
    hits = sum(1 for i, w in enumerate(want)
               if w in have or (i == len(want) - 1 and any(h.startswith(w) for h in have)))
    return hits / len(want)


def read(path):
    """CSV rows as {platform, title, published, fields}; blank cells are left out."""
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            fields = {}
            for name, kind in FIELDS.items():
                cell = (r.get(name) or "").replace(",", "").strip()
                if cell:
                    fields[name] = kind(float(cell))
            rows.append({"platform": r["platform"].strip().lower(), "title": r["title"].strip(),
                         "published": r["published"].strip(), "fields": fields})
    return rows


def match(rows, manifests, run_titles, tz_name, now):
    """([(run_id, platform, row)], [(row, reason)]): each row's post, or why it has none.
    A post matches one row at most."""
    tz = ZoneInfo(tz_name)
    taken, matched, unmatched = set(), [], []
    for row in rows:
        timed = len(row["published"]) > 10
        when = datetime.fromisoformat(row["published"]).replace(tzinfo=tz) if timed else None
        cands = []
        for m in manifests:
            post = (m.get("posts") or {}).get(row["platform"]) or {}
            if not post.get("at") or (m["run_id"], row["platform"]) in taken:
                continue
            at = datetime.fromisoformat(post["at"].replace("Z", "+00:00"))
            if at > now:
                continue
            gap = abs((at - when).total_seconds()) if timed else 0
            if (timed and gap > WINDOW_HOURS * 3600) or (not timed and str(at.astimezone(tz).date()) != row["published"]):
                continue
            cands.append((score(row["title"], run_titles.get(m["run_id"], "")), -gap, m["run_id"]))
        cands.sort(reverse=True)
        if not cands or cands[0][0] < 0.5:
            unmatched.append((row, "no post with that title at that time"))
        elif len(cands) > 1 and cands[1][:2] == cands[0][:2]:
            unmatched.append((row, f"ambiguous: {cands[0][2]} or {cands[1][2]}"))
        else:
            taken.add((cands[0][2], row["platform"]))
            matched.append((cands[0][2], row["platform"], row))
    return matched, unmatched


def record(post, fields, now, source):
    """The fields to merge into a post record, or None when it already holds newer numbers."""
    if post.get("stats_at") and datetime.fromisoformat(post["stats_at"]) > now:
        return None
    age = (now - datetime.fromisoformat(post["at"].replace("Z", "+00:00"))) / timedelta(hours=1)
    return {**fields, "status": "published", "views_age_hours": round(age, 1),
            "stats_at": now.isoformat(timespec="seconds"), "stats_source": source}
