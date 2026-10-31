---
name: go-live
description: First run after the owner has created and connected their accounts. Checks the Metricool and Higgsfield connectors, makes one test video, posts it to every target platform within the next half hour, confirms each post is live, switches the dashboard to live Metricool data and moves the daily schedule into this session. Use when the owner says their accounts are connected, asks for the test round, or types /go-live.
---

# go-live

Run from the repo root on branch `claude/compassionate-ptolemy-rf3q0u`. The owner asked for
this test round, so it may spend one video's credits (~32) and post publicly without a
further question. Stop and report at the first step that fails; never fake a result.

## 1. Connections

1. ToolSearch `metricool` and ToolSearch `higgsfield`. If either connector has no tools in
   this session, stop. Say which one is missing. The owner connects it at
   https://claude.ai/customize/connectors, then starts a new session (connectors load when
   a session starts).
2. Read the input schema of each Metricool tool the run uses: `getBrandSettings`,
   `createScheduledPost`, `getScheduledPosts`, `getBestTimeToPostByNetwork`,
   `getAnalyticsAvailableMetrics`, `getAnalyticsDataByMetrics`.
3. `getBrandSettings`: which networks are linked, and the brand's timezone. Every platform
   in `targets` (`config/platforms.yaml`) must be linked. If one is missing, list it with
   the place to link it (Metricool → brand → Connections) and go on with the linked ones.
   The brand timezone should be America/New_York. If it is not, say so; post times are
   always sent with an explicit timezone anyway.
4. Higgsfield `balance`. Stop if it is below 40 credits.

## 2. One test video

If a run already has a finished video and no posts (`python -m pipeline history`: status
`video_ready`, empty `posts`), use it and spend nothing. Otherwise follow
`.claude/skills/autopilot/SKILL.md` step 4 for one script from
`python -m pipeline library pick --count 1`. That covers keyframes, motion, voice,
`assets.json`, the render, the quality check, `set-video` and `captions`.

## 3. Post it everywhere, now

1. `python -m pipeline publish-plan RUN --asap`. Every target platform goes out
   `min_lead_minutes` from now.
2. For each entry, call `createScheduledPost` with the entry's `metricool` values unchanged
   (autopilot step 5). Then record it: `python -m pipeline record-post RUN --platform <p> --status scheduled
   --at <at> --id <id> --via metricool`.
3. Once the time has passed, call `getScheduledPosts` for today every few minutes, for up
   to 30 minutes. For each post, record `published` with its link, or `failed` with
   Metricool's reason.

## 4. Learn the account's post times

Autopilot step 1b.1: save `data/timing/<today>.json` from `getBestTimeToPostByNetwork`
and run `python -m pipeline timing validate`. A new account may have no activity data
yet. Then skip it; the research defaults stay in charge.

## 5. Dashboard on live data

1. Call `getAnalyticsAvailableMetrics`, then `getAnalyticsDataByMetrics` for followers and
   views per linked network.
2. Follow the dashboard type's `artifact-type/reference/sources.md`, section "Switching a
   file to live data", for `datasets/platforms` on https://claude.ai/artifact/WMZmvWFEeRZ3caLHidP6Xa:
   - a live query on the Metricool connector;
   - a `dash.loader` that returns the file's columns (`platform`, `account`, `followers`,
     `views`, `likes`, `comments`, `shares`, `earnings_30d`, `earnings_source`), with
     `account` "Connected" for linked networks;
   - the call stored exactly as it ran.
3. Do the same for YouTube revenue only if Metricool's metrics include it.
4. Run `python -m pipeline metrics collect --balance <credits>` and upload the changed
   files as autopilot step 6 does.

## 6. Daily schedule into this session

`list_triggers`: find "Daily shorts autopilot". It is bound to the session that built the
workflow, which cannot see Metricool. Delete it and create it again with no
`persistent_session_id`, so it fires into this session. Keep the same name, prompt and
cron (`CRON_TZ=America/New_York 54 7 * * *`).

## 7. Commit and report

Commit the run folder, `data/` and any changed files, then push. Report in five lines:

- the video;
- each platform's link or failure;
- credits spent;
- whether the dashboard reads live data;
- the next daily run time.
