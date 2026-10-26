# CLAUDE.md

Faceless short-video autopilot for high-RPM Western niches: research → Higgsfield video →
YouTube Shorts / Instagram Reels / Facebook Reels → earnings dashboard.

- The weekly batch is the `autopilot` skill (`.claude/skills/autopilot/SKILL.md`): owner's
  rule (2026-10-26), every Monday before the first post it makes the whole week's videos and
  schedules them across the week. One video on demand is `make-short`. Follow them rather
  than improvising.
- The owner asked for full automation: the autopilot may spend Higgsfield credits up to the
  `budget --week` allowance and post publicly while `autopublish: true` in
  `config/platforms.yaml`. Outside the autopilot, confirm before spending credits or posting.
- Keep content monetizable: sourced facts, no AI persona giving personal finance, health or
  legal advice, varied structures and styles,
  AI labels on.
- `python -m pipeline --help` lists commands. Run `python -m pytest` after changing `pipeline/`
  or `tools/`. If `tools/assemble.py` changes, commit and push it, then point
  `render.assembler_url` in `config/production.yaml` at its raw GitHub URL for that commit
  and update `render.assembler_sha256` (a test enforces the hash).
- Runway (`runway` in `config/production.yaml`) makes the music/effects library; daily motion
  stays on Higgsfield, which is about 10x cheaper.
- Owner's rules (2026-10-22): every video is generated at 480p, 2-3 videos a day at the best
  quality that allows. The default tier makes one multi-shot clip per block from an asset
  roster (`tiers.multishot`); a test enforces 480p.
- Strategy is reach-first until a platform pays (`strategy.phase` in
  `config/production.yaml`); until then niche scoring ignores the ad-revenue tier (owner's
  rule). Each run learns from its own videos (`pipeline insights`,
  `data/insights/lessons.md`) and posts only to platforms linked in Metricool.
- Watching a video: the `watch` skill (`.claude/skills/watch`, MIT, vendored unchanged from
  bradautomates/claude-video at 03ceb42 after a source review) works only in the Higgsfield
  sandbox, because the local proxy blocks YouTube. Clone that commit there and give yt-dlp
  `--js-runtimes node`. Run it with `--engine local --sub-lang en`: its automatic caption pick
  chose a dubbed track. If captions return 429, transcribe with the sandbox's faster-whisper.
  Never use its Gemini engine or cookies, and never ask the owner for keys.
- three.js motion graphics (`tools/motion3d`, method in `research/threejs-motion-graphics.md`)
  draw exact numbers, diagrams and money for zero credits: use them where AI clips get facts wrong.
- Owner's rule (2026-10-26): no video is published until the `video-reviewer` agent
  (`.claude/agents/video-reviewer.md`, Sonnet, high effort) has watched every frame and
  written a PASS in `runs/<id>/review.json`.
- Behavior lives in `config/`; change it there before changing code.
- Commit `runs/`, `library/` and `data/` after each run; rotation and the dashboard read them.
- Never commit `.env` or put credentials in commands, commits or run files.
