"""Regenerate the evaluation fixtures in evals/fixtures/ (overwrites fixture files only)."""

import os
import textwrap

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def w(base, rel, text):
    p = os.path.join(ROOT, base, *rel.split("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(textwrap.dedent(text).lstrip("\n"))


# ------------------------------------------------------------------ web-shop
B = "web-shop"
w(B, "package.json", """
{
  "name": "web-shop",
  "private": true,
  "type": "module",
  "scripts": {
    "test": "node --test"
  }
}
""")
w(B, "README.md", """
# web-shop

Small storefront UI. Components are plain functions that return HTML strings
(no framework, so the fixture runs with Node only). Features live in
`src/features/<feature>/` with `components/` and `hooks/` subfolders; generic UI
lives in `src/components/ui/`.

Run tests: `npm test` (uses `node --test`).
""")
w(B, "src/main.js", """
import { CartList } from './features/cart/components/CartList.js';
import { CheckoutPage } from './features/checkout/CheckoutPage.js';

export function renderApp(route, state) {
  if (route === '/cart') return CartList(state.cart);
  if (route === '/checkout') return CheckoutPage(state.checkout).html;
  return '<h1>Home</h1>';
}
""")
w(B, "src/components/ui/Button.js", """
export function Button({ label, variant = 'primary', disabled = false }) {
  return `<button class="btn btn-${variant}"${disabled ? ' disabled' : ''}>${label}</button>`;
}
""")
w(B, "src/utils/formatPrice.js", """
import { CURRENCIES } from '../lib/currencyTable.js';

export function formatPrice(amount, currency = 'IDR') {
  const meta = CURRENCIES[currency];
  if (!meta) throw new Error(`Unknown currency: ${currency}`);
  return `${meta.symbol} ${amount.toFixed(meta.decimals)}`;
}
""")
w(B, "src/features/cart/hooks/useCart.js", """
export function useCart(initialItems = []) {
  const items = [...initialItems];
  return {
    items,
    add(item) { items.push(item); },
    total() { return items.reduce((sum, i) => sum + i.price * i.qty, 0); },
  };
}
""")
w(B, "src/features/cart/components/CartList.js", """
import { Button } from '../../../components/ui/Button.js';
import { formatPrice } from '../../../utils/formatPrice.js';

export function CartList(cart) {
  const rows = cart.items
    .map((i) => `<li>${i.name} x${i.qty} - ${formatPrice(i.price * i.qty, cart.currency)}</li>`)
    .join('');
  return `<ul>${rows}</ul>${Button({ label: 'Checkout' })}`;
}
""")
w(B, "src/features/cart/cart.test.js", """
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
  assert.match(html, /Tea x2 - \\$ 3.00/);
  assert.match(html, /btn-primary/);
});
""")
w(B, "src/features/checkout/CheckoutPage.js", """
import { Button } from '../../components/ui/Button.js';

// Checkout page: renders the form, keeps form state, validates input,
// and submits the order to the backend.

const EMAIL_RE = /^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$/;

export function validateCheckout(values) {
  const errors = {};
  if (!values.name || values.name.trim().length < 2) errors.name = 'Name is too short';
  if (!EMAIL_RE.test(values.email || '')) errors.email = 'Email is invalid';
  if (!values.address) errors.address = 'Address is required';
  if (values.postalCode && !/^\\d{5}$/.test(values.postalCode)) errors.postalCode = 'Postal code must be 5 digits';
  return errors;
}

export async function submitOrder(values, fetchImpl = globalThis.fetch) {
  const res = await fetchImpl('/api/orders', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      customer: { name: values.name.trim(), email: values.email },
      shipping: { address: values.address, postalCode: values.postalCode || null },
    }),
  });
  if (!res.ok) {
    const err = new Error(`Order failed with status ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export function CheckoutPage(initial = {}) {
  const state = {
    values: { name: '', email: '', address: '', postalCode: '', ...initial },
    errors: {},
    status: 'idle',
    orderId: null,
  };

  function setField(field, value) {
    state.values = { ...state.values, [field]: value };
    if (state.errors[field]) {
      const { [field]: _removed, ...rest } = state.errors;
      state.errors = rest;
    }
  }

  async function submit(fetchImpl) {
    state.errors = validateCheckout(state.values);
    if (Object.keys(state.errors).length > 0) {
      state.status = 'invalid';
      return state;
    }
    state.status = 'submitting';
    try {
      const order = await submitOrder(state.values, fetchImpl);
      state.orderId = order.id;
      state.status = 'done';
    } catch (e) {
      state.status = e.status === 409 ? 'duplicate' : 'error';
    }
    return state;
  }

  function render() {
    const field = (name, label) =>
      `<label>${label}<input name="${name}" value="${state.values[name]}"/>` +
      (state.errors[name] ? `<span class="error">${state.errors[name]}</span>` : '') +
      '</label>';
    return [
      '<main class="checkout">',
      '<h1>Checkout</h1>',
      '<form>',
      field('name', 'Name'),
      field('email', 'Email'),
      field('address', 'Address'),
      field('postalCode', 'Postal code'),
      Button({
        label: state.status === 'submitting' ? 'Sending...' : 'Place order',
        disabled: state.status === 'submitting',
      }),
      '</form>',
      state.status === 'done' ? `<p class="ok">Order ${state.orderId} placed</p>` : '',
      '</main>',
    ].join('');
  }

  return { state, setField, submit, render, get html() { return render(); } };
}
""")
w(B, "src/features/checkout/checkout.test.js", """
import test from 'node:test';
import assert from 'node:assert/strict';
import { CheckoutPage } from './CheckoutPage.js';

test('checkout renders the form', () => {
  const page = CheckoutPage();
  assert.match(page.html, /<h1>Checkout<\\/h1>/);
  assert.match(page.html, /Place order/);
});
""")
codes = [("IDR", "Rp", 0, "Indonesian rupiah"), ("USD", "$", 2, "US dollar"), ("EUR", "€", 2, "Euro"),
         ("JPY", "¥", 0, "Japanese yen"), ("SGD", "S$", 2, "Singapore dollar"), ("MYR", "RM", 2, "Malaysian ringgit"),
         ("GBP", "£", 2, "Pound sterling"), ("AUD", "A$", 2, "Australian dollar"), ("CNY", "¥", 2, "Chinese yuan"),
         ("KRW", "₩", 0, "South Korean won"), ("THB", "฿", 2, "Thai baht"), ("PHP", "₱", 2, "Philippine peso"),
         ("VND", "₫", 0, "Vietnamese dong"), ("INR", "₹", 2, "Indian rupee"), ("CHF", "CHF", 2, "Swiss franc"),
         ("CAD", "C$", 2, "Canadian dollar"), ("NZD", "NZ$", 2, "New Zealand dollar"), ("HKD", "HK$", 2, "Hong Kong dollar"),
         ("SAR", "SR", 2, "Saudi riyal"), ("AED", "AED", 2, "UAE dirham"), ("SEK", "kr", 2, "Swedish krona"),
         ("NOK", "kr", 2, "Norwegian krone"), ("DKK", "kr", 2, "Danish krone"), ("BRL", "R$", 2, "Brazilian real")]
lines = ["// Currency metadata used for price formatting. One table, one reason to change:",
         "// add or correct a currency here.", "", "export const CURRENCIES = {"]
for c, s, d, n in codes:
    lines += ["  %s: {" % c, "    code: '%s'," % c, "    name: '%s'," % n, "    symbol: '%s'," % s,
              "    decimals: %d," % d, "  },"]
lines += ["};", "", "export function currencyCodes() {", "  return Object.keys(CURRENCIES);", "}", "",
          "export function isSupportedCurrency(code) {",
          "  return Object.prototype.hasOwnProperty.call(CURRENCIES, code);", "}", ""]
w(B, "src/lib/currencyTable.js", "\n".join(lines))
g = ["// @generated by openapi-codegen from api/openapi.yaml. DO NOT EDIT.", ""]
for i, n in enumerate(["Order", "OrderLine", "Customer", "Address", "Payment", "Refund", "Shipment", "Coupon",
                       "Product", "Inventory", "Warehouse", "Invoice", "TaxRate", "Discount", "Review"]):
    g += ["export const %sSchema = Object.freeze({" % n, "  name: '%s'," % n,
          "  fields: ['id', 'createdAt', 'updatedAt'],", "  version: %d," % (i + 1), "});", ""]
w(B, "src/generated/apiTypes.js", "\n".join(g))

# ------------------------------------------------------------------ orders-api
B = "orders-api"
w(B, "package.json", """
{
  "name": "orders-api",
  "private": true,
  "type": "module",
  "main": "src/server.js",
  "scripts": {
    "start": "node src/server.js",
    "test": "node --test \\"test/**/*.test.js\\""
  }
}
""")
w(B, "src/server.js", """
import http from 'node:http';
import { handleOrders } from './routes/orders.js';
import { handleHealth } from './routes/health.js';

export function createServer() {
  return http.createServer(async (req, res) => {
    const chunks = [];
    for await (const c of req) chunks.push(c);
    const body = chunks.length ? JSON.parse(Buffer.concat(chunks).toString('utf8')) : null;
    const result = req.url.startsWith('/orders')
      ? await handleOrders({ method: req.method, url: req.url, body })
      : handleHealth();
    res.writeHead(result.status, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(result.body));
  });
}

if (process.argv[1] && process.argv[1].endsWith('server.js')) {
  createServer().listen(3000);
}
""")
w(B, "src/routes/health.js", """
export function handleHealth() {
  return { status: 200, body: { ok: true } };
}
""")
w(B, "src/services/customerService.js", """
import { db } from '../db/memory.js';

export function findCustomer(id) {
  return db.customers.find((c) => c.id === id) || null;
}
""")
w(B, "src/db/memory.js", """
export const db = {
  customers: [
    { id: 'c1', name: 'Ayu', tier: 'gold' },
    { id: 'c2', name: 'Budi', tier: 'standard' },
  ],
  orders: [],
};
""")
w(B, "src/routes/orders.js", """
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
""")
w(B, "test/orders.test.js", """
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
""")

# ------------------------------------------------------------------ monorepo
B = "monorepo"
w(B, "package.json", """
{
  "name": "acme",
  "private": true,
  "workspaces": ["apps/*", "packages/*"],
  "scripts": {
    "test": "node --test \\"apps/**/*.test.js\\" \\"packages/**/*.test.js\\""
  }
}
""")
w(B, "packages/shared/package.json", """
{
  "name": "@acme/shared",
  "version": "1.0.0",
  "type": "module",
  "exports": { ".": "./src/index.js" }
}
""")
w(B, "packages/shared/src/index.js", """
export { formatDate } from './formatDate.js';
export { orderStatusText } from './orderStatus.js';
""")
w(B, "packages/shared/src/formatDate.js", """
export function formatDate(iso) {
  const d = new Date(iso);
  return `${String(d.getUTCDate()).padStart(2, '0')}/${String(d.getUTCMonth() + 1).padStart(2, '0')}/${d.getUTCFullYear()}`;
}
""")
w(B, "packages/shared/src/orderStatus.js", """
// Shared helper used by web and admin.
import { STATUS_LABELS } from '../../../apps/web/src/features/orders/statusLabels.js';

export function orderStatusText(status) {
  return STATUS_LABELS[status] || 'Unknown';
}
""")
w(B, "packages/shared/src/shared.test.js", """
import test from 'node:test';
import assert from 'node:assert/strict';
import { formatDate, orderStatusText } from './index.js';

test('formatDate', () => assert.equal(formatDate('2026-01-05T00:00:00Z'), '05/01/2026'));
test('orderStatusText', () => assert.equal(orderStatusText('shipped'), 'Shipped'));
""")
w(B, "apps/web/package.json", """
{ "name": "@acme/web", "private": true, "type": "module", "dependencies": { "@acme/shared": "1.0.0" } }
""")
w(B, "apps/web/src/features/orders/statusLabels.js", """
export const STATUS_LABELS = { pending: 'Pending', shipped: 'Shipped', delivered: 'Delivered' };
""")
w(B, "apps/web/src/features/orders/OrderList.js", """
import { formatDate, orderStatusText } from '../../../../../packages/shared/src/index.js';

export function OrderList(orders) {
  return orders.map((o) => `<li>${formatDate(o.createdAt)} ${orderStatusText(o.status)}</li>`).join('');
}
""")
w(B, "apps/admin/package.json", """
{ "name": "@acme/admin", "private": true, "type": "module", "dependencies": { "@acme/shared": "1.0.0" } }
""")
w(B, "apps/admin/src/modules/users/users.service.js", """
import { formatDate } from '../../../../../packages/shared/src/index.js';

export function describeUser(user) {
  return `${user.name} (joined ${formatDate(user.joinedAt)})`;
}
""")
w(B, "apps/admin/src/modules/users/users.controller.js", """
import { describeUser } from './users.service.js';

export function getUser(req, users) {
  const user = users.find((u) => u.id === req.params.id);
  return user ? { status: 200, body: describeUser(user) } : { status: 404, body: null };
}
""")
w(B, "apps/admin/src/modules/users/users.test.js", """
import test from 'node:test';
import assert from 'node:assert/strict';
import { getUser } from './users.controller.js';

test('getUser', () => {
  const res = getUser({ params: { id: 'u1' } }, [{ id: 'u1', name: 'Sari', joinedAt: '2025-03-02T00:00:00Z' }]);
  assert.equal(res.body, 'Sari (joined 02/03/2025)');
});
""")

# ------------------------------------------------------------------ py-billing
B = "py-billing"
w(B, "pyproject.toml", """
[project]
name = "billing"
version = "0.3.0"
requires-python = ">=3.9"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
""")
w(B, "Makefile", """
test:
\tPYTHONPATH=src python -m unittest discover -s tests -t .
""")
w(B, "src/billing/__init__.py", """
from billing.invoice import Invoice, build_invoice

__all__ = ["Invoice", "build_invoice"]
""")
w(B, "src/billing/invoice.py", """
from dataclasses import dataclass, field

from billing.tax import apply_tax


@dataclass
class Invoice:
    customer: str
    lines: list = field(default_factory=list)

    @property
    def subtotal(self):
        return sum(qty * price for qty, price in self.lines)

    @property
    def total(self):
        return apply_tax(self.subtotal)


def build_invoice(customer, lines):
    return Invoice(customer=customer, lines=list(lines))
""")
w(B, "src/billing/tax.py", """
VAT_RATE = 0.11


def apply_tax(amount):
    return round(amount * (1 + VAT_RATE), 2)
""")
w(B, "tests/__init__.py", "")
w(B, "tests/test_invoice.py", """
import unittest

from billing import build_invoice


class InvoiceTest(unittest.TestCase):
    def test_total_includes_vat(self):
        inv = build_invoice("ACME", [(2, 50.0)])
        self.assertEqual(inv.subtotal, 100.0)
        self.assertEqual(inv.total, 111.0)


if __name__ == "__main__":
    unittest.main()
""")

# ------------------------------------------------------------------ next-app (static, not runnable)
B = "next-app"
w(B, "package.json", """
{
  "name": "next-app",
  "private": true,
  "scripts": { "dev": "next dev", "build": "next build", "lint": "next lint" },
  "dependencies": { "next": "15.1.0", "react": "19.0.0", "react-dom": "19.0.0", "server-only": "0.0.1" }
}
""")
w(B, "next.config.mjs", """
/** @type {import('next').NextConfig} */
const nextConfig = {};
export default nextConfig;
""")
w(B, "tsconfig.json", """
{ "compilerOptions": { "baseUrl": ".", "paths": { "@/*": ["./src/*"] }, "jsx": "preserve", "strict": true } }
""")
w(B, "src/app/layout.tsx", """
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}
""")
w(B, "src/app/(shop)/products/page.tsx", """
import { listProducts } from '@/server/products';
import { ProductFilters } from './_components/ProductFilters';

export default async function ProductsPage() {
  const products = await listProducts();
  return (<main><ProductFilters /><ul>{products.map((p) => <li key={p.id}>{p.name}</li>)}</ul></main>);
}
""")
w(B, "src/app/(shop)/products/_components/ProductFilters.tsx", """
'use client';
import { useState } from 'react';

export function ProductFilters() {
  const [q, setQ] = useState('');
  return <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search" />;
}
""")
w(B, "src/app/api/products/route.ts", """
import { listProducts } from '@/server/products';

export async function GET() {
  return Response.json(await listProducts());
}
""")
w(B, "src/server/products.ts", """
import 'server-only';

export async function listProducts() {
  return [{ id: 'p1', name: 'Kopi' }, { id: 'p2', name: 'Teh' }];
}
""")

# ------------------------------------------------------------------ tidy-notes (already consistent)
B = "tidy-notes"
w(B, "package.json", """
{
  "name": "tidy-notes",
  "private": true,
  "type": "module",
  "scripts": { "test": "node --test" }
}
""")
w(B, "src/notes/noteStore.js", """
export function createNoteStore() {
  const notes = new Map();
  return {
    add(id, text) { notes.set(id, { id, text }); },
    get(id) { return notes.get(id) || null; },
    list() { return [...notes.values()]; },
  };
}
""")
w(B, "src/notes/noteStore.test.js", """
import test from 'node:test';
import assert from 'node:assert/strict';
import { createNoteStore } from './noteStore.js';

test('add and list', () => {
  const s = createNoteStore();
  s.add('a', 'hello');
  assert.deepEqual(s.list(), [{ id: 'a', text: 'hello' }]);
});
""")
w(B, "src/notes/renderNote.js", """
export function renderNote(note) {
  return `<article data-id="${note.id}">${note.text}</article>`;
}
""")
w(B, "src/notes/renderNote.test.js", """
import test from 'node:test';
import assert from 'node:assert/strict';
import { renderNote } from './renderNote.js';

test('renders', () => assert.equal(renderNote({ id: 'a', text: 'x' }), '<article data-id="a">x</article>'));
""")
w(B, "src/main.js", """
import { createNoteStore } from './notes/noteStore.js';
import { renderNote } from './notes/renderNote.js';

export function app() {
  const store = createNoteStore();
  store.add('welcome', 'Welcome to tidy-notes');
  return store.list().map(renderNote).join('');
}
""")
print("ok")
