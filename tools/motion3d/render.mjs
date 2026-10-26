// Render a three.js scene to MP4, frame by frame, in headless Chromium.
//
//   node render.mjs scenes/<name>.html out.mp4 [--fps 30] [--width 1080] [--height 1920]
//                   [--from 0] [--to <seconds>] [--stills 0.5,2,6 --stills-dir dir]
//
// A scene is a web page that sets `window.SCENE = {duration, renderAt(t)}` and then
// `window.SCENE_READY = true`. renderAt(t) draws the frame at t seconds (canvas and HTML
// overlays alike) from t alone: no requestAnimationFrame, no clocks, seeded randomness.
// The renderer steps a virtual clock, screenshots each frame and pipes the JPEGs to ffmpeg,
// so a slow software GPU never drops a frame and the same scene always gives the same video.
import { spawn } from "node:child_process";
import { createServer } from "node:http";
import { mkdirSync, readFileSync, statSync } from "node:fs";
import { extname, join, resolve } from "node:path";
import { createRequire } from "node:module";

// Playwright is installed globally (NODE_PATH), which ES module imports ignore.
const { chromium } = createRequire(import.meta.url)("playwright");

const ROOT = resolve(new URL(".", import.meta.url).pathname);
const args = process.argv.slice(2);
const opt = (name, dflt) => {
  const i = args.indexOf(`--${name}`);
  return i < 0 ? dflt : args[i + 1];
};
const [scenePath, outPath] = args.filter((a, i) => !a.startsWith("--") && !(i > 0 && args[i - 1].startsWith("--")));
if (!scenePath || !outPath) {
  console.error("usage: node render.mjs scenes/<name>.html out.mp4 [--fps 30] [--width 1080] [--height 1920]");
  process.exit(2);
}
const fps = Number(opt("fps", 30));
const width = Number(opt("width", 1080));
const height = Number(opt("height", 1920));

// Static server for the scene and node_modules (ES modules do not load over file://).
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".json": "application/json",
  ".png": "image/png", ".jpg": "image/jpeg", ".woff2": "font/woff2", ".ttf": "font/ttf", ".css": "text/css" };
const server = createServer((req, res) => {
  const path = join(ROOT, decodeURIComponent(new URL(req.url, "http://x").pathname));
  try {
    if (!path.startsWith(ROOT) || !statSync(path).isFile()) throw new Error("not found");
    res.writeHead(200, { "content-type": TYPES[extname(path)] || "application/octet-stream" });
    res.end(readFileSync(path));
  } catch {
    res.writeHead(404).end();
  }
});
await new Promise((ok) => server.listen(0, "127.0.0.1", ok));
const base = `http://127.0.0.1:${server.address().port}`;

const browser = await chromium.launch({
  args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist",
    "--font-render-hinting=none", "--disable-lcd-text"],
});
const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
page.on("console", (m) => m.type() === "error" && console.error("[scene]", m.text()));
page.on("pageerror", (e) => console.error("[scene]", e.message));
await page.goto(`${base}/${scenePath}?w=${width}&h=${height}`);
await page.waitForFunction(() => window.SCENE_READY === true, null, { timeout: 120000 });
const duration = await page.evaluate(() => window.SCENE.duration);
const from = Number(opt("from", 0));
const to = Math.min(Number(opt("to", duration)), duration);

// Stills only (the verification loop): frames at the given times, no video.
const stills = opt("stills", null);
if (stills) {
  const dir = opt("stills-dir", "stills");
  mkdirSync(dir, { recursive: true });
  for (const t of stills.split(",").map(Number)) {
    await page.evaluate((t) => window.SCENE.renderAt(t), t);
    await page.screenshot({ path: join(dir, `t${t.toFixed(2)}.jpg`), type: "jpeg", quality: 85 });
  }
  await browser.close();
  server.close();
  process.exit(0);
}

const ffmpeg = spawn("ffmpeg", ["-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(fps), "-c:v", "mjpeg",
  "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-movflags", "+faststart", outPath],
  { stdio: ["pipe", "inherit", "inherit"] });
const frames = Math.round((to - from) * fps);
const started = Date.now();
for (let i = 0; i < frames; i++) {
  await page.evaluate((t) => window.SCENE.renderAt(t), from + i / fps);
  const jpg = await page.screenshot({ type: "jpeg", quality: 95 });
  if (!ffmpeg.stdin.write(jpg)) await new Promise((ok) => ffmpeg.stdin.once("drain", ok));
  if (i % fps === 0) process.stderr.write(`\rframe ${i}/${frames}  ${((Date.now() - started) / 1000).toFixed(0)}s`);
}
ffmpeg.stdin.end();
await new Promise((ok, fail) => ffmpeg.on("close", (c) => (c ? fail(new Error(`ffmpeg ${c}`)) : ok())));
process.stderr.write(`\rdone: ${frames} frames in ${((Date.now() - started) / 1000).toFixed(0)}s -> ${outPath}\n`);
await browser.close();
server.close();
