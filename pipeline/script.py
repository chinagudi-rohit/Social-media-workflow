"""Validate a video script and build per-platform captions from it.

Script format (runs/<run_id>/script.json) is documented in templates/script_guide.md.
"""

import re

FORMATS = ("narrated", "clip")
# Narration is read at ~150 wpm; each 10s block needs 7.8-9.5s of speech.
BLOCK_WORDS = (19, 24)
HOOK_MAX_WORDS = 15
ON_SCREEN_HOOK_WORDS = (2, 7)   # big title over the first seconds; *stars* mark the gold word
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
    on_screen = script.get("on_screen_hook")
    if on_screen is not None:
        lo, hi = ON_SCREEN_HOOK_WORDS
        if not isinstance(on_screen, str) or not lo <= word_count(on_screen) <= hi:
            errors.append(f"on_screen_hook needs {lo}-{hi} words")
    for key in ("youtube_title", "on_screen_hook"):
        if re.search(r"\bin \d+ seconds\b", str(script.get(key) or ""), re.I):
            errors.append(f"{key} must not promise a running time; the voiceover sets the length")
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
    hook_max = platforms["captions"]["hook_line_max"]
    if len(captions.get("hook_line", "")) > hook_max:
        errors.append(f"captions.hook_line is {len(captions['hook_line'])} chars; keep it to {hook_max} "
                      "(the first line Reels and Facebook show before 'more')")

    for tag in script.get("hashtags", []):
        if not isinstance(tag, str) or not TAG_RE.match(tag):
            errors.append(f"hashtag {tag!r} must be letters/digits/underscore with no '#'")

    errors += footage_errors(blocks, platforms.get("footage") or {})

    if fmt == "narrated":
        sources = script.get("sources") or []
        if not any(isinstance(s, dict) and str(s.get("url", "")).startswith("http") for s in sources):
            errors.append("narrated scripts need at least one source with a URL for their facts")
    return errors


def footage_errors(blocks, rules):
    """Archive footage blocks: an allowed source and licence, a credit, a direct URL, and no
    more than `max_share` of the video (config/footage.yaml)."""
    used = [(i, b["footage"]) for i, b in enumerate(blocks, 1) if isinstance(b, dict) and b.get("footage")]
    if not used:
        return []
    if not rules:
        return ["footage blocks need config/footage.yaml"]
    errors = []
    for i, f in used:
        if f.get("source") not in rules["sources"]:
            errors.append(f"block {i}: footage source must be one of {', '.join(rules['sources'])}")
        if f.get("license") not in rules["licenses"]:
            errors.append(f"block {i}: footage licence must be one of {', '.join(rules['licenses'])}")
        if not f.get("credit"):
            errors.append(f"block {i}: footage needs a credit line")
        url = str(f.get("url", ""))
        if not url.startswith("http") or re.search(r"youtube\.com|youtu\.be", url):
            errors.append(f"block {i}: footage url must be a direct file from the source (never YouTube)")
    if len(used) > rules["max_share"] * len(blocks):
        errors.append(f"footage fills {len(used)} of {len(blocks)} blocks; at most {rules['max_share']:.0%}")
    return errors


def footage_credits(script):
    seen = []
    for b in script.get("blocks", []):
        credit = (b.get("footage") or {}).get("credit")
        if credit and credit not in seen:
            seen.append(credit)
    return f"Footage: {'; '.join(seen)}." if seen else ""


def validate_library(script, niches, platforms, structures):
    """Library scripts must also be long enough to earn on every platform."""
    errors = validate(script, niches, platforms)
    if not script.get("id"):
        errors.append("'id' is required")
    if script.get("structure") not in structures:
        errors.append(f"structure must be one of {structures}")
    if script.get("format") != "narrated":
        errors.append("library scripts are narrated")
    if not script.get("on_screen_hook"):
        errors.append("'on_screen_hook' is required: the title burned in over the first seconds")
    min_blocks = platforms["video"]["library_min_blocks"]
    if len(script.get("blocks", [])) < min_blocks:
        errors.append(
            f"needs {min_blocks}+ blocks ({min_blocks * platforms['video']['block_seconds']}s+) "
            "(platforms.yaml video.library_min_blocks)"
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


def build_captions(script, niche, platforms, hashtags=None):
    """Per-platform captions. `hashtags` (a list) replaces the topic and niche tags; an empty
    list posts with none (experiment arms)."""
    caps = script["captions"]
    topic_tags = script.get("hashtags", [])
    disclaimer = niche.get("disclaimer", "")
    ig, yt, x = platforms["instagram"], platforms["youtube"], platforms["twitter"]

    if hashtags is not None:
        ig_tags, yt_tags = list(hashtags)[: ig["max_hashtags"]], list(hashtags)[: yt["max_hashtags"]]
    else:
        ig_tags = merge_hashtags(topic_tags, niche["hashtags"], ig["max_hashtags"])
        yt_tags = merge_hashtags(topic_tags, niche["hashtags"], yt["max_hashtags"])
    shorts_tag = yt.get("shorts_tag", True) and hashtags != []

    yt_title = script["youtube_title"]
    if shorts_tag and "#shorts" not in yt_title.lower() and len(yt_title) + len(" #Shorts") <= yt["title_max"]:
        yt_title += " #Shorts"
    sources = "\n".join(f"Source: {s['url']}" for s in script.get("sources", []) if s.get("url"))

    return {
        "instagram": {
            "caption": _clip(
                _join(caps["hook_line"], caps["body"], caps.get("share_line"), script["cta"],
                      ig.get("link_in_bio_cta"), disclaimer, footage_credits(script), _tags(ig_tags)),
                ig["caption_max"],
            ),
        },
        "youtube": {
            "title": yt_title,
            "description": _clip(
                _join(caps["body"], script["cta"], disclaimer, sources, footage_credits(script), yt.get("ai_note"),
                      _tags(yt_tags + (["Shorts"] if shorts_tag else []))),
                yt["description_max"],
            ),
            "tags": merge_hashtags(topic_tags, niche["hashtags"], 15),
        },
        "twitter": {"text": x_post(caps["hook_line"], caps["body"], _tags(merge_hashtags(
            topic_tags, niche["hashtags"], x["max_hashtags"])), x["text_max"])},
    }


def x_post(hook, body, tags, limit, disclosure="Made with AI."):
    """Hook, then the body's first sentence if it fits, then the AI disclosure and tags."""
    first = re.split(r"(?<=[.!?])\s+", body.strip())[0]
    for parts in ((hook, first, disclosure, tags), (hook, disclosure, tags), (hook, disclosure)):
        text = _join(*parts)
        if len(text) <= limit:
            return text
    return _clip(hook, limit - len(disclosure) - 2) + "\n\n" + disclosure
