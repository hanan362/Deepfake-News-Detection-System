# Requirements specification

Each requirement has an identifier, a status in the current build and the evidence for it. Status values: **Done** (built and tested), **Partial** (built with a stated gap), **Planned** (not built; the product says so).

## 1. Stakeholders and users

| Role | Needs |
|---|---|
| Reader or student | A quick, honest signal about an article or image, with its limits explained |
| Researcher on the team | Reproducible training and evaluation, documented models and data |
| Administrator | Manage accounts, see feedback, read the audit log, see model status |
| Supervisor and examiners | Clear documentation, verified references, no overclaiming |

## 2. Functional requirements

### Accounts

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| FR-01 | A visitor can register with e-mail, username and a strong password | Done | `test_auth.py`, e2e `auth.spec.ts` |
| FR-02 | A user can log in with e-mail or username and log out. Logout ends the session | Done | `test_auth.py`, e2e |
| FR-03 | A user can reset a forgotten password with a single-use, expiring token | Partial | Works and is tested. There is no e-mail service, so an operator must deliver the token (the token is returned directly only in development) |
| FR-04 | A user can edit their name and username, change their password and set or remove a profile picture | Done | `test_auth.py`, `test_image.py`, e2e |
| FR-05 | An administrator can list users, change roles and enable or disable accounts, but not lock themselves out | Done | `test_platform.py`, e2e `admin.spec.ts` |

### Analysis

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| FR-06 | A user can submit an English article (60 words or more) and receive a verdict, probabilities and a term-level explanation | Done | `test_text.py`, e2e `analysis.spec.ts` |
| FR-07 | The system declines text that is too short or in an unsupported script and says why | Done | `test_text.py` |
| FR-08 | A user can upload an image (JPEG, PNG, WEBP) and receive forensic indicators and a heatmap | Done | `test_image.py`, e2e |
| FR-09 | Every result shows its limitations in plain language | Done | `test_text.py`, `test_image.py`, e2e |
| FR-10 | A user can download a PDF report of an analysis | Done | `test_history_reports.py` |
| FR-11 | A user can list, filter, search and delete their analyses and see only their own | Done | `test_history_reports.py`, e2e |
| FR-12 | A user sees a dashboard computed from their own records | Done | `test_platform.py` |
| FR-13 | A user can send feedback or report a wrong result, and an administrator can review it | Done | `test_platform.py`, e2e |
| FR-14 | The public can see the status of every module and the measured results of the text model | Done | `test_platform.py`, e2e `pages.spec.ts` |
| FR-15 | Video deepfake analysis | Done, limited | Frame-based pipeline with face detection, aggregation and calibrated thresholds; `test_video.py`, `video.spec.ts`. Experimental: measured on tens of videos, no motion or audio model |
| FR-16 | Text and image consistency analysis | Done, limited | CLIP similarity with measured thresholds and a written fusion rule; `test_multimodal.py`, `multimodal.spec.ts`. Thresholds from Flickr30k, not news |
| FR-17 | Evidence-based claim verification | Done, limited | Wikipedia (and optional fact-check) retrieval, pretrained stance model, sources listed with links, *Insufficient Evidence* when nothing reliable is found; `test_evidence.py`, `evidence.spec.ts`. Retrieval quality not measured |
| FR-18 | News URL credibility | Done, limited | Guarded server-side fetch, article extraction, text score and a domain check against a 51-entry list; unknown domains are never called fake; `test_url.py` (97 tests), `url.spec.ts` |
| FR-19 | Urdu text analysis | Done, experimental | Separate model, accuracy 0.862 on a held-out split of one collection; `test_text_urdu.py`. No second Urdu collection to test on. Other Arabic-script text is declined |

### Administration

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| FR-20 | An administrator can read aggregate statistics without seeing users' content | Done | `test_platform.py` |
| FR-21 | An administrator can read an audit log of security-relevant events | Done | `test_auth.py`, `test_platform.py` |
| FR-22 | An administrator can see the model registry and the database records of models | Done | `test_platform.py` |

## 3. Non-functional requirements

| ID | Category | Requirement | Status | Evidence |
|---|---|---|---|---|
| NFR-01 | Honesty | The system never shows an invented prediction, demo number or unbuilt feature as working | Done | `test_platform.py` (empty dashboard shows zeroes, registry honest), a missing model gives 503 or a labelled reduced result, no verdict from too few video faces, unknown websites never called fake |
| NFR-02 | Security | Passwords hashed with bcrypt. Tokens revocable. Reset tokens hashed. Admin and owner checks on every route | Done | `test_auth.py`, `test_history_reports.py`, `test_platform.py` |
| NFR-03 | Privacy | Uploaded media and submitted text are private to their owner, including from administrators | Done | `test_history_reports.py`, `test_image.py` |
| NFR-04 | Security | Uploads validated by content, size and pixel limits, stored under random names | Done | `test_image.py` |
| NFR-05 | Security | Rate limiting on all routes and a stricter limit on authentication | Done (in memory, per process) | `test_auth.py` |
| NFR-06 | Reliability | One error format for every error. Clear message and fix when a model is missing or its version differs | Done | `test_platform.py`, `test_text.py` |
| NFR-07 | Reproducibility | Training is one command and writes metrics, metadata, registry and manifest. Dataset hashes and a seed are recorded | Done | `train_text_baseline.py`, `test_text.py` (registry matches the metrics file) |
| NFR-08 | Maintainability | Schema changes need a migration. A test fails on drift. API documentation is checked against the app | Done | `test_migrations.py`, `test_api_docs.py` |
| NFR-09 | Usability | Responsive layout, keyboard focus, light and dark themes, plain-language messages, forms that explain errors | Done | e2e, screenshots in `docs/screenshots/` |
| NFR-10 | Accessibility | Labels on fields, visible focus, reduced-motion support, colour never the only signal | Partial | Built in, but no formal audit or screen-reader testing was done |
| NFR-11 | Performance | Text scoring and image analysis finish in well under a second on a CPU | Done. Measured in the build container (CPU only): about 41 ms for an 89-word article through the whole text detector including the explanation (200 runs), and about 150 ms for Error Level Analysis of a 1600 by 1200 JPEG (5 runs). Other machines will differ | ad-hoc timing, not an automated test |
| NFR-12 | Portability | Runs on Windows, macOS and Linux with Python 3.10 or newer and Node 20 or newer, and in Docker | Partial | Backend tests pass on Python 3.10, 3.13 and 3.14 (Linux). Docker was run once in a Linux sandbox. The PowerShell scripts and Docker Desktop were not run |
| NFR-13 | Time | Timestamps are UTC with an explicit offset | Done | `test_timestamps.py`, `utils.test.ts` |
| NFR-14 | Cost | No paid service or API key is required for implemented features | Done | `.env.example` |
| NFR-15 | Limits | Image 10 MB and 40 million pixels. Text 50,000 characters. 120 requests per minute | Done, configurable | `config.py` |

## 4. Constraints

- A student laptop without a GPU is the reference hardware.
- Only openly available data and software are used.
- No claim of novelty or accuracy may go beyond what was measured.

## 5. Acceptance

The acceptance checklist, with evidence for every item in the project specification, is in `docs/ACCEPTANCE_CHECKLIST.md`.
