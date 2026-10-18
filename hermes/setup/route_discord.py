"""Route a Discord channel (#faceless) to fm-lead through your existing Discord bot.

    hermes/setup/route-discord.sh <channel id> [--no-restart]

1. config/hermes.yaml: notify.chat_id = <channel id> (kickoff and card notifications go there).
2. Default profile (~/.hermes/config.yaml), through `hermes config set`:
   - gateway.multiplex_profiles: true and a gateway.profile_routes entry
     {platform: discord, guild_id, chat_id: <channel id>, profile: fm-lead};
   - discord.free_response_channels gets the channel, so you can talk without @mentions.
3. fm-lead's fm-kickoff cron delivers to discord:<channel id>.
4. Restarts the Hermes gateway (your WhatsApp / Telegram / Discord bots reconnect within
   seconds) unless --no-restart.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from pipeline import hermes_ops  # noqa: E402


def sh(cmd):
    print("  $ " + " ".join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.exit(f"failed: {' '.join(cmd[:4])}\n{res.stderr or res.stdout}")
    return res.stdout


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("channel_id")
    ap.add_argument("--no-restart", action="store_true")
    args = ap.parse_args()
    chat = args.channel_id.strip()
    if not re.fullmatch(r"\d{15,22}", chat):
        sys.exit("channel id must be the numeric Discord channel id (Developer Mode → Copy Channel ID)")
    cfg = hermes_ops.load_cfg()
    lead, guild = cfg["profiles"]["lead"], str(cfg["notify"]["guild_id"])

    cfg_path = REPO / "config" / "hermes.yaml"
    text = cfg_path.read_text(encoding="utf-8")
    text, n = re.subn(r'(\n  chat_id: )"[^"\n]*"', rf'\1"{chat}"', text, count=1)
    if n != 1:
        sys.exit("could not find notify.chat_id in config/hermes.yaml")
    cfg_path.write_text(text, encoding="utf-8")
    print(f"config/hermes.yaml: notify.chat_id = {chat}")

    default = yaml.safe_load((hermes_ops.HERMES_ROOT / "config.yaml").read_text(encoding="utf-8")) or {}
    routes = [r for r in ((default.get("gateway") or {}).get("profile_routes") or [])
              if r.get("name") != "faceless-channel"]
    routes.append({"name": "faceless-channel", "platform": "discord", "guild_id": guild,
                   "chat_id": chat, "profile": lead})
    sh(["hermes", "config", "set", "gateway.multiplex_profiles", "true"])
    sh(["hermes", "config", "set", "gateway.profile_routes", json.dumps(routes)])
    free = (default.get("discord") or {}).get("free_response_channels") or ""
    ids = [c.strip() for c in (free if isinstance(free, list) else str(free).split(",")) if str(c).strip()]
    if chat not in ids:
        ids.append(chat)
    sh(["hermes", "config", "set", "discord.free_response_channels", ",".join(ids)])

    jobs_file = hermes_ops.profile_home(lead) / "cron" / "jobs.json"
    jobs = json.loads(jobs_file.read_text(encoding="utf-8")).get("jobs", []) if jobs_file.exists() else []
    job = next((j for j in jobs if j.get("name") == "fm-kickoff"), None)
    if job:
        sh(["hermes", "-p", lead, "cron", "edit", job["id"], "--deliver", f"discord:{chat}"])
    else:
        print("fm-kickoff cron not found: run hermes/setup/install.sh first")

    if args.no_restart:
        print("Skipped the gateway restart. Run `hermes gateway restart` before the next kickoff.")
    else:
        sh(["hermes", "gateway", "restart"])
    print("Done. Say hi in the channel: fm-lead answers there.")


if __name__ == "__main__":
    main()
