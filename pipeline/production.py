"""Turn a script into Higgsfield generation requests, then into an assembler plan.

Flow for one run:
  1. generation_requests() -> runs/<id>/generation.json. The autopilot submits
     "keyframes" with generate_image_batch, then "motion" with generate_video_batch
     (each motion request starts from its shot's finished keyframe job), and "voice"
     with generate_audio.
  2. The autopilot writes the finished result URLs to runs/<id>/assets.json, keyed by
     shot id ("2.1" = block 2, shot 1; a block without a shot list is just "2"):
     {"keyframes": {"1.1": url, ...}, "motion": {"1.1": url, ...}, "voice": url,
      "job_ids": [...], "credits_spent": n}
  3. render_plan() -> runs/<id>/render.json, the input for tools/assemble.py.
"""

import zlib

MOTION_PLACEHOLDER = "<keyframe job_id for shot {shot}>"
REF_PLACEHOLDER = "<keyframe job_id for shot {shot}>"   # same job, used as a character reference


def shots_of(block):
    """A block's shots; a block written without a shot list is one shot of its own visual."""
    return block.get("shots") or [{"visual": block["visual"]}]


def shot_ids(i, block):
    """Asset keys for block i's shots: "i.k" for a shot list, "i" for a whole block."""
    return [f"{i}.{k}" for k in range(1, len(block["shots"]) + 1)] if block.get("shots") else [str(i)]


def motion_blocks(tier, block_count, override=None):
    """1-based blocks that open on an animated moment; a script's `motion_blocks` overrides the tier."""
    blocks = override if override is not None else tier["motion"]["blocks"]
    return list(range(1, block_count + 1)) if blocks == "all" else [b for b in blocks if b <= block_count]


def cast_line(script, shot):
    """The fixed description of every recurring character in the shot (the script's `cast`),
    repeated word for word in each prompt so faces and outfits do not drift."""
    cast = script.get("cast") or {}
    people = [f"{name}: {cast[name]}" for name in shot.get("cast") or [] if name in cast]
    return f" Characters: {'; '.join(people)}." if people else ""


def motion_text(shot, prompts, model):
    """What the clip does. `beats` spell it out second by second over the part of the clip
    the edit keeps (`prompts.beat_window` s); otherwise the shot's `action`. A named
    `camera` move is added in words and, for models that take them, as a bracket command."""
    beats = shot.get("beats")
    if beats:
        step = prompts.get("beat_window", 4.5) / len(beats)
        text = " ".join(f"{k * step:g}-{(k + 1) * step:g} s: {b.rstrip('. ')}." for k, b in enumerate(beats))
    else:
        text = (shot.get("action") or shot["visual"]).rstrip(". ") + "."
    move = (prompts.get("camera_moves") or {}).get(shot.get("camera"))
    if move:
        text += f" Camera: {move['words']}."
        if model in prompts.get("camera_bracket_models", []):
            text += f" {move['bracket']}"
    return text


def pick_voice(voices, run_count):
    """Rotate narrators so consecutive uploads do not share one voice."""
    return voices[run_count % len(voices)]


def generation_requests(script, niche, prod_cfg, voice):
    tier = prod_cfg["tiers"][prod_cfg["tier"]]
    prompts = prod_cfg["prompts"]
    style = script.get("visual_style") or niche["visual_style"]
    blocks = script["blocks"]
    hook_key = tier["keyframe"].get("hook")      # a better model for the very first frame

    keyframes, motion = [], []
    animated = set(motion_blocks(tier, len(blocks), script.get("motion_blocks")))
    for i, b in enumerate(blocks, 1):
        if b.get("footage"):                     # archive footage needs no generated picture
            continue
        for sid, shot in zip(shot_ids(i, b), shots_of(b)):
            ref = shot.get("ref")
            first = not keyframes
            # A shot that brings back an earlier shot's character is drawn from that frame.
            key = tier["keyframe"]["ref"] if ref else hook_key if hook_key and first else tier["keyframe"]
            item = {
                "index": len(keyframes) + 1,
                "block": i,
                "shot": sid,
                "credits": key["credits"],
                "params": {
                    "model": key["model"],
                    "prompt": (f"Same character and art style as the reference image. " if ref else "")
                              + (f"{shot['framing'].rstrip('. ')}: " if shot.get("framing") else "")
                              + f"{shot['visual'].rstrip('. ')}.{cast_line(script, shot)} {style}. {prompts['keyframe_suffix']}"
                              + (f" {prompts['hook_suffix']}" if first and prompts.get("hook_suffix") else ""),
                    **key["params"],
                },
            }
            if ref:
                item["after"] = ref
                item["params"]["medias"] = [{"role": "image_references", "value": REF_PLACEHOLDER.format(shot=ref)}]
            keyframes.append(item)
            if i not in animated or shot.get("still"):
                continue
            action = motion_text(shot, prompts, tier["motion"]["model"])
            # A suffix about faces and outfits makes Hailuo add people to object shots.
            suffix = prompts["motion_suffix"] if shot.get("cast") else prompts.get("motion_object_suffix", prompts["motion_suffix"])
            motion.append({
                "index": 100 + len(motion) + 1,
                "block": i,
                "shot": sid,
                "params": {
                    "model": tier["motion"]["model"],
                    "prompt": f"{action} {suffix}"
                              + (f" {prompts['motion_hook_suffix']}" if sid == keyframes[0]["shot"] and prompts.get("motion_hook_suffix") else "")
                              + (f" {prompts['motion_audio_suffix']}" if tier["motion"]["params"].get("generate_audio")
                                 and prompts.get("motion_audio_suffix") else ""),
                    "medias": [{"role": "start_image", "value": MOTION_PLACEHOLDER.format(shot=sid)}],
                    **tier["motion"]["params"],
                },
            })
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
        sum(k["credits"] for k in keyframes)
        + len(motion) * tier["motion"]["credits"]
        + words / 100 * tier["voice"]["credits_per_100_words"]
    )
    retry = tier["keyframe"].get("retry")
    motion_retry = tier["motion"].get("retry")
    return {
        "tier": prod_cfg["tier"],
        # A keyframe that fails or garbles is regenerated once with this model instead.
        "keyframe_retry": {"model": retry["model"], **retry["params"]} if retry else None,
        # A motion job that fails is retried once on this model.
        "motion_retry": {"model": motion_retry["model"], **motion_retry["params"]} if motion_retry else None,
        "keyframes": keyframes,
        "motion": motion,
        "voice": voice_req,
        "estimated_credits": round(estimate, 2),
    }


def validate_assets(assets, script, generation):
    errors = []
    keys = assets.get("keyframes", {})
    for i, b in enumerate(script["blocks"], 1):
        if b.get("footage"):
            continue
        for sid in shot_ids(i, b):
            if not str(keys.get(sid, "")).startswith("http"):
                errors.append(f"keyframes.{sid} needs a result URL")
    for m in generation["motion"]:
        sid = m.get("shot", str(m["block"]))
        if not str(assets.get("motion", {}).get(sid, "")).startswith("http"):
            errors.append(f"motion.{sid} needs a result URL (or drop it from generation.json)")
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
        # A looping ending runs straight back into the first line: no pause after the last word.
        "end_hold": 0.3 if script.get("ending") == "loop" else render_cfg["end_hold"],
        "captions": render_cfg["captions"],
        "hook_title": script.get("on_screen_hook"),
        "hook_seconds": render_cfg.get("hook_seconds", 2.6),
        "shot_seconds": render_cfg.get("shot_seconds", 3.5),
        "audio": audio_plan(audio, script.get("niche_id"), seed) if audio else None,
        "voice_url": assets["voice"],
        "effectcraft": render_cfg.get("effectcraft"),
        "blocks": [block_plan(i, b, assets, motion, (audio or {}).get("sfx") or {})
                   for i, b in enumerate(script["blocks"], 1)],
    }


def audio_plan(audio, niche_id, seed):
    """The assembler's audio settings: levels, effects, and one music bed for this video."""
    beds = list((audio.get("music") or {}).values())
    fits = [b for b in beds if niche_id in b.get("niches", ())] or beds
    out = {k: v for k, v in audio.items() if k not in ("music", "sfx")}
    if fits:
        out["music_url"] = fits[seed % len(fits)]["url"]
    return {**out, "seed": seed}


def sound_cue(sheet, name):
    """Where a named effect sits in the sound sheet (config/production.yaml render.audio.sfx):
    {url, start, seconds}, or None."""
    names = (sheet or {}).get("names") or []
    if not name or name not in names:
        return None
    slot = sheet.get("slot_seconds", 2.5)
    return {"url": sheet["url"], "start": names.index(name) * slot, "seconds": slot}


def block_plan(i, block, assets, motion, sfx=None):
    if block.get("footage"):
        f = block["footage"]
        return {"text": block["narration"], "image_url": None, "motion_url": f["url"], "footage": True,
                "clip_start": float(f.get("start", 0)), "clip_fit": f.get("fit", "blur")}
    if block.get("shots"):
        shots = [{"words": shot.get("words"), "image_url": assets["keyframes"][sid], "motion_url": motion.get(sid),
                  "overlay": shot.get("overlay"), "counter": shot.get("counter"),
                  "sfx": sound_cue(sfx, shot.get("sfx"))}
                 for sid, shot in zip(shot_ids(i, block), block["shots"])]
        return {"text": block["narration"], "image_url": shots[0]["image_url"], "motion_url": None, "shots": shots}
    return {"text": block["narration"], "image_url": assets["keyframes"][str(i)], "motion_url": motion.get(str(i))}
