# Overlay - automated N14 acceptance

Cette mise à jour remplace la frontière N14 toujours BLOCKED par une recette locale automatisée
qui reste confinée aux ressources jetables : backup/restore réel, déploiement Docker Compose
isolé, seed et 24 parcours Playwright. Les fournisseurs externes ne sont jamais invoqués sans
workflow spécifique ; s’ils sont configurés, N14 reste WARN sur cette seule frontière.

Séquence UI après installation : **Reset / Prepare PostgreSQL test -> acceptance -> Run campaign**.
Ne pas démarrer **Start Orgo test** pour acceptance ; N14 démarre sa propre pile de production.
