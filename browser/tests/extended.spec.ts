import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { api, form, id, login, nav, openWork, profile, seedWork, submit, taskInput, unique, value } from './support';

test('E01 edit a task and reject a stale revision', async ({ page }) => {
  const { token } = await login(page);
  const task = await seedWork(page, token);
  await openWork(page, 'Tâches', task.title);
  const edit = await form(page, 'Modifier le travail');
  const title = unique('edited');
  await edit.getByLabel('Titre', { exact: true }).fill(title);
  await submit(page, edit, `tasks/${id(task)}`, 'PATCH');
  await expect(page.getByRole('heading', { name: title, exact: true })).toBeVisible();
  const stale = await api(page, token, `tasks/${id(task)}`, 'PATCH', { title: 'STALE', revision: task.revision });
  expect(stale.status()).toBe(409);
  const saved = await value(await api(page, token, `tasks/${id(task)}`));
  expect(saved.title).toBe(title);
});

test('E02 create a linked task from a case and navigate back', async ({ page }) => {
  const { token } = await login(page);
  const parent = await seedWork(page, token, 'cases');
  await openWork(page, 'Dossiers', parent.title);
  await page.locator('aside.detail').getByRole('button', { name: '+ Ajouter', exact: true }).click();
  const panel = page.getByRole('region', { name: 'Créer un élément' });
  const title = unique('linked');
  await panel.getByLabel('Titre', { exact: true }).fill(title);
  await expect(panel.getByLabel('Dossier associé (identifiant, facultatif)')).toHaveValue(id(parent));
  const pending = page.waitForResponse(r => r.url().endsWith('/api/v3/tasks') && r.request().method() === 'POST');
  await panel.getByRole('button', { name: 'Créer', exact: true }).click();
  const child = await value(await pending);
  expect(child.case_id).toBe(id(parent));
  await page.locator('aside.detail').getByRole('button', { name: title }).click();
  await expect(page.getByRole('heading', { name: title, exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Ouvrir le dossier associé ↗' }).click();
  await expect(page.getByRole('heading', { name: parent.title, exact: true })).toBeVisible();
});

test('E03 add a comment and display markup as plain text', async ({ page }) => {
  const { token } = await login(page);
  const task = await seedWork(page, token);
  await openWork(page, 'Tâches', task.title);
  const text = `<img src=x onerror="window.orgoInjected=true"> ${unique('comment')}`;
  await page.getByLabel('Ajouter un commentaire').fill(text);
  const pending = page.waitForResponse(r => r.url().endsWith('/comments') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Commenter', exact: true }).click();
  await value(await pending);
  await expect(page.locator('.comment').filter({ hasText: text })).toBeVisible();
  expect(await page.evaluate(() => (window as any).orgoInjected)).toBeUndefined();
  expect((await value(await api(page, token, `tasks/${id(task)}`))).comments.some((c: any) => c.body === text)).toBe(true);
});

test('E04 assign a task to the current user and find it in My Work', async ({ page }) => {
  const { token, context } = await login(page);
  const task = await seedWork(page, token);
  await openWork(page, 'Tâches', task.title);
  await page.locator('aside.detail select[name="owner"]').selectOption(context.actorUserId);
  const pending = page.waitForResponse(r => r.url().endsWith('/assignment') && r.request().method() === 'PATCH');
  await page.getByRole('button', { name: 'Attribuer', exact: true }).click();
  await value(await pending);
  await profile(page, 'My Work');
  await openWork(page, 'Mon travail', task.title);
  const mine = await value(await api(page, token, `tasks?mine=true&search=${encodeURIComponent(task.title)}`));
  expect(mine.items.some((item: any) => id(item) === id(task))).toBe(true);
  expect((await value(await api(page, token, `tasks/${id(task)}`))).owner_user_id).toBe(context.actorUserId);
});

test('E05 upload download and remove an attachment', async ({ page }) => {
  const { token } = await login(page);
  const task = await seedWork(page, token);
  await openWork(page, 'Tâches', task.title);
  const filename = `${unique('file')}.txt`;
  const content = Buffer.from('Orgo attachment: café\nVerified bytes.');
  const pending = page.waitForResponse(r => r.url().endsWith('/attachments') && r.request().method() === 'POST');
  await page.getByLabel('Ajouter un fichier (1 Mio maximum)').setInputFiles({ name: filename, mimeType: 'text/plain', buffer: content });
  const attachment = await value(await pending);
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: `${filename} (${content.length} octets)`, exact: true }).click();
  const file = await download;
  expect(file.suggestedFilename()).toBe(filename);
  expect(await readFile((await file.path())!)).toEqual(content);
  const removed = page.waitForResponse(r => r.url().endsWith(`/attachments/${id(attachment)}`) && r.request().method() === 'DELETE');
  await page.getByRole('button', { name: `Retirer ${filename}`, exact: true }).click();
  await value(await removed);
  await expect(page.getByRole('button', { name: `Retirer ${filename}`, exact: true })).toHaveCount(0);
  expect((await api(page, token, `attachments/${id(attachment)}`)).status()).toBe(404);
});

test('E06 reject an oversized attachment without persisting it', async ({ page }) => {
  const { token } = await login(page);
  const task = await seedWork(page, token);
  await openWork(page, 'Tâches', task.title);
  await page.getByLabel('Ajouter un fichier (1 Mio maximum)').setInputFiles({ name: 'oversized.txt', mimeType: 'text/plain', buffer: Buffer.alloc(1048577, 65) });
  await expect(page.locator('.evidence').getByRole('alert')).toHaveText('Le fichier dépasse 1 Mio.');
  expect(await value(await api(page, token, `work/task/${id(task)}/attachments`))).toEqual([]);
});

test('E07 publish immutable workflow versions and simulate without effects', async ({ page }) => {
  const { token } = await login(page);
  await profile(page, 'Workflow Admin');
  const code = unique('workflow').toLowerCase();
  const generatedTitle = unique('simulation');
  const rules = { rules: [{ id: 'create', enabled: true, match: { source: 'API' }, actions: [{ type: 'CREATE_TASK', input: taskInput(generatedTitle) }] }] };
  await page.getByLabel('Code', { exact: true }).fill(code);
  await page.getByLabel('Règles (JSON)').fill(JSON.stringify(rules));
  const publish = async () => {
    const pending = page.waitForResponse(r => r.url().endsWith(`/workflows/${code}/versions`) && r.request().method() === 'POST');
    await page.getByRole('button', { name: 'Publier la version', exact: true }).click();
    return value(await pending);
  };
  const first = await publish();
  expect(first.version).toBe(1);
  rules.rules[0].id = 'create-v2';
  await page.getByLabel('Règles (JSON)').fill(JSON.stringify(rules));
  expect((await publish()).version).toBe(2);
  const block = page.locator('section').filter({ has: page.getByRole('heading', { name: 'Versions publiées', exact: true }) });
  // Direct child of the versions panel is the definition, not all ancestor divs.
  const versionBlock = block.locator(':scope > div').filter({ has: page.getByRole('heading', { name: code, exact: true }) });
  await expect(versionBlock.getByRole('button', { name: 'Simuler', exact: true })).toHaveCount(2);
  const simulation = page.waitForResponse(r => r.url().endsWith('/simulate') && r.request().method() === 'POST');
  await versionBlock.getByRole('button', { name: 'Simuler', exact: true }).first().click();
  const output = await value(await simulation);
  expect(output.actions).toHaveLength(1);
  await expect(page.getByRole('heading', { name: 'Simulation sans effet', exact: true })).toBeVisible();
  const definitions = await value(await api(page, token, 'workflows'));
  const original = definitions.find((w: any) => w.code === code).versions.find((v: any) => v.id === first.id);
  expect(original.content.rules[0].id).toBe('create');
  expect((await value(await api(page, token, `tasks?search=${encodeURIComponent(generatedTitle)}`))).total).toBe(0);
});

test('E08 invalid workflow JSON shows an error without publication', async ({ page }) => {
  const { token } = await login(page);
  await profile(page, 'Workflow Admin');
  const code = unique('invalid').toLowerCase();
  await page.getByLabel('Code', { exact: true }).fill(code);
  await page.getByLabel('Règles (JSON)').fill('{invalid');
  await page.getByRole('button', { name: 'Publier la version', exact: true }).click();
  await expect(page.locator('form').filter({ has: page.getByLabel('Règles (JSON)') }).getByRole('alert')).toBeVisible();
  expect((await value(await api(page, token, 'workflows'))).some((w: any) => w.code === code)).toBe(false);
});

test('E09 queue offline work and replay it exactly once', async ({ page, context }) => {
  const { token } = await login(page);
  await nav(page, 'Hors ligne');
  const panel = await form(page, 'Préparer une commande hors ligne');
  const title = unique('offline');
  await panel.getByLabel('Titre', { exact: true }).fill(title);
  try {
    await context.setOffline(true);
    await panel.getByRole('button', { name: 'Enregistrer', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Retirer de la file', exact: true })).toHaveCount(1);
  } finally { await context.setOffline(false); }
  const replay = page.waitForResponse(r => r.url().endsWith('/sync/replay') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Synchroniser', exact: true }).click();
  const result = await value(await replay);
  expect(result.results).toHaveLength(1);
  expect(result.results[0].ok).toBe(true);
  await expect(page.getByRole('button', { name: 'Retirer de la file', exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: 'Synchroniser', exact: true }).click();
  expect((await value(await api(page, token, `tasks?search=${encodeURIComponent(title)}`))).total).toBe(1);
  await openWork(page, 'Tâches', title);
});

test('E10 download a task CSV with spreadsheet-safe content', async ({ page }) => {
  const { token } = await login(page);
  const title = `=1+1 ${unique('csv')}`;
  await value(await api(page, token, 'tasks', 'POST', taskInput(title)));
  await profile(page, 'Supervisor');
  await nav(page, 'Rapports');
  const pending = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Exporter', exact: true }).click();
  const download = await pending;
  expect(download.suggestedFilename()).toBe('orgo-tasks.csv');
  const csv = await readFile((await download.path())!, 'utf8');
  expect(csv).toContain(title);
  expect(csv).toContain(`'${title}`);
});

test('E11 create a read-only user and enforce permissions in UI and API', async ({ page, browser }) => {
  const { token } = await login(page);
  const task = await seedWork(page, token);
  await profile(page, 'Full Control Panel');
  await nav(page, 'Accès');
  const email = `${unique('reader').toLowerCase()}@example.test`, password = unique('password');
  const userForm = await form(page, 'Créer un compte');
  await userForm.getByLabel('Courriel', { exact: true }).fill(email);
  await userForm.getByLabel('Nom affiché', { exact: true }).fill(email);
  await userForm.getByLabel('Mot de passe', { exact: true }).fill(password);
  const user = await submit(page, userForm, 'users');
  const roleForm = await form(page, 'Créer un rôle');
  await roleForm.getByLabel('code', { exact: true }).fill(unique('reader').toLowerCase());
  await roleForm.getByLabel('Nom affiché', { exact: true }).fill('E2E read-only');
  await roleForm.getByLabel(/^Permissions/).fill('["work:read"]');
  const role = await submit(page, roleForm, 'roles');
  await page.locator('tbody').getByRole('button', { name: email, exact: true }).click();
  const assign = await form(page, 'Attribuer des rôles');
  await assign.getByLabel(/^Rôles/).fill(JSON.stringify([role.id]));
  await submit(page, assign, `users/${user.id}/roles`, 'PUT');
  const isolated = await browser.newContext({ baseURL: new URL(page.url()).origin });
  try {
    const reader = await isolated.newPage();
    const session = await login(reader, email, password);
    await openWork(reader, 'Tâches', task.title);
    await expect(reader.getByRole('button', { name: /Nouvelle tâche/ })).toHaveCount(0);
    await expect(reader.getByRole('button', { name: 'En cours', exact: true })).toHaveCount(0);
    expect((await api(reader, session.token, 'tasks', 'POST', taskInput(unique('denied')))).status()).toBe(403);
    // Revoke only this generated account's role; the current token must lose access.
    await value(await api(page, token, `users/${user.id}/roles`, 'PUT', { role_ids: [] }));
    expect((await api(reader, session.token, `tasks/${id(task)}`)).status()).toBe(403);
  } finally { await isolated.close(); }
});

test('E12 scope a reader to one team and hide another team task', async ({ page, browser }) => {
  const { token } = await login(page);
  const team = unique('team'), other = unique('other');
  const user = await value(await api(page, token, 'users', 'POST', { email: `${unique('scope')}@example.test`, display_name: 'E2E scoped', password: 'E2E-scope-only-password-123' }));
  const role = await value(await api(page, token, 'roles', 'POST', { code: unique('scope'), display_name: 'E2E scope', permissions: ['work:read'] }));
  await value(await api(page, token, `identity/users/${user.id}/scopes`, 'POST', { role_id: role.id, scope_type: 'team', scope_reference: team }));
  const inside = await value(await api(page, token, 'tasks', 'POST', { ...taskInput(unique('inside')), access_scope_type: 'team', access_scope_reference: team }));
  const outside = await value(await api(page, token, 'tasks', 'POST', { ...taskInput(unique('outside')), access_scope_type: 'team', access_scope_reference: other }));
  const context = await browser.newContext({ baseURL: new URL(page.url()).origin });
  try {
    const scoped = await context.newPage();
    const session = await login(scoped, user.email, 'E2E-scope-only-password-123');
    await openWork(scoped, 'Tâches', inside.title);
    const pending = scoped.waitForResponse(r => new URL(r.url()).searchParams.get('search') === outside.title);
    await scoped.getByRole('textbox', { name: 'Rechercher dans la vue' }).fill(outside.title);
    expect((await value(await pending)).total).toBe(0);
    await expect(scoped.locator('tbody tr')).toHaveCount(0);
    expect((await api(scoped, session.token, `tasks/${id(outside)}`)).status()).toBe(404);
  } finally { await context.close(); }
});

test('E13 create a maintenance asset and complete its appointment', async ({ page }) => {
  const { token } = await login(page);
  await profile(page, 'Full Control Panel');
  await nav(page, 'Maintenance');
  const panel = await form(page, 'Ajouter un équipement');
  const name = unique('asset');
  await panel.getByLabel('Nom', { exact: true }).fill(name);
  await panel.getByLabel(/^category/).selectOption('request');
  const asset = await submit(page, panel, 'maintenance/assets');
  await expect(page.getByRole('cell', { name, exact: true })).toBeVisible();
  const slot = await form(page, 'Planifier une intervention');
  const title = unique('appointment');
  await slot.getByLabel('Titre', { exact: true }).fill(title);
  await slot.getByLabel('Équipement', { exact: true }).fill(id(asset));
  const created = await submit(page, slot, 'maintenance/calendar');
  const card = page.locator('section').filter({ has: page.getByRole('heading', { name: title, exact: true }) });
  for (const state of ['in_progress', 'completed']) {
    const pending = page.waitForResponse(r => r.url().endsWith(`/maintenance/calendar/${id(created)}/status`) && r.request().method() === 'PUT');
    await card.getByRole('button', { name: state, exact: true }).click();
    expect((await value(await pending)).status).toBe(state);
    await expect(card).toContainText(state);
  }
});

test('E14 create an education group and its support task', async ({ page }) => {
  const { token } = await login(page);
  await profile(page, 'Full Control Panel');
  await nav(page, 'Éducation');
  const panel = await form(page, 'Créer un groupe');
  const name = unique('group');
  await panel.getByLabel('code', { exact: true }).fill(name.toLowerCase());
  await panel.getByLabel('Nom', { exact: true }).fill(name);
  const group = await submit(page, panel, 'education/groups');
  await page.getByRole('button', { name, exact: true }).click();
  const task = await form(page, 'Créer une tâche de soutien');
  const title = unique('support');
  await task.getByLabel('Titre', { exact: true }).fill(title);
  await submit(page, task, 'education/tasks');
  expect((await value(await api(page, token, `tasks?search=${encodeURIComponent(title)}`))).total).toBe(1);
});

test('E15 create a confidential HR case with its work task', async ({ page }) => {
  const { token } = await login(page);
  await profile(page, 'Full Control Panel');
  await nav(page, 'Ressources humaines');
  const panel = await form(page, 'Ouvrir un dossier RH confidentiel');
  const code = unique('hr');
  await panel.getByLabel('Code du dossier', { exact: true }).fill(code);
  await panel.getByRole('group', { name: 'Dossier', exact: true }).getByLabel('Titre', { exact: true }).fill(code);
  await panel.getByRole('group', { name: 'Tâche', exact: true }).getByLabel('Titre', { exact: true }).fill(`${code}-task`);
  await submit(page, panel, 'hr/cases');
  await page.getByRole('button', { name: code, exact: true }).click();
  await expect(page.getByRole('heading', { name: code, exact: true })).toBeVisible();
  expect((await value(await api(page, token, `tasks?search=${encodeURIComponent(code + '-task')}`))).total).toBe(1);
});
