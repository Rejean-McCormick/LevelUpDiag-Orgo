import { test, expect, Page } from '@playwright/test';
import { login, nav } from './support';

const CASES = [
  'Résonance danse / texte manuscrit',
  'Deux vidéos d’incarnation Réjean / King Klown',
  'Alerte publique contextuelle',
  'Pacte de gouvernance Kristal Farms',
  'Fonds commun kOA',
];
const TASKS = [
  'Documenter les deux sources et la chronologie',
  'Tester correspondances, non-correspondances et contrôles',
  'Formuler l’hypothèse de résonance de Pi',
  'Formaliser le mécanisme abstrait de superposition',
  'Vérifier la limite entre interprétation et affirmation',
  'Concevoir les deux chorégraphies',
  'Préparer publication et traçabilité',
  'Cadre éthique et explicitation fictionnelle',
  'Analyser réception et apprentissage',
  'Définir la population concernée',
  'Configurer le routage local',
  'Préparer message compréhensible',
  'Évaluer compréhension et faux positifs',
  'Rédiger garde-fous',
  'Cartographier dépendances opérationnelles',
  'Cartographier financement et risques de capture',
  'Proposer mécanisme financier',
  'Définir limites et conflits',
  'Créer workflow de décision/exécution',
];

async function ecosystemLogin(page: Page) {
  await page.goto('/');
  const auto = await page.request.post(new URL('/api/v3/auth/local-auto-login', page.url()).toString());
  if (auto.ok()) {
    await page.reload();
    await expect(page.getByRole('navigation', { name: 'Navigation Orgo' })).toBeVisible();
    return;
  }
  await login(page);
}

async function visibleTitles(page: Page, label: string, endpoint: string, titles: string[]) {
  await nav(page, label);
  const search = page.getByRole('textbox', { name: 'Search this view' });
  for (const title of titles) {
    const pending = page.waitForResponse(r => {
      const u = new URL(r.url());
      return r.request().method() === 'GET' && u.pathname === `/api/v3/${endpoint}` && u.searchParams.get('search') === title;
    });
    await search.fill(title);
    expect((await pending).ok(), `Search failed for ${title}`).toBeTruthy();
    await expect(page.locator('tbody').getByRole('button', { name: title })).toBeVisible();
  }
}

test('Konvergence seed is visible in Orgo', async ({ page }) => {
  await ecosystemLogin(page);
  await visibleTitles(page, 'Cases', 'cases', CASES);
  await visibleTitles(page, 'Tasks', 'tasks', TASKS);
  await nav(page, 'Cases');
  await page.getByRole('textbox', { name: 'Search this view' }).fill(CASES[0]);
  await expect(page.locator('tbody').getByRole('button', { name: CASES[0] })).toBeVisible();
  const screenshot = process.env.ORGO_ECOSYSTEM_SCREENSHOT;
  if (screenshot) await page.screenshot({ path: screenshot, fullPage: true });
});
