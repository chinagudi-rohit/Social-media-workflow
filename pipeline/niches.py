"""Pick the next niche: weighted least-recently-used rotation over past runs."""

from datetime import datetime


def _parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def pick_niche(niches, manifests, now):
    """Return the niche that is most overdue.

    A niche never used comes first (in config order). Otherwise the score is
    days since last use times the niche's weight, highest wins.
    """
    last_used = {}
    for m in manifests:
        ts = _parse(m["created_at"])
        if m["niche_id"] not in last_used or ts > last_used[m["niche_id"]]:
            last_used[m["niche_id"]] = ts

    def score(niche):
        if niche["id"] not in last_used:
            return float("inf")
        days = (now - last_used[niche["id"]]).total_seconds() / 86400
        return days * niche.get("weight", 1)

    # max() keeps the first of equal scores, so config order breaks ties.
    return max(niches, key=score)


def recent_topics(manifests, niche_id, limit=10):
    """Topics already covered in this niche, newest first, so scripts don't repeat."""
    runs = [m for m in manifests if m["niche_id"] == niche_id]
    runs.sort(key=lambda m: m["created_at"], reverse=True)
    return [m["topic"] for m in runs[:limit]]
