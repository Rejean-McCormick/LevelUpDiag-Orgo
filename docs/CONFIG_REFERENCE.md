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
- `execution.allow_target_mutation`: allow validators explicitly marked mutating.
- `execution.allow_network`: allow validators explicitly marked networked.
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
