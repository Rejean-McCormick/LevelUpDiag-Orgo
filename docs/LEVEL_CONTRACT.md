# Contrat d’un niveau LevelUpDiag

Un niveau est un fichier `.pyw` autonome dans `levels/`.

Il doit :

1. lire la config centrale avec `load_config()` ou via `run_level_app()` ;
2. produire des findings structurés ;
3. écrire un rapport JSON/TXT ;
4. éviter les effets destructifs par défaut ;
5. rester lançable seul par double-clic ou via `scripts/run_level.py`.

## Format de finding

```python
report.add(
    "api.openapi.fetch",
    PASS,
    "api",
    "OpenAPI disponible",
    endpoint="/openapi.json",
    recommendation="..."
)
```

## Verdicts

```text
PASS          valide
WARN          non bloquant
FAIL          bloquant
SKIP          volontairement non exécuté
BLOCKED       impossible à cause d’un prérequis
PARTIAL       incomplet mais utile
ERROR         bug dans le niveau
INFRA_ERROR   outil/service indisponible
CONFIG_ERROR  config locale invalide
```
