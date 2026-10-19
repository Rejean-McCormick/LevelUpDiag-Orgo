# LevelUpDiag-Orgo — Tournée 7/8 — Correctif V2 Windows

**Cette V2 remplace la V1 échouée sous Windows. Ne pas exécuter les scripts V1.**

La V1 a été refusée avant toute écriture des sources : Windows produisait `levels\\Nxx\\result.json`,
alors que l’admission exige des chemins canoniques `levels/Nxx/result.json`.
La V2 utilise un sérialiseur indépendant du système pour écrire les chemins et
**continue de refuser** les séparateurs Windows, traversées de répertoire et chemins étrangers lors de la vérification.

Extraire tout le ZIP à la racine `C:\mycode\Orgo\LevelUpDiag-Orgo`.
Les anciens lanceurs V1 peuvent rester présents sans être exécutés.

```powershell
cd 'C:\mycode\Orgo\LevelUpDiag-Orgo'
.\PREVIEW_LEVELUPDIAG_TOUR_P1_V2.cmd
.\INSTALL_LEVELUPDIAG_TOUR_P1_V2.cmd
.\VERIFY_LEVELUPDIAG_TOUR_P1_V2.cmd
```

Le rollback explicite utilise `ROLLBACK_LEVELUPDIAG_TOUR_P1_V2.cmd`.
La sauvegarde séparée de la V2 se situe sous :
`C:\mycode\Orgo\Tandem_Local\levelupdiag_tour_p1_v2\backups\`.

* Le manifeste V2 attend les **empreintes originales du snapshot**, car la V1 n’a pas été installée.
* Les 8 fichiers applicatifs de la V1 sont installés avec le correctif additionnel Windows.
* Les scripts ne lancent aucune campagne Orgo, aucun PostgreSQL, Docker, Playwright, service ou VPS.
* Tests dans une copie isolée ; si la suite échoue, installation refusée sans toucher aux sources.
* Les rapports obtenus sont des preuves d’intégrité, **pas des signatures** ou preuves de qualification réelle.
* Si l’installation V2 est interrompue, transmettre la sortie; ne pas supprimer les sauvegardes.

**Validation hors Windows** : suite Python complète, campagne sur cible temporaire,
cycle PREVIEW → INSTALL → VERIFY → INSTALL (idempotent) → ROLLBACK,
et détection de divergence SHA-256. L’exécution native sur Windows sera confirmée
par les sorties de l’installateur sur ton poste.
