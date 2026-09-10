import { test, expect, Page } from '@playwright/test';
import { randomUUID } from 'node:crypto';

async function login(page: Page, password = process.env.ORGO_E2E_PASSWORD!) {
  await page.goto('/');
  await page.getByLabel('Organisation', { exact: true }).fill(process.env.ORGO_E2E_ORGANIZATION!);
  await page.getByLabel('Adresse courriel').fill(process.env.ORGO_E2E_EMAIL!);
  await page.getByLabel('Mot de passe', { exact: true }).fill(password);
  const response = page.waitForResponse(r => r.url().endsWith('/auth/login') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Se connecter', exact: true }).click();
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
  const form = page.getByRole('region', { name: 'Créer un élément' });
  await form.getByLabel('Titre', { exact: true }).fill(title);
  await form.getByLabel('Description', { exact: true }).fill('Playwright acceptance fixture');
  const pending = page.waitForResponse(r => r.url().endsWith(`/api/v3/${kind}`) && r.request().method() === 'POST');
  await form.getByRole('button', { name: 'Créer', exact: true }).click();
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
  await expect(page.getByRole('textbox', { name: 'Rechercher dans la vue' })).toBeFocused();
  const logout = page.waitForResponse(r => r.url().endsWith('/auth/logout'));
  await page.getByRole('button', { name: 'Se déconnecter' }).click();
  expect((await logout).ok()).toBeTruthy();
  await expect(page.getByRole('button', { name: 'Se connecter', exact: true })).toBeVisible();
  await expect(page.getByRole('navigation')).toHaveCount(0);
});

for (const [kind, label, button] of [
  ['cases', 'Dossiers', 'Nouveau dossier'],
  ['tasks', 'Tâches', 'Nouvelle tâche'],
  ['signals', 'Signaux', 'Nouveau signal'],
]) {
  test(`${kind}: create, search and reopen persisted detail`, async ({ page }) => {
    await authenticated(page);
    await navigate(page, label);
    const title = `E2E-${kind}-${randomUUID()}`;
    await create(page, kind, button, title);
    const searchResponse = page.waitForResponse(r => r.request().method() === 'GET' && new URL(r.url()).searchParams.get('search') === title);
    await page.getByRole('textbox', { name: 'Rechercher dans la vue' }).fill(title);
    expect((await searchResponse).ok()).toBeTruthy();
    await page.getByRole('button', { name: title }).click();
    await expect(page.getByRole('heading', { name: title, exact: true })).toBeVisible();
    // Reload forces another real login and server-side read (tokens live in memory).
    const detailURL = page.url();
    await page.reload();
    await authenticated(page);
    await page.getByRole('navigation').getByRole('button', { name: label, exact: true }).click();
    await page.getByRole('textbox', { name: 'Rechercher dans la vue' }).fill(title);
    await page.getByRole('button', { name: title }).click();
    await expect(page).toHaveURL(detailURL);
    await expect(page.getByRole('heading', { name: title, exact: true })).toBeVisible();
  });
}

test('task lifecycle is persisted by the API', async ({ page }) => {
  await authenticated(page);
  await navigate(page, 'Tâches');
  const title = `E2E-lifecycle-${randomUUID()}`;
  await create(page, 'tasks', 'Nouvelle tâche', title);
  await page.getByRole('textbox', { name: 'Rechercher dans la vue' }).fill(title);
  await page.getByRole('button', { name: title }).click();
  for (const [label, status] of [['En cours', 'IN_PROGRESS'], ['Terminée', 'COMPLETED']]) {
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
  await navigate(page, 'Dossiers');
  const query = `E2E-absent-${randomUUID()}`;
  const pending = page.waitForResponse(r => new URL(r.url()).searchParams.get('search') === query);
  await page.getByRole('textbox', { name: 'Rechercher dans la vue' }).fill(query);
  expect((await pending).ok()).toBeTruthy();
  await expect(page.getByText('Aucun résultat pour cette recherche.', { exact: true })).toBeVisible();
  await expect(page.locator('tbody tr')).toHaveCount(0);
});
