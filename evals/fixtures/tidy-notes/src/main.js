import { createNoteStore } from './notes/noteStore.js';
import { renderNote } from './notes/renderNote.js';

export function app() {
  const store = createNoteStore();
  store.add('welcome', 'Welcome to tidy-notes');
  return store.list().map(renderNote).join('');
}
