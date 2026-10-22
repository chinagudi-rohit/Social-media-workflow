# Video quality audit: our first six Shorts against top rivals (2026-10-19)

The owner's verdict on the first uploads: the animation looks bad next to rival channels.
This file measures why, compares the videos with top faceless Shorts on the same themes,
and records the fixes now in the pipeline (shot lists, `quality` tier).

## 1. What our videos actually show

Measured from the posted files: one frame a second, frame-to-frame motion at 10 fps,
ffprobe for size and bitrate.

| Video | Length | Distinct pictures | Seconds per picture | Animated share | Notes |
|---|---|---|---|---|---|
| Car insurance deductible | 56 s | 8 | 7.0 | ~30% | clay diorama, abstract props (gauges with price tags) |
| Hear your name in a noisy room | 25.5 s | 3 | 8.5 | ~31% | faceless clay doll standing still for 8 s |
| What if the Sun disappeared | 36.4 s | 6 | 6.1 | ~45% | cartoon sun, NASA film in a blurred band, frozen ocean: four looks in one video |
| Why cards have 16 digits | 26.2 s | 3 | 8.7 | ~46% | no credit card ever shown: coins on a box, clay huts, beads |
| 1859 Carrington Event | 66.8 s | 7 | 9.5 | ~42% | painterly stills, people standing still, one picture per 10 s |

Every video also had:

- **Motion clips at 496x864** (Seedance Mini 480p), blown up 2.2x to 1080x1920, cut against
  1152x2048 stills: the picture visibly softens and sharpens at every cut.
- **"Living photo" motion.** Four-second clips where the subject sways or blinks; nobody
  does anything. Two thirds of the screen time was a still with a slow zoom, and the
  "cuts every 3.5 s" were crops of the same picture, so a viewer saw 3 to 8 pictures.
- **Metaphors instead of the subject.** "Every digit has a job" showed glass beads; "the
  bank that issued your card" showed clay huts. With on-picture text banned (AI garbles
  it), nothing on screen ever showed a number, a label or a diagram.
- **2.3-3.5 Mbps uploads**, veryfast CRF 20. YouTube and Instagram re-compress whatever
  they receive; a soft, low-bitrate source comes out mushier still.
- **Big captions in the middle of the frame** (96 px), often over the subject's face.

## 2. What the rivals do

Higgsfield scene-by-scene analyses of nine top Shorts from `research/shorts-2026.md` §7,
plus their vertical thumbnails. Six are animated explainers comparable to ours:

| Short | Theme | Length | Scenes | Seconds per scene | What every scene does |
|---|---|---|---|---|---|
| ecIwfilIkTY | ladder to space (what-if) | 150 s | 31 | 4.8 | one mascot climbs, falls, floats; diagrams with labels (40,000 km, 1,600 km/h) |
| h8v8SQH7eNQ | Dunning-Kruger (psychology) | 40 s | 11 | 3.6 | one mascot acts out each line: climbs "Mount Stupid", slides into the valley |
| xxC58MiSUiY | how elevators work | 47 s | 12 | 3.9 | clean 3D cutaway; each named part lights up as it is named, with a label |
| nwn3pnkcAMQ | Cold War (history) | 46 s | 12 | 3.8 | flat 2D illustration, a new scene per clause; 1-2 s shots in the hook |
| jHJJLNL6Bd8 | pyramid burger (Zack D. style) | 29 s | 7 | 4.1 | photoreal 3D hands perform each step as it is said; the camera orbits |
| ahVpc364DOk | Sun into a black hole | 66 s | 8 | 8.3 | live simulator screen recording with labels (the one slow exception) |

The pattern:

1. **A new picture every 3-5 s, 1-2 s in the hook.**
2. **The picture is the sentence.** Whatever the narrator says is literally on screen: the
   elevator's guide rails light up on "guide rails", the mascot slides on "slide down".
3. **Characters act.** They climb, fall, flinch and grin. The motion carries meaning; it is
   never ambient sway.
4. **One character and one style through the whole video**, often a channel mascot.
5. **Labels and numbers are graphics laid over the picture**, never painted into it.
6. **Bold, clean, high-contrast art**: one subject, simple background, readable on a phone.

## 3. Bake-off (same frames, credits from `get_cost`)

Keyframes, same prompt in a new direction ("Pixar-quality expressive character, bold
saturated colors, one clear subject, simple background"):

| Model | Credits | Result |
|---|---|---|
| Z Image | 0.15 | Clean and expressive at 1152x2048. **Default for most shots.** |
| Seedream 5.0 Flash 1k | 0.5 | Best acting in the face; takes reference images. **Hook frame and recurring characters.** |
| Nano Banana Flash | 1.0 | Good but busier; no gain. |

The change of art direction alone did more than any model change: the same Z Image that
drew the faceless clay dolls drew a readable, expressive character.

Motion, image-to-video from the same frame, prompt "he whips his head around, eyebrows
shooting up... camera pushes in":

| Model | Credits | Output | Result |
|---|---|---|---|
| **Hailuo 2.3 Fast, 768, 6 s** | **4.0** | 768x1366, 24 fps, 5.9 s | Real acting: turns away, spins back with a surprised face; stable character. **Default.** |
| Seedance 2.0 Mini, 720p, 5 s | 5.0 | 720x1280, 5.0 s | Also acts well (eye-roll, splash, push-in); strongest camera moves. **Retry model.** |
| Kling 3.0 Turbo, 720p, 5 s | 7.5 | (still rendering after 10+ min) | Slower and pricier; not needed. |
| Seedance 2.0 Mini, 480p, 4 s (old) | 2.0 | 496x864 | What the first videos used. |

Hailuo runs about five jobs at once; submit motion in groups of five.

## 4. What changed in the pipeline

| Problem | Fix | Where |
|---|---|---|
| 3-8 pictures a video | Every block splits into 2-3 **shots** of 5-13 words (3-4 s), each its own picture | `config/platforms.yaml` video.shots_*, `pipeline/script.py` |
| Stills with a zoom for 2/3 of the time | Every shot is animated; a clip plays slower (up to 1.5x) rather than freezing | `tools/assemble.py` units / plan_shots |
| Ambient sway | Each shot has an `action` (what the subject does + the camera) that leads the motion prompt | `pipeline/production.py` |
| Metaphors, no labels | Shots show the literal subject; numbers and names go in an `overlay` label popped in a box | `tools/assemble.py` overlay_events, Label style |
| Character changes every shot | `ref: "1.1"` draws a shot from an earlier shot's frame (Seedream reference) | `pipeline/production.py` |
| 480p clips, 2-3 Mbps | Hailuo 768p, lanczos upscale + light sharpen, near-lossless intermediates, final CRF 18 up to 12 Mbps | `config/production.yaml` quality tier, `tools/assemble.py` |
| Captions over faces | 84 px, 470 px from the bottom | `config/production.yaml` render.captions |
| Four looks in one video | One `visual_style` per video; footage only when it can fill the frame | `templates/script_guide.md` |

## 5. Cost and cadence

About 4.2 credits a shot: a 25-30 s video (7-9 shots) is ~32-40 credits, a 45 s video
(11-13 shots) ~50. The old reach tier made 12-credit videos. With ~1,000 credits a month
that is one strong video a day instead of two or three weak ones. Rival channels that grow
post about once a day, and a Short that viewers swipe away from in the first second gets
no reach however many of them go up. `cadence.max_videos_per_day` is now 2 and the budget
paces by pictures (`tiers.quality.typical`).

## 6. Pilot

The noisy-room video remade with a shot list:
`runs/2026-10-19-psychology-why-you-hear-your-name-across-a-loud-par`
([video](https://d2ol7oe51mr4n9.cloudfront.net/user_3KiaiPFpiBgipyl9nPlZn5fUZ7G/1330a011-5dad-4414-a7a3-4d17bb2521b4.mp4)).

| | Old (posted 2026-10-18) | Pilot |
|---|---|---|
| Length | 25.5 s | 26.1 s |
| Distinct pictures | 3 | 9 |
| Longest picture | ~10 s | 3.9 s |
| Animated share | ~31% | 100% (9 of 9 shots) |
| Clip resolution | 496x864 | 768x1366 (Hailuo), 720x1280 (hook shot, Seedance) |
| Look | faceless clay doll, strainer over a brain | one party-goer who acts, a brain mascot, a 1950s lab |
| Labels | none | "COCKTAIL PARTY EFFECT", "1959: 1 IN 3" |
| Video bitrate | 2.3 Mb/s | 5.1 Mb/s (CRF 18; flat cartoon colour compresses well) |
| Credits | 5.6 | ~42 |

Lessons from making it: Hailuo runs about five jobs at once (a sixth gets 429); a shot
whose character returns must say `ref`, or the second frame draws a different person
(shot 2.3 had to be redone); keyframes are cheap, so look at all of them before paying
for motion.
