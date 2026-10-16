export function createNoteStore() {
  const notes = new Map();
  return {
    add(id, text) { notes.set(id, { id, text }); },
    get(id) { return notes.get(id) || null; },
    list() { return [...notes.values()]; },
  };
}
