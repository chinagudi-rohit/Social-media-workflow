# CLAUDE.md

Faceless short-video autopilot for high-RPM Western niches: research → Higgsfield video →
TikTok / Reels / Shorts / Facebook → earnings dashboard.

- The daily procedure is the `autopilot` skill (`.claude/skills/autopilot/SKILL.md`); one
  video on demand is `make-short`. Follow them rather than improvising.
- The owner asked for full automation: the autopilot may spend Higgsfield credits up to the
  `budget` command's daily allowance and post publicly while `autopublish: true` in
  `config/platforms.yaml`. Outside the autopilot, confirm before spending credits or posting.
- Keep content monetizable: sourced facts, no AI persona giving personal finance, health or
  legal advice, videos over 60 seconds while TikTok is a target, varied structures and styles,
  AI labels on.
- `python -m pipeline --help` lists commands. Run `python -m pytest` after changing `pipeline/`
  or `tools/`. If `tools/assemble.py` changes, re-host it and update `render.assembler_url`
  and `render.assembler_sha256` in `config/production.yaml` (a test enforces the hash).
- Strategy is reach-first until a platform pays (`strategy.phase` in
  `config/production.yaml`); each run learns from its own videos (`pipeline insights`,
  `data/insights/lessons.md`) and posts only to platforms linked in Metricool.
- Behavior lives in `config/`; change it there before changing code.
- Commit `runs/`, `library/` and `data/` after each run; rotation and the dashboard read them.
- Never commit `.env` or put credentials in commands, commits or run files.
