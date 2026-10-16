import { formatDate } from '../../../../../packages/shared/src/index.js';

export function describeUser(user) {
  return `${user.name} (joined ${formatDate(user.joinedAt)})`;
}
