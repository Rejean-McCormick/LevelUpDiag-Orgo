# Upgrade Ariane_Diagnostics → LevelUpDiag Universal Frame

## Décision

On ne jette pas Ariane_Diagnostics. On garde son frame :

- dépôt diagnostics autonome ;
- wrapper GUI ;
- manifest central ;
- niveaux `.pyw` séparés ;
- noyau partagé pour éviter la duplication ;
- launchers `.bat` optionnels.

L’upgrade consiste à rendre le frame universel :

- remplacer les constantes Ariane hardcodées par une config centrale ;
- remplacer `.ariane-control` par `.levelupdiag` ;
- remplacer `ariane_diag_manifest.json` par `levelupdiag_manifest.json` ;
- remplacer `ariane_diag_core` par `levelupdiag_core` ;
- garder `/levels` comme seule zone normalement modifiée pour une nouvelle app.

## Ce qu’on garde

Le modèle existant a déjà les bons blocs : manifest, wrapper, core, scripts, launchers et levels. Le point important à préserver est que le wrapper ne doit pas importer les fichiers de `levels/`; il doit les lancer comme processus séparés.

## Ce qu’on change

### Avant

```text
ARIANE_TARGET_REPO_ROOT
ARIANE_BACKEND_URL
ARIANE_FRONTEND_URL
.ariane-control/
ariane_diag_manifest.json
ariane_diag_core/
```

### Après

```text
LEVELUPDIAG_TARGET_REPO_ROOT
LEVELUPDIAG_BACKEND_URL
LEVELUPDIAG_FRONTEND_URL
.levelupdiag/
levelupdiag_manifest.json
levelupdiag_core/
levelupdiag.config.local.json
```

## Nouvelle règle centrale

Aucun niveau ne doit hardcoder les paramètres locaux suivants :

- racine du repo cible ;
- backend URL ;
- frontend URL ;
- commandes start/build/test ;
- routes critiques ;
- endpoints health/openapi ;
- budgets de performance ;
- dossiers d’artefacts.

Tous ces paramètres doivent venir de `levelupdiag.config.local.json` via `load_config()`.

## Portage d’un niveau Ariane

1. Remplacer les constantes locales par :

```python
from levelupdiag_core.config import load_config
config = load_config()
```

2. Remplacer :

```python
ROOT_DEFAULT = r"C:\mycode\Ariane\Ariane"
BACKEND_URL_DEFAULT = "http://127.0.0.1:8000"
FRONTEND_URL_DEFAULT = "http://localhost:5173"
```

par :

```python
config.target_root_path
config.backend_url
config.frontend_url
```

3. Remplacer les chemins `.ariane-control/...` par :

```python
config.artifacts_root_path
```

4. Laisser la logique métier dans `/levels`.

## Résultat visé

Pour une nouvelle app, on ne modifie normalement que :

```text
levelupdiag.config.local.json
levels/08-critical_ux_flows.pyw
levels/15-real_world_sandbox.pyw
```

Et parfois :

```text
levels/04-api_contract.pyw
levels/07-routing.pyw
levels/13-security.pyw
```

Le reste devient un frame stable.
