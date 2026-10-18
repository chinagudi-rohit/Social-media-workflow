"""Command line for the short-video pipeline. Run `python -m pipeline --help`."""

import argparse
import csv
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import requests

from . import budget, instagram, library, metrics, production, trends, uploadpost, youtube
from .config import ROOT, load_niches, load_platforms, load_yaml, niche_by_id
from .niches import pick_niche, recent_topics
from .runs import (
    create_run,
    list_manifests,
    load_manifest,
    load_script,
    record_post,
    save_manifest,
)
from .script import build_captions, validate, validate_library

ENV_KEYS = {
    "uploadpost": ("UPLOADPOST_API_KEY", "UPLOADPOST_USER"),
    "youtube": ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"),
    "instagram": ("IG_USER_ID", "IG_ACCESS_TOKEN"),
    "facebook_earnings": ("FB_PAGE_ID", "FB_PAGE_TOKEN"),
}


def load_dotenv(path=ROOT / ".env"):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def out(data):
    print(json.dumps(data, indent=2, ensure_ascii=False))


def fail(message):
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def missing_env(group):
    return [k for k in ENV_KEYS[group] if not os.environ.get(k)]


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path):
    if not Path(path).exists():
        fail(f"{path} not found")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def checked_script(run_dir):
    if not (Path(run_dir) / "script.json").exists():
        fail(f"{run_dir}/script.json not found")
    script = load_script(run_dir)
    errors = validate(script, load_niches(), load_platforms())
    if errors:
        fail("script.json is invalid:\n  - " + "\n  - ".join(errors))
    return script


def captions_for(run_dir):
    script = checked_script(run_dir)
    return build_captions(script, niche_by_id(script["niche_id"]), load_platforms())


def days_since_last_video(manifests, today):
    made = [m for m in manifests if m.get("video", {}).get("url")]
    if not made:
        return None
    last = max(datetime.fromisoformat(m["created_at"].replace("Z", "+00:00")).date() for m in made)
    return (today - last).days


# ---- setup and planning -----------------------------------------------------------

def cmd_check(args):
    out({g: {"ready": not missing_env(g), "missing": missing_env(g)} for g in ENV_KEYS})


def cmd_budget(args):
    prod = load_yaml("production.yaml")
    today = date.fromisoformat(args.date) if args.date else date.today()
    out(budget.plan_today(prod, args.balance, today, days_since_last_video(list_manifests(), today)))


def cmd_trends(args):
    niches = load_niches()
    day = args.date or str(date.today())
    path = trends.snapshot_path(day)
    if args.action == "template":
        if path.exists():
            fail(f"{path.relative_to(ROOT)} already exists")
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, trends.template(niches, day))
        print(path.relative_to(ROOT))
    elif args.action == "validate":
        errors = trends.validate(read_json(path), niches)
        if errors:
            fail("trend snapshot is invalid:\n  - " + "\n  - ".join(errors))
        print("ok")
    else:
        snap = trends.load_latest(on_or_before=day)
        weights = load_yaml("production.yaml").get("scoring")
        out(trends.score_niches(niches, snap, list_manifests(), datetime.now(timezone.utc), weights))


def cmd_library(args):
    niches, platforms, manifests = load_niches(), load_platforms(), list_manifests()
    scripts = library.load_scripts()
    if args.action == "validate":
        bad = {s["id"]: e for s in scripts
               if (e := validate_library(s, niches, platforms, library.STRUCTURES))}
        if bad:
            fail(json.dumps(bad, indent=2))
        print(f"ok ({len(scripts)} scripts)")
    elif args.action == "stock":
        out(library.stock(scripts, manifests))
    else:
        snap = trends.load_latest()
        scored = trends.score_niches(niches, snap, manifests, datetime.now(timezone.utc))
        picks = library.pick(scripts, scored, manifests, args.count)
        score_of = {s["id"]: s["score"] for s in scored}
        out([{"script_id": s["id"], "niche_id": s["niche_id"], "structure": s["structure"],
              "niche_score": score_of[s["niche_id"]], "topic": s["topic"]} for s in picks])


def cmd_start_run(args):
    scripts = {s["id"]: s for s in library.load_scripts()}
    if args.script_id not in scripts:
        fail(f"unknown script id {args.script_id}")
    manifests = list_manifests()
    if args.script_id in library.used_ids(manifests):
        fail(f"{args.script_id} was already used")
    script = scripts[args.script_id]
    voice = production.pick_voice(load_yaml("production.yaml")["voices"], len(manifests))
    run_dir = create_run(script["niche_id"], script["topic"], script_id=script["id"],
                         structure=script["structure"], voice=voice["name"])
    body = {k: v for k, v in script.items() if k not in ("id", "structure")}
    write_json(run_dir / "script.json", body)
    print(run_dir.relative_to(ROOT))


def cmd_pick_niche(args):
    niches, manifests = load_niches(), list_manifests()
    niche = niche_by_id(args.niche, niches) if args.niche else pick_niche(
        niches, manifests, datetime.now(timezone.utc)
    )
    out({**niche, "recent_topics": recent_topics(manifests, niche["id"])})


def cmd_new_run(args):
    niche_by_id(args.niche)
    print(create_run(args.niche, args.topic).relative_to(ROOT))


def cmd_validate(args):
    checked_script(args.run)
    print("ok")


def cmd_captions(args):
    captions = captions_for(args.run)
    write_json(Path(args.run) / "captions.json", captions)
    out(captions)


# ---- production -------------------------------------------------------------------

def cmd_gen_plan(args):
    script = checked_script(args.run)
    manifest = load_manifest(args.run)
    prod = load_yaml("production.yaml")
    voices = {v["name"]: v for v in prod["voices"]}
    voice = voices.get(manifest.get("voice")) or prod["voices"][0]
    plan = production.generation_requests(script, niche_by_id(script["niche_id"]), prod, voice)
    write_json(Path(args.run) / "generation.json", plan)
    out({"estimated_credits": plan["estimated_credits"], "keyframes": len(plan["keyframes"]),
         "motion": len(plan["motion"]), "voice": plan["voice"]["voice_name"]})


def cmd_render_plan(args):
    run = Path(args.run)
    script = checked_script(run)
    assets = read_json(run / "assets.json")
    errors = production.validate_assets(assets, script, read_json(run / "generation.json"))
    if errors:
        fail("assets.json is incomplete:\n  - " + "\n  - ".join(errors))
    render_cfg = load_yaml("production.yaml")["render"]
    write_json(run / "render.json", production.render_plan(script, assets, render_cfg))
    manifest = load_manifest(run)
    manifest["video"]["job_ids"] = assets.get("job_ids", [])
    manifest["video"]["credits_spent"] = assets.get("credits_spent")
    save_manifest(run, manifest)
    print((run / "render.json").relative_to(ROOT) if run.is_absolute() else run / "render.json")


def cmd_set_video(args):
    manifest = load_manifest(args.run)
    manifest["video"] = {
        **manifest.get("video", {}),
        "url": args.url,
        "duration_seconds": args.duration,
    }
    if args.job_id:
        manifest["video"]["job_ids"] = args.job_id
    if args.credits is not None:
        manifest["video"]["credits_spent"] = args.credits
    manifest["status"] = "video_ready"
    save_manifest(args.run, manifest)
    print("ok")


# ---- publishing -------------------------------------------------------------------

def cmd_record_post(args):
    fields = {k: v for k, v in {"status": args.status, "id": args.id, "url": args.url, "note": args.note}.items() if v}
    out(record_post(args.run, args.platform, **fields)["posts"][args.platform])


def download(url, dest):
    if dest.exists() and dest.stat().st_size:
        return dest
    with requests.get(url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(1 << 20):
                f.write(chunk)
    return dest


def publish_all(args, run_dir, captions, video_url, platforms_cfg):
    manifest = load_manifest(run_dir)
    targets = args.platforms.split(",") if args.platforms else list(uploadpost.PLATFORMS)
    request_id = manifest["run_id"]
    fields = uploadpost.build_form(
        captions, video_url, os.environ.get("UPLOADPOST_USER", "<UPLOADPOST_USER>"), targets,
        platforms_cfg, request_id, args.schedule, os.environ.get("UPLOADPOST_FACEBOOK_PAGE_ID"),
    )
    if args.dry_run:
        out({"platforms": targets, "fields": fields})
        return
    if missing_env("uploadpost"):
        fail(f"missing credentials: {', '.join(missing_env('uploadpost'))} (see .env.example)")
    body = uploadpost.publish(requests.Session(), os.environ["UPLOADPOST_API_KEY"], fields, request_id)
    manifest["upload_request_id"] = body.get("request_id", request_id)
    manifest["upload_job_id"] = body.get("job_id")
    save_manifest(run_dir, manifest)
    for p in targets:
        record_post(run_dir, p, status="scheduled" if args.schedule else "processing")
    out(body)


def cmd_publish(args):
    run_dir, platform = Path(args.run), args.platform
    all_captions = captions_for(run_dir)
    video_url = load_manifest(run_dir)["video"]["url"]
    if not video_url:
        fail("no video yet; run `set-video` with the Higgsfield URL first")
    platforms = load_platforms()
    if platform == "all":
        publish_all(args, run_dir, all_captions, video_url, platforms)
        return

    captions = all_captions[platform]
    if args.dry_run:
        out({"platform": platform, "video_url": video_url, "captions": captions})
        return
    if missing_env(platform):
        fail(f"missing credentials for {platform}: {', '.join(missing_env(platform))} (see .env.example)")

    session = requests.Session()
    try:
        if platform == "youtube":
            video_path = download(video_url, run_dir / "video.mp4")
            token = youtube.access_token(
                session, os.environ["YT_CLIENT_ID"], os.environ["YT_CLIENT_SECRET"], os.environ["YT_REFRESH_TOKEN"]
            )
            result = youtube.upload(session, token, video_path, youtube.build_metadata(captions, platforms["youtube"]))
        else:
            host = os.environ.get("IG_GRAPH_HOST", "graph.facebook.com")
            version = os.environ.get("IG_GRAPH_API_VERSION", "v23.0")
            result = instagram.publish_reel(
                session,
                base_url=f"https://{host}/{version}",
                ig_user_id=os.environ["IG_USER_ID"],
                token=os.environ["IG_ACCESS_TOKEN"],
                video_url=video_url,
                caption=captions["caption"],
                share_to_feed=platforms["instagram"]["share_to_feed"],
            )
    except (youtube.YouTubeError, instagram.InstagramError, requests.RequestException) as e:
        record_post(run_dir, platform, status="failed", note=str(e))
        fail(str(e))
    out(record_post(run_dir, platform, status="published", **result)["posts"][platform])


def cmd_publish_status(args):
    if missing_env("uploadpost"):
        fail(f"missing credentials: {', '.join(missing_env('uploadpost'))}")
    manifest = load_manifest(args.run)
    rid, jid = manifest.get("upload_request_id"), manifest.get("upload_job_id")
    if not (rid or jid):
        fail("this run has no Upload-Post request; publish it first")
    body = uploadpost.status(requests.Session(), os.environ["UPLOADPOST_API_KEY"],
                             request_id=None if jid else rid, job_id=jid)
    for platform, r in uploadpost.platform_results(body).items():
        fields = {k: v for k, v in r.items() if v not in (None, False)}
        if r["draft"]:
            fields["status"] = "draft"
        record_post(args.run, platform, **fields)
    out({"status": body.get("status"), "posts": load_manifest(args.run)["posts"]})


# ---- monetization metrics ---------------------------------------------------------

def cmd_earnings_add(args):
    path = metrics.MANUAL_EARNINGS
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["date", "platform", "amount_usd", "source", "note"])
        w.writerow([args.date or str(date.today()), args.platform, f"{args.amount:.2f}", args.source, args.note or ""])
    print("ok")


def cmd_metrics(args):
    today = date.fromisoformat(args.date) if args.date else date.today()
    start, end = metrics.default_window(today, args.days)
    session = requests.Session()
    errors, stats, yt_rows, fb_rows = {}, {}, [], []

    if not missing_env("uploadpost"):
        try:
            body = uploadpost.analytics(session, os.environ["UPLOADPOST_API_KEY"], os.environ["UPLOADPOST_USER"],
                                        list(uploadpost.PLATFORMS), os.environ.get("UPLOADPOST_FACEBOOK_PAGE_ID"))
            stats = metrics.normalize_uploadpost(body)
        except (uploadpost.UploadPostError, requests.RequestException) as e:
            errors["uploadpost"] = str(e)
    if not missing_env("youtube"):
        try:
            token = youtube.access_token(session, os.environ["YT_CLIENT_ID"], os.environ["YT_CLIENT_SECRET"],
                                         os.environ["YT_REFRESH_TOKEN"])
            yt_rows = metrics.youtube_revenue(session, token, start, end)
        except (youtube.YouTubeError, RuntimeError, requests.RequestException) as e:
            errors["youtube_revenue"] = str(e)
    if not missing_env("facebook_earnings"):
        try:
            base = f"https://graph.facebook.com/{os.environ.get('IG_GRAPH_API_VERSION', 'v23.0')}"
            fb_rows = metrics.facebook_earnings(session, base, os.environ["FB_PAGE_ID"],
                                                os.environ["FB_PAGE_TOKEN"], start, end)
        except (RuntimeError, requests.RequestException) as e:
            errors["facebook_earnings"] = str(e)

    manual = metrics.manual_earnings()
    totals = metrics.earnings_by_platform(yt_rows, fb_rows, manual, start, end)
    daily = {}
    for r in yt_rows:
        daily.setdefault(r["day"], {})["youtube"] = float(r.get("estimatedRevenue") or 0)
    for r in fb_rows:
        daily.setdefault(r["day"], {})["facebook"] = r["earnings"]
    for r in manual:
        if str(start) <= r["date"] <= str(end):
            d = daily.setdefault(r["date"], {})
            d[r["platform"]] = round(d.get(r["platform"], 0) + r["amount_usd"], 2)

    runs = [
        {"run_id": m["run_id"], "niche": m["niche_id"], "topic": m["topic"], "date": m["created_at"][:10],
         "credits": m.get("video", {}).get("credits_spent"),
         "published": any(p.get("status") == "published" for p in m.get("posts", {}).values()),
         "posts": {p: {"status": v.get("status"), "url": v.get("url")} for p, v in m.get("posts", {}).items()}}
        for m in list_manifests()
    ]
    credits = {"spent_30d": round(sum(r["credits"] or 0 for r in runs if r["date"] >= str(start)), 2),
               "balance": args.balance}
    snap = metrics.snapshot(today, stats, totals, [{"date": d, **v} for d, v in sorted(daily.items())], runs, credits)
    snap["errors"] = errors
    metrics.METRICS_DIR.mkdir(parents=True, exist_ok=True)
    write_json(metrics.METRICS_DIR / f"{today}.json", snap)
    write_json(metrics.METRICS_DIR / f"{today}.rows.json", metrics.dashboard_rows(snap))
    out({"snapshot": f"data/metrics/{today}.json", "rows": f"data/metrics/{today}.rows.json",
         "earnings_30d": totals, "errors": errors})


def cmd_history(args):
    out([
        {"run_id": m["run_id"], "niche": m["niche_id"], "status": m["status"],
         "posts": {p: v.get("status") for p, v in m["posts"].items()}}
        for m in list_manifests()
    ])


def main(argv=None):
    load_dotenv()
    parser = argparse.ArgumentParser(prog="python -m pipeline", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check", help="show which credentials are set").set_defaults(func=cmd_check)

    p = sub.add_parser("budget", help="how many videos to make today within the Higgsfield plan")
    p.add_argument("--balance", type=float, required=True, help="current Higgsfield credits")
    p.add_argument("--date")
    p.set_defaults(func=cmd_budget)

    p = sub.add_parser("trends", help="daily trend snapshot: template | validate | score")
    p.add_argument("action", choices=("template", "validate", "score"))
    p.add_argument("--date")
    p.set_defaults(func=cmd_trends)

    p = sub.add_parser("library", help="script library: validate | stock | pick")
    p.add_argument("action", choices=("validate", "stock", "pick"))
    p.add_argument("--count", type=int, default=1)
    p.set_defaults(func=cmd_library)

    p = sub.add_parser("start-run", help="create a run from a library script")
    p.add_argument("script_id")
    p.set_defaults(func=cmd_start_run)

    p = sub.add_parser("pick-niche", help="choose the next niche by rotation")
    p.add_argument("--niche", help="force a niche id instead of rotating")
    p.set_defaults(func=cmd_pick_niche)

    p = sub.add_parser("new-run", help="create runs/<run_id>/ for a freshly written script")
    p.add_argument("--niche", required=True)
    p.add_argument("--topic", required=True)
    p.set_defaults(func=cmd_new_run)

    for name, func, help_text in (
        ("validate", cmd_validate, "check runs/<run_id>/script.json"),
        ("captions", cmd_captions, "write per-platform captions.json"),
        ("gen-plan", cmd_gen_plan, "write generation.json (Higgsfield requests) for a run"),
        ("render-plan", cmd_render_plan, "check assets.json and write render.json for the assembler"),
        ("publish-status", cmd_publish_status, "poll Upload-Post and record per-platform results"),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("run")
        p.set_defaults(func=func)

    p = sub.add_parser("set-video", help="record the finished Higgsfield-hosted video")
    p.add_argument("run")
    p.add_argument("--url", required=True)
    p.add_argument("--job-id", action="append")
    p.add_argument("--duration", type=float)
    p.add_argument("--credits", type=float)
    p.set_defaults(func=cmd_set_video)

    p = sub.add_parser("record-post", help="record a post made outside this CLI")
    p.add_argument("run")
    p.add_argument("--platform", required=True, choices=("tiktok", "instagram", "youtube", "facebook"))
    p.add_argument("--status", required=True,
                   choices=("published", "draft", "processing", "scheduled", "failed", "skipped"))
    p.add_argument("--id")
    p.add_argument("--url")
    p.add_argument("--note")
    p.set_defaults(func=cmd_record_post)

    p = sub.add_parser("publish", help="publish: all (Upload-Post) or youtube/instagram direct")
    p.add_argument("platform", choices=("all", "youtube", "instagram"))
    p.add_argument("run")
    p.add_argument("--platforms", help="comma list for `all`, default tiktok,instagram,youtube,facebook")
    p.add_argument("--schedule", help="ISO-8601 time to publish (Upload-Post scheduling)")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_publish)

    p = sub.add_parser("earnings", help="log earnings that have no API (TikTok, affiliates)")
    p.add_argument("action", choices=("add",))
    p.add_argument("--platform", required=True)
    p.add_argument("--amount", type=float, required=True)
    p.add_argument("--source", default="creator_rewards")
    p.add_argument("--date")
    p.add_argument("--note")
    p.set_defaults(func=cmd_earnings_add)

    p = sub.add_parser("metrics", help="collect a monetization snapshot for the dashboard")
    p.add_argument("action", choices=("collect",))
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--balance", type=float, help="current Higgsfield credits, shown on the dashboard")
    p.add_argument("--date")
    p.set_defaults(func=cmd_metrics)

    sub.add_parser("history", help="list past runs").set_defaults(func=cmd_history)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
