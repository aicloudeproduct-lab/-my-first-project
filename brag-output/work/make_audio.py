"""Soundtrack + shared timeline for the /brag launch video (brag-output/work/brag.html).

The timeline below is the single source of truth: it is written to timeline.js, which the
animation reads, so every hit lands on its frame. From the click (6.0 s) the product's own
soundtrack (video/audio/soundtrack.wav: Ernur's Kazakh voice + music) plays, matching the real
ernur.html animation shown in the phone. Music and effects stay in A minor / C major, the same
key as that soundtrack, and are mixed soft under it.

Usage: python3 brag-output/work/make_audio.py   (needs numpy, soundfile, ffmpeg)
"""
import json
import os
import subprocess

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SR = 44100
BEAT = 0.5  # 120 bpm

TL = {
    "duration": 23.0,
    "scenes": [0.0, 3.0, 7.5, 13.5, 19.5],
    "hook": {"words": [0.25, 0.5, 0.75, 1.0], "red": 1.5, "glitch": 2.75},
    "page": {"cursorIn": 4.6, "hover": 5.8, "click": 6.0},
    "player": {"start": 6.0, "posterAt": 3.2, "length": 13.5},  # ernur.html time = t - start
    "cards": [8.0, 9.0, 10.0, 11.0],
    "end": {"logo": 19.5, "name": 20.0, "cta": 20.5, "url": 21.0, "fade": 22.6},
}
FLICKER = [[0, 0.04, 0.08, 0.13, 0.18, 0.24, 0.3, 0.42, 3.0], [1, 0.15, 1, 0.3, 1, 0.5, 1, 1, 1]]

rng = np.random.default_rng(7)


def tt(d):
    return np.arange(int(d * SR)) / SR


def note(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env(t, a, d):
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d)


def lowpass(x, k):
    """One-pole low-pass; k in (0, 1], smaller = darker."""
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += k * (v - acc)
        y[i] = acc
    return y


class Bus:
    def __init__(self, dur):
        self.l = np.zeros(int(dur * SR))
        self.r = np.zeros(int(dur * SR))

    def add(self, at, sig, gain=1.0, pan=0.5):
        i0 = int(round(at * SR))
        sig = sig[: max(0, len(self.l) - i0)] * gain
        self.l[i0:i0 + len(sig)] += sig * np.sqrt(1 - pan)
        self.r[i0:i0 + len(sig)] += sig * np.sqrt(pan)

    def stereo(self):
        return np.stack([self.l, self.r], 1)


# ---------- instruments (soft, rounded) ----------
def pad(ms, d, attack=0.5, release=0.6):
    t = tt(d)
    e = np.minimum(1, t / attack) * np.minimum(1, np.maximum(0, d - t) / release)
    s = sum(np.sin(2 * np.pi * note(m) * t) + 0.4 * np.sin(2 * np.pi * note(m) * 1.003 * t + k)
            for k, m in enumerate(ms))
    return s * e / len(ms)


def bass(m, d):
    t = tt(d)
    return np.sin(2 * np.pi * note(m) * t) * np.minimum(1, t / 0.01) * np.exp(-t / 0.5) * np.minimum(1, (d - t) / 0.03)


def kick():
    t = tt(0.4)
    f = 48 + 90 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(t, 0.003, 0.14)


def hat():
    t = tt(0.05)
    n = rng.standard_normal(len(t))
    return (n - lowpass(n, 0.25)) * env(t, 0.001, 0.012) * 0.4


def pluck(m, d=1.2):
    t = tt(d)
    f = note(m)
    s = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)
    return s * env(t, 0.004, 0.35)


def tick():
    t = tt(0.04)
    return np.sin(2 * np.pi * note(81) * t) * env(t, 0.001, 0.008)


def soft_click():
    t = tt(0.06)
    body = np.sin(2 * np.pi * 900 * t) * env(t, 0.0005, 0.01)
    n = lowpass(rng.standard_normal(len(t)), 0.3) * env(t, 0.0005, 0.004)
    return body * 0.7 + n * 0.5


def whoosh(d, up=True):
    t = tt(d)
    n = rng.standard_normal(len(t))
    k = np.linspace(0.01, 0.12, len(t)) if up else np.linspace(0.12, 0.01, len(t))
    y = np.empty_like(n)
    acc = 0.0
    for i, v in enumerate(n):
        acc += k[i] * (v - acc)
        y[i] = acc
    return y * np.sin(np.pi * t / d) ** 2 * 2.5


def riser(d):
    t = tt(d)
    tone = np.sin(2 * np.pi * np.cumsum(note(57) * (1 + (t / d) ** 2)) / SR)  # A3 gliding up an octave
    return (lowpass(rng.standard_normal(len(t)), 0.08) * 1.5 + tone * 0.3) * (t / d) ** 2


def hit(root=33):
    t = tt(1.8)
    boom = np.sin(2 * np.pi * np.cumsum(note(root) + 40 * np.exp(-t * 12)) / SR) * env(t, 0.003, 0.6)
    air = lowpass(rng.standard_normal(len(t)), 0.15) * env(t, 0.002, 0.15) * 0.5
    return boom + air


def neon(d):
    """Hum on A (110 Hz harmonics), gated by the same flicker as the red word."""
    t = tt(d)
    hum = sum(np.sin(2 * np.pi * 110 * k * t) / k for k in (1, 2, 3))
    return hum * np.interp(t, *FLICKER) * np.exp(-t / 1.0) * 0.12


def main():
    D = TL["duration"]
    S = TL["scenes"]
    music, sfx = Bus(D), Bus(D)

    # Scene 1 — hook
    music.add(0.0, pad([45, 52, 57], 3.0, attack=0.8, release=0.3), 0.10)
    for w in TL["hook"]["words"]:
        sfx.add(w, tick(), 0.10, pan=0.5)
    sfx.add(TL["hook"]["red"] - 0.9, riser(0.9), 0.12)
    sfx.add(TL["hook"]["red"], hit(33), 0.45)
    sfx.add(TL["hook"]["red"], neon(1.2), 0.9)
    sfx.add(S[1] - 0.4, whoosh(0.45), 0.10)

    # Scene 2 — light beat until the click, Am → F
    click = TL["page"]["click"]
    for b in range(int((click - S[1]) / BEAT)):
        t0 = S[1] + b * BEAT
        music.add(t0, kick(), 0.35)
        music.add(t0 + BEAT / 2, hat(), 0.10, pan=0.6)
        if b % 4 == 0:
            chord = [57, 60, 64] if b < 4 else [53, 57, 60]
            music.add(t0, pad(chord + [chord[0] + 12], 4 * BEAT + 0.2, attack=0.05, release=0.25), 0.06)
            music.add(t0, bass(chord[0] - 24, 4 * BEAT), 0.22)
    sfx.add(S[1], whoosh(0.5, up=False), 0.08)
    sfx.add(click, soft_click(), 0.55)

    # From the click: the product's own soundtrack plays with the real ernur.html animation
    p = TL["player"]
    ern, sr = sf.read(os.path.join(ROOT, "video", "audio", "soundtrack.wav"))
    assert sr == SR
    seg = ern[: int(p["length"] * SR)].copy()
    fade = np.minimum(1, (len(seg) - np.arange(len(seg))) / (0.5 * SR))
    seg *= fade[:, None]
    i0 = int(p["start"] * SR)
    product = np.zeros((int(D * SR), 2))
    product[i0:i0 + len(seg)] = seg

    # Scene 3 — one soft in-key pluck per feature card (A minor pentatonic, rising)
    for i, c in enumerate(TL["cards"]):
        m = [76, 79, 81, 84][i]
        sfx.add(c, pluck(m), 0.10, pan=0.35 + 0.1 * i)
        sfx.add(c + 0.18, pluck(m + 12, 0.6), 0.03, pan=0.65)  # small echo
    sfx.add(S[3] - 0.45, whoosh(0.5), 0.08)

    # Scene 4 — bridge the quiet scene change inside the Ernur video with a soft pad on the
    # chord its music is playing there (Am7 until ernur t = 11.25 s)
    music.add(S[3] - 0.2, pad([57, 60, 64, 67], 3.9, attack=0.8, release=1.2), 0.07)

    # Scene 5 — warm resolve on C major
    e = TL["end"]
    sfx.add(S[4] - 0.35, whoosh(0.4), 0.07)
    sfx.add(e["logo"], hit(36), 0.35)
    music.add(e["logo"], pad([48, 55, 60, 64, 67, 71], D - e["logo"], attack=0.3, release=1.2), 0.11)
    music.add(e["logo"], bass(36, 2.5), 0.25)
    for k, key in enumerate(("name", "cta", "url")):
        sfx.add(e[key], pluck([84, 88, 91][k], 1.4), 0.06, pan=0.4 + 0.1 * k)

    work = os.path.join(HERE, "audio")
    os.makedirs(work, exist_ok=True)
    paths = {}
    for name, x in (("music", music.stereo()), ("sfx", sfx.stereo()), ("product", product)):
        paths[name] = os.path.join(work, f"{name}.wav")
        sf.write(paths[name], x, SR)

    # Mix: a little shared room on music + sfx so effects sit inside the music,
    # gentle glue compression, then normalise to -14 LUFS with a true-peak limit.
    mixed = os.path.join(work, "mix.wav")
    graph = ("[1:a]aecho=0.8:0.5:60|110:0.18|0.10[sfxr];"
             "[0:a][sfxr]amix=inputs=2:normalize=0,aecho=0.8:0.6:80:0.12[bed];"
             "[bed][2:a]amix=inputs=2:normalize=0[pre];"
             "[pre]acompressor=threshold=0.25:ratio=2:attack=20:release=250,"
             f"atrim=0:{D}[out]")
    subprocess.run(["ffmpeg", "-y", "-i", paths["music"], "-i", paths["sfx"], "-i", paths["product"],
                    "-filter_complex", graph, "-map", "[out]", "-ar", str(SR), mixed],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    out = os.path.join(HERE, "soundtrack.wav")
    subprocess.run(["ffmpeg", "-y", "-i", mixed, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", str(SR), out],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    with open(os.path.join(HERE, "timeline.js"), "w", encoding="utf-8") as f:
        f.write("// Generated by make_audio.py — timeline shared by brag.html and its soundtrack.\n")
        f.write("window.BRAG = " + json.dumps({**TL, "flicker": FLICKER}, ensure_ascii=False) + ";\n")
    print("saved", out)


if __name__ == "__main__":
    main()
