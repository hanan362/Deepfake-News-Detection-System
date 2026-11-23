# Research methodology

This document describes how models in this project are built, evaluated and judged. The text baseline already follows it. The sections on image, video, multimodal and evidence modules describe the protocol those modules must meet before they can be offered as more than `experimental` or `heuristic`.

## 1. Principles

1. A result counts only if it can be reproduced from the repository: scripts, seeds, dataset hashes and the evaluation file are all stored.
2. Every model is evaluated on a held-out split of its own collection and on at least one different collection. Both numbers are reported.
3. No model is tuned on the external collection.
4. A module may return a verdict only if it passed the protocol. Otherwise it returns measurements or an honest "not implemented".
5. Negative and weak results are reported in the same place as good ones.

## 2. Text baseline (implemented)

| Step | What is done | Where |
|---|---|---|
| Download | GonzaloA/fake_news (training) and LIAR2 test (external) from Hugging Face | `ai_models/training/train_text_baseline.py download` |
| Prepare | Validate, clean, remove empty or very short rows, remove duplicates and cross-split leaks, strip source artefacts such as datelines | `prepare` |
| Label check | The label meaning of the training data is not documented on its card, so label 1 was checked empirically against the rate of wire-agency tags (95.9% for label 1 against 0.04% for label 0) and treated as "real" | dataset manifest |
| Features | TF-IDF, unigrams and bigrams, 60,000 features | `features` |
| Models | Naive Bayes, linear SVM, random forest and logistic regression are compared with a fixed seed (42) | `train` |
| Choice | Logistic regression is deployed because its term contributions are exact. It was not chosen for its external score: random forest scored higher on LIAR2 F1 (0.682 against 0.643) | `finalize` |
| External labels | LIAR2 six-level labels are mapped to fake-ish (pants-fire, false, barely-true) and true-ish (half-true, mostly-true, true) | `prepare` |
| Metrics | Accuracy, precision, recall and F1 for the fake class, ROC AUC, PR AUC, confusion matrix, expected calibration error and Brier score | metrics JSON |
| Output | Checkpoint, model metadata including the scikit-learn version, registry entry, dataset manifest, metrics file | `ai_models/` |

Training takes about 90 seconds on a CPU, so it can be repeated by anyone who clones the repository.

### Measured result

| Set | n | Accuracy | F1 (fake) | ROC AUC | ECE |
|---|---|---|---|---|---|
| GonzaloA test split | 8,084 | 0.973 | 0.972 | 0.995 | 0.030 |
| LIAR2 test (external) | 2,296 | 0.552 | 0.643 | 0.549 | 0.129 |

Reading: the model separates the articles of its own collection almost perfectly and is close to chance on short political statements. The two sets differ in length (median 16 tokens in LIAR2), source and label meaning, so this is an upper bound on what the baseline can claim, not a measure of "all fake news".

### Decision rule at run time

The service refuses text under 60 words, refuses text that is mostly in a non-Latin script, scores the rest, and returns Likely Fake or Likely Real only if the model's probability for that class reaches the configured threshold (default 0.80). Otherwise the result is Unverified. The threshold is a configurable default and was not tuned on data. A coverage-risk analysis to choose it properly is future work.

## 3. Image module (implemented as indicators)

Error Level Analysis re-saves the image as JPEG at a fixed quality and measures the difference, and the module reads the metadata. Numbers (mean level, maximum, block variation) and a heatmap are reported, and the interface states that they are indicators and not proof. No learned model is shipped. A learned detector would need to pass the protocol in section 5.

## 4. The other modules and their gate

Each module below now exists in the build. What was measured, and what the gate still asks for, is stated per module. The model cards are in `docs/technical_documentation/ai_model_documentation.md`.

| Module | Data used | Gate before a verdict is shown | State |
|---|---|---|---|
| Video | Celeb-DF v2 (120 calibration, 48 test) and Google DeepFakeDetection (40) | Cross-dataset test: calibrate on one, test on another, and report both | Done at small scale. The module gives a verdict, labelled experimental, and the rule was right on 81% of the videos it decided on the second set. Training on FaceForensics++ or DFDC and testing on news footage remain open |
| Multimodal consistency | Flickr30k (600 images, split 300/300) | Held-out split plus a hand-checked sample of real headline-image pairs | Held-out split done; the news sample was not available. The check can only add a *Mismatch Flagged* label for a person to look at, and it never turns a text result into *Likely Fake* |
| Evidence verification | FEVER gold evidence (1,200 claims) | Agreement with fact-check labels with and without retrieval, sources shown | Stance step measured with gold evidence; retrieval and recent claims not measured, so the module reports stances and *Insufficient Evidence* and never a truth verdict |
| Urdu text | "Bend the Truth" (634 train, 260 test) | Train on one, test on the other | Only one collection was available, so the module is experimental |
| News address | None (rules, 51-entry list) | Safety of the fetch; no claim of reliability for unknown sites | Built; unknown domains are never called fake |

Dataset licences were checked and are recorded in the manifests. Some of the datasets named in the literature (FaceForensics++, DFDC, NewsCLIPpings) need a request form or have restricted use and were not used. The repository never stores third-party data.

## 5. Evaluation protocol for any new model

1. Fix a seed and record library versions.
2. Split the collection into train, validation and test with no duplicate or leaked rows.
3. Tune only on validation.
4. Report test results, then results on an external collection that was never used in tuning.
5. Report calibration error and a coverage-risk curve for any module that abstains.
6. Report robustness to the conditions of real use: compression, resizing, re-encoding for media; paraphrase for text.
7. Write an error analysis (examples of mistakes by category) next to the metrics.
8. Record dataset licence and known biases in the manifest.

## 6. Threats to validity

| Threat | Effect | Mitigation or status |
|---|---|---|
| Source-style shortcuts in the training collection | Inflated in-collection scores | Datelines removed, external test reported. Other shortcuts may remain |
| Label noise and unknown provenance of the training data | Unknown ceiling | Stated in the manifest, label direction checked empirically |
| Task mismatch between training and external data | External score understates transfer | Both numbers reported, mismatch stated |
| Temporal drift | Old articles do not represent current news | Limitation stated in the interface |
| Machine-written text | Unknown behaviour | Limitation stated |
| Small team and a single seed | Variance not estimated | Seed fixed. Multiple seeds and confidence intervals are future work |
| Explanation misread as proof | Over-trust | The panel says it explains the model's score, not the truth of claims |

## 6b. Software verification (implemented)

| Layer | Tool | Count at last run |
|---|---|---|
| Backend unit and API tests | pytest | 269 (266 passed and 3 skipped on SQLite, 269 on PostgreSQL) |
| Frontend unit and component tests | vitest | 24 |
| Type checking | TypeScript | clean |
| Browser end-to-end tests against the real backend | Playwright with Chrome | 47 passed, 1 skipped (screenshot helper) |

Details are in `docs/technical_documentation/testing_report.md`.
