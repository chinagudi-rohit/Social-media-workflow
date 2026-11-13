# SkillSpector scan: Newuxtreme/watch-video-skill @ 1631315

Tool: NVIDIA SkillSpector d7338f5. Run in the Higgsfield sandbox with `scan --no-llm`; the
AI-assisted stage needs a key, so it was not run. Result: score 100, CRITICAL,
DO_NOT_INSTALL, from 18 findings. On manual review, every finding is a false positive:

| Finding | Where | Reality |
|---|---|---|
| CRITICAL, tainted flow from env to urlopen | whisper.py:170 | The Groq/OpenAI key goes only to that provider's own transcription endpoint. That is its job. |
| HIGH ×5, credential access (".env") | setup.py, whisper.py | It reads and scaffolds its own `~/.config` .env for the optional Whisper key. |
| MEDIUM ×5, subprocess | download, frames, whisper, setup | It runs yt-dlp, ffmpeg and brew with list arguments, with no shell. |
| MEDIUM ×2, "sudo" | setup.py:183 | These are printed `apt install` hints. Nothing runs them. |
| MEDIUM ×2, external transmission | whisper.py:28,31 | The Groq/OpenAI endpoint constants. |
| MEDIUM, no allowed-tools; MEDIUM, ~/.config; LOW, "not limited to" | SKILL.md, setup.py, license | Metadata and license wording. |

Verdict: safe. It is an older copy of bradautomates/claude-video, which is already vendored
as `.claude/skills/watch`, plus a slash-only guard. It reads no cookies. It was not
installed because it adds nothing. Its downloader hits the same YouTube bot check in the
sandbox.
