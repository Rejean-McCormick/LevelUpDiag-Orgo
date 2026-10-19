# Result and campaign model

Each level writes:

```text
.levelupdiag/runs/<run-id>/levels/<level-id>/result.json
```

A campaign writes:

```text
.levelupdiag/runs/<run-id>/summary.json
.levelupdiag/runs/<run-id>/summary.txt
```

`latest/` contains convenience copies and does not replace history.

Campaign aggregation rules:

1. diagnostics/config errors cannot become target success;
2. any executed target `FAIL` makes the campaign `FAIL`;
3. required `SKIP`, `BLOCKED`, `PARTIAL`, or `INFRA_ERROR` makes evidence incomplete (`BLOCKED`);
4. equivalent statuses on optional levels degrade to `WARN`;
5. `WARN` remains accepted but visible;
6. missing results are never final evidence.

A level's `required` flag affects completeness, not whether an observed `FAIL` matters. An optional level that actually executes and finds a target failure is still a failure.

## Tournée Tandem 7/8 — Vérification de l'intégrité (2026-10-19)

Les nouvelles campagnes enregistrent `evidence_integrity` dans le `summary.json`
**du run** avec le SHA-256 exact de chaque `levels/<id>/result.json`.
`verify-run` relit tous les rapports, reconstitue le verdict, vérifie cible,
run_id, nombres et `target_protection`, et refuse toute preuve manquante ou altérée.
Une preuve d'intégrité **n'est pas** une attestation signée.

Utiliser `python levelupdiag.py verify-run <runs/run-id/summary.json>` puis
épingler le `Summary SHA-256` dans un registre indépendant. Le contrôle
`--expected-summary-sha256` valide cette ancre lors de la relecture.
Les copies sous `latest/` et les anciennes preuves sans `evidence_integrity`
ne sont pas acceptées comme nouvelles preuves qualifiées.
Voir `docs/TANDEM_TOUR_LEVELUPDIAG_EVIDENCE_2026-10-19.md`.
