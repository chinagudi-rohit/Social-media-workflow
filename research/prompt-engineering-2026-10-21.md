# Directing the tools: prompt engineering for every model we use (2026-10-21)

How to write the script, the keyframes, the motion, the voice, the music and the edit so each
tool in the pipeline does what we mean. Built from the vendors' own guides (MiniMax, ByteDance,
Tongyi, Runway, ElevenLabs, Google), Higgsfield's in-house faceless-video and narration
workflows (the same models and voice engine we call), and our own runs. Read-only research: no
credits spent. Claims a source could not confirm are marked *unverified*.

## 1. Method

Three research passes ran in parallel (video models; image models; Runway, voice, editing and
script), plus a read of Higgsfield's bundled workflow files (`faceless-video` SKILL.md,
`references/scriptwriter.md`, `references/vo_and_captions.md`, `narration`) and
`models_explore` for each model we call. Reddit blocked both search and fetch, so community
evidence is thin; vendor docs and our own clips carry the weight.

What `models_explore` says we can and cannot set:

| Model (our use) | Knobs | Not available |
|---|---|---|
| `minimax_hailuo` 2.3 Fast (motion) | duration 6/10, resolution 768/1080, start_image (end_image listed) | prompt_optimizer switch; MiniMax's first+last frame only works on Hailuo-02, so an end frame on 2.3 probably does nothing |
| `seedance_2_0_mini` (motion retry) | 4-15 s, 480p/720p, genre, generate_audio, start/end image, up to 9 image refs, video/audio refs | |
| `seedream_5_0_flash` (hook and character frames) | 1k-2k, aspect, image_references | seed |
| `z_image` (most keyframes) | aspect only | seed, negative prompt, references |
| `text2speech_v2` elevenlabs (voice) | voice_id, voice_type | rate, stability, model choice |

So consistency can only come from reference images plus identical wording, never seeds.

## 2. Rules every model agrees on

1. **Image-to-video prompts describe change, not the picture.** The start frame already fixes
   subject, look and light; restating them weakens the motion (Runway, Kling, Veo, MiniMax).
   Our 10-19 bake-off measured +54% motion from motion-only prompts.
2. **One main action, starting at once, then its consequence.** One scene per clip.
3. **Positive wording.** Describe what is there and what holds still ("locked camera", "only
   the scale moves", "empty room, only the table"), not "no X". Z Image ignores negatives
   entirely and draws every noun it is given.
4. **One camera move per shot**, written with "the camera" as the subject; Hailuo also takes
   MiniMax's 15 bracket commands, which it follows more exactly than prose.
5. **Concrete verbs with range, speed and force** for bodies and materials ("hauls the yoke
   back hard", "cracks race outward"), never feelings.
6. **No quality boosters** ("8K", "masterpiece") and **no studio, brand or franchise names**:
   they oversaturate or pull in the franchise (a superhero walked into our 10-21 impact clip).
7. **Don't ask for what the frame does not show.** A pull-back or zoom-out from a close object
   makes the model invent the rest of the room, people included (*unverified* as a rule;
   matches two of our four stranger clips).

## 3. MiniMax Hailuo 2.3 Fast (every animated shot)

- Template: `[Camera cmd] The <short noun> <action + speed/force>, then <consequence>, then
  <follow-through>. <What stays still>. <Style tag if stylised>.` About 25-60 words; the API
  caps prompts at 2,000 characters.
- Order beats with **"then"**: MiniMax's own examples chain events; per-second timings are not
  in its docs (and ByteDance calls them unstable on Seedance).
- Up to three bracket commands in one bracket act together; clashing moves break the clip.
- Strengths (MiniMax): body physics, micro-expressions, art styles, object motion. Weak spots:
  in-frame text (keep it out; labels go in the edit), more than a few people.
- Short style tag for stylised frames ("Stylized 3D animation.") keeps a cartoon start frame
  cartoon.
- **Ours, 10-21:** a suffix about "the same face, body and outfit" on shots with no character
  walked strangers into four object shots (one a superhero). Object shots now get "only what
  is already in the frame moves". Characters never talk: cast shots say "Characters emote and
  gesture with closed mouths" (Higgsfield's faceless workflow does the same).

## 4. Seedance 2.0 mini (motion retry)

- Formula: style, shot size, one camera move, subject action (body part + range/speed/force),
  consequence, sound or silence, a stability constraint. Constraint words are endorsed here
  ("face remains stable without deformation").
- **On 9:16 it tends to draw subtitles**: add "Keep it subtitle-free, with no on-screen text."
- Slow continuous motion is more stable than sprints and jumps; more than four people is
  unstable; multi-view character sheets cause twins.
- Multi-shot inside one clip ("Shot 1: … Shot 2: …" or "cut to") is its edge over Hailuo; not
  for our 4.5 s cut.

## 5. Keyframes: Seedream 5.0 Flash and Z Image

**Seedream** (hook frames, recurring characters): coherent natural sentences, subject → action
→ environment, then style, light, composition. With a reference, say what to keep from which
image: "Keep the character from image 1 exactly: …. New scene: …". Text renders only for 1-3
large words; numbers drift. Say where empty space goes ("large empty area above").

**Z Image** (most frames): a distilled model with no guidance, so **negative prompts do
nothing** and nouns are drawn literally ("real-looking hands" put hands everywhere;
"expressive characters" put a mascot on a wing). Longer concrete prompts work best: subject
with count and state, foreground / subject / background, camera and placement, one light
source, materials, palette. No metaphors. Contradictory styles ("photoreal cartoon") break it.

**The style line describes only the look.** All twelve niche `visual_style` lines named
content ("Pixar-quality expressive characters who act out each line", "hands and machines",
"a cute cartoon brain mascot") and a studio name. They now describe shading, materials, light
and palette only; characters live in `cast`, objects in `visual`.

**Characters across frames:** draw every frame of a character from its **first** frame (the
master), never from a copy of a copy; repeat the identity block word for word; keep the style
string identical.

**Composition for 9:16** (YouTube Shorts and Reels cover the bottom ~35% and the right ~18%
with their UI; top ~15% is the status area): subject in the upper middle (y 15-59%), a plain
darker lower third, space left in the direction of motion, the moment a split second before
the peak so the clip has somewhere to go.

## 6. Runway (hero shot, music, effects, edits)

- **Gen-4.5 image-to-video:** describe motion only; "The camera [move] as the subject
  [action]"; timestamps work ("[00:01] … [00:03] …"); "Continuous, seamless shot." stops stray
  cuts. 12 credits a second, 2-10 s.
- **Aleph edits** (remove a person, relight, restyle): action verb + target, works best with an
  edited keyframe. **28 Runway credits a second, 56 minimum**: a 4 s fix costs 18% of the
  625-credit plan, more than a whole Higgsfield video. Not a routine fix; regenerate on
  Higgsfield or trim before the intruder instead.
- **Music:** genre → mood → instrumentation → tempo in BPM and key → structure, every choice
  named; "instrumental only, no vocals"; for loops state bars, BPM and key and ban a lead
  melody. `lyria-3-clip` (4 credits) is the bed model.
- **Effects:** source → action → space ("dense metal cube slams onto a wooden table, sharp
  immediate impact, wood cracking, short room reverb"); one sound per generation; trim the
  leading silence in the edit.

## 7. Voice (ElevenLabs through Higgsfield)

- Higgsfield's narration workflow, on the same `text2speech_v2` ElevenLabs engine, prefixes
  every line with **one delivery bracket** repeated verbatim:
  `[curious, lively explainer, warm bright timbre, neutral accent, conversational pace, starts
  speaking immediately] …`. It sets the read, keeps the timbre stable and removes the leading
  pause. Which ElevenLabs model sits behind it is not exposed; on a pre-v3 model a bracket
  could be read aloud (*unverified*), so the render check compares spoken and written word
  counts and falls back to the bare narration.
- **Length is set by words, never by speed.** No rate knob; never time-stretch. Each full stop
  costs ~0.7 s of air and each comma ~0.5 s: comma-light, at most two sentences per block, one
  flowing clause where possible. Cap 2.9 words a second (top Shorts we measured: 2.8-3.2).
- Numbers as words in the narration (digits are read long and wrong); digits in captions.
- Performed tags (`[whispers]`, `[scoffs]`) cost ~1 s each and English only; one per 2-3
  sentences at most. Not adopted yet (§11).

## 8. Script craft

- **Through-line:** one physical object that appears in every block, escalates, and resolves
  in the payoff (a fuse burning down, a jar filling) — Higgsfield's scriptwriter makes it the
  first decision. It is what the eye follows from shot to shot.
- **Cold open short:** first sentence ≤ 8 words, the raw fact stated flat (a what-if question
  up to 12 for us; our what-ifs lead).
- **"But / so", never "and then"** (Parker and Stone; Jenny Hoyos's conflict → resolve → new
  conflict). The reorder test: if two build blocks could swap, it is a list.
- **Every block pays rent:** one new concrete thing per block; one modifier per thing; no
  filler. Too short? Add a fact, never an adjective.
- **Turn, then payoff that reframes the hook**; land it 2-3 s before the end and stop.
- Retention, not length, is the lever (Galloway: Shorts averaging over 50 s watched averaged
  4.1M views); Facebook benchmarks us at 8.1 s against 15.4 s for similar earners.

## 9. Editing grammar

- Frame 0 carries voice, motion and on-screen text together (9 of 10 top Shorts we measured
  speak at 0.0 s). A new picture every 2-4 s; a pattern break every 8-15 s.
- Sound on every cut; let the next shot's sound lead the picture by a few frames (J-cut).
- Captions 2-3 words, active word highlighted, bold with a stroke, **above the bottom 35%**.
  Ours sat at about 70-75% of the height, under the platforms' title and buttons; moved up
  (`margin_v` 470 → 680) with keyframe subjects moved to the upper middle.
- Numbers on screen at the payoff (labels and counters); many watch muted.
- -14 LUFS integrated, about -1 dBTP (ours: `loudnorm I=-14:TP=-1.5`); music 6-12 dB ducked
  under the voice.

## 10. What changed in the pipeline

| Finding | Change | Where |
|---|---|---|
| Hailuo and Seedance prefer ordered events to timings | beats chain "A, then B, then C" (`beat_style: then`; "timed" kept as an option) | `pipeline/production.py` `motion_text`, `config/production.yaml` |
| Brackets followed exactly | Hailuo's bracket command opens the motion prompt | `motion_text` |
| Stylised frames drift to live action | a short style tag after the action (`motion_style_tags`) | `motion_style_tag` |
| Seedance draws subtitles on 9:16 | retry model gets "Keep it subtitle-free…" (`motion_model_suffix`, `motion_retry.prompt_suffix`) | config, skill |
| Characters never talk | cast shots: "Characters emote and gesture with closed mouths" | `motion_suffix` |
| Z Image ignores negatives, draws nouns | keyframe suffix is all positive ("plain unmarked surfaces and blank screens") | `keyframe_suffix` |
| Safe zones | subject in the upper middle, plain darker lower third; captions `margin_v` 680 | `keyframe_suffix`, `render.captions` |
| Clip needs somewhere to go | hook frame caught "a split second before the peak" | `hook_suffix` |
| Seedream references: name what to keep | "Keep the character from image 1 exactly: … New scene:" | `ref_prefix` |
| Copy of a copy drifts | a `ref` is followed back to the character's first frame | `master_ref` |
| Style lines named content and a studio | all 12 niche styles and the experiment's cartoon set rewritten look-only | `config/niches.yaml`, `config/experiment.yaml` |
| Studio/brand names, child words | validator rejects `banned_words` in any prompt text | `pipeline/script.py`, config |
| One delivery bracket on the voice | `[delivery, starts speaking immediately]` before the narration; script/niche `delivery` overrides; word-count check catches a read-aloud bracket | `voice_prompt`, skill |
| Through-line, short first sentence, but/so, pays rent, comma-light | script guide rules; hook check | `templates/script_guide.md`, skill |
| Music and effect prompt order | written into the skill's music step | skill |
| Aleph too dear for routine fixes | QC rejects strangers, talking mouths, text; regenerate instead | skill |

## 11. Not adopted yet

- **A style key on every frame**: Higgsfield builds every asset on a reference "style key"
  image. For us that means Seedream on every keyframe (+~0.35 credits a frame, ~+3.9 a video)
  in place of Z Image. Worth a two-video test against today's look; needs the owner's yes
  outside the autopilot.
- **Per-block mood tags** (`[a bright knowing reveal]`, `[whispers]`) and CAPS emphasis:
  wait until the delivery bracket has proven itself on a few videos.
- **First + last frame** for transformations: not supported on Hailuo 2.3; Seedance mini has it
  at higher cost.
- **Seedance multi-shot clips**: one 6 s clip of several cuts; a different edit model.

## Sources

Video models: https://platform.minimax.io/docs/api-reference/video-generation-i2v.md ·
https://platform.minimax.io/docs/api-reference/video-generation-fl2v.md ·
https://www.minimax.io/news/minimax-hailuo-23 ·
https://docs.byteplus.com/en/docs/ModelArk/seedance-2-0-prompt-guide ·
https://fal.ai/learn/tools/seedance-2-0-prompting-guide ·
https://help.runwayml.com/hc/en-us/articles/39789879462419-Gen-4-Video-Prompting-Guide ·
https://docs.cloud.google.com/vertex-ai/generative-ai/docs/video/video-gen-prompt-guide ·
https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1 ·
https://kling.ai/quickstart/image-to-video-guide · https://kling.ai/blog/kling-ai-prompt-guide ·
https://help.scenario.com/en/articles/minimax-hailuo-video-the-essentials

Image models: https://www.volcengine.com/docs/82379/1829186 ·
https://blog.fal.ai/seedream-5-0-lite-prompting-guide ·
https://docs.gmicloud.ai/model-quickstarts/image/seedream-5-0-pro.md ·
https://huggingface.co/Tongyi-MAI/Z-Image-Turbo ·
https://huggingface.co/spaces/Tongyi-MAI/Z-Image-Turbo/blob/main/pe.py ·
https://github.com/Tongyi-MAI/Z-Image · https://fal.ai/learn/devs/z-image-turbo-prompt-guide ·
https://runware.ai/docs/learn/image-to-video ·
https://www.socialync.io/tools/safe-zones/youtube-shorts ·
https://www.inro.social/tools/instagram-reels-safe-zone-checker

Runway, voice, editing, script:
https://help.runwayml.com/hc/en-us/articles/48324313115155-Image-to-Video-Prompting-Guide ·
https://help.runwayml.com/hc/en-us/articles/52150503729171-Aleph-2-0-Prompting-Guide ·
https://help.runwayml.com/hc/en-us/articles/51683104370451-Creating-with-Edit-Studio ·
https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices ·
https://elevenlabs.io/docs/best-practices/prompting ·
https://elevenlabs.io/docs/overview/capabilities/music/best-practices ·
https://elevenlabs.io/docs/overview/capabilities/sound-effects ·
https://docs.cloud.google.com/vertex-ai/generative-ai/docs/music/music-gen-prompt-guide ·
https://techcrunch.com/2025/03/26/youtube-is-changing-how-youtube-shorts-views-are-counted ·
https://www.digitalinformationworld.com/2023/04/paddy-galloway-decoded-youtube-shorts.html ·
https://vidiq.com/blog/post/how-jenny-hoyos-gets-10m-views-per-youtube-short/ ·
https://writerunboxed.com/?p=35610

Higgsfield workflows (read with `get_workflow_bundle_file`): `faceless-video` SKILL.md,
`references/scriptwriter.md`, `references/vo_and_captions.md`; `narration` SKILL.md.

Our own evidence: `data/insights/lessons.md`, `research/runway-bakeoff-2026-10-19.md`,
`research/viral-ai-shorts/measurements.json`, runs of 2026-10-21 (`assets.json` `redone`).
