import { setTimeout as delay } from 'node:timers/promises';

// AuthController permits 10 logins per IP per minute. With one worker,
// delaying every login also preserves the budget across test-file boundaries.
// This is deliberate rate limiting, not a sleep used to wait for UI state.
export async function paceLogin() {
  await delay(6500);
}
