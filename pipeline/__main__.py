"""Command line for the short-video pipeline. Run `python -m pipeline --help`."""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

from . import instagram, youtube
from .config import ROOT, load_niches, load_platforms, niche_by_id
from .niches import pick_niche, recent_topics
from .runs import (
    create_run,
    list_manifests,
    load_manifest,
    load_script,
    record_post,
    save_manifest,
)
from .script import build_captions, validate

ENV_KEYS = {
    "youtube": ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"),
    "instagram": ("IG_USER_ID", "IG_ACCESS_TOKEN"),
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


def missing_env(platform):
    return [k for k in ENV_KEYS[platform] if not os.environ.get(k)]


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


def cmd_check(args):
    out({p: {"ready": not missing_env(p), "missing": missing_env(p)} for p in ENV_KEYS} | {
        "tiktok": {"ready": None, "note": "checked through the Higgsfield MCP (tiktok_accounts)"},
    })


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
    (Path(args.run) / "captions.json").write_text(json.dumps(captions, indent=2, ensure_ascii=False) + "\n")
    out(captions)


def cmd_set_video(args):
    manifest = load_manifest(args.run)
    manifest["video"] = {
        "url": args.url,
        "job_ids": args.job_id or [],
        "duration_seconds": args.duration,
        "credits_spent": args.credits,
    }
    manifest["status"] = "video_ready"
    save_manifest(args.run, manifest)
    print("ok")


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


def cmd_publish(args):
    run_dir, platform = Path(args.run), args.platform
    captions = captions_for(run_dir)[platform]
    video_url = load_manifest(run_dir)["video"]["url"]
    if not video_url:
        fail("no video yet; run `set-video` with the Higgsfield URL first")
    platforms = load_platforms()

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
                session,
                os.environ["YT_CLIENT_ID"],
                os.environ["YT_CLIENT_SECRET"],
                os.environ["YT_REFRESH_TOKEN"],
            )
            result = youtube.upload(
                session, token, video_path, youtube.build_metadata(captions, platforms["youtube"])
            )
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


def cmd_history(args):
    out([
        {
            "run_id": m["run_id"],
            "niche": m["niche_id"],
            "status": m["status"],
            "posts": {p: v.get("status") for p, v in m["posts"].items()},
        }
        for m in list_manifests()
    ])


def main(argv=None):
    load_dotenv()
    parser = argparse.ArgumentParser(prog="python -m pipeline", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check", help="show which publishing credentials are set").set_defaults(func=cmd_check)

    p = sub.add_parser("pick-niche", help="choose the next niche to post in")
    p.add_argument("--niche", help="force a niche id instead of rotating")
    p.set_defaults(func=cmd_pick_niche)

    p = sub.add_parser("new-run", help="create runs/<run_id>/ for a new video")
    p.add_argument("--niche", required=True)
    p.add_argument("--topic", required=True)
    p.set_defaults(func=cmd_new_run)

    for name, func, help_text in (
        ("validate", cmd_validate, "check runs/<run_id>/script.json"),
        ("captions", cmd_captions, "write per-platform captions.json"),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("run")
        p.set_defaults(func=func)

    p = sub.add_parser("set-video", help="record the finished Higgsfield video")
    p.add_argument("run")
    p.add_argument("--url", required=True, help="Higgsfield-hosted video URL")
    p.add_argument("--job-id", action="append", help="Higgsfield job id (repeatable)")
    p.add_argument("--duration", type=float)
    p.add_argument("--credits", type=float)
    p.set_defaults(func=cmd_set_video)

    p = sub.add_parser("record-post", help="record a post made outside this CLI (e.g. TikTok via Higgsfield)")
    p.add_argument("run")
    p.add_argument("--platform", required=True, choices=("tiktok", "instagram", "youtube"))
    p.add_argument("--status", required=True, choices=("published", "draft", "processing", "failed", "skipped"))
    p.add_argument("--id")
    p.add_argument("--url")
    p.add_argument("--note")
    p.set_defaults(func=cmd_record_post)

    p = sub.add_parser("publish", help="publish to YouTube Shorts or Instagram Reels")
    p.add_argument("platform", choices=("youtube", "instagram"))
    p.add_argument("run")
    p.add_argument("--dry-run", action="store_true", help="print what would be posted")
    p.set_defaults(func=cmd_publish)

    sub.add_parser("history", help="list past runs").set_defaults(func=cmd_history)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
