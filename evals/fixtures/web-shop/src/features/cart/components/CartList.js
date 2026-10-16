import { Button } from '../../../components/ui/Button.js';
import { formatPrice } from '../../../utils/formatPrice.js';

export function CartList(cart) {
  const rows = cart.items
    .map((i) => `<li>${i.name} x${i.qty} - ${formatPrice(i.price * i.qty, cart.currency)}</li>`)
    .join('');
  return `<ul>${rows}</ul>${Button({ label: 'Checkout' })}`;
}
