# Extended browser acceptance — 24 required journeys

Extract this overlay into `C:\mycode\Orgo\LevelUpDiag-Orgo`, replacing matching
files. Close and reopen the console so it reloads the campaign description.
No application source changes, package upgrades, password resets or database
migrations are required. The previous autostart and readiness fixes remain in use.

Use **Start Orgo test**, wait for readiness, fill **Browser settings** with your
existing administrator test account, and run **browser** as before.

## Added coverage

| Test | Journey and evidence |
|---|---|
| E01 | Edit a task through the UI; reject a stale API revision without overwriting it |
| E02 | Create a task from a case; verify linkage and navigate both directions |
| E03 | Persist a comment; render HTML-like input as text |
| E04 | Assign to the current user; find the task in My Work |
| E05 | Upload, download and byte-compare a file; remove it and verify download refusal |
| E06 | Reject an oversized file without persisting it |
| E07 | Publish two immutable workflow versions; simulate and verify no task was created |
| E08 | Reject invalid workflow JSON without publishing a definition |
| E09 | Queue work with the browser offline; reconnect, synchronize and verify one task |
| E10 | Download CSV and verify formula-like titles are escaped |
| E11 | Create user/role and grant through UI; verify read-only UI, API write denial and live revocation |
| E12 | Scoped user sees one team's task; another team's task is absent and direct access returns 404 |
| E13 | Create maintenance equipment and complete a scheduled intervention |
| E14 | Create an education group and its support task |
| E15 | Create a confidential HR case and its associated task |
| E16 | Verify SSO is unconfigured in the managed standalone runtime, local login remains visible, and a real local login succeeds |
| E17 | Mock only the public SSO-config response to verify the UI can advertise `kOA Identity` without hiding the local login form |

The seven previously passing journeys remain. All tests use the real API and
local database. Some scenarios prepare independent fixtures using authenticated
API calls and verify persistence or access denial using additional API calls.
Browser actions themselves are not mocked.

## Runtime and evidence

Expect several minutes: logins are deliberately spaced 6.5 seconds apart to
respect Orgo's 10-per-minute limit. Do not manually log in or run another
campaign concurrently. If a previous run or manual login exhausts the shared
limit, wait one minute before restarting. The tests do not disable throttling.

The account must have the seeded administrator permissions. Unique test data
is retained for investigation: Work records, users, roles, workflow versions,
assets and groups. Only objects created within a scenario are removed or have
their roles revoked. No existing user password or role is changed.
Repeated runs can eventually reach current list limits (100 assets/groups/
users). Use a fresh disposable environment when needed; this suite does not
automatically purge your database.

N15 validates test identities against `browser/coverage.json`, not just a hardcoded
pass count. All 24 named Chromium tests must pass: missing, skipped, duplicate,
unexpected or flaky tests cannot produce PASS. `deep` remains unchanged.
Reports and failure traces remain under `browser/runs/<run_id>/`. These can
contain credentials and confidential test data; keep them private.

## Delivery verification and remaining boundaries

The coverage manifest requires 24 named tests. Five regression tests validate N15 coverage aggregation. Live Playwright discovery/typechecking and browser execution against the Windows Orgo instance remain to be performed locally after applying this overlay.

This does not claim complete product acceptance. Cross-organization isolation,
worker-driven workflow execution, real notifications/providers, end-to-end OIDC provider exchange, Koali
hosting, mobile layout and exhaustive accessibility still need dedicated
scenarios. Team scope isolation is not cross-organization isolation. Workflow
simulation is not async workflow execution; the launcher still starts API/web
only. Existing N14 manual acceptance is not converted to PASS by these tests.


E17 deliberately mocks only `GET /api/v3/auth/sso/config`; it does not claim IdP interoperability. E16 uses the real local API and real password login. The managed test runtime removes inherited `OIDC_*` variables so E16 is deterministic and cannot accidentally use a developer's external IdP configuration.
