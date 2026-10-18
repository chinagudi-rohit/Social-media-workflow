---
name: fm-produce
description: Produces the faceless short videos for prepared runs through the Higgsfield MCP. Generates keyframes, animated moments and a voiceover, renders 1080x1920 with timed captions in the Higgsfield sandbox, quality-checks the result locally, and records the hosted video and captions. Resumable and capped by a credit limit. Use for a "Produce N video(s) <date>" kanban card or an approved on-demand video.
version: 1.0.0
author: Faceless Monitisation
metadata:
  hermes:
    tags: [faceless, higgsfield, video, production]
    requires_toolsets: [terminal]
---

# fm-produce

Spends real Higgsfield credits. Two hard rules:
1. Never spend more than the credit limit in the card body.
2. Never submit a job twice. `RUN/jobs.json` is the ledger: record every job id the
   moment a submission returns, and on a retry resume from the ledger.

Higgsfield MCP tools carry the server prefix (for example
`mcp__higgsfield__generate_image_batch`); below they are named without it. Never set
`use_unlim` or `use_free_gens`. If a call answers with `unlim_choice`, call again with
`use_unlim: false`.

## When to Use
- A kanban card titled `Produce N video(s) <date>`.
- An on-demand card from fm-lead after the owner approved the quoted cost.

## Procedure

0. `kanban_show()`. Take the credit limit `L` from the body and the run folders from the
   scripts card's handoff (`metadata.runs`). Call `balance` and note `credits` as
   `B0`. Spent so far = `B0` minus the current balance. Before every submission, check
   that spent + that submission's estimate <= `L`. If it would not fit, stop and
   `kanban_block(kind="needs_input", reason=...)`.

For each `RUN`, one at a time:

1. **Plan.** `./fm gen-plan RUN` writes `RUN/generation.json` and prints
   `estimated_credits`. If `RUN/jobs.json` exists, read it and resume: wait on recorded
   job ids, and submit only entries that were never submitted or failed (at most one
   retry each).
2. **Keyframes.** One `generate_image_batch` call. Its `requests` are the
   `generation.json` `keyframes` entries as `{index, params}`, unchanged (at most 12 per
   call). Immediately write each returned `{index: job_id}` to
   `RUN/jobs.json` under `keyframes`. Then `jobs_wait` in groups of up to 12 until every
   job is terminal. Call again after `poll_after_seconds` while `all_terminal` is false,
   and use `kanban_heartbeat` every few polls. Record each result URL in `jobs.json`.
   Retry a failed or nsfw index once, with the prompt reworded more plainly.
3. **Motion.** One `generate_video_batch` with the `motion` entries. Replace each
   `<keyframe job_id for block N>` placeholder with block N's keyframe `job_id`. Record
   job ids, then wait the same way. If a motion job fails twice, drop it: remove that block
   from `motion` in `generation.json` (its keyframe still carries the block).
4. **Voice.** One `generate_audio_batch` with a single request, `index: 0`, and the
   `voice.params` unchanged. Record and wait.
5. **Assets.** Write `RUN/assets.json`:
   `{"keyframes": {"1": url, ...}, "motion": {"1": url, ...}, "voice": url,
   "job_ids": [...all...], "credits_spent": <B0 minus the balance now, for this run>}`.
   Then `./fm render-plan RUN` writes `RUN/render.json`.
6. **Render in the Higgsfield sandbox.**
   - `media_upload` with `filename: "<run_id>.mp4"`. Keep `upload_url`, `media_id` and the
     returned `content_type`.
   - One `sandbox_exec` with `background: true`, `size: "xl"`. Fill in the values from
     `config/production.yaml` (`render.assembler_url`, `render.assembler_sha256`):
     ```
     set -e; mkdir -p ~/r/<run_id> && cd ~/r/<run_id>
     curl -fsSL '<assembler_url>' -o assemble.py
     echo '<assembler_sha256>  assemble.py' | sha256sum -c -
     cat > render.json <<'JSON'
     <contents of RUN/render.json>
     JSON
     python3 assemble.py render.json > report.json 2> render.log
     [ -s final.mp4 ]
     curl -f -sS -X PUT -H 'Content-Type: <content_type>' -H 'If-None-Match: *' --upload-file final.mp4 '<upload_url>' -o put.out -w '%{http_code}' > put.code
     ```
   - Poll right away, and keep polling with foreground `sandbox_exec`:
     `tail -n 5 ~/r/<run_id>/render.log; cat ~/r/<run_id>/report.json ~/r/<run_id>/put.code`
     until `put.code` reads `200`. Renders take 1-3 minutes. If the result says
     `sandbox_created: true`, the files are gone: rerun the render command. On a failure,
     read `render.log`, fix the input and rerun once.
   - `media_confirm` with `media_id` and `type: "video"`. Its URL is the hosted video URL
     `V`.
7. **Quality check on this Mac.**
   ```
   mkdir -p RUN/frames && curl -fsSL '<V>' -o RUN/final.mp4
   ffprobe -v error -show_entries format=duration:stream=codec_type,width,height -of json RUN/final.mp4
   for t in 2 20 40 60; do ffmpeg -v error -y -ss $t -i RUN/final.mp4 -frames:v 1 -vf scale=540:-1 RUN/frames/f$t.jpg; done
   ```
   The checks: duration >= 61 s, 1080x1920, an audio stream. `report.json` (from the
   sandbox) says `"transcribed": true`. Look at each frame with `vision_analyze` and
   compare it with that moment's narration. Reject garbled text, broken anatomy, or a
   frame that contradicts the narration. Then regenerate only that block's keyframe
   (1 credit, within `L`), update `assets.json`, run `./fm render-plan RUN` again and
   re-render once.
8. **Record.** `./fm set-video RUN --url <V> --duration <seconds> --credits <spent>`, with
   one `--job-id` per job id, then `./fm captions RUN`.

If a run still fails after its one retry:
`./fm record-post RUN --platform youtube --status skipped --note "<why>"`, then move to the
next run and list it under `skipped`.

9. `kanban_complete(summary=<videos and links>, metadata={"videos": [{"run", "url",
   "duration", "credits"}], "credits_spent": <B0 minus final balance>, "balance": <final>,
   "skipped": [...]})`.

## Pitfalls
- A batch that timed out or partly failed is not safe to resubmit as a whole. Look up the
  recorded job ids with `jobs_wait` first.
- Sandbox commands time out after 120 s in the foreground. Renders always go in the
  background, polled.
- `RUN/final.mp4` and `RUN/frames/` are local QC copies: git-ignored, never committed.
- If the Higgsfield tools are missing, or answer that you are not signed in:
  `kanban_block(kind="needs_input", reason="Higgsfield MCP not signed in for fm-producer:
  hermes -p fm-producer mcp login higgsfield")`.
- Free-trial accounts cannot generate through the MCP. If generation is refused for the
  plan, block with that reason. Do not try other models or presets to get around it.

## Verification
Each produced run's manifest has `video.url`, `RUN/captions.json` exists, and the final
balance shows spending within `L`.
