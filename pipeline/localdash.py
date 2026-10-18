"""The Creator Earnings dashboard for the Hermes instance, served on this Mac.

The claude.ai Dashboard artifact only updates from Claude, so the Hermes instance serves
the same page (dashboard/index.html) locally: `python -m pipeline dashboard serve`.

- The page's runtime (`dash.calc`, `dash.data`, `dash.onData`, `dash.setLink`) is a small
  shim that reads the dataset files `metrics collect` writes to data/dashboard/ and
  re-reads them every minute.
- The Accounts card gets Connect buttons for Higgsfield and Metricool. Each runs
  `hermes -p <profile> mcp login <server>`, which opens the sign-in in your browser.
- It listens on 127.0.0.1 only. The Connect endpoints need the per-start token embedded in
  the page and a same-origin request, so other sites cannot trigger them.
"""

import json
import secrets
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from .config import ROOT, load_yaml
from . import hermes_ops

D3 = "https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"

TOKENS = """
:root {
  --color-bg: #f2f2f7; --color-fg: #1d1d1f; --color-fg-muted: #6e6e73; --color-panel: #ffffff;
  --color-border-line: rgba(60, 60, 67, .12); --cds-dur-slow: .35s; --cds-ease-out: cubic-bezier(.2, .8, .2, 1);
  --cds-chart-grid: rgba(60, 60, 67, .12); --cds-border: rgba(60, 60, 67, .14);
  --cds-surface-popover: rgba(255, 255, 255, .97); --cds-shadow-popover: 0 8px 30px rgba(0, 0, 0, .12);
  --cds-text-secondary: #6e6e73;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --color-bg: #000000; --color-fg: #f5f5f7; --color-fg-muted: #98989d; --color-panel: #1c1c1e;
    --color-border-line: rgba(235, 235, 245, .12); --cds-chart-grid: rgba(235, 235, 245, .12);
    --cds-border: rgba(235, 235, 245, .16); --cds-surface-popover: rgba(44, 44, 46, .97);
    --cds-shadow-popover: 0 8px 30px rgba(0, 0, 0, .5); --cds-text-secondary: #98989d;
  }
}
:root[data-theme="dark"] {
  --color-bg: #000000; --color-fg: #f5f5f7; --color-fg-muted: #98989d; --color-panel: #1c1c1e;
  --color-border-line: rgba(235, 235, 245, .12); --cds-chart-grid: rgba(235, 235, 245, .12);
  --cds-border: rgba(235, 235, 245, .16); --cds-surface-popover: rgba(44, 44, 46, .97);
  --cds-shadow-popover: 0 8px 30px rgba(0, 0, 0, .5); --cds-text-secondary: #98989d;
}
html { color-scheme: light dark; }
body { margin: 0; background: var(--color-bg); color: var(--color-fg); -webkit-font-smoothing: antialiased; }
.fm-wrap { padding: 24px 16px 40px; }
.dash-skeleton { color: transparent; background: rgba(120, 120, 128, .14); border-radius: 6px; }
button.ap-btn { border: 0; cursor: pointer; }
button.ap-btn[disabled] { opacity: .6; cursor: default; }
#connect-metricool { display: none; }
.fm-signin { display: inline-flex; align-items: center; gap: 8px; }
"""

SHIM = """
(function () {
  const state = {}, calcs = {}, listeners = [];
  let loaded = false;
  window.dash = {
    calc(id, spec) { calcs[id] = spec; },
    data(id) { return state[id] || { status: 'loading', data: [] }; },
    onData(fn) { listeners.push(fn); if (loaded) fn(); },
    setLink(name) { history.replaceState(null, '', '#' + name); },
  };
  async function load() {
    await Promise.all(FM.datasets.map(async (id) => {
      try {
        const r = await fetch('data/' + id + '.json', { cache: 'no-store' });
        if (!r.ok) throw new Error(r.status);
        state[id] = { status: 'ok', data: await r.json() };
      } catch (e) { state[id] = { status: 'error', data: [] }; }
    }));
    const done = new Set(FM.datasets);
    for (let progress = true; progress;) {
      progress = false;
      for (const [id, spec] of Object.entries(calcs)) {
        if (done.has(id) || !spec.inputs.every((i) => done.has(i))) continue;
        const ins = spec.inputs.map((i) => state[i]);
        try {
          state[id] = ins.every((x) => x.status === 'ok')
            ? { status: 'ok', data: spec.fn(...ins.map((x) => x.data)) }
            : { status: 'error', data: [] };
        } catch (e) { console.error(id, e); state[id] = { status: 'error', data: [] }; }
        done.add(id); progress = true;
      }
    }
    loaded = true;
    listeners.forEach((fn) => { try { fn(); } catch (e) { console.error(e); } });
  }
  document.addEventListener('DOMContentLoaded', load);
  setInterval(load, 60000);
})();
"""

SIGNIN = """
(function () {
  const card = document.querySelector('#accounts-card .ap-actions');
  if (!card) return;
  const servers = [['higgsfield', 'Connect Higgsfield'], ['metricool', 'Connect Metricool']];
  const chips = {};
  servers.forEach(([server, label], i) => {
    const wrap = document.createElement('span'); wrap.className = 'fm-signin';
    const b = document.createElement('button'); b.type = 'button'; b.className = 'ap-btn';
    const n = document.createElement('span'); n.className = 'n'; n.textContent = String(i + 1);
    b.append(n, label);
    const chip = document.createElement('span'); chip.className = 'ap-chip'; chip.textContent = 'Checking…';
    chips[server] = chip;
    b.addEventListener('click', async () => {
      b.disabled = true;
      const r = await fetch('api/connect/' + server, { method: 'POST', headers: { 'X-FM-Token': FM.token } });
      chip.className = 'ap-chip run';
      chip.textContent = r.ok ? 'Finish sign-in in your browser' : 'Could not start sign-in';
      setTimeout(() => { b.disabled = false; refresh(); }, 20000);
    });
    wrap.append(b, chip);
    card.insertBefore(wrap, document.getElementById('link-accounts'));
  });
  const link = document.getElementById('link-accounts');
  if (link) { const n = link.querySelector('.n'); if (n) n.textContent = '3'; }
  async function refresh() {
    try {
      const s = await (await fetch('api/status', { cache: 'no-store' })).json();
      for (const [server] of servers) {
        const ok = s[server];
        chips[server].className = 'ap-chip ' + (ok === null ? '' : ok ? 'ok' : 'bad');
        chips[server].textContent = ok === null ? 'Checking…' : ok ? 'Connected' : 'Not signed in';
      }
    } catch (e) { /* server stopped */ }
  }
  refresh(); setInterval(refresh, 30000);
})();
"""


def datasets():
    return list(load_yaml("dashboard.yaml")["datasets"])


def render_page(token, page=None):
    cfg = load_yaml("dashboard.yaml")
    body = (page if page is not None else (ROOT / cfg["page"]).read_text(encoding="utf-8"))
    body = body.replace("Connect Metricool to Claude", "Connect Higgsfield and Metricool to Hermes")
    fm = json.dumps({"token": token, "datasets": datasets()})
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Creator Earnings</title>"
        f"<style>{TOKENS}</style>"
        f'<script src="{D3}"></script>'
        f"<script>window.FM = {fm};{SHIM}</script>"
        f'</head><body><main class="fm-wrap">\n{body}\n</main><script>{SIGNIN}</script></body></html>\n'
    )


class Status:
    """Sign-in state per MCP server, checked in the background (each check takes seconds)."""

    def __init__(self, cfg, ttl=120, run=hermes_ops._run):
        self.cfg, self.ttl, self.run = cfg, ttl, run
        self.value = {"higgsfield": None, "metricool": None}
        self.checked = 0.0
        self.lock = threading.Lock()

    def _check(self):
        value = {}
        for role in ("producer", "publisher"):
            server = self.cfg["mcp"][role]
            value[server] = hermes_ops.mcp_ready(self.cfg["profiles"][role], server, self.run)
        self.value = value

    def get(self):
        with self.lock:
            stale = time.time() - self.checked > self.ttl
            if stale:
                self.checked = time.time()
        if stale:
            threading.Thread(target=self._check, daemon=True).start()
        return self.value

    def invalidate(self):
        self.checked = 0.0


def make_handler(token, cfg, status, launch=subprocess.Popen):
    allowed = set(datasets())
    profiles = {cfg["mcp"][role]: cfg["profiles"][role] for role in ("producer", "publisher")}

    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, body=b"", ctype="application/json"):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):
            pass

        def do_GET(self):
            path = urlparse(self.path).path
            if path in ("/", "/index.html"):
                return self._send(200, render_page(token).encode(), "text/html; charset=utf-8")
            if path == "/api/status":
                return self._send(200, json.dumps(status.get()).encode())
            if path.startswith("/data/") and path.endswith(".json"):
                name = path[len("/data/"):-len(".json")]
                file = ROOT / "data" / "dashboard" / f"{name}.json"
                if name in allowed and file.exists():
                    return self._send(200, file.read_bytes())
            return self._send(404, b'{"error":"not found"}')

        def do_POST(self):
            path = urlparse(self.path).path
            origin = self.headers.get("Origin")
            host = self.headers.get("Host", "")
            if self.headers.get("X-FM-Token") != token or (origin and urlparse(origin).netloc != host):
                return self._send(403, b'{"error":"forbidden"}')
            server = path.rsplit("/", 1)[-1]
            if not path.startswith("/api/connect/") or server not in profiles:
                return self._send(404, b'{"error":"not found"}')
            launch(["hermes", "-p", profiles[server], "mcp", "login", server],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            status.invalidate()
            return self._send(202, b'{"started":true}')

    return Handler


def serve(host=None, port=None, open_browser=False):
    cfg = hermes_ops.load_cfg()
    host = host or cfg["dashboard"]["host"]
    port = port or cfg["dashboard"]["port"]
    token = secrets.token_urlsafe(24)
    httpd = ThreadingHTTPServer((host, port), make_handler(token, cfg, Status(cfg)))
    url = f"http://{host}:{port}/"
    print(f"Creator Earnings dashboard: {url}  (Ctrl+C to stop)", flush=True)
    if open_browser:
        subprocess.Popen(["open", url])
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
