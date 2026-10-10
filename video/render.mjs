// Renders an HTML animation frame by frame and encodes an MP4 with ffmpeg.
// Usage: node video/render.mjs [page.html] [audio file]
//   node video/render.mjs                                         -> salem-claude.mp4 (silent)
//   node video/render.mjs ernur.html audio/soundtrack.wav         -> ernur.mp4 (with sound)
// The page must expose window.renderFrame(t) and window.DURATION. Needs playwright + ffmpeg.
import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

const dir = path.dirname(fileURLToPath(import.meta.url));
const FPS = 30;
const html = process.argv[2] ?? 'salem-claude.html';
const audio = process.argv[3] ? path.resolve(dir, process.argv[3]) : null;
const out = path.join(dir, html.replace(/\.html$/, '.mp4'));

const browser = await chromium.launch(
  process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
await page.goto(pathToFileURL(path.join(dir, html)).href + '?export', { waitUntil: 'load', timeout: 20000 }).catch(() => {});
await page.evaluate(() => document.fonts.ready);

const duration = await page.evaluate(() => window.DURATION);
const frames = Math.round(duration * FPS);

const args = ['-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-'];
if (audio) args.push('-i', audio, '-c:a', 'aac', '-b:a', '192k', '-shortest');
args.push('-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-preset', 'slow', '-crf', '18',
  '-movflags', '+faststart', out);
const ff = spawn('ffmpeg', args, { stdio: ['pipe', 'inherit', 'inherit'] });

for (let i = 0; i < frames; i++) {
  await page.evaluate((t) => window.renderFrame(t), i / FPS);
  const buf = await page.screenshot({ type: 'png' });
  if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
  if (i % 30 === 0) console.log(`frame ${i}/${frames}`);
}
ff.stdin.end();
await new Promise((r) => ff.on('close', r));
await browser.close();
console.log('saved', out);
