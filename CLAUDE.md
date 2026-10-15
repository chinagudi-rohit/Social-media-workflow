# CLAUDE.md

Short-video workflow for US niches: script → Higgsfield MCP video → TikTok / Reels / Shorts.

- The end-to-end procedure is the `make-short` skill (`.claude/skills/make-short/SKILL.md`).
  Follow it for any request to make or post a video.
- Never spend Higgsfield credits or post publicly without the user's approval in the
  conversation (the skill's gates).
- `python -m pipeline --help` lists CLI commands. Run `python -m pytest` after changing `pipeline/`.
- Niches and platform rules live in `config/`; change behavior there before changing code.
- Commit each `runs/<run_id>/` folder after a run; the niche rotation reads them.
- Never commit `.env` or put credentials in commands, commits or run files.
