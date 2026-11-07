import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { Script } from 'node:vm';

const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const embeddedScripts = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)]
  .map((match) => match[1].trim()).filter(Boolean);

test('v2 remains a self-contained HTML document', () => {
  assert.match(html, /^<!doctype html>/i);
  assert.match(html, /<html lang="zh-Hant">/);
  assert.equal(embeddedScripts.length, 1);
  assert.doesNotMatch(html, /<script[^>]+src=/i);
});

test('embedded JavaScript is syntactically valid', () => {
  assert.doesNotThrow(() => new Script(embeddedScripts[0], { filename: 'index.html' }));
});

test('baseline controls and gene inspector are present', () => {
  const ids = [
    'world', 'geneText', 'createBtn', 'feedText', 'feedBtn',
    'living', 'foodCount', 'births', 'autoFeed', 'simSpeed',
    'startMode', 'pauseBtn', 'resetBtn', 'clearBtn', 'demoBtn',
    'eventLog', 'selectedInfo', 'inspector', 'traitGrid', 'traceBody'
  ];
  for (const id of ids) {
    assert.ok(html.includes('id="' + id + '"'), 'Missing DOM control: ' + id);
  }
  assert.match(html, /value="empty"/);
  assert.match(html, /value="demo"/);
});

test('five morphologies and responsive breakpoints are retained', () => {
  for (const name of ['浮游鐘', '甲殼盤', '星刺體', '節環蟲', '翼葉體']) {
    assert.ok(html.includes(name), 'Missing morphology: ' + name);
  }
  assert.match(html, /function decode\(text\)/);
  assert.match(html, /@media\(max-width:800px\)/);
  assert.match(html, /@media\(max-width:600px\)/);
});
