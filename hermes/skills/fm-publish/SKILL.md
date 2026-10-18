---
name: fm-publish
description: Publishes the faceless autopilot's finished videos and closes the day. Refreshes post-time data, schedules each platform's post at its own best time through the Metricool MCP (or Upload-Post), records post results, pulls audience and revenue numbers into the earnings dashboard data, then commits and pushes. Use for a "Publish, earnings and dashboard <date>" kanban card, or when asked to post a finished run or refresh earnings.
version: 1.0.0
author: Faceless Monitisation
metadata:
  hermes:
    tags: [faceless, publishing, metricool, analytics, dashboard]
    requires_toolsets: [terminal]
---

# fm-publish

Metricool MCP tools carry the server prefix (for example
`mcp__metricool__createScheduledPost`). The ones this skill uses are
`getBestTimeToPostByNetwork`, `createScheduledPost`, `getScheduledPosts`,
`getAnalyticsDataByMetrics`, and the tool that lists brands. Read each tool's input schema
before its first call in a session. Never guess a parameter.

## When to Use
- A kanban card titled `Publish, earnings and dashboard <date>`.
- Someone asks to post a finished run, or to refresh earnings or the dashboard.

## Procedure

0. **Preflight.** `kanban_show()`. Take the date `D`. Videos to post: `metadata.videos` in
   the produce card's handoff, plus any run in `./fm history` that has a video and no
   `scheduled` or `published` post. Publisher order (`publisher` in
   `config/platforms.yaml`; `auto` takes the first one that is ready):
   - the Metricool tools are available → Metricool;
   - else `./fm check` shows `uploadpost` ready → Upload-Post;
   - else direct YouTube / Instagram where `./fm check` shows them.

   If none is ready and there are videos to post:
   `kanban_block(kind="needs_input", reason="no publisher signed in: hermes -p
   fm-publisher mcp login metricool")`.
1. **Metricool brand.** Read `metricool.brand_id` in `config/hermes.yaml`. If it is empty,
   list the brands. With exactly one brand, write its id into that field. With several,
   block with `needs_input` and list them by name so the owner can choose.
2. **Post-time data** (Metricool only).
   - Audience: if `data/timing/` has no file from the last 7 days, call
     `getBestTimeToPostByNetwork` for tiktok, instagram, youtube and facebook over the next
     7 days in `America/New_York`. Write `data/timing/D.json` as
     `{"date", "source": "metricool", "timezone": "America/New_York", "platforms":
     {<platform>: {"mon": {"<hour 0-23>": <activity>}, ...}}}` with the values it returns
     (any scale). `./fm timing validate` must print `ok`.
   - Results: for each run whose post on a platform went out 36-60 hours ago
     (`posts.<platform>.at` in its manifest), read that post's views
     (`getAnalyticsDataByMetrics`, or `getScheduledPosts` for its link) and run
     `./fm post-stats RUN --platform <p> --views <n>`.
3. **Publish**, only while `autopublish: true` in `config/platforms.yaml`. Each platform
   gets its own slot (`./fm timing plan` shows them).
   - Metricool: `./fm publish-plan RUN` writes `RUN/publish_plan.json`, one entry per
     platform with `local_time`, `timezone`, `video_url`, `text` (plus `title` and `tags`
     for YouTube and Facebook). For each entry, call `createScheduledPost` once, for that
     network only, at that time and timezone. Use the video URL as the media, the text as
     the post text, and the title where the network has one. Turn on every AI-generated /
     synthetic-content option the tool offers for that network. Where it offers none, add
     the entry's `ai_disclosure_fallback` as the last line of the text. Then run
     `./fm record-post RUN --platform <p> --status scheduled --at <entry.at> --id <post id>
     --via metricool`. If a network refuses, record it `failed` with the reason and go on.
   - Upload-Post: `./fm publish all RUN --schedule auto`.
   - Direct only: `./fm publish youtube RUN` / `./fm publish instagram RUN` post now.
     TikTok then has no unattended route: run `./fm record-post RUN --platform tiktok
     --status skipped --note "needs Metricool or Upload-Post"`.

   With `autopublish: false`, schedule nothing. List the runs awaiting approval in the
   summary instead.
4. **Post status.** Upload-Post runs from the last 3 days: `./fm publish-status RUN`.
   Metricool runs: `getScheduledPosts` for the same days. Record each post's state and link
   with `./fm record-post` (keep `--at`).
5. **Earnings and dashboard.**
   - From Metricool, read for each platform: followers, views, likes, comments, shares
     (last 30 days). Also read YouTube estimated revenue by day, and Facebook earnings by
     day where Metricool has them. Write `data/metricool/D.json`:
     `{"date": "D", "source": "metricool", "platforms": {<p>: {"followers": n, "views": n,
     ...}}, "youtube_revenue": [{"day": "YYYY-MM-DD", "estimatedRevenue": usd}],
     "facebook_earnings": [{"day", "earnings": usd}]}`. Include only numbers Metricool
     returned; leave a counter out rather than guess. `./fm metrics validate --date D` must
     print `ok`.
   - Balance: `higgsfield account status --json` → `credits`.
   - `./fm metrics collect --balance <credits> --date D`. The local dashboard
     (`./fm dashboard serve`) reads `data/dashboard/*.json` live, so there is nothing to
     upload.
6. **Commit and push.** `git add runs library data research pipeline/dashboard.py
   config/hermes.yaml`, then `git commit -m "Autopilot D: <n> videos, <credits> credits"`
   and `git push origin hermes/autopilot`. Retry network failures up to 4 times with
   backoff. Never add `.env`, `runs/*/final.mp4` or `runs/*/frames/`.
7. `kanban_complete(summary=<what was scheduled when, in ET>, metadata={"scheduled":
   {<run>: {<platform>: "<ISO time>"}}, "failed": {...}, "earnings_30d": <total>,
   "balance": <credits>, "commit": "<sha>"})`.

## Pitfalls
- One `createScheduledPost` per network per video. Never post all four platforms in one
  call: each platform has its own best time.
- The Metricool Free plan schedules only 20 posts a month. If scheduling is refused for
  plan limits, block with `needs_input` and say so.
- TikTok Creator Rewards and affiliate payouts have no feed. They arrive through
  `./fm earnings add` (fm-lead logs them when the owner reports a payout).

## Verification
Every new run's manifest shows a `scheduled` (or `failed` / `skipped` with a note) post for
each platform, `./fm metrics collect` printed its snapshot, and `git log -1` shows the
commit.
