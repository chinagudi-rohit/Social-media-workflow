#!/usr/bin/env python3
"""Assemble a finished 9:16 faceless video in the Higgsfield sandbox.

Runs standalone (stdlib + ffmpeg + faster-whisper, all preinstalled there):

    python3 assemble.py plan.json

plan.json (written by `python -m pipeline render-plan`):
{
  "output": "final.mp4",
  "width": 1080, "height": 1920, "fps": 30,
  "min_duration": 0,             # optional floor on the length (the end is held)
  "end_hold": 1.2,               # seconds held after the last word
  "voice_url": "https://...",
  "blocks": [{"text": "...", "image_url": "https://...", "motion_url": "https://..." | null,
              "shots": [{"words": 7, "image_url": "...", "motion_url": "..." | null,
                         "overlay": "4 = VISA" | null,
                         "counter": {"to": 480000, "from": 0, "prefix": "$", "suffix": "",
                                     "decimals": 0} | null,
                         "clip_start": 2.5, "clip_len": 3.0}, ...]}],   # shots optional; clip_* below
             # a public-domain footage block instead: {"text", "motion_url": <footage>,
             #   "footage": true, "clip_start": 12.0, "clip_fit": "blur" | "crop"}
  "captions": {"font": "Montserrat ExtraBold", "size": 96, "max_words": 3, "margin_v": 560,
               "highlight": "&H003DB8F5"},   # numbers and amounts in this colour (ASS BGR)
  "hook_title": "The *math* nobody explains", # big title over the opening; *word* in gold
  "hook_seconds": 2.6,
  "shot_seconds": 3.5,           # a still longer than this is split into two shots (a cut)
  "audio": {"music_db": -27, "sfx_db": -19, "native_db": -25, "seed": 7,  # optional bed
            "music_url": "https://.../bed.mp3", "whoosh_url": "...", "hit_url": "..."},  # optional
  "effectcraft": {"url": "https://.../effectcraft-<v>-linux-x86_64.tar.gz", "sha256": "..."}  # optional
}

Each block's on-screen window comes from where its words fall in the voiceover
(faster-whisper word timestamps). A block with `shots` is split the same way: every shot
covers its own words and plays its own animated clip (slowed by up to half when the words
run longer), with an optional label (`overlay`) popped over it, so a new picture arrives
every two to four seconds. A block without shots opens on its motion clip and continues on
its keyframe with a slow camera move; long stills are cut into two shots (the second a
closer punch-in). Captions are
burned from the transcribed words, numbers highlighted, with a big hook title over the
opening (the script's on_screen_hook). Under the voice sits a bed made here from nothing but code (so nothing can be
claimed): a quiet synthesized music loop, a whoosh on every cut, a low hit on the first
frame, and the motion clips' own ambient sound. Generated beds and effects (`music_url`,
`whoosh_url`, `hit_url` in "audio") take the place of the synthesized ones when given. Footage blocks (public-domain archive film
used as B-roll) are muted, cut into shots from different points of the film, and wide
footage sits over a blurred fill instead of being cropped. Shots that share one multi-shot
clip (the H3 tier: one clip per block, its shots as hard cuts) carry `clip_start` and
`clip_len`, their planned stretch of it; each stretch is moved onto the nearest cut the clip
really has (ffmpeg's scene score), and a shot with no keyframe takes its stills from its own
stretch. A shot with a `counter` gets a
number that counts up and pops in the caption colour, drawn with EffectCraft (an open-source
After Effects clean room; the pinned release is checked against its sha256) and laid over the
shot after the hook title; if EffectCraft fails the video renders without it. Prints a JSON
report as the last line.
"""

import difflib
import json
import math
import os
import re
import subprocess
import sys
import urllib.request
import zlib

KB_MOVES = ("zoom_in", "pan_right", "zoom_out", "pan_up", "pan_left", "zoom_in_left")
PUNCH_MOVES = ("punch_center", "punch_left", "punch_right")


# ---------- pure helpers (unit-tested locally) ---------------------------------

def word_counts(blocks):
    return [len(b["text"].split()) for b in blocks]


MAX_STRETCH = 1.5   # a shot's clip may play this much slower to cover its words
MAX_SHOT = 4.8      # no picture holds longer: a longer window cuts to a closer angle


def units(blocks):
    """The pieces the picture follows, in order: each block's shots, or the block itself.

    Every unit carries its block index, its share of the narration words (`words`, scaled so
    a block's shots add up to the block's words; even shares when not given) and whether it
    is a shot. Footage blocks stay whole."""
    out = []
    for i, b in enumerate(blocks):
        n = len(b["text"].split())
        shots = [] if b.get("footage") else (b.get("shots") or [])
        if not shots:
            out.append({**b, "block": i, "words": n, "shot": False})
            continue
        given = [s.get("words") for s in shots]
        if not all(isinstance(x, (int, float)) and x > 0 for x in given):
            given = [1] * len(shots)
        scale = n / sum(given)
        out += [{**s, "block": i, "words": x * scale, "shot": True} for s, x in zip(shots, given)]
    return out


def block_windows(counts, word_times, total):
    """Map each block to [start, end) seconds using transcribed word start times.

    counts: script words per block. word_times: start time of each transcribed word.
    The transcript can differ in length from the script ("$9,000" vs "nine thousand"),
    so block boundaries are placed proportionally along the transcribed words.
    """
    n = len(word_times)
    total_words = sum(counts)
    windows, cum = [], 0
    start = 0.0
    for i, c in enumerate(counts):
        cum += c
        if i == len(counts) - 1 or n == 0:
            end = total if i == len(counts) - 1 else total * cum / total_words
        else:
            idx = min(n - 1, round(cum / total_words * n))
            end = word_times[idx]
        end = max(end, start + 0.5)
        windows.append((round(start, 3), round(min(end, total), 3)))
        start = end
    return windows


def align_words(words, script_text):
    """Captions spell words as the script does when the voice was misheard ("weak" for
    "wheat"): where transcript and script differ by the same number of words, the script's
    word replaces the transcript's. Numbers keep the transcript's digits ("1932", "$9,000")."""
    def norm(t):
        return re.sub(r"[^a-z0-9']", "", t.lower())

    script = script_text.split()
    out = list(words)
    matcher = difflib.SequenceMatcher(None, [norm(w[2]) for w in words], [norm(t) for t in script], autojunk=False)
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op != "replace" or i2 - i1 != j2 - j1:
            continue
        for k in range(i2 - i1):
            start, end, heard = out[i1 + k]
            said = script[j1 + k]
            if re.search(r"\d", heard + said) or re.match(r"^[^A-Za-z]", heard):
                continue
            out[i1 + k] = (start, end, said)
    return out


def merge_tokens(words):
    """Rejoin pieces Whisper splits off: "tax" "-free", "$9" ",000", "50" "%", "don" "'t"."""
    out = []
    for start, end, text in words:
        if out and (re.match(r"^(-|%|'|’|[,.]\d)", text) or out[-1][2].endswith(("-", "$"))):
            out[-1] = (out[-1][0], end, out[-1][2] + text)
        else:
            out.append((start, end, text))
    return out


def caption_chunks(words, max_words=3, max_gap=0.6):
    """Group (start, end, text) words into short on-screen phrases."""
    words = merge_tokens(words)
    chunks, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or w[0] - cur[-1][1] > max_gap):
            chunks.append(cur)
            cur = []
        cur.append(w)
        if re.search(r"[.?!,:;]$", w[2]):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    out = []
    for c in chunks:
        text = " ".join(x[2] for x in c).strip()
        text = re.sub(r"[.,;:]+$", "", text)
        out.append((c[0][0], max(c[-1][1], c[0][0] + 0.25), text.upper()))
    # Hold each phrase until the next one starts, so captions never flicker off mid-sentence.
    for i in range(len(out) - 1):
        if out[i + 1][0] - out[i][1] < 0.35:
            out[i] = (out[i][0], out[i + 1][0], out[i][2])
    return out


def proportional_words(blocks, total):
    """Fallback timings when transcription fails: spread script words evenly."""
    tokens = [t for b in blocks for t in b["text"].split()]
    step = total / max(1, len(tokens))
    return [(i * step, (i + 1) * step, t) for i, t in enumerate(tokens)]


NUMBER_RE = re.compile(r"[0-9$%]")


def highlight(text, colour="&H003DB8F5"):
    """Colour every word that carries a number, amount or percent, or is wrapped in *stars*."""
    out = []
    for w in text.split(" "):
        starred = len(w) > 2 and w.startswith("*") and w.rstrip(".,!?:;").endswith("*")
        w = w.replace("*", "")
        out.append(f"{{\\c{colour}&}}{w}{{\\c&H00FFFFFF&}}" if colour and (starred or NUMBER_RE.search(w)) else w)
    return " ".join(out)


def snap_cuts(planned, found, tol=1.0, min_gap=0.5):
    """Each planned cut (seconds into a multi-shot clip) moved to the nearest cut the clip
    really has, within `tol` and keeping cuts in order at least `min_gap` apart; a planned
    cut with no detected cut near it stays where it was."""
    out, used = [], set()
    for p in planned:
        floor = (out[-1] if out else 0.0) + min_gap
        near = [(abs(f - p), f) for f in found if f not in used and abs(f - p) <= tol and f >= floor]
        t = min(near)[1] if near else max(p, floor)
        if near:
            used.add(t)
        out.append(round(t, 3))
    return out


def clip_spans(starts, total, found, tol=1.0):
    """[(start, length)] for the shots of one multi-shot clip, from their planned starts
    (seconds), the clip's length and the cuts detected in it."""
    cuts = snap_cuts(starts[1:], found, tol)
    bounds = [starts[0]] + cuts + [total]
    return [(round(a, 3), round(max(0.3, b - a), 3)) for a, b in zip(bounds, bounds[1:])]


def hook_lines(title, per_line=3):
    """The hook title in lines of up to per_line words, upper-cased."""
    words = title.upper().split()
    return [" ".join(words[i:i + per_line]) for i in range(0, len(words), per_line)]


def plan_shots(windows, motion_seconds, shot_seconds=3.5, min_shot=1.4, footage=(), stretch=(), max_shot=None):
    """Split each unit's window into shots: [(unit, start, dur, kind)].

    kind is "motion" (the unit's clip), "still" (slow move), "punch" (closer second
    angle) or "footage" (a stretch of the unit's archive film). A still longer than
    shot_seconds is cut in two so the picture keeps moving; footage is cut into equal parts
    no longer than shot_seconds. Units in `stretch` (shots) play their clip slower, up to
    MAX_STRETCH, rather than ending on a still; with `max_shot`, a window longer than that
    plays the clip for at most `max_shot` and cuts to a closer angle for the rest (a narrator
    who reads slowly would otherwise hold one picture past five seconds).
    """
    shots = []
    for i, (t0, t1) in enumerate(windows):
        if i in footage:
            n = max(1, math.ceil((t1 - t0) / shot_seconds - 1e-9))
            part = (t1 - t0) / n
            shots += [(i, round(t0 + k * part, 3), round(part, 3), "footage") for k in range(n)]
            continue
        t, end = t0, t1
        clip = motion_seconds[i] or 0.0
        used = end - t if i in stretch and clip and end - t <= clip * MAX_STRETCH else min(end - t, clip)
        if max_shot and clip and used > max_shot and end - t - min_shot >= min_shot:
            used = min(used, max_shot, end - t - min_shot)
        if used > 0.05:
            shots.append((i, round(t, 3), round(used, 3), "motion"))
            t += used
        rest = end - t
        if rest <= 0.05:
            continue
        if rest > shot_seconds and rest / 2 >= min_shot:
            half = rest / 2
            first = "punch" if used > 0.05 else "still"
            shots.append((i, round(t, 3), round(half, 3), first))
            shots.append((i, round(t + half, 3), round(rest - half, 3), "punch" if first == "still" else "still"))
        else:
            shots.append((i, round(t, 3), round(rest, 3), "punch" if used > 0.05 else "still"))
    return shots


def ass_time(t):
    h, rem = divmod(max(t, 0), 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def overlay_events(spans, hook_seconds, min_len=0.6):
    """(start, end, text) labels, starting after the hook title and dropped if too short."""
    out = []
    for start, end, text in spans:
        start = max(start + 0.12, hook_seconds if start < hook_seconds else start)
        if text and end - start >= min_len:
            out.append((round(start, 3), round(end, 3), text))
    return out


def ass_document(chunks, width, height, font, size, margin_v, colour="&H003DB8F5", hook=None, hook_seconds=2.6,
                 overlays=()):
    head = (
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {width}\nPlayResY: {height}\nWrapStyle: 0\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Cap,{font},{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,"
        f"-1,0,0,0,100,100,0,0,1,7,2,2,80,80,{margin_v},1\n"
        f"Style: Hook,{font},{round(size * 1.25)},&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,"
        f"-1,0,0,0,100,100,0,0,1,9,3,8,70,70,300,1\n"
        # Labels: white on a dark box near the top third, numbers in gold.
        f"Style: Label,{font},{round(size * 0.9)},&H00FFFFFF,&H00FFFFFF,&H30101010,&H00000000,"
        f"-1,0,0,0,100,100,0,0,3,18,0,8,90,90,{round(height * 0.2)},1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    pop = r"{\fscx112\fscy112\t(0,90,\fscx100\fscy100)}"
    lines = [
        f"Dialogue: 0,{ass_time(s)},{ass_time(e)},Cap,,0,0,0,,{pop}{highlight(text, colour)}"
        for s, e, text in chunks
    ]
    label_pop = r"{\fad(80,120)\fscx70\fscy70\t(0,140,\fscx104\fscy104)\t(140,220,\fscx100\fscy100)}"
    lines += [f"Dialogue: 2,{ass_time(s)},{ass_time(e)},Label,,0,0,0,,{label_pop}{highlight(text.upper(), colour)}"
              for s, e, text in overlays]
    if hook:
        grow = r"{\fad(0,200)\fscx55\fscy55\t(0,160,\fscx106\fscy106)\t(160,260,\fscx100\fscy100)}"
        lines.insert(0, f"Dialogue: 1,{ass_time(0)},{ass_time(hook_seconds)},Hook,,0,0,0,,{grow}"
                        + "\\N".join(highlight(line, colour) for line in hook_lines(hook)))
    return head + "\n".join(lines) + "\n"


def kenburns(move, frames, width, height, fps):
    """zoompan filter for a slow camera move over a still image."""
    step = 0.10 / max(frames, 1)
    center = "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
    exprs = {
        "zoom_in": f"z='1+{step}*on':{center}",
        "zoom_out": f"z='1.10-{step}*on':{center}",
        "pan_right": f"z=1.10:x='(iw-iw/zoom)*on/{frames}':y='ih/2-(ih/zoom/2)'",
        "pan_left": f"z=1.10:x='(iw-iw/zoom)*(1-on/{frames})':y='ih/2-(ih/zoom/2)'",
        "pan_up": f"z=1.10:x='iw/2-(iw/zoom/2)':y='(ih-ih/zoom)*(1-on/{frames})'",
        "zoom_in_left": f"z='1+{step}*on':x='0':y='ih/2-(ih/zoom/2)'",
        # Second angle on the same frame: start 30% closer, keep drifting in.
        "punch_center": f"z='1.30+{step}*on':{center}",
        "punch_left": f"z='1.30+{step}*on':x='iw/4-(iw/zoom/4)':y='ih/2-(ih/zoom/2)'",
        "punch_right": f"z='1.30+{step}*on':x='3*iw/4-(3*iw/zoom/4)':y='ih/2-(ih/zoom/2)'",
    }
    return f"zoompan={exprs[move]}:d={frames}:s={width}x{height}:fps={fps}"


def final_duration(voice_seconds, end_hold, min_duration):
    return round(max(voice_seconds + end_hold, min_duration), 3)


# ---------- media steps (run in the sandbox) -----------------------------------

def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def fetch(url, path):
    if not (os.path.exists(path) and os.path.getsize(path) > 0):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
            f.write(r.read())
    return path


def probe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    return float(out)


def trim_lead(src, out="work/voice_trim.wav"):
    """Drop the silence before the first word: voice, picture and title all start on frame one."""
    run(["ffmpeg", "-y", "-i", src, "-af", "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.02",
         "-ar", "48000", out])
    return out


def transcribe(path):
    from faster_whisper import WhisperModel

    model = WhisperModel("base.en", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(path, language="en", word_timestamps=True, vad_filter=False)
    words = []
    for seg in segments:
        for w in seg.words or []:
            words.append((float(w.start), float(w.end), w.word.strip()))
    return words


def encode_args(fps):
    # Near-lossless intermediates: the final pass is the only real compression.
    return ["-r", str(fps), "-c:v", "libx264", "-preset", "veryfast", "-crf", "15",
            "-pix_fmt", "yuv420p", "-an"]


# Final encode: Shorts and Reels re-compress whatever they get, so upload generously.
FINAL_VIDEO = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-maxrate", "12M", "-bufsize", "24M",
               "-profile:v", "high", "-pix_fmt", "yuv420p"]


def still_segment(img, out, dur, move, w, h, fps):
    frames = max(1, round(dur * fps))
    vf = (f"scale={int(w * 1.5)}:{int(h * 1.5)}:force_original_aspect_ratio=increase,"
          f"crop={int(w * 1.5)}:{int(h * 1.5)},{kenburns(move, frames, w, h, fps)},setsar=1")
    run(["ffmpeg", "-y", "-loop", "1", "-i", img, "-vf", vf, "-frames:v", str(frames),
         *encode_args(fps), out])


def motion_vf(w, h, fps, slow=1.0):
    """Fill the frame from a 480-768p clip: lanczos upscale, a light sharpen, optional slow-down."""
    speed = f"setpts={slow:.4f}*PTS," if slow > 1.001 else ""
    return (f"{speed}scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h},"
            f"unsharp=5:5:0.45:5:5:0,setsar=1,fps={fps}")


def motion_segment(clip, out, dur, w, h, fps, clip_seconds=None, start=0.0):
    slow = max(1.0, dur / clip_seconds) if clip_seconds else 1.0
    seek = ["-ss", f"{start:.3f}"] if start > 0 else []
    run(["ffmpeg", "-y", *seek, "-i", clip, "-t", f"{dur:.3f}", "-vf", motion_vf(w, h, fps, slow), *encode_args(fps), out])


def scene_cuts(path, threshold=0.3):
    """Seconds where a clip hard-cuts (ffmpeg's scene score), or [] when detection fails."""
    try:
        err = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-an", "-vf",
                              f"select=gt(scene\\,{threshold}),showinfo", "-f", "null", "-"],
                             capture_output=True, text=True, timeout=180).stderr
    except Exception:  # noqa: BLE001 - planned cuts are used instead
        return []
    return [round(float(t), 3) for t in re.findall(r"pts_time:([0-9.]+)", err)]


def frame_of(clip, t, out):
    """One frame of a clip, `t` seconds in (a still for a shot that has no keyframe)."""
    run(["ffmpeg", "-y", "-ss", f"{max(0.0, t):.3f}", "-i", clip, "-frames:v", "1", out])
    return out


def effectcraft(cfg):
    """A verified effectcraft-cli (the pinned EffectCraft release in `cfg`, cached between
    renders), or None when no release is configured. Raises if the download does not match."""
    if not cfg or not cfg.get("url"):
        return None
    import glob
    import hashlib
    cache = os.path.expanduser(os.path.join("~", ".cache", "effectcraft", cfg["sha256"][:16]))
    found = glob.glob(os.path.join(cache, "*", "bin", "effectcraft-cli"))
    if found:
        return found[0]
    os.makedirs(cache, exist_ok=True)
    tgz = fetch(cfg["url"], os.path.join(cache, "release.tar.gz"))
    with open(tgz, "rb") as f:
        if hashlib.sha256(f.read()).hexdigest() != cfg["sha256"]:
            os.remove(tgz)
            raise RuntimeError("EffectCraft release does not match its pinned sha256")
    run(["tar", "xzf", tgz, "-C", cache])
    return glob.glob(os.path.join(cache, "*", "bin", "effectcraft-cli"))[0]


def counter_jsx(spec, dur, w, h, fps, font, rgb, project):
    """An EffectCraft (After Effects-style) script for a number that counts up and pops: from
    `from` to `to` over the first 70% of the shot, then a small bounce as it lands."""
    start, end = 0.1, round(max(0.6, dur * 0.7), 3)
    dec = max(0, min(2, int(spec.get("decimals", 0))))
    expr = (f"var v = linear(time, {start}, {end}, {float(spec.get('from', 0))}, {float(spec['to'])});"
            f"var p = v.toFixed({dec}).split('.');"
            "p[0] = p[0].replace(/\\B(?=(\\d{3})+(?!\\d))/g, ',');"
            f"{json.dumps(str(spec.get('prefix', '')))} + p.join('.') + {json.dumps(str(spec.get('suffix', '')))};")
    # As big as fits: about 0.63 em a character in Montserrat ExtraBold, within 88% of the width.
    text = max((f"{float(spec.get(k, 0)):,.{dec}f}" for k in ("from", "to")), key=len)
    chars = len(str(spec.get("prefix", ""))) + len(text) + len(str(spec.get("suffix", "")))
    size = round(min(w * 0.15, w * 0.88 / (0.63 * chars)))
    return "\n".join([
        f"var comp = app.project.items.addComp('Counter', {w}, {h}, 1, {dur:.3f}, {fps});",
        "var t = comp.layers.addText('0');",
        "var src = t.property('Source Text');",
        "var doc = src.value;",
        f"doc.fontSize = {size}; doc.font = {json.dumps(font)};",
        f"doc.fillColor = [{rgb[0]:.3f}, {rgb[1]:.3f}, {rgb[2]:.3f}];",
        f"doc.applyStroke = true; doc.strokeColor = [0, 0, 0]; doc.strokeWidth = {round(size * 0.09)};",
        "doc.justification = ParagraphJustification.CENTER_JUSTIFY;",
        "src.setValue(doc);",
        f"src.expression = {json.dumps(expr)};",
        f"t.property('Position').setValue([{w / 2:.0f}, {h * 0.26:.0f}]);",
        "var sc = t.property('Scale');",
        "sc.setValueAtTime(0, [0, 0]); sc.setValueAtTime(0.2, [118, 118]); sc.setValueAtTime(0.35, [100, 100]);",
        f"sc.setValueAtTime({end}, [100, 100]); sc.setValueAtTime({end + 0.12:.3f}, [112, 112]);"
        f" sc.setValueAtTime({end + 0.25:.3f}, [100, 100]);",
        f"app.project.save(new File({json.dumps(project)}));",
    ])


def add_counter(cli, part, spec, dur, offset, w, h, fps, font, rgb, k):
    """Overlay an EffectCraft counter on a rendered shot, starting `offset` s in (after the hook
    title). Returns True when the shot now carries it."""
    length = dur - offset
    if length < 1.0:
        return False
    project, jsx = os.path.abspath(f"work/counter{k:03d}.ecproj"), f"work/counter{k:03d}.jsx"
    with open(jsx, "w", encoding="utf-8") as f:
        f.write(counter_jsx(spec, round(length, 3), w, h, fps, font, rgb, project))
    run([cli, "script", jsx, "--empty"])
    mov = os.path.abspath(f"work/counter{k:03d}.mov")
    run([cli, "render", "--project", project, "--comp", "Counter", "--out", mov,
         "--format", "prores", "--prores", "4444", "--channels", "rgba"])
    out = part.replace(".mp4", "_counter.mp4")
    # A soft dark shadow under the number keeps it readable on light pictures.
    run(["ffmpeg", "-y", "-i", part, "-i", mov, "-filter_complex",
         f"[1:v]setpts=PTS+{offset:.3f}/TB,format=rgba,split[c][s];"
         "[s]colorchannelmixer=rr=0:gg=0:bb=0:aa=0.9,boxblur=10:2[sh];"
         "[0:v][sh]overlay=5:8:format=auto:eof_action=pass[b];"
         "[b][c]overlay=0:0:format=auto:eof_action=pass,format=yuv420p",
         *encode_args(fps), out])
    os.replace(out, part)
    return True


def footage_filter(fit, w, h, fps):
    """Archive film into the 9:16 frame: 'crop' fills it; 'blur' keeps most of a wide shot,
    centred over a blurred, darkened copy of itself."""
    if fit == "crop":
        return ["-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,fps={fps}"]
    band = int(w * 0.73) // 2 * 2
    graph = (f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},boxblur=24:2,"
             f"eq=brightness=-0.12,setsar=1[bg];"
             f"[0:v]scale=-2:{band},crop='min(iw,{w})':ih,setsar=1[fg];"
             f"[bg][fg]overlay=(W-w)/2:(H-h)/2,fps={fps}[v]")
    return ["-filter_complex", graph, "-map", "[v]"]


def footage_segment(clip, out, dur, offset, fit, w, h, fps):
    """A muted stretch of footage from `offset` seconds, looped if the film runs out."""
    run(["ffmpeg", "-y", "-stream_loop", "-1", "-ss", f"{offset:.3f}", "-i", clip, "-t", f"{dur:.3f}",
         *footage_filter(fit, w, h, fps), *encode_args(fps), out])


# ---------- the audio bed: synthesized here, so nothing in it can be claimed --------

SR = 48000
KEYS = (0, 2, 3, 5, 7, 8, 10)                    # semitone shifts from A
PROGRESSIONS = ((0, 5, 3, 7), (0, 3, 5, 4), (0, 8, 3, 10), (0, 5, 8, 7))  # i-VI-III-VII etc.


def music_bed(total, seed, np):
    """A quiet lo-fi loop: soft pad, plucked arpeggio, light kick. Varies by seed."""
    rng = np.random.default_rng(seed)
    bpm = float(rng.integers(84, 101))
    beat = 60.0 / bpm
    root = 110.0 * 2 ** (KEYS[seed % len(KEYS)] / 12)
    prog = PROGRESSIONS[seed % len(PROGRESSIONS)]
    n = int(total * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    bar = 4 * beat
    minor = (0, 3, 7)
    for b in range(int(total / bar) + 1):
        b0 = int(b * bar * SR)
        if b0 >= n:
            break
        b1 = min(n, int((b + 1) * bar * SR))
        deg = prog[b % len(prog)]
        tones = [root * 2 ** ((deg + iv) / 12) for iv in minor]
        seg = t[b0:b1] - b * bar
        env = np.minimum(1, seg / 0.6) * np.minimum(1, (bar - seg) / 0.4)
        for f in tones:                                   # pad, a little detuned
            out[b0:b1] += 0.10 * env * (np.sin(2 * np.pi * f * t[b0:b1]) + 0.5 * np.sin(2 * np.pi * f * 1.003 * t[b0:b1]))
        for k in range(8):                                # eighth-note arpeggio
            s0 = b0 + int(k * beat / 2 * SR)
            s1 = min(b1, s0 + int(0.45 * SR))
            if s0 >= b1:
                break
            f = tones[k % 3] * 2
            tt = np.arange(s1 - s0) / SR
            out[s0:s1] += 0.07 * np.exp(-tt * 9) * np.sin(2 * np.pi * f * tt)
        for k in (0, 2):                                  # soft kick on 1 and 3
            s0 = b0 + int(k * beat * SR)
            s1 = min(n, s0 + int(0.25 * SR))
            tt = np.arange(s1 - s0) / SR
            out[s0:s1] += 0.25 * np.exp(-tt * 18) * np.sin(2 * np.pi * (48 + 60 * np.exp(-tt * 30)) * tt)
    # gentle low-pass for warmth (one-pole response, applied in the frequency domain)
    freqs = np.fft.rfftfreq(n, 1 / SR)
    y = np.fft.irfft(np.fft.rfft(out) / np.sqrt(1 + (freqs / 2200) ** 2), n)
    fade = np.minimum(1, t / 0.8) * np.minimum(1, (total - t) / 1.5)
    return y * fade


def whoosh(np, rng, length=0.38):
    n = int(length * SR)
    noise = rng.standard_normal(n)
    noise = np.diff(np.concatenate([[0.0], noise]))       # brighter
    tt = np.arange(n) / n
    return noise * np.sin(np.pi * tt) ** 2 * 0.5


def impact(np, length=0.7):
    tt = np.arange(int(length * SR)) / SR
    return np.exp(-tt * 7) * np.sin(2 * np.pi * (42 + 80 * np.exp(-tt * 25)) * tt)


def read_mono(path, np, seconds, start=0.0):
    """Decode any audio/video file's first audio stream to a float mono array, or None."""
    try:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-i", path, "-t", f"{seconds:.3f}",
                              "-vn", "-ac", "1",
                              "-ar", str(SR), "-f", "s16le", "-"], check=True, capture_output=True).stdout
    except subprocess.CalledProcessError:
        return None
    return np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768 if raw else None


def db(x):
    return 10 ** (x / 20)


def load_sound(url, name, np, seconds, start=0.0):
    """The sound at `url` (from `start` s), decoded to mono, or None when it cannot be fetched
    or is silent."""
    if not url:
        return None
    try:
        path = fetch(url, f"work/{name}{os.path.splitext(url.split('?')[0])[1] or '.mp3'}")
    except OSError:
        return None
    a = read_mono(path, np, seconds, start)
    return a if a is not None and len(a) and np.abs(a).max() > 1e-4 else None


def sample(cfg, key, np, seconds):
    """The generated sound at cfg[key] (a URL), decoded to mono, or None to fall back to synthesis."""
    return load_sound(cfg.get(key), key, np, seconds)


def loop_to(a, n, np, xfade=SR):
    """Repeat a clip to n samples, crossfading each seam so the loop point is not heard."""
    out = a[:n].copy()
    while len(out) < n:
        k = min(xfade, len(a) // 4, len(out))
        ramp = np.linspace(0, 1, k)
        out[-k:] = out[-k:] * (1 - ramp) + a[:k] * ramp
        out = np.concatenate([out, a[k:]])
    return out[:n]


def peak_at(a, np):
    """Sample index where a sound is loudest (10 ms envelope)."""
    return int(np.argmax(np.convolve(np.abs(a), np.ones(480) / 480, "same")))


def audio_bed(total, cuts, motion_audio, cfg, seed, cues=()):
    """music + whooshes on cuts + first-frame impact + shot cues + motion clips' own sound
    -> work/bed.wav

    music_url, whoosh_url and hit_url (generated beds and effects) replace the synthesized
    loop, whoosh and hit; without them, or if one fails to load, the synthesized one plays.
    `cues` are (seconds, {url, start, seconds}): a shot's own sound effect (one slot of a
    sound sheet), its loudest moment on the shot's first frame, playing instead of the
    whoosh on that cut."""
    import numpy as np
    import wave

    n = int(total * SR)
    t = np.arange(n) / SR
    bed = np.zeros(n)
    used = {}
    if cfg.get("music_db") is not None:
        m = sample(cfg, "music_url", np, 600)
        used["music"] = "sample" if m is not None else "synth"
        if m is not None:
            m = loop_to(m, n, np) * np.minimum(1, t / 0.8) * np.minimum(1, (total - t) / 1.5)
        else:
            m = music_bed(total, seed, np)
        bed += m / (np.sqrt(np.mean(m ** 2)) + 1e-9) * db(cfg["music_db"])
    if cfg.get("sfx_db") is not None:
        w = sample(cfg, "whoosh_url", np, 3)
        used["whoosh"] = "sample" if w is not None else "synth"
        lead = peak_at(w, np) if w is not None else int(0.22 * SR)    # loudest point lands on the cut
        if w is None:
            w = whoosh(np, np.random.default_rng(seed + 1))
        w = w / (np.abs(w).max() + 1e-9) * db(cfg["sfx_db"])
        placed = 0
        for at, cue in cues:
            a = load_sound(cue["url"], f"sfx{zlib.crc32(cue['url'].encode()):08x}", np,
                           cue.get("seconds", 2.5), cue.get("start", 0.0))
            if a is None:
                continue
            a = a / (np.abs(a).max() + 1e-9) * db(cfg["sfx_db"] + cfg.get("cue_gain_db", 2))
            s0 = int(at * SR) - min(peak_at(a, np), int(0.15 * SR))
            seg = a[max(0, -s0): max(0, min(len(a), n - s0))]
            s0 = max(0, s0)
            bed[s0:s0 + len(seg)] += seg
            placed += 1
        used["cues"] = placed
        cued = [at for at, _ in cues]
        for c in cuts:
            if any(abs(c - at) < 0.05 for at in cued):
                continue           # the shot's own sound marks this cut
            s0 = int(c * SR) - lead
            seg = w[max(0, -s0): max(0, min(len(w), n - s0))]
            s0 = max(0, s0)
            bed[s0:s0 + len(seg)] += seg
        hit = sample(cfg, "hit_url", np, 3)
        used["hit"] = "sample" if hit is not None else "synth"
        if hit is not None:
            hit = hit[max(0, peak_at(hit, np) - int(0.03 * SR)):]     # the boom on frame one
        else:
            hit = impact(np)
        hit = hit / np.abs(hit).max() * db(cfg["sfx_db"] + 3)
        bed[: len(hit)] += hit[: n]
    audio_bed.used = used
    if cfg.get("native_db") is not None:
        for start, path, dur, *offset in motion_audio:
            a = read_mono(path, np, dur, offset[0] if offset else 0.0)
            if a is None or not len(a) or np.abs(a).max() < 1e-4:
                continue
            a = a / (np.sqrt(np.mean(a ** 2)) + 1e-9) * db(cfg["native_db"])
            s0 = int(start * SR)
            a = a[: max(0, n - s0)]
            bed[s0:s0 + len(a)] += a
    peak = np.abs(bed).max()
    if peak > 0.95:
        bed *= 0.95 / peak
    with wave.open("work/bed.wav", "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes((bed * 32767).astype(np.int16).tobytes())
    return "work/bed.wav"


def main(plan_path):
    plan = json.load(open(plan_path))
    w, h, fps = plan.get("width", 1080), plan.get("height", 1920), plan.get("fps", 30)
    cap = {"font": "Montserrat ExtraBold", "size": 96, "max_words": 3, "margin_v": 560,
           "highlight": "&H003DB8F5", **plan.get("captions", {})}
    os.makedirs("work", exist_ok=True)
    blocks = plan["blocks"]
    parts_of = units(blocks)

    voice = trim_lead(fetch(plan["voice_url"], "work/voice.audio"))
    voice_dur = probe_duration(voice)
    total = final_duration(voice_dur, plan.get("end_hold", 1.2), plan.get("min_duration", 0))

    try:
        words = transcribe(voice)
        transcribed = len(words) >= 0.6 * sum(word_counts(blocks))
        words = align_words(words, " ".join(b["text"] for b in blocks))
    except Exception as e:  # noqa: BLE001 - fall back to even timings, report it
        print(f"transcription failed: {e}", file=sys.stderr)
        words, transcribed = [], False
    if not transcribed:
        words = proportional_words(blocks, voice_dur)
    windows = block_windows([u["words"] for u in parts_of], [x[0] for x in words], total)

    clips, paths = {}, {}
    for i, u in enumerate(parts_of):
        if u.get("motion_url"):
            paths.setdefault(u["motion_url"], f"work/motion{len(paths):02d}.mp4")
            clips[i] = fetch(u["motion_url"], paths[u["motion_url"]])
    footage = {i for i, u in enumerate(parts_of) if u.get("footage") and i in clips}
    clip_seconds = [probe_duration(clips[i]) if i in clips and i not in footage else 0.0
                    for i in range(len(parts_of))]
    # Multi-shot clips: each shot plays its stretch, moved onto the clip's real cuts.
    spans, cuts_found = {}, {}
    groups = {}
    for i, u in enumerate(parts_of):
        if i in clips and i not in footage and u.get("clip_len"):
            groups.setdefault(clips[i], []).append(i)
    for path, members in groups.items():
        members.sort(key=lambda i: float(parts_of[i].get("clip_start", 0)))
        found = scene_cuts(path)
        cuts_found[os.path.basename(path)] = {"planned": len(members) - 1, "found": len(found)}
        for i, span in zip(members, clip_spans([float(parts_of[i].get("clip_start", 0)) for i in members],
                                               clip_seconds[members[0]], found)):
            spans[i] = span
            clip_seconds[i] = span[1]
    shots = plan_shots(windows, clip_seconds, plan.get("shot_seconds", 3.5), footage=footage,
                       stretch={i for i, u in enumerate(parts_of) if u["shot"]},
                       max_shot=plan.get("max_shot", MAX_SHOT))

    parts, motion_audio, n_still, n_punch, seen = [], [], 0, 0, {}
    for k, (i, start, dur, kind) in enumerate(shots):
        out = f"work/shot{k:03d}.mp4"
        if kind == "footage":
            # Each cut jumps further into the film, so consecutive shots differ.
            j = seen[i] = seen.get(i, -1) + 1
            offset = float(parts_of[i].get("clip_start", 0)) + j * (dur + 2.0)
            footage_segment(clips[i], out, dur, offset, parts_of[i].get("clip_fit", "blur"), w, h, fps)
        elif kind == "motion":
            offset = spans[i][0] if i in spans else 0.0
            motion_segment(clips[i], out, dur, w, h, fps, clip_seconds[i], offset)
            motion_audio.append((start, clips[i], dur, offset))
        else:
            if parts_of[i].get("image_url"):
                img = fetch(parts_of[i]["image_url"], f"work/key{i:02d}.img")
            else:   # a multi-shot stretch: its own last moment
                a, length = spans.get(i, (0.0, clip_seconds[i]))
                img = frame_of(clips[i], a + max(0.0, length - 0.2), f"work/key{i:02d}.png")
            if kind == "punch":
                move = PUNCH_MOVES[n_punch % len(PUNCH_MOVES)]
                n_punch += 1
            else:
                move = KB_MOVES[n_still % len(KB_MOVES)]
                n_still += 1
            still_segment(img, out, dur, move, w, h, fps)
        parts.append(out)
    # A counting number (EffectCraft) over the first shot of each unit that asks for one.
    first_shot = {}
    for k, (i, _, _, _) in enumerate(shots):
        first_shot.setdefault(i, k)
    wanted = [k for i, k in sorted(first_shot.items()) if parts_of[i].get("counter")]
    counted, counter_errors = 0, []
    if wanted:
        rgb = tuple(int(cap["highlight"][-2 * (n + 1):][:2], 16) / 255 for n in range(3))   # ASS &HAABBGGRR
        try:
            cli = effectcraft(plan.get("effectcraft"))
        except Exception as e:  # noqa: BLE001 - a counter is decoration; the video renders without it
            cli, counter_errors = None, [f"effectcraft: {e}"]
        for k in wanted if cli else []:
            i, start, dur, _ = shots[k]
            offset = max(0.0, plan.get("hook_seconds", 2.6) - start)
            try:
                counted += add_counter(cli, parts[k], parts_of[i]["counter"], dur, offset, w, h, fps,
                                       cap["font"].replace(" ", "-"), rgb, k)
            except Exception as e:  # noqa: BLE001
                counter_errors.append(f"shot {k}: {e}")
        for e in counter_errors:
            print(f"counter skipped: {e}", file=sys.stderr)
    cuts = [start for _, start, _, _ in shots[1:]]
    first = {}
    for i, start, _, _ in shots:
        first.setdefault(i, start)
    cues = [(first[i], parts_of[i]["sfx"]) for i in sorted(first) if (parts_of[i].get("sfx") or {}).get("url")]

    with open("work/list.txt", "w") as f:
        f.writelines(f"file '{os.path.basename(p)}'\n" for p in parts)
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "work/list.txt", "-c", "copy", "work/video.mp4"])

    chunks = caption_chunks(words, cap["max_words"])
    with open("work/captions.ass", "w", encoding="utf-8") as f:
        labels = overlay_events([(t0, t1, u.get("overlay")) for (t0, t1), u in zip(windows, parts_of)],
                                plan.get("hook_seconds", 2.6))
        f.write(ass_document(chunks, w, h, cap["font"], cap["size"], cap["margin_v"], cap["highlight"],
                             plan.get("hook_title"), plan.get("hook_seconds", 2.6), labels))

    audio = plan.get("audio")
    bed = audio_bed(total, cuts, motion_audio, audio, int(audio.get("seed", 1)), cues) if audio else None
    vchain = f"[0:v]ass=work/captions.ass,tpad=stop_mode=clone:stop_duration=5,trim=0:{total},setpts=PTS-STARTPTS[v]"
    if bed:
        # The bed ducks under the voice, then the mix is levelled for Shorts and Reels.
        achain = (f"[1:a]aresample=48000,apad,atrim=0:{total},asetpts=PTS-STARTPTS,asplit=2[vo][key];"
                  f"[2:a]aresample=48000,atrim=0:{total}[bed];"
                  "[bed][key]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=350[duck];"
                  "[vo][duck]amix=inputs=2:normalize=0:duration=first,"
                  "loudnorm=I=-14:TP=-1.5:LRA=11[a]")
        inputs = ["-i", "work/video.mp4", "-i", voice, "-i", bed]
    else:
        achain = f"[1:a]loudnorm=I=-14:TP=-1.5:LRA=11,apad,atrim=0:{total},asetpts=PTS-STARTPTS[a]"
        inputs = ["-i", "work/video.mp4", "-i", voice]
    run([
        "ffmpeg", "-y", *inputs,
        "-filter_complex", f"{vchain};{achain}",
        "-map", "[v]", "-map", "[a]", "-r", str(fps), *FINAL_VIDEO,
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
        plan.get("output", "final.mp4"),
    ])
    run(["ffmpeg", "-y", "-ss", "1", "-i", plan.get("output", "final.mp4"), "-frames:v", "1", "cover.jpg"])

    report = {
        "output": plan.get("output", "final.mp4"),
        "duration": round(probe_duration(plan.get("output", "final.mp4")), 2),
        "voice_seconds": round(voice_dur, 2),
        "transcribed": transcribed,
        "words": len(words),
        "captions": len(chunks),
        "windows": windows,
        "shots": len(shots),
        "pictures": len(parts_of),   # distinct scenes: shots, or whole blocks
        "motion_shots": sum(1 for x in shots if x[3] == "motion"),
        "labels": len(labels),
        "longest_shot": round(max(d for _, _, d, _ in shots), 2),
        "footage_shots": sum(1 for s in shots if s[3] == "footage"),
        "hook_title": plan.get("hook_title"),
        "audio_bed": bool(bed),
        "audio_sources": getattr(audio_bed, "used", {}) if bed else {},
        "sound_cues": len(cues),
        "counters": counted,
        "counter_errors": counter_errors,
        "multishot_cuts": cuts_found,   # per multi-shot clip: cuts asked for and cuts found
    }
    print(json.dumps(report))


if __name__ == "__main__":
    main(sys.argv[1])
