# Acceptance diagnostics hardening

This overlay hardens N14 backup/restore acceptance after a real run stopped with only a generic `RuntimeError`.

Changes:
- Docker failures now include the exit code plus redacted command output instead of discarding stderr.
- N14 records the exact backup/restore stage that failed.
- The temporary restore database is created from PostgreSQL `template0` for a clean restore target.
- Secrets remain redacted from diagnostic evidence.

No production database is targeted. Backup/restore remains confined to the validated `orgo-test-postgres` container and temporary `orgo_restore_validation_*` databases.
