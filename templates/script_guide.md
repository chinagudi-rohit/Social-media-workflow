# Writing a short-video script for a US audience

The script lives at `runs/<run_id>/script.json`. `python -m pipeline validate runs/<run_id>`
enforces the hard rules below; the rest is craft.

## Formats

| format     | What Higgsfield makes                                          | Length        | Cost   |
|------------|----------------------------------------------------------------|---------------|--------|
| `narrated` | Faceless narrated video: voiceover, keyframes with animated moments, burned captions | 2-9 blocks × 10s | ~32 credits (lean tier) |
| `clip`     | One generated clip; voiceover comes from the model's native audio | 5-30s         | Low    |

Default to `narrated` with **4-5 blocks** (85-115 words): about 30-40 seconds of speech with
the ElevenLabs voices (they read about 2.9 words a second). A story may run 6-8 blocks
(about 45-65 s) when every block turns the plot. Viewers watched 7-12 s on average whatever
the length, and videos of 30-45 s got the most views per hour so far
(`python -m pipeline insights`, length lift); follow that lift as it changes. Library
scripts must have at least
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

1. **Hook (0-2s)** — the first sentence of block 1. 15 words max, spoken from frame one,
   about "you" or the object on screen. A claim, a number, or a question the viewer needs
   answered. Patterns from top Shorts (`research/viral-ai-shorts-2026-10-20.md`):
   - "What happens if the cable holding your elevator snaps?" (what-if, the snap on screen)
   - "What really happens inside your body after eating ___?" (inside view promised)
   - "The ___ you use every day is ___." (myth break; only with a source that says so)
   - "Top student versus failing student. Who earns more by thirty?" (versus with a deadline)
   - "This $5 fix can cut an electric bill by ___." / "Here's what nobody tells you about ___."
   See "The first two seconds" below.
2. **Build (middle blocks)** — one idea per block, each escalating on the one before (if two
   blocks could swap places, rewrite). Concrete numbers, US examples. Every 8-15 s a
   **re-hook** turns the story: "But let's say they all snap at once.", "But in 1945…",
   "So how is the patient still alive?", "Age 24.". Past about 70% of the video, a second
   twist the viewer did not see coming.
3. **Payoff (last block)** — the answer, then a last line that rhymes with the opening (the
   same object or frame comes back) or lands a punchline: "So next time you step into an
   elevator, relax. The stairs are way more dangerous." No sign-off after it: none of the
   ten top Shorts studied ends on "follow" or "subscribe", and our loop endings beat the
   follow-line ending (`data/experiments/2026-10-quality-test/report.json`). The `cta`
   field still goes in the captions; spoken, it fits best right after the first payoff
   (about 40% in), or not at all.

Each block carries **19-24 words** of narration (about 7-8 s spoken), written to be
spoken, and splits into 2-3 shots (below). No lists of more than three items. No filler
("basically", "you know"), no word repeated within six words. More rules for the read
(`research/prompt-engineering-2026-10-21.md` §voice, Higgsfield's narration workflow on the
same ElevenLabs engine):

- **At most two sentences a block, comma-light.** The voice leaves about 0.7 s at every full
  stop and 0.5 s at every comma: one flowing clause reads faster and less choppy than three
  clipped ones. Keep the whole read under 2.9 words a second.
- **First sentence short.** The opening line states the hook flat in 8 words or fewer where
  it can (a what-if question up to 12); the block then fills out.
- **Every block pays rent:** one new concrete thing (a number, a name, a place, a mechanism,
  a comparison) the block before did not have. One modifier per thing. Too short? Add a
  fact, never an adjective.
- **Join beats with "but" or "so", never "and then"** (Parker and Stone's rule; Jenny
  Hoyos's conflict → resolve → new conflict). If two blocks could swap places, rewrite.
- **A through-line** (`through_line`, one line): one physical object that shows up in every
  block, changes as the story escalates, and pays off at the end (the sugar cube; the fuel
  gauge; a jar filling with coins). It is the thing the eye follows; give it the same words
  in every shot that shows it.
- `delivery` (optional): the narrator's read in a few words ("hushed, suspenseful storyteller,
  low warm timbre, unhurried"); without it the default in `config/production.yaml`
  `prompts.voice_delivery` is used. Never brackets or stage directions inside the narration.

### Shapes that travel (pick one per video; record it as `hook_type`)

- **what-if** — a disaster or impossible premise, shown happening in shot 1.1, then the
  chain of consequences. Best performer on this channel so far.
- **cutaway** (how it works, inside your body) — the hidden mechanism revealed: a wall
  removed, a cross-section, an X-ray body, a camera flying inside. The explanation is a
  chain (governor → rope → lever → wedges) with one **tracer** the eye follows from link to
  link: blue energy, a glowing molecule, a coloured arrow, the same seed. 7 of the 10 top
  Shorts studied had an inside view.
- **versus** — two rivals on the same path (top student vs failing student, $1M now vs a
  doubling penny), cross-cut in equal shots, with time stamps ("Day 15", "Age 24") as
  re-hooks and the numbers on props. This is how money topics go wide: a third-person
  story with checked maths, never advice to the viewer.
- **micro-story** — one person, one moment, a twist; holds viewers longest.
- **myth-flip** — the familiar thing is not what you think; the proof on screen.

## The first two seconds

Most viewers decide whether to stay within the first two seconds. Three things land in
that window, and the script controls all of them:

- **Spoken hook.** The first five words carry the stake: a number ("One percent can cost
  you…"), a consequence for the viewer ("Your deductible could be costing you…"), a myth to
  break, or a surprising fact ("Airplane windows used to be square."). No greeting, no
  title, no "did you know", no "in this video". An either/or question works only as a
  versus with both rivals on screen and a deadline ("…who earns more by thirty?"), never
  bare ("Roth or traditional?").
- **`on_screen_hook`.** 2-7 words, burned in big over the first 2.6 s, so a muted viewer
  gets the stake too. It adds to the spoken line instead of repeating it word for word.
  Wrap the one word that matters in stars: `"The deductible math *nobody* explains"`;
  numbers turn gold on their own.
- **Opening picture.** Shot 1.1 is mid-action, never set-up: the cable already snapping,
  the plug already going in, the scalpel already cutting. It is the most striking scene in
  the script and moves from its first frame. Make block 1's shots the shortest (5-8
  words): the hook cuts fastest.

Then keep them: promise the answer early, pay it off late, and let the last line lead back
into the first so a replay feels natural. A quiet music bed and a whoosh on each cut sit
under the voice; write actions that make a sound (sparks, a slam, a screech), so the edit
can put one on each.

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
- Copy how top Shorts are built, never their facts: two of the biggest studied (186M and
  170M views) told stories that are false (`research/viral-ai-shorts-2026-10-20.md`).

## Shot list (every run script)

Top faceless Shorts show a new picture every 3-4 seconds, the picture is literally what the
narrator is saying, and something in it acts. Ours had one picture per 8 s of metaphors
that barely moved, and lost (`research/quality-audit-2026-10-19.md`). So every block of a
run script carries `shots`: 2-3 of them, each covering 5-13 of its narration words.

```json
{"words": 7, "framing": "Extreme close-up, low angle", "visual": "...", "cast": ["Mia"],
 "beats": ["...", "...", "..."], "camera": "crash zoom", "sfx": "snap", "overlay": "4 = VISA",
 "ref": "1.1"}
{"words": 8, "framing": "Macro, side view", "visual": "...", "beats": ["...", "..."],
 "camera": "static", "counter": {"to": 3100000, "suffix": " MPH"}}
```

**Multi-shot clips (the default tier since 2026-10-22).** Each block becomes one clip of
its shots, joined by hard cuts and drawn from the video's roster pictures (each character,
object and place once, in the style key's look), so nothing changes look between shots. The
same fields apply, with three differences: there is no start frame, so each `visual` names
the subject, the place and the moment in full; `beats` are the shot's motion in order, slow
and continuous (Seedance is steadiest that way; one impact beat a block is enough); and a
block's clip holds at most 15 s, so keep blocks to 40 words or fewer and 2-4 shots. Aim the
video at ~95 words (30-40 s): clips are paid by the second.

The per-shot tiers turn each shot into two prompts: a **keyframe** (`framing: visual. Characters:
… style. suffix`) and a **motion** prompt timed beat by beat. Write both as a director's
shot list, frame by frame, not as a caption.

- `words` — how many narration words this shot covers, in order; a block's shots add up
  to its narration. Split at commas and full stops so each picture changes with the idea.
- `framing` — shot size, angle and lens, put first in the keyframe prompt: "Extreme
  close-up, low angle", "Wide shot, overhead", "Macro, side view", "Cross-section cutaway,
  straight on", "Over-the-shoulder of Mia" (only when Mia is in the shot). **Neighbouring
  shots never share a framing** (the validator checks): WIDE → CU → ECU → MEDIUM, with
  the angle changing too. Only the first shot in a new place is a wide establishing shot.
- `visual` — the first frame: **the literal subject of those words**, one clear subject in
  the middle third, simple background. A credit card shot shows a credit card; "the bank
  that issued it" shows a bank. Metaphors only when the narration is a metaphor. Name the
  subject, where it is in the frame, the one prop or detail that carries the fact, the
  light (rim light, single lamp, glow from inside) and the moment; leave the art style out
  (it is added from `visual_style`). Catch the instant just before the action peaks, so the
  clip has somewhere to go.
- **The opening shot stops the scroll.** Shot 1.1 is close, the subject fills most of the
  frame, and it holds a vivid emotion (shock, awe, panic) or a startling detail (wrong
  scale, something where it should not be). The pipeline adds high-contrast hook styling.
- `cast` + the script's `cast` — every recurring character gets one fixed description at
  the top of the script (`"cast": {"Mia": "30-year-old woman, short black bob, mustard
  raincoat, round red glasses"}`: age, build, hair, an outfit with colours and one
  signature item). Shots list who is in them and the description is pasted word for word
  into the keyframe prompt, so the face and outfit never drift. Two rivals get two outfits
  that read apart at a glance (white shirt vs black hoodie). Use with `ref` below.
- `beats` — the motion, **frame by frame**: 2-3 short lines in time order, spread over the
  first 4.5 s of the clip (the edit keeps at most 4.8 s of each 6 s clip), so the payoff
  lands in time. Pure choreography: the frame already shows who and where, so say only what
  moves. Elements enter one after another ("the lid lifts, then steam bursts out, then the
  dial spins"), with landing verbs (snaps into place, stamps down, drops with a bounce,
  cracks open, settles). Beat 1 moves on frame one; the last beat is the impact (a slam, a
  snap, a burst, a collapse). Characters act the sentence: they flinch, grin, grab, point,
  fall. Say what happens, never what should not ("no blur" tends to cause blur). Never
  "gentle motion" or "subtle sway". `action` (one line, a main beat then a second) still
  works for a simple shot. Writing only what moves, in beats, with one named camera move
  made the same Hailuo clip move about 50% more (`research/runway-bakeoff-2026-10-19.md`).
- `camera` — exactly one move per shot, by name: push in, pull back, crash zoom, zoom out,
  tracking, orbit, crane up, crane down, tilt up, tilt down, pan left, pan right, truck
  left, truck right, shake, static (`config/production.yaml` `camera_moves`). The pipeline
  writes it in words and, for Hailuo, as MiniMax's bracket command (`[Push in]`), which it
  follows more exactly than prose. Two moves in one shot read as AI soup. Use `static` when
  the subject's own motion is the point.
- `sfx` (optional) — the shot's own sound on its first frame, in place of that cut's whoosh:
  click, snap, ding, zap, thud, rumble, pop, coins, crack, splash, whoomp, tick, heartbeat,
  cash (`config/production.yaml` `render.audio.sfx`). Give one to the shots whose action
  makes a sound (the plug clicks in, the cable snaps, coins drop, the answer dings): about
  every other shot, never two loud ones in a row. Top Shorts give every visible action a
  sound.
- `overlay` (optional, 28 characters max) — a label popped over the shot: the number, name
  or term the narrator says ("COCKTAIL PARTY EFFECT", "8 MIN 20 S", "4 = VISA"). Generated
  pictures never contain text; labels are how numbers and names get on screen. Use one on
  roughly every other shot that carries a number or a term.
- `counter` (optional, instead of an `overlay`) — a number that counts up on screen and
  lands with a bounce, in the caption gold: `{"to": 3100000, "suffix": " MPH"}`, with
  optional `from` (default 0), `prefix` (3 characters max, "+$"), `suffix` (6 max) and
  `decimals` (0-2). Give it to the one or two shots where a big number is the payoff (the
  speed, the total, the weight); a count builds suspense a static label cannot. Not on
  block 1's first shot (the hook title covers it). Drawn with EffectCraft at render time.
- `ref` (optional) — an earlier shot id ("1.1" = block 1, shot 1) whose character returns
  here; the frame is drawn from that shot so the face, clothes and style match. Give a
  video one recurring character (a person, or a mascot such as a cartoon brain) and bring
  it back in the middle and at the end.
- `still: true` (rare, at most a quarter of shots) — a held frame for a label-only beat.

One `visual_style` per video, and it says only **how things look** (shading, materials,
light, palette), never what is in the frame: "Stylized 3D animated film look, soft rounded
shapes, smooth clean surfaces, bold saturated colors, strong rim light", or for objects and
processes "Hyper-realistic 3D render, macro detail, crisp material textures, dramatic soft
key light". Image models draw every noun in it into every frame ("expressive characters"
put a mascot on an airliner's wing), so characters belong in `cast`, objects in `visual`.
No studio, brand or franchise names anywhere in a prompt (a superhero walked into a clip
once). No clay dolls, no faceless figures, no dioramas. Archive footage only when it fills
the frame (`fit: crop`).

**One world, locked (the asset lock).** The Gimli Glider failed review (2026-10-22) because
every shot invented its own world: a red-tailed jet, then a blue one, then a white one; a
3D Quintal, then a flat one; sunset, then noon; a brass scale on a blue studio backdrop in
the middle of a cockpit story. Every run script therefore declares, once:

- `world` — one line every frame carries: era, place, time of day, light, palette ("Summer
  1983, Canada, late-afternoon sun turning to sunset, warm amber light").
- `cast` — every recurring character (as before).
- `props` — every object that appears in more than one shot, with its exact look ("Jet": "a
  white twin-engine Boeing 767 airliner with a red tail and a thin red stripe along the
  windows"). Shots list them in `props`.
- `places` — every location used more than once ("Cockpit": "the cockpit of a 1983 airliner,
  analog dials, amber panel light, side windows showing sky"). A shot names it in `place`.

The pipeline pastes these descriptions into every frame that uses them and draws each
character, object and place from the frame where it first appeared, after the video's style
key. So: **stay inside the story world.** Every shot happens in one of the story's places or
in the world line, never on a studio backdrop; explain a mechanism with an object that is
in the scene (the fuel slip with two numbers, the gauge going dark), or a cutaway of the
real object in its real place, not with a symbolic prop (a balance scale, a light bulb).
Keep the time of day moving one way only.

**Writing the `visual` (the keyframe).** Plain, concrete nouns, no metaphors: the subject
with its count, action and state, then what is in front of it and behind it (foreground,
subject, background: depth gives the clip room to move), then the one light source. Leave
empty space where the motion will go (above a falling object, ahead of a moving one).
Object-only shots end with "only the X in the room" or "empty street, only the Y": Z Image
ignores "no ..." phrases, and naming people, hands or faces puts them in. Frame the subject
in the upper middle; the bottom third carries captions and the platform's buttons.

**Writing `beats` (the motion).** Pure choreography with short nouns ("the pilot", "the
cube"): body parts and materials with range, speed and force ("hauls the yoke back hard",
"cracks race outward"), never feelings. Objects move the way the real thing would, at its
real speed: a scale "dips and settles", a hose "goes slack", never "slams" or "tips hard"
(the Gimli scale spun like a top). One movement per object. They are joined with "then", so each reads as the
next event. Never ask the clip for what the keyframe does not show: a `pull back` or
`zoom out` on an object shot invites the model to invent the rest of the room (strangers
walked into two such shots on 2026-10-21); use them only when the frame already holds the
wider scene.

Faceless videos never show a talking presenter; characters gesture, they do not speak.

## Captions

- `captions.hook_line` — first line of every caption (≤150 chars; Reels and Facebook show
  about that much before "more").
- `captions.body` — 1-3 sentences that add value beyond the video.
- `captions.comment_prompt` — one short question the account posts as the first comment on
  Instagram and Facebook (≤120 chars, ends with `?`). Ask for a guess or a side, never a
  personal money, health or legal situation: "Would you have heard the sun go out first, or
  felt it?"
- `youtube_title` — ≤100 chars; `#Shorts` is appended when it fits. No running time.
- `hashtags` — 2-4 topic tags, no `#`. Niche tags are merged in per platform limits.

## Example

See `templates/example_script.json`.
