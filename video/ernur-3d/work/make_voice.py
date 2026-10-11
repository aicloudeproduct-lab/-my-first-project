"""Narration for the 3D video: Piper kk_KZ-issai-high (male speaker Iseke) via sherpa-onnx,
reusing the model, synthesis settings and word-timing (prefix + DTW) code from
video/audio/make_audio.py.

Writes work/voice/line*.wav and work/voice.json (each line's start/end and every word's start,
in video time), which the animation reads for subtitles and the mixer for placement.

Usage: python3 video/ernur-3d/work/make_voice.py
"""
import json
import os
import subprocess
import sys

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "audio")))
import make_audio as M  # noqa: E402

import sherpa_onnx  # noqa: E402

# (video start time, text, length_scale, playful) — verbatim script, one sentence per line.
# The dash sentence is split so «күйеу бала …» can be read lighter, with a smile.
LINES = [
    (0.8, "Ассалаумағалейкум!", 1.05, False),
    (4.4, "Мен Ернұрмын, жасым он сегізде.", 1.05, False),
    (8.4, "Қазіргі таңда Қарағандыдағы Бөкетов университетінің екінші курсында оқимын.", 1.05, False),
    (14.15, "Бос уақытымда кітап оқығанды, домбыра тартқанды және музыка тыңдағанды жақсы көремін.", 1.04, False),
    (20.4, "Айтпақшы, тамақты керемет жасаймын —", 1.05, False),
    (23.0, "күйеу бала керек болса, айтыңдар!", 0.98, True),
    (26.4, "Қазір жасанды интеллектпен жұмыс істеуді үйреніп жүрмін.", 1.05, False),
    (31.4, "Уақыт бөліп көргендеріңізге рахмет!", 1.05, False),
]


def make_tts(length_scale, noise_scale):
    d = M.model_dir()
    return sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(
            vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                model=os.path.join(d, "kk_KZ-issai-high.onnx"),
                tokens=os.path.join(d, "tokens.txt"),
                data_dir=os.path.join(d, "espeak-ng-data"),
                noise_scale=noise_scale, noise_scale_w=0.7, length_scale=length_scale),
            num_threads=4)))


def main():
    out_dir = os.path.join(HERE, "voice")
    os.makedirs(out_dir, exist_ok=True)
    cache = {}
    result = []
    for i, (start, text, ls, playful) in enumerate(LINES):
        key = (ls, playful)
        if key not in cache:
            # a little more variation in the playful line makes it livelier
            cache[key] = make_tts(ls, 0.75 if playful else 0.6)
        tts = cache[key]
        spoken = text.replace("—", "").strip()
        audio = tts.generate(spoken, sid=M.SPEAKER_ID)
        x, sr = np.array(audio.samples), audio.sample_rate
        onsets = M.word_onsets(tts, spoken, x, sr)
        voiced = np.where(M.frame_rms(x, sr) > 0.01)[0]
        path = os.path.join(out_dir, f"line{i + 1}.wav")
        sf.write(path, x, sr)
        if playful:
            # raise the pitch ~1.2 semitones without changing timing: a brighter, smiling read
            tmp = path + ".tmp.wav"
            subprocess.run(["ffmpeg", "-y", "-i", path, "-af", f"asetrate={sr}*1.072,aresample={sr},atempo=1/1.072",
                            tmp], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            os.replace(tmp, path)
        words = [w for w in text.split() if w != "—"]
        result.append({
            "text": text,
            "start": start,
            "end": round(start + (voiced[-1] + 1) * M.FRAME, 2),
            "words": [{"w": w, "t": round(start + t, 2)} for w, t in zip(words, onsets)],
            "file": f"voice/line{i + 1}.wav",
        })
        print(f"{start:6.2f}–{result[-1]['end']:6.2f}  {text}")
    with open(os.path.join(HERE, "voice.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
