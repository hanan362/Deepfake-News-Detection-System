# Team organisation

Institution: Muhammad Nawaz Sharif University of Engineering and Technology, Multan
Department: Computer Science
Supervisor: Mr. Talha Jahangir

| Student | Roll no | Role |
|---|---|---|
| Mudassar Hussain | 2023-CS-163 | Group leader |
| Abdul Hannan Anwar | 2023-CS-25 | Team member |
| Saqlain Muratza | 2023-CS-79 | Team member |
| Muhammad Ubaid UR Rehman | 2023-CS-69 | Team member |

The names, roll numbers, supervisor, institution and department were supplied by the team and are also in `frontend/src/config/project.ts` (they appear on the About page).

The project is organised into four areas of work. **Which student owns which area has not been decided or supplied, so no name is placed against an area below.**

| Area | Name | Work |
|---|---|---|
| Member 1 | to be assigned | NLP, fake-news detection, text datasets, model evaluation |
| Member 2 | to be assigned | Image deepfake detection, video detection, computer vision |
| Member 3 | to be assigned | Multimodal fusion, evidence verification, explainable AI, research integration |
| Member 4 | to be assigned | Frontend, UI and UX, backend, database, deployment |

## Responsibilities

### Member 1: NLP and evaluation

| Area | Owns | Files |
|---|---|---|
| Text data | Download, cleaning, leakage checks, manifests | `ai_models/training/train_text_baseline.py`, `datasets/` |
| Text models | Baseline, transformer experiments, Urdu | `ai_models/`, `backend/app/ml/text_detection/` |
| Evaluation | The evaluation protocol, calibration, threshold, error analysis | `ai_models/evaluation/`, `docs/research/research_methodology.md` |
| Research | Papers 1.1 to 1.10 | `docs/research/member1_nlp_text_papers.md` |

### Member 2: image and video

| Area | Owns | Files |
|---|---|---|
| Image | ELA and metadata module, pretrained-feature detector experiments | `backend/app/ml/image_detection/` |
| Video | Frame sampling, face detection, video classifier, cross-dataset tests | `backend/app/ml/video_detection/` |
| Robustness | Compression and resizing tests | `docs/technical_documentation/` |
| Research | Papers 2.1 to 2.10 | `docs/research/member2_image_video_papers.md` |

### Member 3: multimodal, evidence and explainability

| Area | Owns | Files |
|---|---|---|
| Multimodal | Image and headline consistency | `backend/app/ml/multimodal/` |
| Evidence | Retrieval design, claim handling, source policy | `backend/app/ml/fact_checking/` |
| Explainability | Term explanations, faithfulness checks, user study | `backend/app/ml/explainability/`, text service explanation |
| Research integration | Literature review, gaps, contribution statement | `docs/research/` |
| Research | Papers 3.1 to 3.10 | `docs/research/member3_multimodal_evidence_xai_papers.md` |

### Member 4: frontend, backend, database, deployment

| Area | Owns | Files |
|---|---|---|
| Frontend | Pages, design system, accessibility | `frontend/` |
| Backend | API, security, services, reports | `backend/app/` |
| Database | Models, migrations, PostgreSQL | `backend/app/models/`, `backend/alembic/` |
| Deployment | Docker, nginx, scripts, CI | `deployment/`, `Dockerfile`, `docker-compose.yml`, `scripts/` |
| Research | Papers 4.1 to 4.10 | `docs/research/member4_engineering_ai_papers.md` |

## Shared duties

All four members contribute every month to:

| Duty | What it means |
|---|---|
| Documentation | Keep the documents of their area correct when the code changes |
| Research | Read and verify papers, write the analysis fields, update the literature review |
| Testing | Add tests with each change. Do not merge with failing suites |
| Integration | Review each other's interfaces: model output to API to interface to report |

## Working agreements

1. Every claim about a model must link to a saved evaluation file.
2. A module that does not pass its gate stays `planned` or `experimental` in the registry.
3. Code review by a second member before merging into the main branch.
4. `scripts/run_all_tests.sh` must pass before a demo.
5. Never commit secrets, real datasets, private data or model checkpoints.

## Hand-over checklist for a member leaving a task

- Latest metrics file and manifest committed.
- Tests for the code they wrote pass.
- Open questions listed in the relevant document.
- Secrets and data access details shared outside the repository.
