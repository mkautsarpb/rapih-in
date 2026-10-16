import { Button } from '../../components/ui/Button.js';

// Checkout page: renders the form, keeps form state, validates input,
// and submits the order to the backend.

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export function validateCheckout(values) {
  const errors = {};
  if (!values.name || values.name.trim().length < 2) errors.name = 'Name is too short';
  if (!EMAIL_RE.test(values.email || '')) errors.email = 'Email is invalid';
  if (!values.address) errors.address = 'Address is required';
  if (values.postalCode && !/^\d{5}$/.test(values.postalCode)) errors.postalCode = 'Postal code must be 5 digits';
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
