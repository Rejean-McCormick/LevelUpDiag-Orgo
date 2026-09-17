# Adapter votre copie séparée de LevelUpDiag à Orgo

## Installation de l'overlay

Sauvegarder votre copie de LevelUpDiag, puis y fusionner les fichiers de ce ZIP,
à la racine contenant `levelupdiag.py`. **Ne rien copier dans Orgo.**
Ne pas appliquer le précédent overlay destiné au dépôt Orgo.
Vos autres fichiers et votre configuration locale ne sont pas supprimés.
Comparer les fichiers modifiés localement avant de les remplacer.

L'application contient ses adaptateurs Node dans `adapters/`. Ils invoquent les
scripts npm publics d'Orgo avec son répertoire comme dossier de travail.
Ni `scripts/diag-step.mjs`, ni `scripts/npm-command.mjs` ne sont requis dans Orgo.
Les tests exécutés sont ceux déjà présents dans votre version d'Orgo.

## Premier lancement PowerShell

Depuis votre copie LevelUpDiag-Orgo :

```powershell
python levelupdiag.py --target "C:\mycode\Orgo\Orgo" run baseline
```

Python 3.10+ et Node 22+ sont requis. Utiliser `py -3` si nécessaire.
Installer explicitement les dépendances d'Orgo avec `npm ci` dans Orgo :
LevelUpDiag ne les installe pas à votre place.

Pour activer génération et tests, créer ou fusionner `levelupdiag.config.local.json`
dans LevelUpDiag-Orgo :

```json
{
  "target_repo_root": "C:/mycode/Orgo/Orgo",
  "execution": {
    "allow_target_mutation": true,
    "allow_network": false
  }
}
```

Puis :

```powershell
python levelupdiag.py run quick
python levelupdiag.py run embedded
```

Le fichier d'exemple `levelupdiag.config.orgo.example.json` fournit cette structure.
Ne pas écraser une configuration locale existante sans la comparer.

## Campagnes

| Campagne | Couverture |
| --- | --- |
| baseline | Inventaire, intégrité et hygiène ; pas de validation métier |
| quick / standard | Préflight, Prisma, architecture, types, tests du lanceur et tests unitaires |
| embedded | Quick + intégration sur PGlite jetable ; WARN car concurrence native non prouvée |
| database | Quick + migrations et tests d'intégration sur PostgreSQL natif |
| build | Types et compilations API/web |
| security | Hygiène et npm audit moderate+, sans correction automatique |
| deep | Standard + PostgreSQL natif + builds + audit |
| acceptance | Deep + backup/restore réel sur `orgo_test` + déploiement Docker Compose isolé + seed + 24 parcours Playwright |

Les mutations sont désactivées par défaut. Les autoriser permet aux commandes
d'Orgo de générer Prisma, des fichiers de compilation et des fixtures de test ;
cela **n'installe pas le diagnostic dans Orgo**.
Ces drapeaux sont une politique de sélection des commandes, pas un pare-feu OS.
PGlite utilise une connexion TCP locale ; npm/Prisma doivent être préparés avant
une campagne sans téléchargements.

## PostgreSQL natif et audit

Utiliser une base jetable `orgo_test` et un compte limité à cette base.
Ne jamais utiliser une base contenant des données utiles. Les migrations historiques
peuvent être destructives ; le nom « test » n'est qu'un garde-fou.
Définir `allow_network: true` localement pour PostgreSQL natif et npm audit.

Dans la console desktop, **Prepare PostgreSQL test** démarre et vérifie le conteneur
existant `orgo-test-postgres` (DB/user/password `orgo_test`, port 5432 local), puis
remplit le champ Test database URL. Ce bouton ne démarre pas API/web et permet donc
d'exécuter `database` ou `deep` sans concurrence avec le runtime navigateur.
`Start Orgo test` réutilise le même conteneur pour les campagnes navigateur et remplit
aussi le champ, mais il faut arrêter API/web avant une campagne native sur la même DB.

```powershell
$env:TEST_DATABASE_URL = 'postgresql://USER:PASSWORD@localhost:5432/orgo_test?connection_limit=5'
python levelupdiag.py run database
python levelupdiag.py run security
python levelupdiag.py run deep
```

Remplacer les identifiants et encoder les caractères réservés du mot de passe.
`export` est une commande Bash, pas PowerShell.
LevelUpDiag fournit par défaut l’URL locale dédiée `orgo_test` via sa configuration. Il peut aussi lire les paramètres DB du `.env` Orgo en mémoire, mais aucun repli de `TEST_DATABASE_URL` vers `DATABASE_URL` n’est effectué. Le bouton Reset / Prepare recrée explicitement la base jetable gérée; aucun correctif npm automatique n’est appliqué.
Ne pas lancer `npm audit fix --force` aveuglément.

## Rapports et séparation

Tous les rapports sont conservés côté **LevelUpDiag-Orgo** :
`.levelupdiag/runs/<id>/summary.json`, `summary.txt` et rapports par niveau.
`.levelupdiag/latest/summary.json` pointe vers la dernière campagne seulement.
Même avec un ancien fichier local, `control_dir` est relatif au diagnostic.
Un chemin absolu ou sortant du diagnostic est refusé.
Les applications ne peuvent être identiques ou imbriquées.

Les sorties sont bornées et les secrets masqués ; relire les rapports avant partage.
Un échec, une absence de tests ou un test natif ignoré ne devient pas PASS.
Codes campagne : PASS/WARN 0, FAIL 10, preuve manquante 20, erreur de configuration 30.
Un WARN n'est pas une certification.

## Acceptance automatisée N14

La campagne `acceptance` attend toujours la base jetable gérée `orgo_test`, les permissions
**Allow generation, tests and builds** et **Allow network**, ainsi que le compte browser chargé
depuis le `.env` et le consentement d’écriture sur instance jetable. Elle automatise ensuite :

- l’exécution des scripts livrés `scripts/operations/backup.sh` et `restore.sh` vers une base
  temporaire `orgo_restore_validation_*`, avec comparaison du nombre de tables et migrations ;
- la construction et le démarrage du vrai `docker-compose.yml` sous un nom de projet unique,
  avec volume PostgreSQL propre, endpoints fournisseurs externes neutralisés et cleanup `down -v` ;
- l’allocation automatique de ports loopback libres pour l’API et le web de cette pile ; les ports
  locaux 3000/4000 déjà utilisés par une autre instance ne bloquent donc plus N14 ;
- le healthcheck API/web, le seed du compte de test et les **24 parcours Playwright** sur cette
  pile de production conteneurisée ;
- la conservation de logs Compose expurgés dans le rapport N14.

Les fournisseurs externes (SMTP/SMS/OIDC/Kristal/Konnaxion/Architect/kOA/webhook) ne reçoivent
jamais automatiquement une opération réelle : leurs URLs configurées sont détectées et N14
produit `WARN` tant qu’une recette fournisseur spécifique n’est pas conservée séparément. Si
aucun endpoint externe n’est configuré dans `.env`, cette frontière est considérée hors scope
de l’instance locale et n’empêche pas N14 de passer. Les tests de charge restent séparés.

Les documents neutres hérités « copy-in » ne sont pas prescriptifs pour cette adaptation.


## Validation Common Login

Après l'upgrade Orgo Common Login, la séquence recommandée est : `quick` (types + unit/OIDC), `deep` avec PostgreSQL natif préparé, puis `browser`. Le navigateur contient E16/E17 pour prouver le maintien du login local et l'option SSO au niveau UI. Un vrai fournisseur OIDC reste hors de cette preuve et doit être validé séparément.
