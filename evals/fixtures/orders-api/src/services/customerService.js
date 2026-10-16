import { db } from '../db/memory.js';

export function findCustomer(id) {
  return db.customers.find((c) => c.id === id) || null;
}
