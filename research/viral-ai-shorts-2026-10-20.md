# What makes AI-made learning Shorts go viral (2026-10-20)

The owner asked: study viral AI-generated Shorts in our learning niches and pull in what
works: script, hook, and more detailed, frame-by-frame prompts for the video models.

## Method

- **Finding winners.** YouTube searches sorted by views (2026 uploads, Shorts) and a scan
  of each candidate channel's latest 400 Shorts with `yt-dlp` in the Higgsfield sandbox
  (view counts as of today). Keyword search was noisy (ads, kids songs, Indian cartoons),
  so channels were the better unit.
- **Taking 10 apart.** Higgsfield scene-by-scene analyses (`analyses/<id>.json`, verbatim),
  plus our own measurements (`measurements.json`): ffmpeg scene cuts, Whisper word timings,
  the frames at 0, 0.5, 1.5 and 3 s.
- **Prompt grammar.** Higgsfield's own `faceless-video` workflow (v2.4,
  `references/prompts.md`), MiniMax's documented Hailuo camera commands, and public
  Kling/Veo prompt guides (sources at the end).

## The channels

| Channel | Look | Subs | Median views per Short (last 400) | Top Short |
|---|---|---|---|---|
| FactoHolic | presenter + 2D/stock, shock facts | 22.9M | 20,000,000 | "World's Most Expensive School 😱" 201M |
| Zack D. Films | human-made 3D, absurd mechanisms | 29.3M | 10,000,000 | "Toucan Gets A Custom Artificial Beak" 56M |
| Professor Of How | 3D explainers, X-ray bodies, news cases | 16.0M | 8,700,000 | "Even a simple hit… SO MUCH painful? WHY?" 194M |
| Between The Thoughts | 3D surgery / inside the body | 193k | 29,000 | "Your Heart Is Removed… So How Are You Still Alive?" 23M |
| if_true | AI skeletons, money "versus" stories | 49k | 37,000 | "A-student or C-student? who make money?" 6.3M |
| BlueNova | 3D inside-the-body | 9k | 2,200 | "What Happens If You Eat Chia Seeds Every Day?" 6.9M |
| CUTAWAY | 3D cutaway mechanisms | – | – | "What Happens If an Elevator Cable Snaps?" 1.3M in 10 days |

Small channels break out on single videos (BlueNova: a 6.9M hit against a 2,200 median),
which matches our own all-or-nothing YouTube results.

## The ten Shorts taken apart

| Short | Views | Length | Scenes (s each) | Cuts measured (s per shot) | Opening (first 3 s) |
|---|---|---|---|---|---|
| FactoHolic "Oreo is FAKE 😱" | 186.9M | 60 s | 15 (4.0) | 27 (2.1) | "The Oreo you are eating today is fake, because the real Oreo closed down in 1999." |
| FactoHolic "Man Who Ate A Entire Plane 😱" | 170.0M | 67 s | 17 (3.9) | 36 (1.8) | "This man you're seeing isn't a human, he's a monster…" |
| Professor Of How "How do Fish Breath Underwater?" | 69.0M | 54 s | 11 (5.0) | 8 (6.0) | a man's head held underwater: "If you were held underwater by your head like this…" |
| Professor Of How "Bryan Johnson Experiments" | 45.0M | 85 s | 14 (6.1) | 12 (6.6) | money figure + taboo body detail over an X-ray body |
| Zack D. Films "How Electrical Outlets Work 🤔" | 39.5M in 2 days | 24 s | 9 (2.7) | 0 hard cuts detected | no words: a plug goes in, the wall becomes a cross-section, a hamster powers the grid |
| Between The Thoughts "Your Heart Is Removed…" | 23.9M | 64 s | 12 (5.3) | 12 (4.9) | the scalpel already cutting |
| BlueNova "Chia Seeds Every Day?" | 6.9M | 30 s | 14 (2.1) | 6 (4.3) | "What really happens inside your body after eating chia seeds?" then a POV down the throat |
| if_true "A-student or C-student?" | 6.4M | 63 s | 19 (3.4) | 23 (2.7) | "Top student versus failing student. Who will earn more by the age of 30?" |
| if_true "$1M Now vs Doubling 1¢" | 1.8M | 92 s | 14 in 46 s (3.3) | 15 (5.7) | "A million now or one cent that doubles every day? Who ends up with more?" |
| CUTAWAY "Elevator Cable Snaps?" | 1.3M | 86 s | 17 (5.1) | 21 (3.9) | the cable fraying and bursting on "…the cable holding your elevator snaps?" |

All narrated ones speak on frame one, at 2.0-3.2 words a second (ours: 2.9). Scene counts
are coarse; real cuts are faster. FactoHolic, Professor Of How (Hindi narration) and
Bryan Johnson are Indian-audience videos; their structure transfers, their topics do not.

## Eleven patterns that repeat

1. **Frame one is mid-action, never set-up**: the cable snapping, the plug going in, the
   scalpel cutting, a head held underwater (6 of 10).
2. **A hook of 15 words or fewer, spoken at 0 s, aimed at "you" or the object on screen.**
   No greeting, title card, "did you know" or "in this video" in any of the ten.
3. **An inside view reveals the hidden mechanism** (7 of 10): a wall turned cross-section,
   an X-ray body, a camera flying down the throat, the elevator shaft cut open.
4. **The mechanism is a chain with a tracer** the eye follows from link to link: blue
   energy (hamster → belt → generator → cable → phone), molecules, coloured arrows, the
   same glossy seed.
5. **Locked characters; colour is identity.** White vs gold skeleton, black suit vs green
   shirt, cowboy hat + yellow vest, blue scrubs. Outfits change only to mark a status jump
   (graduation gown, a suit when rich).
6. **Versus, cross-cut in equal shots**: two rivals on the same path, same backdrop,
   mirrored poses. This is how money topics went viral (6.4M, 1.8M): a third-person race
   with numbers, not advice.
7. **Time stamps and numbers ride on props**: "Age 24", "Day 15", "1854", "75 floors", a
   phone reading -$2,500.00, a "25%" battery.
8. **A re-hook every 8-15 s and a second twist past ~70%**: "But let's say they all snap at
   once.", "But in 1945…", "So how is the patient still alive?"
9. **A fast clock**: scenes of 2-4 s up to about a minute; any shot held past ~6 s moves.
10. **The ending rhymes with frame one or lands a punchline**, and none ends on "follow" or
    "subscribe": the coin returns, the battery dings, "The stairs are way more dangerous."
    Calls to action, when present, sit mid-video (0:09, 0:19) or point to the comments.
11. **Every visible action has a sound** (Zack D.: click, whip crack, paw patter, buzz,
    whoosh, ding; the music drops out at the payoff).

**Caution.** The two biggest (186M, 170M) tell false stories (Hydrox was Sunshine's 1908
biscuit, Oreo Nabisco's 1912 one; there were no rival brothers). Copy the build, never the
facts. The Bryan Johnson video is sexual-health content and not ad-friendly.

## How the prompts are written (the frame-by-frame part)

Higgsfield's own faceless-video workflow writes each 10 s clip as five timed, hard-cut
shots for MiniMax H3:

```
SHOT 1 — 0.0s to 2.0s — {SIZE+ANGLE}: {beat}.
HARD CUT.
SHOT 2 — 2.0s to 4.0s — {DIFFERENT SIZE+ANGLE}: {beat}.
…
```

Its rules that carry over to our one-keyframe-per-shot pipeline:

- **Every cut changes size and angle** (WIDE → CU → ECU → MEDIUM); only the first shot in
  a new place is an establishing wide; over-the-shoulder only when that character is on
  screen (otherwise the model invents a person).
- **Beats are pure choreography**: the style owns the look, so no colour or material words
  in the action. Elements enter one after another ("A, then B, then C") with landing verbs
  (snaps into place, stamps down, drops with a bounce, settles).
- **Exactly one camera behaviour per shot**; two moves in one cut "reads as AI soup".
- **One impact beat per clip** (slam, stamp, snap, collapse), echoed by a sound.
- **One fixed style formula pasted byte-identical in every prompt** plus reference images
  is the whole consistency method; the same goes for each character's description.
- Motion starts on frame one; a frozen opening is regenerated.

MiniMax documents 15 bracketed camera commands for Hailuo 02 / 2.3 / 2.3 Fast ([Push in],
[Pull out], [Zoom in], [Zoom out], [Pan left/right], [Tilt up/down], [Truck left/right],
[Pedestal up/down], [Shake], [Tracking shot], [Static shot]), up to three combined in one
bracket, and says they are followed more exactly than prose. Kling and Veo guides agree on
the rest: in image-to-video, spend the words on motion, not on what the frame already
shows; one beat per clip; name what stays still.

## What changed in the pipeline

| Pattern | Change | Where |
|---|---|---|
| Frame-by-frame motion | Shots take `beats`: 2-3 lines timed across the first 4.5 s (the edit keeps at most 4.8 s of each 6 s clip), e.g. "0-1.5 s: … 1.5-3 s: … 3-4.5 s: …" | `pipeline/production.py` `motion_text`, `config/production.yaml` `beat_window` |
| One camera move, exact syntax | Shots name one `camera` move; the prompt gets it in words and, for Hailuo, as MiniMax's bracket command | `camera_moves`, `camera_bracket_models` |
| Size and angle change every cut | Shots take a `framing`, put first in the keyframe prompt; the validator rejects two neighbours with the same framing | `pipeline/script.py` |
| Locked characters (5) | A script-level `cast` of fixed descriptions, pasted word for word into each keyframe that lists the character (with `ref` for the face) | `production.cast_line` |
| Hooks, re-hooks, endings (1, 2, 8, 10) | Hook examples from the winners; build/re-hook/second-twist structure; end on a loop or punchline, never a spoken follow line | `templates/script_guide.md`, autopilot skill hook check |
| Shapes (3, 4, 6) | "Shapes that travel": what-if, cutaway with a tracer, versus for money topics, micro-story, myth-flip | `templates/script_guide.md` |
| Sound on actions (11) | Shots take an `sfx` from a 14-effect sound sheet, played on the shot's first frame in place of the cut's whoosh | `tools/assemble.py`, `render.audio.sfx`, `templates/script_guide.md` |

## Not adopted yet, and why

- ~~Per-shot sound effects~~: done 2026-10-21. 14 effects made with Runway sound effects
  (18 credits) in one hosted sound sheet; a shot's `sfx` plays its slot on the shot's first
  frame instead of that cut's whoosh (`tools/assemble.py`, `render.audio.sfx`).
- **Multi-shot clips** (Higgsfield's five cuts in one 10 s MiniMax H3 clip): a different
  production path at 2K whose credit cost per shot is unknown here; worth a one-video
  bake-off against our keyframe + Hailuo path before switching.
- **2-second shots throughout**: our hook shots are already the shortest; the length lift
  (30-45 s best) and the 4.8 s shot cap stay until a test says faster cuts win.
- **Emoji in titles**: three of the seven channels use one (😱 🤔 🤯), four do not; no
  evidence either way, so it is not a rule.

## Sources

- Analyses and measurements: `research/viral-ai-shorts/analyses/*.json`,
  `research/viral-ai-shorts/measurements.json` (Higgsfield video analysis, yt-dlp, ffmpeg,
  faster-whisper; 2026-10-20).
- Higgsfield `faceless-video` workflow v2.4, `references/prompts.md` (read through the
  Higgsfield MCP).
- Hailuo camera commands: https://www.hedra.com/models/video/minimax/hailuo-23 ;
  https://minimax-ai.chat/models/minimax-hailuo-23-fast/ ;
  https://www.kapwing.com/resources/how-to-prompt-minimax-h3-hailuo-3-0-a-guide-for-ai-video-creators/
- Kling image-to-video: https://kling.ai/quickstart/image-to-video-guide ;
  https://morphed.app/blog/kling-ai-prompt-guide ; https://www.leonardo.ai/news/kling-ai-prompts/
- Veo timestamp prompting: https://skills.sh/leegonzales/aiskills/veo3-prompter ;
  https://ltx.io/blog/veo-prompt-guide
- AI skeleton format: https://ghostshorts.com/blog/what-are-skeleton-ai-videos-2026
- Hooks and open loops (vendor blogs, directional only):
  https://www.socialync.io/blog/open-loops-in-content-2026 ;
  https://aibrify.com/blog/youtube-shorts-retention-curve-playbook
