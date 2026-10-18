"""Turn a script into Higgsfield generation requests, then into an assembler plan.

Flow for one run:
  1. generation_requests() -> runs/<id>/generation.json. The autopilot submits
     "keyframes" with generate_image_batch, then "motion" with generate_video_batch
     (each motion request starts from its block's finished keyframe job), and "voice"
     with generate_audio.
  2. The autopilot writes the finished result URLs to runs/<id>/assets.json:
     {"keyframes": {"1": url, ...}, "motion": {"1": url, ...}, "voice": url,
      "job_ids": [...], "credits_spent": n}
  3. render_plan() -> runs/<id>/render.json, the input for tools/assemble.py.
"""

import zlib

MOTION_PLACEHOLDER = "<keyframe job_id for block {block}>"


def motion_blocks(tier, block_count, override=None):
    """1-based blocks that open on an animated moment; a script's `motion_blocks` overrides the tier."""
    blocks = override if override is not None else tier["motion"]["blocks"]
    return list(range(1, block_count + 1)) if blocks == "all" else [b for b in blocks if b <= block_count]


def pick_voice(voices, run_count):
    """Rotate narrators so consecutive uploads do not share one voice."""
    return voices[run_count % len(voices)]


def generation_requests(script, niche, prod_cfg, voice):
    tier = prod_cfg["tiers"][prod_cfg["tier"]]
    prompts = prod_cfg["prompts"]
    style = script.get("visual_style") or niche["visual_style"]
    blocks = script["blocks"]

    keyframes = [
        {
            "index": i,
            "block": i,
            "params": {
                "model": tier["keyframe"]["model"],
                "prompt": f"{style}. {b['visual']}. {prompts['keyframe_suffix']}",
                **tier["keyframe"]["params"],
            },
        }
        for i, b in enumerate(blocks, 1)
        if not b.get("footage")                 # archive footage needs no generated picture
    ]
    motion = [
        {
            "index": 100 + i,
            "block": i,
            "params": {
                "model": tier["motion"]["model"],
                "prompt": f"{blocks[i - 1]['visual']}. {style}. {prompts['motion_suffix']}"
                          + (f" {prompts['motion_audio_suffix']}" if tier["motion"]["params"].get("generate_audio")
                             and prompts.get("motion_audio_suffix") else ""),
                "medias": [{"role": "start_image", "value": MOTION_PLACEHOLDER.format(block=i)}],
                **tier["motion"]["params"],
            },
        }
        for i in motion_blocks(tier, len(blocks), script.get("motion_blocks"))
        if not blocks[i - 1].get("footage")
    ]
    narration = " ".join(b["narration"] for b in blocks)
    words = len(narration.split())
    voice_req = {
        "params": {
            "model": tier["voice"]["model"],
            "prompt": narration,
            "voice_id": voice["voice_id"],
            "voice_type": voice["voice_type"],
            **tier["voice"]["params"],
        },
        "voice_name": voice["name"],
    }
    estimate = (
        len(keyframes) * tier["keyframe"]["credits"]
        + len(motion) * tier["motion"]["credits"]
        + words / 100 * tier["voice"]["credits_per_100_words"]
    )
    retry = tier["keyframe"].get("retry")
    return {
        "tier": prod_cfg["tier"],
        # A keyframe that fails or garbles is regenerated once with this model instead.
        "keyframe_retry": {"model": retry["model"], **retry["params"]} if retry else None,
        "keyframes": keyframes,
        "motion": motion,
        "voice": voice_req,
        "estimated_credits": round(estimate, 2),
    }


def validate_assets(assets, script, generation):
    errors = []
    keys = assets.get("keyframes", {})
    for i, b in enumerate(script["blocks"], 1):
        if not b.get("footage") and not str(keys.get(str(i), "")).startswith("http"):
            errors.append(f"keyframes.{i} needs a result URL")
    for m in generation["motion"]:
        if not str(assets.get("motion", {}).get(str(m["block"]), "")).startswith("http"):
            errors.append(f"motion.{m['block']} needs a result URL (or drop it from generation.json)")
    if not str(assets.get("voice", "")).startswith("http"):
        errors.append("voice needs a result URL")
    return errors


def render_plan(script, assets, render_cfg):
    motion = assets.get("motion", {})
    audio = render_cfg.get("audio")
    # The music bed varies by video but re-renders of one script sound the same.
    seed = zlib.crc32((script.get("id") or script["topic"]).encode()) % 100000
    return {
        "output": "final.mp4",
        "width": render_cfg["width"],
        "height": render_cfg["height"],
        "fps": render_cfg["fps"],
        "end_hold": render_cfg["end_hold"],
        "captions": render_cfg["captions"],
        "hook_title": script.get("on_screen_hook"),
        "hook_seconds": render_cfg.get("hook_seconds", 2.6),
        "shot_seconds": render_cfg.get("shot_seconds", 3.5),
        "audio": {**audio, "seed": seed} if audio else None,
        "voice_url": assets["voice"],
        "blocks": [block_plan(i, b, assets, motion) for i, b in enumerate(script["blocks"], 1)],
    }


def block_plan(i, block, assets, motion):
    if block.get("footage"):
        f = block["footage"]
        return {"text": block["narration"], "image_url": None, "motion_url": f["url"], "footage": True,
                "clip_start": float(f.get("start", 0)), "clip_fit": f.get("fit", "blur")}
    return {"text": block["narration"], "image_url": assets["keyframes"][str(i)], "motion_url": motion.get(str(i))}
