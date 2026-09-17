# LevelUpDiag overlay — Browser credentials from Orgo .env

- Reads `ORGO_ADMIN_PASSWORD` from the selected Orgo repository `.env`.
- Prefills **Test password** in memory only.
- Also uses `ORGO_ADMIN_EMAIL` and `ORGO_ORGANIZATION` as matching browser defaults when present.
- Does not write these secrets to `levelupdiag.config.json`, `levelupdiag.config.local.json`, or effective reports.
- A non-empty manual Browser settings password remains an in-session override for the same target.
- Switching target repositories reloads browser defaults from the new target `.env`.
