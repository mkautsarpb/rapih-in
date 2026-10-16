import test from 'node:test';
import assert from 'node:assert/strict';
import { createNoteStore } from './noteStore.js';

test('add and list', () => {
  const s = createNoteStore();
  s.add('a', 'hello');
  assert.deepEqual(s.list(), [{ id: 'a', text: 'hello' }]);
});
