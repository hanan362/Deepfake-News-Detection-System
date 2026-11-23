# Deepfake News Detection System

A web platform that helps a reader check news content, and shows what its checks can and cannot say. It is a final-year research project: a complete working application around seven analysis modules (text in two languages, images, news web addresses, evidence retrieval, image with text, and video), with the research, tests and documentation that go with it. Every module states how well it was measured, and the weak ones say so.

**Read this first.** Results describe a model's behaviour, not the truth. The text model separates its own collection's articles very well (97.3% accuracy) and is close to guessing on a different kind of data (55.2% accuracy, where answering "fake" every time would score 57.6%). Administrators see both numbers in the console, every reader is told the same thing in plain words on each result, and the system abstains when it is unsure, and gives *indicators* instead of a verdict for images. The video classifier was measured on only tens of videos (ROC AUC 0.84 on a dataset it was not calibrated on, with a wide interval) and is labelled experimental. Details are in [Known limitations](#known-limitations).

## What works today

| Module | Status | What it does |
|---|---|---|
| Accounts | Working | Register, log in and out, reset password, profile, roles (user and admin), audit log |
| Text analysis | Working, baseline | English news articles of at least 60 words. TF-IDF and logistic regression trained on GonzaloA/fake_news. Returns probabilities, a verdict (*Likely Fake*, *Likely Real* or *Unverified*) and an exact explanation of which terms moved the score |
| Image analysis | Working, heuristic | Error Level Analysis map, measurements and camera metadata. Verdict is always *Indicators Only*. It cannot tell authentic, edited or AI-generated images apart |
| History and reports | Working | Every analysis is saved. Search, filter, delete, PDF report, print view |
| Home | Working | The six kinds of check, and counts computed from your own saved analyses |
| Administrator console | Working | A separate area (`/admin`) for administrators only: system totals, user roles and activation, feedback review, audit log (no access to users' articles or images), the model registry and measured results, the methodology. Enforced on the server (401 without a token, 403 for an ordinary user), not only hidden in the interface |
| Model registry | Working, administrators only | The console's Models page shows each module's status and the measured results. Everyone else gets `GET /modules`: which checks run, a plain description and the size limits |
| Urdu text | Working, experimental | A separate TF-IDF model for Urdu, trained on one small collection (86.2% accuracy, ROC AUC 0.911 on that collection's own test split; no second Urdu collection exists to test it on) |
| News web address | Working | The server reads a public news page (with limits and protection against being pointed at internal addresses), extracts the article, scores the text, and shows a rule-based check of the website. It cannot read pages that need JavaScript or a login |
| Evidence check | Working, partly needs optional packages | Picks claims, retrieves Wikipedia passages (and published fact-checks when an optional Google key is set), and labels each passage as supporting, contradicting or unclear with a pretrained NLI model. Says *Insufficient Evidence* when nothing reliable is found. Stance step measured on FEVER gold evidence: 93.7% correct on the 72.5% of cases it decides. The whole check was measured on 80 short, well-known claims (held-out half: 32 right, 2 wrong, 6 no call; the claim's subject is also searched on its own since 23 November, which did not change those counts); news claims were not measured |
| Text against headline | Working, needs the NLI model (runs on the server, sends nothing out) | Reads the first ten sentences of the text against its headline and compares the headline's numbers and names. **Only a text about another story stops a *Likely Real* (result *Unverified*)**: real articles got that result in 1 of 242 cases and texts taken from another story in 95%. A text that says something different, or lacks a name or number of the headline, is shown as a warning and does not change the verdict, because such results also appeared on about one real article in seven (14% on 59 new articles). So a real headline over an *altered version of the same story* keeps its verdict, and **a text that agrees with its headline and then adds false details is not caught either**. On a page from a listed outlet's own website nothing changes the verdict. It never makes a verdict *Likely Fake*. `TEXT_MATCH_ENABLED=false` turns it off, `TEXT_MATCH_STRICT=true` makes every difference stop a *Likely Real* |
| Headline check | Working, needs the NLI model and internet | Searches the headline in recent news (Google News RSS, an unofficial feed; **only the headline is sent**, and `CORROBORATION_ENABLED=false` turns it off) and compares it with headlines of 43 listed outlets. Shows *reported by listed outlets*, *a listed outlet reports something different* or *no matching report*; it never makes a verdict *Likely Fake*. On 126 fresh real headlines (two independent sets) 75% were found at a listed outlet (15% when the outlet the headline came from is not counted); none of 12 invented and none of 39 distorted headlines were. When nothing matches, related headlines of listed outlets are listed for the reader (they never change the verdict). A rate limit from the news feed is retried once, then paused for a minute. A page served from a listed outlet's own website is lifted from *Unverified* to *Likely Real* ("published by", a rule, not a measured model) |
| Image with text | Working, partly needs optional packages | Analyses an image and its text together. Text model, image forensics and a CLIP image-text similarity each give their own result; a fixed written rule combines them and can flag *Mismatch Flagged*. CLIP thresholds were measured on Flickr30k photos, not news |
| Video | Working, experimental, needs optional packages | Samples 16 frames across the video, finds the face in each, scores each with a pretrained image classifier, and summarises the scores over time. Frame-based: it does not learn motion or timing. Needs a clear face in at least 8 frames. Without the ML packages it still gives frames, face boxes and measurements, and no verdict |

The packages for the last three rows (torch, transformers, opencv) are optional: `bash scripts/setup/install_ml.sh` (or `make install-ml`). It also downloads the three pretrained models (about 1.3 GB); `scripts/setup/download_models` repeats that step. Without them each module says exactly what is missing and degrades to what it can still measure. No paid service or API key is needed; a Google Fact Check Tools key is an optional extra for the evidence check.

No external API key or paid service is needed.

## Quick start

Requirements: Python 3.10 or newer, Node.js 20.19 or newer (22 recommended), about 1.5 GB of disk and an internet connection for the one-time package and dataset downloads.

### Linux, macOS, or Windows with WSL

```bash
bash scripts/setup/setup_local.sh           # Python environment, packages, .env, database, frontend packages
bash scripts/training/train_text_model.sh   # downloads the datasets, trains the text model (about 2 minutes of computing)
bash scripts/run_backend.sh                 # API at http://127.0.0.1:8000  (interactive docs at /docs)
bash scripts/run_frontend.sh                # web app at http://localhost:5173  (second terminal)
```

`make setup`, `make train`, `make backend` and `make frontend` do the same.

### Windows (PowerShell)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup\setup_windows.ps1
scripts\training\train_text_model.ps1
scripts\run_backend.ps1      # first terminal
scripts\run_frontend.ps1     # second terminal
```

### Docker Compose

```bash
cp .env.example .env         # then set SECRET_KEY and POSTGRES_PASSWORD
docker compose up --build    # web app at http://localhost:8080
docker compose run --rm --user root backend python /app/ai_models/training/train_text_baseline.py all
docker compose restart backend
```

Open the web app, register an account and try **Text** and **Image**. Until the text model is trained, the Text module says it is unavailable. Nothing is faked. For the other modules run `bash scripts/setup/install_ml.sh`, then (optionally) `bash scripts/training/train_text_urdu.sh` for Urdu and the `evaluate_*` scripts in `scripts/evaluation/` to measure the evidence, CLIP and video models on your machine. The first use of the evidence, CLIP and video models downloads them from the Hugging Face Hub (about 1 GB in total).

The Docker route was built and run once in a Linux sandbox (details in the installation manual, section 5); it has not been run on Docker Desktop for Windows or macOS, and the PowerShell scripts for native Windows have not been run. The default Docker image does not include the optional ML packages (set `INSTALL_ML=true` in `.env` to add them). See [Known limitations](#known-limitations).

### First administrator

An administrator opens the **Admin console** from the left-hand navigation. Ordinary users do not see it.

Set `ADMIN_EMAIL` and `ADMIN_PASSWORD` in `.env`, restart the backend, sign in, then remove the password line. Details are in [docs/user_manual/installation_manual.md](docs/user_manual/installation_manual.md).

## Tests

```bash
bash scripts/run_all_tests.sh          # everything (or: make test)
cd backend && python -m pytest         # back end only
cd frontend && npm run typecheck && npm test   # front end type check and unit tests
cd frontend && npx playwright test     # browser tests against a temporary real backend (see the installation manual for the browser)
```

Results of the recorded runs are in [docs/technical_documentation/testing_report.md](docs/technical_documentation/testing_report.md). In short, in the development container: 508 back-end tests passed on SQLite (3 skipped on purpose) and all 511 on a real PostgreSQL 16 server, 55 front-end unit tests passed, and the browser tests ran against a real backend (counts in the report). The same back-end suite also passed on Python 3.14.6 (508 passed, 3 skipped), the Python version on the team laptop. On a second machine (a Linux VM on a Windows laptop, Python 3.10, no torch) the back-end suite gave 258 passed and 5 skipped before the last changes, and the front end type check, unit tests and build passed there. See the report. The report also lists what these tests do not cover.

## Measured results of the text model

| Set | n | Accuracy | F1 (fake) | ROC AUC | A constant answer scores |
|---|---|---|---|---|---|
| Held-out articles of the training collection | 8,084 | 0.973 | 0.972 | 0.995 | 0.536 |
| LIAR2, a different collection of short political claims | 2,296 | 0.552 | 0.643 | 0.549 | 0.576 |

These figures come from the container run. A second training run on another machine (different scikit-learn version) differed only in the third decimal, and a running system shows its own machine's numbers on the administrators' Models page. Four classifiers (logistic regression, linear SVM, Naive Bayes, random forest) behave alike. Logistic regression was deployed because its explanations are exact. See [docs/technical_documentation/results_and_discussion.md](docs/technical_documentation/results_and_discussion.md).

## Folder layout

```
backend/            FastAPI application (app/), Alembic migrations (alembic/), tests (tests/)
frontend/           React, TypeScript, Vite and Tailwind (src/), browser tests (e2e/)
ai_models/          training/ scripts, inference/ notes, evaluation/ saved metrics, model_registry/, checkpoints/ (not in Git)
datasets/           README with sources and licence notes, manifests/, raw/ and processed/ (not in Git)
storage/            uploads/, reports/, temporary/ and the SQLite database (not in Git)
scripts/            setup/, training/, database/, evaluation/, maintenance/, run_*.sh and run_*.ps1
deployment/         docker/ (Dockerfiles) and nginx/ (nginx.conf)
docs/               documentation, research, diagrams, API reference, manuals, screenshots
tests/              notes on where each kind of test lives (README files)
Dockerfile, docker-compose.yml, Makefile, LICENSE, .env.example, .gitignore
```

## Important files

| What | Where |
|---|---|
| API routes | `backend/app/api/routers/` and the generated reference `docs/api/api_reference.md` |
| Text model code and decision rule | `backend/app/ml/text_detection/`, `backend/app/services/` |
| Image forensics | `backend/app/ml/image_detection/` |
| Urdu text, web-address reading, evidence, image-with-text, video | `backend/app/ml/text_detection/` (Urdu), `url_analysis/`, `fact_checking/`, `multimodal/`, `video_detection/` |
| Evaluation and training scripts | `ai_models/training/` (`train_text_urdu.py`, `evaluate_evidence_nli.py`, `evaluate_clip_consistency.py`, `prepare_video_data.py`, `evaluate_video.py`) |
| Training script | `ai_models/training/train_text_baseline.py` |
| Saved evaluation | `ai_models/evaluation/results/text_baseline_en_metrics.json` |
| Database models and migrations | `backend/app/models/entities.py`, `backend/alembic/versions/` |
| Settings | `.env` (from `.env.example`), `backend/app/core/config.py` |
| Interface pages | `frontend/src/pages/` |

## Documentation

Start at [docs/README.md](docs/README.md). It maps the 26 documents of the project specification to files, and links the research folder (40 verified papers), the [team plan](docs/TEAM.md), the [12-month roadmap](docs/ROADMAP.md) and the [acceptance checklist](docs/ACCEPTANCE_CHECKLIST.md).

## Known limitations

The full list with reasons is in [docs/technical_documentation/limitations.md](docs/technical_documentation/limitations.md). The main ones:

- The text model learned the style of one collection. A verdict on text unlike its training articles should be ignored. It does not check facts, supports English only, and needs at least 60 words.
- The image module is a heuristic and was not validated as a detector.
- The Urdu model is experimental: one small training collection, no second collection to test it on.
- The video classifier is frame-based, was trained by a third party (this project only measured and calibrated it), and was measured on tens of videos of face-swap datasets. It has not been tested on news footage, other generators, heavy compression, or audio fakes. On a dataset it was not calibrated on, about one call in five was wrong.
- The evidence check measured its stance step on FEVER gold evidence and the whole check on 80 short well-known claims, not on news. Wikipedia does not cover recent news. Without a Google key no published fact-checks are searched.
- The headline check compares headlines only, against 43 hand-listed outlets, through an unofficial feed. Old, local and paraphrased stories are *Not found* (3% of older real headlines were found), and a real headline pasted over a false article is caught only when the text does not match its headline (the next item). Its test sets are small and written by the developers.
- The text-against-headline check reads only the first ten sentences of an English text. A text that agrees with its headline and then adds false details passes (14 of 16 such test texts did). It does not say that anything is true. Its test texts were altered or written by the developers.
- The image-text check was calibrated on everyday photos, not news, and flags about 1 in 10 matching captions as mismatched. It cannot say whether a photo is from the event the text names.
- Reading a web address cannot handle JavaScript-only or paywalled pages, and the website check uses a small hand-made list of known sites.
- Docker was run once in a Linux sandbox, not on Docker Desktop, and without outbound network inside the containers. Native Windows and the PowerShell scripts were not run. PostgreSQL was exercised both in the Compose service and in the embedded server (full back-end suite).
- There is no e-mail service, so password-reset tokens are handed over by the operator. The rate limiter is in memory per process.
- Accessibility was designed in but not formally audited.
- The 0.80 confidence threshold was not tuned.
- The training data's provenance is undocumented. Datasets are not included and keep their own terms. The MIT licence of the code needs the team's confirmation.

## Team and licence

Muhammad Nawaz Sharif University of Engineering and Technology, Multan, Department of Computer Science. Supervisor: Mr. Talha Jahangir. Students: Mudassar Hussain (group leader), Abdul Hannan Anwar, Saqlain Muratza, Muhammad Ubaid UR Rehman (see [docs/TEAM.md](docs/TEAM.md)). The code is released under the MIT licence (see [LICENSE](LICENSE)).
