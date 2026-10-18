"""Install or update the Hermes instance: five profiles, the kanban board, the kickoff cron.

Run through hermes/setup/install.sh (it prepares .venv first). Safe to re-run: existing
profiles are updated in place, the board and the cron job are created only once.

    .venv/bin/python hermes/setup/install.py [--only fm-writer] [--dry-run]

What it does for each hermes/profiles/<name>/profile.yaml:
  - `hermes profile create <name> --no-skills` when the profile does not exist yet;
  - `hermes profile describe <name> --text ...` (the kanban orchestrator reads it);
  - `hermes -p <name> config set <key> <value>` for every entry under `config`, with
    "{repo}" replaced by this repo's path;
  - copies SOUL.md; copies the `env_from_default` keys from ~/.hermes/.env into the
    profile's .env (values are never printed); copies memories/USER.md when
    `copy_user_memory` is set.
Then: the `faceless` board, fm-lead's scripts/fm-kickoff.sh, and the fm-kickoff cron job
(07:54 America/New_York, created paused).
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from pipeline import hermes_ops  # noqa: E402

PROFILES_DIR = REPO / "hermes" / "profiles"
ROOT = hermes_ops.HERMES_ROOT

KICKOFF_SH = """#!/bin/bash
# Installed by hermes/setup/install.py. fm-lead's no-agent cron runs this at 07:54 ET:
# plan today's run and create its kanban cards. Its stdout goes to #faceless.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
exec "{repo}/fm" hermes kickoff
"""


def sh(cmd, dry, check=True):
    print("  $ " + " ".join(c if " " not in c and c else repr(c) for c in cmd))
    if dry:
        return ""
    res = subprocess.run(cmd, capture_output=True, text=True)
    if check and res.returncode != 0:
        sys.exit(f"failed: {' '.join(cmd[:4])}\n{res.stderr or res.stdout}")
    return res.stdout


def fill(value):
    if isinstance(value, str):
        return value.replace("{repo}", str(REPO))
    if isinstance(value, list):
        return [fill(v) for v in value]
    if isinstance(value, dict):
        return {k: fill(v) for k, v in value.items()}
    return value


def read_env(path):
    env = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v
    return env


def copy_env_keys(name, keys, dry):
    source = read_env(ROOT / ".env")
    target = hermes_ops.profile_home(name) / ".env"
    lines = target.read_text(encoding="utf-8").splitlines() if target.exists() else []
    copied = []
    for key in keys:
        if key not in source:
            continue
        lines = [ln for ln in lines if not ln.split("=", 1)[0].strip() == key]
        lines.append(f"{key}={source[key]}")
        copied.append(key)
    print(f"  .env: {', '.join(copied) or 'nothing to copy'} (values not shown)")
    if not dry and copied:
        target.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.chmod(target, 0o600)


def install_profile(spec_dir, dry):
    name = spec_dir.name
    spec = yaml.safe_load((spec_dir / "profile.yaml").read_text(encoding="utf-8"))
    home = hermes_ops.profile_home(name)
    print(f"\n{name}")
    if not (home / "config.yaml").exists():
        sh(["hermes", "profile", "create", name, "--no-skills"], dry)
    sh(["hermes", "profile", "describe", name, "--text", " ".join(spec["description"].split())], dry)
    for key, value in spec["config"].items():
        value = fill(value)
        text = value if isinstance(value, str) else json.dumps(value)
        sh(["hermes", "-p", name, "config", "set", key, text], dry)
    print("  SOUL.md")
    if not dry:
        shutil.copyfile(spec_dir / "SOUL.md", home / "SOUL.md")
    if spec.get("env_from_default"):
        copy_env_keys(name, spec["env_from_default"], dry)
    if spec.get("copy_user_memory"):
        src, dst = ROOT / "memories" / "USER.md", home / "memories" / "USER.md"
        if src.exists() and not dst.exists():
            print("  memories/USER.md")
            if not dry:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)


def install_kickoff(cfg, dry):
    lead = cfg["profiles"]["lead"]
    home = hermes_ops.profile_home(lead)
    script = home / "scripts" / "fm-kickoff.sh"
    print(f"\nkickoff cron ({lead})\n  {script}")
    if not dry:
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text(KICKOFF_SH.replace("{repo}", str(REPO)), encoding="utf-8")
        script.chmod(0o755)
    jobs_file = home / "cron" / "jobs.json"
    jobs = json.loads(jobs_file.read_text(encoding="utf-8")).get("jobs", []) if jobs_file.exists() else []
    if any(j.get("name") == "fm-kickoff" for j in jobs):
        print("  fm-kickoff already exists (left as is)")
        return
    chat = cfg["notify"].get("chat_id")
    deliver = f"{cfg['notify']['platform']}:{chat}" if chat else "local"
    sh(["hermes", "-p", lead, "cron", "create", "54 7 * * *", "--name", "fm-kickoff",
        "--script", "fm-kickoff.sh", "--no-agent", "--deliver", deliver,
        "--paused", "--paused-reason", "Finish hermes/SETUP.md, then resume"], dry)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", action="append", help="install just these profiles")
    ap.add_argument("--dry-run", action="store_true", help="print the commands without running them")
    args = ap.parse_args()
    if not shutil.which("hermes"):
        sys.exit("hermes is not on PATH")
    cfg = hermes_ops.load_cfg()
    for spec_dir in sorted(p for p in PROFILES_DIR.iterdir() if (p / "profile.yaml").exists()):
        if not args.only or spec_dir.name in args.only:
            install_profile(spec_dir, args.dry_run)
    print(f"\nkanban board {cfg['board']}")
    if not args.dry_run:
        hermes_ops.ensure_board(cfg)
    install_kickoff(cfg, args.dry_run)
    print("\nDone. Next: hermes/SETUP.md, part 2 (sign-ins), then `./fm hermes doctor`.")


if __name__ == "__main__":
    main()
