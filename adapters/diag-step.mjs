import { spawnSync } from 'node:child_process';
import { npmCommand, testDatabase } from './npm-command.mjs';
import path from 'node:path';

const steps = {
  generate: ['run', 'db:generate'], architecture: ['run', 'check:architecture'],
  types: ['run', 'typecheck'], unit: ['run', 'test'],
  pglite: ['run', 'test:pglite'], migrate: ['run', 'db:migrate'],
  integration: ['run', 'test:integration'], build: ['run', 'build'],
  audit: ['audit', '--json', '--audit-level=moderate'],
};
const step = process.argv[2];
const target = process.argv[3];
if (!target || !path.isAbsolute(target)) throw new Error('An absolute Orgo target path is required');
if (step === 'launcher') {
  const result = spawnSync(process.execPath, ['--test', path.join(import.meta.dirname, 'npm-command.test.mjs')], {
    cwd: target, stdio: 'inherit',
  });
  process.exit(result.status ?? 30);
}
if (!Object.hasOwn(steps, step)) throw new Error('Unknown diagnostic step');
const env = { ...process.env, NEXT_TELEMETRY_DISABLED: '1' };
if (['migrate', 'integration'].includes(step)) {
  try { env.DATABASE_URL = testDatabase(env.TEST_DATABASE_URL); }
  catch (error) { console.error(error.message); process.exit(20); }
  // A native run must never silently use PGlite's concurrency-test exemption.
  delete env.ORGO_TEST_ENGINE;
}
const [executable, ...args] = npmCommand(steps[step]);
const result = spawnSync(executable, args, { cwd: target, env, stdio: 'inherit' });
if (result.error) console.error(result.error.message);
process.exitCode = result.status ?? 30;
