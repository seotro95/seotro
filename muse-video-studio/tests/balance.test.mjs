import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseMuseBalance } from '../muse-balance.mjs';

test('reads explicitly labelled token or credit balances, including a real zero', () => {
  assert.equal(parseMuseBalance('Tokens remaining: 1,234').valueText, '1,234');
  assert.equal(parseMuseBalance('0', 'credit-balance').valueText, '0');
  assert.equal(parseMuseBalance('0', 'credit-balance').unit, 'credit');
  assert.equal(parseMuseBalance('12.5K tokens left').valueText, '12.5K');
});
test('does not invent a balance from a context limit, ratio, unlabelled number or unknown state', () => {
  for (const label of ['128K tokens context window', '42', 'Credits: unknown', 'Tokens remaining 20 / 100', 'Token balance 4, updated 10:30', 'How many tokens left 42?']) assert.equal(parseMuseBalance(label), null);
});
