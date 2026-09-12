import { test, expect } from '@playwright/test';
import { login } from './support';

test('E16 local login remains available when SSO is unconfigured', async ({ page }) => {
  const pending = page.waitForResponse(response =>
    new URL(response.url()).pathname === '/api/v3/auth/sso/config'
      && response.request().method() === 'GET'
  );
  await page.goto('/');
  const response = await pending;
  expect(response.ok(), `SSO config HTTP ${response.status()}`).toBeTruthy();
  const body = await response.json();
  expect(body.ok).toBe(true);
  expect(body.data.available).toBe(false);
  expect(body.data.local_login_available).toBe(true);
  expect(body.data.identity_key).toBe('issuer+subject');
  await expect(page.getByRole('button', { name: 'Se connecter', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: /Se connecter avec / })).toHaveCount(0);
  await login(page);
});

test('E17 SSO option keeps the local login visible when federation is advertised', async ({ page }) => {
  await page.route('**/api/v3/auth/sso/config', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true,
        data: {
          available: true,
          display_name: 'kOA Identity',
          local_login_available: true,
          identity_key: 'issuer+subject',
        },
        error: null,
      }),
    });
  });
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Se connecter', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Se connecter avec kOA Identity', exact: true })).toBeVisible();
  await expect(page.getByLabel('Mot de passe', { exact: true })).toBeVisible();
});
