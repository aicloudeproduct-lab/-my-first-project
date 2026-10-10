"""Builds the soundtrack for ernur.html: Kazakh neural voice + soft generated music.

Voice: Piper TTS "kk_KZ-issai-high" (trained on the ISSAI KazakhTTS corpus, CC-BY-4.0),
run with sherpa-onnx. The model (~130 MB) is downloaded on first run into
video/audio/models/ (git-ignored).

Usage: pip install sherpa-onnx soundfile numpy
       python3 video/audio/make_audio.py          (needs ffmpeg)
Output: video/audio/soundtrack.wav (15 s, 44.1 kHz stereo)
        video/audio/timings.js   (when each spoken word starts; ernur.html reads it,
                                  so the text on screen follows the actual voice)
"""
import json
import os
import subprocess
import tarfile
import urllib.request
import wave

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 44100
DURATION = 15.0

# (start second, text read aloud). Digits are written out so they are read in Kazakh.
# «Сәлем!» and the rest of sentence 1 are separate clips to leave a natural pause.
VOICE = [
    (0.9, "Сәлем!"),
    (1.85, "Менің есімім Ернұр."),
    (5.5, "Мен он сегіз жастамын."),
    (9.7, "Жасанды интеллектпен жұмыс істеуді үйреніп жүрмін."),
]

MODEL_NAME = "vits-piper-kk_KZ-issai-high"
MODEL_URL = f"https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/{MODEL_NAME}.tar.bz2"
SPEAKER_ID = 1         # ISSAI_KazakhTTS_M1_Iseke: male, low and steady voice
LENGTH_SCALE = 1.12    # >1 = slower speech (about 12% slower than default)
MUSIC_GAIN = 0.16      # background music level (voice stays well on top)


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


def model_dir():
    root = os.path.join(HERE, "models")
    d = os.path.join(root, MODEL_NAME)
    if not os.path.exists(os.path.join(d, "kk_KZ-issai-high.onnx")):
        os.makedirs(root, exist_ok=True)
        archive = os.path.join(root, MODEL_NAME + ".tar.bz2")
        print("downloading", MODEL_URL)
        urllib.request.urlretrieve(MODEL_URL, archive)
        with tarfile.open(archive) as tar:
            tar.extractall(root, filter="data")
        os.remove(archive)
    return d


def synthesize(lines, out_dir):
    import sherpa_onnx

    d = model_dir()
    tts = sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(
            vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                model=os.path.join(d, "kk_KZ-issai-high.onnx"),
                tokens=os.path.join(d, "tokens.txt"),
                data_dir=os.path.join(d, "espeak-ng-data"),
                noise_scale=0.6, noise_scale_w=0.7, length_scale=LENGTH_SCALE),
            num_threads=4)))
    paths, word_starts = [], []
    for i, text in enumerate(lines):
        audio = tts.generate(text, sid=SPEAKER_ID)
        x, sr = np.array(audio.samples), audio.sample_rate
        p = os.path.join(out_dir, f"voice{i + 1}.wav")
        sf.write(p, x, sr)
        paths.append(p)
        word_starts.append(word_onsets(tts, text, x, sr))
    return paths, word_starts


# ---------- word timing ----------
# Piper's durations vary a little on every run, so word start times are measured on
# the clip actually generated: each prefix of the sentence ("w1", "w1 w2", ...) is
# synthesized and aligned to the full clip with DTW; where the prefix ends is where
# the next word starts. (Silence gaps can't be used: stop consonants like «кт» also
# make short silences inside words.)

FRAME = 0.01


def frame_rms(x, sr):
    h = int(FRAME * sr)
    return np.array([np.sqrt((x[i:i + h] ** 2).mean()) for i in range(0, len(x) - h, h)])


def log_bands(x, sr):
    n, h = int(0.025 * sr), int(FRAME * sr)
    frames = np.array([x[i:i + n] * np.hanning(n) for i in range(0, len(x) - n, h)])
    spec = np.abs(np.fft.rfft(frames, axis=1)) ** 2
    freqs = np.fft.rfftfreq(n, 1 / sr)
    edges = np.geomspace(60, sr / 2, 41)
    bands = np.stack([spec[:, (freqs >= edges[k]) & (freqs < edges[k + 1])].sum(1) for k in range(40)], 1)
    feats = np.log(bands + 1e-8)
    return feats - feats.mean(0)


def dtw_end(prefix, full):
    """Frame in `full` where `prefix` (aligned from the start) ends."""
    cost = np.linalg.norm(prefix[:, None, :] - full[None, :, :], axis=2)
    m, n = cost.shape
    acc = np.full((m + 1, n + 1), np.inf)
    acc[0, 0] = 0
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            acc[i, j] = cost[i - 1, j - 1] + min(acc[i - 1, j], acc[i, j - 1], acc[i - 1, j - 1])
    return int(np.argmin(acc[m, 1:] / (m + np.arange(1, n + 1))))


def word_onsets(tts, text, x, sr):
    """Start time (s, from clip start) of every word in `text`."""
    words = text.split()
    voiced = np.where(frame_rms(x, sr) > 0.01)[0]
    starts = [voiced[0] * FRAME]
    full = log_bands(x, sr)
    for k in range(1, len(words)):
        px = np.array(tts.generate(" ".join(words[:k]), sid=SPEAKER_ID).samples)
        last = np.where(frame_rms(px, sr) > 0.01)[0][-1]
        end = dtw_end(log_bands(px, sr)[:last + 1], full)
        starts.append(max(starts[-1] + 0.1, (end + 1) * FRAME))
    return [round(t, 2) for t in starts]


def main():
    tmp = os.path.join(HERE, "_tmp")
    os.makedirs(tmp, exist_ok=True)

    music = os.path.join(tmp, "music.wav")
    make_music(music)

    voices, word_starts = synthesize([text for _, text in VOICE], tmp)

    timings = []
    for (start, text), onsets, path in zip(VOICE, word_starts, voices):
        x, sr = sf.read(path)
        voiced = np.where(frame_rms(x, sr) > 0.01)[0]
        timings.append({
            "text": text,
            "start": start,
            "end": round(start + (voiced[-1] + 1) * FRAME, 2),
            "words": [{"w": w, "t": round(start + t, 2)} for w, t in zip(text.split(), onsets)],
        })
    with open(os.path.join(HERE, "timings.js"), "w", encoding="utf-8") as f:
        f.write("// Generated by make_audio.py: when each spoken word starts (seconds).\n")
        f.write("window.VOICE_TIMINGS = " + json.dumps(timings, ensure_ascii=False, indent=2) + ";\n")

    # Each line: upsample, warm EQ (a touch of body, softer highs), gentle
    # compression and a small room, then delay it to its start time.
    # The music is kept quiet and ducked further under the voice.
    inputs = ["-i", music]
    for p in voices:
        inputs += ["-i", p]
    parts = []
    for i, (start, _) in enumerate(VOICE):
        ms = int(start * 1000)
        parts.append(
            f"[{i + 1}:a]aresample={SR}:resampler=soxr,highpass=f=70,"
            f"equalizer=f=180:t=q:w=1:g=2.5,equalizer=f=3200:t=q:w=1.5:g=1.5,"
            f"highshelf=f=7000:g=-3,acompressor=threshold=0.1:ratio=2.5:attack=10:release=150:makeup=1.5,"
            f"aecho=0.85:0.6:30|55:0.10|0.06,adelay={ms}|{ms},pan=stereo|c0=c0|c1=c0[v{i}]"
        )
    parts.append(f"{''.join(f'[v{i}]' for i in range(len(VOICE)))}amix=inputs={len(VOICE)}:normalize=0,"
                 f"apad=whole_dur={DURATION},volume=2.2[voice]")
    parts.append("[voice]asplit=2[vmix][vside]")
    parts.append(f"[0:a]volume={MUSIC_GAIN}[mus]")
    parts.append("[mus][vside]sidechaincompress=threshold=0.015:ratio=8:attack=30:release=600[ducked]")
    parts.append(f"[vmix][ducked]amix=inputs=2:normalize=0,alimiter=limit=0.9,atrim=0:{DURATION}[out]")

    out = os.path.join(HERE, "soundtrack.wav")
    run("ffmpeg", "-y", *inputs, "-filter_complex", ";".join(parts), "-map", "[out]",
        "-ar", str(SR), "-ac", "2", out)
    print("saved", out)


if __name__ == "__main__":
    main()
