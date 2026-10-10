# -my-first-project
## Видео: «Сәлем! Мен Claude-пен жұмыс істеймін»

- `video/salem-claude.html` — HTML-анимация (1080×1920, 10 с). Браузерде ашсаңыз, цикл бойынша ойнайды.
- `video/salem-claude.mp4` — дайын MP4 (H.264, 30 fps).
- `video/render.mjs` — HTML-ді кадр-кадрмен MP4-ке айналдыратын скрипт (Playwright + ffmpeg): `node video/render.mjs`

## Видео: «Сәлем! Менің есімім Ернұр»

15 секунд, 1080×1920, 30 fps, қазақша дауыс пен фондық музыкасы бар. Үш бөлік, араларында өтпелі эффект.

- `video/ernur.html` — HTML-анимация («▶ Дыбыспен ойнату» батырмасын бассаңыз, дыбыспен синхронды ойнайды).
- `video/ernur.mp4` — дайын видео (H.264 + AAC).
- `video/audio/make_audio.py` — дыбыс жолын жасайды: espeak-ng (қазақ дауысы) + генерацияланған жеңіл музыка → `video/audio/soundtrack.wav`.
- Қайта жасау: `python3 video/audio/make_audio.py && node video/render.mjs ernur.html audio/soundtrack.wav`
