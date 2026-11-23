# Member 4: Engineering, responsible AI, calibration and interface research

Ten verified papers for this area. Bibliographic details (title, authors, venue, DOI or arXiv number) were checked against Crossref, arXiv, publisher or proceedings pages, and the source of each venue is named in the entry.

How to read each entry: fields 1 to 5 are bibliographic facts. Fields 6 to 10 (problem, methodology, models, dataset, reported results) stay within what the abstract or the cited page states; where an abstract gives no number the entry says so instead of guessing. Fields 11 to 15 (advantages, limitations, gaps, improvements, relevance) are our own assessment.

## 4.1 Model Cards for Model Reporting

1. **Title:** Model Cards for Model Reporting
2. **Authors:** Margaret Mitchell, Simone Wu, Andrew Zaldivar, Parker Barnes, Lucy Vasserman, Ben Hutchinson, Elena Spitzer, Inioluwa Deborah Raji, Timnit Gebru
3. **Year:** 2019
4. **Venue:** FAT* 2019, DOI 10.1145/3287560.3287596 (checked via: arXiv journal_ref)
5. **DOI / link:** DOI [10.1145/3287560.3287596](https://doi.org/10.1145/3287560.3287596); arXiv [1810.03993](https://arxiv.org/abs/1810.03993)
6. **Problem addressed:** Released models are used in high-impact settings without documentation of intended use and performance.
7. **Methodology:** Model cards: short documents accompanying a model, giving benchmarked evaluation under varied conditions and stating intended use, evaluation procedure and other relevant information. Example cards for a smiling-face detector and a toxic-comment detector.
8. **Models used:** No model. It proposes a documentation framework.
9. **Dataset:** Example cards use public data (see paper).
10. **Reported results:** None. It is a framework paper (FAT* 2019).
11. **Advantages:** A simple, adoptable template that makes limits visible.
12. **Limitations:** Voluntary and uneven in practice.
13. **Research gaps:** No standard way to check that a card is accurate.
14. **Possible improvements:** Generate the card from the saved evaluation, so it cannot drift.
15. **Relevance to this project:** Our model registry and the Models page act as a generated model card. The numbers are read from the evaluation file produced by the training script.

## 4.2 Datasheets for Datasets

1. **Title:** Datasheets for Datasets
2. **Authors:** Timnit Gebru, Jamie Morgenstern, Briana Vecchione, Jennifer Wortman Vaughan, Hanna Wallach, Hal Daumé, Kate Crawford
3. **Year:** 2021
4. **Venue:** Communications of the ACM, December 2021 (checked via: arXiv comment)
5. **DOI / link:** arXiv [1803.09010](https://arxiv.org/abs/1803.09010)
6. **Problem addressed:** No standard process for documenting datasets exists, with serious consequences in high-stakes domains.
7. **Methodology:** Datasheets for datasets: documentation of motivation, composition, collection process and recommended uses, by analogy with electronics datasheets.
8. **Models used:** None.
9. **Dataset:** Not dataset-specific.
10. **Reported results:** None. It is a proposal (CACM, December 2021).
11. **Advantages:** A question list that exposes gaps in provenance and licensing.
12. **Limitations:** Depends on dataset creators answering honestly.
13. **Research gaps:** Tooling that enforces the sheet.
14. **Possible improvements:** Version and check the sheet alongside the data.
15. **Relevance to this project:** We keep a manifest per dataset (source, licence, row counts, removed rows, label checks). The training dataset's licence is not stated on its card, and we record that fact instead of guessing.

## 4.3 Software Engineering for Machine Learning: A Case Study

1. **Title:** Software Engineering for Machine Learning: A Case Study
2. **Authors:** Saleema Amershi, Andrew Begel, Christian Bird, Robert DeLine, Harald Gall, Ece Kamar, Nachiappan Nagappan, Besmira Nushi, Thomas Zimmermann
3. **Year:** 2019
4. **Venue:** ICSE-SEIP 2019 (checked via: Crossref DOI)
5. **DOI / link:** DOI [10.1109/icse-seip.2019.00042](https://doi.org/10.1109/icse-seip.2019.00042)
6. **Problem addressed:** How do software teams build AI applications, and what is different from ordinary software engineering?
7. **Methodology:** An observational study of teams at Microsoft using a nine-stage machine learning workflow.
8. **Models used:** None.
9. **Dataset:** Not applicable (a case study of teams).
10. **Reported results:** Three aspects make AI fundamentally different: data discovery, management and versioning are harder, model customisation and reuse need different skills, and AI components are harder to treat as separate modules because models can become entangled.
11. **Advantages:** Concrete engineering practices from real teams. ICSE-SEIP 2019.
12. **Limitations:** Single company.
13. **Research gaps:** Tooling for data and model versioning in small teams.
14. **Possible improvements:** Lightweight versioning in student projects.
15. **Relevance to this project:** Our structure keeps data manifests, a model registry with versions, saved metrics and a version check, so that every analysis records which model version produced it.

## 4.4 On Calibration of Modern Neural Networks

1. **Title:** On Calibration of Modern Neural Networks
2. **Authors:** Chuan Guo, Geoff Pleiss, Yu Sun, Kilian Q. Weinberger
3. **Year:** 2017
4. **Venue:** ICML 2017 (checked via: arXiv comment)
5. **DOI / link:** arXiv [1706.04599](https://arxiv.org/abs/1706.04599)
6. **Problem addressed:** Are modern neural networks' probability estimates trustworthy?
7. **Methodology:** Experiments on how depth, width, weight decay and batch normalisation affect calibration, and a comparison of post-processing calibration methods.
8. **Models used:** Modern deep networks, with temperature scaling and other calibrators.
9. **Dataset:** Image and document classification datasets.
10. **Reported results:** Modern networks are poorly calibrated. On most datasets temperature scaling, a single-parameter variant of Platt scaling, is surprisingly effective.
11. **Advantages:** Simple, practical recipe. ICML 2017.
12. **Limitations:** Calibration holds only on data like the calibration set.
13. **Research gaps:** Calibration under distribution shift.
14. **Possible improvements:** Report calibration on out-of-distribution data as well.
15. **Relevance to this project:** We measure calibration error and report it for both test sets. It is low in-distribution and much worse on LIAR2, which supports not presenting the score as a probability of truth.

## 4.5 Selective Classification for Deep Neural Networks

1. **Title:** Selective Classification for Deep Neural Networks
2. **Authors:** Yonatan Geifman, Ran El-Yaniv
3. **Year:** 2017
4. **Venue:** NeurIPS (NIPS) 2017 (checked via: NeurIPS page)
5. **DOI / link:** arXiv [1705.08500](https://arxiv.org/abs/1705.08500)
6. **Problem addressed:** Selective classification (reject option) had not been studied for deep neural networks.
7. **Methodology:** A method that builds a selective classifier from a trained network. The user sets a desired risk level and the classifier rejects instances to meet it with high probability.
8. **Models used:** Selective wrappers around trained CNNs.
9. **Dataset:** CIFAR and ImageNet.
10. **Reported results:** For example, 2% error in top-5 ImageNet classification guaranteed with probability 99.9% at almost 60% test coverage.
11. **Advantages:** Formalises the trade-off between coverage and risk. NeurIPS 2017.
12. **Limitations:** Guarantees assume test data comes from the same distribution as the calibration data.
13. **Research gaps:** Selective classification under shift.
14. **Possible improvements:** Calibrate the threshold on a validation set from the target domain.
15. **Relevance to this project:** Supports the Unverified verdict. Our text model abstains below a confidence threshold, below 60 words and for unsupported scripts, and the guarantee limitation applies to our threshold as well.

## 4.6 Real Solutions for Fake News? Measuring the Effectiveness of General Warnings and Fact-Check Tags in Reducing Belief in False Stories on Social Media

1. **Title:** Real Solutions for Fake News? Measuring the Effectiveness of General Warnings and Fact-Check Tags in Reducing Belief in False Stories on Social Media
2. **Authors:** Katherine Clayton, Spencer Blair, Jonathan A. Busam, Samuel Forstner, John Glance, Guy Green, Anna Kawata, Akhila Kovvuri, Jonathan Martin, Evan Morgan, Morgan Sandhu, Rachel Sang, Rachel Scholz-Bright, Austin T. Welch, Andrew G. Wolff, Amanda Zhou, Brendan Nyhan
3. **Year:** 2019 (Crossref issued date)
4. **Venue:** Political Behavior (checked via: Crossref DOI)
5. **DOI / link:** DOI [10.1007/s11109-019-09533-0](https://doi.org/10.1007/s11109-019-09533-0)
6. **Problem addressed:** How effective are general warnings and fact-check tags at reducing belief in false stories on social media?
7. **Methodology:** A pre-registered survey experiment comparing a general warning, a Disputed tag and a Rated false tag on perceived accuracy of headlines.
8. **Models used:** None.
9. **Dataset:** Survey data from U.S. adults (2,994 respondents in the abstract excerpt we retrieved).
10. **Reported results:** Adding a Rated false tag lowers perceived accuracy more than a Disputed tag. A general warning also lowered belief in true headlines.
11. **Advantages:** Controlled comparison of interface wording. Peer reviewed (Political Behavior).
12. **Limitations:** A single survey experiment with U.S. adults, so findings may not transfer to other countries or to real feeds.
13. **Research gaps:** Long-term effects and real feeds.
14. **Possible improvements:** Field trials.
15. **Relevance to this project:** Wording matters. Our verdict names are chosen to say what was measured (Likely Fake, Unverified, Indicators Only), and we avoid blanket warnings that would reduce trust in true news.

## 4.7 The Implied Truth Effect: Attaching Warnings to a Subset of Fake News Headlines Increases Perceived Accuracy of Headlines Without Warnings

1. **Title:** The Implied Truth Effect: Attaching Warnings to a Subset of Fake News Headlines Increases Perceived Accuracy of Headlines Without Warnings
2. **Authors:** Gordon Pennycook, Adam Bear, Evan T. Collins, David G. Rand
3. **Year:** 2020
4. **Venue:** Management Science (checked via: Crossref DOI)
5. **DOI / link:** DOI [10.1287/mnsc.2019.3478](https://doi.org/10.1287/mnsc.2019.3478)
6. **Problem addressed:** Warnings attached to fact-checked headlines may have an unintended consequence.
7. **Methodology:** A formal model and two online experiments (n = 5,271 and n = 1,568) testing whether headlines without a warning are seen as validated.
8. **Models used:** A Bayesian belief-updating model.
9. **Dataset:** Survey experiments on Mechanical Turk workers.
10. **Reported results:** Warnings modestly reduce perceived accuracy of tagged false headlines, but untagged false headlines are seen as more accurate than in the control (the implied truth effect). Attaching verifications to some true headlines removes and slightly reverses it.
11. **Advantages:** Identifies a design risk before it ships. Management Science 2020.
12. **Limitations:** Crowdworker samples and headline-level tasks.
13. **Research gaps:** Effects in real platforms.
14. **Possible improvements:** Test with mixed tagged and verified content.
15. **Relevance to this project:** Our Unverified and Indicators Only labels say explicitly that no verdict was made, because absence of a Likely Fake label must never be read as a sign that content is genuine.

## 4.8 Towards A Rigorous Science of Interpretable Machine Learning

1. **Title:** Towards A Rigorous Science of Interpretable Machine Learning
2. **Authors:** Finale Doshi-Velez, Been Kim
3. **Year:** 2017
4. **Venue:** arXiv preprint (checked via: arXiv (no venue listed))
5. **DOI / link:** arXiv [1702.08608](https://arxiv.org/abs/1702.08608)
6. **Problem addressed:** There is little agreement on what interpretable machine learning is or how to measure it.
7. **Methodology:** A position paper that defines interpretability, says when it is needed, and proposes a taxonomy for rigorous evaluation.
8. **Models used:** None.
9. **Dataset:** None.
10. **Reported results:** None. It exposes open questions.
11. **Advantages:** Separates application-grounded, human-grounded and functionally grounded evaluation.
12. **Limitations:** A position paper with no experiments.
13. **Research gaps:** Agreed metrics for explanation quality.
14. **Possible improvements:** Human evaluation of the explanation panel.
15. **Relevance to this project:** Helps us state what our explanation is: exact (functionally grounded), not shown to improve human decisions. The latter has not been tested and is listed as future work.

## 4.9 DistilBERT, a distilled version of BERT: smaller, faster, cheaper and lighter

1. **Title:** DistilBERT, a distilled version of BERT: smaller, faster, cheaper and lighter
2. **Authors:** Victor Sanh, Lysandre Debut, Julien Chaumond, Thomas Wolf
3. **Year:** 2019
4. **Venue:** arXiv preprint (NeurIPS 2019 EMC2 workshop version not checked here) (checked via: arXiv)
5. **DOI / link:** arXiv [1910.01108](https://arxiv.org/abs/1910.01108)
6. **Problem addressed:** Large pre-trained language models are hard to run on edge devices or under constrained compute.
7. **Methodology:** Knowledge distillation during pre-training with a triple loss combining language modelling, distillation and cosine-distance losses.
8. **Models used:** DistilBERT.
9. **Dataset:** General-purpose pre-training with evaluation on language understanding tasks (see paper).
10. **Reported results:** Reduces BERT's size by 40% while retaining 97% of its language understanding capabilities and being 60% faster. A proof-of-concept and an on-device study are reported.
11. **Advantages:** Practical route to transformer quality on modest hardware.
12. **Limitations:** Quality is slightly below the full model.
13. **Research gaps:** Not specific to misinformation.
14. **Possible improvements:** Fine-tune on our data with early stopping and calibration.
15. **Relevance to this project:** The most realistic route to a transformer-based text model on a student laptop. Not trained here.

## 4.10 MobileNetV2: Inverted Residuals and Linear Bottlenecks

1. **Title:** MobileNetV2: Inverted Residuals and Linear Bottlenecks
2. **Authors:** Mark Sandler, Andrew Howard, Menglong Zhu, Andrey Zhmoginov, Liang-Chieh Chen
3. **Year:** 2018
4. **Venue:** CVPR 2018, pp. 4510-4520 (checked via: arXiv journal_ref)
5. **DOI / link:** arXiv [1801.04381](https://arxiv.org/abs/1801.04381)
6. **Problem addressed:** Image models need to run efficiently on mobile hardware.
7. **Methodology:** MobileNetV2: inverted residual blocks with thin bottleneck layers, lightweight depthwise convolutions and removal of non-linearities in narrow layers.
8. **Models used:** MobileNetV2, with SSDLite for detection and Mobile DeepLabv3 for segmentation.
9. **Dataset:** ImageNet classification, COCO detection, VOC segmentation.
10. **Reported results:** Improves state-of-the-art mobile models across a range of sizes. The paper also analyses the trade-off between accuracy, multiply-adds and parameters.
11. **Advantages:** Small and fast, so a sensible backbone for CPU inference. CVPR 2018.
12. **Limitations:** Not designed for forensics, which needs high-frequency detail that downscaling removes.
13. **Research gaps:** Forensic use of lightweight backbones.
14. **Possible improvements:** Evaluate on resized and compressed fakes.
15. **Relevance to this project:** A backbone candidate for the image and video modules under our limited-hardware constraint.

