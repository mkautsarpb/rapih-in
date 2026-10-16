import test from 'node:test';
import assert from 'node:assert/strict';
import { CheckoutPage } from './CheckoutPage.js';

test('checkout renders the form', () => {
  const page = CheckoutPage();
  assert.match(page.html, /<h1>Checkout<\/h1>/);
  assert.match(page.html, /Place order/);
});
