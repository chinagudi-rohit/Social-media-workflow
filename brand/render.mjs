// Renders the channel art from brand.json: banner (2048x1152), picture (800x800) and
// video watermark (150x150, transparent). Run: node brand/render.mjs
import { createRequire } from 'node:module';
import { readFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const { chromium } = createRequire(import.meta.url)(process.env.PLAYWRIGHT_PATH || 'playwright'); // a global install works
const b = JSON.parse(readFileSync(join(here, 'brand.json'), 'utf8'));
const c = b.colors;
const out = join(here, 'out');
mkdirSync(out, { recursive: true });

const spark = (x, y, r, fill) =>
  `<path transform="translate(${x} ${y}) scale(${r})" fill="${fill}" d="M0-1C.12-.12.12-.12 1 0 .12.12.12.12 0 1-.12.12-.12.12-1 0-.12-.12-.12-.12 0-1Z"/>`;

// The mark: a heavy W with a gold spark, on an ink disc with a thin gold ring.
const mark = (size, { disc = true } = {}) => `
<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 800 800">
  <defs>
    <radialGradient id="g" cx="35%" cy="28%" r="80%"><stop offset="0" stop-color="${c.ink2}"/><stop offset="1" stop-color="${c.ink}"/></radialGradient>
  </defs>
  ${disc ? `<circle cx="400" cy="400" r="400" fill="url(#g)"/><circle cx="400" cy="400" r="372" fill="none" stroke="${c.gold}" stroke-opacity=".55" stroke-width="10"/>` : ''}
  <text x="388" y="548" text-anchor="middle" font-family="Inter Display" font-weight="900" font-size="440" fill="${c.white}" letter-spacing="-18">${b.mark}</text>
  ${spark(612, 238, 74, c.gold)}
  ${spark(676, 330, 26, c.sky)}
</svg>`;

// Simple line icons, one per kind of topic, drawn on a 48-unit grid.
const icons = {
  coin: '<circle cx="24" cy="24" r="18"/><path d="M30 17c-2-2-4.5-2.5-6.5-2.5-3.5 0-6 1.8-6 4.5 0 6 12.5 3 12.5 9.5 0 2.8-2.7 4.5-6.3 4.5-2.6 0-5-.9-6.7-2.7M24 11v26"/>',
  house: '<path d="M6 24 24 8l18 16M11 20v20h26V20"/><path d="M20 40V29h8v11"/>',
  chip: '<rect x="12" y="12" width="24" height="24" rx="3"/><rect x="19" y="19" width="10" height="10" rx="1"/><path d="M18 6v6M24 6v6M30 6v6M18 36v6M24 36v6M30 36v6M6 18h6M6 24h6M6 30h6M36 18h6M36 24h6M36 30h6"/>',
  gear: '<circle cx="24" cy="24" r="6"/><path d="M24 6v6M24 36v6M6 24h6M36 24h6M11.3 11.3l4.2 4.2M32.5 32.5l4.2 4.2M11.3 36.7l4.2-4.2M32.5 15.5l4.2-4.2"/><circle cx="24" cy="24" r="13"/>',
  column: '<path d="M8 14 24 6l16 8H8ZM10 40h28M12 36h24M14 18v18M21 18v18M27 18v18M34 18v18"/>',
  planet: '<circle cx="24" cy="24" r="11"/><ellipse cx="24" cy="24" rx="21" ry="7" transform="rotate(-20 24 24)"/>',
  bulb: '<path d="M17 30c-3-2.5-5-6-5-10a12 12 0 0 1 24 0c0 4-2 7.5-5 10v4H17v-4ZM19 39h10M21 43h6"/>',
  chart: '<path d="M6 40h36M10 34l9-10 7 6 12-14"/><path d="M32 16h6v6"/>',
};
const icon = (name, x, y, s, color, op, sw = 2.2) =>
  `<g transform="translate(${x} ${y}) scale(${s / 48})" fill="none" stroke="${color}" stroke-opacity="${op}" stroke-width="${sw}" stroke-linecap="round" stroke-linejoin="round">${icons[name]}</g>`;

const banner = () => {
  const names = Object.keys(icons);
  let deco = '';
  // Side bands stay visible on desktop (centre 2048x~423); the outer rows only show on TV.
  const placed = [
    [120, 470, 96], [290, 600, 64], [170, 700, 56], [1780, 470, 96], [1930, 600, 64], [1760, 700, 56],
    [420, 180, 90], [900, 120, 70], [1350, 170, 84], [1700, 230, 66], [250, 300, 60],
    [380, 900, 88], [820, 980, 64], [1250, 920, 90], [1660, 960, 72], [180, 1000, 60], [1880, 860, 60],
  ];
  placed.forEach(([x, y, s], i) => {
    const gold = i % 5 === 0;
    deco += icon(names[i % names.length], x - s / 2, y - s / 2, s, gold ? c.gold : c.white, gold ? 0.35 : 0.14);
  });
  const chips = b.topics.map((t) => `<span class="chip">${t}</span>`).join('');
  return `<!doctype html><html><head><meta charset="utf-8"><style>
  html,body{margin:0;width:2048px;height:1152px;overflow:hidden}
  body{background:radial-gradient(120% 90% at 30% 20%, ${c.ink2} 0%, ${c.ink} 60%);font-family:'Inter Display',Inter,sans-serif;color:${c.white};position:relative}
  .dots{position:absolute;inset:0;background-image:radial-gradient(rgba(255,255,255,.07) 1.6px,transparent 1.6px);background-size:36px 36px}
  svg.deco{position:absolute;inset:0}
  .safe{position:absolute;left:${(2048 - 1235) / 2}px;top:${(1152 - 338) / 2}px;width:1235px;height:338px;display:flex;align-items:center;gap:40px;box-sizing:border-box;padding-left:22px}
  .safe svg{flex:none}
  .words{display:grid;gap:12px;min-width:0}
  .eyebrow{font:700 22px/1 Inter,sans-serif;letter-spacing:.14em;text-transform:uppercase;color:${c.gold}}
  h1{margin:0;font-weight:900;font-size:104px;line-height:.95;letter-spacing:-.035em;white-space:nowrap}
  h1 em{font-style:normal;color:${c.gold}}
  p{margin:0;font-weight:600;font-size:36px;letter-spacing:-.01em;color:rgba(255,255,255,.86);white-space:nowrap}
  .chips{display:flex;flex-wrap:nowrap;gap:8px;margin-top:6px}
  .chip{font:600 18px/1 Inter,sans-serif;padding:8px 12px;border-radius:999px;background:rgba(255,255,255,.09);border:1px solid rgba(255,255,255,.16);white-space:nowrap}
  </style></head><body><div class="dots"></div>
  <svg class="deco" width="2048" height="1152" viewBox="0 0 2048 1152">${deco}</svg>
  <div class="safe">${mark(230)}<div class="words">
    <div class="eyebrow">${b.cadence}</div>
    <h1>${b.name.split(' ').map((w, i) => (i === b.name.split(' ').length - 1 ? `<em>${w}</em>` : w)).join(' ')}</h1>
    <p>${b.tagline}</p>
    <div class="chips">${chips}</div></div></div></body></html>`;
};

// X header (1500x500): phones crop the top and bottom, and the profile picture covers
// the bottom-left, so the words sit centre-right in the middle band.
const xHeader = () => {
  const names = Object.keys(icons);
  let deco = '';
  [[90, 120, 70], [260, 90, 54], [160, 260, 60], [1400, 110, 70], [1250, 70, 50], [1420, 390, 60],
   [700, 60, 44], [1080, 450, 50]].forEach(([x, y, sz], i) => {
    const gold = i % 4 === 0;
    deco += icon(names[(i + 2) % names.length], x - sz / 2, y - sz / 2, sz, gold ? c.gold : c.white, gold ? 0.35 : 0.14);
  });
  return `<!doctype html><html><head><meta charset="utf-8"><style>
  html,body{margin:0;width:1500px;height:500px;overflow:hidden}
  body{background:radial-gradient(120% 120% at 25% 20%, ${c.ink2} 0%, ${c.ink} 65%);font-family:'Inter Display',Inter,sans-serif;color:${c.white};position:relative}
  .dots{position:absolute;inset:0;background-image:radial-gradient(rgba(255,255,255,.07) 1.6px,transparent 1.6px);background-size:32px 32px}
  svg.deco{position:absolute;inset:0}
  .safe{position:absolute;left:420px;right:150px;top:110px;bottom:110px;display:grid;align-content:center;gap:12px}
  .eyebrow{font:700 20px/1 Inter,sans-serif;letter-spacing:.14em;text-transform:uppercase;color:${c.gold}}
  h1{margin:0;font-weight:900;font-size:96px;line-height:.95;letter-spacing:-.035em;white-space:nowrap}
  h1 em{font-style:normal;color:${c.gold}}
  p{margin:0;font-weight:600;font-size:32px;letter-spacing:-.01em;color:rgba(255,255,255,.86);white-space:nowrap}
  </style></head><body><div class="dots"></div>
  <svg class="deco" width="1500" height="500" viewBox="0 0 1500 500">${deco}</svg>
  <div class="safe"><div class="eyebrow">${b.cadence}</div>
    <h1>${b.name.split(' ').map((w, i, a) => (i === a.length - 1 ? `<em>${w}</em>` : w)).join(' ')}</h1>
    <p>${b.tagline}</p></div></body></html>`;
};

// Instagram Story highlight covers (1080x1920): Instagram shows the centre as a circle,
// so the icon sits inside a 600 px disc in the middle.
const highlight = (name) => `<!doctype html><html><head><meta charset="utf-8"><style>
  html,body{margin:0;width:1080px;height:1920px;overflow:hidden}
  body{background:radial-gradient(90% 60% at 50% 45%, ${c.ink2} 0%, ${c.ink} 70%);display:grid;place-items:center}
  </style></head><body>
  <svg width="600" height="600" viewBox="0 0 600 600">
    <circle cx="300" cy="300" r="290" fill="none" stroke="${c.gold}" stroke-opacity=".6" stroke-width="10"/>
    ${name === 'start'
      ? `<text x="292" y="398" text-anchor="middle" font-family="Inter Display" font-weight="900" font-size="300" fill="${c.white}" letter-spacing="-12">${b.mark}</text>${spark(440, 180, 52, c.gold)}`
      : icon(name, 120, 120, 360, c.white, 1, 2.6)}
  </svg></body></html>`;

const page = (svg, size, transparent) => `<!doctype html><html><head><style>
  html,body{margin:0;width:${size}px;height:${size}px;overflow:hidden;background:${transparent ? 'transparent' : c.ink}}
  svg{display:block}</style></head><body>${svg}</body></html>`;

const browser = await chromium.launch();
const shot = async (html, w, h, file, transparent = false) => {
  const p = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
  await p.setContent(html, { waitUntil: 'load' });
  await p.evaluate(() => document.fonts.ready);
  const fit = await p.evaluate(() => {
    const safe = document.querySelector('.safe');
    if (!safe) return null;
    const s = safe.getBoundingClientRect();
    const r = [...safe.querySelectorAll('*')].map((e) => e.getBoundingClientRect()).filter((x) => x.width && x.height);
    return { right: Math.max(...r.map((x) => x.right)) - s.right, bottom: Math.max(...r.map((x) => x.bottom)) - s.bottom,
             top: s.top - Math.min(...r.map((x) => x.top)) };
  });
  if (fit && (fit.right > 0 || fit.bottom > 0 || fit.top > 0)) throw new Error(`banner text leaves the safe area: ${JSON.stringify(fit)}`);
  await p.screenshot({ path: join(out, file), omitBackground: transparent });
  await p.close();
};
await shot(banner(), 2048, 1152, 'banner-2048x1152.png');
await shot(page(mark(800), 800, false), 800, 800, 'picture-800x800.png');
await shot(xHeader(), 1500, 500, 'x-header-1500x500.png');
const covers = { start: 'start', money: 'coin', 'ai-tools': 'chip', 'how-its-made': 'gear', history: 'column',
  space: 'planet', mind: 'bulb' };
for (const [label, name] of Object.entries(covers)) {
  await shot(highlight(name), 1080, 1920, `ig-highlight-${label}.png`);
}
await shot(page(mark(150), 150, true), 150, 150, 'watermark-150x150.png', true);
await browser.close();
console.log('ok');
