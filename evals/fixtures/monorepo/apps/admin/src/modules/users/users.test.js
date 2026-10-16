import test from 'node:test';
import assert from 'node:assert/strict';
import { getUser } from './users.controller.js';

test('getUser', () => {
  const res = getUser({ params: { id: 'u1' } }, [{ id: 'u1', name: 'Sari', joinedAt: '2025-03-02T00:00:00Z' }]);
  assert.equal(res.body, 'Sari (joined 02/03/2025)');
});
