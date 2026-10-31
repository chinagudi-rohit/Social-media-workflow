# motion3d: three.js motion graphics to MP4

Code-drawn animation for shots AI video gets wrong: cutaways, diagrams, data, maps, counters.
Costs no credits; renders locally (or in the Higgsfield sandbox) with headless Chromium.

```
cd tools/motion3d && npm install          # three.js only; Playwright comes preinstalled
node render.mjs scenes/gravity-tunnel.html out.mp4                    # 1080x1920, 30 fps
node render.mjs scenes/gravity-tunnel.html - --stills 1,5,9 --stills-dir stills   # check frames
```

A scene is one HTML page. It sets `window.SCENE = {duration, renderAt(t)}` (via `ready()` in
`scenes/kit.js`) and draws frame `t` from `t` alone: no `requestAnimationFrame`, no clocks,
seeded randomness. The renderer steps a virtual clock and screenshots every frame, so the
software GPU can be slow without dropping frames, and HTML/CSS overlays (titles, glass cards,
labels) land in the video exactly as laid out.

Workflow (from the "Claude + three.js" method): write the scene, render 4-6 stills, look at
them, fix layout and exposure, then render the clip. Software rendering runs about 1-2 s per
1080x1920 frame, so a 12 s clip takes 6-12 minutes.

`kit.js` holds the shared pieces:
- `makeRenderer({tone, msaa, finish, shadows, fov, bloom})`. ACES or neutral tone mapping, a
  half-float MSAA target and half-res bloom. `finish` adds grain, vignette and chromatic
  aberration, and `shadows: "vsm"` turns on soft shadows. Call `draw(t)` so the grain is seeded
  by the frame time.
- `studio` (gradient dome, shadow-only floor, dotted grid fading with distance),
  `studioEnvironment` (RoomEnvironment reflections) and `clay` (sheen plus a fresnel rim).
- `cameraRig(keys)`: keyframed position and look-at with an expo ease between keys plus a seeded
  drift.
- Easing and timeline helpers (`span`, `window01`, `easeInOutExpo`), seeded `rng`, twinkling
  `stars`, additive `glow` sprites and `toScreen` for HTML labels that track 3D points.

Scenes: `gravity-tunnel.html` (dark, ACES, glowing cutaway) and `mortgage-rate.html` (light
clay studio, coin stacks to scale, counter). In a light scene, keep the bloom threshold above
the backdrop's brightness (1.15 here); otherwise the whole frame hazes.

A scene prompt that works (from `research/threejs-motion-graphics.md`): give the format and the
t-driven determinism. Name the style with hex colours, then the materials, the studio lights and
the camera keys. Add a numbered story with second ranges and named geometry, and say that text is
pinned by projection. End with the finish chain and "check stills from every scene first".
