"""Validate a video script and build per-platform captions from it.

Script format (runs/<run_id>/script.json) is documented in templates/script_guide.md.
"""

import re

FORMATS = ("narrated", "clip")
# Narration is read at ~150 wpm; each 10s block needs 7.8-9.5s of speech.
BLOCK_WORDS = (19, 24)
HOOK_MAX_WORDS = 15
TAG_RE = re.compile(r"^[A-Za-z0-9_]+$")


def word_count(text):
    return len(text.split())


def validate(script, niches, platforms):
    """Return a list of human-readable problems. Empty list means valid."""
    errors = []
    video = platforms["video"]

    def need(key, kind=str):
        value = script.get(key)
        if not isinstance(value, kind) or not value:
            errors.append(f"'{key}' is required")
            return None
        return value

    niche_id = need("niche_id")
    if niche_id and niche_id not in {n["id"] for n in niches}:
        errors.append(f"niche_id '{niche_id}' is not in config/niches.yaml")
    need("topic")
    fmt = need("format")
    if fmt and fmt not in FORMATS:
        errors.append(f"format must be one of {FORMATS}")

    hook = need("hook")
    if hook and word_count(hook) > HOOK_MAX_WORDS:
        errors.append(f"hook has {word_count(hook)} words; keep it to {HOOK_MAX_WORDS} or fewer")
    need("cta")

    blocks = need("blocks", list) or []
    if fmt == "clip" and len(blocks) != 1:
        errors.append("a clip script has exactly 1 block")
    if fmt == "narrated" and not video["min_blocks"] <= len(blocks) <= video["max_blocks"]:
        errors.append(
            f"a narrated script has {video['min_blocks']}-{video['max_blocks']} blocks "
            f"of {video['block_seconds']}s; got {len(blocks)}"
        )
    for i, block in enumerate(blocks, 1):
        if not isinstance(block, dict) or not block.get("visual"):
            errors.append(f"block {i}: 'visual' is required")
            continue
        if fmt == "narrated":
            words = word_count(block.get("narration", ""))
            lo, hi = BLOCK_WORDS
            if not lo <= words <= hi:
                errors.append(f"block {i}: narration has {words} words; need {lo}-{hi} to fill 10s")

    captions = need("captions", dict) or {}
    for key in ("hook_line", "body"):
        if not captions.get(key):
            errors.append(f"captions.{key} is required")

    title = need("youtube_title")
    if title and len(title) > platforms["youtube"]["title_max"]:
        errors.append(f"youtube_title is {len(title)} chars; max {platforms['youtube']['title_max']}")
    tiktok_max = platforms["tiktok"]["title_max"]
    if len(captions.get("hook_line", "")) > tiktok_max:
        errors.append(f"captions.hook_line is over the TikTok title limit of {tiktok_max} chars")

    for tag in script.get("hashtags", []):
        if not isinstance(tag, str) or not TAG_RE.match(tag):
            errors.append(f"hashtag {tag!r} must be letters/digits/underscore with no '#'")

    if fmt == "narrated":
        sources = script.get("sources") or []
        if not any(isinstance(s, dict) and str(s.get("url", "")).startswith("http") for s in sources):
            errors.append("narrated scripts need at least one source with a URL for their facts")
    return errors


def validate_library(script, niches, platforms, structures):
    """Library scripts must also be long enough to earn on every platform."""
    errors = validate(script, niches, platforms)
    if not script.get("id"):
        errors.append("'id' is required")
    if script.get("structure") not in structures:
        errors.append(f"structure must be one of {structures}")
    if script.get("format") != "narrated":
        errors.append("library scripts are narrated")
    min_blocks = platforms["video"]["monetized_min_blocks"]
    if len(script.get("blocks", [])) < min_blocks:
        errors.append(
            f"needs {min_blocks}+ blocks ({min_blocks * platforms['video']['block_seconds']}s+) "
            "to qualify for TikTok Creator Rewards"
        )
    return errors


def merge_hashtags(topic_tags, niche_tags, limit):
    seen, merged = set(), []
    for tag in list(topic_tags) + list(niche_tags):
        if tag.lower() not in seen:
            seen.add(tag.lower())
            merged.append(tag)
    return merged[:limit]


def _tags(tags):
    return " ".join(f"#{t}" for t in tags)


def _join(*parts):
    return "\n\n".join(p for p in parts if p)


def _clip(text, limit):
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def build_captions(script, niche, platforms):
    caps = script["captions"]
    topic_tags = script.get("hashtags", [])
    disclaimer = niche.get("disclaimer", "")
    tt, ig, yt = platforms["tiktok"], platforms["instagram"], platforms["youtube"]

    tt_tags = merge_hashtags(topic_tags, niche["hashtags"], tt["max_hashtags"])
    ig_tags = merge_hashtags(topic_tags, niche["hashtags"], ig["max_hashtags"])
    yt_tags = merge_hashtags(topic_tags, niche["hashtags"], yt["max_hashtags"])

    yt_title = script["youtube_title"]
    if "#shorts" not in yt_title.lower() and len(yt_title) + len(" #Shorts") <= yt["title_max"]:
        yt_title += " #Shorts"
    sources = "\n".join(f"Source: {s['url']}" for s in script.get("sources", []) if s.get("url"))

    return {
        "tiktok": {
            "title": _clip(caps["hook_line"], tt["title_max"]),
            "description": _clip(
                _join(caps["hook_line"], caps["body"], disclaimer, _tags(tt_tags)), tt["description_max"]
            ),
        },
        "instagram": {
            "caption": _clip(
                _join(caps["hook_line"], caps["body"], script["cta"], disclaimer, _tags(ig_tags)),
                ig["caption_max"],
            ),
        },
        "youtube": {
            "title": yt_title,
            "description": _clip(
                _join(caps["body"], script["cta"], disclaimer, sources, _tags(yt_tags + ["Shorts"])),
                yt["description_max"],
            ),
            "tags": merge_hashtags(topic_tags, niche["hashtags"], 15),
        },
    }
