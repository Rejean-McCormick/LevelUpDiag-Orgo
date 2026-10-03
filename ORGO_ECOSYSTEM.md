# OrgoDiag — Ecosystem E2E

The optimized desktop console has two primary actions:

- **VALIDER ORGO**: focused Orgo code/preflight/unit validation.
- **VALIDER ÉCOSYSTÈME**: the end-to-end user path, with Android emulator by default and an optional physical-smartphone toggle.

`ecosystem` resolves `N07` then `N16` and runs one focused chain:

1. reuse or start local Orgo;
2. inject/verify the embedded canonical Konvergence seed (5 Cases / 19 Tasks);
3. prove the same records are visible in Orgo Web with a focused Playwright test and screenshot;
4. start an isolated local Kor service and publish 5 `kor.surface/1.2` owner surfaces;
5. start/reuse an Android emulator, or select an ADB physical phone;
6. build/install the real Kor debug application, connect it, sync it and verify the 5 surface IDs in its real Room database;
7. retain Android screenshot/UI XML and Orgo Playwright evidence under `.levelupdiag/runs/<run>/ecosystem/`.

The normal UI intentionally hides database/runtime/browser details under **Avancé**. The expected user workflow is simply **VALIDER ÉCOSYSTÈME → read PASS/FAIL**.
