# Overlay — Orgo .env + persistent TEST_DATABASE_URL

This overlay keeps database configuration deterministic without weakening the native test-database guard.

- Reads `Orgo/.env` in memory for `DATABASE_URL` / `POSTGRES_PASSWORD` discovery.
- Never copies Orgo database secrets into LevelUpDiag JSON or reports.
- Adds the documented disposable `orgo_test` URL to `levelupdiag.config.json`.
- Prefills the desktop Test database URL field from configuration.
- Native `database`, `deep`, and `acceptance` campaigns automatically use the configured test URL when the process environment does not already define `TEST_DATABASE_URL`.
- Direct CLI campaigns receive the same configured test URL.
- `DATABASE_URL` is never used as a fallback for native test campaigns.

Apply by merging this archive into `C:\mycode\Orgo\LevelUpDiag-Orgo` and replacing matching files.
