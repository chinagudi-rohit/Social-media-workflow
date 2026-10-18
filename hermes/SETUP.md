# Faceless autopilot on Hermes: setup and operations

This repo is the Hermes copy of the Claude Code workflow built in the claude.ai session
"US niches video workflow with Higgsfield MCP" (branch
`claude/compassionate-ptolemy-rf3q0u`). It does the same job:
research → script → Higgsfield video → TikTok / Reels / Shorts / Facebook at each
platform's best time → earnings dashboard. Hermes runs it with five specialised bots
instead of one Claude session. **Hermes takes over the same four accounts and the whole
Higgsfield budget**, so the Claude session's daily run must stop (Part 0).

```
07:54 ET  fm-lead cron ── ./fm hermes kickoff (no model: balance → budget → cards)
                │
                ▼  kanban board "faceless" (each card = one specialist, one skill)
   Research refresh ──► Choose N script(s) ──► Produce N video(s) ──► Publish, earnings, dashboard
   fm-research          fm-writer              fm-producer             fm-publisher
   Grok → web + X       Claude Opus 5.5        GPT-6.1 + Higgsfield    Grok + Metricool
                │                                                         │
                └── every finished / failed card pings #faceless ◄────────┘ wakes fm-lead → daily report
```

## Why specialised bots beat one big agent here

| | One agent (the Claude session) | Five Hermes bots |
|---|---|---|
| Model fit | One model for everything | Grok for live search, Claude for writing, GPT for long tool runs |
| Your $20 plans | One plan carries the whole run | The load is spread across Grok, ChatGPT and Claude |
| Context | Research, scripts and render logs share one context | Each bot starts clean with only its stage |
| Failure | A failure mid-run stops everything | A card blocks, retries or pings you; earlier stages are kept |
| Money safety | Rules in one long skill | The producer has a hard credit limit and a job ledger; no other bot can spend |
| Memory | Session-bound | Each bot keeps its own memory (the publisher learns your Metricool brand, the writer learns what flopped) |

## The bots

| Profile | Job | Model, then fallback | Tools |
|---|---|---|---|
| `fm-lead` | #faceless chat, daily report, failures, on-demand videos | Grok 4.7 → GPT-6.1-sol → Claude Sonnet 4.6 → Qwen 3.8 27B | terminal, files, kanban, cron |
| `fm-research` | Daily trends and monetization rules | Grok 4.7 → GPT-6.1-sol → Claude Sonnet 4.6 → Qwen | web, X search |
| `fm-writer` | Picks and writes the scripts | Claude Opus 5.5 → Grok → GPT-6.1-sol → Qwen | web |
| `fm-producer` | Higgsfield video production | GPT-6.1-sol → Grok → Claude Sonnet 4.6 (no Qwen: it spends credits) | Higgsfield MCP, vision |
| `fm-publisher` | Scheduling, results, earnings, dashboard, git | Grok 4.7 → GPT-6.1-sol → Claude Sonnet 4.6 (no Qwen: posts publicly) | Metricool MCP |

Fallback is automatic. A model that is rate-limited, out of quota or down is skipped for
that turn. Each bot's settings come from `hermes/profiles/<name>/profile.yaml`, and the
procedures from `hermes/skills/<skill>/SKILL.md`. Every bot reads `HERMES.md`.

> **Grok is currently refusing requests.** On 18 Oct 2026 xAI answered
> `403 personal-team-blocked:spending-limit` ("You have run out of credits or need a Grok
> subscription"). The Grok-first bots are failing over to GPT-6.1-sol, which works. Check
> the SuperGrok subscription or its usage limit at https://grok.com/?_s=usage. Nothing
> needs changing here once it works again.

---

## Part 0: stop the Claude instance's daily run (1 minute)

Two runners on one Higgsfield plan and the same four accounts would double-post and
overspend.

1. Open the claude.ai session "US niches video workflow with Higgsfield MCP".
2. Send: `Stop the daily scheduled autopilot run. Hermes has taken over this workflow.`
3. Also check https://claude.ai/code/routines and delete any autopilot routine there.

The Claude dashboard artifact (claude.ai "Creator Earnings") stops updating. The Hermes
dashboard (Part 5) replaces it.

## Part 1: install (already done; re-run any time)

```bash
cd ~/Downloads/"Faceless Monitisation"
hermes/setup/install.sh
```

This prepares `.venv`, runs the tests, and creates or updates the five profiles from
`hermes/profiles/`. It also creates the `faceless` kanban board and adds the `fm-kickoff`
cron job to fm-lead (07:54 America/New_York, created **paused**). Re-running it after you
edit a `profile.yaml` applies the change.

## Part 2: sign in to Higgsfield and Metricool for Hermes (3 minutes, browser)

The Claude connectors do not carry over. Hermes needs its own OAuth sign-in to each MCP.
Use the same accounts you used with Claude.

1. **Higgsfield** (the producer bot):
   ```bash
   hermes -p fm-producer mcp login higgsfield
   ```
   Your browser opens Higgsfield's sign-in. Sign in as chinagudi.rohit@gmail.com (the
   Plus account) and press Allow. Then check it:
   ```bash
   hermes -p fm-producer mcp test higgsfield
   ```
   You should see `✓ Connected` and about 12 tools.
2. **Metricool** (the publisher bot):
   ```bash
   hermes -p fm-publisher mcp login metricool
   ```
   Sign in to Metricool in the browser and press Allow. Check it with
   `hermes -p fm-publisher mcp test metricool`.
   - TikTok, Instagram, YouTube and the Facebook Page must be linked inside Metricool
     (https://app.metricool.com/). You did this for Claude, and it is the same Metricool
     account, so nothing changes.
   - The Metricool Free plan schedules only 20 posts a month. One video a day on four
     platforms is about 120, so it needs a paid plan.
   - The first publish run saves your Metricool brand id to `config/hermes.yaml`. If the
     account has several brands, fm-lead asks you which one in #faceless.

You can also use the dashboard's **Connect Higgsfield** and **Connect Metricool** buttons
(Part 5). They run the same commands.

## Part 3: the #faceless Discord channel (2 minutes)

fm-lead lives in its own channel on your existing Discord bot. No new bot token is needed.

1. In Discord, open your server (the one with the `Daily AI news` #general channel).
   Click **+** next to Text Channels, choose **Text**, name it `faceless`, and Create.
2. Turn on Developer Mode: **User Settings → Advanced → Developer Mode**.
3. Right-click **#faceless** and choose **Copy Channel ID**.
4. Run:
   ```bash
   hermes/setup/route-discord.sh <paste the channel id>
   ```
   It saves the id in `config/hermes.yaml` and routes #faceless to fm-lead
   (`gateway.profile_routes` in `~/.hermes/config.yaml`). It also lets you talk there
   without @mentions, points the kickoff cron's messages at the channel, and restarts the
   Hermes gateway. WhatsApp, Telegram and Discord reconnect within seconds; a cron job
   running at that moment is retried.
5. Type `status` in #faceless. fm-lead should answer.

## Part 4: go live

```bash
./fm hermes doctor                 # every line should say ok
./fm hermes kickoff --dry-run      # today's plan: expect 1 video while credits allow
```

Then either wait for 07:54 ET, or start today's run now:

```bash
./fm hermes kickoff                # creates today's cards (safe to re-run: same-day cards are reused)
hermes kanban --board faceless watch
```

Turn on the daily schedule:

```bash
hermes -p fm-lead cron list        # note the id of fm-kickoff
hermes -p fm-lead cron resume <id>
```

## Part 5: the dashboard

```bash
./fm dashboard serve --open        # http://127.0.0.1:8765, Ctrl+C to stop
hermes/setup/dashboard-service.sh install    # optional: keep it running, start at login
```

It is the same Apple-style Creator Earnings page as the Claude version: earnings, progress
to each payout program, credits, the next post time per platform, videos and niches. The
publisher refreshes its data every morning (`data/dashboard/*.json`), and the page reloads
it every minute. The **Accounts** card has the browser sign-ins. The server only listens
on this Mac (127.0.0.1).

---

## Daily timeline

| US Eastern | India (until Nov 1) | India (from Nov 1, US winter time) | What happens |
|---|---|---|---|
| 07:54 | 17:24 | 18:24 | Kickoff message in #faceless; cards created |
| ~08:00-08:15 | | | fm-research refreshes trends and policy |
| ~08:15-08:30 | | | fm-writer picks or writes the script(s) |
| ~08:30-09:15 | | | fm-producer makes the video(s) |
| ~09:15-09:30 | | | fm-publisher schedules posts and updates earnings; fm-lead posts the report |
| 12:30 pm / 4:00 pm / 6:00 pm / 7:30 pm | +9h30 / +10h30 | | Facebook / YouTube / TikTok / Instagram posts go out (weekday defaults; they adapt to your audience) |

The cron uses fm-lead's `timezone: America/New_York`, so the US daylight-saving change
needs no action.

## Talking to fm-lead in #faceless

| You type | It does |
|---|---|
| `status` | Today's cards and their state |
| `make a short about the new 401k limits for 2027` | Writer prepares one script, fm-lead quotes the credits; on your yes, production starts (say "and post it" to schedule it too) |
| `make one from inv-rule-of-72` | Same, from a library script |
| `TikTok paid $12.40 today` | Logs the payout, refreshes earnings, commits |
| `pause the autopilot` / `resume the autopilot` | Pauses or resumes the 07:54 cron |
| `switch to the standard tier` | Edits `config/production.yaml` after confirming |
| `is everything set up?` | Runs `./fm hermes doctor` |

Each card also posts a line when it finishes, and a blocked card explains what it needs.

## Command cheat sheet

```bash
./fm hermes doctor                           # setup checklist
./fm hermes kickoff [--dry-run] [--date D]   # today's cards (the cron runs this)
./fm hermes status [--date D]                # today's cards
./fm hermes request --topic "..."            # on-demand script (fm-lead uses this)
./fm hermes approve --task t_x --credits 32 [--post]
hermes kanban --board faceless list          # the board
hermes kanban --board faceless show <id>     # a card, with its handoffs and errors
hermes kanban --board faceless unblock <id>  # retry a blocked card
hermes -p fm-producer chat                   # talk to one bot directly (any profile)
./fm history | budget --balance N | timing plan | library stock | metrics collect --balance N
.venv/bin/python -m pytest -q
```

## Changing how it works

| To change | Edit |
|---|---|
| Niches, angles, hashtags | `config/niches.yaml` |
| Production tier, videos per day, narrators | `config/production.yaml` |
| Autopublish on/off, caption limits | `config/platforms.yaml` |
| Post slots and how they learn | `config/timing.yaml` |
| Board, stage time limits and retries, Discord channel | `config/hermes.yaml` |
| A bot's model, fallback, tools | `hermes/profiles/<bot>/profile.yaml`, then `hermes/setup/install.sh` |
| A bot's procedure | `hermes/skills/<skill>/SKILL.md` (read live, no reinstall) |
| A bot's personality | `hermes/profiles/<bot>/SOUL.md`, then `hermes/setup/install.sh` |

## Money and limits

- **Higgsfield Plus**: 1,000 credits a month, renewing on the 18th. The lean tier costs
  about 31 credits per 80-second video, so the budget paces about one video a day and
  keeps an 80-credit reserve. The producer card's limit is that day's budget plus 20%.
- **LLM plans**: a normal day is about 4 bot runs. Claude carries only the scripts, and
  GPT carries production; Grok (once working) carries research, publishing and chat.
- **Metricool**: needs a paid plan for one video a day on four platforms.
- **TikTok Creator Rewards** has no data feed. Tell fm-lead when a payout arrives.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Kickoff says "Higgsfield is not signed in" | `hermes -p fm-producer mcp login higgsfield` |
| Kickoff says "no publisher is signed in" | `hermes -p fm-publisher mcp login metricool` |
| Cards stay `ready` | The gateway hosts the dispatcher: `hermes gateway status`, then `hermes gateway restart` |
| A card is `blocked` | `hermes kanban --board faceless show <id>` shows why; fix it, then `unblock` |
| Nothing arrives in #faceless | `./fm hermes doctor` (route line), then `hermes gateway restart` |
| An OAuth sign-in expired | Run the same `mcp login` again; the bot picks it up on its next run |
| Every Grok bot is slow to start | Grok is failing over (see the note above) |

## Keeping up with the Claude version

The code started from the Claude branch. To pull later improvements made there:

```bash
git fetch origin
git merge origin/claude/compassionate-ptolemy-rf3q0u
.venv/bin/python -m pytest -q
```

The Hermes-only parts (`HERMES.md`, `hermes/`, `config/hermes.yaml`,
`pipeline/hermes_ops.py`, `pipeline/localdash.py`, `tests/test_hermes.py`) do not
conflict with it.

## What maps to what (Claude → Hermes)

| Claude Code instance | Hermes instance |
|---|---|
| One Claude session, `CLAUDE.md` | Five profiles, `HERMES.md` (Hermes reads it before `CLAUDE.md`) |
| `.claude/skills/autopilot` | `fm-research`, `fm-scripts`, `fm-produce`, `fm-publish` (one stage each) |
| `.claude/skills/make-short` | fm-lead's on-demand flow (`./fm hermes request` / `approve`) |
| Scheduled task at 07:54 ET in the session | fm-lead's `fm-kickoff` cron, no model, timezone-aware |
| Higgsfield connector | `mcp_servers.higgsfield` on fm-producer (OAuth) |
| Metricool connector | `mcp_servers.metricool` on fm-publisher (OAuth) |
| claude.ai Dashboard artifact | `./fm dashboard serve` (same page, local) |
| Metricool live data in the artifact | `data/metricool/<date>.json` → `./fm metrics collect` |
| Report at the end of the chat | fm-lead's report in #faceless |
| Branch `claude/compassionate-ptolemy-rf3q0u` | Branch `hermes/autopilot` |

## Uninstall

```bash
hermes -p fm-lead cron list    # then: hermes -p fm-lead cron remove <id>
for p in fm-lead fm-research fm-writer fm-producer fm-publisher; do hermes profile delete $p --yes; done
hermes kanban boards rm faceless
hermes/setup/dashboard-service.sh uninstall
```

Then remove the `faceless-channel` entry from `gateway.profile_routes` in
`~/.hermes/config.yaml` and restart the gateway.
