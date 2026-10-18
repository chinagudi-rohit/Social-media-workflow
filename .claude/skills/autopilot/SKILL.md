---
name: autopilot
description: Daily money-making run for the faceless short-video channels. Refreshes niche and monetization research, decides how many videos the Higgsfield credits allow today, produces them (keyframes, animated moments, voiceover, captions) through the Higgsfield MCP, schedules each platform's post at its best time through Metricool (or Upload-Post), collects earnings and post results, refreshes the Creator Earnings dashboard and commits everything. Use when asked to run the autopilot, the daily run, or the scheduled task fires.
---

# autopilot

Run from the repo root. Work through the steps in order. Each step lists what to do when it
fails; never stop silently and never skip the final report. The owner asked for full
automation, so this run spends credits within the budget below and posts without asking
when `autopublish: true` in `config/platforms.yaml`. When a person is chatting in this
session, still do it the same way; they can interrupt.

Hard limits:
- Never spend more Higgsfield credits than step 2 allows (+20% for retries). Never use
  `use_unlim` or `use_free_gens` unless the owner asked in this conversation.
- Every published video is a library or freshly written script that passes
  `python -m pipeline library validate` (or `validate RUN`).
- Every post carries the AI-generated label (Upload-Post fields are set by the CLI).
- Facts need sources. No personalised advice, no on-camera persona.

## 0. Preflight (run together)

- `git checkout claude/compassionate-ptolemy-rf3q0u && git pull --ff-only origin
  claude/compassionate-ptolemy-rf3q0u`. A scheduled run may start in a fresh container;
  everything it needs (runs, library, data, config) is in that branch.
- `pip install -q -r requirements.txt` if `python -c "import yaml, requests"` fails.
- `python -m pipeline check`: which publishing/analytics credentials exist.
- Higgsfield `balance`: note `credits`.
- ToolSearch `metricool`: are the Metricool connector's tools here
  (`createScheduledPost`, `getBestTimeToPostByNetwork`, `getAnalyticsDataByMetrics`, ...)?
  Read each one's input schema before its first call in the session.

Publisher (`publisher` in `config/platforms.yaml`; `auto` takes the first that is ready):
Metricool tools present → `metricool`; else `uploadpost` ready in `check` → `uploadpost`;
else direct YouTube/Instagram where `check` shows them. If Higgsfield tools are missing,
report "Higgsfield connector not available in this session" and jump to step 6. If no
publisher is ready, produce nothing (step 2 = 0) and report: "Sign in on the dashboard's
Accounts card (Metricool), or add Upload-Post keys".

## 1. Research refresh (before anything is chosen)

1. `python -m pipeline trends template` creates `data/trends/<today>.json` (skip if it
   exists from an earlier run today).
2. For each niche in `config/niches.yaml`, run one standard WebSearch for what US audiences
   are searching or talking about this week in that niche (news, seasonal hooks such as tax
   season, open enrollment, Q4 shopping, rate changes, launches). Send the searches in
   parallel batches. Then score:
   - `trend_boost` 0-3: 0 nothing new; 1 seasonal relevance or steady interest; 2 a clear
     news hook this week; 3 a major event with heavy search interest.
   - `saturation` 0-1: how much of the hot angle is already covered by big creators.
   - `signals`: one line each, with the source.
   - `topic_ideas`: up to 2 per niche when boost >= 2, each `{topic, angle, why_now, sources}`.
3. One more search pass for program and policy changes in the last 7 days: YouTube Partner
   Program / Shorts monetization, Facebook Content Monetization,
   Instagram originality. Record findings in `program_changes` / `policy_notes`. If a
   payout rule changed, update `PROGRAMS` in `pipeline/dashboard.py` and add a dated line
   to `research/monetization-2026.md`.
4. `python -m pipeline trends validate` must print `ok`; fix and repeat.
5. `python -m pipeline trends score` shows today's ranking.

If search is unavailable, keep the template's zeros and continue; scoring then rests on
the RPM and reach tiers.

### 1b. Post-time data (Metricool only; skip otherwise)

1. Audience: if `data/timing/` has no file from the last 7 days, call
   `getBestTimeToPostByNetwork` for each platform in `targets` over the
   next 7 days in `America/New_York`. Write `data/timing/<today>.json` as
   `{"date", "source": "metricool", "timezone": "America/New_York",
   "platforms": {<platform>: {"mon": {"<hour 0-23>": <activity>}, ...}}}` using the values
   it returns (any scale), then `python -m pipeline timing validate` must print `ok`.
2. Results: for every run whose post on a platform went out 36-60 hours ago
   (`posts.<platform>.at` in its manifest), read that post's views from Metricool
   (`getAnalyticsDataByMetrics`, or `getScheduledPosts` for its link) and record them:
   `python -m pipeline post-stats RUN --platform <p> --views <n>`. These two inputs move
   future post times toward what works for this account (`config/timing.yaml`).

### 1c. Analyse how the videos did, and improve

Goal: more reach until a platform pays (strategy `phase: reach` in
`config/production.yaml`), then more revenue.

1. **Collect stats.** Metricool `getAnalyticsDataByMetrics` for the last 7 days, with
   these YouTube metrics:
   - `YTVP04` video id
   - `YTVP06` views
   - `YTVP08` average view duration
   - `YTVP09` likes
   - `YTVP11` comments
   - `YTVP12` shares

   Match each row to a run by `posts.youtube.id` in its manifest. For each post that went
   out 36-60 hours ago and has no `views_age_hours` yet:
   `python -m pipeline post-stats RUN --platform youtube --views N --avg-view-seconds S
   --likes L --comments C --shares H`.
   When Instagram, Facebook or X are linked, do the same with their posts metrics
   (`getAnalyticsAvailableMetrics` lists the field ids per network).
2. **Summarize.** `python -m pipeline insights` writes `data/insights/<today>.json` and
   prints what is working, by niche, structure, voice, post hour and length:
   - lift: views per hour against the channel median, shrunk while there are few videos;
   - retention: average view duration over length;
   - engagement.

   Niche lifts already feed the niche ranking, and niches with few videos get an explore
   bonus.
3. **Learn.** Read `data/insights/lessons.md`. Compare the best and worst videos so far:
   hook line, structure, topic, visuals, length, retention. Add or revise at most 3
   lessons, each dated and naming its evidence (run ids, numbers). Remove any lesson newer
   data contradicts. Keep the file under 40 lines.
4. **Apply.** Every script written today follows `lessons.md`. In the reach phase:
   - favor hooks that stop the scroll in the first second;
   - favor topics with broad US appeal;
   - write shorter scripts (6 blocks, about 40 s) when the length lift says shorter
     videos hold viewers better.
5. **Phase switch.** When YouTube revenue (`YTEV03`) is above 0, or the owner says the
   channel was accepted into the Partner Program, set `strategy.phase: revenue` and say so
   in the report.

## Experiment mode (while `config/experiment.yaml` is active)

A reach test replaces the usual pacing, script choice and post times for its window. Steps
1, 4, 6 and 7 stay as written; these change:

- **Budget (step 2):** `budget` returns the test's `videos_today` and the credits left
  under `credit_cap`. Use exactly that.
- **Scripts (step 3):** `python -m pipeline experiment plan --count <videos_today>` gives
  one set of arms per video. For each, write a fresh script (new run with `new-run`,
  `script.json` by hand) that follows its arms:
  - `format` → the template and hook type in `research/shorts-2026.md` §8.2 and §8.7;
    record `hook_type` in the script. Pick the niche the format fits; one niche per day.
  - `length` → S 65-85 words (3 blocks), M 100-130 (5), L 145-165 (7).
  - `ending` → `"ending": "loop"` with a last line that runs into the first, or `"cta"`.
  - `motion` → `"motion_blocks": "all"` for full; omit for some.
  - `footage` → `mix`: find public-domain film in the Higgsfield sandbox with the search
    URLs in `config/footage.yaml` (NASA first), look at frames for text or logos, and put
    up to half the blocks on it with a `footage` object (source, direct file url, start,
    fit, licence, credit, page). Only space, history or how-it's-made; elsewhere treat
    the arm as `none` and say so in the report.
  - Titles of 40 characters or fewer, keyword first; `captions.share_line` for Reels.
  Then `python -m pipeline experiment tag RUN --arms '<the arms JSON>'`, set the
  manifest's `voice` (rotate) and `structure`, and produce as in step 4.
- **Publish (step 5):** each video takes the next unused time of today's `post_hours`
  (US Eastern): `python -m pipeline publish-plan RUN --at <YYYY-MM-DDTHH:MM:00-04:00>`.
  YouTube first; Instagram and Facebook while Metricool's monthly post limit allows.
- **Stats:** the "Experiment stats" scheduled task pulls per-video stats every 4 hours
  (below). After `analyze_on`, run the analysis and set `active: false`.

### Experiment stats (the scheduled pull)

1. Preflight's git step, then ToolSearch `metricool`.
2. For each platform in `experiment.METRICS` that is linked, call
   `getAnalyticsDataByMetrics` with `brandId`, `from` = the experiment's start at
   00:00 UTC, `to` = now, and `metrics` = that platform's list in
   `pipeline/experiment.py` (same order). Save each answer to
   `data/experiments/<id>/raw/<platform>-<YYYYMMDDTHHMM>.json` and run
   `python -m pipeline experiment ingest --platform <p> --file <that file>`.
   Empty rows are normal for the first hours (Metricool syncs per-video data with a lag).
3. `python -m pipeline experiment report`, then commit `Experiment stats <time>` and push.
4. One line to the owner: videos so far, the leading and trailing value of each variable
   (with how many videos each rests on).

### Experiment analysis (after `analyze_on`)

`experiment report`, then `pipeline insights`. Write `research/experiment-<id>.md`: what
won per variable (views per hour, YouTube retention, engagement, with counts), the top and
bottom three videos and why, and the changes to make. Apply them in `config/` (formats,
lengths, hashtag rule, ending, motion level, footage use) and `templates/script_guide.md`,
add the strongest finding to `data/insights/lessons.md`, set `active: false`, commit.

## 2. Budget: how many videos today

`python -m pipeline budget --balance <credits>` returns `videos_today` and
`est_cost_per_video`. It spreads the balance across the days left before the plan renews,
keeping `reserve_credits`. Use exactly that number. If it is 0, skip to step 6.

## 3. Choose scripts

1. `python -m pipeline library pick --count <videos_today>`.
2. Topical override: if today's snapshot has a topic idea with `trend_boost` >= 2 in a top-4
   niche and no library script covers it, write a new script for it instead of the
   weakest pick (rules below) and use that.
3. Restock: `python -m pipeline library stock`; for each top-4 niche with fewer than 2
   unused scripts, write 2 new scripts (at most 4 new scripts per run).

Writing a script: follow `data/insights/lessons.md` and `templates/script_guide.md`, and copy the shape of
`library/scripts/inv-25-vs-35.json`. 8 blocks, each 19-24 spoken words; hook under 15
words; an `on_screen_hook` of 2-7 words with one `*starred*` word; a `youtube_title`
that never promises a running time; numbers written as words in narration; a `structure` from
`comparison | myth-vs-fact | mistake | how-it-works | story | countdown` the niche has not
used recently; a CTA that differs from the niche's last two; sources with URLs; `visual`
lines describe scenes with no on-screen text. Save to `library/scripts/<id>.json` and run
`python -m pipeline library validate` until it prints ok.

4. **Hook check** for every chosen script, before any credits are spent. Viewers decide in
   the first 1-2 seconds; a weak opening wastes the whole video. Read block 1 aloud and
   check (`templates/script_guide.md`, "The first two seconds"):
   - the first five spoken words carry the stake: a number, a consequence for "you", a
     myth to break, or a surprising fact. No warm-up, no bare "X or Y?" question;
   - `on_screen_hook` reads in one glance, adds to the spoken line rather than repeating
     it word for word, and stars the one word that matters;
   - block 1's `visual` is the most striking scene of the script (block 1 always opens on
     motion);
   - the answer is promised early and paid off late.
   If any check fails, rewrite block 1 (keep 19-24 words and the sources) and the
   `on_screen_hook`, then validate again.

## 4. Produce each video

For each chosen script id (one at a time):

1. `python -m pipeline start-run <script_id>` prints the run folder (`RUN`).
   `python -m pipeline gen-plan RUN` writes `RUN/generation.json` and prints the estimate.
2. Keyframes: one `generate_image_batch` call with the `keyframes` entries as
   `requests` (`{index, params}` unchanged). `jobs_wait` in groups of up to 12 until all are
   terminal (call again after `poll_after_seconds`). Retry a failed or nsfw index once, the
   second time with the prompt reworded more plainly and, when `generation.json` has a
   `keyframe_retry`, with that model and its params. Keep each block's `job_id` and
   result URL.
3. Motion: one `generate_video_batch` with the `motion` entries, replacing each
   `<keyframe job_id for block N>` with block N's keyframe `job_id`. Wait the same way. A
   motion job that fails twice is dropped: remove that block from `motion` in
   `generation.json` (its keyframe still carries the block).
4. Voice: one `generate_audio_batch` with a single request, the `voice.params` unchanged.
   Wait for it.
5. Write `RUN/assets.json`:
   `{"keyframes": {"1": url, …}, "motion": {"1": url, …}, "voice": url, "job_ids": [...],
   "credits_spent": <sum of quoted credits>}` and run `python -m pipeline render-plan RUN`.
6. Render in the Higgsfield sandbox:
   - `media_upload` with `filename` `<run_id>.mp4`; keep `upload_url`, `media_id` and the
     returned `content_type`.
   - One `sandbox_exec` with `background: true`:
     ```
     set -e; mkdir -p ~/r/<run_id> && cd ~/r/<run_id>
     curl -fsSL '<render.assembler_url from config/production.yaml>' -o assemble.py
     echo '<render.assembler_sha256>  assemble.py' | sha256sum -c -
     cat > render.json <<'JSON'
     <contents of RUN/render.json>
     JSON
     python3 assemble.py render.json > report.json 2> render.log
     [ -s final.mp4 ]
     curl -f -sS -X PUT -H 'Content-Type: <content_type>' -H 'If-None-Match: *' --upload-file final.mp4 '<upload_url>' -o put.out -w '%{http_code}' > put.code
     ```
     Poll right away and keep polling with `tail -n 5 ~/r/<run_id>/render.log; cat
     ~/r/<run_id>/report.json ~/r/<run_id>/put.code` until `put.code` reads 200 (renders take
     1-3 minutes). On failure read `render.log`, fix the input, rerun once.
   - `media_confirm` with `media_id` and `type: video`; its URL is the hosted video URL.
7. Quality check in the sandbox (one foreground call): `ffprobe` duration matches
   `report.json`, 1080x1920,
   an audio stream; extract frames at 0.5 s, 2 s, 15 s and 30 s (scaled to 360 px wide)
   and look at them with `image_paths`. The 0.5 s and 2 s frames must show the hook title,
   readable and clear of the captions. Reject garbled text, broken anatomy or a frame that
   contradicts the narration: regenerate that one keyframe with `keyframe_retry` and
   re-render once. `report.json` must say `"transcribed": true`, `"audio_bed": true`, a
   `hook_title`, and a `longest_shot` under 6 s.
8. `python -m pipeline set-video RUN --url <hosted url> --duration <seconds>` and
   `python -m pipeline captions RUN`.

If a step keeps failing after its one retry, mark the run with
`python -m pipeline record-post RUN --platform youtube --status skipped --note "<why>"`,
move to the next script and report it.

## 5. Publish, each platform at its best time

Only when `autopublish: true`, and only to the platforms that are both in `targets`
(`config/platforms.yaml`) and linked in Metricool (`getBrandSettings` `networksData`).
Pass them as `--platforms`, e.g. `--platforms youtube` while Instagram and Facebook await
verification. A network linked later joins automatically. Every platform gets its own slot from
`config/timing.yaml` (research defaults, re-ranked by the account's audience data and its
own results; `python -m pipeline timing plan` shows them).

- **Metricool**: `python -m pipeline publish-plan RUN` writes `RUN/publish_plan.json`, one
  entry per platform. Each entry's `metricool` object holds the exact `blogId`, `date` and
  `info` for `createScheduledPost`. Call the tool once per entry with those three values
  unchanged: one network, the video as media, the AI-content flag set, and the disclosure
  line in the text for Facebook. Then
  `python -m pipeline record-post RUN --platform <p> --status scheduled --at <entry.at>
  --id <data.id it returned> --via metricool`. A refused network: record it `failed`
  with the reason and go on. If Metricool refuses because the plan's monthly post limit
  is used up, stop scheduling for today (record the rest `failed` with that reason) and
  put "Metricool post limit reached: upgrade to Starter" at the top of the report. Videos
  stay in `runs/` and go out with `publish-plan RUN --asap` once the limit lifts.
- **Upload-Post**: `python -m pipeline publish all RUN --schedule auto` (one request per
  slot; platforms sharing a slot go together).
- **Direct only**: `python -m pipeline publish youtube RUN` /
  `python -m pipeline publish instagram RUN` post now.

When `autopublish` is false, stop after step 4 and list the videos awaiting approval.

## Evening check (the second scheduled task)

A short run, no production and no credits:

1. Preflight's git step, then ToolSearch `metricool` and read the schemas.
2. For each run with a post `scheduled` for today or yesterday (`python -m pipeline
   history`), `getScheduledPosts` for those days in the brand timezone. Record each post
   `published` with its link, or `failed` with Metricool's reason (`record-post`, keep
   `--at`).
3. A post that failed for a reason other than the plan limit gets one retry:
   `python -m pipeline publish-plan RUN --asap --platforms <p> --force`, then
   `createScheduledPost` as in step 5. Record it.
4. Step 6.2-6.3 (metrics collect and dashboard files), then commit
   `Evening check <date>` and push.
5. Report in two lines: what is live, and anything that failed with its reason.

## 6. Earnings and dashboard

1. Upload-Post runs from the last 3 days (`upload_requests` in the manifest):
   `python -m pipeline publish-status RUN`. Metricool runs: `getScheduledPosts` for the
   same days; record each post's state and link with `record-post` (keep `--at`).
2. Higgsfield `balance` again, and Metricool `getBrandSettings` for the linked networks
   (`networksData`: youtubeData → youtube, instagramData → instagram, facebookData →
   facebook, twitterData → twitter). For each linked network read followers and views
   from Metricool (`getAnalyticsAvailableMetrics` for that network's evolution field ids,
   then `getAnalyticsDataByMetrics` over the last 90 days). Write them to
   `data/metrics/<today>.stats.json` as `{"instagram": {"followers": n, "views": n,
   "views_90d": n}, ...}`. Then run `python -m pipeline metrics collect --balance <credits>
   --linked <comma list> --stats-file data/metrics/<today>.stats.json`. It prints the
   dashboard files that changed.
   Then `python -m pipeline milestones`: every step it lists under `reached` goes in the
   report, as "Instagram hit 500 followers: turn on Gifts (…)". Steps with
   `owner: false` are yours to apply from today. The next step per platform goes in the
   report as one line.
3. For each changed file, update the dashboard at `url` in `config/dashboard.yaml`:
   Artifact `publish` with that `url`, `file_path` the file, `asset: true` (one call per
   file); then ArtifactData `get` `datasets/<id>` and `update` it (pin `if_version`) with
   `source: {kind: "file", url: <new /_blob/ url>, name: <file name>}` and
   `updated: {at: <now ISO>, by: "Autopilot"}`. A file with no `datasets/<id>` document yet
   (a new dataset) gets one with `set`: `title`, `description`, that `source`, `updated`,
   `schedule: "Refreshed every morning by the autopilot run"`, `staleAfterHours: 48`. If
   `dashboard/index.html` changed in the repo, also `update` `files/index.html` with
   `{text: <file contents>}`.
4. YouTube followers, views and revenue reach the dashboard live: `datasets/audience` is a
   query on the Metricool connector (`getAnalyticsDataByMetrics`, YTEV metrics, a rolling
   90-day window the page sets). When Instagram or Facebook get linked, add their
   evolution metrics the same way (find the field ids with `getAnalyticsAvailableMetrics`,
   run the call, add rows for that platform in the page's `audience` loader) and say so in
   the report.

## 7. Commit

`git add runs library data research config pipeline/dashboard.py` and commit
`Autopilot <date>: <n> videos, <credits> credits`, ending with the attribution lines the
session requires; push to the current branch (retry network failures up to 4 times with
backoff).

## 8. Report

Five lines at most: videos made (topic, niche, link), each platform's scheduled time (US
Eastern) or failure, credits spent and left, 30-day earnings, and anything that needs the
owner (an account to sign in, a failed platform, a policy change).
