---
name: make-short
description: Make and post one short-form video for a US niche. Picks a niche, writes a researched script, generates a 9:16 video through the Higgsfield MCP, then publishes to TikTok (via Higgsfield), Instagram Reels and YouTube Shorts. Use when asked to make, create or post a short, reel, TikTok or YouTube Short, or to run the social video workflow. Optional args - a niche id, "clip" for the cheap single-clip format, or a list of platforms.
---

# make-short

One run = one video, tracked in `runs/<run_id>/`. All commands run from the repo root.
Stop and report at any failed step; never skip a gate below.

## 0. Preflight

Run these together:

- `python -m pipeline check` — which of Instagram / YouTube have credentials.
- Higgsfield `balance` — credits available.
- Higgsfield `tiktok_accounts` — an `active` account is needed for TikTok.

Drop any platform that is not ready and say which, in one line. Continue if at least one
platform is ready, or if the user only wants the video. With 0 credits, stop: tell the user
to top up (Higgsfield `show_plans_and_credits`).

## 1. Niche and topic

1. `python -m pipeline pick-niche` (or `--niche <id>` if the user named one). It returns the
   niche, its angles, and `recent_topics` to avoid.
2. Find a timely US angle: web-search the niche for what is trending in the US this week
   (news, seasonal hooks, Google Trends, popular questions). Pick one topic that fits an
   angle and is not in `recent_topics`. Keep 1-3 reputable source URLs.
3. `python -m pipeline new-run --niche <id> --topic "<topic>"` — prints the run folder.

## 2. Script

Read `templates/script_guide.md` and `templates/example_script.json`, then write
`runs/<run_id>/script.json`. Default `format: narrated`, 3 blocks (30s). Use `clip` when the
user asked for it or credits are tight.

`python -m pipeline validate runs/<run_id>` must print `ok`. Fix and re-run until it does.

**Gate — script + cost.** Get the credit cost first (step 3 explains how), then show the
user the hook, the narration, and the cost, and ask to approve. Skip the wait only when the
user already approved spending in this conversation or set a budget the cost fits under.

## 3. Generate the video (Higgsfield MCP)

Never use `use_unlim` or `use_free_gens` unless the user asked for it. Save the final
generation prompt to `runs/<run_id>/prompt.txt`.

**Website fallback.** Higgsfield free-trial accounts cannot generate through the MCP ("Your
free trial supports generation only on higgsfield.ai"), and website-only offers (such as
unlimited Wan generations) are not usable through it either. On that error, stop
retrying: give the user `prompt.txt` to run on higgsfield.ai, then continue from
"Record the result" with the video URL they send back.

### narrated

Load the Higgsfield workflow with `get_workflow_instructions({workflow: "faceless-video"})`
and follow it exactly. Hand it everything this run already decided, so its intake only asks
what is still open (voice):

- Channel type: **History** for `american-history`, else **Explainer**. Motion mode: animated.
- Style: the preset card closest to the script's `visual_style`.
- Duration: `len(blocks) × 10` seconds. Aspect: **9:16**. Subtitles: on. Thumbnail: no.
- Topic: the script — paste the block narrations as the user's own script, in order, with
  `youtube_title` as its title. Narration is authored text; it must not be rewritten.
- Sources: the script's `sources`.

Cost: the workflow quotes it; generation calls take `get_cost: true` for a preflight.

### clip

One `generate_video` call: `aspect_ratio: "9:16"`, the block's `visual` plus the niche
`visual_style` as the prompt, duration 5-15s. Pick the model with
`models_explore(action: "recommend")` (default general-purpose model otherwise). Preflight
with `get_cost: true`, then submit and wait with `jobs_wait`.

### Record the result

The final video must be a **Higgsfield-hosted URL** (from `media_confirm` or the completed
job's result). TikTok only accepts Higgsfield-hosted media.

```
python -m pipeline set-video runs/<run_id> --url "<hosted url>" --job-id <id> [--job-id <id>...] --duration <s> --credits <n>
```

## 4. Captions

`python -m pipeline captions runs/<run_id>` writes `captions.json` with a TikTok title and
description, an Instagram caption, and a YouTube title, description and tags.

## 5. Publish

**Gate — posting is public.** Show the video link and each platform's caption, and get an
explicit yes before posting anywhere, unless the user already said to post without asking.

- **TikTok** — `tiktok_prepare_publish` with the `connector_id`, `media_type: VIDEO`,
  `video_url`, `title` and `description` from `captions.json`, `mode` from
  `config/platforms.yaml`, and `is_aigc: true`. The user reviews and submits in Higgsfield's
  publish widget (music can be added there); do not call `tiktok_publish` yourself. Then
  check `tiktok_publish_status` and record it:
  `python -m pipeline record-post runs/<run_id> --platform tiktok --status published --id <publish_id>`.
  If the client cannot show the widget, record `--status skipped --note "needs MCP Apps client"`.
- **Instagram Reels** — `python -m pipeline publish instagram runs/<run_id>`
- **YouTube Shorts** — `python -m pipeline publish youtube runs/<run_id>`

Both publish commands record the outcome in the manifest themselves. Use `--dry-run` to
preview a payload.

## 6. Wrap up

1. Commit `runs/<run_id>/` (manifest, script, captions; the downloaded `video.mp4` is
   ignored) so the niche rotation remembers this run. Push to the working branch.
2. Report in a few lines: niche, topic, video link, each platform's post link or status,
   credits spent.
