---
name: make-short
description: Make (and optionally post) one faceless short right now, outside the daily autopilot. Uses the same production path - a library script or a freshly written one, Higgsfield keyframes, animated moments and voiceover, sandbox render, publishing through Metricool or Upload-Post at each platform's best time. Use when asked to make, create or post one short, reel, TikTok or YouTube Short, optionally for a named niche, topic or script id.
---

# make-short

Run from the repo root. This is the autopilot's steps 3-5 for a single video, with the
owner in the loop.

1. **Pick the script.** A script id the user named; else a topic or niche they named (write
   a new script for it as in the autopilot's step 3, rules in `templates/script_guide.md`);
   else `python -m pipeline library pick --count 1`.
2. **Quote and confirm.** `python -m pipeline start-run <id>` then
   `python -m pipeline gen-plan RUN` prints `estimated_credits`. Higgsfield `balance` for
   the current credits. Show the hook, the topic and the cost, and wait for a yes unless the
   user already approved spending in this conversation.
3. **Produce.** Follow `.claude/skills/autopilot/SKILL.md` step 4 exactly (keyframes,
   motion, voice, `assets.json`, `render-plan`, sandbox render, quality check, `set-video`,
   `captions`). Send the user the hosted video link.
4. **Post.** Only after the user says to post, or if they asked for posting up front:
   autopilot step 5 (each platform at its best slot today; `python -m pipeline timing plan`
   shows them). Otherwise leave it in `runs/` and say it can be posted later.
5. **Commit** the run folder and push.

If Higgsfield generation through the MCP is refused (a free-trial account), say so, save
the keyframe prompts from `generation.json` for the user to run on higgsfield.ai, and
continue from `assets.json` once they send the result links.
