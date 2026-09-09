# Vérification de l'adaptation autonome

Cet overlay s'applique au snapshot LevelUpDiag fourni, dans sa copie séparée.
Il ne contient aucun fichier de production Orgo ni modification de ses tests.
Il remplace l'approche d'installation dans Orgo proposée précédemment.

Vérifications exécutées le 9 septembre 2026 :

- 26 tests Python du diagnostic : réussis, notamment séparation des dossiers,
  confinement des rapports, refus d'une cible implicite et respect des politiques.
- Campagne embedded depuis LevelUpDiag vers le dossier Orgo séparé : WARN attendu.
- Prisma, architecture et types : PASS.
- 3 tests de l'adaptateur npm et 13 tests unitaires présents dans Orgo : PASS.
- Intégration sur le dossier Orgo disponible : 33 PASS, 1 SKIP réservé à PostgreSQL natif.
- Rapports enregistrés sous le dossier du diagnostic, pas sous le dossier Orgo.

Les preuves de cette exécution sont incluses dans `verification/`.
Les nombres de tests métier dépendent de la version d'Orgo ciblée ; cet overlay
n'installe pas les trois tests supplémentaires du précédent overlay Orgo.
Windows natif, PostgreSQL natif, builds de production, audit réseau et recette
manuelle ne sont pas certifiés par ces résultats.

Pour réexécuter les tests du diagnostic :

```powershell
python -m unittest discover -s tests -v
```

Les rapports de test se trouvent également côté diagnostic. Pour l'utilisation,
suivre `ORGO_VALIDATION.md`. La configuration locale n'est pas incluse dans le ZIP.
