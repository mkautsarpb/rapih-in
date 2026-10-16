import test from 'node:test';
import assert from 'node:assert/strict';
import { CartList } from './components/CartList.js';
import { useCart } from './hooks/useCart.js';

test('cart total', () => {
  const cart = useCart([{ name: 'Tea', price: 10, qty: 2 }]);
  cart.add({ name: 'Cup', price: 5, qty: 1 });
  assert.equal(cart.total(), 25);
});

test('cart list renders formatted prices', () => {
  const html = CartList({ currency: 'USD', items: [{ name: 'Tea', price: 1.5, qty: 2 }] });
  assert.match(html, /Tea x2 - \$ 3.00/);
  assert.match(html, /btn-primary/);
});
