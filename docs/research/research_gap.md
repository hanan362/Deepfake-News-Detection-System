# Research gap

Each gap below is tied to papers that point at it and, where we have one, to a measurement made in this project. A gap is listed only if the literature supports it. Whether this project can close a gap is discussed in `proposed_contribution.md`.

## G1. Generalisation across datasets and sources

**Evidence from the literature.** Li et al. (2020) built Celeb-DF because existing datasets had low visual quality and did not resemble fakes circulating online, and report that it is much harder for current methods. Ye et al. (2024) name over-fitting to method-specific traces as the core problem and test across four datasets. Ojha et al. (2023) and Pellegrini et al. (2025) show or test generalisation to unseen generators.

**Evidence from this project.** Text accuracy is 97.3% on the held-out split and 55.2% on LIAR2 (ROC AUC 0.995 against 0.549). See `ai_models/evaluation/results/text_baseline_en_metrics.json`.

**Gap.** Text models trained on one collection of articles do not transfer to short statements from another source. Most text papers reviewed here report results on the collection they introduce, so external tests are the exception in what we read.

## G2. Evidence-grounded verdicts with inspectable sources

**Evidence from the literature.** Thorne et al. (2018) show the task is hard (31.87% with correct evidence in their baseline). Abdelnabi et al. (2022) show that models using retrieved evidence clearly outperform those without. Guo et al. (2022) list evidence retrieval and justification as open challenges.

**Gap.** In the papers reviewed, verdicts that come with retrieved sources depend on web retrieval and large models. We did not find a lightweight, inspectable version that a non-expert can run, and retrieval quality and time-sensitivity remain open.

## G3. Faithful explanations

**Evidence from the literature.** Doshi-Velez and Kim (2017) argue for rigorous evaluation of interpretability. Qi et al. (2024) report that generated explanations are persuasive, which is not the same as being faithful. LIME and SHAP (Ribeiro 2016, Lundberg 2017) are approximations for general models.

**Gap.** Explanations for multimodal and LLM-based detectors are rarely checked for faithfulness. For a linear text model the exact attribution exists, but it explains the model, not the truth of the claims.

## G4. Real-world robustness of image and video detection

**Evidence from the literature.** Li et al. (2025) find that current detectors struggle after social-media transmission and re-digitisation. Corvi et al. (2023) examine compression and resizing. Rössler et al. (2019) include compression levels in the FF++ benchmark.

**Gap.** Detection after re-sharing is much less reliable than detection on clean files, and news images are almost always re-shared files.

## G5. Machine-written text

**Evidence from the literature.** Chen and Shu (2024) report that LLM-generated misinformation can be harder to detect. Zellers et al. (2019) show detection depends on knowing the generator.

**Gap.** Detectors trained on human-written misinformation are not known to cover LLM-written misinformation, and the data for current generators ages quickly.

## G6. Low-resource languages, especially Urdu

**Evidence from the literature.** Amjad et al. (2020) provide 900 training articles in five domains. Harris et al. (2024) add 10,083 items in fifteen domains and describe earlier Urdu datasets as limited.

**Gap.** Urdu resources are small compared with the English ones in this review, and the abstracts do not report cross-dataset results. Our application currently declines Arabic-script text rather than guess.

## G7. Presenting uncertainty to users

**Evidence from the literature.** Guo et al. (2017) show poor calibration in modern networks, and Geifman and El-Yaniv (2017) provide a way to abstain at a chosen risk. Clayton et al. (2020) and Pennycook et al. (2020) show that label wording and partial labelling change what people believe, including an implied truth effect.

**Gap.** Detector papers report accuracy, not how a verdict, an abstention or a "no verdict" result should be shown so that users do not over-trust it.

## G8. Detection on limited hardware

**Evidence from the literature.** Sanh et al. (2019) and Sandler et al. (2018) give efficient model designs. Top competition systems for deepfake detection are heavy (Dolhansky 2020 analyse the leading Kaggle submissions).

**Gap.** Pellegrini et al. (2025) design their benchmark to keep training requirements practical, but from the abstracts we read, none of the reviewed papers compares detectors under a common laptop-CPU budget.

## Summary table

| Gap | Strength of literature support | Measured here | Addressed in current build |
|---|---|---|---|
| G1 cross-dataset generalisation | Strong | Yes (text) | Reported, not solved |
| G2 evidence-grounded verdicts | Strong | Partly | Wikipedia retrieval with a stance model, sources always listed; only the stance step measured, no truth verdict |
| G3 faithful explanations | Moderate | Yes (exactness test, text) | Text only |
| G4 real-world robustness | Strong | Partly | Image module gives no verdict. Video was calibrated on one dataset and tested on a second, where it is weaker |
| G5 machine-written text | Moderate | No | Stated as a limitation |
| G6 Urdu | Strong | Partly | An experimental model on one collection, no second collection to test on |
| G7 presenting uncertainty | Moderate | Partly (calibration and abstention) | Yes (Unverified, Indicators Only) |
| G8 limited hardware | Moderate | Yes (CPU only, 90 s training) | Yes for the baseline |
