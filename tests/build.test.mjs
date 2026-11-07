import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { test } from 'node:test';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');

test('build generates only the canonical offline HTML in dist', () => {
  execFileSync(process.execPath, [resolve(root, 'scripts/build.mjs')], { cwd: root });
  const produced = readdirSync(resolve(root, 'dist')).sort();
  assert.deepEqual(produced, ['.nojekyll', 'index.html']);
  assert.deepEqual(
    readFileSync(resolve(root, 'dist/index.html')),
    readFileSync(resolve(root, 'index.html')),
    'deployment output must be an exact copy of the canonical source before modularization',
  );
  assert.equal(statSync(resolve(root, 'dist/.nojekyll')).size, 0);
});
