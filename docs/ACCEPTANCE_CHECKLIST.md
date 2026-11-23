# Acceptance checklist

This checks every item of section 16 of the project specification against evidence. **Status key:** **Met** (checked by a test or a run, evidence given), **Met, limited** (met with a stated limit), **Honest refusal** (the feature or an input cannot be used, and the system says so instead of inventing a result), **Not met**, and **Not verified** (written but never run).

Environment of the recorded runs: development container, Python 3.13, scikit-learn 1.9.1, Node 22, Chrome. A second environment (a Linux VM on the team's Windows laptop, Python 3.10, scikit-learn 1.7.2, no torch) ran the back-end suite (258 passed, 5 skipped, before the last changes) and the front-end type check, unit tests and build (all passed). A third run used Python 3.14.6 (the laptop's version). Both are in `technical_documentation/testing_report.md` sections 1 and 2.

| # | Criterion | Status | Evidence and notes |
|---|---|---|---|
| 1 | The complete project exists inside the root folder | **Met** | Folder layout in `README.md`. `test_runtime_folders_exist_in_a_fresh_clone` checks the runtime folders |
| 2 | Frontend dependencies install successfully | **Met** | `npm ci` from `package-lock.json` succeeded in the container. In the laptop environment it succeeded in an earlier run (about 75 seconds), but an `npm install` into the synchronised folder timed out several times in the final run |
| 3 | Backend dependencies install successfully | **Met** | `pip install -r backend/requirements.txt -r backend/requirements-dev.txt` in the container (Python 3.13) and the laptop environment (Python 3.10) |
| 4 | Database initialises on a clean environment | **Met** | `test_upgrade_creates_every_table`, `test_an_empty_database_is_migrated_normally`, and a real run of `python -m app.db.migrate` on an empty SQLite file |
| 5 | Database migrations execute successfully | **Met** on SQLite and on PostgreSQL 16 | `test_migrations.py` (10 tests: up, down, drift, role migration, adoption). The whole back-end suite (511 tests) also ran against a real PostgreSQL 16 server (an embedded server in the container) and passed. The Compose PostgreSQL 16 service also ran the migrations at start. A PostgreSQL server installed the normal way was not used |
| 6 | Frontend starts successfully | **Met** | The production build succeeds in both environments. The browser tests serve it with `vite preview`. The Vite dev server that `scripts/run_frontend.sh` starts was run and answered HTTP 200 |
| 7 | Backend starts successfully | **Met** | `test_health`, every browser test starts the real server, and `python -m app.db.migrate` followed by `uvicorn app.main:app` was run directly and reported a healthy database and an available text model |
| 8 | Frontend communicates with backend | **Met** | 48 browser tests use the real API. The Vite dev proxy was checked by hand: a health request and a registration both worked through it |
| 9 | Registration and login work | **Met** | `test_auth.py`, `auth.spec.ts` |
| 10 | Authentication and authorization work | **Met** | Invalid and revoked tokens, disabled accounts, admin-only routes, owner-only analyses (`test_protected_routes_need_a_valid_token`, `test_admin_routes_require_admin`, `test_other_users_and_admins_cannot_read_or_delete_an_analysis`, browser two-user tests) |
| 11 | Dashboard retrieves actual database statistics | **Met** | `test_dashboard_numbers_are_counted_from_the_database`, `test_empty_dashboard_is_zeroes_not_demo_data` |
| 12 | Text analysis executes a real model or reports its unavailability honestly | **Met** | Trained TF-IDF and logistic-regression model. `test_missing_model_gives_a_clear_503` and `test_version_mismatch_is_refused_not_silently_scored` cover unavailability |
| 13 | Image analysis executes a real model or reports its unavailability honestly | **Met, limited** | Real ELA and metadata measurements. It is a heuristic, not a trained model, and gives indicators only |
| 14 | Video analysis executes a real pipeline or reports its unavailability honestly | **Met, limited** | Real pipeline: content-checked upload, 16 sampled frames, YuNet face detection, pretrained frame classifier, score aggregation with thresholds calibrated on separate videos, per-frame results and thumbnails. At least 8 face frames are required, otherwise no verdict; without OpenCV it reports *unavailable* and without torch it reports measurements only (`test_video.py`, 24 tests; `video.spec.ts`, 4 tests). Measured on 3 small sets (ROC AUC 0.84 on a second dataset). **Frame-based, third-party model, no motion or audio model**, and nothing measured on news footage. See `ai_model_documentation.md` section 8 |
| 15 | Multimodal analysis handles available and missing inputs correctly | **Met, limited** | Text only, image only, text with image, and a missing or unreadable part each give a defined result (`test_multimodal.py`, 28 tests; `multimodal.spec.ts`). Fusion is a written rule; CLIP thresholds were measured on Flickr30k, not on news |
| 16 | Evidence links are genuine and traceable | **Met, limited** | Every evidence item carries the title and the address returned by Wikipedia (or the fact-check service when a key is set) and is stored with the analysis. Nothing is generated. When nothing is found the answer is *Insufficient Evidence* (`test_evidence.py`, 22 tests, with the search providers replaced by recorded answers; `evidence.spec.ts`). The live Wikipedia call was spot-checked. Each claim and each source is also stored in the `claims` and `evidence_sources` tables |
| 17 | Analysis history works | **Met** | `test_history_lists_only_own_items_newest_first_with_paging`, filters, deletion, browser test |
| 18 | PDF reports can be generated | **Met** | `test_pdf_report_for_text_and_image`, `test_pdf_report_survives_non_latin_and_markup_text`, browser export test |
| 19 | Admin access is protected | **Met** | `test_admin_routes_require_admin`, `test_technical_endpoints_are_for_administrators_only` (the model registry and the four evaluation routes give 401 without a token and 403 for a user), `admin.spec.ts` (an ordinary user is sent home from every admin and technical address; the server refuses the API calls) |
| 20 | File uploads are validated | **Met** | Content check, size and pixel limits, random stored names, path traversal refused (`test_image.py`) |
| 21 | Responsive UI works | **Met, limited** | Checked visually at 390 px (`docs/screenshots/11-mobile-text.png`, `12-mobile-result.png`). No automated responsive test |
| 22 | No broken navigation links | **Met, limited** | A browser test opens every sidebar destination and checks for console errors. Unknown addresses give a 404 page. Other links were followed during the tests, not every link on every page |
| 23 | No non-functional buttons | **Met, limited** | Controls were built only where they act. Every module page has a working analysis control or says why it cannot run. Checked by the browser tests and by review, not by an automated crawl of every button |
| 24 | No fake AI predictions | **Met** | No random or hard-coded prediction exists. The tests refuse a missing model, a video without enough faces gets no verdict, an unknown site is never called fake, and each result shows its model name and version |
| 25 | No exposed secrets | **Met** | No `.env` in the project, `.env.example` holds no secret (`test_env_example_names_are_real_settings_and_hold_no_secret`), a search for key patterns found none, `.gitignore` excludes `.env` and data |
| 26 | Critical tests pass | **Met** | `testing_report.md`: back end 511 collected, 508 passed and 3 skipped on SQLite (a skip needs a condition the container does not have) and 511 passed on PostgreSQL, and the same 508 passed and 3 skipped on Python 3.14.6; unit tests 55 of 55; browser tests 62 passed and 1 skipped on purpose (container only), all run on 23 November 2026. The laptop runs (back end 258 passed and 5 skipped, no torch) are older than the last changes and were not repeated; see `testing_report.md` section 1 |
| 27 | README contains accurate setup instructions | **Met, limited** | The clean-install sequence (`setup_local.sh`, text and Urdu training, `install_ml.sh`, `run_all_tests.sh`) ran end to end on a fresh copy of the sources in the sandbox, and Docker Compose ran end to end there too. The PowerShell scripts and native Windows were not run (a static test only checks the paths they name) |
| 28 | Known limitations are documented | **Met** | `technical_documentation/limitations.md`, the interface's own limits text, `README.md` |

## Criteria that cannot be completed, why, and the remaining steps

| Item | Why it is incomplete | Remaining steps |
|---|---|---|
| 14 Video, deeper | A model that learns motion, audio analysis, validation on news footage and other generators, a sandboxed decoder | Roadmap months 5 and 7; GPU and DFDC or FaceForensics++ access |
| 15 Multimodal, on news | Thresholds measured on news photographs | NewsCLIPpings or similar (roadmap months 8 and 9) |
| 16 Evidence, end to end | Retrieval quality was not measured, and Wikipedia has little recent news | A hand-checked claim set with the right sources marked |
| 5 PostgreSQL, normal install | The server used was an embedded PostgreSQL 16 build, not a standard installation | The Compose PostgreSQL 16 service ran the migrations and stored an analysis in the sandbox, but the test suite itself ran only against the embedded server. Repeat the suite against a normal server or the Compose service (roadmap month 5) |
| 27 Clean install on all platforms | Docker ran only in a Linux sandbox without outbound network inside containers; the shell scripts ran on Linux only; native Windows was not available | Run `docker compose up --build` on Docker Desktop and `scripts\setup\setup_windows.ps1` on a real Windows machine (roadmap month 5) |
| 21 to 23 UI criteria | No automated responsive, link and button audit | Add them to the browser suite and run an accessibility audit |

## Specification requirements outside section 16

| Requirement | Status |
|---|---|
| Distinguish trained, pretrained, baseline, experimental, demo and planned (section 14) | **Met**: registry statuses and labels. There is no demo mode, so no demo data can be mixed with real results |
| Test categories of section 15 | Mapped in `testing_report.md` section 4 |
| Documentation items 1 to 26 (section 19) | **Met**: index in `docs/README.md` |
| Four-member organisation and roadmap (section 20) | **Met** as documents: `TEAM.md`, `ROADMAP.md`. Student, supervisor, institution and department are recorded; who owns which area was not supplied |
