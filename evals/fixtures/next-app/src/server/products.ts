import 'server-only';

export async function listProducts() {
  return [{ id: 'p1', name: 'Kopi' }, { id: 'p2', name: 'Teh' }];
}
