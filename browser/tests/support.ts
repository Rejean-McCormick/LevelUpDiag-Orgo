import { expect, Page, Locator, APIResponse } from '@playwright/test';
import { randomUUID } from 'node:crypto';
import { paceLogin } from './login-pacing';

export const unique = (kind: string) => `E2E-${kind}-${randomUUID()}`;
export const id = (row: any) => row.id ?? row.task_id ?? row.case_id ?? row.signal_id;
export const taskInput = (title: string) => ({ title, label: '1.11', type: 'general', category: 'request' });

export async function login(page: Page, email = process.env.ORGO_E2E_EMAIL!, password = process.env.ORGO_E2E_PASSWORD!) {
  await page.goto('/');
  await page.getByLabel('Organisation', { exact: true }).fill(process.env.ORGO_E2E_ORGANIZATION!);
  await page.getByLabel('Adresse courriel').fill(email);
  await page.getByLabel('Mot de passe', { exact: true }).fill(password);
  await paceLogin();
  const pending = page.waitForResponse(r => r.url().endsWith('/auth/login') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Se connecter', exact: true }).click();
  const response = await pending;
  expect(response.ok(), `Login HTTP ${response.status()}`).toBeTruthy();
  const result = await response.json();
  expect(result.ok).toBe(true);
  await expect(page.getByRole('navigation', { name: 'Navigation Orgo' })).toBeVisible();
  return result.data;
}

export async function api(page: Page, token: string, path: string, method = 'GET', data?: unknown) {
  return page.request.fetch(new URL(`/api/v3/${path}`, page.url()).toString(), {
    method, data, headers: { Authorization: `Bearer ${token}`, 'Idempotency-Key': randomUUID() },
  });
}
export async function value(response: APIResponse | Awaited<ReturnType<Page['waitForResponse']>>) {
  expect(response.ok(), `API HTTP ${response.status()} on ${new URL(response.url()).pathname}`).toBeTruthy();
  const body = await response.json();
  expect(body.ok).toBe(true);
  return body.data;
}
export async function profile(page: Page, name: string) {
  await page.locator('.profile-label select').selectOption(name);
}
export async function nav(page: Page, label: string) {
  await page.getByRole('navigation').getByRole('button', { name: label, exact: true }).click();
  await expect(page.getByRole('heading', { name: label, level: 1, exact: true })).toBeVisible();
}
export async function openWork(page: Page, label: string, title: string) {
  await nav(page, label);
  const search = page.getByRole('textbox', { name: 'Rechercher dans la vue' });
  const endpoint = label === 'Dossiers' ? 'cases' : label === 'Signaux' ? 'signals' : 'tasks';
  const isListResponse = (response: Awaited<ReturnType<Page['waitForResponse']>>, expectedSearch: string) => {
    const url = new URL(response.url());
    return response.request().method() === 'GET'
      && url.pathname === `/api/v3/${endpoint}`
      && url.searchParams.get('search') === expectedSearch
      && (label !== 'Mon travail' || url.searchParams.get('mine') === 'true');
  };

  // Orgo debounces the visible search value into `query` by 250 ms. A profile
  // or section transition can therefore leave the input and the effective
  // query temporarily out of sync. Force a unique intermediate query and
  // wait for its list response before applying the real title. This makes
  // opening work deterministic even when the prior effective query already
  // equals `title` (notably Tasks -> My Work in E04).
  const syncSearch = `__orgo_e2e_sync_${randomUUID()}__`;
  const synced = page.waitForResponse(response => isListResponse(response, syncSearch));
  await search.fill(syncSearch);
  let response = await synced;
  expect(response.ok(), `List HTTP ${response.status()} while synchronizing search`).toBeTruthy();

  const filtered = page.waitForResponse(response => isListResponse(response, title));
  await search.fill(title);
  response = await filtered;
  expect(response.ok(), `List HTTP ${response.status()} while searching ${title}`).toBeTruthy();

  const row = page.locator('tbody').getByRole('button', { name: title });
  await expect(row).toBeVisible();
  await row.click();
  await expect(page.getByRole('heading', { name: title, exact: true })).toBeVisible();
}
export async function form(page: Page, title: string) {
  const panel = page.locator('details').filter({ has: page.locator('summary', { hasText: title }) });
  await expect(panel).toHaveCount(1);
  if (await panel.getAttribute('open') === null) await panel.locator('summary').click();
  return panel;
}
export async function submit(page: Page, panel: Locator, path: string, method = 'POST') {
  const pending = page.waitForResponse(r => new URL(r.url()).pathname === `/api/v3/${path}` && r.request().method() === method);
  await panel.getByRole('button', { name: 'Enregistrer', exact: true }).click();
  return value(await pending);
}
export async function seedWork(page: Page, token: string, kind = 'tasks') {
  const title = unique(kind);
  const data = kind === 'tasks' ? taskInput(title) : { title, label: '1.11' };
  return value(await api(page, token, kind, 'POST', data));
}
