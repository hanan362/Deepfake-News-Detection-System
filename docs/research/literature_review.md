# Literature review

This review connects the 40 papers in `references.md`. Short citations such as (Shu et al., 2017) can be looked up in `references.md`, and the member files hold the full entry for each paper. The review states what the papers report and then what that means for this project. It does not repeat numbers it cannot trace to an abstract.

## 1. Fake news detection from text

**The problem and its framing.** Shu et al. (2017) survey fake news detection on social media and separate two sources of signal: the content of the news and the social context around it, such as who shares it. A detector that only reads an article, as ours does, uses the first source alone and has no access to propagation or user behaviour.

**Datasets and classical methods.** Wang (2017) released LIAR, about 12.8 thousand short statements labelled by PolitiFact, with analysis reports and source links. Pérez-Rosas et al. (2018) built two datasets of full-length articles across seven domains and reported detectors with accuracies of up to 76%, together with a comparison to human judgement. Ahmed et al. (2017) compared six classifiers with n-gram features and reported a linear SVM on TF-IDF as best at 92% accuracy. Together they show that simple lexical models can score well inside one collection. They do not show that those scores carry over to other sources.

**Language models and machine-written news.** Zellers et al. (2019) built Grover, a generator of fake news, and found that its best defence is a discriminator built on the same generator (92% against 73% for other discriminators in their setting). Chen and Shu (2024) report that LLM-generated misinformation can be harder for both people and detectors to spot than human-written misinformation with the same meaning. Hu et al. (2024) find that GPT-3.5 gives useful rationales but does not beat a fine-tuned BERT, and propose letting the small model learn selectively from the large model's reasoning. Chen and Shu's survey (2023) places these results in the wider question of how large language models help and harm the fight against misinformation.

**Urdu.** Amjad et al. (2020) report the first shared task on Urdu fake news detection, with 900 training and 400 test articles in five domains, 42 registered teams and a best F-score of 0.90 from a BERT-based approach. Harris et al. (2024) add Ax-to-Grind Urdu, 10,083 items in fifteen domains annotated by journalists, benchmarked with an ensemble of multilingual transformers.

**What this means for the project.** The deployed text model belongs to the classical family. It reproduces the high in-collection scores the literature reports, and our external test shows the weakness the literature warns about (section 6).

## 2. Image and video manipulation

**Face-manipulation benchmarks.** Rössler et al. (2019) released FaceForensics++, with four manipulation methods and over 1.8 million manipulated images. Li et al. (2020) released Celeb-DF, with 5,639 higher-quality DeepFake videos, and showed that it is harder for existing detectors. Dolhansky et al. (2020) released the DFDC dataset, with over 100,000 clips from 3,426 consenting actors, and report that a model trained only on it can generalise to real in-the-wild deepfakes while the problem remains unsolved. Tolosana et al. (2020) survey four kinds of face manipulation.

**Generalisation.** Ye et al. (2024) target the central weakness, over-fitting to the traces of a particular forgery method, by decoupling forgery semantics. They report good generalisation across FF++, Celeb-DF, DFD and DFDC.

**AI-generated images.** Wang et al. (2020) show that a classifier trained on one GAN generalises to many other CNN generators. Corvi et al. (2023) examine diffusion-model images, including compression and resizing on social networks. Ojha et al. (2023) classify in the feature space of a pretrained vision-language model, without learning the real-versus-fake task, and report gains of +15.07 mAP and +25.90% accuracy on unseen diffusion and autoregressive models. Pellegrini et al. (2025) propose a benchmark with a temporal protocol that tests generalisation to newer generators. Li et al. (2025) show with RRDataset that detectors struggle under real-world conditions such as social-media transmission and re-digitisation.

**What this means for the project.** The strongest consistent message is that detectors do not transfer to new generators and degrade after re-sharing. That is why our image module reports measurements (Error Level Analysis and metadata) and gives no verdict, and why the video module is not built until it can be validated.

## 3. Multimodal checking and evidence

**Evidence-based verification.** Thorne et al. (2018) created FEVER, 185,445 claims verified against Wikipedia. Their best pipeline labelled claims with correct evidence 31.87% of the time, which shows how hard the task is. Guo et al. (2022) survey automated fact-checking and describe the pipeline of claim detection, evidence retrieval, verdict prediction and justification.

**Image and text together.** Radford et al. (2021) trained CLIP on 400 million image-text pairs, which gives a shared embedding that is the usual starting point for consistency checks. Khattar et al. (2019) learn a shared text-and-image representation with a variational autoencoder for microblog posts. Luo et al. (2021) build NewsCLIPpings, out-of-context pairs made by pairing real images with real but mismatched captions. Abdelnabi et al. (2022) add retrieved web evidence and a consistency-checking network, and report that evidence-using models clearly beat those without. Qi et al. (2024) present SNIFFER, an instruction-tuned multimodal LLM that also explains its judgement, and Yang et al. (2026) address domain shift with test-time training.

**What this means for the project.** The design pattern that the best-supported work shares is "retrieve evidence, then compare", with the retrieved sources shown. The planned evidence module follows that pattern and is not built. The consistency module would start from CLIP features.

## 4. Explanation, documentation and responsible use

**Explanations.** Ribeiro et al. (2016) introduced LIME and Lundberg and Lee (2017) SHAP, both model-agnostic ways to attribute a prediction to features. Doshi-Velez and Kim (2017) argue that interpretability needs a definition and an evaluation method of its own. For the linear model in this project the contribution of each term can be computed exactly, so we use that and test that it adds up.

**Documentation.** Mitchell et al. (2019) propose model cards, and Gebru et al. (2021) datasheets for datasets. The Models page, the model registry files and the dataset manifests in this repository play that role.

**Reliability.** Guo et al. (2017) show that modern networks are poorly calibrated and that temperature scaling often fixes it. Geifman and El-Yaniv (2017) show how a classifier can abstain to meet a chosen error rate. We measure calibration error and use an abstention threshold.

**How users read labels.** Clayton et al. (2020) find that a "Rated false" tag lowers belief more than a "Disputed" tag, and that general warnings can also reduce belief in true headlines. Pennycook et al. (2020) find an implied truth effect: when only some false headlines carry a warning, those without one are judged more accurate. This is why our "Unverified" and "Indicators Only" results say explicitly that no verdict was made.

**Engineering.** Amershi et al. (2019) describe how data and model versioning make machine-learning engineering different from ordinary software engineering. Sanh et al. (2019) show that a distilled BERT is 40% smaller and 60% faster while keeping 97% of the language understanding, and Sandler et al. (2018) present MobileNetV2 for mobile hardware. Both are the realistic routes to better models on a student laptop.

## 5. Synthesis

1. Text, image, video, multimodal and evidence methods have each been studied for years, and good results are common inside a single dataset.
2. Generalisation to new data, new generators and re-shared media is the open problem named by almost every recent paper (Li 2020, Ye 2024, Ojha 2023, Pellegrini 2025, Li 2025, Chen 2024).
3. Verdicts that come with evidence and explanations are the direction the multimodal papers take (Abdelnabi 2022, Qi 2024).
4. Presentation matters. The wording and completeness of labels change what people believe (Clayton 2020, Pennycook 2020).

## 6. A local measurement that agrees with the literature

The deployed text model scores 97.3% accuracy and 0.995 ROC AUC on the held-out test split of the training collection. On an unrelated collection of short political statements (LIAR2, 2,296 rows) the same model scores 55.2% accuracy and 0.549 ROC AUC, close to chance. The model has learned how the articles in its training collection are written, not how misinformation in general looks. This is the same pattern the literature describes, so the application shows both numbers and declines to claim more than the second one supports.
