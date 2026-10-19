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
  under `credit_cap`. Then cap it by **Metricool posts left this month** (step 2's post
  check): never make a video that cannot be posted.
- **Scripts (step 3):** `python -m pipeline experiment plan --count <videos_today>` gives
  one set of arms per video. For each, write a fresh script (new run with `new-run`,
  `script.json` by hand) that follows its arms:
  - `format` → the template and hook type in `research/shorts-2026.md` §8.2 and §8.7;
    record `hook_type` in the script. Pick the niche the format fits; one niche per day.
  - `length` → S 65-85 words (3 blocks), M 100-130 (5).
  - `ending` → `"ending": "loop"` with a last line that runs into the first, or `"cta"`.
  - `style` → the script's `visual_style` is `style_sets[<arm>]` from
    `config/experiment.yaml`, word for word; shots follow it (photoreal: real-looking
    hands, people and objects doing the action; cartoon: expressive characters acting).
  - Titles of 40 characters or fewer, keyword first; `captions.share_line` for Reels.
  Then `python -m pipeline experiment tag RUN --arms '<the arms JSON>'`, set the
  manifest's `voice` (rotate) and `structure`, and produce as in step 4.
- **Competitor breakdowns (before writing scripts):** Higgsfield `video_analysis_jobs`
  lists the scene-by-scene analyses of the top Shorts in `research/shorts-2026.md` §7.
  For each completed one not yet in §9 of that file, add its shot length, hook (first
  two seconds: words, on-screen text, visual), caption style and ending, then use what
  repeats across them in today's scripts. Queued or failed ones: skip, no new requests.
- **Publish (step 5):** on YouTube each video takes the next unused time of today's
  `post_hours` (US Eastern): `python -m pipeline publish-plan RUN --platforms youtube
  --at <YYYY-MM-DDTHH:MM:00-04:00>`. Instagram and Facebook get the video too, at their
  own best slots: `python -m pipeline publish-plan RUN --platforms instagram,facebook`.
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
lengths, hashtag rule, ending, style) and `templates/script_guide.md`,
add the strongest finding to `data/insights/lessons.md`, set `active: false`, commit.

**Old-look cleanup (owner's rule, 2026-10-19).** The five videos posted before the quality
tier (runs dated 2026-10-18) stay up unless they have barely any views. At this analysis,
read each of their posts' views (Metricool per-video rows, the same calls as the stats
pull, `from` 2026-10-18). Any post under 50 views after 48 h goes on a "delete" list for
the owner: platform, title, link. The connector cannot delete published posts, so the
owner removes them in YouTube Studio, Instagram or Facebook; put the list in the report.
The old noisy-room video (`2026-10-18-psychology-why-you-hear-your-name-in-a-noisy-room`)
was remade as the pilot; list its posts the same way.

## 2. Budget: how many videos today

`python -m pipeline budget --balance <credits>` returns `videos_today` and
`est_cost_per_video`. It spreads the balance across the days left before the plan renews,
keeping `reserve_credits`. Use exactly that number. If it is 0, skip to step 6.

**Post check.** Metricool's plan caps posts a month (`metricool.monthly_post_limit` in
`config/platforms.yaml`; each network a video goes to is one post). `getScheduledPosts`
from the 1st of this month to its last day (brand timezone) lists every post made or
scheduled this month; posts left = the limit minus their count. Make no more videos than
posts left, and give each video YouTube first, then Instagram, then Facebook while posts
remain. With no posts left, make no videos (credits would be wasted), skip to step 6, and
open the report with "Metricool post limit reached".

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

4. **Shot list** for every chosen script, before any credits are spent
   (`templates/script_guide.md` "Shot list", `templates/example_script.json`). After
   `start-run`, give each block of `RUN/script.json` 2-3 `shots`: `words` that split the
   block's narration at its commas and full stops, a literal `visual`, an `action` that
   plays out (the subject acts, then the camera), an `overlay` label where a number or
   term is said, and `ref` to bring back the video's one recurring character. Set one
   character-animation `visual_style` for the video. `python -m pipeline validate RUN`
   until it prints ok. Long library scripts: cut to 3-5 blocks (S or M) rather than paying
   for 20 shots.
5. **Hook check** for every chosen script, before any credits are spent. Viewers decide in
   the first 1-2 seconds; a weak opening wastes the whole video. Read block 1 aloud and
   check (`templates/script_guide.md`, "The first two seconds"):
   - the first five spoken words carry the stake: a number, a consequence for "you", a
     myth to break, or a surprising fact. No warm-up, no bare "X or Y?" question;
   - `on_screen_hook` reads in one glance, adds to the spoken line rather than repeating
     it word for word, and stars the one word that matters;
   - shot 1.1 is the most striking scene of the script, acting from its first frame, and
     block 1's shots are the shortest;
   - the answer is promised early and paid off late.
   If any check fails, rewrite block 1 (keep 19-24 words and the sources) and the
   `on_screen_hook`, then validate again.

## 4. Produce each video

For each chosen script id (one at a time):

1. `python -m pipeline start-run <script_id>` prints the run folder (`RUN`); write the shot
   list (step 3.4). `python -m pipeline gen-plan RUN` writes `RUN/generation.json` and
   prints the estimate.
2. Keyframes: one `generate_image_batch` with the `keyframes` entries that have no
   `after` (`{index, params}` unchanged). When those finish, a second batch with the
   entries that have `after`, replacing `<keyframe job_id for shot X>` in their `medias`
   with shot X's keyframe `job_id`. `jobs_wait` in groups of up to 12 until all are
   terminal. **Look at every keyframe** before animating (one sandbox contact sheet,
   `image_paths`): the literal subject of its words, one clear subject, the recurring
   character matching, no garbled text, faces and hands intact. Redo a bad frame once
   with `keyframe_retry` (add the `ref` medias when the shot has one).
3. Motion: `generate_video_batch` with the `motion` entries, replacing each
   `<keyframe job_id for shot X>` with shot X's keyframe `job_id`. **Hailuo takes about
   five jobs at once**: submit in groups of five and send the next group when one
   finishes (a 429 means wait, not fail; image models share a limit of about eight jobs
   at once). A request answered with a `preset_recommendation` instead of a job is
   resubmitted unchanged plus `declined_preset_id`. A motion job that fails is resubmitted once
   with `motion_retry` (same prompt and start image); if that fails too, set the shot to
   `"still": true` in `script.json`, rerun `gen-plan`, and go on.
   **Runway hero shot** (`runway.hero_shot` in config/production.yaml): when its `when`
   holds for this video and Runway `whoami` shows `credits.total` of at least `credits` +
   `min_balance`, animate shot 1.1 with Runway instead: `generate_video` with that
   `model` and `params`, `startFrame.url` = shot 1.1's keyframe URL, `promptText` = shot
   1.1's motion prompt from `generation.json`; poll `get_task` and use its URL as shot
   1.1's motion. Any failure falls back to the Hailuo clip. Everything else stays on
   Hailuo (Runway's other video models cost about ten times more).
   **Music:** `render-plan` picks the bed from `render.audio.music` by niche. A niche with
   no bed of its own gets one: Runway `generate_music` (`runway.music.model`, an
   instrumental ~30 s underscore in the niche's mood, "no vocals, sparse in the mid range
   so a voiceover sits on top"), downloaded in the sandbox, re-hosted with
   `media_upload` + PUT + `media_confirm` (type audio), and added to the config.
4. Voice: one `generate_audio_batch` with a single request, the `voice.params` unchanged.
   Submit it with the first keyframe batch.
5. Write `RUN/assets.json`, keyed by shot id ("2.1"; a block without shots is "2"):
   `{"keyframes": {"1.1": url, …}, "motion": {"1.1": url, …}, "voice": url, "job_ids": [...],
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
     ```
     with `size: "xl"`. Poll with `tail -n 5 ~/r/<run_id>/render.log; cat
     ~/r/<run_id>/report.json` until the report appears (2-4 minutes). On failure read
     `render.log`, fix the input, rerun once.
7. Quality check in the sandbox (one foreground call): `ffprobe` duration matches
   `report.json`, 1080x1920, an audio stream, video bitrate above 3.5 Mb/s (the CRF 18
   encode follows the content: smooth skies and flat colour land at 3.5-5); a contact sheet
   of one frame a second (`fps=1,scale=150:-2,tile=8x6`) and frames at 0.5 s and 2 s,
   looked at with `image_paths`. The 0.5 s and 2 s frames show the hook title, readable
   and clear of the captions; the sheet changes picture every 3-4 s and every label is
   readable. Reject garbled text, broken anatomy, a character that changes face, or a
   frame that contradicts the narration: redo that shot's keyframe and clip once and
   re-render. `report.json` must say `"transcribed": true`, `"audio_bed": true`, a
   `hook_title`, `pictures` at least the length in seconds divided by 4, and a
   `longest_shot` under 5 s. Only then upload: in the sandbox,
   `curl -f -sS -X PUT -H 'Content-Type: <content_type>' -H 'If-None-Match: *' --upload-file
   final.mp4 '<upload_url>' -w '%{http_code}'` must print 200; then `media_confirm` with
   `media_id` and `type: video`; its URL is the hosted video URL.
8. `python -m pipeline set-video RUN --url <hosted url> --duration <seconds>` and
   `python -m pipeline captions RUN`.

If a step keeps failing after its one retry, mark the run with
`python -m pipeline record-post RUN --platform youtube --status skipped --note "<why>"`,
move to the next script and report it.

## 5. Publish, each platform at its best time

Only when `autopublish: true`, and only to the platforms that are both in `targets`
(`config/platforms.yaml`) and linked in Metricool (`getBrandSettings` `networksData`).
Pass them as `--platforms`. Every video goes to every one of them (YouTube, Instagram and
Facebook are all linked); a platform is skipped only when the post check says the plan's
limit is reached. A network linked later joins automatically. Schedule and `record-post`
one video's posts before planning the next, so its slots count as taken. Every platform gets its own slot from
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
  put "Metricool post limit reached" at the top of the report. Videos
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
   "views_90d": n}, ...}` (YouTube `YTEV01`/`YTEV02`, Instagram `IGEV01`/`IGEV23` Reels
   views, Facebook `FBEV17`/`FBEV22` Reels views). Runway `whoami` gives `credits.plan` and
   `credits.purchased`. Then run `python -m pipeline metrics collect --balance <credits>
   --linked <comma list> --stats-file data/metrics/<today>.stats.json --runway-plan-left
   <plan> --runway-purchased <purchased>`. It prints the dashboard files that changed.
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
