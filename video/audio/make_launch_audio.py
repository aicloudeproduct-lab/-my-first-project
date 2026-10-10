"""Soundtrack + timeline for the launch video (launch.html).

The timeline below is the single source of truth: it is written to
video/audio/launch_timings.js, which launch.html reads, so every sound effect
and music hit lands on the matching animation frame.

Scene 4 plays a real line from the project's own voice pipeline
(make_audio.synthesize — Piper kk_KZ-issai-high) with its measured word timings.

Usage: python3 video/audio/make_launch_audio.py   (needs ffmpeg, numpy, soundfile, sherpa-onnx)
Output: video/audio/launch_soundtrack.wav, video/audio/launch_timings.js
"""
import json
import os
import subprocess

import numpy as np
import soundfile as sf

from make_audio import SR, frame_rms, synthesize

HERE = os.path.dirname(os.path.abspath(__file__))
BPM = 120
BEAT = 60 / BPM

# Everything is on the 120 bpm grid (0.5 s beats).
TL = {
    "duration": 22.0,
    "scenes": [0.0, 3.0, 8.0, 14.0, 18.5],        # scene start times
    "hook": {"words": [0.3, 0.6, 0.9], "red": 1.5, "last": 2.0, "glitch": 2.6},
    "site": {"cursorIn": 4.6, "hover": 6.0, "click": 6.5, "done": 7.25, "zoom": 7.5},
    "cards": [8.5, 9.5, 10.5, 11.5],
    "focus": {"voice": 14.75},
    "end": {"logo": 18.5, "name": 19.0, "cta": 19.5, "url": 20.0, "fade": 21.4},
}
DEMO_LINE = "Жасанды интеллектпен жұмыс істеуді үйреніп жүрмін."


def env(t, attack, decay):
    return np.minimum(1, t / max(attack, 1e-4)) * np.exp(-t / decay)


def note(m):
    return 440.0 * 2 ** ((m - 69) / 12)


class Mix:
    def __init__(self, dur):
        self.n = int(dur * SR)
        self.l = np.zeros(self.n)
        self.r = np.zeros(self.n)

    def add(self, at, sig, gain=1.0, pan=0.5):
        i0 = int(at * SR)
        if i0 >= self.n:
            return
        sig = sig[: self.n - i0] * gain
        self.l[i0:i0 + len(sig)] += sig * np.sqrt(1 - pan)
        self.r[i0:i0 + len(sig)] += sig * np.sqrt(pan)


rng = np.random.default_rng(5)


def tt(d):
    return np.arange(int(d * SR)) / SR


def kick():
    t = tt(0.45)
    f = 45 + 110 * np.exp(-t * 28)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(t, 0.002, 0.16)


def hat(open_=False):
    t = tt(0.25 if open_ else 0.06)
    x = rng.standard_normal(len(t))
    x = np.diff(np.concatenate([[0], x]))  # crude high-pass
    return x * env(t, 0.001, 0.08 if open_ else 0.018) * 0.5


def clap():
    t = tt(0.25)
    x = rng.standard_normal(len(t))
    e = sum(env(np.maximum(0, t - d), 0.001, 0.012) * (t >= d) for d in (0, 0.011, 0.022)) + env(t, 0.003, 0.09)
    return np.convolve(x, np.ones(6) / 6, "same") * e * 0.5


def pluck(m, d=0.9):
    t = tt(d)
    f = note(m)
    return (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t) + 0.1 * np.sin(6 * np.pi * f * t)) * env(t, 0.004, 0.25)


def pad(ms, d):
    t = tt(d)
    e = np.minimum(1, t / 0.4) * np.minimum(1, (d - t) / 0.4)
    return sum(np.sin(2 * np.pi * note(m) * t) + 0.5 * np.sin(2 * np.pi * note(m) * 1.004 * t + 1) for m in ms) * e / len(ms)


def bass(m, d):
    t = tt(d)
    f = note(m)
    s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t)
    return s * np.minimum(1, t / 0.01) * np.exp(-t / 0.6) * np.minimum(1, (d - t) / 0.03)


def whoosh(d=0.6, up=True):
    t = tt(d)
    x = rng.standard_normal(len(t))
    # sweep a simple one-pole low-pass
    cut = np.linspace(0.02, 0.35, len(t)) if up else np.linspace(0.35, 0.02, len(t))
    y = np.zeros_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += cut[i] * (x[i] - acc)
        y[i] = acc
    shape = np.sin(np.pi * t / d) ** 2
    return y * shape * 1.6


def riser(d):
    t = tt(d)
    x = rng.standard_normal(len(t))
    y = np.convolve(x, np.ones(4) / 4, "same")
    tone = np.sin(2 * np.pi * np.cumsum(200 + 900 * (t / d) ** 2) / SR) * 0.25
    return (y * 0.6 + tone) * (t / d) ** 2


def impact():
    t = tt(1.6)
    boom = np.sin(2 * np.pi * np.cumsum(38 + 70 * np.exp(-t * 9)) / SR) * env(t, 0.003, 0.5)
    noise = rng.standard_normal(len(t)) * env(t, 0.001, 0.12) * 0.4
    return boom + noise


def neon_buzz(d, flicker):
    """Mains hum gated by the same flicker pattern the red word uses on screen."""
    t = tt(d)
    hum = sum(np.sin(2 * np.pi * 100 * k * t) / k for k in (1, 2, 3, 5))
    gate = np.interp(t, *flicker)
    return hum * gate * np.exp(-t / 1.2) * 0.12


def click():
    t = tt(0.05)
    return (np.sin(2 * np.pi * 2500 * t) * 0.6 + rng.standard_normal(len(t)) * 0.4) * env(t, 0.0005, 0.008)


def chime(ms):
    t = tt(1.4)
    return sum(np.sin(2 * np.pi * note(m) * t) * env(t, 0.003, 0.45) for m in ms) / len(ms)


def tick():
    t = tt(0.03)
    return np.sin(2 * np.pi * 1800 * t) * env(t, 0.0005, 0.006)


# Flicker of the red word: (times relative to TL.hook.red, brightness). Shared with launch.html.
FLICKER = [[0, 0.04, 0.08, 0.13, 0.18, 0.24, 0.3, 0.42, 3.0], [1, 0.15, 1, 0.3, 1, 0.5, 1, 1, 1]]


def main():
    tmp = os.path.join(HERE, "_tmp")
    os.makedirs(tmp, exist_ok=True)
    D = TL["duration"]
    S = TL["scenes"]
    music, sfx = Mix(D), Mix(D)

    # ---- Scene 1: hook on black ----
    music.add(0.0, pad([45, 52], 3.0), 0.12)                         # low drone
    for w in TL["hook"]["words"]:
        sfx.add(w, tick(), 0.35)
    sfx.add(TL["hook"]["red"] - 1.1, riser(1.1), 0.25)
    sfx.add(TL["hook"]["red"], impact(), 0.7)
    sfx.add(TL["hook"]["red"], neon_buzz(1.3, FLICKER), 1.0)
    sfx.add(TL["hook"]["last"], tick(), 0.35)
    sfx.add(S[1] - 0.45, whoosh(0.5), 0.35)

    # ---- Scenes 2–3: the beat (Am – F – C – G, 2 s per chord) ----
    prog = [(57, [57, 60, 64, 67]), (53, [53, 57, 60, 64]), (48, [55, 60, 64, 67]), (55, [55, 59, 62, 67])]
    for b in range(int((S[3] - S[1]) / BEAT)):
        t0 = S[1] + b * BEAT
        music.add(t0, kick(), 0.55)
        if b % 2 == 1:
            music.add(t0, clap(), 0.22)
        music.add(t0 + BEAT / 2, hat(), 0.18, pan=0.65)
        music.add(t0, hat(), 0.08, pan=0.35)
        if b % 4 == 0:
            root, chord = prog[(b // 4) % 4]
            music.add(t0, pad(chord, 4 * BEAT + 0.3), 0.07)
            for k in range(4):
                music.add(t0 + k * BEAT, bass(root - 12, BEAT * 0.9), 0.22)
        if b >= 10:  # arpeggio joins for the features part
            root, chord = prog[(b // 4) % 4]
            music.add(t0, pluck(chord[b % 4] + 12, 0.5), 0.05, pan=0.3 + 0.4 * (b % 2))

    site = TL["site"]
    sfx.add(S[1], whoosh(0.6, up=False), 0.3)
    sfx.add(site["click"], click(), 0.8)
    sfx.add(site["done"], chime([76, 81, 84]), 0.25)
    sfx.add(site["zoom"], whoosh(S[2] - site["zoom"]), 0.45)
    sfx.add(S[2], impact(), 0.35)
    for i, c in enumerate(TL["cards"]):
        sfx.add(c, chime([72 + [0, 2, 4, 7][i], 84 + [0, 2, 4, 7][i]]), 0.22, pan=0.4 + 0.07 * i)
        sfx.add(c - 0.25, whoosh(0.3), 0.15)
    sfx.add(S[3] - 0.5, whoosh(0.55), 0.4)

    # ---- Scene 4: close-up on word sync, with a real voice line ----
    music.add(S[3], pad([57, 60, 64, 67], S[4] - S[3] + 0.3), 0.06)
    for b in range(int((S[4] - S[3]) / BEAT)):
        music.add(S[3] + b * BEAT + BEAT / 2, hat(), 0.08)
    (voice_path,), (onsets,) = synthesize([DEMO_LINE], tmp)
    vx, vsr = sf.read(voice_path)
    rms = frame_rms(vx, vsr)
    voiced = np.where(rms > 0.01)[0]
    v0 = TL["focus"]["voice"]
    words = [{"w": w, "t": round(v0 + t, 2)} for w, t in zip(DEMO_LINE.split(), onsets)]
    for w in words:
        sfx.add(w["t"], tick(), 0.12)
    # Waveform for the screen: 64 RMS bins over the spoken part of the clip
    speech = rms[voiced[0]:voiced[-1] + 1]
    bins = np.array_split(speech, 64)
    wave = np.array([b.mean() for b in bins])
    demo = {
        "text": DEMO_LINE,
        "start": round(v0 + voiced[0] * 0.01, 2),
        "end": round(v0 + (voiced[-1] + 1) * 0.01, 2),
        "words": words,
        "wave": [round(float(x), 3) for x in wave / wave.max()],
    }

    # ---- Scene 5: logo ----
    e = TL["end"]
    sfx.add(S[4] - 0.4, riser(0.4), 0.2)
    sfx.add(e["logo"], impact(), 0.5)
    music.add(e["logo"], pad([48, 55, 60, 64, 67, 71], D - e["logo"]), 0.12)
    music.add(e["logo"], bass(36, 2.5), 0.3)
    for k, key in enumerate(("name", "cta", "url")):
        sfx.add(e[key], chime([79 + 3 * k, 91 + 3 * k]), 0.12)

    # ---- Mix: voice (warm EQ as in make_audio.py) ducks the music; sfx on top ----
    mpath, spath = os.path.join(tmp, "launch_music.wav"), os.path.join(tmp, "launch_sfx.wav")
    for m, path in ((music, mpath), (sfx, spath)):
        sf.write(path, np.stack([m.l, m.r], 1) * 0.9, SR)
    ms = int(v0 * 1000)
    graph = ";".join([
        f"[2:a]aresample={SR}:resampler=soxr,highpass=f=70,equalizer=f=180:t=q:w=1:g=2.5,"
        f"equalizer=f=3200:t=q:w=1.5:g=1.5,highshelf=f=7000:g=-3,"
        f"acompressor=threshold=0.1:ratio=2.5:attack=10:release=150:makeup=1.5,"
        f"aecho=0.85:0.6:30|55:0.10|0.06,adelay={ms}|{ms},pan=stereo|c0=c0|c1=c0,"
        f"apad=whole_dur={D},volume=2.2,asplit=2[v][vside]",
        "[0:a][vside]sidechaincompress=threshold=0.015:ratio=8:attack=30:release=500[mus]",
        f"[mus][1:a][v]amix=inputs=3:normalize=0,alimiter=limit=0.9,atrim=0:{D}[out]",
    ])
    out = os.path.join(HERE, "launch_soundtrack.wav")
    subprocess.run(["ffmpeg", "-y", "-i", mpath, "-i", spath, "-i", voice_path, "-filter_complex", graph,
                    "-map", "[out]", "-ar", str(SR), "-ac", "2", out],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    with open(os.path.join(HERE, "launch_timings.js"), "w", encoding="utf-8") as f:
        f.write("// Generated by make_launch_audio.py: timeline shared by launch.html and its soundtrack.\n")
        f.write("window.LAUNCH = " + json.dumps({**TL, "flicker": FLICKER, "demo": demo}, ensure_ascii=False) + ";\n")
    print("saved", out)


if __name__ == "__main__":
    main()
