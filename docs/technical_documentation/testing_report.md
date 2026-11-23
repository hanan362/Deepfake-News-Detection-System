# Testing report

This report states what was run, where, and what happened. Nothing here is estimated. Numbers come from the runs described in section 2. Test names are exact, so each claim can be re-checked with the commands in section 8.

## 1. Summary

| Suite | Tests | Result | Where it ran |
|---|---|---|---|
| Back end (pytest), SQLite | 511 | **508 passed, 3 skipped** | Development container (Python 3.13, scikit-learn 1.9.1), run on 23 November 2026 after the last changes |
| Back end (pytest), PostgreSQL 16 | 511 | **511 passed** | Development container, embedded PostgreSQL 16 server, run on 23 November 2026 |
| Front end type check (tsc) | | **No errors** | Container |
| Front end unit tests (vitest) | 55 | **55 passed** | Container (time zone set to Asia/Karachi) |
| Production build (vite) | | **Built** | Container (during the browser run) |
| Browser end-to-end (Playwright, Chrome) | 63 | **62 passed, 1 skipped on purpose** | Container only, run on 23 November 2026 |
| Migration helper on real SQLite files | 3 cases | **Worked** (legacy database adopted, repeat run, fresh database) | Container |
| Back end (pytest), SQLite, Python 3.14.6 | 511 | **508 passed, 3 skipped** (run on 23 November 2026) | Development container, a second environment with Python 3.14.6 (the version on the team laptop) and the same package versions that pip installs for Windows (numpy 2.5.5, pandas 3.1.1, scikit-learn 1.9.1, FastAPI 0.165, SQLAlchemy 2.1, pydantic 2.14), with torch 2.15 (CPU), transformers 5.24 and OpenCV 5.1 |
| Clean install on a fresh copy of the sources (container, Python 3.13), done on 21 November 2026 and **not repeated after the changes of 22 November** | whole chain | **All passed** (`run_all_tests.sh` exit code 0: 266 back-end tests passed and 3 skipped, 24 unit tests, build, 47 browser tests passed and 1 skipped) | `setup_local.sh` took 21 s, `train_text_model.sh` 1.5 min, then `install_ml.sh`, `train_text_urdu.sh` and `run_all_tests.sh`, all with real downloads. The copy was made from the list of project files because the sandbox had no git repository, so it is not a literal `git clone` |
| Back end (pytest), SQLite, laptop Linux environment | 263 | **258 passed, 5 skipped** (full run, **before the changes of 22 November, not repeated since**). The two files changed since, `test_evidence.py` and `test_deploy_files.py`, were re-run there: 33 passed, 1 skipped | Laptop (Python 3.10.12, scikit-learn 1.7.2, OpenCV 5.1, no torch) |
| Front end on the laptop Linux environment (before the changes of 22 November, not repeated since) | 24 unit tests | **Type check clean, 24 passed, production build built** | Laptop (Node 22, installed outside the mounted folder; the type checker was confirmed to fail on a deliberately wrong line). The browser tests were not run there (no browser) |

The 3 skipped back-end tests are the migration tests that run only against PostgreSQL (`TEST_DATABASE_URL is not a PostgreSQL URL`); they ran and passed in the PostgreSQL run. The skipped browser test (`screenshots.spec.ts`) only takes pictures for the manual and runs when `SCREENSHOTS=1` is set. **Failed tests in the final runs: none.**

On the laptop the 5 skips are the 3 PostgreSQL-only migration tests, the test that needs the real stance model and the test that needs the real CLIP model (the optional torch packages are not installed there, which also shows that those modules start and degrade as documented). The video tests ran with OpenCV and without torch. The back-end suite was run in four batches because a command there is limited to 180 s, and one test first failed because that environment lacked `pypdf` (listed in `requirements-dev.txt`); after installing it the test passed. The front end was first not runnable on the laptop: `npm install` into the mounted Windows folder timed out repeatedly (that folder is slow for thousands of small files). Installing into a normal folder of the Linux environment took 12 s, and there the type check, the 24 unit tests and the production build ran and passed. Source files synchronised to the laptop are checked with `sha256sum -c manifest.sha256`; four files that the laptop produced itself (the text-model metrics and registry entries from its own training with its own scikit-learn) differ on purpose and were left alone. One file, `.gitignore`, could not be updated there because Windows refused the write (Controlled Folder Access); it only adds a line that ignores a 74 MB regenerable cache.

Docker was run once in the sandbox (see section 7). Not run anywhere: the PowerShell scripts, the complete clean-install scripts, browsers other than Chrome. See section 7.

## 2. Environments

| Item | Container |
|---|---|
| Operating system | Linux, 2 CPUs, no GPU |
| Python | 3.13 |
| scikit-learn | 1.9.1 |
| torch, transformers, OpenCV | 2.15 (CPU), 5.23, 5.1 |
| Node | 22.23 |
| Browser | Google Chrome (headless) |
| Text models | English and Urdu, trained in the container (2026-11-21) |
| Database | SQLite (temporary files) and PostgreSQL 16 (embedded server) |

The laptop environment is a Linux VM on a Windows laptop: Python 3.10.12, scikit-learn 1.7.2, OpenCV 5.1.0, Node 22, 2 CPUs, no browser, no torch or transformers. Its English model was trained there earlier and its Urdu model on 2026-11-21 (test accuracy 0.8615, the same as in the container).

Each environment trains its own text models, because a model file is refused when the scikit-learn version differs. A model trained on another machine gives results that agree to within a few samples (earlier English runs on two machines: test accuracy 0.9734 and 0.9735, LIAR2 accuracy 0.5523 and 0.5527). The documents quote the container figures. The administrators' Models page of a running system shows the figures of its own machine.

## 3. Back-end tests by file

| File | Tests | What it covers |
|---|---|---|
| `test_auth.py` | 18 | Registration, hashed passwords, duplicate and weak input, login with e-mail or username, same error for wrong password and unknown user, protected routes and invalid tokens, logout, disabled accounts, password reset (single use, hashed, expiry, no enumeration, ends old sessions), profile, password change, audit events, login rate limit |
| `test_text.py` | 13 | Cleaning, script detection, short and unsupported text declined, valid deterministic probabilities, decision rule and threshold, exact explanation (adds up to the log-odds), stored result, input validation, missing model gives 503, version mismatch refused, registry matches the evaluation file |
| `test_text_urdu.py` | 8 | Urdu detection and routing, Urdu model loaded and labelled experimental, other Arabic-script text declined, missing Urdu model gives a clear error, result stored with its model |
| `test_image.py` | 9 | ELA values are real measurements, no verdict returned, owner-only media, content-based upload validation, size and pixel limits, random stored names, sanitised display names, path traversal refused, avatar re-encoded |
| `test_url.py` | 97 | Address validation (schemes, ports, credentials, private, loopback, link-local and reserved ranges, IPv6 and encoded forms), DNS pinning and redirect re-checks, size and time limits, non-HTML refused, article extraction, domain list, look-alike detection, unknown domains never called fake, stored result, per-user rate limit, unreadable pages give no verdict |
| `test_text_match.py` | 116 | The text-against-headline check, with a stand-in for the inference model: each result (consistent, contradicts, unrelated, different details, not stated), numbers and names written another way, a line that only repeats the headline, the first word of a headline, input too short, a missing or failing model, only the first ten sentences read, a mismatch stops a *Likely Real* and nothing else, **the check never produces *Likely Fake*** (every result against every verdict), the API for pasted text and web addresses, switched off, a settings file from before the check or before the strict option, Urdu, the PDF, the verdict policy for every result (default and strict), a difference on a listed outlet's own page that is shown but changes nothing, a question headline, years, an ordinary first word, amounts written "$200m" or "200 million", a title before a name, and a number that appears only later in the text |
| `test_corroboration.py` | 86 | The headline check: each rule (listed outlet, unlisted and satire outlets never counted, too few shared words, model not sure, a contradiction needs a closer match, support wins, one outlet counted once), no search without a usable headline, a failing search or missing model reported and never raised, the model not loaded when nothing needs comparing, an old settings file leaves the check off, how the result moves a verdict (never to *Likely Fake*), the web-address rules (the article's own outlet is not counted, a page on a listed site lifts an undecided reading, look-alike and unlisted sites get nothing, a difference blocks the lift), the feed reader (outlet name removed, entity and DOCTYPE documents refused), what the provider sends, the switch, the per-user limit, Urdu not compared, and the PDF section (text read back with pypdf) |
| `test_evidence.py` | 49 | Claim selection, provider failures and rate limits handled, stance only above the certainty threshold, verdict rule, *Insufficient Evidence* when nothing is found, every source keeps its title and address, nothing invented, claims and sources stored and deleted with the analysis. The search providers are replaced by recorded answers; the stance model runs for real where the ML packages are present |
| `test_multimodal.py` | 28 | Every combination of text, image and caption, missing and unreadable parts, the written fusion rule (including that image forensics never changes the verdict), CLIP thresholds read from the evaluation file, reduced result without the model, stored result, report |
| `test_video.py` | 24 | Content-based video validation and limits, frame sampling, face requirement (fewer than 8 face frames gives no verdict), aggregation and thresholds, the result never claims a temporal model, `503 BUSY` beyond two concurrent analyses, owner-only frame and video access with Range requests, stored names hidden, deletion removes files, report section |
| `test_history_reports.py` | 7 | Own items only, paging, filters and search, other users and admins cannot read or delete, deletion removes files, PDF for text and image, PDF with non-Latin text, unknown id gives 404 |
| `test_platform.py` | 21 | Dashboard from the database, empty dashboard shows zeroes, honest registry (administrators only), health, feedback flow, admin routes need admin, admin statistics and audit log, role changes and self-lock-out, one error format, security headers and CORS, OpenAPI available, limits endpoint, evaluation endpoints, **the registry and the four evaluation routes give 401 without a token and 403 to an ordinary user (5 cases), the public module list carries only module, status and description and no model name or number** |
| `test_migrations.py` | 10 | Upgrade builds every table, models and migrations agree (no drift), downgrade, roles migration keeps accounts, adoption of a database made without migrations, refusal of a mismatching one, normal migration of an empty database |
| `test_deploy_files.py` | 11 | Root Dockerfile equals the deployment one, Compose points to files that exist, production settings are safe, every variable Compose reads is documented, `.env.example` has real names and no secret, nginx proxies the API and serves the single-page app, runtime folders exist in a fresh clone, nginx lets the largest allowed video through, the PowerShell scripts only name files that exist (a static check, they were not run) |
| `test_event_loop.py` | 5 | Image and image-with-text requests do not freeze the server while a slow analysis runs (the longest stall of the event loop stays under 0.5 s; verified to fail without the fix) |
| `test_model_loading.py` | 4 | A model that failed to load is tried again after 30 s and not before (CLIP, stance and video models) |
| `test_roles.py` | 2 | Roles exist after start-up, the database rejects an unknown role |
| `test_timestamps.py` | 2 | Every timestamp carries a UTC offset, a value stored without one is read back as UTC |
| `test_api_docs.py` | 1 | The committed OpenAPI file equals the live application |
| **Total** | **505** | |

Tests that need OpenCV, torch or transformers use `pytest.importorskip`, so a machine without those packages skips them instead of failing. The three skips on SQLite are the PostgreSQL-only migration tests.

## 4. Coverage of the required test categories

Section 15 of the specification lists the categories below. A category marked *partly* has a gap that is stated.

| Category | Required | Evidence | Status |
|---|---|---|---|
| **Authentication** | Registration, login, logout, invalid credentials, access control | `test_auth.py`; `auth.spec.ts` (9) | Covered |
| **Database** | Connection, migrations, relationships, CRUD | `test_migrations.py`; roles tests; CRUD through the history and platform tests; foreign-key enforcement on SQLite (`test_an_unknown_role_is_rejected_by_the_database`), deletion of an analysis with its files | Covered on SQLite. **PostgreSQL not run** |
| **AI: model loading** | | `test_missing_model_gives_a_clear_503`, `test_version_mismatch_is_refused_not_silently_scored` | Covered |
| **AI: input validation** | | `test_short_text_is_declined_not_scored`, `test_non_english_script_is_declined`, `test_text_endpoint_validation` | Covered |
| **AI: inference and output format** | | `test_probabilities_are_valid_deterministic_and_never_misleading`, `test_text_endpoint_stores_a_complete_result`, `test_explanation_is_exact_for_the_linear_model` | Covered |
| **AI: model quality** | | Evaluation file, not a unit test | Measured, see `results_and_discussion.md`. External result is weak |
| **Media: image upload, invalid type, oversize, empty, processing failure** | | `test_image.py` (content check, limits). An empty file is refused with 400 and a file that is not an image with 415. A browser test rejects non-images before upload | Covered |
| **Media: video upload, invalid type, oversize, too long, no faces, processing failure** | | `test_video.py`; `video.spec.ts` | Covered |
| **Frontend: rendering, navigation, forms, upload, API, result display** | | `pages.spec.ts`, `auth.spec.ts`, `analysis.spec.ts`, `url.spec.ts`, `evidence.spec.ts`, `corroboration.spec.ts`, `multimodal.spec.ts`, `video.spec.ts`, 34 unit tests | Covered in Chrome |
| **Integration: front end to back end, back end to database, to model services, report generation** | | Every browser test uses the real server, database and models. `test_pdf_report_*` | Covered |
| **Security: unauthorised access, invalid tokens, cross-user access, upload validation, rate limiting** | | `test_protected_routes_need_a_valid_token`, `test_other_users_and_admins_cannot_read_or_delete_an_analysis`, `test_heatmap_and_original_are_served_only_to_the_owner`, `test_upload_is_validated_by_content_not_name_or_declared_type`, `test_login_endpoint_is_rate_limited`, browser two-user tests | Covered. No penetration test |
| **End to end: register, log in, submit, receive analysis, view, save history, download report, log out** | | `analysis.spec.ts` (article analysed, explained, saved, exported and deleted), `auth.spec.ts` (log in, log out), history tests | Covered in two connected tests, not as one single script from registration to logout |

## 5. Browser tests (Playwright)

| File | Tests | Content |
|---|---|---|
| `auth.spec.ts` | 10 | Field-level registration errors, duplicate e-mail, log in and out and a wrong password, private pages redirect and logout ends the session, forgotten-password flow, profile and password change, theme kept after reload, two users cannot see each other's data, server-rejected e-mail explained |
| `analysis.spec.ts` | 9 | Short text blocked with a reason, Arabic text refused, Urdu accepted and labelled experimental, a real article analysed, explained, saved, exported as PDF and deleted, history search and filters, another user cannot open an analysis, non-image files rejected before upload, an image gets measurements and a real error map and no verdict |
| `url.spec.ts` | 8 | The page is a real form, an article is read, analysed, described by its website, exported and deleted, a recognised publisher is named and a satire site gets no verdict, a page that cannot be read gives no verdict, and three refusals with an explanation (the server's own address, an internal service port, a host that resolves to a private network) |
| `evidence.spec.ts` | 3 | The page is a real form, a wrong claim is contradicted and a right claim supported with every source listed and the dashboard counts both, a claim nothing is known about gets *Insufficient Evidence* and text with no claim is refused |
| `multimodal.spec.ts` | 4 | The page needs at least one input, an image with an article gives separate results, the match check and the combining rule, an image alone gets indicators only and a short caption alone is not judged, a file that is not an image is refused |
| `text_match.spec.ts` | 3 | Real server and real inference model: a real headline (confirmed by the stand-in search) over a text about a swimmer is *Unverified*, the panel says the text is about something else and shows the closest sentence, and the PDF downloads; a headline over its own text is read as matching; without a headline no panel is shown |
| `corroboration.spec.ts` | 6 | Real server and real inference model with a stand-in news search: a headline a listed outlet also ran is shown as reported and exported, a very similar headline that says the opposite is flagged as different and never as fake, a headline nobody ran is not held against it, no headline means no search, a page on a listed outlet's own site is not confirmed by that outlet itself, an article from an unlisted site is compared with the listed outlets |
| `video.spec.ts` | 4 | The page is a real form, a video with no usable face gets no verdict and says why, frames and scores over time with the video, the report and deletion, the administrators' Models page shows the measured results and what they do not show |
| `pages.spec.ts` | 7 | Home page (check box, the three answers, "what it cannot do", none of the measured numbers or model names), text typed on the home page is waiting after sign-in, About page and the technical addresses sending a visitor to sign in, 404 page, unknown API path gives the standard error, every navigation destination loads without console errors and none is technical, feedback can be sent and listed |
| `admin.spec.ts` | 8 | Ordinary users cannot reach any admin or technical address (old or new) and see no admin link, the server answers 401 and 403 for the registry and evaluation routes while the public module list holds nothing technical, an administrator opens the console and the Models and Methodology pages and the old addresses lead there, an administrator's own result has a closed technical section, ordinary users cannot reach admin pages, administrator sees totals but not other people's analyses, feedback review, deactivation and reactivation of a user, an administrator cannot demote or deactivate themselves |
| `screenshots.spec.ts` | 1 | Skipped unless `SCREENSHOTS=1` |

The counts above are the numbers of test runs in each file, listed by `npx playwright test --list`. The browser tests build the interface, serve it with `vite preview`, and start a temporary real back end through `e2e/run_backend.py` with its own database and the trained text models. They never touch the developer's data. A stand-in news site answers for fictional host names in the URL tests, and the Wikipedia answer is canned in the evidence tests, so the browser suite needs no internet; the models themselves are real. The evidence test is skipped when the inference packages are missing. The video tests use two short fixtures in `e2e/fixtures`.

## 6. Defects found by testing and fixed

| # | Defect | How it was found | Fix |
|---|---|---|---|
| 1 | Timestamps were serialised without an offset, so a browser in UTC+5 showed a time five hours wrong | Reading the dashboard and result pages in a non-UTC time zone | `UTCDateTime` column type and `parseApiDate` in the interface. `test_timestamps.py` and a unit test. The back-end test was shown to fail without the fix |
| 2 | The `roles` table named in the design did not exist, so a role was a free string | Comparing the design with the schema | Roles table, foreign key and migration 0002, with a test that existing accounts survive |
| 3 | `alembic upgrade head` failed on a database created without migrations | Reasoning about the start-up path, then reproduced: a plain upgrade stops with "table dataset_versions already exists" | `app/db/migrate.py` and three tests. Scripts and Docker use it |
| 4 | The scoreboard compared the model with a random guess (50%) while the external set has 57.6% fake items, so "barely better than chance" understated the problem | Computing trivial baselines from the confusion matrices | A *Constant answer* figure on the scoreboard and Models page, with a unit test and a browser assertion |
| 5 | Screenshots of the login and a module page captured the loading spinner | Looking at the pictures | Capture script waits for the page heading |
| 6 | Several documentation statements were stronger than the evidence (an ELA test description, API status codes, dataset and venue claims in paper analyses, deployment claims) | Re-reading each against the code and the sources | Corrected to what the tests and sources support |
| 7 | Videos larger than 12 MB failed in Docker with nginx's own HTML error page, although the application allows 100 MB | Running the Docker stack and uploading a 25 MB video (HTTP 413) | `client_max_body_size` 110m, longer proxy timeouts, and `test_nginx_lets_the_largest_allowed_video_through` |
| 8 | A Wikipedia answer of HTTP 429 (seen 1 in 3 tries from the sandbox) made the evidence check report an error at once | Trying the live search by hand | Bounded retry (3 tries, server Retry-After capped at 4 s) and 4 unit tests. In six live searches afterwards no retry was needed, so the retry path itself is covered by the unit tests only |
| 9 | On a clean install without the optional ML packages, `run_all_tests.sh` failed two browser tests (the video page's Analyse button is disabled when OpenCV is missing) | Running `run_all_tests.sh` on the fresh copy | The two tests skip themselves when the video module is `unavailable`, like the evidence test already did. Verified in both configurations |
| 10 | The administration test about deactivating and reactivating a user failed once in the fresh-copy run: the notice from the first step was still on screen (it lasts 4.5 s) when the second one appeared, so the text matched two elements | The same run | The test waits for the first notice to disappear and checks the state change. It then passed three times in a row, but one failure in a few runs means it was timing-dependent before |

## 7. What the tests do not cover

| Gap | Note |
|---|---|
| Docker build and Compose | Run once in the sandbox: images built, `docker compose up` brought db, backend and web (nginx) to healthy on PostgreSQL 16; the migrations ran at start; a registered user, a text analysis (stored in PostgreSQL), the in-Docker training of the English and Urdu models, and, with `INSTALL_ML=true`, an image-text check and video checks (5 MB and 25 MB) all worked through nginx. Not covered: Docker Desktop on Windows or macOS, a 100 MB upload, reading a web address and the Wikipedia search from inside a container (no outbound network in the sandbox), the in-container model download. The sandbox run needed CA-patched base images, a build proxy and a read-only mount of the host's model cache, which an ordinary machine does not. `test_deploy_files.py` still only checks the files against each other |
| PostgreSQL as a normal installation | The suite passed against an embedded PostgreSQL 16 server. A server installed the usual way and the Compose service were not used |
| Native Windows and the PowerShell scripts | Run once by the owner on a Windows laptop (setup, `install_ml`, the Urdu training and starting the app; see section 9). The setup stopped at first on Windows Smart App Control, which blocks unsigned compiled Python files, and worked after the owner turned it off. Not run on other Windows machines, and the `.ps1` files have no automated test beyond the static check in `test_deploy_files.py` |
| `setup_local.sh` and `run_all_tests.sh` on a real clone, and on other machines | Run end to end on a fresh copy of the sources in the container (see section 1). Not run on a literal `git clone`, on macOS, or on Windows |
| Browsers other than Chrome | Not run |
| Live Wikipedia, live news sites and the live Hugging Face downloads | The automated tests use canned answers and a stand-in site. The live Wikipedia search and a few live news pages were tried by hand, and the models were downloaded and run for the evaluations |
| Video decoding of hostile files | Only malformed and oversized files were tested. The decoder is not sandboxed |
| Automated accessibility audit, responsive layout test and link crawl | Not present |
| Load, stress and long-running behaviour | Not tested beyond the two-concurrent-video limit |
| Model quality beyond the evaluation sets | See `ai_model_documentation.md` and `results_and_discussion.md` |
| Penetration testing and dependency audit | Not done |
| Test coverage percentage | Not measured |

## 8. How to rerun

```bash
cd backend && python -m pytest -p no:cacheprovider -o addopts=""     # 505 tests; add -q for a short summary
cd frontend && npm run typecheck && TZ=Asia/Karachi npm test         # tsc, then 39 unit tests
cd frontend && E2E_CHROME_PATH=/usr/bin/google-chrome npx playwright test --reporter=list   # 58 passed, 1 skipped
bash scripts/run_all_tests.sh                                        # all of the above in order
```

The text tests need the trained models (`bash scripts/training/train_text_model.sh` and `train_text_urdu.sh`). The tests for evidence, image-text and video need the optional packages (`bash scripts/setup/install_ml.sh`) and are skipped without them. To run the back-end suite on PostgreSQL, set `TEST_DATABASE_URL` to a `postgresql+psycopg://` address of an empty database before `pytest` (the tests create and drop their own tables). The unit tests that format dates run in the time zone above on purpose, because the timestamp defect only shows outside UTC.

## 9. Live spot check in a browser (22 November 2026)

After setup on the owner's Windows laptop, every analysis page was used by hand in Chrome against the running application (Vite dev server and a local back end, all models installed). The ground truth was known in advance for each input. This is a **small, hand-picked sample (about 30 inputs)**. It shows how the application behaves; it does not measure accuracy. The measured figures are in `ai_model_documentation.md` and `results_and_discussion.md`. The cases are stored in the owner's history (roughly cases 0004 to 0030, mixed with the owner's own earlier tries).

| Module | Inputs (ground truth) | Result |
|---|---|---|
| English text | 6 articles (real and fake) | 2 right, 3 "Unverified", **1 wrong**: a fake written in a sober news style was called "Likely Real" at 93% |
| Urdu text | 4 articles | 2 right, 2 "Unverified", 0 wrong |
| Evidence | 4 claims: 2 false, 2 true | 3 right (both false claims "Contradicted", Apollo 11 in 1969 "Supported"), 1 "Mixed Evidence" for the true claim about the Eiffel Tower. Some cited passages were only loosely related to the claim |
| Image and text | matching caption, and a caption about a flood under a photo of a dog | the unrelated caption was "Mismatch Flagged" (similarity 0.13); the matching caption scored 0.327, just under the 0.33 line, so "Unclear" |
| Image alone | 2 original photos | "Indicators Only", as designed. The image module gives no real or fake verdict |
| News address | an encyclopedia article, a satire article, a news article, a second news article | encyclopedia article "Likely Real"; the satire site was recognised from the source list and the verdict stayed "Unverified"; the Dawn article was "Likely Real" at 98% (668 words read); the NPR page did not answer in time and the application showed "The website took too long to answer" |
| Video | 6 clips from the DeepFake Detection set (3 fake, 3 real), uploaded without looking at the labels | 3 right ("Likely Fake" for two fakes, "Likely Real" for one real clip), 3 "Unverified" (one fake and two real clips; frame scores 0.94, 0.83 and 0.95 fell between the thresholds), 0 wrong |

Counting only the inputs where the application made a call: 13 of 14 were right and 1 was wrong; it declined to call 11 other inputs. The refusals are a design choice (a verdict only above a confidence line) and are not a measure of accuracy. A wrong call at high confidence on one of six English articles shows why no result can be presented as certain.

Other observations from the same session:

- The first use of the image-text, evidence and video models downloaded them and took from several minutes to a quarter of an hour on the laptop. During a download the local server answered slowly or not at all. The pages kept waiting and showed the result when it came.
- With the model files in place a video took about 20 to 40 seconds and an image-text check a few seconds.
- The test files were removed from the project folder afterwards.

## 10. Defects found in that session, and what was done (22 November 2026)

| Finding | Cause | Change | Check |
|---|---|---|---|
| The whole back end, and with it the development web server, stopped answering during the first image-text or image analysis | Two endpoints were declared `async` and ran blocking model code on the server's event loop | They now run that code in a worker thread (`run_in_threadpool`) | `test_event_loop.py`: a ticker task measures the longest stall of the event loop while a slow analysis runs. It reported a stall of 2.06 s without the change and passes (under 0.5 s) with it. The first version of that test passed without the change too and was rewritten |
| "Restoring your session" could stay on screen with no end while the server was busy | No time limit on the session check | After 8 s a message explains that the server is slow, with a "Try again" button | `slow.test.tsx` (4 tests) and a browser test with a session check that never answers |
| A model that failed to download (no network at that moment) stayed "unavailable" until the server restarted | The failure was remembered for good | A failed load is tried again after 30 s (CLIP, stance and video models) | `test_model_loading.py` |
| The Evidence, Video and Image-with-text pages looked frozen during their first, slow use | No feedback | A notice after a few seconds says the first use loads a model; `scripts/setup/download_models` fetches all three models up front and `install_ml` now runs it | `slow.test.tsx`; `test_deploy_files.py` checks that the script is wired in, can be skipped and refuses unknown names without touching the network |
| A true claim ("The Eiffel Tower is located in Paris, France") was called *Contradicted* | The first sentence of a Wikipedia page holds a pronunciation guide that the stance model read as contradicting the claim, and a page about a different "Eiffel Tower" (in a town named Paris in Texas) was counted | Pronunciation guides are removed, a page about a namesake is not used, a leading pronoun is replaced by the page title, one sentence per page, and a different stance model (`cross-encoder/nli-deberta-v3-small`) | `test_evidence.py` (12 new tests), the FEVER stance evaluation again, and the live claim evaluation described in `ai_model_documentation.md` section 6: on the 40 claims written after the changes were final, 21 right and 9 wrong before, **32 right and 2 wrong after** (6 without a call). The 40 claims used while developing went from 25 right and 3 wrong to 32 right and 3 wrong |
| A text result gave no hint that the text model does not check facts | Missing link | The result page links to the Evidence check with the same text prefilled | A browser test follows the link |

Findings that were **not** removed, because they are limits of the models and not defects of the application: the English text model can call a fake written in a sober news style "Likely Real" at high confidence (it judges writing style, not truth); the evidence check still calls a few true claims *Contradicted* when a page about a neighbouring subject is read as contradicting them (2 of 20 true claims in the held-out set; the earlier run of the Eiffel claim is fixed, the Nile, Newton and Great Barrier Reef style cases are not); video and Urdu stay experimental; images get indicators only.


## 11. The headline check (23 November 2026)

Built after the owner's complaint that real news is shown as *Unverified*. Measured on saved search results (`ai_models/training/evaluate_corroboration.py`, figures in `ai_model_documentation.md` section 6a and `limitations.md` L16 and L17), then built, and tested as follows.

| Finding | Cause | Change | Check |
|---|---|---|---|
| Word overlap alone accepted 11 of 14 edited headlines (a changed number, place or verb) as "reported" | A changed number still shares most words with the real headline | The inference model must also say the real headline *entails* the user's (at least 60% sure) | `test_corroboration.py`; evaluation: 0 of 14 and 0 of 9 edited headlines corroborated |
| Only 19% of real headlines were confirmed once the outlet they came from was left out | A web address from Dawn is confirmed by Dawn's own page, which proves nothing | That outlet is not counted for addresses; a separate rule says a page served from a listed outlet's own website was published by it (*Likely Real*, "published by") | Tests for both; the rule has no measured error rate (limitations L17) |
| A web address on a listed site with a *disputed* headline was first lifted to *Likely Real* | The lift rule ran after a "disputed" result that left the reading unchanged | A difference reported by another outlet now blocks the lift | `test_a_disputed_headline_on_a_listed_outlets_site_stays_unverified`, found by that test |
| The first text analysis with a headline was slow and two older browser tests timed out in the full run | The check asked whether the inference model was available before searching, which loaded it (several seconds the first time) even when no headline needed comparing | The search runs first and the model is loaded only when a listed outlet's headline is close enough to compare; the Text page shows a first-use notice | `test_the_model_is_not_touched_when_nothing_is_close_enough_to_compare`; the full browser run, which had 2 failures, passed |
| The e2e table in this report said 9 tests for `auth.spec.ts` and 8 for `analysis.spec.ts` | Two tests were added without updating the table | Corrected from `npx playwright test --list` | The total of 56 matches the list |
| Live test in the owner's browser: the same headline got "The news search is limiting requests" (HTTP 429) from Google News on the second try | The unofficial feed refuses repeated requests from one address | One retry (the server's `Retry-After`, capped at 3 s), then a 60 s pause with a clear message, so a blocked server stops asking; the verdict is unchanged. The result page showed "Could not be checked" correctly | Four tests in `test_corroboration.py` (retry, cap, pause, cap on a very long `Retry-After`); the same headline worked on the next try |
| Live test: a false claim ("The Eiffel Tower is located in Rome, Italy") was *Contradicted* by a page about the tallest buildings, not the Eiffel Tower page | The Wikipedia search used every word of the claim and was pulled toward pages sharing its wrong details | The claim's leading name is also searched alone and those pages are read first | Four tests in `test_evidence.py`; replay on the 80 saved claims (`evaluate_evidence_live.py`): verdict counts unchanged, subject page now present, two true claims became *Mixed Evidence* |
| Live test: the landing page and the headline and website sections of the result page still said these checks send nothing out or are "not combined" with the verdict | Text written before the headline check and the publisher rule existed | Sentences corrected on the landing, methodology and result pages | Read in the browser after the change; one vitest case on the related-coverage panel |
| A third test set (84 real, 30 distorted headlines) showed a distorted headline ("Iraq ..." for "Iran ...") being confirmed, and one real headline flagged as different | The inference model reads one country name for a similar one as the same statement; a fact-check headline on the same story scored as contradicting | A rule that every name and number of the user's headline must also appear in the confirming headline (it costs some real matches: 79% to 74% on the held-out set). The false "different" was left as is and recorded in the limits | `test_a_changed_name_or_number_is_not_confirmed_even_when_the_model_says_the_same` and a test that faithful copies and Title Case headlines are not blocked; all sets replayed |
| First run of the text-against-headline check on 70 real articles flagged 20 of them as not matching their own headline | Names and numbers of the headline were compared as exact words: "Korea" against "Korean", "China's", "Ebola-hit", abbreviations ("US", "DR", "PM"), headline openers ("Inside", "How") and the first word of a headline all counted as missing | Possessives and hyphens removed, a number word equals its digits, two words that start with the same five letters are the same, abbreviations of up to three capitals and headline openers are ignored. The rules were then frozen and measured once on 58 other articles (7% wrongly flagged); three further rule changes made after looking at those false alarms removed them but did not lower the rate on 55 new articles (8 of 55, 15%, wrongly flagged). A third version (question headlines, years, ordinary first words) and a fourth set of 59 whole articles gave 8 of 59 (14%) against 10 of 59 for the second version; the application therefore withholds a *Likely Real* only for a text about another story (1 of 242 real articles), and warns about the other differences | `test_text_match.py`; figures in `ai_model_documentation.md` section 6b |
| Browser test of a headline over its own text failed | The test paired a ferry headline with the fixture's city-council text, which really are different stories | The test uses the fixture's own headline; the first test uses a real unrelated text | `text_match.spec.ts` |

Not tested: the real Google News feed and the real Wikipedia API inside the automated tests (all tests use stand-ins; the feed was reached from the development container when the test sets were collected), and any fake article published on a listed outlet's site.

## 12. The redesign and the administrator-only split (23 November 2026)

What changed: a new look (midnight, paper and a highlighter yellow, with a coloured band for each verdict), three areas (public site, the app, the administrator console), and the model registry, the measured evaluation, the methodology and the technology list moved behind an administrator check that the server enforces.

| Check | Result |
|---|---|
| `GET /models` and the four `/models/*/evaluation` routes | 401 without a token and 403 with an ordinary user's token, in `test_platform.py` (5 cases) and again in a browser test that uses a real user's token |
| `GET /modules` (public) | Carries `module`, `status` and `description` and the size limits only. A test fails if the words ROC, joblib, LIAR2, TF-IDF, logistic, CLIP, "Bend the Truth" or the name of the dataset appear in it |
| Interface | An ordinary user who types `/admin`, `/admin/users`, `/admin/models`, `/admin/methodology`, `/models` or `/methodology` lands on the home page; a visitor who is not signed in is sent to the sign-in page. Ordinary navigation holds no technical link |
| A result for an ordinary reader | Shows the band, a bar with words and no percentages, and the limits in plain words. No percentages, no model name, no word weights, no measurement table (browser tests) |
| The same result for an administrator | Has a closed *Technical details* section with the percentages, word weights, measurements, model name and the model's own limits (browser test) |
| Visual review | Looked at in a real browser at 1360 px and 390 px wide, in the light and the dark theme: home page, sign-in, home, the text form, a text result, an image result, past checks, the administrator overview, users, models |

What these checks do not cover: there is no automated visual test, so a later change can break the look without a test failing. Contrast was calculated for the colour pairs in the design tokens (white on each verdict colour at least 5.3:1 in the light theme and 4.8:1 in the dark theme), not measured on rendered pages. No screen reader was used. The text typed on the home page is kept in the browser's session storage until the check page picks it up; that was tested in one browser only. A reader's own PDF and report view still contain the model scores and the model's statement of its limits (limitation L19). The changed files were copied to the team laptop on 23 November 2026 and compared with the tested copy by checksum (for the screenshots and the icon, which carry an embedded content-credentials block added during the transfer, the decoded pictures were compared instead). The tests were not run on the laptop for this change, and `backend/app/core/config.py` there still lacks the `text_match_strict` setting, because Windows blocked the write.
