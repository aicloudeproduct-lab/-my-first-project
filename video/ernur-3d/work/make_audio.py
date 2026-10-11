"""Soundtrack for the 3D video: generated dombra-led background music (no third-party audio),
soft transition whooshes, a few accents, and the narration from make_voice.py. The music ducks
under the voice; the mix is normalised to -14 LUFS.

Usage: python3 video/ernur-3d/work/make_audio.py   (after make_voice.py; needs numpy, soundfile, ffmpeg)
"""
import json
import os
import subprocess

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 44100
D = 35.0
BPM = 112
BEAT = 60 / BPM
# Transition windows — must match TR in index.html
TR = {"through": (3.6, 4.0), "cube": (7.6, 8.35), "flip": (13.6, 14.35), "page": (19.75, 20.5),
      "parts": (25.3, 27.0), "flare": (30.45, 31.0)}

rng = np.random.default_rng(11)


def tt(d):
    return np.arange(int(d * SR)) / SR


def note(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def lowpass(x, k):
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += k * (v - acc)
        y[i] = acc
    return y


def pluck(m, dur=1.2, bright=0.5, decay=0.996):
    """Karplus–Strong string, computed one delay-line period at a time (vectorised)."""
    f = note(m)
    n = max(2, int(round(SR / f)))
    total = int(dur * SR)
    burst = rng.standard_normal(n)
    burst = lowpass(burst, 0.25 + 0.6 * bright)        # softer pick = darker attack
    out = np.zeros(total + n + 1)
    out[:n] = burst
    i = n
    while i < total:
        seg = out[i - n:i]
        nxt = np.concatenate([seg[1:], seg[-1:]])
        out[i:i + n] = decay * 0.5 * (seg + nxt)
        i += n
    y = out[:total]
    y *= np.minimum(1, (total - np.arange(total)) / (0.05 * SR))
    return y / (np.abs(y).max() + 1e-9)


class Bus:
    def __init__(self):
        self.x = np.zeros((int(D * SR), 2))

    def add(self, at, sig, gain=1.0, pan=0.5):
        i0 = int(round(at * SR))
        if i0 >= len(self.x):
            return
        sig = sig[: len(self.x) - i0] * gain
        self.x[i0:i0 + len(sig), 0] += sig * np.sqrt(1 - pan)
        self.x[i0:i0 + len(sig), 1] += sig * np.sqrt(pan)


def pad(ms, d):
    t = tt(d)
    e = np.minimum(1, t / 0.8) * np.minimum(1, (d - t) / 0.8)
    return sum(np.sin(2 * np.pi * note(m) * t) + 0.35 * np.sin(2 * np.pi * note(m) * 1.004 * t + k) for k, m in enumerate(ms)) * e / len(ms)


def kick():
    t = tt(0.35)
    return np.sin(2 * np.pi * np.cumsum(50 + 80 * np.exp(-t * 30)) / SR) * np.exp(-t / 0.12) * np.minimum(1, t / 0.003)


def shaker():
    t = tt(0.07)
    n = rng.standard_normal(len(t))
    return (n - lowpass(n, 0.3)) * np.minimum(1, t / 0.01) * np.exp(-t / 0.025) * 0.5


def whoosh(d, up=True):
    t = tt(d)
    n = rng.standard_normal(len(t))
    k = np.linspace(0.015, 0.14, len(t)) if up else np.linspace(0.14, 0.015, len(t))
    y = np.empty_like(n)
    acc = 0.0
    for i, v in enumerate(n):
        acc += k[i] * (v - acc)
        y[i] = acc
    return y * np.sin(np.pi * t / d) ** 2 * 3.0


def shimmer(d):
    t = tt(d)
    s = sum(np.sin(2 * np.pi * note(m) * t + k) for k, m in enumerate([86, 90, 93, 98]))
    return s * np.minimum(1, t / 0.05) * np.exp(-t / (d / 3)) / 4


def thud():
    t = tt(0.5)
    return np.sin(2 * np.pi * np.cumsum(70 + 60 * np.exp(-t * 25)) / SR) * np.exp(-t / 0.15)


def page_flip():
    t = tt(0.35)
    n = rng.standard_normal(len(t))
    return (n - lowpass(n, 0.12)) * np.sin(np.pi * t / 0.35) ** 3 * 0.8


# D major; dombra tuned in fourths (D3–G3). Chords per two bars: D, G, A, D, Bm, G, A, D
CHORDS = [(50, 57), (55, 62), (57, 64), (50, 57), (59, 66), (55, 62), (57, 64), (50, 57)]
# D major pentatonic motif (scale degrees on top string), one per bar
MOTIF = [[74, 76, 78, 81], [78, 76, 74, 71], [76, 78, 81, 83], [81, 78, 76, 74]]


def main():
    music, sfx = Bus(), Bus()
    bar = 4 * BEAT
    music_start = 0.6
    nbars = int((D - music_start) / bar) + 1

    # warm pad under everything
    for b in range(0, nbars, 2):
        root, fifth = CHORDS[(b // 2) % len(CHORDS)]
        music.add(music_start + b * bar, pad([root - 12, fifth - 12, root], 2 * bar + 0.6), 0.05)

    for b in range(nbars):
        t_bar = music_start + b * bar
        root, fifth = CHORDS[(b // 2) % len(CHORDS)]
        intro = t_bar < 4.0
        outro = t_bar >= 31.0
        for beat in range(4):
            tb = t_bar + beat * BEAT
            if tb >= D - 0.5:
                break
            # dombra strum «dum-ta-ta»: a down-stroke on the beat, two light strokes after
            for k, (off, g) in enumerate([(0, 1.0), (BEAT * 0.5, 0.55), (BEAT * 0.75, 0.6)]):
                if intro and k:
                    continue
                if outro and (k or beat):
                    continue
                for s, (m, pan) in enumerate([(root, 0.42), (fifth, 0.58)]):
                    music.add(tb + off + s * 0.009, pluck(m, 1.1 if k == 0 else 0.6, bright=0.45 if k else 0.6), 0.10 * g, pan)
            if not intro and not outro:
                if beat in (0, 2):
                    music.add(tb, kick(), 0.25)
                music.add(tb + BEAT * 0.5, shaker(), 0.06, 0.65)
        # melody on the top string from scene 2, phrased by bar
        if 4.0 <= t_bar < 31.0:
            for i, m in enumerate(MOTIF[b % len(MOTIF)]):
                music.add(t_bar + i * BEAT + 0.012, pluck(m, 0.9, bright=0.7, decay=0.997), 0.085, 0.5 + 0.12 * (i % 2 - 0.5))
    # final ringing chord
    music.add(31.0, pluck(50, 3.5), 0.16, 0.45)
    music.add(31.01, pluck(57, 3.5), 0.14, 0.55)
    music.add(31.02, pluck(62, 3.5), 0.12, 0.5)
    music.add(31.0, pad([38, 45, 50, 54], 4.0), 0.07)

    # soft whoosh at every transition, plus a few accents in key
    for name, (a, b) in TR.items():
        d = min(b - a, 0.9)
        sfx.add(a - 0.05, whoosh(d + 0.1), 0.11)
    sfx.add(TR["through"][1] - 0.02, shimmer(1.2), 0.05)
    sfx.add(TR["page"][0] + 0.1, page_flip(), 0.06)
    voice = json.load(open(os.path.join(HERE, "voice.json"), encoding="utf-8"))
    tp = voice[2]["words"][2]["t"] - 0.1
    sfx.add(tp + 0.45, thud(), 0.12)                         # pin lands on Karaganda
    sfx.add(voice[5]["words"][0]["t"] - 0.08, pluck(81, 0.6, bright=0.8), 0.08)  # «Күйеу бала» pops
    sfx.add(voice[5]["words"][0]["t"] + 0.07, pluck(86, 0.5, bright=0.8), 0.06)
    sfx.add(TR["parts"][0] + 0.75, shimmer(1.6), 0.05)       # particles gather into the network
    sfx.add(TR["flare"][1] - 0.05, shimmer(2.0), 0.07)       # light flare

    # fades
    t = np.arange(len(music.x)) / SR
    music.x *= (np.minimum(1, t / 1.0) * np.minimum(1, np.maximum(0, D - t) / 2.5))[:, None]

    wd = os.path.join(HERE, "audio")
    os.makedirs(wd, exist_ok=True)
    sf.write(os.path.join(wd, "music.wav"), music.x, SR)
    sf.write(os.path.join(wd, "sfx.wav"), sfx.x, SR)

    # narration track: each line at its start, upsampled, warm EQ (as in video/audio/make_audio.py)
    inputs, parts = [], []
    for i, line in enumerate(voice):
        inputs += ["-i", os.path.join(HERE, line["file"])]
        ms = int(line["start"] * 1000)
        parts.append(f"[{i}:a]aresample={SR}:resampler=soxr,highpass=f=70,equalizer=f=180:t=q:w=1:g=2.5,"
                     f"equalizer=f=3200:t=q:w=1.5:g=1.5,highshelf=f=7000:g=-3,"
                     f"acompressor=threshold=0.1:ratio=2.5:attack=10:release=150:makeup=1.5,"
                     f"aecho=0.85:0.6:30|55:0.10|0.06,adelay={ms}|{ms},pan=stereo|c0=c0|c1=c0[v{i}]")
    parts.append("".join(f"[v{i}]" for i in range(len(voice))) + f"amix=inputs={len(voice)}:normalize=0,apad=whole_dur={D},volume=2.2[vo]")
    graph = ";".join(parts)
    vpath = os.path.join(wd, "voice.wav")
    subprocess.run(["ffmpeg", "-y", *inputs, "-filter_complex", graph, "-map", "[vo]", "-ar", str(SR), "-t", str(D), vpath],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # mix: music ducks under the voice; sfx sit in the same small room as the music
    mix = os.path.join(wd, "mix.wav")
    graph = ("[2:a]asplit=2[v][vs];"
             "[0:a][vs]sidechaincompress=threshold=0.02:ratio=7:attack=25:release=450[duck];"
             "[1:a]aecho=0.8:0.5:60|110:0.15|0.08[fx];"
             f"[duck][fx][v]amix=inputs=3:normalize=0,atrim=0:{D}[out]")
    subprocess.run(["ffmpeg", "-y", "-i", os.path.join(wd, "music.wav"), "-i", os.path.join(wd, "sfx.wav"), "-i", vpath,
                    "-filter_complex", graph, "-map", "[out]", "-ar", str(SR), mix],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    out = os.path.join(HERE, "soundtrack.wav")
    subprocess.run(["ffmpeg", "-y", "-i", mix, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", str(SR), out],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("saved", out)


if __name__ == "__main__":
    main()
