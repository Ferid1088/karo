// Run with: node --test tests/test_drafts.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const script = readFileSync(new URL('../app/static/drafts.js', import.meta.url), 'utf8');
function setup({revision = 0, draft, fetch} = {}) {
  const listeners = new Map();
  const values = new Map(draft ? [['karo-antworten-7', JSON.stringify(draft)]] : []);
  const buttons = [];
  const field = {name: 'antwort_1', value: 'server', type: 'text'};
  const rev = {value: revision};
  const status = {textContent: '', after: button => buttons.push(button)};
  const form = {
    action: 'http://localhost/quiz/7/antworten', dataset: {},
    hasAttribute: () => false,
    querySelector: selector => selector.includes('_csrf') ? {value: 'csrf'} : selector.includes('draft_revision') ? rev : status,
    querySelectorAll: selector => selector.includes('draft-choice') ? buttons : [field],
    addEventListener: (type, fn) => listeners.set(type, fn),
    dispatchEvent: () => {},
  };
  const quiz = {dataset: {draftKey: 'karo-antworten-7', quizState: 'bereit', draftRevision: revision}};
  const document = {
    querySelector: selector => selector === '[data-draft-key]' ? quiz : form,
    addEventListener: () => {},
    createElement: () => ({dataset: {}, addEventListener(type, fn) {this.click = fn;}, remove() {}}),
  };
  let submitted = false;
  const windowListeners = new Map();
  vm.runInNewContext(script, {
    document, window: {addEventListener: (type, fn) => windowListeners.set(type, fn)},
    localStorage: {getItem: key => values.get(key), setItem: (key, value) => values.set(key, value)},
    URLSearchParams, Event, fetch,
    setTimeout: () => 1, clearTimeout: () => {},
    HTMLFormElement: {prototype: {submit() {submitted = true;}}},
  });
  return {form, field, rev, status, buttons, listeners, windowListeners,
    cache: () => JSON.parse(values.get('karo-antworten-7')), submitted: () => submitted};
}
const ok = revision => ({ok: true, json: async () => ({revision, saved: true})});

test('typing during a save is serialized and final submit waits for all answers', async () => {
  const calls = [];
  let release;
  const ui = setup({fetch: async (_, request) => {
    calls.push(Object.fromEntries(request.body));
    if (calls.length === 1) await new Promise(resolve => {release = resolve;});
    return ok(calls.length);
  }});
  ui.field.value = 'first'; ui.form.karoDraft.schedule();
  const saving = ui.form.karoDraft.flush();
  ui.field.value = 'latest'; ui.form.karoDraft.schedule();
  release(); await saving;
  assert.equal(calls.length, 2);
  assert.equal(calls[1].revision, '1');
  assert.equal(JSON.parse(calls[1].values).antwort_1, 'latest');
  assert.equal(ui.cache().unsynced, false);
  await ui.listeners.get('submit')({preventDefault() {}});
  assert.equal(ui.submitted(), true);
  assert.equal(ui.rev.value, 3);
});

test('failed save keeps local answers and a reopened page restores and uploads them', async () => {
  const offline = setup({fetch: async () => {throw new Error('offline');}});
  offline.field.value = '3/4'; offline.form.dataset.position = 2;
  offline.form.karoDraft.schedule();
  await assert.rejects(offline.form.karoDraft.flush());
  assert.equal(offline.cache().unsynced, true);
  const resumed = setup({draft: offline.cache(), fetch: async () => ok(1)});
  assert.equal(resumed.field.value, '3/4');
  assert.equal(resumed.form.dataset.position, 2);
  await resumed.form.karoDraft.flush();
  assert.equal(resumed.cache().unsynced, false);
});

test('stale tabs cannot silently overwrite newer server answers or submit', async () => {
  const stale = setup({fetch: async () => ({ok: false, status: 409})});
  stale.field.value = 'my draft'; stale.form.karoDraft.schedule();
  await assert.rejects(stale.form.karoDraft.flush());
  await stale.listeners.get('submit')({preventDefault() {}});
  assert.equal(stale.submitted(), false);
  const resumed = setup({revision: 4, draft: stale.cache(), fetch: async () => ok(5)});
  assert.equal(resumed.field.value, 'server');
  assert.equal(resumed.field.disabled, true);
  assert.equal(resumed.buttons.length, 2);
  resumed.buttons[0].click();
  assert.equal(resumed.field.value, 'my draft');
  assert.equal(resumed.field.disabled, false);
  await resumed.form.karoDraft.flush();
  assert.equal(resumed.rev.value, 5);
});
