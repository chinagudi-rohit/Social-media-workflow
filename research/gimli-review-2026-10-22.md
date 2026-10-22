# Why the Gimli Glider looked like eleven different videos (2026-10-22)

The owner's review: every scene changes animation style, the shots are unrealistic, the
balance-scale clip (job `01fe0374…`, shot 2.2) hallucinates, no consistency at all. A frame
from each shot of the final video confirms it:

| Shot | What went wrong | Cause in the prompts |
|---|---|---|
| 1.2, 4.2, 5.1 vs 1.3 | The airliner changes livery: red tail and belly, then a blue diagram jet, then all white | The jet was never described once and reused; each shot invented it |
| 3.2 vs 2.1 | Quintal turns from a 3D character into a flat 2D cartoon with a different face | 3.2 was drawn on Z Image from text alone; 2.1 on Seedream. Two image models, no shared reference |
| 1.2, 2.2, 3.1, 4.2, 5.1 vs 1.1, 2.1, 4.1, 5.2 | Two renderings alternate (Z Image's semi-real 3D, Seedream's character 3D) | Z Image for most frames, Seedream for the hook and the character frames |
| 1.1, 4.1, 5.2 vs 2.1, 3.1, 3.2 | Sunset, then noon, then sunset | No time-of-day or light line shared by the frames |
| 2.2 | A brass scale on a blue studio backdrop, which then spins like a top | A symbolic prop outside the story's world; beats said "slams down", "tips hard" |
| 1.3 | A blue diagram wing, unlike any other frame | A cutaway on a plain backdrop instead of the story's jet |
| 5.1 | Race cars with cartoon eyes | The old style line's "expressive characters", plus a franchise look |

## What changed (in the pipeline, for every video from now on)

1. **One image model and one look.** The style key is on for every video
   (`tiers.quality.keyframe.style_key.mode: always`): one Seedream frame sets the look, and
   every keyframe is drawn on Seedream with it as image 1. About +3-4 credits a video.
2. **The asset lock.** A run script declares a `world` line (era, place, time of day, light;
   now required with a shot list), `props` (every object seen twice, with its exact look) and
   `places` (every location used twice), beside `cast`. The descriptions are pasted into every
   frame that uses them, and every character, object and place is drawn from the frame where
   it first appeared (up to 5 references per frame, made in waves).
3. **Stay inside the story world.** No symbolic props on studio backdrops; mechanisms are
   shown with objects in the scene. Time of day only moves forward.
4. **Plausible motion.** Object beats move the way the real thing would ("dips and settles",
   "goes slack"); both motion suffixes end "physically plausible motion at a natural speed",
   and rigid objects keep their exact shape.
5. **A consistency gate before motion.** The style key and every frame on one contact sheet;
   any frame off in style, face, livery, place or light is redrawn once before animating.

`runs/2026-10-21-history-mysteries-the-gimli-glider/script_v2.json` is the same story
rewritten under these rules (the jet, the fuel truck, the cockpit, the apron and the Gimli
strip locked; the scale shot replaced by Quintal working the numbers under the jet's wing).
Its plan: 12 Seedream frames in four waves, 10 clips, ~48 credits.
