import { existsSync, realpathSync } from 'node:fs';
import path from 'node:path';

// Invoke npm's JavaScript entry point, never npm.cmd through a shell.
export function npmCommand(args, env = process.env) {
  const candidates = [env.npm_execpath,
    path.join(path.dirname(process.execPath), 'node_modules/npm/bin/npm-cli.js'),
    path.resolve(path.dirname(process.execPath), '../lib/node_modules/npm/bin/npm-cli.js')];
  for (const directory of (env.PATH ?? env.Path ?? '').split(path.delimiter)) {
    if (!directory) continue;
    candidates.push(path.join(directory, 'node_modules/npm/bin/npm-cli.js'));
    const executable = path.join(directory, 'npm');
    if (existsSync(executable)) candidates.push(realpathSync(executable));
  }
  const cli = candidates.find(candidate => candidate && /npm-cli\.js$/i.test(candidate) && existsSync(candidate));
  if (!cli) throw new Error('npm-cli.js not found. Install Node.js with npm and reopen the terminal.');
  return [process.execPath, cli, ...args];
}

export function testDatabase(value) {
  if (!value) throw new Error('TEST_DATABASE_URL is required (dedicated disposable PostgreSQL database).');
  let url;
  try { url = new URL(value); } catch { throw new Error('TEST_DATABASE_URL is not a valid PostgreSQL URL.'); }
  const name = decodeURIComponent(url.pathname.slice(1));
  if (!['postgres:', 'postgresql:'].includes(url.protocol) || !url.hostname ||
      !/(^|[_-])(test|validation)([_-]|$)/i.test(name))
    throw new Error('Use a PostgreSQL database with a separate test or validation name segment, e.g. orgo_test.');
  return value;
}

export function redact(text, env = process.env) {
  let output = String(text);
  for (const [key, value] of Object.entries(env)) {
    if (value?.length >= 4 && /password|secret|token|database_url|api_?key/i.test(key))
      output = output.split(value).join('<REDACTED>');
  }
  return output.replace(/\b([a-z][a-z0-9+.-]*:\/\/)[^\s/"'<>]+@/gi, '$1<REDACTED>@')
    .replace(/\bBearer\s+[\w.~+/=-]+/gi, 'Bearer <REDACTED>');
}
