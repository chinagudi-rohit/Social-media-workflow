# three.js motion graphics (2026-10-26)

Source: Matt Penny, "Claude + Three.js = Premium 3D Motion Graphics" (YouTube CCUSpJkAfgU,
12:19, uploaded 2026-10-15). It was watched with the `watch` skill in the Higgsfield sandbox:
the downloaded video gave 39 scene frames and 44 cue frames (the on-screen prompts were read at
full 1280 px), with a faster-whisper transcript.

## The method

- Every element is code. Claude writes a web page; three.js draws the 3D; a hidden browser
  (Playwright) screenshots each frame; ffmpeg joins them. `tools/motion3d/render.mjs` does
  exactly this, with every animation a function of a time value `t` (deterministic).
- His five demos: a glassmorphism "idea to app" flythrough, liquid-metal balls explaining an
  LLM (vertical), a clay "How RAG works", a paper-texture gradient-descent landscape, and a
  holographic globe that routes packets between real cities. Each one is 15 s, 1920x1080, 60 fps.
- Claimed cost: 37k output tokens for a 15 s clip, about $0.74 at API prices or about
  $0.05 on a subscription. Seedance 2.5 would be about $1.50 for the same clip, and every
  edit costs that again.

## What his prompts specify (the parts that make it look premium)

1. Format and determinism: length, resolution, fps, "render frame by frame to MP4 with
   Playwright and ffmpeg, every animation driven by a time value t".
2. A named style with exact colours: "soft light premium clay", "holographic sci-fi",
   "glassmorphism"; pastels plus one accent hex.
3. Materials by name. Clay is MeshPhysicalMaterial with sheen, plus `onBeforeCompile` for a rim
   light and a noise dissolve with glowing edges. Glass is transmission with roughness about
   0.4, on rounded extruded slabs. Reflections come from RoomEnvironment.
4. The studio: a backdrop dome with a GLSL gradient, a ShadowMaterial floor with a dotted grid
   fading with distance, a hemisphere light, a key light with VSM shadows and a cool fill.
5. Camera: keyframed positions and look-at targets. It drifts slowly within a scene and whips
   between scenes (expo ease). Objects move too, not just the camera.
6. A numbered story with second ranges per beat ("1. Intro (0-3s): ..."). Each beat names the
   geometry (InstancedMesh, TubeGeometry along Bezier or CatmullRom curves, Points with a custom
   shader), not just the idea.
7. Text: a 2D layer drawn every frame over the 3D, after tone mapping. Labels are pinned by
   projecting 3D positions to the screen.
8. Finish: a half-float HDR target with 4x MSAA, UnrealBloom with a high threshold, neutral tone
   mapping, then film grain, vignette and slight chromatic aberration. Clamp anything fed to
   `pow()` so shaders never produce NaN.
9. A verification loop: "keep text readable and away from 3D objects; check still frames from
   every scene before rendering the full clip".
10. Tips: say "use three.js and shaders"; "make it professional and sleek"; "pretend this is
    your showreel for a motion-graphics job you really want"; use the strongest model.

## Our version

- `tools/motion3d/scenes/kit.js` has the finish chain (`makeRenderer({tone, msaa, finish,
  shadows})`), `studioEnvironment`, `cameraRig` (expo keys plus drift), `clay` (sheen plus rim)
  and `studio` (gradient dome, shadow floor, dotted grid).
- `scenes/mortgage-rate.html` is a 12.5 s vertical clay explainer: 6% vs 7% coin stacks
  (48 vs 53 coins, to scale), the 5 extra coins glowing, then 30 year-stacks counting up to
  $94,700. The same day, Seedance put Bitcoin logos on every coin close-up in that video.
- Software rendering is the cost: about 4-5 s per 1080x1920 frame with MSAA, VSM shadows and
  bloom, so a 12 s clip at 30 fps takes about 30 minutes. It costs no credits.
- Fit for the channel: numbers, money, maps, diagrams and processes, as a 4-6 s cutaway inside a
  Higgsfield video or as a whole data-led Short. People, places and real objects stay on
  Higgsfield.
