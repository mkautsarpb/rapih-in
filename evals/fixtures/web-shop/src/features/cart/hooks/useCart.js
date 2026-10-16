export function useCart(initialItems = []) {
  const items = [...initialItems];
  return {
    items,
    add(item) { items.push(item); },
    total() { return items.reduce((sum, i) => sum + i.price * i.qty, 0); },
  };
}
