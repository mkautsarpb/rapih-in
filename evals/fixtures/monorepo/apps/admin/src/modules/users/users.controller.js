import { describeUser } from './users.service.js';

export function getUser(req, users) {
  const user = users.find((u) => u.id === req.params.id);
  return user ? { status: 200, body: describeUser(user) } : { status: 404, body: null };
}
