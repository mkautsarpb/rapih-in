import { db } from '../db/memory.js';
import { findCustomer } from '../services/customerService.js';

// Orders endpoint: parses the request, applies pricing rules, and stores orders.

const TIER_DISCOUNT = { gold: 0.1, standard: 0 };

export async function handleOrders(req) {
  if (req.method === 'GET') {
    const id = req.url.split('/')[2];
    if (!id) return { status: 200, body: db.orders };
    const order = db.orders.find((o) => o.id === id);
    return order ? { status: 200, body: order } : { status: 404, body: { error: 'not_found' } };
  }
  if (req.method !== 'POST') return { status: 405, body: { error: 'method_not_allowed' } };

  const input = req.body || {};
  if (!input.customerId || !Array.isArray(input.lines) || input.lines.length === 0) {
    return { status: 400, body: { error: 'invalid_order' } };
  }
  const customer = findCustomer(input.customerId);
  if (!customer) return { status: 422, body: { error: 'unknown_customer' } };

  const subtotal = input.lines.reduce((sum, l) => sum + l.unitPrice * l.qty, 0);
  const discount = Math.round(subtotal * (TIER_DISCOUNT[customer.tier] || 0) * 100) / 100;
  const shipping = subtotal - discount >= 100 ? 0 : 7.5;
  const total = Math.round((subtotal - discount + shipping) * 100) / 100;

  const order = { id: `o${db.orders.length + 1}`, customerId: customer.id, subtotal, discount, shipping, total };
  db.orders.push(order);
  return { status: 201, body: order };
}
