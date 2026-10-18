# Writing a short-video script for a US audience

The script lives at `runs/<run_id>/script.json`. `python -m pipeline validate runs/<run_id>`
enforces the hard rules below; the rest is craft.

## Formats

| format     | What Higgsfield makes                                          | Length        | Cost   |
|------------|----------------------------------------------------------------|---------------|--------|
| `narrated` | Faceless narrated video: voiceover, keyframes with animated moments, burned captions | 2-9 blocks × 10s | ~32 credits (lean tier) |
| `clip`     | One generated clip; voiceover comes from the model's native audio | 5-30s         | Low    |

Default to `narrated` with **8 blocks**: about 65-80 seconds of speech. TikTok's Creator
Rewards only pays for videos over 1 minute, Facebook rewards longer watch time, and YouTube
Shorts allows up to 3 minutes, so 8 blocks earns on every platform. Library scripts must
have at least 7 blocks. Use `clip` only for a quick test or a video made by hand on
higgsfield.ai (a 30s Wan 3.0 clip with native audio can carry a short voiceover).

## Clip with voiceover

- One block. `narration` is spoken word for word by the model: about **2.2 words per
  second** of clip, so 60-66 words for 30s, 30-33 for 15s. Numbers read slower; write
  them as words ("two hundred forty-four thousand").
- `visual` is a shot list with timestamps (`SHOT 1 (0-4s): …`), one action per shot,
  about 5 seconds each. Ask for no on-screen text: video models garble letters, so
  numbers go in the voiceover and the subtitles.
- Save the full model prompt to `runs/<run_id>/prompt.txt`.

## Structure of a narrated script

1. **Hook (0-2s)** — the first sentence of block 1. 15 words max. Make a claim, a number,
   or a question the viewer needs answered. Patterns that work with US viewers:
   - "Most Americans get this wrong about ___."
   - "This $5 fix cut my electric bill by ___."
   - "Here's what nobody tells you about ___."
   - "Stop doing ___ — do this instead."
2. **Payoff (middle blocks)** — one idea per block. Concrete numbers, US examples.
3. **CTA (last block)** — end the narration with it: "Follow for one money rule a day."

Each block is exactly 10 seconds of video and carries **19-24 words** of narration,
written to be spoken. Short sentences. No lists of more than three items.

## US-audience rules

- Dollars (`$`), miles, °F, US date format, US spelling.
- Reference US institutions correctly (IRS, FDA, NPS, 401(k), Roth IRA, HSA).
- Prefer "most Americans", state names, and US cities over generic phrasing.
- Time topics to the US calendar: tax season (Jan-Apr), summer travel, back to school,
  Thanksgiving, holiday shopping, New Year resolutions.

## Accuracy and compliance

- Every factual claim needs a source in `sources` (gov, `.edu`, or a reputable outlet).
  Check numbers are current for the year you are posting.
- Finance, health, tax and legal niches: no promises of returns or outcomes; the niche
  disclaimer is added to captions automatically.
- No real brand logos, celebrities, or copyrighted characters in `visual` prompts.
  Describe the look instead.
- Do not repeat a topic listed in `recent_topics` from `pick-niche`.

## Visual prompts

`visual` describes what is on screen for that block: setting, subject, action, camera.
Faceless videos never show a talking presenter; characters gesture, they do not speak.
Keep the niche's `visual_style` consistent across blocks.

## Captions

- `captions.hook_line` — first line of every caption; also the TikTok title (≤150 chars).
- `captions.body` — 1-3 sentences that add value beyond the video.
- `youtube_title` — ≤100 chars; `#Shorts` is appended when it fits.
- `hashtags` — 2-4 topic tags, no `#`. Niche tags are merged in per platform limits.

## Example

See `templates/example_script.json`.
