# Acceptance dynamic host ports

N14 no longer requires local ports 3000 and 4000 to be free.

- LevelUpDiag asks the OS for two free loopback ports for the isolated Compose acceptance stack.
- `ORGO_API_HOST_PORT` and `ORGO_WEB_HOST_PORT` are passed only to that Compose run.
- `ORGO_PUBLIC_URL`, readiness probes and `ORGO_E2E_URL` use the allocated web/API ports.
- Orgo `docker-compose.yml` keeps 4000/3000 as defaults for normal use, but accepts the two host-port overrides.
- No unrelated process is killed or replaced.
- The tracked **Start Orgo test** runtime must still be stopped before `acceptance` because it shares `orgo_test`, even though port collisions are no longer a reason to block.
