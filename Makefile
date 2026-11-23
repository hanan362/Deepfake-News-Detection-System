# Shortcuts for common tasks. On Windows without make, use the PowerShell scripts in scripts/ instead.
# Run "make help" to list the targets.

PY ?= python
VENV ?= .venv
ACTIVATE = . $(VENV)/bin/activate &&

.PHONY: help setup install-ml train train-urdu evaluate-evidence evaluate-clip evaluate-video migrate backend frontend test test-backend test-frontend e2e build docker-up docker-train dockerfile clean

help:
	@echo "setup          create .venv, install packages, create .env, migrate the database, install frontend packages"
	@echo "install-ml    install the optional machine-learning packages (torch, transformers, opencv; about 700 MB)"
	@echo "evaluate-evidence | evaluate-clip | evaluate-video   measure the evidence, CLIP and video models and save the results"
	@echo "train          download the datasets and train the text model (about 2 minutes after the download)"
	@echo "train-urdu     download the Urdu dataset and train the experimental Urdu text model (about 1 minute)"
	@echo "migrate        apply database migrations"
	@echo "backend        run the API on http://127.0.0.1:8000 (docs at /docs)"
	@echo "frontend       run the web app on http://localhost:5173"
	@echo "test           run every automated check"
	@echo "test-backend   pytest only"
	@echo "test-frontend  type check and unit tests only"
	@echo "e2e            browser tests against a temporary real backend"
	@echo "build          production build of the frontend"
	@echo "docker-up      docker compose up --build (needs .env with SECRET_KEY and POSTGRES_PASSWORD)"
	@echo "docker-train   train the text model inside the Docker image"
	@echo "dockerfile     refresh ./Dockerfile from deployment/docker/backend.Dockerfile"

setup:
	bash scripts/setup/setup_local.sh

install-ml:
	bash scripts/setup/install_ml.sh

evaluate-evidence:
	bash scripts/evaluation/evaluate_evidence.sh

evaluate-clip:
	bash scripts/evaluation/evaluate_clip.sh

evaluate-video:
	bash scripts/evaluation/evaluate_video.sh

train:
	bash scripts/training/train_text_model.sh

train-urdu:
	bash scripts/training/train_text_urdu.sh

migrate:
	bash scripts/database/migrate.sh

backend:
	bash scripts/run_backend.sh

frontend:
	bash scripts/run_frontend.sh

test:
	bash scripts/run_all_tests.sh

test-backend:
	$(ACTIVATE) cd backend && python -m pytest -q

test-frontend:
	cd frontend && npm run typecheck && npm test

e2e:
	$(ACTIVATE) cd frontend && E2E_PYTHON=python npx playwright test

build:
	cd frontend && npm run build

docker-up:
	docker compose up --build

docker-train:
	docker compose run --rm --user root backend python /app/ai_models/training/train_text_baseline.py all

dockerfile:
	{ echo "# Backend image, built from the project root:  docker build -t dfnd-backend ."; \
	  echo "# This file is a copy of deployment/docker/backend.Dockerfile (the one docker-compose uses). A test keeps them identical;"; \
	  echo "# after editing the deployment file run:  make dockerfile"; \
	  tail -n +2 deployment/docker/backend.Dockerfile; } > Dockerfile

clean:
	rm -rf frontend/dist frontend/test-results frontend/playwright-report
