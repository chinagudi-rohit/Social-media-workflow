# Social-media-workflow

A daily autopilot that makes faceless short videos for the highest-paying Western niches
and posts them to TikTok, Instagram Reels, YouTube Shorts and Facebook Reels, then tracks
what they earn on the **Creator Earnings** dashboard.

```
research ─► budget ─► pick scripts ─► Higgsfield: keyframes + motion + voice ─► sandbox render ─► Metricool / Upload-Post ─► metrics ─► dashboard
(trends,    (credits   (50-script       (lean tier ≈ 32 credits / 80 s video)   (captions, Ken     (4 platforms, each at   (earnings,  (claude.ai)
 policies)   pacing)    library)                                                  Burns, loudness)   its best time, AI labels) views)
```

It runs inside Claude Code: Claude does the research and writing and drives the Higgsfield
MCP; a Python CLI (`pipeline/`) handles scoring, budgeting, plans, publishing and metrics.

## Why it is built this way

From `research/monetization-2026.md`:

- **Pick niches for money, not just views.** Finance, credit, insurance, real estate, AI
  tools and business earn 5-10× the ad revenue per view of entertainment. How-it's-made,
  history, science and psychology add reach. Each niche has an RPM tier and a reach tier.
- **Every video runs 65-80 seconds.** TikTok Creator Rewards pays only for videos over
  1 minute, so all 50 library scripts are 8 blocks of ~22 words.
- **One render, four platforms.** Each video goes to TikTok, Reels, Shorts and Facebook.
- **Stay monetizable.** YouTube demonetizes template and mass-produced content and AI
  personas giving finance, health or legal advice; TikTok excludes static slideshows. So
  scripts are sourced explainers with no persona, structures, narrators and visual styles
  rotate, hooks and key beats are animated, and every post carries the AI label.
- **Spend credits evenly.** The Plus plan gives 1,000 credits a month. The budget step
  spreads them across the cycle: about one video a day at the lean tier.

## Daily run

`/autopilot` (or the scheduled task) does, in order (`.claude/skills/autopilot/SKILL.md`):

1. **Research**: per-niche US trend search plus monetization-policy news, written to
   `data/trends/<date>.json` and scored.
2. **Budget**: `python -m pipeline budget --balance <credits>` decides today's count.
3. **Scripts**: best unused library scripts for the top niches, or a fresh script when a
   topic is trending; restocks thin niches.
4. **Produce**: Higgsfield keyframes (Seedream 4.5), 5-second animated moments (Seedance 2.0
   mini, image-to-video), one voiceover (ElevenLabs via Higgsfield), then
   `tools/assemble.py` in the Higgsfield sandbox renders 1080×1920 with whisper-timed
   captions and checks the result.
5. **Publish**: each platform scheduled at its own best time (below) through Metricool or
   Upload-Post.
6. **Earnings**: audience counts, YouTube revenue, Facebook earnings and logged payouts go
   into `data/metrics/` and the dashboard; each post's early views feed the post-time model.
7. **Commit** everything.

`/make-short` makes one video on demand with a cost confirmation.

## Post times (`config/timing.yaml`)

The scheduled run starts at 7:54 am US Eastern and finishes production by about 9 am. Each
platform's post then goes out at its own slot. Weekday defaults:

| Platform | Default slot (ET) |
|---|---|
| Facebook Reels | 12:30 pm |
| YouTube Shorts | 4:00 pm |
| TikTok | 6:00 pm |
| Instagram Reels | 7:30 pm |

Weekends use morning slots. The defaults come from published studies
(`research/monetization-2026.md` §8). Two more inputs re-rank them once they exist:

- When this account's followers are online (Metricool).
- How its own posts did by the hour they went out.

15% of posts try the runner-up slot so the model keeps learning.
`python -m pipeline timing plan` shows today's choice and why.

## Production tiers (`config/production.yaml`)

| Tier | What moves | Credits / video | Videos / month on Plus |
|---|---|---|---|
| **lean** (default) | Hook + 3 beats animated, other scenes slow camera moves | ~32 | ~28 |
| standard | Every scene opens animated | ~52 | ~17 |
| premium | Every scene fully animated | ~92 | ~10 |

Change `tier:` to switch. Upgrading to Ultra (3,000 credits) supports ~3 standard videos a day.

## Setup

The owner is in India, so the default `targets` are YouTube, Instagram and Facebook
(`config/platforms.yaml`):

- TikTok is blocked in India.
- TikTok Creator Rewards only pays accounts based in its eligible countries.
- YouTube and Facebook pay by where the viewers are. US viewers earn US rates.
- On YouTube, file the W-8BEN in AdSense to claim the India-US treaty. Google then
  withholds 15% of US-viewer earnings, instead of 24% of all earnings when no tax form
  is on file.

1. **Higgsfield**: connector added in Claude, Plus plan or higher (free trials cannot
   generate through the MCP).
2. **Publishing and analytics, signed in through the browser (recommended): Metricool.**
   - Add the Metricool connector in Claude (Settings → Connectors). Sign-in happens in the
     browser.
   - In Metricool, link YouTube, Instagram and the Facebook Page. Each one is a browser
     login. Set the brand's timezone to New York.
   - The dashboard's **Accounts** card links to both steps.
   - Metricool also gives the account's best posting hours and YouTube revenue. No keys
     are needed.
   - The Free plan only schedules 20 posts a month. Four platforms a day needs a paid plan.

   **Alternative: Upload-Post** (API key):
   - Create an API key and a profile.
   - Connect the four accounts in Upload-Post.
   - Add the `UPLOADPOST_*` variables (step 4).
   - TikTok needs a paid Upload-Post plan.
3. **Revenue data without Metricool** (optional):
   - YouTube: a Google OAuth client and a refresh token with the scopes
     `youtube.upload`, `yt-analytics.readonly` and `yt-analytics-monetary.readonly`.
   - Facebook: a Page access token with `read_insights` for a Page in Content Monetization.
   - TikTok Creator Rewards and affiliate payouts have no API: log them with
     `python -m pipeline earnings add --platform tiktok --amount 12.40`.
4. **Credentials**: for scheduled cloud runs, add the variables from `.env.example` in the
   cloud environment's settings (environment menu → Edit) as environment variables. For
   local runs, `cp .env.example .env`. `python -m pipeline check` shows what is missing.
5. **Network** (only for the API-key routes; cloud environment → Network access → Allowed
   domains): `api.upload-post.com`, `oauth2.googleapis.com`, `www.googleapis.com`,
   `youtubeanalytics.googleapis.com`, `graph.facebook.com`.
6. **Schedule**: a daily scheduled task runs the autopilot at 7:54 am US Eastern
   (`run_at` in `config/timing.yaml`).
7. **First run**: in a new session (connectors load at session start), type `/go-live`. It
   makes one test video, posts it everywhere and confirms each post. It also switches the
   dashboard to live data and moves the daily schedule into that session.

## CLI

```
python -m pipeline check | budget --balance N | history
python -m pipeline trends template|validate|score
python -m pipeline library validate|stock|pick --count N
python -m pipeline start-run SCRIPT_ID | gen-plan RUN | render-plan RUN
python -m pipeline set-video RUN --url URL --duration S | captions RUN
python -m pipeline timing plan | timing validate      # post times; audience file check
python -m pipeline publish-plan RUN                    # per-platform posts + times (Metricool)
python -m pipeline publish all RUN [--schedule auto] [--dry-run]   # Upload-Post
python -m pipeline record-post RUN --platform P --status S [--at ISO] [--id ID]
python -m pipeline post-stats RUN --platform P --views N
python -m pipeline publish youtube|instagram RUN          # direct APIs, no Upload-Post
python -m pipeline publish-status RUN
python -m pipeline earnings add --platform tiktok --amount 12.40
python -m pipeline metrics collect --balance N
```

## Layout

| Path | What |
|---|---|
| `research/` | Monetization research and the niche-by-platform viewership ranking |
| `config/niches.yaml` | 12 niches with RPM and reach tiers, styles, hashtags, disclaimers |
| `config/production.yaml` | Higgsfield plan, budget pacing, tiers, voices, render settings |
| `config/platforms.yaml` | Caption limits, AI labels, publisher, autopublish |
| `config/timing.yaml` | Run time, per-platform post slots, how audience data and results re-rank them |
| `config/dashboard.yaml` | Dashboard URL and dataset files |
| `library/scripts/` | 50 ready scripts; the autopilot adds more |
| `pipeline/` | CLI: trends, budget, library, production, publishing, metrics |
| `tools/assemble.py` | Renderer that runs in the Higgsfield sandbox (hosted copy pinned by hash) |
| `dashboard/index.html` | Source of the dashboard page |
| `brand/` | Worth Knowing: profile fields (`brand/youtube-profile.md`), art rendered by `brand/render.mjs` into `brand/out/` |
| `runs/<run_id>/` | One folder per video: script, plans, assets, captions, manifest |
| `data/` | Trend snapshots, audience posting hours (`timing/`), metrics snapshots, dashboard dataset files |

## Tests

```
pip install pytest && python -m pytest
```
