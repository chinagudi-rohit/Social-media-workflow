# Writing a short-video script for a US audience

The script lives at `runs/<run_id>/script.json`. `python -m pipeline validate runs/<run_id>`
enforces the hard rules below; the rest is craft.

## Formats

| format     | What Higgsfield makes                                          | Length        | Cost   |
|------------|----------------------------------------------------------------|---------------|--------|
| `narrated` | Faceless narrated video: voiceover, keyframes with animated moments, burned captions | 2-9 blocks × 10s | ~32 credits (lean tier) |
| `clip`     | One generated clip; voiceover comes from the model's native audio | 5-30s         | Low    |

Default to `narrated` with **8 blocks**: about 55 seconds of speech with the ElevenLabs
voices (they read about 2.9 words a second). Library scripts must have at least
`video.library_min_blocks` blocks (`config/platforms.yaml`). Use `clip` only for a quick test or a video made by hand on
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
   - "Most Americans get this wrong about ___." (only with a source that says so)
   - "This $5 fix can cut an electric bill by ___."
   - "Here's what nobody tells you about ___."
   - "Stop doing ___ — do this instead."
   See "The first two seconds" below.
2. **Payoff (middle blocks)** — one idea per block. Concrete numbers, US examples.
3. **CTA (last block)** — end the narration with it: "Follow for one money rule a day."

Each block carries **19-24 words** of narration (about 7-8 s spoken), written to be
spoken, and splits into 2-3 shots (below). Short sentences. No lists of more than three
items.

## The first two seconds

Most viewers decide whether to stay within the first two seconds. Three things land in
that window, and the script controls all of them:

- **Spoken hook.** The first five words carry the stake: a number ("One percent can cost
  you…"), a consequence for the viewer ("Your deductible could be costing you…"), a myth to
  break, or a surprising fact ("Airplane windows used to be square."). No warm-up ("Today
  we're talking about…"), no bare either/or question ("Roth or traditional?").
- **`on_screen_hook`.** 2-7 words, burned in big over the first 2.6 s, so a muted viewer
  gets the stake too. It adds to the spoken line instead of repeating it word for word.
  Wrap the one word that matters in stars: `"The deductible math *nobody* explains"`;
  numbers turn gold on their own.
- **Opening picture.** Shot 1.1 is the most striking scene in the script and moves from
  its first frame. Make block 1's shots the shortest (5-8 words): the hook cuts fastest.

Then keep them: promise the answer early, pay it off late, and let the last line lead back
into the first so a replay feels natural. A quiet music bed and a whoosh on each cut sit
under the voice.

Titles never promise a running time ("in 80 seconds"): the voiceover sets the length.

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

## Shot list (every run script)

Top faceless Shorts show a new picture every 3-4 seconds, the picture is literally what the
narrator is saying, and something in it acts. Ours had one picture per 8 s of metaphors
that barely moved, and lost (`research/quality-audit-2026-10-19.md`). So every block of a
run script carries `shots`: 2-3 of them, each covering 5-13 of its narration words.

```json
{"words": 7, "visual": "...", "action": "...", "overlay": "4 = VISA", "ref": "1.1"}
```

- `words` — how many narration words this shot covers, in order; a block's shots add up
  to its narration. Split at commas and full stops so each picture changes with the idea.
- `visual` — the first frame: **the literal subject of those words**, one clear subject in
  the middle third, simple background. A credit card shot shows a credit card; "the bank
  that issued it" shows a bank. Metaphors only when the narration is a metaphor.
- `action` — what visibly happens in 4-6 s: the subject's action first ("she shouts and a
  golden ripple of sound crosses the room"), then the camera ("crash zoom into his face").
  Characters act out the sentence: they turn, flinch, grin, climb, drop things. Never
  "gentle motion" or "subtle sway".
- `overlay` (optional, 28 characters max) — a label popped over the shot: the number, name
  or term the narrator says ("COCKTAIL PARTY EFFECT", "8 MIN 20 S", "4 = VISA"). Generated
  pictures never contain text; labels are how numbers and names get on screen. Use one on
  roughly every other shot that carries a number or a term.
- `ref` (optional) — an earlier shot id ("1.1" = block 1, shot 1) whose character returns
  here; the frame is drawn from that shot so the face, clothes and style match. Give a
  video one recurring character (a person, or a mascot such as a cartoon brain) and bring
  it back in the middle and at the end.
- `still: true` (rare, at most a quarter of shots) — a held frame for a label-only beat.

One `visual_style` per video, and it is a character-animation look: "Stylized 3D animated
film look, Pixar-quality expressive cartoon characters, bold saturated colors, clean simple
backgrounds", or for objects and processes "Hyper-realistic 3D render, macro product
photography, dramatic soft key light, clean dark background". No clay dolls, no faceless
figures, no dioramas. Archive footage only when it fills the frame (`fit: crop`).

Faceless videos never show a talking presenter; characters gesture, they do not speak.

## Captions

- `captions.hook_line` — first line of every caption (≤150 chars; Reels and Facebook show
  about that much before "more").
- `captions.body` — 1-3 sentences that add value beyond the video.
- `youtube_title` — ≤100 chars; `#Shorts` is appended when it fits. No running time.
- `hashtags` — 2-4 topic tags, no `#`. Niche tags are merged in per platform limits.

## Example

See `templates/example_script.json`.
