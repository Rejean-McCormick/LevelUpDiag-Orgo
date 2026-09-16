# Configuration reference

Configuration is JSON. `levelupdiag.config.json` is committed. `levelupdiag.config.local.json`, when present, is recursively merged over it.

## Core keys

- `target_repo_root`: `"auto"` means parent of the LevelUpDiag source directory.
- `control_dir`: generated evidence directory relative to target root.
- `execution.max_parallel`: maximum simultaneous process-isolated levels.
- `execution.default_timeout_seconds`: default external command timeout.
- `execution.fail_fast`: stop scheduling new levels after a hard failure.
- `execution.capture_limit_kb`: bound stdout/stderr stored per external command.
- `execution.protect_tracked_files`: compare tracked Git state before and after a campaign.
- `execution.restore_generated_tracked_files`: tracked files that builds may rewrite; LevelUpDiag snapshots and restores their exact pre-campaign bytes before enforcing VCS protection. Default: `apps/web/next-env.d.ts`.
- `execution.allow_target_mutation`: allow validators explicitly marked mutating.
- `execution.allow_network`: allow validators explicitly marked networked.
- `database.target_env_file`: relative Orgo dotenv file read in memory (default `.env`). Only `DATABASE_URL`, `POSTGRES_PASSWORD`, and `TEST_DATABASE_URL` are considered; values are never copied into LevelUpDiag configuration.
- `database.test_database_url`: dedicated disposable PostgreSQL URL used by native `database`, `deep`, and `acceptance` campaigns when `TEST_DATABASE_URL` is not already set in the process environment. It must identify a test/validation database; `DATABASE_URL` is never a fallback.
- `scan.*`: bounded scanner limits and excluded directories.
- `toolchain.required`: tools whose absence blocks Tooling Discovery.
- `toolchain.optional`: informational tools reserved for local extensions.
- `validators`: explicit target validator declarations.
- `security.additional_patterns`: additional regular expressions for hygiene review; never put real secrets here.

## Validator object

```json
{
  "id": "stable-id",
  "name": "Human name",
  "command": ["executable", "arg"],
  "cwd": ".",
  "required": true,
  "timeout_seconds": 300,
  "mutates_target": false,
  "network": false,
  "enabled": true
}
```

Strings are accepted for `command` for convenience, but argument arrays are preferred. Commands are always executed with `shell=False`.

## Managed Orgo test database

The desktop **Reset / Prepare PostgreSQL test** action validates the fixed `orgo-test-postgres` container and recreates only the disposable `orgo_test` database. It does not use Orgo `DATABASE_URL` as a reset target.
