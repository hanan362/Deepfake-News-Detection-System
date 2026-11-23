# Member 3: Multimodal reasoning, evidence retrieval, explainability

Ten verified papers for this area. Bibliographic details (title, authors, venue, DOI or arXiv number) were checked against Crossref, arXiv, publisher or proceedings pages, and the source of each venue is named in the entry.

How to read each entry: fields 1 to 5 are bibliographic facts. Fields 6 to 10 (problem, methodology, models, dataset, reported results) stay within what the abstract or the cited page states; where an abstract gives no number the entry says so instead of guessing. Fields 11 to 15 (advantages, limitations, gaps, improvements, relevance) are our own assessment.

## 3.1 FEVER: a large-scale dataset for Fact Extraction and VERification

1. **Title:** FEVER: a large-scale dataset for Fact Extraction and VERification
2. **Authors:** James Thorne, Andreas Vlachos, Christos Christodoulopoulos, Arpit Mittal
3. **Year:** 2018
4. **Venue:** NAACL 2018 (checked via: arXiv comment)
5. **DOI / link:** arXiv [1803.05355](https://arxiv.org/abs/1803.05355)
6. **Problem addressed:** No large dataset existed for verifying claims against textual evidence.
7. **Methodology:** Created claims by altering sentences from Wikipedia, verified them by annotators who did not see the source sentence, and labelled each Supported, Refuted or NotEnoughInfo with evidence sentences. Built a pipeline baseline and compared it with oracles.
8. **Models used:** Retrieval and entailment pipeline baseline.
9. **Dataset:** FEVER: 185,445 claims. Annotators agreed at Fleiss kappa 0.6841.
10. **Reported results:** Best accuracy labelling a claim with the correct evidence is 31.87%. Ignoring the evidence gives 50.91%.
11. **Advantages:** Large, evidence-annotated and public. It defines the retrieve-then-verify task.
12. **Limitations:** Claims come from Wikipedia text, not from real news or social claims.
13. **Research gaps:** Open-domain evidence and real-world claims.
14. **Possible improvements:** Retrieval from web sources and fact-check archives.
15. **Relevance to this project:** Defines the shape of the planned evidence module: retrieve evidence and report Supported, Refuted or Not Enough Info. The module is not built.

## 3.2 Learning Transferable Visual Models From Natural Language Supervision

1. **Title:** Learning Transferable Visual Models From Natural Language Supervision
2. **Authors:** Alec Radford, Jong Wook Kim, Chris Hallacy, Aditya Ramesh, Gabriel Goh, Sandhini Agarwal, Girish Sastry, Amanda Askell, Pamela Mishkin, Jack Clark, Gretchen Krueger, Ilya Sutskever
3. **Year:** 2021
4. **Venue:** ICML 2021, PMLR 139:8748-8763 (checked via: PMLR page)
5. **DOI / link:** arXiv [2103.00020](https://arxiv.org/abs/2103.00020)
6. **Problem addressed:** Vision systems trained on fixed label sets generalise poorly. Raw text about images is a broader source of supervision.
7. **Methodology:** Pre-train by predicting which caption goes with which image on 400 million image-text pairs, then use natural language to reference visual concepts for zero-shot transfer.
8. **Models used:** CLIP (image and text encoders).
9. **Dataset:** 400 million (image, text) pairs collected from the internet. Evaluated on over 30 existing vision datasets.
10. **Reported results:** Transfers non-trivially to most tasks and is often competitive with fully supervised baselines. It matches the original ResNet-50 on ImageNet zero-shot without using its training examples.
11. **Advantages:** A joint image-text embedding that is reusable for consistency checks.
12. **Limitations:** Large to download and run. Inherits web biases.
13. **Research gaps:** Not trained for news-specific mismatch.
14. **Possible improvements:** Fine-tune on news image-caption pairs.
15. **Relevance to this project:** The most likely backbone for the planned headline-and-image consistency check. It is not installed in this build.

## 3.3 MVAE: Multimodal Variational Autoencoder for Fake News Detection

1. **Title:** MVAE: Multimodal Variational Autoencoder for Fake News Detection
2. **Authors:** Dhruv Khattar, Jaipal Singh Goud, Manish Gupta, Vasudeva Varma
3. **Year:** 2019
4. **Venue:** The World Wide Web Conference (WWW 2019) (checked via: Crossref DOI)
5. **DOI / link:** DOI [10.1145/3308558.3313552](https://doi.org/10.1145/3308558.3313552)
6. **Problem addressed:** Existing fake-news detectors cannot learn a shared representation of text and image content in posts.
7. **Methodology:** A bimodal variational autoencoder coupled with a binary classifier, trained end to end. It has an encoder, a decoder and a fake-news detector module.
8. **Models used:** MVAE.
9. **Dataset:** Two standard microblog datasets: Weibo and Twitter.
10. **Reported results:** The abstract states that on average across the two datasets the model outperforms state-of-the-art methods. Exact figures are in the paper.
11. **Advantages:** Learns text and image jointly instead of treating them separately. Peer reviewed (WWW 2019).
12. **Limitations:** Microblog posts, with small, event-specific datasets that can leak event-related cues.
13. **Research gaps:** Cross-event and cross-platform generalisation.
14. **Possible improvements:** Evaluate on event-disjoint splits.
15. **Relevance to this project:** A reference design for any fusion model in the multimodal module. We would have to validate it on our own data.

## 3.4 Out-of-Context Misinformation Detection via Variational Domain-Invariant Learning with Test-Time Training

1. **Title:** Out-of-Context Misinformation Detection via Variational Domain-Invariant Learning with Test-Time Training
2. **Authors:** Xi Yang, Han Zhang, Zhijian Lin, Yibiao Hu, Hong Han
3. **Year:** 2026
4. **Venue:** AAAI 2026 (checked via: arXiv comment)
5. **DOI / link:** arXiv [2511.10213](https://arxiv.org/abs/2511.10213)
6. **Problem addressed:** Out-of-context misinformation (real images with wrong captions) models assume training and test data share a distribution, and fail on new news domains.
7. **Methodology:** VDT: a variational module that learns domain-invariant features, a domain consistency constraint, and test-time training with confidence-variance filtering that updates the encoder and classifier during testing.
8. **Models used:** VDT (variational encoder with test-time training).
9. **Dataset:** Benchmark: NewsCLIPpings, in domain adaptation settings.
10. **Reported results:** Outperforms state-of-the-art baselines under most domain adaptation settings (AAAI 2026, as stated on arXiv).
11. **Advantages:** Targets domain shift, which is our central problem. Recent.
12. **Limitations:** Evaluated on one benchmark. Test-time training adds complexity.
13. **Research gaps:** Evidence is not retrieved, so it relies on the pair alone.
14. **Possible improvements:** Combine with retrieved evidence.
15. **Relevance to this project:** Shows that domain shift is a recognised failure mode for multimodal misinformation as well, which matches what we measured for text.

## 3.5 NewsCLIPpings: Automatic Generation of Out-of-Context Multimodal Media

1. **Title:** NewsCLIPpings: Automatic Generation of Out-of-Context Multimodal Media
2. **Authors:** Grace Luo, Trevor Darrell, Anna Rohrbach
3. **Year:** 2021
4. **Venue:** EMNLP 2021 (checked via: arXiv comment)
5. **DOI / link:** arXiv [2104.05893](https://arxiv.org/abs/2104.05893)
6. **Problem addressed:** Datasets that generate image-text inconsistencies by manipulating text miss the case where both image and text are real but mismatched.
7. **Methodology:** Automatically retrieve convincing images for a caption through several strategies (inconsistent entities or semantic context), creating mismatched but unmanipulated pairs. Benchmark multimodal models.
8. **Models used:** Several state-of-the-art multimodal models.
9. **Dataset:** NewsCLIPpings: a large, automatically generated out-of-context dataset.
10. **Reported results:** Shows machine-driven image repurposing is a realistic threat, and that samples can mislead humans. Reports benchmark results across pretraining domains and visual backbones (see paper).
11. **Advantages:** Scales without manual labelling. EMNLP 2021.
12. **Limitations:** Automatically generated mismatches may be easier or different from real misinformation.
13. **Research gaps:** Real-world mismatches are subtler than generated ones.
14. **Possible improvements:** Add human-verified real cases.
15. **Relevance to this project:** The training and test source for a headline-and-image consistency check.

## 3.6 Open-Domain, Content-based, Multi-modal Fact-checking of Out-of-Context Images via Online Resources

1. **Title:** Open-Domain, Content-based, Multi-modal Fact-checking of Out-of-Context Images via Online Resources
2. **Authors:** Sahar Abdelnabi, Rakibul Hasan, Mario Fritz
3. **Year:** 2022
4. **Venue:** CVPR 2022 (checked via: arXiv comment)
5. **DOI / link:** arXiv [2112.00061](https://arxiv.org/abs/2112.00061)
6. **Problem addressed:** Out-of-context images are a cheap and effective way to spread false stories. Verification needs web evidence.
7. **Methodology:** A multi-modal cycle-consistency check: gather textual and visual evidence from the web, compare it with the paired caption or image, and use a consistency-checking network that mimics layered human reasoning (caption vs textual evidence, image vs visual evidence, image vs caption).
8. **Models used:** Consistency-Checking Network (CCN).
9. **Dataset:** A new benchmark for open-domain, content-based, multi-modal fact-checking.
10. **Reported results:** Significantly outperforms baselines that do not use external evidence.
11. **Advantages:** Inspectable (it shows the evidence it used) and open-domain. CVPR 2022.
12. **Limitations:** Depends on search engines and web availability.
13. **Research gaps:** Evidence quality and time-sensitivity.
14. **Possible improvements:** Cache and timestamp evidence.
15. **Relevance to this project:** The design closest to what our planned evidence module should do: show the sources it found and never invent them.

## 3.7 A Survey on Automated Fact-Checking

1. **Title:** A Survey on Automated Fact-Checking
2. **Authors:** Zhijiang Guo, Michael Schlichtkrull, Andreas Vlachos
3. **Year:** 2022
4. **Venue:** Transactions of the ACL (TACL) 2022 (checked via: arXiv comment)
5. **DOI / link:** arXiv [2108.11896](https://arxiv.org/abs/2108.11896)
6. **Problem addressed:** Misinformation spreads faster than people can check it, so automated fact-checking is studied.
7. **Methodology:** A survey of automated fact-checking from NLP: datasets, models and connections to related tasks, with a unified set of concepts and a list of future challenges.
8. **Models used:** No new model.
9. **Dataset:** No new dataset.
10. **Reported results:** None reported. It is a survey (TACL 2022).
11. **Advantages:** Shows the standard pipeline: claim detection, evidence retrieval, verdict prediction and justification production.
12. **Limitations:** Text-centric, and dated for LLM-based approaches.
13. **Research gaps:** Evidence retrieval, explainability and low-resource languages.
14. **Possible improvements:** Extend to multimodal claims.
15. **Relevance to this project:** The design reference for the evidence module and for our requirement that verdicts come with traceable sources.

## 3.8 "Why Should I Trust You?": Explaining the Predictions of Any Classifier

1. **Title:** "Why Should I Trust You?": Explaining the Predictions of Any Classifier
2. **Authors:** Marco Tulio Ribeiro, Sameer Singh, Carlos Guestrin
3. **Year:** 2016
4. **Venue:** KDD 2016, DOI 10.1145/2939672.2939778 (checked via: arXiv paper front matter)
5. **DOI / link:** DOI [10.1145/2939672.2939778](https://doi.org/10.1145/2939672.2939778); arXiv [1602.04938](https://arxiv.org/abs/1602.04938)
6. **Problem addressed:** Machine learning models are black boxes, and trust requires understanding their predictions.
7. **Methodology:** LIME explains a single prediction of any classifier by fitting an interpretable model locally around it. It also selects representative predictions with a submodular optimisation.
8. **Models used:** Model-agnostic explainer.
9. **Dataset:** Used on text (for example random forests) and image (neural networks) classifiers.
10. **Reported results:** Simulated and human-subject experiments show explanations help decide whether to trust a prediction, choose between models, improve an untrustworthy classifier and find why a classifier should not be trusted.
11. **Advantages:** Works on any model, and is easy to show to users. KDD 2016.
12. **Limitations:** The explanation is an approximation and can vary between runs.
13. **Research gaps:** Faithfulness is only local.
14. **Possible improvements:** Prefer exact attributions when the model allows.
15. **Relevance to this project:** We do not need LIME for the deployed text model: a linear model's term contributions are exact, and a test checks that they add up to the model's score. LIME would be needed for non-linear models.

## 3.9 A Unified Approach to Interpreting Model Predictions

1. **Title:** A Unified Approach to Interpreting Model Predictions
2. **Authors:** Scott Lundberg, Su-In Lee
3. **Year:** 2017
4. **Venue:** NeurIPS (NIPS) 2017 (checked via: arXiv comment)
5. **DOI / link:** arXiv [1705.07874](https://arxiv.org/abs/1705.07874)
6. **Problem addressed:** Complex models are accurate but hard to interpret, and it is unclear how the many explanation methods relate.
7. **Methodology:** SHAP assigns each feature an importance value for a prediction, from a unified class of additive feature importance measures with a unique solution that satisfies desirable properties.
8. **Models used:** Model-agnostic and model-specific SHAP estimators.
9. **Dataset:** Not dataset-specific.
10. **Reported results:** Unifies six existing methods and gives new methods with better computational performance and/or consistency with human intuition.
11. **Advantages:** Theoretical grounding and consistent attributions. NeurIPS 2017.
12. **Limitations:** Exact computation is expensive for large models.
13. **Research gaps:** Explanations do not prove correctness of the prediction.
14. **Possible improvements:** Use fast model-specific estimators.
15. **Relevance to this project:** For a linear model, the SHAP value reduces to coefficient times feature value (relative to a baseline), which is the kind of attribution we display.

## 3.10 SNIFFER: Multimodal Large Language Model for Explainable Out-of-Context Misinformation Detection

1. **Title:** SNIFFER: Multimodal Large Language Model for Explainable Out-of-Context Misinformation Detection
2. **Authors:** Peng Qi, Zehong Yan, Wynne Hsu, Mong Li Lee
3. **Year:** 2024
4. **Venue:** CVPR 2024 (checked via: arXiv comment)
5. **DOI / link:** arXiv [2403.03170](https://arxiv.org/abs/2403.03170)
6. **Problem addressed:** Out-of-context detectors judge image-text consistency but give no convincing explanations, which are essential for debunking.
7. **Methodology:** SNIFFER: a multimodal LLM with two-stage instruction tuning on InstructBLIP. Stage one aligns generic objects with news-domain entities, stage two uses language-only GPT-4-generated OOC instruction data. External tools and retrieval give contextual verification.
8. **Models used:** SNIFFER (instruction-tuned InstructBLIP).
9. **Dataset:** OOC misinformation benchmarks (see paper), with human evaluation of explanations.
10. **Reported results:** Surpasses the original MLLM by over 40% and outperforms state-of-the-art methods in detection accuracy, with accurate and persuasive explanations validated by quantitative and human evaluation.
11. **Advantages:** Produces human-readable explanations and uses external knowledge. CVPR 2024.
12. **Limitations:** Likely needs a large multimodal LLM and a GPU. LLM explanations can be fluent but wrong.
13. **Research gaps:** Faithfulness of generated explanations.
14. **Possible improvements:** Verify the explanation against retrieved evidence.
15. **Relevance to this project:** Recent state of the art for explainable multimodal checking. It is out of reach for our hardware budget, and its explanations would need the same faithfulness checks we apply to the text module.

