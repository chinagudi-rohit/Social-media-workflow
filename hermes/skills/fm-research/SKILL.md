---
name: fm-research
description: Daily research refresh for the faceless short-video autopilot. Searches what US audiences want this week in each niche, scores trend boost and saturation, records monetization-program and policy changes, then writes and validates data/trends/<date>.json. Use for a "Research refresh <date>" kanban card, or when asked to refresh niche or monetization research.
version: 1.0.0
author: Faceless Monitisation
metadata:
  hermes:
    tags: [faceless, research, trends, monetization]
    requires_toolsets: [terminal]
---

# fm-research

Runs before anything is chosen, every day. Scripts and production read your snapshot, so
the day's videos are only as good as this research.

## When to Use
- A kanban card titled `Research refresh <date>`.
- Someone asks to refresh trends, niche scores or monetization rules.

## Procedure

1. `kanban_show()`. Take the date `D` from the card title (US Eastern).
2. `./fm trends template --date D`. If it says the file already exists, an earlier attempt
   started it: keep editing `data/trends/D.json`, do not delete it.
3. Read `config/niches.yaml` (ids, names, angles, monetization notes).
4. **Niche pass.** For every niche, search for what US audiences are searching or talking
   about this week: news, rule or rate changes, product launches, and seasonal hooks
   (tax season Jan-Apr, open enrollment Nov 1-Jan 15, Medicare enrollment Oct 15-Dec 7,
   Q4 shopping, back to school, New Year resolutions). Use `web_search`, plus `x_search`
   for what is trending on X. Send searches in parallel batches of 4-6, about one per
   niche. Then fill each niche in the snapshot:
   - `trend_boost` 0-3: 0 nothing new; 1 seasonal relevance or steady interest; 2 a clear
     news hook this week; 3 a major event with heavy search interest.
   - `saturation` 0-1: how much of the hot angle big creators already cover.
   - `signals`: one line each, ending with the source URL.
   - `topic_ideas` (only when `trend_boost` >= 2, at most 2):
     `{"topic", "angle", "why_now", "sources": ["https://..."]}`. The angle must suit a
     sourced, faceless explainer: no advice tailored to the viewer, no promises of returns.
5. **Policy pass.** Search the last 7 days for changes to YouTube Partner Program / Shorts
   monetization, TikTok Creator Rewards, Facebook Content Monetization and Instagram
   originality or AI-label rules. Record them in `program_changes` / `policy_notes`, each
   with its source. If a payout rule changed:
   - update `PROGRAMS` in `pipeline/dashboard.py`;
   - add a dated line to `research/monetization-2026.md`;
   - run `.venv/bin/python -m pytest -q`.
6. `./fm trends validate --date D` must print `ok`. Fix the file and repeat until it does.
7. `./fm trends score` and read the ranking.
8. `kanban_complete(summary=<2-3 lines>, metadata={"snapshot": "data/trends/D.json",
   "top_niches": [{"id", "score"} for the top 4], "topic_ideas": [{"niche", "topic",
   "trend_boost"}], "program_changes": [...]})`.

## Pitfalls
- Never invent a source. Every signal and idea carries a URL from an actual search result
  or page you opened.
- Stay near 12 niche searches plus 4 policy searches. Depth on the top niches beats
  breadth.
- If search is unavailable, keep the template's zeros, say so in the summary and complete.
  Scoring then rests on the RPM and reach tiers.
- Do not touch `library/` or `runs/`. That is the writer's stage.

## Verification
`./fm trends validate --date D` prints `ok`, and `./fm trends score` lists every niche.
