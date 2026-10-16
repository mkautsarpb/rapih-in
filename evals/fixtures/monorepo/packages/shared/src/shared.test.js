import test from 'node:test';
import assert from 'node:assert/strict';
import { formatDate, orderStatusText } from './index.js';

test('formatDate', () => assert.equal(formatDate('2026-01-05T00:00:00Z'), '05/01/2026'));
test('orderStatusText', () => assert.equal(orderStatusText('shipped'), 'Shipped'));
