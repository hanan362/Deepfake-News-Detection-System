# Installation manual

Two ways to run the system: **local** (recommended for development and for a demo on one computer) and **Docker Compose** (closer to production). The local route was tested. The Docker route was built and run once in the development sandbox (PostgreSQL 16, backend and nginx containers all healthy; details and the limits of that run are in section 5). It has not been run on Docker Desktop for Windows or macOS.

## 1. Requirements

| Item | Local | Docker |
|---|---|---|
| Python | 3.10 or newer (tested with 3.10, 3.13 and 3.14) | in the image (3.12) |
| Node.js | 20.19 or newer (tested with 22) | in the image (22) |
| Disk | About 1.5 GB for the basic install; about 5 GB with the optional ML packages and models | about the same |
| Internet | Needed for installing packages and downloading the training datasets. The optional ML features need three models (about 1.3 GB in total). `install_ml` downloads them; a model that was skipped or failed is downloaded on first use instead, which can take up to a quarter of an hour on a slow connection. The news-address, headline-check and evidence features contact other sites every time they are used (the headline check sends only the headline to Google News search; `CORROBORATION_ENABLED=false` in `.env` turns it off) | same |
| GPU | Not needed | not needed |
| Browser | Any current Chrome, Edge, Firefox or Safari | same |

No API key or paid service is required. An optional `GOOGLE_FACT_CHECK_API_KEY` adds published fact-checks to the evidence check.

## 2. Get the project

Copy the project folder to your computer (or clone the repository). All commands below are run from the project's root folder, the one that contains `README.md`.

## 3. Local installation

### Linux, macOS or Windows with WSL

```bash
bash scripts/setup/setup_local.sh           # Python environment, packages, .env, database, frontend packages
bash scripts/training/train_text_model.sh   # downloads the datasets and trains the text model
bash scripts/run_backend.sh                 # API on http://127.0.0.1:8000  (docs at /docs)
bash scripts/run_frontend.sh                # web app on http://localhost:5173  (second terminal)
```

The same steps are available as `make setup`, `make train`, `make backend` and `make frontend` if `make` is installed.

### Windows (PowerShell)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup\setup_windows.ps1
scripts\training\train_text_model.ps1
scripts\run_backend.ps1          # first terminal
scripts\run_frontend.ps1         # second terminal
```

The PowerShell scripts were written to mirror the shell scripts but were **not run on native Windows** in this build.

### What each step does

| Step | Effect |
|---|---|
| setup | Creates `.venv`, installs `backend/requirements.txt` and `requirements-dev.txt`, copies `.env.example` to `.env` if there is none, creates the database (`python -m app.db.migrate`), and installs the frontend packages with `npm ci` |
| train | Downloads the two datasets into `datasets/raw/`, cleans them, trains four classifiers, evaluates them, and writes the deployed model to `ai_models/checkpoints/`, plus metrics, registry entry and manifest. About 2 minutes of computing after the download |
| backend | Applies migrations and serves the API with auto-reload |
| frontend | Starts the Vite dev server, which forwards `/api` to the backend |

Until the model is trained, the Text module reports itself as unavailable. Nothing is faked. The image module works immediately.

### Optional: Urdu and the machine-learning modules

```bash
bash scripts/training/train_text_urdu.sh    # Urdu text model, about 1 minute
bash scripts/setup/install_ml.sh            # torch, transformers and OpenCV (about 2 GB), then downloads the three models (about 1.3 GB more)
bash scripts/setup/download_models.sh       # only the model downloads (CLIP, evidence, video), e.g. after a failed or skipped download
```

PowerShell has the same scripts (`train_text_urdu.ps1`, `install_ml.ps1`). Without `install_ml`, the Evidence, Multimodal and Video modules still run in a reduced, clearly labelled form: evidence passages are listed but their stance is not judged, the image-text match is skipped, and a video gets frame measurements only (or *unavailable* if OpenCV is missing). `install_ml` also downloads the models now (evidence about 570 MB, image-text about 600 MB, video about 110 MB) and they are cached; `-SkipModels` (PowerShell) or `SKIP_MODELS=1` (bash) leaves that out, and `download_models` does it later. A model that is not downloaded yet is fetched when its page is first used. The face detector for video ships with the repository. The measured results can be reproduced with `scripts/evaluation/evaluate_evidence.sh`, `evaluate_clip.sh` and `evaluate_video.sh` (these download research datasets).

### Open the app

Go to http://localhost:5173, register an account, and try **Text** and **Image**.

## 4. Settings (`.env`)

`.env` lives in the project root and is never committed. The defaults work for local use. The ones you may want to change:

| Variable | Default | Meaning |
|---|---|---|
| `ENVIRONMENT` | `development` | `production` makes `SECRET_KEY` mandatory and refuses `EXPOSE_RESET_TOKEN` |
| `SECRET_KEY` | placeholder | Signs login tokens. In development an unset key becomes random each start, so logins end on restart. Generate a real one: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `DATABASE_URL` | SQLite file `storage/app.db` | For PostgreSQL: `postgresql+psycopg://user:password@host:5432/dbname` |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | empty | When both are set and no such user exists, the first administrator is created at start-up. Remove the password afterwards |
| `EXPOSE_RESET_TOKEN` | `false` | `true` returns the reset token in the response so the flow can be tried without e-mail. Never use in production |
| `TEXT_CONFIDENCE_THRESHOLD`, `MIN_TEXT_TOKENS` | `0.80`, `60` | The text decision rule |
| `MAX_IMAGE_MB`, `MAX_IMAGE_PIXELS` | `10`, `40000000` | Upload limits |
| `MAX_VIDEO_MB`, `MAX_VIDEO_SECONDS`, `VIDEO_SAMPLE_FRAMES` | `100`, `180`, `16` | Video limits. Keep the number of frames at 16: the thresholds were measured with 16 |
| `URL_FETCH_ENABLED`, `URL_FETCH_RATE_LIMIT_PER_MINUTE` | `true`, `10` | Turn the news-address fetch off, or limit it per user. It is the only feature that fetches arbitrary web pages |
| `GOOGLE_FACT_CHECK_API_KEY` | empty | Optional key for the Google Fact Check Tools API |
| `RATE_LIMIT_PER_MINUTE`, `AUTH_RATE_LIMIT_PER_MINUTE` | `120`, `10` | Rate limits |
| `CORS_ORIGINS` | the Vite dev addresses | Browser origins allowed to call the API directly |

### Create the first administrator

Set `ADMIN_EMAIL` and `ADMIN_PASSWORD` in `.env` (a strong password), restart the backend, sign in, then delete the password line from `.env`. Alternatively register a normal account and promote it from an existing administrator on the **Admin, Users** page.

## 5. Docker Compose

```bash
cp .env.example .env
# edit .env: set SECRET_KEY (a long random value) and POSTGRES_PASSWORD
docker compose up --build        # PostgreSQL, backend, and nginx with the built web app
```

Open http://localhost:8080 (change the port with `WEB_PORT`).

The backend image contains only the basic packages. To use the evidence, image-text and video modules in Docker, set `INSTALL_ML=true` in `.env` before `docker compose up --build` (the image grows by about 2 GB; the models download on first use into `ai_models`). This option was run: with `INSTALL_ML=true` the evidence, image-text and video modules all started inside the container, and an image-text check and a video check (a 5 MB and a 25 MB file) ran through nginx. In that test the models came from a read-only copy of the host's Hugging Face cache, because the sandbox containers had no outbound network, so the in-container model download itself was not exercised.

The text model is not inside the image. Train it once with the image's own Python, so that the scikit-learn version matches:

```bash
docker compose run --rm --user root backend python /app/ai_models/training/train_text_baseline.py all
```

The model is written to `./ai_models/checkpoints` on the host and persists. Restart the backend afterwards (`docker compose restart backend`). The Urdu model is trained the same way:

```bash
docker compose run --rm --user root backend python /app/ai_models/training/train_text_urdu.py
```

(The Urdu script downloads its dataset, so the container needs internet access when you run it.)

Notes for Docker:

- The backend runs the migration helper (`python -m app.db.migrate`) at start and sets `AUTO_CREATE_TABLES=false`. In the sandbox run the migrations ran at start on the Compose PostgreSQL 16 service, and a text analysis sent through nginx was stored there. The back-end test suite was run separately against an embedded PostgreSQL 16 server.
- A model trained outside Docker with a different scikit-learn version is refused by the version check. Train it inside Docker as shown.
- Uploads and reports are kept in the `storage` volume and the database in `pgdata`.
- PostgreSQL reads `POSTGRES_PASSWORD` only when it first creates `pgdata`. If you change the password later the backend fails with "password authentication failed". Either put the old password back, or, if you do not need the stored data, run `docker compose down -v` (this deletes the database and the uploads volume) and start again.
- nginx accepts uploads up to 110 MB, just above the 100 MB video limit (`MAX_VIDEO_MB`). If you raise `MAX_VIDEO_MB`, raise `client_max_body_size` in `deployment/nginx/nginx.conf` too, otherwise nginx answers with its own HTML error page (413) before the application sees the file. A 12 MB limit that was in the first version of this file was found this way and fixed.
- Not checked in Docker: reading a web address and the Wikipedia evidence search (the sandbox containers had no outbound network), and a 100 MB upload (25 MB was tried).

## 6. Run the tests

```bash
bash scripts/run_all_tests.sh      # or: make test
```

This runs the backend tests, the frontend type check, the frontend unit tests, a production build and the browser end-to-end tests. The end-to-end tests start their own temporary backend and database, so they never touch your data. They need the trained text model and a browser:

```bash
cd frontend
npx playwright install chromium            # once, to download a test browser
# or use a browser you already have:
E2E_CHROME_PATH="/usr/bin/google-chrome" npx playwright test
```

Single suites: `cd backend && python -m pytest`, `cd frontend && npm test`, `cd frontend && npm run typecheck`.

## 7. Updating

```bash
git pull                                   # if you use git
pip install -r backend/requirements.txt    # inside .venv
(cd backend && python -m app.db.migrate)
(cd frontend && npm ci)
```

After upgrading scikit-learn, retrain the text model.

## 8. Troubleshooting

| Problem | Cause and fix |
|---|---|
| Text page says the model is not available | Run the training script. If it says the model was trained with a different scikit-learn version, retrain with the same command |
| Windows: `ImportError: DLL load failed ... An Application Control policy has blocked this file` (often with a Windows Security notice "Part of this app has been blocked") during `setup_windows.ps1` or when starting the back end | Windows Smart App Control (or an organisation's application-control policy) refuses to load the compiled, unsigned `.pyd` files that Python packages such as SQLAlchemy, NumPy, SciPy and pandas contain. The packages are installed correctly; Windows blocks them at the first import. Found on a Windows 11 laptop with Python 3.14.6. Options: (1) run the project in WSL 2 (Ubuntu) or with Docker Desktop, where Linux binaries are used and this policy does not apply; (2) if the laptop is yours, check Windows Security, App and browser control, Smart App Control; turning it off lets the packages load, but it is a security feature and, on many Windows versions, cannot be turned on again without resetting Windows, so decide deliberately; (3) on a laptop managed by a school or company the policy is theirs to change, so use option 1 or another computer |
| `npm ci` fails on an old Node | Install Node 20.19 or newer (22 recommended) |
| Port 8000 or 5173 already in use | Stop the other program, or start the backend with another port and set `VITE_PROXY_TARGET=http://127.0.0.1:<port>` before the frontend |
| Login lasts only until the server restarts | `SECRET_KEY` is not set. Set it in `.env` |
| `python -m app.db.migrate` stops with "schema differs from the application's" | The database has tables but no migration history, and they differ from what this version expects (an old development database). Nothing was changed. Delete `storage/app.db` (development only) and run it again. A database that matches exactly is adopted automatically |
| Download of the datasets fails | Check internet access and that huggingface.co is reachable. Re-run the `download` stage |
| Video says *unavailable* or *measurements only* | OpenCV or torch is missing: run `scripts/setup/install_ml.sh`. A video with fewer than 8 usable faces gets no verdict on purpose |
| Evidence, Multimodal or Video says a model could not be loaded | The download from Hugging Face failed. Check internet access and disk space. The server tries again by itself after 30 seconds; `scripts/setup/download_models.sh` (or `.ps1`) downloads all three and says which one failed |
| The first Evidence, Multimodal or Video analysis takes many minutes, or the page shows "The server is taking a long time to answer" | The model is being downloaded and loaded. Other pages keep working. Run `download_models` once after installing so this does not happen during a demonstration |
| News address cannot be read | The page needs a script, a login or a subscription, or the server has no outbound access. This is reported in the result and is not a fault |
| PowerShell blocks scripts | Run them with `powershell -ExecutionPolicy Bypass -File <script>` |
| End-to-end tests cannot find a browser | `npx playwright install chromium` or set `E2E_CHROME_PATH` |

## 9. Uninstall

Delete the project folder. Nothing is installed outside it, except the optional Playwright browser download in your user cache.
