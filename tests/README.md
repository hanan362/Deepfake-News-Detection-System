# Tests

The automated tests live next to the code they check, so each toolchain can run them without extra setup. The folders below map the layout of the project specification to the real locations.

| Kind | Location | Run with |
|---|---|---|
| Unit and integration (API with a real database) | `backend/tests/` | `cd backend && python -m pytest -q` |
| Frontend unit and component | `frontend/src/tests/` | `cd frontend && npm test` |
| End to end (real browser, real backend, temporary database) | `frontend/e2e/` | `cd frontend && npx playwright test` |
| Acceptance (specification checklist) | `docs/ACCEPTANCE_CHECKLIST.md` | read, with the evidence column |
| Everything | `scripts/run_all_tests.sh` | `make test` |

Results of the last run are in `docs/technical_documentation/testing_report.md`.
