export function renderNote(note) {
  return `<article data-id="${note.id}">${note.text}</article>`;
}
