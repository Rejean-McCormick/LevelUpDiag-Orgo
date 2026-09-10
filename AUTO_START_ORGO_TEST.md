# Start Orgo test from LevelUpDiag

Extract this cumulative overlay into `C:\mycode\Orgo\LevelUpDiag-Orgo`.
Replace matching files, then reopen `LEVELUPDIAG_CONSOLE.pyw`.
No changes to the Orgo source repository are included.

## Daily use

1. Open Docker Desktop and wait for its engine to be ready.
2. Double-click `LEVELUPDIAG_CONSOLE.pyw`.
3. Click **Start Orgo test**. Wait for the runtime status to say ready.
4. Select `browser` and fill **Browser settings** using your existing seeded
   account (`orgo-e2e`, `e2e@example.test`, and its password).
5. Confirm test-instance writes, enable the existing execution/network
   checkboxes, and click **Run campaign**.
6. When the campaign is finished, click **Stop Orgo test** before closing.

The console starts the existing `orgo-test-postgres` container, then the API
on 4000 and frontend on 3000. It pins the API database to the documented local
`orgo_test` setup (user/password `orgo_test`, port 5432). Frontend requests are
proxied to that API. Readiness is checked over HTTP, including API database
readiness. A occupied API/web port blocks startup: close previously opened
manual Orgo processes first. The runtime does not reuse unknown servers.

**Runtime logs** opens `runtime-logs/<startup-id>/` with separate API and web
logs. Keep logs private. The window stays responsive during startup/shutdown.
The stop button cancels startup when necessary, and is disabled while a
diagnostic campaign is running.

## One-time prerequisites

Docker Desktop, the already created test container, Node.js, installed Orgo
dependencies/generated Prisma client/migrations, the seeded test account, and
installed Playwright/Chromium are still required. This upgrade does not create
containers, install packages, migrate schemas or change account passwords.
It does not launch Docker Desktop itself. See `PLAYWRIGHT_ORGO.md` for setup.

The runtime starts API and web directly using the repository's tsx and Next
CLIs, without needing separate terminal windows. It does not start the worker;
the seven existing browser tests do not cover worker-driven processing.

Stopping terminates only processes owned by this console (including their
child processes on Windows). It does not stop PostgreSQL or remove its data.
Do not run destructive native integration fixtures while using this test UI.

## Verification

13 support tests passed: five existing desktop tests, three browser settings
tests and five runtime tests. Python syntax compilation passed. Actual Windows
process startup, live API/database readiness and browser journeys require local
execution. A green support suite is not evidence that browser acceptance passed.
