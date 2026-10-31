# SkillSpector scan: ComposioHQ/awesome-claude-skills @ be2a406, video-downloader skill

The repo is a catalog of about 30 skills. The only one about video is `video-downloader`
(SKILL.md plus scripts/download_video.py, about 7 KB). It is a thin wrapper around yt-dlp.

Scan: NVIDIA SkillSpector e717246, `scan --no-llm`, run in the Higgsfield sandbox.
Result: score 22, MEDIUM, CAUTION, with 5 findings.
- LP3: the skill declares no allowed-tools.
- AST4 ×4: list-form subprocess calls to `yt-dlp` and `pip install --break-system-packages
  yt-dlp`. The pip call auto-installs a missing package.

On manual review the skill is safe. It reads no cookies or keys and makes no other network
calls; it downloads to `/mnt/user-data/outputs` unless `-o` is given.

It was not installed. It adds nothing over the vendored `watch` skill, which already wraps
yt-dlp and extracts frames. A test download in the sandbox hit YouTube's "Sign in to confirm
you're not a bot", the same block every yt-dlp tool gets from cloud IPs. It was also blocked
from the owner's Default environment on 2026-10-27.
