# -my-first-project
## Видео: «Сәлем! Мен Claude-пен жұмыс істеймін»

- `video/salem-claude.html` — HTML-анимация (1080×1920, 10 с). Браузерде ашсаңыз, цикл бойынша ойнайды.
- `video/salem-claude.mp4` — дайын MP4 (H.264, 30 fps).
- `video/render.mjs` — HTML-ді кадр-кадрмен MP4-ке айналдыратын скрипт (Playwright + ffmpeg): `node video/render.mjs`

## Видео: «Сәлем! Менің есімім Ернұр»

15 секунд, 1080×1920, 30 fps, қазақша дауыс пен фондық музыкасы бар. Үш бөлік, араларында өтпелі эффект.

- `video/ernur.html` — HTML-анимация («▶ Дыбыспен ойнату» батырмасын бассаңыз, дыбыспен синхронды ойнайды).
- `video/ernur.mp4` — дайын видео (H.264 + AAC).
- `video/audio/make_audio.py` — дыбыс жолын жасайды: Piper TTS `kk_KZ-issai-high` нейрондық қазақ дауысы
  (sherpa-onnx арқылы, ер дауысы Iseke, ~12% баяуланған) + тыныш фондық музыка → `video/audio/soundtrack.wav`.
  Әр сөздің айтылу уақытын өлшеп, `video/audio/timings.js` файлына жазады — анимация сол бойынша жүреді.
- Қайта жасау:
  `pip install sherpa-onnx soundfile numpy && python3 video/audio/make_audio.py && node video/render.mjs ernur.html audio/soundtrack.wav`
  (модель ~130 МБ, алғашқы іске қосуда GitHub Releases-тен `video/audio/models/` ішіне жүктеледі).

Дауыс моделі: [Piper kk_KZ-issai-high](https://github.com/k2-fsa/sherpa-onnx/releases/tag/tts-models),
ISSAI KazakhTTS деректерімен үйретілген, лицензиясы CC-BY-4.0.
