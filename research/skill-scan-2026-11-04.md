# Skill safety scan, 2026-11-04

Scanners, run in the Higgsfield sandbox on read-only clones:
- NVIDIA SkillSpector f06ca15, `scan --no-llm`.
- Cloudflare security-audit-skill c1c8a8c in guidance mode (AI-AND-LLM and SUPPLY-CHAIN checks): a manual read
  for network calls, credential reads, hidden Unicode, prompt-injection text and install-time fetches.

| Skill | Commit | SkillSpector | Manual (Cloudflare checklist) | Decision |
|---|---|---|---|---|
| vyralcontent/content-skills viral-youtube-shorts | 349e495 | LOW, SAFE | Markdown only, MIT, no hidden characters, no instructions to fetch or send anything | Installed |
| vyralcontent/content-skills viral-instagram-reels | 349e495 | LOW, SAFE (one AR2 hit) | AR2 hit is policy text ("shadow-capped with no warning"), a false positive | Installed |
| vyralcontent/content-skills viral-hooks | 349e495 | LOW, SAFE | Not needed (covered by the two above) | Not installed |
| AgriciDaniel/claude-youtube | 84c3fa6 | 100/100 CRITICAL, DO NOT INSTALL | Most hits are benign (reads its own YouTube API key or OAuth file under ~/.claude; Google read-only scopes; yt-dlp subprocess; AR2 hits are YouTube policy tables). Real concerns: `curl ... | bash` installer, writes OAuth tokens under ~/.claude, an unresolved "obfuscated instruction text" flag in SKILL.md, and it needs keys we do not hand out | Not installed |

The installed copies sit in `.claude/skills/viral-youtube-shorts` and `.claude/skills/viral-instagram-reels`,
unchanged, with their MIT LICENSE.
