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
| acceptance | Deep + frontière de recette locale explicitement BLOCKED |

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
Aucun repli sur `DATABASE_URL` n'est effectué. Aucun reset ni correctif npm automatique.
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

## Limites

Windows natif, PostgreSQL natif, navigateur, fournisseurs SMTP/SMS/OIDC et
Kristal/Konnaxion, sauvegarde/restauration, charge et déploiement requièrent la recette locale.
Les contrats Koali/Capsule doivent être validés avec leurs implémentations réelles.
N14 reste BLOCKED : une déclaration manuelle n'est pas une preuve automatique.
Les documents neutres hérités « copy-in » ne sont pas prescriptifs pour cette adaptation.


## Validation Common Login

Après l'upgrade Orgo Common Login, la séquence recommandée est : `quick` (types + unit/OIDC), `deep` avec PostgreSQL natif préparé, puis `browser`. Le navigateur contient E16/E17 pour prouver le maintien du login local et l'option SSO au niveau UI. Un vrai fournisseur OIDC reste hors de cette preuve et doit être validé séparément.
