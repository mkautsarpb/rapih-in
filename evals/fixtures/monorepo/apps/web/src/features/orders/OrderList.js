import { formatDate, orderStatusText } from '../../../../../packages/shared/src/index.js';

export function OrderList(orders) {
  return orders.map((o) => `<li>${formatDate(o.createdAt)} ${orderStatusText(o.status)}</li>`).join('');
}
