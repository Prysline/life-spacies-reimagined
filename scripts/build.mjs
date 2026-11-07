// 唯一正式來源目前是根目錄 index.html。
// 未來模組化時只需要更換這支建置腳本，GitHub Pages 仍發布 dist/。
import { copyFileSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const source = resolve(root, 'index.html');
const output = resolve(root, 'dist');
const html = readFileSync(source, 'utf8');

if (!/^<!doctype html>/i.test(html) || !html.includes('id="world"') || !html.includes('</html>')) {
  throw new Error('正式 index.html 的必要結構不完整；拒絕產出部署檔案。');
}

rmSync(output, { recursive: true, force: true });
mkdirSync(output, { recursive: true });
copyFileSync(source, resolve(output, 'index.html'));
writeFileSync(resolve(output, '.nojekyll'), '');
console.log('已產生 dist/index.html 與 dist/.nojekyll');
