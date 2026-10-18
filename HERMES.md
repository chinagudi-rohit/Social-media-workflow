# HERMES.md

Faceless short-video autopilot for high-RPM Western niches, run by Hermes Agent:
research → Higgsfield video → TikTok / Reels / Shorts / Facebook (Metricool) → earnings dashboard.

This file is the project context for every Hermes profile working here. `CLAUDE.md` and
`.claude/skills/` belong to the Claude Code instance: do not follow them and do not call the
tools they name. Setup and operations: `hermes/SETUP.md`.

## Who does what

Five Hermes profiles, one stage each, coordinated on the kanban board `faceless`
(`config/hermes.yaml`). Every day at 07:54 US Eastern, fm-lead's cron runs
`./fm hermes kickoff`, which reads the Higgsfield balance, runs the budget and creates the
day's cards:

| Card | Profile | Skill | Model first |
|---|---|---|---|
| Research refresh | fm-research | `fm-research` | Grok (web + X search) |
| Choose N script(s) | fm-writer | `fm-scripts` | Claude |
| Produce N video(s) | fm-producer | `fm-produce` | OpenAI (Higgsfield MCP) |
| Publish, earnings and dashboard | fm-publisher | `fm-publish` | Grok (Metricool MCP) |
| Report and chat in #faceless | fm-lead | `fm-lead` | Grok |

A card's worker: `kanban_show` → follow the card's skill → `kanban_complete` with the
metadata the card body asks for. Workers never create cards for other stages; fm-lead
orchestrates. If you cannot finish, `kanban_block` with `kind=needs_input` (a person must act:
a sign-in, a plan limit, a decision) or `kind=transient` (retry later), and a one-line reason.
The next card sees your summary and metadata under "Parent task results", so put
everything it needs there.

## Rules for every profile

- **Money.** The owner asked for full automation: a production card may spend Higgsfield
  credits up to the limit written in its body, and posts go out publicly while
  `autopublish: true` in `config/platforms.yaml`. Outside a card, ask in #faceless before
  spending credits or posting. Never set `use_unlim` or `use_free_gens`; if a Higgsfield call
  answers with `unlim_choice`, call again with `use_unlim: false`.
- **Monetizable content.** Sourced facts, no on-camera persona, no personalised finance,
  health, tax or legal advice, videos over 60 seconds, structures / narrators / styles rotate,
  the AI-generated label on every post. Reasons: `research/monetization-2026.md`.
- **The CLI.** `./fm <command>` runs the pipeline in the repo's `.venv` (`./fm --help`).
  Commands that take `--date` get the card's date (US Eastern). Behavior lives in `config/`;
  change config before code. After changing `pipeline/` or `tools/`, run
  `.venv/bin/python -m pytest -q`. A change to `tools/assemble.py` needs a re-host and a new
  `render.assembler_sha256` in `config/production.yaml` (a test enforces it).
- **Paths.** The repo path contains a space: quote it in shell commands, or use paths
  relative to the repo root (tools start there).
- **Git.** Work on branch `hermes/autopilot`. fm-publisher commits `runs/ library/ data/
  research/` after each run and pushes. Never commit `.env`, `runs/*/final.mp4` or
  `runs/*/frames/`; never put credentials in commands, commits or run files.
- **Facts.** Never invent a source, a number, a URL, a job id or a result. Report what a
  tool actually returned.
