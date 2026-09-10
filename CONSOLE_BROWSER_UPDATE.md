# Browser settings in the existing console

Extract this overlay into `C:\mycode\Orgo\LevelUpDiag-Orgo` and replace the
matching files. It includes the previous Playwright suite and updated console
modules. Keep your local configuration and existing reports.

Double-click `LEVELUPDIAG_CONSOLE.pyw`, select `browser`, then fill the
automatically selected **Browser settings** tab:

- Local Orgo URL: `http://127.0.0.1:3000`
- Test organization: `orgo-e2e`
- Test email: `e2e@example.test`
- Password: the existing seeded test account password
- Confirm the instance is disposable and may receive test records

Enable generation/tests and network execution in the existing checkboxes,
then click **Run campaign**. No PowerShell environment variables are needed.
Browser fields are never written by Save settings. The password is masked,
passed in the browser child process environment, and cleared on closing.
Playwright failure traces may contain credentials; keep them private.

This update launches diagnostics only. Install browser dependencies/Chromium,
seed the test account and start PostgreSQL/API/frontend as described in
`PLAYWRIGHT_ORGO.md`. Do not point the running API at production data.

Validation: browser settings tests and existing desktop service tests run
locally; UI syntax checked. Windows double-click and live browser journeys
must be verified locally. The separate BAT launcher is optional.
