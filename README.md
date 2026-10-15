# Social-media-workflow

Makes short vertical videos for US-audience niches and posts them as TikToks,
Instagram Reels and YouTube Shorts.

```
pick niche ─► research + write script ─► Higgsfield MCP video (9:16) ─► captions ─► post
 (rotation)     (Claude, with sources)     narrated or single clip                 TikTok · Reels · Shorts
```

The workflow runs inside Claude Code: Claude writes the script and drives the
[Higgsfield MCP](https://higgsfield.ai) to make the video. A small Python CLI
(`pipeline/`) handles niche rotation, script validation, captions, run tracking, and
publishing to Instagram and YouTube.

## Run it

In Claude Code, in this repo:

```
/make-short                      # next niche in the rotation, narrated 30s video
/make-short pets                 # a specific niche
/make-short clip                 # cheap single-clip format
```

The steps are in [`.claude/skills/make-short/SKILL.md`](.claude/skills/make-short/SKILL.md).
Claude asks before spending credits and before posting.

## Setup

1. **Python 3.10+**: `pip install -r requirements.txt`
2. **Higgsfield**: connect the Higgsfield connector in Claude, and have credits on the
   account. Connect TikTok through Higgsfield (Claude can run `tiktok_connect`).
3. **Credentials**: `cp .env.example .env` and fill in the platforms you use.
   `python -m pipeline check` shows what is missing.

### Instagram Reels

Needs an Instagram **Business or Creator** account linked to a Facebook Page, and a Meta
app with `instagram_basic` and `instagram_content_publish` permissions.

- `IG_USER_ID` — the Instagram business account id.
- `IG_ACCESS_TOKEN` — a long-lived user or system-user token.

The Higgsfield video URL is passed straight to Instagram, which downloads it.

### YouTube Shorts

Needs a Google Cloud project with the **YouTube Data API v3** enabled and an OAuth client
(type *Desktop app*).

- `YT_CLIENT_ID`, `YT_CLIENT_SECRET` — from the OAuth client.
- `YT_REFRESH_TOKEN` — get one with the
  [OAuth Playground](https://developers.google.com/oauthplayground): gear icon → *Use your
  own OAuth credentials*, scope `https://www.googleapis.com/auth/youtube.upload`, authorize,
  exchange for tokens.

Uploads from an unverified API project are locked to private until Google audits the
project. Each upload uses 1,600 of the default 10,000 daily quota units.

### TikTok

Posted through the Higgsfield MCP. Higgsfield requires a person to confirm each post in
its publish widget, so TikTok posting needs a client that shows MCP Apps widgets (the
Claude apps). Instagram and YouTube can post unattended.

## CLI

```
python -m pipeline check                       # credential status
python -m pipeline pick-niche [--niche ID]     # next niche + topics to avoid
python -m pipeline new-run --niche ID --topic "..."
python -m pipeline validate runs/<run_id>      # check script.json
python -m pipeline captions runs/<run_id>      # write captions.json
python -m pipeline set-video runs/<run_id> --url URL [--job-id ID] [--duration S] [--credits N]
python -m pipeline publish instagram|youtube runs/<run_id> [--dry-run]
python -m pipeline record-post runs/<run_id> --platform tiktok --status published --id ID
python -m pipeline history
```

## Layout

| Path | What |
|------|------|
| `config/niches.yaml` | US niches: audience, angles, style, hashtags, disclaimers, weights |
| `config/platforms.yaml` | Caption limits, privacy, AI-content labels, video format |
| `templates/script_guide.md` | How to write a script that works for US short-form |
| `templates/example_script.json` | A valid example script |
| `pipeline/` | CLI: rotation, validation, captions, publishers |
| `runs/<run_id>/` | One folder per video: `script.json`, `manifest.json`, `captions.json` |

## Tests

```
pip install pytest && python -m pytest
```
