import test from 'node:test';
import assert from 'node:assert/strict';
import { renderNote } from './renderNote.js';

test('renders', () => assert.equal(renderNote({ id: 'a', text: 'x' }), '<article data-id="a">x</article>'));
