#!/usr/bin/env python3
"""Assemble a finished 9:16 faceless video in the Higgsfield sandbox.

Runs standalone (stdlib + ffmpeg + faster-whisper, all preinstalled there):

    python3 assemble.py plan.json

plan.json (written by `python -m pipeline render-plan`):
{
  "output": "final.mp4",
  "width": 1080, "height": 1920, "fps": 30,
  "min_duration": 62.0,          # TikTok Creator Rewards needs > 60 s
  "end_hold": 1.2,               # seconds held after the last word
  "voice_url": "https://...",
  "blocks": [{"text": "...", "image_url": "https://...", "motion_url": "https://..." | null}],
  "captions": {"font": "Montserrat ExtraBold", "size": 96, "max_words": 3, "margin_v": 560}
}

Each block's on-screen window comes from where its words fall in the voiceover
(faster-whisper word timestamps). A block with a motion clip opens on that clip and
continues on its keyframe with a slow camera move. Captions are burned from the
transcribed words. Prints a JSON report as the last line of output.
"""

import json
import os
import re
import subprocess
import sys
import urllib.request

KB_MOVES = ("zoom_in", "pan_right", "zoom_out", "pan_up", "pan_left", "zoom_in_left")


# ---------- pure helpers (unit-tested locally) ---------------------------------

def word_counts(blocks):
    return [len(b["text"].split()) for b in blocks]


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


def ass_time(t):
    h, rem = divmod(max(t, 0), 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def ass_document(chunks, width, height, font, size, margin_v):
    head = (
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {width}\nPlayResY: {height}\nWrapStyle: 0\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Cap,{font},{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,"
        f"-1,0,0,0,100,100,0,0,1,7,2,2,80,80,{margin_v},1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    pop = r"{\fscx112\fscy112\t(0,90,\fscx100\fscy100)}"
    lines = [
        f"Dialogue: 0,{ass_time(s)},{ass_time(e)},Cap,,0,0,0,,{pop}{text}"
        for s, e, text in chunks
    ]
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
    return ["-r", str(fps), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-an"]


def still_segment(img, out, dur, move, w, h, fps):
    frames = max(1, round(dur * fps))
    vf = (f"scale={int(w * 1.5)}:{int(h * 1.5)}:force_original_aspect_ratio=increase,"
          f"crop={int(w * 1.5)}:{int(h * 1.5)},{kenburns(move, frames, w, h, fps)},setsar=1")
    run(["ffmpeg", "-y", "-loop", "1", "-i", img, "-vf", vf, "-frames:v", str(frames),
         *encode_args(fps), out])


def motion_segment(clip, out, dur, w, h, fps):
    vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,fps={fps}"
    run(["ffmpeg", "-y", "-i", clip, "-t", f"{dur:.3f}", "-vf", vf, *encode_args(fps), out])


def main(plan_path):
    plan = json.load(open(plan_path))
    w, h, fps = plan.get("width", 1080), plan.get("height", 1920), plan.get("fps", 30)
    cap = {"font": "Montserrat ExtraBold", "size": 96, "max_words": 3, "margin_v": 560,
           **plan.get("captions", {})}
    os.makedirs("work", exist_ok=True)
    blocks = plan["blocks"]

    voice = fetch(plan["voice_url"], "work/voice.audio")
    voice_dur = probe_duration(voice)
    total = final_duration(voice_dur, plan.get("end_hold", 1.2), plan.get("min_duration", 62.0))

    try:
        words = transcribe(voice)
        transcribed = len(words) >= 0.6 * sum(word_counts(blocks))
    except Exception as e:  # noqa: BLE001 - fall back to even timings, report it
        print(f"transcription failed: {e}", file=sys.stderr)
        words, transcribed = [], False
    if not transcribed:
        words = proportional_words(blocks, voice_dur)
    windows = block_windows(word_counts(blocks), [x[0] for x in words], total)

    parts = []
    for i, (b, (t0, t1)) in enumerate(zip(blocks, windows)):
        img = fetch(b["image_url"], f"work/key{i:02d}.img")
        dur = t1 - t0
        used = 0.0
        if b.get("motion_url"):
            clip = fetch(b["motion_url"], f"work/motion{i:02d}.mp4")
            used = min(dur, probe_duration(clip))
            out = f"work/seg{i:02d}a.mp4"
            motion_segment(clip, out, used, w, h, fps)
            parts.append(out)
        if dur - used > 0.05:
            out = f"work/seg{i:02d}b.mp4"
            still_segment(img, out, dur - used, KB_MOVES[i % len(KB_MOVES)], w, h, fps)
            parts.append(out)

    with open("work/list.txt", "w") as f:
        f.writelines(f"file '{os.path.basename(p)}'\n" for p in parts)
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "work/list.txt", "-c", "copy", "work/video.mp4"])

    chunks = caption_chunks(words, cap["max_words"])
    with open("work/captions.ass", "w", encoding="utf-8") as f:
        f.write(ass_document(chunks, w, h, cap["font"], cap["size"], cap["margin_v"]))

    run([
        "ffmpeg", "-y", "-i", "work/video.mp4", "-i", voice,
        "-filter_complex",
        f"[0:v]ass=work/captions.ass,tpad=stop_mode=clone:stop_duration=5,trim=0:{total},setpts=PTS-STARTPTS[v];"
        f"[1:a]loudnorm=I=-14:TP=-1.5:LRA=11,apad,atrim=0:{total},asetpts=PTS-STARTPTS[a]",
        "-map", "[v]", "-map", "[a]", "-r", str(fps),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
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
        "segments": len(parts),
    }
    print(json.dumps(report))


if __name__ == "__main__":
    main(sys.argv[1])
