import { test, expect, Page } from '@playwright/test';
import { randomUUID } from 'node:crypto';
import { paceLogin } from './login-pacing';

async function login(page: Page, password = process.env.ORGO_E2E_PASSWORD!) {
  await page.goto('/');
  await page.getByLabel('Organization', { exact: true }).fill(process.env.ORGO_E2E_ORGANIZATION!);
  await page.getByLabel('Email address').fill(process.env.ORGO_E2E_EMAIL!);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await paceLogin();
  const response = page.waitForResponse(r => r.url().endsWith('/auth/login') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  return response;
}

async function authenticated(page: Page) {
  const response = await login(page);
  // Do not print response bodies: successful login responses contain tokens.
  expect(response.ok(), `Orgo login refused: HTTP ${response.status()}. Check the Browser settings account and the API test database.`).toBeTruthy();
  await expect(page.getByRole('navigation', { name: 'Navigation Orgo' })).toBeVisible();
}

async function navigate(page: Page, label: string) {
  await page.getByRole('navigation').getByRole('button', { name: label, exact: true }).click();
  await expect(page.getByRole('heading', { name: label, exact: true, level: 1 })).toBeVisible();
}

async function create(page: Page, kind: string, button: string, title: string) {
  await page.getByRole('button', { name: button }).click();
  const form = page.getByRole('region', { name: 'Create item' });
  await form.getByLabel('Title', { exact: true }).fill(title);
  await form.getByLabel('Description', { exact: true }).fill('Playwright acceptance fixture');
  const pending = page.waitForResponse(r => r.url().endsWith(`/api/v3/${kind}`) && r.request().method() === 'POST');
  await form.getByRole('button', { name: 'Create', exact: true }).click();
  const response = await pending;
  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  expect(body.ok).toBe(true);
  await expect(form).toBeHidden();
  return body.data;
}

test('invalid credentials show an error and keep the session closed', async ({ page }) => {
  const response = await login(page, `invalid-${randomUUID()}`);
  expect([400, 401, 403]).toContain(response.status());
  await expect(page.locator('form.login-form').getByRole('alert')).toBeVisible();
  await expect(page.getByRole('navigation')).toHaveCount(0);
});

test('login, keyboard search and logout', async ({ page }) => {
  await authenticated(page);
  await page.keyboard.press('Control+k');
  await expect(page.getByRole('textbox', { name: 'Search this view' })).toBeFocused();
  const logout = page.waitForResponse(r => r.url().endsWith('/auth/logout'));
  await page.getByRole('button', { name: 'Sign out' }).click();
  expect((await logout).ok()).toBeTruthy();
  await expect(page.getByRole('button', { name: 'Sign in', exact: true })).toBeVisible();
  await expect(page.getByRole('navigation')).toHaveCount(0);
});

for (const [kind, label, button] of [
  ['cases', 'Cases', 'New case'],
  ['tasks', 'Tasks', 'New task'],
  ['signals', 'Signals', 'New signal'],
]) {
  test(`${kind}: create, search and reopen persisted detail`, async ({ page }) => {
    await authenticated(page);
    await navigate(page, label);
    const title = `E2E-${kind}-${randomUUID()}`;
    await create(page, kind, button, title);
    const searchResponse = page.waitForResponse(r => r.request().method() === 'GET' && new URL(r.url()).searchParams.get('search') === title);
    await page.getByRole('textbox', { name: 'Search this view' }).fill(title);
    expect((await searchResponse).ok()).toBeTruthy();
    await page.getByRole('button', { name: title }).click();
    await expect(page.getByRole('heading', { name: title, exact: true })).toBeVisible();
    // Reload forces another real login and server-side read (tokens live in memory).
    const detailURL = page.url();
    await page.reload();
    await authenticated(page);
    await page.getByRole('navigation').getByRole('button', { name: label, exact: true }).click();
    await page.getByRole('textbox', { name: 'Search this view' }).fill(title);
    await page.getByRole('button', { name: title }).click();
    await expect(page).toHaveURL(detailURL);
    await expect(page.getByRole('heading', { name: title, exact: true })).toBeVisible();
  });
}

test('task lifecycle is persisted by the API', async ({ page }) => {
  await authenticated(page);
  await navigate(page, 'Tasks');
  const title = `E2E-lifecycle-${randomUUID()}`;
  await create(page, 'tasks', 'New task', title);
  await page.getByRole('textbox', { name: 'Search this view' }).fill(title);
  await page.getByRole('button', { name: title }).click();
  for (const [label, status] of [['In progress', 'IN_PROGRESS'], ['Completed', 'COMPLETED']]) {
    const pending = page.waitForResponse(r => r.url().endsWith('/status') && r.request().method() === 'PATCH');
    await page.getByRole('button', { name: label, exact: true }).click();
    const response = await pending;
    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    expect(body.ok).toBe(true);
    await expect(page.locator('aside.detail .badge').first()).toHaveText(label);
  }
});

test('empty search does not display unrelated work', async ({ page }) => {
  await authenticated(page);
  await navigate(page, 'Cases');
  const query = `E2E-absent-${randomUUID()}`;
  const pending = page.waitForResponse(r => new URL(r.url()).searchParams.get('search') === query);
  await page.getByRole('textbox', { name: 'Search this view' }).fill(query);
  expect((await pending).ok()).toBeTruthy();
  await expect(page.getByText('No results for this search.', { exact: true })).toBeVisible();
  await expect(page.locator('tbody tr')).toHaveCount(0);
});
