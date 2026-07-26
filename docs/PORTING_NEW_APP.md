# Adapter LevelUpDiag à une nouvelle app

## Étape 1 — Copier le frame

Copier le dossier diagnostics dans un dépôt séparé, par exemple :

```text
C:\mycode\MyApp\MyApp_Diagnostics
```

## Étape 2 — Modifier la config locale

Éditer :

```text
levelupdiag.config.local.json
```

Renseigner :

- `app_name`
- `target_repo_root`
- `backend_url`
- `frontend_url`
- `commands`
- `routes`
- `api.health_paths`
- `api.openapi_paths`

## Étape 3 — Lancer les niveaux génériques

```bat
py scriptsun_level.py N01 --wait
py scriptsun_level.py N02 --wait
py scriptsun_level.py N03 --wait
py scriptsun_level.py N04 --wait
```

## Étape 4 — Adapter les niveaux métier

Modifier seulement les fichiers nécessaires dans `levels/` :

- `08-critical_ux_flows.pyw`
- `09-error_resilience.pyw`
- `15-real_world_sandbox.pyw`

## Étape 5 — Release gate

```bat
py scriptsun_level.py N14 --wait
```
