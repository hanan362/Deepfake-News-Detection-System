# Objectives

Status key: **Met** means implemented and checked by a test or run. **Partly** means implemented in part, with the gap stated. **Not met** means not built. Evidence points to where the claim can be checked.

## General objective

Build a working, honest platform for checking news content that combines the defensible analysis modules with an account system, records and reports, and that documents its research basis.

## Specific objectives

| # | Objective | Status | Evidence |
|---|---|---|---|
| O1 | Provide registration, login, logout, password reset, profile and roles, with protected routes | **Met** | `backend/tests/test_auth.py` (18), `frontend/e2e/auth.spec.ts` |
| O2 | Provide a database layer with migrations, relationships and an audit trail | **Met** on SQLite and on PostgreSQL 16 (embedded server) | `test_migrations.py`, `database_documentation.md` |
| O3 | Train and evaluate an English text baseline with a held-out test and an external test | **Met** | `ai_models/evaluation/results/text_baseline_en_metrics.json` |
| O4 | Return text results with probabilities, a decision rule with abstention, and an exact explanation | **Met** | `backend/tests/test_text.py` (13) |
| O5 | Provide image forensic indicators with a heat map and metadata, with no verdict | **Met** as indicators. **Not met** as a detector | `test_image.py` (9) |
| O6 | Store every analysis, show history with search and filters, and export a PDF report | **Met** | `test_history_reports.py` (7), e2e analysis flow |
| O7 | Provide a dashboard from real database counts, and an admin area with user management and logs | **Met** | `test_platform.py`, `admin.spec.ts` |
| O8 | Validate uploads by content and limit size, and protect each user's data | **Met** | `test_image.py`, `test_history_reports.py`, security e2e |
| O9 | Build a responsive, accessible interface of 23 routes with no decorative controls | **Partly**: responsive and checked in a browser, accessibility not formally audited | `pages.spec.ts`, screenshots |
| O10 | Make every limitation visible in the interface | **Met** | Plain-language limits on every result, the administrators' Models page (measured results of the Urdu, evidence and video models), per-module limitation lists |
| O11 | Analyse video | **Partly**: a real pipeline with a measured, experimental frame classifier (ROC AUC 0.84 on a dataset it was not calibrated on, wide interval). Frame-based only | `test_video.py` (24), `e2e/video.spec.ts`, `video_frame_model.json` |
| O12 | Check image and headline consistency | **Partly**: CLIP similarity with thresholds measured on Flickr30k, combined by a fixed rule. Not measured on news data | `test_multimodal.py` (28), `e2e/multimodal.spec.ts`, `multimodal_clip_flickr.json` |
| O13 | Retrieve and cite evidence | **Partly**: retrieval and a stance model that always list sources; only the stance step was measured | `test_evidence.py` (22), `e2e/evidence.spec.ts`, `evidence_nli_fever.json` |
| O14 | Assess news-site credibility | **Partly**: safe fetching, article extraction and rule-based website checks. No trained model | `test_url.py` (97), `e2e/url.spec.ts` |
| O15 | Support Urdu text | **Partly**: an experimental model measured on one collection | `test_text_urdu.py`, `text_baseline_ur_metrics.json` |
| O16 | Provide deployment files and scripts | **Partly**: Docker Compose was run once in a Linux sandbox and the shell scripts ran on a fresh copy; the PowerShell scripts were only statically checked. The back-end suite ran on a real PostgreSQL server | `test_deploy_files.py` |
| O17 | Produce a verified literature review and research-gap analysis | **Met** (40 papers, venue and identifier checked) | `docs/research/` |
| O18 | Produce documentation for the 26 items of the specification and a 12-month plan | **Met** | `docs/README.md` |

## Research objectives

| # | Objective | Outcome |
|---|---|---|
| R1 | Quantify how much a classic text baseline transfers to a different collection | Measured: large drop, see `results_and_discussion.md` |
| R2 | Compare four classifiers on the same features | Done. None transfers well |
| R3 | Test whether an in-collection score is a safe basis for showing confidence | Calibration is good in-collection (ECE 0.030) and poor externally (ECE 0.129) |
| R4 | State a defensible contribution without claiming novelty | `docs/research/proposed_contribution.md` |
