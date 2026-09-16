# LevelUpDiag-Orgo desktop console (English)

Apply this overlay to the standalone LevelUpDiag-Orgo application:
C:\mycode\Orgo\LevelUpDiag-Orgo

Orgo repository (preconfigured default):
C:\mycode\Orgo\Orgo

Merge the archive contents into the diagnostic folder, replacing matching files.
Do not copy anything into Orgo. Requires the standalone Orgo diagnostic overlay
(version 1.2). This archive includes the desktop interface and updated base configuration.
An existing levelupdiag.config.local.json remains untouched and takes precedence;
if it contains another target, select the correct Orgo folder and click Save settings.

## Start

Double-click RUN_ORGO_UI.bat in the diagnostic folder, or use PowerShell:

```powershell
cd "C:\mycode\Orgo\LevelUpDiag-Orgo"
py -3 LEVELUPDIAG_CONSOLE.pyw
```

Python 3.10+ with Tcl/Tk is required. Node.js 22+ and Orgo's dependencies must already
be installed. The console does not install software.

## What is a test database?

A separate, disposable PostgreSQL database for migration and integration tests.
Never use production or a database containing useful data: tests write fixtures,
and migrations may change or remove tables.

- **quick**: no test database URL needed. Generates Prisma, checks architecture
  and types, and runs unit tests.
- **embedded**: no test database URL needed. Creates its own temporary PGlite
  database. This does not prove native PostgreSQL concurrency behavior.
- **database / deep / acceptance**: require a native PostgreSQL test database
  that you create yourself, for example orgo_test.

Example URL (replace the credentials):

```text
postgresql://USER:PASSWORD@localhost:5432/orgo_test?connection_limit=5
```

The shipped LevelUpDiag configuration now contains the documented local `orgo_test` URL, so the masked field is prefilled. You can still override it in the field for one run, or set TEST_DATABASE_URL before starting the console:

```powershell
$env:TEST_DATABASE_URL = 'postgresql://USER:PASSWORD@localhost:5432/orgo_test?connection_limit=5'
py -3 LEVELUPDIAG_CONSOLE.pyw
```

The default test URL lives in `levelupdiag.config.json`. A manually typed override stays in memory only. `TEST_DATABASE_URL` from the process environment can also be used. Orgo `.env` is read in memory for normal Orgo database settings, but `DATABASE_URL` is never reused as the native test database. The “What is a test database?” button explains this in the interface.

## Run and review

1. Confirm the Orgo repository path.
2. Enable “Allow generation, tests and builds” to run quick or embedded.
3. Enable native PostgreSQL / network audit only for campaigns that require it.
4. Choose the campaign and click Run campaign. This also saves the displayed
   repository and permission settings, but never the database URL.
5. Select a completed run, then a level, to inspect its verdict and evidence.

Campaigns run in the background. Only one campaign can run from this window at a time.
Wait for completion before closing it. The activity bar is not a percentage.
The log displays launcher messages; completed verdicts are loaded when the run ends.
The history shows the 40 most recent campaigns and their target paths.

Reports remain in:
C:\mycode\Orgo\LevelUpDiag-Orgo\.levelupdiag

No diagnostic code is installed in Orgo. Authorized generation/build/test commands
can still write their own outputs and test fixtures in the target environment.

## Validation

Configuration, report path confinement and campaign selection have automated tests.
Python compilation is checked. Native Windows visual acceptance remains local:
Tk cannot be loaded in the preparation environment.
