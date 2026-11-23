# Comparative analysis

The table compares the families of approach found in the literature (see `literature_review.md`) with what this repository implements today. "Status here" uses the same words as the model registry in the app.

## 1. Approaches compared

| Family | Typical input | Representative papers | Strength reported | Main weakness reported | Compute need | Status here |
|---|---|---|---|---|---|---|
| Lexical text classifiers (TF-IDF with linear models) | Article text | Ahmed 2017, Pérez-Rosas 2018 | Cheap, fast, easy to explain | Learns collection-specific style, weak transfer | CPU, seconds to train | `trained_baseline` (TF-IDF with logistic regression) |
| Fine-tuned transformers | Article text | Hu 2024, Amjad 2020, Harris 2024 | Stronger language understanding, standard for Urdu | Need GPU or distilled models, same transfer problem | GPU for training | not built (planned) |
| Large language models as advisers | Article text | Hu 2024, Chen 2024 | Give rationales and world knowledge | Underperform fine-tuned small models alone, LLM-written text is harder to detect | API or large GPU | not built, optional and would be labelled |
| Social-context methods | Propagation, user signals | Shu 2017 | Use signals content lacks | Need platform data we do not have | Graph processing | out of scope |
| Image forensics, handcrafted | Pixels and metadata | Corvi 2023 (context), classical ELA | Transparent measurements | Not a verdict, defeated by re-compression | CPU | `heuristic`: ELA and metadata, indicators only |
| Learned image detectors | Pixels | Wang 2020, Ojha 2023, Pellegrini 2025, Li 2025 | Good on generators seen in training | Drop on new generators and after sharing | GPU, or pretrained features | not built |
| Video deepfake detectors | Frames and audio | Rössler 2019, Li 2020, Dolhansky 2020, Ye 2024 | Strong on benchmark data | Poor transfer across datasets and methods | GPU | built in a limited form; see `ai_model_documentation.md` |
| Image-text consistency | Image and caption | Radford 2021, Luo 2021, Khattar 2019, Yang 2026 | Targets out-of-context reuse | Generated pairs may differ from real misinformation | GPU for large models | not built |
| Evidence-grounded checking | Claim and retrieved sources | Thorne 2018, Abdelnabi 2022, Guo 2022 | Verdicts with traceable sources | Depends on retrieval quality and web access | Search access plus model | built in a limited form; see `ai_model_documentation.md` |
| Multimodal LLMs with explanations | Image, text, retrieval | Qi 2024 | Persuasive explanations, uses external knowledge | Heavy, explanations may not be faithful | Large GPU | not built |

## 2. Explanation methods compared

| Method | Model needed | Exact or approximate | Cost | Used here |
|---|---|---|---|---|
| Linear term contribution (coefficient times TF-IDF value) | Linear model | Exact for the model | Negligible | Yes. A test checks that contributions add up to the model's score |
| LIME (Ribeiro 2016) | Any | Local approximation | Many model calls | No, not needed for a linear model |
| SHAP (Lundberg 2017) | Any, faster for some | Principled attribution | Moderate to high | No, reduces to the linear contribution for this model |
| Generated rationales (Hu 2024, Qi 2024) | LLM | Not guaranteed faithful | High | No |

## 3. Evaluation practices compared

| Practice | Reported in | Here |
|---|---|---|
| Single held-out split of the training collection | Almost all classical papers | Yes (test split of GonzaloA/fake_news) |
| Evaluation on a different collection | Recommended by Li 2020, Ye 2024, Ojha 2023, Pellegrini 2025 | Yes (LIAR2, and shown in the app next to the first number) |
| Calibration error | Guo 2017 | Yes (ECE and Brier score on both sets) |
| Abstention or coverage-risk | Geifman 2017 | Partly (confidence threshold, minimum length, language check; no coverage-risk curve yet) |
| Compression and re-sharing robustness | Corvi 2023, Li 2025 | No (the image module makes no learned claim) |
| Human study of explanations | Doshi-Velez 2017, Qi 2024 | No (planned) |

## 4. What the comparison shows

1. The cheap, transparent options are the ones this project can honestly validate on a laptop. That is why the shipped models are the lexical text baseline and the ELA indicators.
2. The options with the best published results (transformers, vision-language models, retrieval pipelines) all need either a GPU, a model download or search access, and all need validation on our own held-out data before they could be offered as verdicts.
3. Every family loses accuracy off its training distribution. A fair system must therefore show external results and abstain, which the app does for text and image.
