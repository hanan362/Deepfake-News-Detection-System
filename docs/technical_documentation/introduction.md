# Introduction

## 1. Background

News now reaches readers as a mixture of text, images and video, shared through platforms that reward speed. Shu et al. (2017) describe fake news detection as a data-mining problem with its own characteristics: the content is short-lived, deliberately written to look real, and spreads through social networks. Detection work has since grown in three directions that matter for this project.

1. **Text.** Classifiers learn the writing patterns of datasets such as LIAR (Wang, 2017). Pérez-Rosas et al. (2018) and Ahmed et al. (2017) show that n-gram and linguistic features give usable accuracy inside a dataset. Zellers et al. (2019) and Chen and Shu (2024) show that machine-written misinformation changes the problem.
2. **Images and video.** FaceForensics++ (Rössler et al., 2019) and DFDC (Dolhansky et al., 2020) made large-scale deepfake video detection possible. Wang et al. (2020), Corvi et al. (2023) and Li et al. (2025) show that detectors of generated images generalise poorly across generators and degrade after compression and resizing.
3. **Context and evidence.** NewsCLIPpings (Luo et al., 2021) addresses images placed in a false context, and fact-checking research tries to ground a verdict in retrieved evidence.

Across these areas, a repeated lesson is that performance measured inside one dataset does not predict performance on another. A second lesson concerns explanation: methods such as LIME (Ribeiro et al., 2016) and SHAP (Lundberg and Lee, 2017) produce plausible-looking explanations, but plausibility is not the same as faithfulness. Model cards (Mitchell et al., 2019) were proposed so that a model's intended use, data and limits are stated with it. The full list of the 40 papers read for this project is in `docs/research/references.md`.

## 2. Motivation

Most student detection projects stop at a notebook and one accuracy number. A reader who uses a real tool needs something different: an account, a record of what was checked, a readable explanation, a way to report a wrong answer, and above all an honest statement of what the tool does not know. This project therefore builds the whole platform, and spends as much effort on the limits as on the models.

## 3. What was built

| Layer | Implementation |
|---|---|
| Interface | React 19 and TypeScript, light and dark themes, responsive |
| Service | FastAPI, JWT login with revocation, bcrypt, roles, audit log, rate limits, a single error format |
| Data | SQLAlchemy 2 with Alembic migrations, SQLite for development and PostgreSQL for deployment |
| Models | English and Urdu text classifiers with exact explanations, an image forensic-indicator module, a news-address and source check, an evidence check with a pretrained stance model, an image-with-text check and a frame-based video module |
| Reports | PDF export for each analysis |
| Operations | Scripts, Dockerfiles, Compose and nginx files (Docker run once in a Linux sandbox; the PowerShell scripts were not executed) |
| Quality | 269 back-end tests, 24 front-end unit tests, 48 browser tests |

## 4. Reading guide

| Document | Content |
|---|---|
| `problem_statement.md`, `objectives.md`, `scope.md` | The problem, the goals and what is in and out |
| `docs/research/` | Literature review, gap, methodology, feasibility |
| `requirements_specification.md`, `docs/architecture/` | Requirements and design |
| `database_documentation.md`, `docs/api/`, `ai_model_documentation.md` | Reference documents |
| `testing_report.md`, `results_and_discussion.md` | Evidence |
| `limitations.md`, `future_work.md`, `conclusion.md` | Honest limits and next steps |
| `docs/user_manual/` | Installation and use |
