import { CartList } from './features/cart/components/CartList.js';
import { CheckoutPage } from './features/checkout/CheckoutPage.js';

export function renderApp(route, state) {
  if (route === '/cart') return CartList(state.cart);
  if (route === '/checkout') return CheckoutPage(state.checkout).html;
  return '<h1>Home</h1>';
}
