# Orgo browser acceptance

Apply this overlay to `C:\mycode\Orgo\LevelUpDiag-Orgo`, not the Orgo repository.
It adds the `browser` campaign (N15), expanded to 22 required journeys.
See `BROWSER_EXTENDED.md` for the full coverage matrix. Existing `deep` and N14 manual acceptance
remain unchanged. Test names and instructions are English; locators match the
French UI present in the supplied Orgo source.

## Install once (PowerShell 7)

```powershell
Set-Location 'C:\mycode\Orgo\LevelUpDiag-Orgo\browser'
npm ci
npx playwright install chromium
```

## Prepare the test application

Use the disposable PostgreSQL container already validated by N11. These tests
create uniquely named records and retain them for diagnosis; they do not delete
existing records. Do not run native integration tests concurrently with browser
tests: integration fixtures may modify the same database.

In terminal A (keep it open):

```powershell
Set-Location 'C:\mycode\Orgo\Orgo'
$env:DATABASE_URL = 'postgresql://orgo_test:orgo_test@127.0.0.1:5432/orgo_test?connection_limit=5'
$env:ORGO_ORGANIZATION = 'orgo-e2e'
$env:ORGO_ADMIN_EMAIL = 'e2e@example.test'
$env:ORGO_ADMIN_PASSWORD = Read-Host 'Choose the test account password (12+ characters)' -MaskInput
npm run db:migrate -w api
npm run db:seed -w api
npm run dev -w api
```

Stop if migration or seed fails. The existing seed does not change a previously
created account password; use its original password on repeat runs.

In terminal B (keep it open):

```powershell
Set-Location 'C:\mycode\Orgo\Orgo'
$env:ORGO_API_URL = 'http://127.0.0.1:4000'
npm run dev -w web
```

In terminal C:

```powershell
Set-Location 'C:\mycode\Orgo\LevelUpDiag-Orgo'
$env:ORGO_E2E_URL = 'http://127.0.0.1:3000'
$env:ORGO_E2E_ORGANIZATION = 'orgo-e2e'
$env:ORGO_E2E_EMAIL = 'e2e@example.test'
$env:ORGO_E2E_PASSWORD = Read-Host 'Enter the same test account password' -MaskInput
$env:ORGO_E2E_ALLOW_WRITES = 'test-instance'
py -3 .\levelupdiag.py --target 'C:\mycode\Orgo\Orgo' run browser
```

LevelUpDiag requires its existing local `execution.allow_network` and
`execution.allow_target_mutation` permissions. The explicit test-instance flag
does not prove which database your running API uses: ensure terminal A uses the
disposable database. Browser target hosts are restricted to loopback.

The desktop interface discovers `browser` from the manifest. To supply its
credentials, launch `py -3 .\LEVELUPDIAG_CONSOLE.pyw` from terminal C after
setting the variables above, then select `browser`.

## Evidence and interactive debugging

Each campaign writes JSON, HTML and failure artifacts under
`browser/runs/<run_id>/`. N15 references those files. All 22 named tests must pass, with zero skips,
zero flaky tests and a successful process are required for PASS. Missing setup
is BLOCKED; zero tests cannot pass.

To debug directly in terminal C (same environment):

```powershell
Set-Location '.\browser'
npm test -- --headed
```

Direct runs write `browser/playwright-report/index.html`; use `npm run report`.
For a campaign HTML report use `npx playwright show-report .\runs\RUN_ID\html`.
Failure traces may include authentication requests and test data. Keep them
private and remove secrets before sharing them.

## Coverage and limits

The original seven journeys are retained. Fifteen additional journeys cover
editing, comments, links, assignments, attachments, workflow publication and
simulation, roles and team scopes, offline replay, CSV, Maintenance, Education
and HR. See `BROWSER_EXTENDED.md` for precise assertions and boundaries.

These are not exhaustive product acceptance. Cross-organization isolation,
worker-driven workflow execution, providers, mobile layout and Koali hosting
still need additional scenarios. The 22 tests were discovered and typechecked;
execution of the expanded suite against your Windows API/database remains local.
