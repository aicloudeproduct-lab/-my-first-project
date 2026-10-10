"""Builds the soundtrack for ernur.html: Kazakh voice (espeak-ng) + soft generated music.

Usage: python3 video/audio/make_audio.py   (needs espeak-ng, ffmpeg, numpy)
Output: video/audio/soundtrack.wav (15 s, 44.1 kHz stereo)

Voice start times must match VOICE in ernur.html.
"""
import os
import subprocess
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 44100
DURATION = 15.0

# (start second, text read aloud). Digits are written out so espeak reads them in Kazakh.
VOICE = [
    (0.9, "Сәлем! Менің есімім Ернұр."),
    (5.6, "Мен он сегіз жастамын."),
    (9.8, "Жасанды интеллектпен жұмыс істеуді үйреніп жүрмін."),
]


def run(*cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def write_wav(path, stereo):
    data = (np.clip(stereo, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def note(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def make_music(path):
    """Gentle lo-fi pad + plucked arpeggio + soft bass, 90 bpm."""
    n = int(SR * DURATION)
    t = np.arange(n) / SR
    left = np.zeros(n)
    right = np.zeros(n)
    rng = np.random.default_rng(3)

    chords = [  # Cmaj7, Am7, Fmaj7, G6 (midi)
        [60, 64, 67, 71],
        [57, 60, 64, 67],
        [53, 57, 60, 64],
        [55, 59, 62, 64],
    ]
    chord_len = DURATION / len(chords)

    for ci, chord in enumerate(chords):
        start = ci * chord_len
        i0, i1 = int(start * SR), min(n, int((start + chord_len + 0.8) * SR))
        tt = t[i0:i1] - start
        env = np.minimum(1, tt / 0.9) * np.exp(-np.maximum(0, tt - chord_len) / 0.4)
        # Pad: detuned sines, panned slightly apart
        for k, m in enumerate(chord):
            f = note(m)
            pad = np.sin(2 * np.pi * f * tt) + 0.5 * np.sin(2 * np.pi * f * 1.003 * tt + k)
            pad *= 0.035 * env * (1 + 0.15 * np.sin(2 * np.pi * 0.25 * tt + k))
            left[i0:i1] += pad * (0.6 + 0.1 * k)
            right[i0:i1] += pad * (0.9 - 0.1 * k)
        # Bass on the root
        f = note(chord[0] - 24)
        bass = np.sin(2 * np.pi * f * tt) * 0.09 * env
        left[i0:i1] += bass
        right[i0:i1] += bass

        # Arpeggio: eighth notes at 90 bpm, one octave up
        step = 60 / 90 / 2
        pattern = [0, 1, 2, 3, 2, 1, 2, 3]
        j = 0
        while start + j * step < start + chord_len - 0.05:
            s = start + j * step
            m = chord[pattern[j % len(pattern)]] + 12
            a0, a1 = int(s * SR), min(n, int((s + 1.2) * SR))
            ta = t[a0:a1] - s
            f = note(m)
            vel = 0.05 * (0.8 + 0.4 * rng.random())
            pluck = (np.sin(2 * np.pi * f * ta) + 0.25 * np.sin(4 * np.pi * f * ta)) * np.exp(-ta * 4.5)
            pluck *= np.minimum(1, ta / 0.005) * vel
            pan = 0.5 + 0.35 * np.sin(j * 1.3)
            left[a0:a1] += pluck * (1 - pan)
            right[a0:a1] += pluck * pan
            j += 1

    # Fade in / out
    fade = np.minimum(1, t / 1.5) * np.minimum(1, (DURATION - t) / 1.5)
    write_wav(path, np.stack([left * fade, right * fade], axis=1))


def main():
    tmp = os.path.join(HERE, "_tmp")
    os.makedirs(tmp, exist_ok=True)

    music = os.path.join(tmp, "music.wav")
    make_music(music)

    voices = []
    for i, (_, text) in enumerate(VOICE):
        p = os.path.join(tmp, f"voice{i + 1}.wav")
        # kk = Kazakh; slightly slower speed and short word gaps for clarity
        run("espeak-ng", "-v", "kk+m3", "-s", "135", "-p", "45", "-g", "4", "-w", p, text)
        voices.append(p)

    # Delay each voice line to its start time, add a light room reverb, then
    # duck the music under the voice (sidechain) and mix.
    inputs = ["-i", music]
    for p in voices:
        inputs += ["-i", p]
    parts = []
    for i, (start, _) in enumerate(VOICE):
        ms = int(start * 1000)
        parts.append(
            f"[{i + 1}:a]aresample={SR},highpass=f=90,lowpass=f=7500,"
            f"aecho=0.8:0.5:40|70:0.18|0.10,adelay={ms}|{ms},pan=stereo|c0=c0|c1=c0[v{i}]"
        )
    parts.append(f"{''.join(f'[v{i}]' for i in range(len(VOICE)))}amix=inputs={len(VOICE)}:normalize=0,"
                 f"apad=whole_dur={DURATION},volume=1.6[voice]")
    parts.append("[voice]asplit=2[vmix][vside]")
    parts.append("[0:a]volume=0.3[mus]")
    parts.append("[mus][vside]sidechaincompress=threshold=0.02:ratio=6:attack=40:release=500[ducked]")
    parts.append(f"[vmix][ducked]amix=inputs=2:normalize=0,alimiter=limit=0.9,atrim=0:{DURATION}[out]")

    out = os.path.join(HERE, "soundtrack.wav")
    run("ffmpeg", "-y", *inputs, "-filter_complex", ";".join(parts), "-map", "[out]",
        "-ar", str(SR), "-ac", "2", out)
    print("saved", out)


if __name__ == "__main__":
    main()
