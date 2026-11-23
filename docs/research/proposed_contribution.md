# Proposed contribution

## What this project does not claim

This project does not claim a new detection algorithm, a new dataset, or state-of-the-art results. Every model in the current build is a standard technique (TF-IDF with logistic regression, Error Level Analysis). The literature review shows each of the larger ideas (multimodal fusion, evidence retrieval, domain generalisation, Urdu datasets) is already being worked on by others. Novelty is therefore not claimed anywhere in this repository. Any later claim of novelty would need a dated literature search that shows the combination has not been published.

## What the project contributes

1. **An honest, runnable reference system.** A full web application (23 pages, API, database, migrations, tests) in which each analysis module states what it is and whether it works. Each module is labelled trained, pretrained, heuristic or experimental according to how it was measured, and a module that cannot run (a missing model or package) says so or returns a reduced, labelled result instead of invented output. Status values come from one registry and are exposed publicly at `GET /api/v1/models`.
2. **Evaluation that shows the weak number.** The Models page shows in-collection and external results side by side, with calibration error. A reader sees 97.3% accuracy next to 55.2% on LIAR2, not only the first. This follows the evaluation practice the literature recommends (gap G1) and is cheap to repeat: `python ai_models/training/train_text_baseline.py` retrains and re-measures in about two minutes.
3. **Abstention built into the product.** The text module declines text under 60 words and languages other than English and Urdu, and returns "Unverified" below a confidence threshold of 0.80. The image module returns measurements and no verdict, a video with too few usable faces gets no verdict, and an unknown website is never called fake. These choices follow Geifman and El-Yaniv (2017) and the label-effect studies of Clayton et al. (2020) and Pennycook et al. (2020).
4. **An exact explanation for the text model.** Each term's contribution is its TF-IDF value times its coefficient. A test checks that the contributions add up to the model's score. The interface says that this explains the model, not the truth of a claim.
5. **Reproducibility and documentation as part of the product.** Dataset manifests (source, licence statement, row counts, removed rows, hashes), a model registry with versions and a version guard that refuses a model trained with a different scikit-learn version, migrations with a drift test, and a verified bibliography of 40 papers.

These are engineering and evaluation-practice contributions. They are real and testable, and they are modest.

## Research directions that remain open

Each direction below is something the literature supports (see `research_gap.md`) and that the project could test in months 7 to 12 of the roadmap. None is implemented. Each has a measurable success condition so that a negative result is also a result.

| Direction | Literature support | Question to test | Success measure |
|---|---|---|---|
| Better text generalisation | Li 2020, Ye 2024, Hu 2024 | Does a fine-tuned DistilBERT-size model close part of the gap between in-collection and LIAR2 results? | External ROC AUC clearly above 0.549 with a confidence interval, using the same evaluation script |
| Urdu baseline | Amjad 2020, Harris 2024 | How well does a multilingual model trained on one Urdu dataset do on the other? | Cross-dataset F1 reported next to in-dataset F1 |
| Cross-modal inconsistency on a CPU budget | Radford 2021, Luo 2021 | Can CLIP-style features flag mismatched headline and image pairs on NewsCLIPpings without a GPU? | Accuracy and latency on a held-out split, on CPU |
| Evidence-grounded checks | Thorne 2018, Abdelnabi 2022 | Do retrieved sources improve agreement with a fact-check label on a small hand-checked set? | Agreement rate with and without evidence, source list shown |
| Explanation usefulness | Doshi-Velez 2017 | Do users make better decisions with the term-contribution panel than without it? | A small user study with a pre-registered question |

## Risks to the contribution

1. A student-scale study can easily over-fit its own validation data. The evaluation script keeps external data separate and never tunes on it.
2. The external dataset has a different label meaning (statement truthfulness against article source style), so low transfer is partly a mismatch of tasks. The documentation says so.
3. Models trained on older human-written data may fail on machine-written text (Chen and Shu, 2024). This is stated as a limitation in the interface.
