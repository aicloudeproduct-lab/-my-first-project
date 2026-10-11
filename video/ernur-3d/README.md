# Ернұр — 3D видео (35 с, 1080×1920, 30 fps)

`ernur-3d.mp4` — дайын видео. Жеті 3D сахна (three.js), әр ауысу әртүрлі:
zoom-through → 3D куб → карточка flip → бет парақтау → бөлшектерге шашырау → light flare.

## Файлдар (`work/`)
- `index.html` — 3D анимация. `render(t)` уақыттың таза функциясы; субтитр мен оқиғалар `voice.json`-дағы сөз уақыттарымен жүреді.
- `make_voice.py` — диктор: Piper `kk_KZ-issai-high` (ер дауыс Iseke) → `voice/line*.wav`, `voice.json`.
- `make_audio.py` — домбыралы фон музыка (Karplus-Strong арқылы жасалған, сырттан алынған дыбыс жоқ), whoosh-тар, дикторды қосып, музыканы оның астында бәсеңдетеді → `soundtrack.wav`.
- `render.mjs` — кадр-кадрмен рендер (Playwright + ffmpeg).
- `photos/` — шынайы суреттер үшін: `ernur.jpg`, `university.jpg`. Жоқ болса, 3D иллюстрация салынады.
- Instagram никнеймі: `index.html` ішіндегі `INSTAGRAM` тұрақтысы.

## Қайта жасау
```bash
cd video/ernur-3d/work && npm install three@0.169.0
python3 make_voice.py && python3 make_audio.py
node render.mjs --out _video.mp4
ffmpeg -i _video.mp4 -i soundtrack.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart ../ernur-3d.mp4
```
