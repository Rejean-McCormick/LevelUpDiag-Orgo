# LevelUpDiag Config Reference

Fichier : `levelupdiag.config.local.json`

## Champs principaux

- `app_name` : nom affiché dans les rapports.
- `target_repo_root` : racine de l’app cible.
- `backend_url` : URL backend locale.
- `frontend_url` : URL frontend locale.
- `control_dir` : dossier local généré dans l’app cible.
- `artifacts_dir` : dossier des rapports.

## `commands`

Commandes locales appelables par les niveaux :

```json
{
  "backend_start": "uv run myapp serve-api",
  "frontend_start": "pnpm -C frontend dev",
  "lint": "pnpm -C frontend lint",
  "typecheck": "pnpm -C frontend typecheck",
  "test": "pytest",
  "build": "pnpm -C frontend build"
}
```

## `routes`

```json
{
  "smoke": ["/"],
  "critical": ["/", "/dashboard", "/settings"]
}
```

## `api`

```json
{
  "health_paths": ["/health", "/healthz", "/readyz"],
  "openapi_paths": ["/openapi.json"]
}
```

## Overrides temporaires

Variables d’environnement supportées :

```text
LEVELUPDIAG_CONFIG
LEVELUPDIAG_TARGET_REPO_ROOT
LEVELUPDIAG_BACKEND_URL
LEVELUPDIAG_FRONTEND_URL
LEVELUPDIAG_APP_NAME
```
