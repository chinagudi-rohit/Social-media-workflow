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

`kit.js` holds the shared pieces: renderer with ACES tone mapping and half-res bloom, easing
and timeline helpers (`span`, `window01`), seeded `rng`, twinkling `stars`, additive `glow`
sprites and `toScreen` for labels that track 3D points.
