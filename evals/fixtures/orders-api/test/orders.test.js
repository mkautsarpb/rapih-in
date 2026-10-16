import test from 'node:test';
import assert from 'node:assert/strict';
import { handleOrders } from '../src/routes/orders.js';

test('creates an order with gold discount and free shipping', async () => {
  const res = await handleOrders({ method: 'POST', url: '/orders', body: {
    customerId: 'c1', lines: [{ unitPrice: 60, qty: 2 }] } });
  assert.equal(res.status, 201);
  assert.deepEqual([res.body.subtotal, res.body.discount, res.body.shipping, res.body.total], [120, 12, 0, 108]);
});

test('rejects unknown customers', async () => {
  const res = await handleOrders({ method: 'POST', url: '/orders', body: { customerId: 'x', lines: [{ unitPrice: 1, qty: 1 }] } });
  assert.equal(res.status, 422);
});
