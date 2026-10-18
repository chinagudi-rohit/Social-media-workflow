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
  "captions": {"font": "Montserrat ExtraBold", "size": 96, "max_words": 3, "margin_v": 560,
               "highlight": "&H003DB8F5"},   # numbers and amounts in this colour (ASS BGR)
  "hook_title": "The *math* nobody explains", # big title over the opening; *word* in gold
  "hook_seconds": 2.6,
  "shot_seconds": 3.5,           # a still longer than this is split into two shots (a cut)
  "audio": {"music_db": -27, "sfx_db": -19, "native_db": -25, "seed": 7}  # optional bed
}

Each block's on-screen window comes from where its words fall in the voiceover
(faster-whisper word timestamps). A block with a motion clip opens on that clip and
continues on its keyframe with a slow camera move; long stills are cut into two shots
(the second a closer punch-in) so the picture changes every few seconds. Captions are
burned from the transcribed words, numbers highlighted, with a big hook title over the
opening (the script's on_screen_hook). Under the voice sits a bed made here from nothing but code (so nothing can be
claimed): a quiet synthesized music loop, a whoosh on every cut, a low hit on the first
frame, and the motion clips' own ambient sound. Prints a JSON report as the last line.
"""

import json
import os
import re
import subprocess
import sys
import urllib.request

KB_MOVES = ("zoom_in", "pan_right", "zoom_out", "pan_up", "pan_left", "zoom_in_left")
PUNCH_MOVES = ("punch_center", "punch_left", "punch_right")


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


NUMBER_RE = re.compile(r"[0-9$%]")


def highlight(text, colour="&H003DB8F5"):
    """Colour every word that carries a number, amount or percent, or is wrapped in *stars*."""
    out = []
    for w in text.split(" "):
        starred = len(w) > 2 and w.startswith("*") and w.rstrip(".,!?:;").endswith("*")
        w = w.replace("*", "")
        out.append(f"{{\\c{colour}&}}{w}{{\\c&H00FFFFFF&}}" if colour and (starred or NUMBER_RE.search(w)) else w)
    return " ".join(out)


def hook_lines(title, per_line=3):
    """The hook title in lines of up to per_line words, upper-cased."""
    words = title.upper().split()
    return [" ".join(words[i:i + per_line]) for i in range(0, len(words), per_line)]


def plan_shots(windows, motion_seconds, shot_seconds=3.5, min_shot=1.4):
    """Split each block window into shots: [(block, start, dur, kind)].

    kind is "motion" (the block's clip), "still" (slow move) or "punch" (closer second
    angle). A still longer than shot_seconds is cut in two so the picture keeps moving.
    """
    shots = []
    for i, (t0, t1) in enumerate(windows):
        t, end = t0, t1
        used = min(end - t, motion_seconds[i] or 0.0)
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


def ass_document(chunks, width, height, font, size, margin_v, colour="&H003DB8F5", hook=None, hook_seconds=2.6):
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
        f"-1,0,0,0,100,100,0,0,1,9,3,8,70,70,300,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    pop = r"{\fscx112\fscy112\t(0,90,\fscx100\fscy100)}"
    lines = [
        f"Dialogue: 0,{ass_time(s)},{ass_time(e)},Cap,,0,0,0,,{pop}{highlight(text, colour)}"
        for s, e, text in chunks
    ]
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


def read_mono(path, np, seconds):
    """Decode any audio/video file's first audio stream to a float mono array, or None."""
    try:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-t", f"{seconds:.3f}", "-vn", "-ac", "1",
                              "-ar", str(SR), "-f", "s16le", "-"], check=True, capture_output=True).stdout
    except subprocess.CalledProcessError:
        return None
    return np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768 if raw else None


def db(x):
    return 10 ** (x / 20)


def audio_bed(total, cuts, motion_audio, cfg, seed):
    """music + whooshes on cuts + first-frame impact + motion clips' own sound -> work/bed.wav"""
    import numpy as np
    import wave

    n = int(total * SR)
    bed = np.zeros(n)
    if cfg.get("music_db") is not None:
        m = music_bed(total, seed, np)
        bed += m / (np.sqrt(np.mean(m ** 2)) + 1e-9) * db(cfg["music_db"])
    if cfg.get("sfx_db") is not None:
        rng = np.random.default_rng(seed + 1)
        w = whoosh(np, rng)
        w = w / (np.abs(w).max() + 1e-9) * db(cfg["sfx_db"])
        for c in cuts:
            s0 = max(0, int((c - 0.22) * SR))
            seg = w[: max(0, min(len(w), n - s0))]
            bed[s0:s0 + len(seg)] += seg
        hit = impact(np)
        hit = hit / np.abs(hit).max() * db(cfg["sfx_db"] + 3)
        bed[: len(hit)] += hit[: n]
    if cfg.get("native_db") is not None:
        for start, path, dur in motion_audio:
            a = read_mono(path, np, dur)
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

    voice = fetch(plan["voice_url"], "work/voice.audio")
    voice_dur = probe_duration(voice)
    total = final_duration(voice_dur, plan.get("end_hold", 1.2), plan.get("min_duration", 0))

    try:
        words = transcribe(voice)
        transcribed = len(words) >= 0.6 * sum(word_counts(blocks))
    except Exception as e:  # noqa: BLE001 - fall back to even timings, report it
        print(f"transcription failed: {e}", file=sys.stderr)
        words, transcribed = [], False
    if not transcribed:
        words = proportional_words(blocks, voice_dur)
    windows = block_windows(word_counts(blocks), [x[0] for x in words], total)

    clips = {}
    for i, b in enumerate(blocks):
        if b.get("motion_url"):
            clips[i] = fetch(b["motion_url"], f"work/motion{i:02d}.mp4")
    shots = plan_shots(windows, [probe_duration(clips[i]) if i in clips else 0.0 for i in range(len(blocks))],
                       plan.get("shot_seconds", 3.5))

    parts, motion_audio, n_still, n_punch = [], [], 0, 0
    for k, (i, start, dur, kind) in enumerate(shots):
        out = f"work/shot{k:03d}.mp4"
        if kind == "motion":
            motion_segment(clips[i], out, dur, w, h, fps)
            motion_audio.append((start, clips[i], dur))
        else:
            img = fetch(blocks[i]["image_url"], f"work/key{i:02d}.img")
            if kind == "punch":
                move = PUNCH_MOVES[n_punch % len(PUNCH_MOVES)]
                n_punch += 1
            else:
                move = KB_MOVES[n_still % len(KB_MOVES)]
                n_still += 1
            still_segment(img, out, dur, move, w, h, fps)
        parts.append(out)
    cuts = [start for _, start, _, _ in shots[1:]]

    with open("work/list.txt", "w") as f:
        f.writelines(f"file '{os.path.basename(p)}'\n" for p in parts)
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "work/list.txt", "-c", "copy", "work/video.mp4"])

    chunks = caption_chunks(words, cap["max_words"])
    with open("work/captions.ass", "w", encoding="utf-8") as f:
        f.write(ass_document(chunks, w, h, cap["font"], cap["size"], cap["margin_v"], cap["highlight"],
                             plan.get("hook_title"), plan.get("hook_seconds", 2.6)))

    audio = plan.get("audio")
    bed = audio_bed(total, cuts, motion_audio, audio, int(audio.get("seed", 1))) if audio else None
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
        "shots": len(shots),
        "longest_shot": round(max(d for _, _, d, _ in shots), 2),
        "hook_title": plan.get("hook_title"),
        "audio_bed": bool(bed),
    }
    print(json.dumps(report))


if __name__ == "__main__":
    main(sys.argv[1])
