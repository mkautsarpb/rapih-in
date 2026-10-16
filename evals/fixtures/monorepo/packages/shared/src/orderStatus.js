// Shared helper used by web and admin.
import { STATUS_LABELS } from '../../../apps/web/src/features/orders/statusLabels.js';

export function orderStatusText(status) {
  return STATUS_LABELS[status] || 'Unknown';
}
