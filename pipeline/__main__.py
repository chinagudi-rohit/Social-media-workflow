"""Command line for the short-video pipeline. Run `python -m pipeline --help`."""

import argparse
import csv
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

from . import (budget, dashboard, expenses, experiment, forecast, imports, insights, instagram, library, metrics, metricool, milestones,
               production, timing, trends, uploadpost, youtube)
from .config import ROOT, load_niches, load_platforms, load_yaml, niche_by_id, strategy_weights
from .niches import pick_niche, recent_topics
from .runs import (
    create_run,
    list_manifests,
    load_manifest,
    load_script,
    now_iso,
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
    errors = validate(script, load_niches(include_inactive=True), load_platforms())
    if errors:
        fail("script.json is invalid:\n  - " + "\n  - ".join(errors))
    return script


def captions_for(run_dir):
    script = checked_script(run_dir)
    arms = (load_manifest(run_dir).get("experiment") or {}).get("arms") or {}
    tags = None
    if arms.get("hashtags"):
        sets = load_yaml("experiment.yaml").get("hashtag_sets") or {}
        tags = sets.get(arms["hashtags"], {}).get(script["niche_id"], sets.get(arms["hashtags"], {}).get("default"))
    return build_captions(script, niche_by_id(script["niche_id"]), load_platforms(), hashtags=tags)


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
    since = days_since_last_video(list_manifests(), today)
    plan = budget.plan_today(prod, args.balance, today, since)
    trial = production.trial_tier(prod, list_manifests())
    if trial != prod["tier"]:
        # The next video is the owner's trial tier: its extra cost comes off the balance first,
        # and the pacing follows `tier`.
        tier = prod["tiers"][trial]
        typical = tier.get("typical") or {}
        cost = budget.video_cost(tier, typical.get("words", 105), typical.get("pictures", 7), typical.get("clip_seconds"))
        extra = max(0.0, cost - plan["est_cost_per_video"])
        plan = {**budget.plan_today(prod, args.balance - extra, today, since), "balance": args.balance,
                "trial_tier": trial, "trial_est_cost": cost}
    exp = load_yaml("experiment.yaml")
    if experiment.active(exp, today):
        # The owner set aside a fixed share of the month's credits for the test.
        manifests = list_manifests()
        left = max(0.0, exp["credit_cap"] - experiment.credits_spent(manifests, exp["id"]))
        made_today = sum(1 for m in experiment.runs_in(manifests, exp["id"]) if m["created_at"][:10] == str(today))
        afford = int(min(left, args.balance - prod["plan"]["reserve_credits"]) // exp["est_cost_per_video"])
        plan.update(experiment=exp["id"], experiment_credits_left=round(left, 2),
                    videos_today=max(0, min(exp["videos_per_day"] - made_today, afford)))
    out(plan)


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
        out(trends.score_niches(niches, snap, list_manifests(), datetime.now(timezone.utc), strategy_weights()))


def cmd_library(args):
    niches, platforms, manifests = load_niches(), load_platforms(), list_manifests()
    all_niches = load_niches(include_inactive=True)
    scripts = library.load_scripts()
    if args.action == "validate":
        bad = {s["id"]: e for s in scripts
               if (e := validate_library(s, all_niches, platforms, library.STRUCTURES))}
        if bad:
            fail(json.dumps(bad, indent=2))
        print(f"ok ({len(scripts)} scripts)")
    elif args.action == "stock":
        active = {n["id"] for n in niches}
        out({k: v for k, v in library.stock(scripts, manifests).items() if k in active})
    else:
        snap = trends.load_latest()
        scored = trends.score_niches(niches, snap, manifests, datetime.now(timezone.utc), strategy_weights())
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
    manifests = list_manifests()
    tier = production.trial_tier(prod, manifests, manifest["run_id"])   # the owner's trial tier first
    key_cfg = prod["tiers"][tier]["keyframe"].get("style_key") or {}
    tried = sum(1 for m in manifests if m.get("style_key") and m["run_id"] != manifest["run_id"])
    mode = key_cfg.get("mode", "trial") if key_cfg else "off"
    plan = production.generation_requests(script, niche_by_id(script["niche_id"]), prod, voice,
                                          style_key=mode == "always" or (mode == "trial" and tried < key_cfg.get("trial_videos", 0)),
                                          tier_name=tier)
    write_json(Path(args.run) / "generation.json", plan)
    manifest.update(style_key=plan["style_key"], tier=plan["tier"], multishot=plan.get("multishot", False))
    save_manifest(args.run, manifest)
    out({"tier": plan["tier"], "estimated_credits": plan["estimated_credits"], "keyframes": len(plan["keyframes"]),
         "motion": len(plan["motion"]), "voice": plan["voice"]["voice_name"], "style_key": plan["style_key"],
         "multishot": plan.get("multishot", False)})


def cmd_render_plan(args):
    run = Path(args.run)
    script = checked_script(run)
    assets = read_json(run / "assets.json")
    generation = read_json(run / "generation.json")
    errors = production.validate_assets(assets, script, generation)
    if errors:
        fail("assets.json is incomplete:\n  - " + "\n  - ".join(errors))
    render_cfg = load_yaml("production.yaml")["render"]
    write_json(run / "render.json", production.render_plan(script, assets, render_cfg, generation))
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
    fields = {k: v for k, v in {"status": args.status, "id": args.id, "url": args.url, "note": args.note,
                                "at": args.at, "via": args.via}.items() if v}
    out(record_post(args.run, args.platform, **fields)["posts"][args.platform])


def targets(args_platforms=None):
    """Platforms to post to: --platforms if given, else `targets` in config/platforms.yaml."""
    return args_platforms.split(",") if args_platforms else list(load_platforms()["targets"])


def post_plan(run_id, platforms, now=None, explore=True):
    """Today's post time per platform for this run (config/timing.yaml)."""
    cfg = load_yaml("timing.yaml")
    if not explore:
        cfg["explore_rate"] = 0
    now = now or datetime.now(timezone.utc)
    day = now.astimezone(ZoneInfo(cfg["timezone"])).date()
    return timing.plan(cfg, day, now, list_manifests(), timing.load_audience(on_or_before=day), platforms, run_id)


def cmd_timing(args):
    cfg = load_yaml("timing.yaml")
    tz = ZoneInfo(cfg["timezone"])
    if args.action == "validate":
        path = Path(args.file) if args.file else None
        doc = read_json(path) if path else timing.load_audience()
        if doc is None:
            fail("no audience file in data/timing/")
        errors = timing.validate_audience(doc)
        if doc.get("timezone") and doc["timezone"] != cfg["timezone"]:
            errors.append(f"hours must be in {cfg['timezone']} (config/timing.yaml), not {doc['timezone']}")
        if errors:
            fail("\n".join(errors))
        print("ok")
        return
    now = datetime.fromisoformat(args.now) if args.now else datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=tz)
    out(post_plan(args.run_id or "", targets(args.platforms), now))


def cmd_post_stats(args):
    post = load_manifest(args.run)["posts"].get(args.platform) or {}
    if not post.get("at"):
        fail(f"no post time recorded for {args.platform}; record-post it with --at first")
    now = datetime.fromisoformat(args.now) if args.now else datetime.now(timezone.utc)
    age = (now - datetime.fromisoformat(post["at"].replace("Z", "+00:00"))).total_seconds() / 3600
    if age <= 0:
        fail("that post has not gone out yet")
    fields = {"views": args.views, "views_age_hours": round(age, 1), "stats_at": now.isoformat(timespec="seconds"),
              "avg_view_seconds": args.avg_view_seconds, "likes": args.likes, "comments": args.comments,
              "shares": args.shares, "saves": args.saves, "follows": args.follows, "reach": args.reach}
    out(record_post(args.run, args.platform, **{k: v for k, v in fields.items() if v is not None})["posts"][args.platform])


def cmd_post_stats_import(args):
    path = Path(args.file).resolve()
    now = datetime.fromisoformat(args.now.replace("Z", "+00:00"))
    tz_name = args.tz or load_platforms()["metricool"]["brand_timezone"]
    manifests = list_manifests()
    titles = {m["run_id"]: imports.titles(ROOT / "runs" / m["run_id"]) for m in manifests}
    matched, unmatched = imports.match(imports.read(path), manifests, titles, tz_name, now)
    source = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else path.name
    posts = {m["run_id"]: m.get("posts") or {} for m in manifests}
    updated, kept = [], []
    for run_id, platform, row in matched:
        fields = imports.record(posts[run_id][platform], row["fields"], now, source)
        if fields is None:
            kept.append(f"{run_id} {platform}")
            continue
        if not args.dry_run:
            record_post(ROOT / "runs" / run_id, platform, **fields)
        updated.append({"run": run_id, "platform": platform, "title": row["title"], "views": fields.get("views")})
    out({"file": source, "dry_run": args.dry_run, "updated": updated, "kept_newer": kept,
         "unmatched": [{"platform": r["platform"], "title": r["title"], "why": why} for r, why in unmatched]})


def cmd_experiment(args):
    exp = load_yaml("experiment.yaml")
    manifests = list_manifests()
    if args.action == "plan":
        done = experiment.runs_in(manifests, exp["id"])
        out({"experiment": exp["id"], "active": experiment.active(exp, date.today()), "videos_so_far": len(done),
             "credits_spent": experiment.credits_spent(manifests, exp["id"]), "credit_cap": exp["credit_cap"],
             "next": experiment.assign(exp["variables"], args.count, start=len(done), seed=exp["id"]),
             "post_hours": exp["post_hours"]})
    elif args.action == "tag":
        manifest = load_manifest(args.run)
        manifest["experiment"] = {"id": exp["id"], "arms": json.loads(args.arms)}
        unknown = set(manifest["experiment"]["arms"]) - set(exp["variables"])
        if unknown:
            fail(f"unknown variables: {', '.join(sorted(unknown))}")
        save_manifest(args.run, manifest)
        out(manifest["experiment"])
    elif args.action == "ingest":
        now = datetime.fromisoformat(args.now) if args.now else experiment.now_utc()
        answer = read_json(Path(args.file))
        stats = experiment.parse_rows(args.platform, answer)
        experiment.save(experiment.snapshot_path(exp["id"], now, args.platform), {"at": now.isoformat(), "rows": stats})
        updated = experiment.merge(manifests, args.platform, stats, now)
        for run_id, fields in updated:
            record_post(ROOT / "runs" / run_id, args.platform, **fields)
        out({"platform": args.platform, "rows": len(stats), "posts_updated": [r for r, _ in updated]})
    else:
        rep = experiment.report(manifests, exp)
        path = experiment.save(experiment.EXP_DIR / exp["id"] / "report.json", rep)
        out({"file": str(path.relative_to(ROOT)), **{k: v for k, v in rep.items() if k != "videos_detail"}})


def cmd_insights(args):
    """What is working, by niche, structure, voice, post hour and length; saved for the record."""
    manifests = list_manifests()
    rows = insights.video_rows(manifests, load_yaml("timing.yaml")["timezone"])
    summary = insights.summarize(rows)
    day = args.date or str(date.today())
    path = ROOT / "data" / "insights" / f"{day}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, {"date": day, "videos": len(rows), "phase": load_yaml("production.yaml")["strategy"]["phase"],
                      "summary": summary, "videos_detail": rows})
    out({"file": str(path.relative_to(ROOT)), "videos_with_stats": len(rows),
         "best": [r for r in summary if r["lift"] > 0][:8], "worst": [r for r in summary if r["lift"] < 0][-5:]})


def download(url, dest):
    if dest.exists() and dest.stat().st_size:
        return dest
    with requests.get(url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(1 << 20):
                f.write(chunk)
    return dest


ACTIVE = ("scheduled", "published", "processing")


def publish_all(args, run_dir, captions, video_url, platforms_cfg):
    """Upload-Post: one request per post time (platforms sharing a slot go together)."""
    manifest = load_manifest(run_dir)
    run_id = manifest["run_id"]
    send_to = targets(args.platforms)
    if not args.force:
        send_to = [p for p in send_to if (manifest["posts"].get(p) or {}).get("status") not in ACTIVE]
        if not send_to:
            fail("already scheduled or published everywhere asked (use --force to send again)")
    tz_name = load_yaml("timing.yaml")["timezone"]
    if args.schedule == "auto":
        times = {p: e["at"] for p, e in post_plan(run_id, send_to).items()}
    elif args.schedule:
        at = datetime.fromisoformat(args.schedule)
        at = at if at.tzinfo else at.replace(tzinfo=ZoneInfo(tz_name))
        times = {p: at.isoformat() for p in send_to}
    else:
        times = {p: None for p in send_to}
    batches = {}
    for p in send_to:
        batches.setdefault(times[p], []).append(p)

    sends = []
    for at, group in sorted(batches.items(), key=lambda kv: kv[0] or ""):
        request_id = run_id if len(batches) == 1 else f"{run_id}-{'-'.join(group)}"
        fields = uploadpost.build_form(
            captions, video_url, os.environ.get("UPLOADPOST_USER", "<UPLOADPOST_USER>"), group, platforms_cfg,
            request_id, uploadpost.local_time(at, tz_name) if at else None,
            os.environ.get("UPLOADPOST_FACEBOOK_PAGE_ID"), tz_name if at else None,
        )
        sends.append({"request_id": request_id, "platforms": group, "at": at, "fields": fields})
    if args.dry_run:
        out(sends)
        return
    if missing_env("uploadpost"):
        fail(f"missing credentials: {', '.join(missing_env('uploadpost'))} (see .env.example)")

    session, results = requests.Session(), []
    for send in sends:
        body = uploadpost.publish(session, os.environ["UPLOADPOST_API_KEY"], send["fields"], send["request_id"])
        manifest = load_manifest(run_dir)
        manifest.setdefault("upload_requests", {})[body.get("request_id", send["request_id"])] = {
            "platforms": send["platforms"], "job_id": body.get("job_id")}
        save_manifest(run_dir, manifest)
        for p in send["platforms"]:
            record_post(run_dir, p, status="scheduled" if send["at"] else "processing",
                        at=send["at"] or now_iso(), via="uploadpost", error=None)
        results.append({"request_id": send["request_id"], "platforms": send["platforms"], "at": send["at"],
                        "response": body})
    out(results)


def cmd_publish_plan(args):
    """Per-platform posts for a publisher driven through MCP tools (Metricool)."""
    run_dir = Path(args.run)
    manifest = load_manifest(run_dir)
    if not manifest["video"]["url"]:
        fail("no video yet; run `set-video` with the Higgsfield URL first")
    caps = captions_for(run_dir)
    send_to = [p for p in targets(args.platforms)
               if args.force or (manifest["posts"].get(p) or {}).get("status") not in ACTIVE]
    tz_name = load_yaml("timing.yaml")["timezone"]
    if args.at:
        times = {p: {"at": datetime.fromisoformat(args.at).isoformat(), "explore": False} for p in send_to}
    elif args.asap:
        lead = load_yaml("timing.yaml")["min_lead_minutes"]
        soon = (datetime.now(timezone.utc) + timedelta(minutes=lead)).astimezone(ZoneInfo(tz_name))
        times = {p: {"at": soon.replace(second=0, microsecond=0).isoformat(), "explore": False} for p in send_to}
    else:
        times = post_plan(manifest["run_id"], send_to)
    yt, ig = caps["youtube"], caps["instagram"]
    texts = {
        "instagram": {"text": ig["caption"], "first_comment": ig.get("first_comment") or ""},
        "youtube": {"title": yt["title"], "text": yt["description"], "tags": yt["tags"]},
        # Facebook shows the video title as is: YouTube's #Shorts tag does not belong there.
        "facebook": {"title": yt["title"].replace(" #Shorts", ""), "text": ig["caption"],
                     "first_comment": ig.get("first_comment") or ""},
        "twitter": {"text": caps["twitter"]["text"]},
    }
    posts = [{
        "platform": p,
        "at": times[p]["at"],
        "local_time": uploadpost.local_time(times[p]["at"], tz_name),
        "timezone": tz_name,
        "video_url": manifest["video"]["url"],
        **texts[p],
        "ai_generated": True,
        "ai_disclosure_fallback": "Made with AI.",
        "explore": times[p]["explore"],
    } for p in send_to]
    cfg = load_platforms()
    for post in posts:
        post["metricool"] = metricool.schedule_args(post, cfg)
    write_json(run_dir / "publish_plan.json", posts)
    out(posts)


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
    out(record_post(run_dir, platform, status="published", at=now_iso(), via=f"{platform}_api", error=None,
                    **result)["posts"][platform])


def cmd_publish_status(args):
    if missing_env("uploadpost"):
        fail(f"missing credentials: {', '.join(missing_env('uploadpost'))}")
    manifest = load_manifest(args.run)
    reqs = dict(manifest.get("upload_requests") or {})
    if not reqs and (manifest.get("upload_request_id") or manifest.get("upload_job_id")):
        reqs[manifest.get("upload_request_id")] = {"job_id": manifest.get("upload_job_id")}
    if not reqs:
        fail("this run has no Upload-Post request; publish it first")
    session, states = requests.Session(), {}
    for rid, info in reqs.items():
        jid = info.get("job_id")
        body = uploadpost.status(session, os.environ["UPLOADPOST_API_KEY"], request_id=None if jid else rid, job_id=jid)
        states[rid] = body.get("status")
        for platform, r in uploadpost.platform_results(body).items():
            if platform not in timing.PLATFORMS:
                continue
            fields = {"status": "draft" if r["draft"] else r["status"], "error": r["error"]}
            fields.update({k: r[k] for k in ("url", "id") if r[k]})
            record_post(args.run, platform, **fields)
    out({"requests": states, "posts": load_manifest(args.run)["posts"]})


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


def cmd_expense_add(args):
    """One charge for running the channel (not the Claude subscription), as billed."""
    today = expenses.default_today(load_yaml("dashboard.yaml")["locale"])
    expenses.add({"date": args.date or str(today), "service": args.service, "item": args.item,
                  "amount": f"{args.amount:.2f}", "currency": args.currency.upper(),
                  "local_amount": "" if args.local_amount is None else f"{args.local_amount:.2f}",
                  "recurring": args.recurring, "source": args.source or ""})
    print("ok")


def cmd_metrics(args):
    today = date.fromisoformat(args.date) if args.date else date.today()
    start, end = metrics.default_window(today, args.days)
    session = requests.Session()
    errors, stats, yt_rows, fb_rows = {}, {}, [], []

    if not missing_env("uploadpost"):
        try:
            body = uploadpost.analytics(session, os.environ["UPLOADPOST_API_KEY"], os.environ["UPLOADPOST_USER"],
                                        targets(), os.environ.get("UPLOADPOST_FACEBOOK_PAGE_ID"))
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

    series, periods = {}, {}
    if args.stats_file:
        # Followers and views per platform read from Metricool by the autopilot:
        # {"instagram": {"followers": 812, "views": 40210, "views_90d": 40210,
        #                "daily": [{"day": "2026-10-18", "followers": 1, "views": 565}, ...]}, ...}
        # A platform whose views Metricool lags on may carry a total read elsewhere instead:
        #   "period": {"from": "2026-10-18", "to": "2026-10-19", "views": 2860, "source": "YouTube Studio"}
        for platform, counters in read_json(Path(args.stats_file)).items():
            series[platform] = counters.pop("daily", [])
            if counters.get("period"):
                periods[platform] = counters.pop("period")
            stats[platform] = {**stats.get(platform, {}), **{k: v for k, v in counters.items() if v is not None}}
    manual = metrics.manual_earnings()
    totals = metrics.earnings_by_platform(yt_rows, fb_rows, manual, start, end)
    sources = {r["platform"]: "Logged by hand" for r in manual}
    if not missing_env("youtube") and "youtube_revenue" not in errors:
        sources["youtube"] = "YouTube Analytics"
    if not missing_env("facebook_earnings") and "facebook_earnings" not in errors:
        sources["facebook"] = "Facebook insights"
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
         "shelved": m.get("shelved"),
         "posts": {p: {"status": v.get("status"), "url": v.get("url")} for p, v in m.get("posts", {}).items()}}
        for m in list_manifests()
    ]
    credits = {"spent_30d": round(sum(r["credits"] or 0 for r in runs if r["date"] >= str(start)), 2),
               "balance": args.balance}
    snap = metrics.snapshot(today, stats, totals, [{"date": d, **v} for d, v in sorted(daily.items())], runs, credits)
    snap["errors"] = errors
    if args.runway_plan_left is not None:
        snap["runway"] = {"plan_left": args.runway_plan_left, "purchased": args.runway_purchased,
                          "balance": args.runway_plan_left + args.runway_purchased}
    snap["linked"] = args.linked.split(",") if args.linked else []
    if "youtube" in snap["linked"]:
        sources.setdefault("youtube", "Metricool (live)")
    snap["earnings_sources"] = sources
    metrics.METRICS_DIR.mkdir(parents=True, exist_ok=True)
    write_json(metrics.METRICS_DIR / f"{today}.json", snap)

    niches = load_niches()
    scored = trends.score_niches(niches, trends.load_latest(on_or_before=today), list_manifests(),
                                 datetime.now(timezone.utc), strategy_weights())
    plan = post_plan("", targets(), explore=False)
    locale = load_yaml("dashboard.yaml")["locale"]
    files = dashboard.datasets(snap, load_yaml("production.yaml"), scored, niches, today, plan,
                               load_yaml("timing.yaml")["timezone"], targets(), load_yaml("monetization.yaml"),
                               locale, expenses.load())
    used = [p for p in targets() if p in snap["linked"]] or targets()
    # Growth history: every day on record across all stats files, today's file last.
    current = Path(args.stats_file).resolve() if args.stats_file else None
    older = [read_json(f) for f in sorted(metrics.METRICS_DIR.glob("*.stats.json")) if f.resolve() != current]
    merged = forecast.history(older + [{p: {"daily": d} for p, d in series.items()}])
    files["forecast"] = forecast.rows(merged, {p: (stats.get(p) or {}).get("followers") for p in used},
                                      load_yaml("forecast.yaml"), expenses.default_today(locale), used, periods)
    files["insights"] = dashboard.insight_rows(
        insights.summarize(insights.video_rows(list_manifests(), load_yaml("timing.yaml")["timezone"])), niches)
    out_dir = ROOT / "data" / "dashboard"
    out_dir.mkdir(parents=True, exist_ok=True)
    changed = []
    for name, rows in files.items():
        path = out_dir / f"{name}.json"
        text = json.dumps(rows, indent=1, ensure_ascii=False) + "\n"
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            path.write_text(text, encoding="utf-8")
            changed.append(f"data/dashboard/{name}.json")
    out({"snapshot": f"data/metrics/{today}.json", "dashboard_files_changed": changed,
         "earnings_30d": totals, "errors": errors})


def cmd_milestones(args):
    """Monetization steps reached since the last check, and the next step per platform."""
    snaps = sorted(metrics.METRICS_DIR.glob("*.json"))
    snaps = [p for p in snaps if "." not in p.stem]          # skip *.rows.json and *.stats.json
    stats = read_json(snaps[-1]).get("platforms", {}) if snaps else {}
    for counters in stats.values():
        counters.setdefault("views_90d", counters.get("views"))
    announced = milestones.load_announced()
    ladder = {p: steps for p, steps in load_yaml("monetization.yaml").items() if p in targets()}
    new, upcoming = milestones.check(ladder, stats, announced)
    if not args.dry_run:
        milestones.save_announced(announced + [milestones.key(s["platform"], s) for s in new])
    out({"reached": new, "next": upcoming})


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
    p.add_argument("--platform", required=True, choices=timing.PLATFORMS)
    p.add_argument("--status", required=True,
                   choices=("published", "draft", "processing", "scheduled", "failed", "skipped"))
    p.add_argument("--id")
    p.add_argument("--url")
    p.add_argument("--note")
    p.add_argument("--at", help="when it goes or went out, ISO-8601 with offset")
    p.add_argument("--via", help="publisher, e.g. metricool")
    p.set_defaults(func=cmd_record_post)

    p = sub.add_parser("timing", help="post times: plan (today's slot per platform) | validate (audience file)")
    p.add_argument("action", choices=("plan", "validate"))
    p.add_argument("--platforms", help="comma list, default `targets` in config/platforms.yaml")
    p.add_argument("--run-id", help="the run being planned (keeps re-plans stable)")
    p.add_argument("--now", help="plan as of this ISO time (testing)")
    p.add_argument("--file", help="audience file to validate (default: newest in data/timing/)")
    p.set_defaults(func=cmd_timing)

    p = sub.add_parser("post-stats", help="record a post's views so post times learn from results")
    p.add_argument("run")
    p.add_argument("--platform", required=True, choices=timing.PLATFORMS)
    p.add_argument("--views", type=int, required=True)
    p.add_argument("--avg-view-seconds", type=float, help="average view duration")
    p.add_argument("--likes", type=int)
    p.add_argument("--comments", type=int)
    p.add_argument("--shares", type=int)
    p.add_argument("--saves", type=int)
    p.add_argument("--follows", type=int, help="follows the post brought in")
    p.add_argument("--reach", type=int, help="accounts reached")
    p.add_argument("--now", help="when the views were read, ISO-8601 (default now)")
    p.set_defaults(func=cmd_post_stats)

    p = sub.add_parser("post-stats-import",
                       help="record many posts' numbers from an owner export (YouTube Studio, Meta Business Suite)")
    p.add_argument("file", help="CSV: platform,title,published[,views,reach,avg_view_seconds,likes,comments,"
                                "shares,saves,follows] (see pipeline/imports.py)")
    p.add_argument("--now", required=True, help="when the numbers were read, ISO-8601")
    p.add_argument("--tz", help="timezone of the published column (default: the Metricool brand's)")
    p.add_argument("--dry-run", action="store_true", help="show the matches, change nothing")
    p.set_defaults(func=cmd_post_stats_import)

    p = sub.add_parser("experiment", help="reach test: plan arms | tag RUN | ingest Metricool rows | report")
    p.add_argument("action", choices=("plan", "tag", "ingest", "report"))
    p.add_argument("run", nargs="?")
    p.add_argument("--count", type=int, default=8, help="plan: how many videos to assign")
    p.add_argument("--arms", help="tag: JSON of the video's arms, as `plan` gave them")
    p.add_argument("--platform", choices=tuple(experiment.METRICS), help="ingest: which network's rows")
    p.add_argument("--file", help="ingest: Metricool getAnalyticsDataByMetrics answer saved as JSON")
    p.add_argument("--now")
    p.set_defaults(func=cmd_experiment)

    p = sub.add_parser("insights", help="what is working: results by niche, format, structure, voice, hour, length")
    p.add_argument("--date")
    p.set_defaults(func=cmd_insights)

    p = sub.add_parser("publish", help="publish: all (Upload-Post) or youtube/instagram direct")
    p.add_argument("platform", choices=("all", "youtube", "instagram"))
    p.add_argument("run")
    p.add_argument("--platforms", help="comma list for `all`, default `targets` in config/platforms.yaml")
    p.add_argument("--schedule", help="'auto' for each platform's best slot today (config/timing.yaml), "
                                      "or one ISO-8601 time for all")
    p.add_argument("--force", action="store_true", help="send again to platforms already scheduled")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_publish)

    p = sub.add_parser("publish-plan", help="per-platform posts and times for an MCP publisher (Metricool)")
    p.add_argument("run")
    p.add_argument("--platforms", help="comma list, default `targets` in config/platforms.yaml")
    p.add_argument("--force", action="store_true", help="include platforms already scheduled")
    p.add_argument("--asap", action="store_true", help="every platform as soon as allowed (test rounds)")
    p.add_argument("--at", help="ISO time with offset for every platform (experiment post grid)")
    p.set_defaults(func=cmd_publish_plan)

    p = sub.add_parser("earnings", help="log earnings that have no API (Instagram Gifts, affiliates)")
    p.add_argument("action", choices=("add",))
    p.add_argument("--platform", required=True)
    p.add_argument("--amount", type=float, required=True)
    p.add_argument("--source", default="creator_rewards")
    p.add_argument("--date")
    p.add_argument("--note")
    p.set_defaults(func=cmd_earnings_add)

    p = sub.add_parser("expense", help="log a charge for running the channel (subscriptions, top-ups)")
    p.add_argument("action", choices=("add",))
    p.add_argument("--service", required=True, help="e.g. Higgsfield, Runway, Metricool")
    p.add_argument("--item", required=True, help="e.g. 'Plus plan', '1000 credits'")
    p.add_argument("--amount", type=float, required=True, help="as billed, in --currency")
    p.add_argument("--currency", default="USD")
    p.add_argument("--local-amount", type=float, help="what the card was charged in the owner's currency, if shown")
    p.add_argument("--recurring", choices=("monthly", "yearly", "one-off"), default="monthly")
    p.add_argument("--source", help="receipt number or bank alert it came from")
    p.add_argument("--date", help="charge date in the owner's time zone, YYYY-MM-DD")
    p.set_defaults(func=cmd_expense_add)

    p = sub.add_parser("metrics", help="collect a monetization snapshot for the dashboard")
    p.add_argument("action", choices=("collect",))
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--balance", type=float, help="current Higgsfield credits, shown on the dashboard")
    p.add_argument("--linked", help="networks linked in Metricool, comma list (from getBrandSettings)")
    p.add_argument("--stats-file", help="JSON of followers/views per platform read from Metricool")
    p.add_argument("--runway-plan-left", type=float, help="Runway whoami credits.plan (this cycle's plan credits left)")
    p.add_argument("--runway-purchased", type=float, default=0, help="Runway whoami credits.purchased")
    p.add_argument("--date")
    p.set_defaults(func=cmd_metrics)

    p = sub.add_parser("milestones", help="monetization steps reached and coming (config/monetization.yaml)")
    p.add_argument("--dry-run", action="store_true", help="do not mark reached steps as announced")
    p.set_defaults(func=cmd_milestones)

    sub.add_parser("history", help="list past runs").set_defaults(func=cmd_history)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
