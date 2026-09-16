# LevelUpDiag overlay — disposable DB reset + generated-file VCS restore

This overlay makes **Reset / Prepare PostgreSQL test** recreate only the validated disposable `orgo_test` database inside the fixed `orgo-test-postgres` container before native PostgreSQL campaigns. It never derives the test target from Orgo `DATABASE_URL`.

It also snapshots configured build-generated tracked files before a campaign and restores their exact original bytes afterward. The default list contains `apps/web/next-env.d.ts`, preventing `next build` from creating a false tracked-VCS mutation while preserving any pre-existing user modification.

Safety invariants:
- container name, database, user, password, and localhost port mapping are validated before reset;
- Orgo API/web runtime must be stopped before reset;
- only `orgo_test` is terminated/dropped/recreated;
- production `DATABASE_URL` is never used as a fallback;
- generated-file restoration is path-confined and only snapshots files already tracked by Git.
