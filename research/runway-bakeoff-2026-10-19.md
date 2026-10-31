# Runway bake-off and prompt rewrite (2026-10-19)

The owner connected Runway (Standard plan: 625 credits a month, plus a 300-credit top-up)
and allowed half the month's credits for tests. This note records what was tested, what it
cost, and what changed in the pipeline.

## 1. Cost per clip

Measured from the balance before and after each call, 5 s image-to-video at 720p:

| Model | Runway credits | Same model on Higgsfield |
|---|---|---|
| Gen-4 Turbo | 25 | (Runway only) |
| Gen-4.5 | 60 | (Runway only) |
| Kling 3.0 Turbo (sound on) | 70 | 7.5 |
| Hailuo 2.3 Fast, 768p, 6 s | (not run) | 4 |
| Music bed, Lyria 3 Clip (~31 s) | 4 | — |
| Sound effect, 1 s | 1 | — |

Runway resells partner models (Kling, Seedance, Veo) at about ten times Higgsfield's
price. A 9-shot video on Gen-4 Turbo would cost about 225 credits, a third of the month.
Runway cannot carry daily motion.

## 2. Motion: same keyframe, four engines

Motion energy is the mean frame-to-frame difference at 10 fps (higher = more happens on
screen). Contact sheets were read frame by frame.

**Stampede (emu video, shot 1.2, cartoon):**

| Clip | Motion | What happens |
|---|---|---|
| Hailuo, old prompt (posted) | 15.1 | emus bob in place, slight drift forward |
| Hailuo, **new prompt** | 23.3 | the flock charges, the lead emu rushes the lens |
| Gen-4 Turbo | 20.5 | charge and whip-pan, but the lead emu's design changes |
| Gen-4.5 | **27.2** | full charge, the lead emu's face fills the frame, the flock passes |
| Kling 3 Turbo | 14.3 | walking pace, one expressive close-up |

**Acting (party video, shot 1.1, cartoon character):**

| Clip | Motion | What happens |
|---|---|---|
| Seedance, old prompt (posted) | 6.7 | turns his back for two seconds, then a surprised face |
| Hailuo, **new prompt** | 6.1 | eye roll, eyes-closed sigh, then a fast push-in to a wide-eyed close-up |
| Gen-4 Turbo | 5.6 | small eye roll, mild surprise, no push-in |
| Gen-4.5 | 7.2 | eye roll, head snaps round, push-in to a big close-up by second 3 |

Findings:

1. **The prompt mattered more than the model.** The same Hailuo model on the same frame
   moved 54% more and did what the script said once the prompt described only motion,
   in beats, with a named camera move, and in positive terms.
2. Gen-4.5 is the best engine for big physical action, and level with new-prompt Hailuo on
   acting, at 15 times the price.
3. Gen-4 Turbo is not worth its 25 credits; Kling on Runway is the same Kling at ten times
   the price.

## 3. Prompt changes (config/production.yaml `prompts`, pipeline/production.py)

Sources: Runway's and MiniMax's image-to-video guidance as summarized by
[Atlabs](https://www.atlabs.ai/blog/how-to-prompt-with-runway-gen-4-image-to-video-a-comprehensive-guide),
[Runware](https://runware.ai/docs/models/runway-gen-4-5/guides/directing-motion),
[Akool](https://akool.com/blog-posts/minimax-hailuo-video-prompt-guide) and
[Hedra](https://www.hedra.com/models/video/minimax/hailuo-23), plus the test above.

- **Keyframes:** the shot's visual first, then the style, then the composition suffix
  (it used to open with the long style string, so every frame weighted the same words).
- **Hook frame** (the first picture) adds `hook_suffix`: subject at the peak of the moment,
  close and filling the frame, a vivid emotion or startling detail, high contrast,
  saturated complementary colours, rim light.
- **Motion:** the shot's action only, then `motion_suffix`. The style is no longer repeated
  (the start frame carries it), and the old "No text, no morphing, no extra limbs" is gone:
  video models tend to draw what a negative names. The new suffix says what should
  happen: motion from the first frame, weight and momentum, the same face and outfit,
  a steady background. The opening shot adds `motion_hook_suffix` (fast, punchy).
- **Script guide:** `visual` starts with the subject and catches the instant before the
  peak; the opening shot is close with an emotion or a startling detail; `action` is
  motion only, present tense, one beat then a second, one named camera move.

## 4. Audio: generated beds and effects

The assembler's synthesized lo-fi loop, whoosh and hit were the cheapest-sounding part of
each video. Six instrumental beds (curious, mystery, epic, money, wonder, playful; ~31 s
each, 4 credits each) and two effects (cut whoosh, opening hit; 1 credit each) were
generated, checked (full length, no gaps, no speech found by Whisper) and hosted on
Higgsfield. `render.audio.music` maps each bed to niches; the assembler loops the bed
with crossfaded seams, lands the whoosh's peak on each cut, and starts the hit on its
boom (`tools/assemble.py` `sample`, `loop_to`, `peak_at`). Total: 26 credits for a library
every video reuses.

## 5. Spend and what Runway is for now

Tests: 240 credits of video (the stampede on three Runway engines, the acting shot on two)
and 26 credits of audio: **266 of the 312-credit test allowance.** Runway balance after the
tests: 659 (625 plan + 300 top-up − 266). Higgsfield: 8 credits for the two new-prompt clips.

Runway's role from here (`runway` in config/production.yaml, autopilot step 4):

- **Music and effects:** new beds only when a niche has none that fits (4 credits each).
- **Hero hook shot:** when a video's opening shot is a big physical action (a stampede,
  crash, explosion, chase), animate shot 1.1 with Gen-4.5 (60 credits) while the Runway
  balance stays at or above `hero_shot.min_balance`; everything else stays on Hailuo.
- Not for daily motion, not for Kling, Seedance or Veo (same models are far cheaper on
  Higgsfield).
