"""Hermes instance: the daily kanban kickoff, board status and setup checks.

The Hermes copy of the autopilot runs as five profiles (config/hermes.yaml). The kickoff is
plain code, no model: it reads the Higgsfield balance from the signed-in `higgsfield` CLI,
decides today's video count with the same budget as `budget`, and creates one kanban card
per stage on the board. The dispatcher in the Hermes gateway spawns each card's profile,
which loads the stage's skill from hermes/skills/ and works in this repo.

Every `hermes` call goes through `run` so tests can replace it.
"""

import json
import os
import shutil
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from . import budget
from .config import ROOT, load_yaml
from .runs import days_since_last_video, list_manifests

HERMES_ROOT = Path(os.environ.get("FM_HERMES_ROOT") or Path.home() / ".hermes")
SKILLS_DIR = ROOT / "hermes" / "skills"
UPLOADPOST_KEYS = ("UPLOADPOST_API_KEY", "UPLOADPOST_USER")


class HermesError(RuntimeError):
    pass


def load_cfg():
    return load_yaml("hermes.yaml")


def today_et():
    tz = ZoneInfo(load_yaml("timing.yaml")["timezone"])
    return datetime.now(timezone.utc).astimezone(tz).date()


def _run(cmd, timeout=120):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def hermes(args, run=_run, timeout=120):
    """Run the hermes CLI and return stdout; raise HermesError on a non-zero exit."""
    res = run(["hermes", *args], timeout=timeout)
    if res.returncode != 0:
        detail = (res.stderr or res.stdout or "").strip().splitlines()
        raise HermesError(f"hermes {' '.join(args[:3])} failed: {detail[-1] if detail else res.returncode}")
    return res.stdout


# ---- inputs ----------------------------------------------------------------------------

def read_balance(cfg, run=_run):
    cmd = cfg["higgsfield"]["balance_command"]
    if run is _run and not shutil.which(cmd[0]):
        raise HermesError(f"{cmd[0]} CLI not found on PATH")
    res = run(cmd, timeout=60)
    if res.returncode != 0:
        raise HermesError(f"Higgsfield balance check failed: {(res.stderr or res.stdout).strip()[:200]}")
    try:
        return float(json.loads(res.stdout)["credits"])
    except (ValueError, KeyError, TypeError) as e:
        raise HermesError(f"unexpected Higgsfield balance output: {res.stdout[:200]}") from e


def mcp_ready(profile, server, run=_run):
    """True when `hermes -p <profile> mcp test <server>` connects (signed in, tools listed)."""
    try:
        return run(["hermes", "-p", profile, "mcp", "test", server], timeout=90).returncode == 0
    except subprocess.TimeoutExpired:
        return False


def readiness(cfg, run=_run, env=os.environ):
    producer = mcp_ready(cfg["profiles"]["producer"], cfg["mcp"]["producer"], run)
    metricool = mcp_ready(cfg["profiles"]["publisher"], cfg["mcp"]["publisher"], run)
    uploadpost = all(env.get(k) for k in UPLOADPOST_KEYS)
    return {"producer": producer, "metricool": metricool, "uploadpost": uploadpost,
            "publisher": metricool or uploadpost}


# ---- the day's cards -------------------------------------------------------------------

def plan_cards(cfg, day, plan, notes=()):
    """Today's cards in dependency order. Each is a dict the kickoff turns into one
    `hermes kanban create`; `parents` name earlier cards by key."""
    p, s = cfg["profiles"], cfg["stages"]
    videos = plan["videos_today"]
    limit = round(videos * plan["est_cost_per_video"] * 1.2, 1)
    context = (f"Date (US Eastern): {day}. Budget: {videos} video(s) today, {plan['tier']} tier, "
               f"~{plan['est_cost_per_video']} credits each; balance {plan['balance']:g}, "
               f"{plan['days_left_in_cycle']} days left in the credit cycle.")
    why = "; ".join(notes)

    def card(key, title, role, parents, body):
        stage = s[key]
        return {"key": key, "title": title, "assignee": p[role], "skill": stage["skill"],
                "parents": parents, "max_runtime": stage["max_runtime"],
                "max_retries": stage["max_retries"],
                "body": f"{body}\n\n{context}\nWork in the repo root and follow the "
                        f"`{stage['skill']}` skill exactly; `./fm` runs the pipeline CLI."}

    cards = [card(
        "research", f"Research refresh {day}", "research", [],
        f"Refresh today's trend snapshot (data/trends/{day}.json) and monetization-policy notes. "
        f"Done when `./fm trends validate --date {day}` prints ok. Complete with metadata "
        '{"snapshot", "top_niches", "topic_ideas", "program_changes"}.')]
    last = "research"
    if videos > 0:
        cards.append(card(
            "scripts", f"Choose {videos} script(s) {day}", "writer", ["research"],
            f"Choose {videos} script(s) for today from the library (or write one for a trending topic) "
            "and create their run folders. Done when every run passes `./fm validate RUN`. "
            'Complete with metadata {"runs": ["runs/<run_id>", ...], "new_scripts": [...]}.'))
        cards.append(card(
            "produce", f"Produce {videos} video(s) {day}", "producer", ["scripts"],
            f"Produce the video for each run in the scripts card's handoff. Credit limit for this "
            f"card: {limit:g} credits (the budget plus 20% for retries); never exceed it. If "
            "RUN/jobs.json exists, resume from it: never resubmit a job that already has an id. "
            'Complete with metadata {"videos": [{"run", "url", "duration", "credits"}], '
            '"credits_spent", "skipped"}.'))
        last = "produce"
    cards.append(card(
        "publish", f"Publish, earnings and dashboard {day}", "publisher", [last],
        ("Schedule each new video on every platform at its own best time, then collect "
         "earnings, refresh the dashboard data and commit. "
         if videos > 0 else
         f"No videos today ({why or 'the budget allows none today'}). Do the post-time data, "
         "post results, earnings, dashboard and commit steps only. ")
        + 'Complete with metadata {"scheduled", "failed", "earnings_30d", "balance", "commit"}.'))
    return cards


def create_cards(cfg, day, cards, run=_run):
    """Create the cards in order and return {key: task_id}. Idempotency keys make a re-run
    of the same day return the existing cards instead of duplicating them."""
    ids = {}
    workspace = f"dir:{ROOT}"
    for c in cards:
        args = ["kanban", "--board", cfg["board"], "create", c["title"],
                "--assignee", c["assignee"], "--workspace", workspace, "--skill", c["skill"],
                "--idempotency-key", f"fm-{day}-{c['key']}", "--max-runtime", c["max_runtime"],
                "--max-retries", str(c["max_retries"]), "--created-by", "fm-kickoff",
                "--body", c["body"], "--json"]
        for parent in c["parents"]:
            args += ["--parent", ids[parent]]
        ids[c["key"]] = json.loads(hermes(args, run))["id"]
    return ids


def subscribe(cfg, ids, final_key, run=_run):
    """Send each card's terminal events to #faceless; the last card also wakes fm-lead so it
    writes the daily report in the channel."""
    if not cfg["notify"].get("chat_id"):
        return False
    for key, task_id in ids.items():
        if key == final_key or cfg["notify"].get("progress", True):
            _subscribe_one(cfg, task_id, "notify+wake" if key == final_key else "notify", run)
    return True


def ensure_board(cfg, run=_run):
    if cfg["board"] not in hermes(["kanban", "boards", "list"], run):
        hermes(["kanban", "boards", "create", cfg["board"], "--name", "Faceless autopilot",
                "--description", "Daily faceless short-video pipeline (Faceless Monitisation repo)"], run)


def kickoff(day=None, balance=None, dry_run=False, cfg=None, run=_run, env=os.environ, manifests=None):
    """Plan today's run and create its cards. Returns a summary dict."""
    cfg = cfg or load_cfg()
    day = day or today_et()
    notes = []
    if balance is None:
        try:
            balance = read_balance(cfg, run)
        except HermesError as e:
            notes.append(str(e))
            balance = 0.0
    prod = load_yaml("production.yaml")
    manifests = list_manifests() if manifests is None else manifests
    plan = budget.plan_today(prod, balance, day, days_since_last_video(manifests, day))
    ready = readiness(cfg, run, env)
    if plan["videos_today"] and not ready["producer"]:
        notes.append(f"Higgsfield is not signed in for {cfg['profiles']['producer']} "
                     f"(hermes -p {cfg['profiles']['producer']} mcp login {cfg['mcp']['producer']})")
    if plan["videos_today"] and not ready["publisher"]:
        notes.append(f"no publisher is signed in: hermes -p {cfg['profiles']['publisher']} "
                     f"mcp login {cfg['mcp']['publisher']}, or add Upload-Post keys")
    if notes:
        plan = {**plan, "videos_today": 0}
    cards = plan_cards(cfg, day, plan, notes)
    summary = {"date": str(day), "videos_today": plan["videos_today"], "balance": balance,
               "est_cost_per_video": plan["est_cost_per_video"], "ready": ready, "notes": notes,
               "cards": [{k: c[k] for k in ("key", "title", "assignee", "skill", "parents")} for c in cards]}
    if dry_run:
        return summary
    ensure_board(cfg, run)
    ids = create_cards(cfg, day, cards, run)
    summary["task_ids"] = ids
    summary["notifications"] = subscribe(cfg, ids, cards[-1]["key"], run)
    return summary


def _subscribe_one(cfg, task_id, mode, run=_run):
    n = cfg["notify"]
    if not n.get("chat_id"):
        return False
    hermes(["kanban", "--board", cfg["board"], "notify-subscribe", task_id,
            "--platform", n["platform"], "--chat-id", str(n["chat_id"]), "--chat-type", "channel",
            "--guild-id", str(n["guild_id"]), "--notifier-profile", cfg["profiles"]["lead"],
            "--delivery-mode", mode], run)
    return True


def request_video(topic=None, niche=None, script_id=None, day=None, cfg=None, run=_run):
    """On-demand video, step 1: a writer card that prepares one run and quotes its cost.
    Its completion wakes fm-lead, which asks the owner before anything is spent."""
    cfg = cfg or load_cfg()
    day = day or today_et()
    if not (topic or niche or script_id):
        raise HermesError("give a topic, a niche or a script id")
    if script_id:
        what = f"library script {script_id}"
    elif topic:
        what = f"a new script about: {topic}" + (f" (niche {niche})" if niche else "")
    else:
        what = f"the best unused library script in niche {niche}"
    stage = cfg["stages"]["scripts"]
    body = (f"On-demand video requested in #faceless on {day} (US Eastern). Prepare exactly one "
            f"run from {what}. Then `./fm gen-plan RUN` and complete with metadata "
            '{"runs": ["runs/<run_id>"], "estimated_credits", "hook", "topic", "niche"}. '
            "Do not produce video or spend credits.\nWork in the repo root and follow the "
            "`fm-scripts` skill (its on-demand section).")
    ensure_board(cfg, run)
    task = json.loads(hermes(
        ["kanban", "--board", cfg["board"], "create", f"On-demand script: {topic or script_id or niche} {day}",
         "--assignee", cfg["profiles"]["writer"], "--workspace", f"dir:{ROOT}", "--skill", stage["skill"],
         "--max-runtime", stage["max_runtime"], "--max-retries", str(stage["max_retries"]),
         "--created-by", "fm-lead", "--body", body, "--json"], run))["id"]
    subscribed = _subscribe_one(cfg, task, "notify+wake", run)
    return {"task_id": task, "notifications": subscribed}


def approve_video(script_task, credits, post=False, day=None, cfg=None, run=_run):
    """On-demand video, step 2 (after the owner said yes): produce, and publish if asked."""
    cfg = cfg or load_cfg()
    day = day or today_et()
    p, s = cfg["profiles"], cfg["stages"]
    limit = round(float(credits) * 1.2, 1)
    ids = {}
    cards = [("produce", p["producer"], [script_task],
              f"Produce the on-demand video for the run in the parent card's handoff. The owner "
              f"approved about {credits:g} credits; credit limit for this card: {limit:g}. "
              'Complete with metadata {"videos": [{"run", "url", "duration", "credits"}], '
              '"credits_spent", "skipped"}.')]
    if post:
        cards.append(("publish", p["publisher"], None,
                      "Schedule the on-demand video from the parent card's handoff on every platform "
                      "at its next best slot, then refresh earnings and commit."))
    for key, assignee, parents, body in cards:
        stage = s[key]
        args = ["kanban", "--board", cfg["board"], "create", f"On-demand {key} {script_task} {day}",
                "--assignee", assignee, "--workspace", f"dir:{ROOT}", "--skill", stage["skill"],
                "--idempotency-key", f"fm-od-{script_task}-{key}", "--max-runtime", stage["max_runtime"],
                "--max-retries", str(stage["max_retries"]), "--created-by", "fm-lead",
                "--body", f"{body}\nWork in the repo root and follow the `{stage['skill']}` skill.", "--json"]
        for parent in parents or [ids["produce"]]:
            args += ["--parent", parent]
        ids[key] = json.loads(hermes(args, run))["id"]
    last = list(ids)[-1]
    for key, task in ids.items():
        _subscribe_one(cfg, task, "notify+wake" if key == last else "notify", run)
    return ids


def kickoff_message(summary, board):
    """Short text for #faceless (the no-agent cron delivers stdout verbatim)."""
    day = datetime.fromisoformat(summary["date"]).strftime("%a %b %-d")
    n = summary["videos_today"]
    head = (f"Faceless kickoff {day} ET: {n} video{'s' if n != 1 else ''} today, "
            f"~{summary['est_cost_per_video']:g} credits each, {summary['balance']:g} credits left.")
    chain = " -> ".join(f"{c['key']} {summary.get('task_ids', {}).get(c['key'], '')}".strip()
                        for c in summary["cards"])
    lines = [head, f"Board {board}: {chain}"]
    lines += [f"Needs you: {note}" for note in summary["notes"]]
    if not summary.get("notifications", True):
        lines.append("Discord channel not set: run hermes/setup/route-discord.sh <channel id>")
    return "\n".join(lines)


# ---- status and doctor -----------------------------------------------------------------

def day_cards(cfg, day, run=_run):
    tasks = json.loads(hermes(["kanban", "--board", cfg["board"], "list", "--json"], run))
    return [t for t in tasks if (t.get("title") or "").endswith(str(day))]


def profile_home(name, root=None):
    root = Path(root) if root else HERMES_ROOT
    return root if name == "default" else root / "profiles" / name


def doctor(cfg=None, run=_run, root=None):
    """Setup checklist: [(ok, label, fix)]."""
    cfg = cfg or load_cfg()
    root = Path(root) if root else HERMES_ROOT
    checks = []

    def add(ok, label, fix=""):
        checks.append((bool(ok), label, fix))

    add(shutil.which("hermes"), "hermes CLI on PATH", "install Hermes Agent")
    try:
        bal = read_balance(cfg, run)
        add(True, f"Higgsfield CLI signed in ({bal:g} credits)")
    except HermesError as e:
        add(False, f"Higgsfield CLI: {e}", "higgsfield auth login")
    for role, name in cfg["profiles"].items():
        home = profile_home(name, root)
        conf = home / "config.yaml"
        add(conf.exists(), f"profile {name} installed",
            f"hermes profile install hermes/profiles/{name} --alias -y")
        if conf.exists():
            data = yaml.safe_load(conf.read_text(encoding="utf-8")) or {}
            dirs = [str(Path(os.path.expanduser(d)).resolve()) for d in
                    (data.get("skills") or {}).get("external_dirs") or []]
            add(str(SKILLS_DIR.resolve()) in dirs, f"profile {name} reads hermes/skills",
                "hermes/setup/install.sh (rewrites skills.external_dirs)")
    for role in ("producer", "publisher"):
        name, server = cfg["profiles"][role], cfg["mcp"][role]
        add(mcp_ready(name, server, run), f"{server} MCP signed in for {name}",
            f"hermes -p {name} mcp login {server}")
    try:
        boards = hermes(["kanban", "boards", "list"], run)
        add(cfg["board"] in boards, f"kanban board {cfg['board']}", "hermes/setup/install.sh")
    except HermesError as e:
        add(False, f"kanban: {e}", "hermes kanban init")
    chat = cfg["notify"].get("chat_id")
    routes = []
    default_conf = root / "config.yaml"
    if default_conf.exists():
        gw = (yaml.safe_load(default_conf.read_text(encoding="utf-8")) or {}).get("gateway") or {}
        routes = gw.get("profile_routes") or []
    routed = any(str(r.get("chat_id")) == str(chat) and r.get("profile") == cfg["profiles"]["lead"]
                 for r in routes) if chat else False
    add(chat and routed, "#faceless Discord channel routed to " + cfg["profiles"]["lead"],
        "hermes/setup/route-discord.sh <channel id>")
    try:
        jobs = hermes(["-p", cfg["profiles"]["lead"], "cron", "list"], run)
        add("fm-kickoff" in jobs, "fm-kickoff cron job exists", "hermes/setup/install.sh")
    except HermesError as e:
        add(False, f"cron: {e}", "hermes/setup/install.sh")
    return checks
