import { CURRENCIES } from '../lib/currencyTable.js';

export function formatPrice(amount, currency = 'IDR') {
  const meta = CURRENCIES[currency];
  if (!meta) throw new Error(`Unknown currency: ${currency}`);
  return `${meta.symbol} ${amount.toFixed(meta.decimals)}`;
}
