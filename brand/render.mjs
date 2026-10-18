// Renders the channel art in brand/src to PNGs in brand/.
// Run: NODE_PATH="$(npm root -g)" node brand/render.mjs
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const { chromium } = createRequire(import.meta.url)('playwright');

const dir = path.dirname(fileURLToPath(import.meta.url));
const jobs = [
  // YouTube banner: 2560x1440; the safe area every device shows is the centered 1546x423.
  { src: 'banner.html', out: 'youtube-banner.png', w: 2560, h: 1440, vars: { u: 1, sw: 1546, sh: 423 }, check: true },
  // Facebook Page cover: 1640x924; phones crop the sides, so content stays in the middle.
  { src: 'banner.html', out: 'facebook-cover.png', w: 1640, h: 924, vars: { u: 0.68, sw: 1100, sh: 420 } },
  { src: 'profile.html', out: 'profile-picture.png', w: 800, h: 800 },
  { src: 'watermark.html', out: 'video-watermark.png', w: 300, h: 300, transparent: true },
];

const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
for (const job of jobs) {
  const page = await browser.newPage({ viewport: { width: job.w, height: job.h } });
  await page.goto('file://' + path.join(dir, 'src', job.src));
  if (job.vars) {
    await page.evaluate((v) => {
      for (const [k, val] of Object.entries(v)) document.documentElement.style.setProperty('--' + k, k === 'u' ? val : val + 'px');
    }, job.vars);
  }
  await page.evaluate(() => document.fonts.ready);
  if (job.check) {
    const box = await page.evaluate(() => {
      const r = (el) => el.getBoundingClientRect();
      const safe = r(document.getElementById('safe'));
      const items = [...document.querySelectorAll('#safe > *, #words > *')].map(r);
      return { safe, left: Math.min(...items.map((b) => b.left)), right: Math.max(...items.map((b) => b.right)),
               top: Math.min(...items.map((b) => b.top)), bottom: Math.max(...items.map((b) => b.bottom)) };
    });
    const inside = box.left >= box.safe.left && box.right <= box.safe.right && box.top >= box.safe.top && box.bottom <= box.safe.bottom;
    console.log(job.out, 'content inside safe area:', inside, JSON.stringify(box));
  }
  await page.screenshot({ path: path.join(dir, job.out), omitBackground: !!job.transparent });
  console.log('wrote', job.out);
  await page.close();
}
await browser.close();
