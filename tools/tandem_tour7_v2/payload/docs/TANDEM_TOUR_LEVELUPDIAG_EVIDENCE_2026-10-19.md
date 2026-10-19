# kOA Tandem 1.0 — Tournée 7/8 — Preuves OrgoDiag indépendantes

## Constat dans le snapshot (2026-10-18)

Le diagnostic existe déjà comme application **séparée** du dépôt Orgo. Il possède
les niveaux N00–N16, les campagnes `baseline`, `standard`, `deep`, `database`,
`acceptance`, `browser`, `embedded`, `ecosystem`, et les résultats Nxx durables.
Les niveaux N11/N14/N15/N16 peuvent nécessiter PostgreSQL, Docker, navigateur,
services et/ou réseau. **Ne pas déclencher ces campagnes pendant l'installation.**

**Écart confirmé** : avant ce lot, `verify-run` acceptait la forme d'un
`summary.json` sans ouvrir les rapports Nxx, sans comparer leurs empreintes,
sans recalculer le verdict et sans vérifier l'identité de la cible.

## Correction locale

- Une campagne nouvelle lie chaque rapport `levels/Nxx/result.json` par
  `evidence_integrity.files[chemin] = sha256` dans `runs/<run-id>/summary.json`.
- `verify-run` contrôle chemins canoniques, rapports complets et non liés par
  symlink, schémas, identité de run et cible, statuts, nombres et verdict calculé.
- `target_protection: ERROR`, niveau requis `SKIP/BLOCKED/PARTIAL`, niveau
  optionnel `FAIL` et rapport altéré ne peuvent plus être annoncés `PASS`.
- L'empreinte du **résumé** est affichée après `run`. Enregistrer ce SHA-256 dans
  un registre **extérieur** à la campagne (ex. registre kOA Digital Ecosystem).
- `--expected-summary-sha256` permet ensuite de vérifier cette ancre externe.
  Il ne faut pas recopier aveuglément une empreinte extraite du même lot suspect.

## Commandes non mutantes (PowerShell 7)

À partir de `C:\mycode\Orgo\LevelUpDiag-Orgo` (racine contenant `levelupdiag.py`) :

```powershell
python -m unittest discover -s tests -v
python levelupdiag.py list
python levelupdiag.py --target 'C:\mycode\Orgo\Orgo' run baseline
# Copier le chemin exact "Report:" et le SHA-256 affichés.
python levelupdiag.py verify-run '.levelupdiag\runs\<RUN_ID>\summary.json'
python levelupdiag.py verify-run '.levelupdiag\runs\<RUN_ID>\summary.json' --expected-summary-sha256 '<SHA256_ANCRE_EXTERNE>'
```

Le mode `baseline` est une lecture du dépôt cible, sans exécution de ses
validateurs applicatifs. `standard`, `deep`, `database`, `acceptance` et
`ecosystem` nécessitent une planification et des environnements dédiés.
Il ne faut **pas** re-jouer l'import ou le scénario E2E FakePlant pour obtenir
un rapport; les preuves déjà existantes se conservent séparément.

## Limites de confiance et de compatibilité

- **SHA-256 ne signe rien.** Quelqu'un pouvant réécrire le résumé ET les rapports
  peut recalculer les empreintes. L'**ancre externe** indépendante est requise
  pour détecter une modification après publication; une autorisation de release
  attend une signature Ed25519 et l'admission KonnaxionDiag/Capsule Agent.
- Les anciens dossiers `verification/embedded` et `.levelupdiag/latest` sont
  utiles comme historique/confort mais **ne constituent pas une preuve strictement
  vérifiable** au nouveau format. Ne pas leur attribuer un PASS cryptographique.
- Une preuve intègre peut conserver le verdict `WARN`, `BLOCKED` ou `FAIL`.
  Vérifier l'intégrité ne signifie pas que l'application cible est qualifiée.
- Le diagnostic sur source locale ne prouve pas que le VPS exécute ces sources.
  Qualifier séparément le runtime et ses dépendances.

## Résultats de qualification du lot

- Suite autonome du snapshot après correctif : **95 tests Python passés**
  (76 tests initiaux + 19 tests de vérification dont tests de portabilité Windows).
- Campagne `baseline` sur un **dossier Orgo fictif** séparé : `WARN` attendu;
  les 6 rapports ont été revérifiés sur disque, verdict `WARN` conservé.
- Aucune campagne profonde, aucun PostgreSQL, aucun Docker, aucun Playwright,
  aucun tenant ni donnée FakePlant n'ont été exécutés ou modifiés ici.

**État de tournée 7/8 : correctif à installer localement; preuves réelles
Orgo encore à collecter pendant la qualification intégrée.**

### Erratum V2 (Windows)
Les chemins des rapports sont sérialisés avec `canonical_level_result_path()` (séparateur `/`) indépendamment de Windows/Linux. Le vérificateur continue de refuser les chemins non canoniques.
