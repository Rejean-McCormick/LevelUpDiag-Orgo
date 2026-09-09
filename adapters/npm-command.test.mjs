import { test } from 'node:test';
import assert from 'node:assert/strict';
import { npmCommand, testDatabase, redact } from './npm-command.mjs';
test('npm is executed as JavaScript without a cmd shell', () => {
  const command = npmCommand(['run', 'test']);
  assert.equal(command[0], process.execPath);
  assert.match(command[1], /npm-cli\.js$/);
  assert.deepEqual(command.slice(2), ['run', 'test']);
});
test('only explicitly named test PostgreSQL databases accepted', () => {
  for (const value of ['', 'invalid', 'https://host/orgo_test', 'postgresql://host/production', 'postgresql://host/latest'])
    assert.throws(() => testDatabase(value));
  assert.equal(testDatabase('postgresql://localhost/orgo_test'), 'postgresql://localhost/orgo_test');
});
test('reports redact database credentials and environment secrets', () => {
  const value = redact('postgresql://user:pass@host/db Bearer abcdefghi TOKEN=supersecret', { TOKEN: 'supersecret' });
  assert.ok(!value.includes('pass@'));
  assert.ok(!value.includes('abcdefghi'));
  assert.ok(!value.includes('supersecret'));
});
