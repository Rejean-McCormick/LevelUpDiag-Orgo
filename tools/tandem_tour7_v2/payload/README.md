# LevelUpDiag for Orgo (OrgoDiag)

**Standalone diagnostic overlay** for the Orgo application and its ecosystem. This repository supplies its own LevelUpDiag application; no diagnostic source files need to be copied into the Orgo repository.

## Windows GUI

Open `LEVELUPDIAG_CONSOLE.pyw`, then select **VALIDER ORGO** (validate Orgo) or **VALIDER ÉCOSYSTÈME** (validate ecosystem). These are existing UI control labels and remain untranslated so users can find them in the current application.

The ecosystem profile uses an Android emulator by default. Select the **Smartphone physique** option only when conducting an actual USB/ADB device test. Advanced technical settings remain available in the **Avancé** interface section.

## Prerequisites and CLI

Requires Python **3.10+**, Node.js **22+**, and the relevant Orgo dependencies already installed.

```powershell
python levelupdiag.py --target "C:\mycode\Orgo\Orgo" run baseline
```

Set `--target` to the **actual Orgo checkout**, external to the diagnostic application directory. Test evidence stays inside this application's `.levelupdiag/` directory.

Source generation, builds and additional test commands are allowed only by explicit local configuration. Business-domain validation reuses the tests already owned by Orgo; it does not inject new tests into the application.

## Documentation and scope

- [Orgo validation](ORGO_VALIDATION.md) — configuration and campaigns
- [Ecosystem validation](ORGO_ECOSYSTEM.md) — cross-component setup

Historical snapshot instructions describing a *copy-in* installation model are superseded by the independent, standalone adaptation documented here.

## Tandem 1.0 — Preuves OrgoDiag vérifiables

Une nouvelle campagne enregistre les SHA-256 des rapports de niveau et affiche
l'empreinte du résumé. Vérifier le run original avec
`python levelupdiag.py verify-run .levelupdiag/runs/<run-id>/summary.json`.
Pour lier les preuves au registre kOA, épingler séparément l'empreinte du résumé,
puis fournir `--expected-summary-sha256 <digest>` lors de la vérification.
Ce n'est **pas une signature**; un verdict `WARN` ou `BLOCKED` reste tel quel.
Voir `docs/TANDEM_TOUR_LEVELUPDIAG_EVIDENCE_2026-10-19.md`.
