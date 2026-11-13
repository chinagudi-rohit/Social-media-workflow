"""Run folders. Each video gets runs/<run_id>/ holding script.json and manifest.json."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .config import RUNS_DIR

PLATFORMS = ("instagram", "youtube", "facebook", "twitter")


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slugify(text, max_len=40):
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len].rstrip("-") or "video"


def create_run(niche_id, topic, runs_dir=RUNS_DIR, today=None, **extra):
    today = today or datetime.now(timezone.utc).date().isoformat()
    base = f"{today}-{niche_id}-{slugify(topic)}"
    run_id, n = base, 2
    while (runs_dir / run_id).exists():
        run_id, n = f"{base}-{n}", n + 1
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True)
    manifest = {
        "run_id": run_id,
        "niche_id": niche_id,
        "topic": topic,
        "created_at": now_iso(),
        "status": "created",
        "video": {"url": None, "job_ids": [], "duration_seconds": None, "credits_spent": None},
        "posts": {},
        **extra,
    }
    save_manifest(run_dir, manifest)
    return run_dir


def load_manifest(run_dir):
    with open(Path(run_dir) / "manifest.json", encoding="utf-8") as f:
        return json.load(f)


def save_manifest(run_dir, manifest):
    manifest["updated_at"] = now_iso()
    path = Path(run_dir) / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def load_script(run_dir):
    with open(Path(run_dir) / "script.json", encoding="utf-8") as f:
        return json.load(f)


def record_post(run_dir, platform, **fields):
    """Merge fields into the platform's post record; a field set to None is removed."""
    if platform not in PLATFORMS:
        raise ValueError(f"unknown platform: {platform}")
    manifest = load_manifest(run_dir)
    merged = {**manifest["posts"].get(platform, {}), **fields, "recorded_at": now_iso()}
    manifest["posts"][platform] = {k: v for k, v in merged.items() if v is not None}
    published = [p for p in manifest["posts"].values() if p.get("status") == "published"]
    if published:
        manifest["status"] = "published" if len(published) == len(manifest["posts"]) else "partially_published"
    save_manifest(run_dir, manifest)
    return manifest


def list_manifests(runs_dir=RUNS_DIR):
    """Every run's manifest, with its script's `hook_type` added (insights group by format)."""
    manifests = []
    for path in sorted(runs_dir.glob("*/manifest.json")):
        with open(path, encoding="utf-8") as f:
            m = json.load(f)
        script = path.parent / "script.json"
        if "hook_type" not in m and script.exists():
            with open(script, encoding="utf-8") as f:
                m["hook_type"] = json.load(f).get("hook_type")
        manifests.append(m)
    return manifests
