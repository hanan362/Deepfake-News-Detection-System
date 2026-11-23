# Member 1: NLP, text datasets and evaluation

Ten verified papers for this area. Bibliographic details (title, authors, venue, DOI or arXiv number) were checked against Crossref, arXiv, publisher or proceedings pages, and the source of each venue is named in the entry.

How to read each entry: fields 1 to 5 are bibliographic facts. Fields 6 to 10 (problem, methodology, models, dataset, reported results) stay within what the abstract or the cited page states; where an abstract gives no number the entry says so instead of guessing. Fields 11 to 15 (advantages, limitations, gaps, improvements, relevance) are our own assessment.

## 1.1 Fake News Detection on Social Media

1. **Title:** Fake News Detection on Social Media
2. **Authors:** Kai Shu, Amy Sliva, Suhang Wang, Jiliang Tang, Huan Liu
3. **Year:** 2017
4. **Venue:** ACM SIGKDD Explorations Newsletter (checked via: Crossref DOI)
5. **DOI / link:** DOI [10.1145/3137597.3137600](https://doi.org/10.1145/3137597.3137600)
6. **Problem addressed:** Fake news spreads on social media at low cost and high speed. Detecting it from content alone is hard because fake news is written to look credible, so extra signals such as user engagement are needed, and those signals are big, noisy and incomplete.
7. **Methodology:** A survey. It reviews psychological and social theories of fake news, detection algorithms from a data-mining viewpoint (content-based and social-context-based), evaluation metrics and datasets.
8. **Models used:** No new model. It organises existing approaches.
9. **Dataset:** No new dataset. It lists representative datasets from the literature.
10. **Reported results:** None reported. It is a review and lists open problems and future directions.
11. **Advantages:** Clear taxonomy that separates what can be done from article text and what needs social context. A good map of the field for newcomers.
12. **Limitations:** Dated 2017, so it predates large pretrained language models, LLM-generated news and multimodal detectors.
13. **Research gaps:** Names the lack of benchmark datasets and of explainable, early-stage detection as open problems.
14. **Possible improvements:** Re-run the taxonomy with transformer, LLM and multimodal methods (later surveys in this folder do part of this).
15. **Relevance to this project:** Defines the problem framing we use: our text module is a content-only detector, so it has no access to propagation or user signals. That limit is stated in the product.

## 1.2 "Liar, Liar Pants on Fire": A New Benchmark Dataset for Fake News Detection

1. **Title:** "Liar, Liar Pants on Fire": A New Benchmark Dataset for Fake News Detection
2. **Authors:** William Yang Wang
3. **Year:** 2017
4. **Venue:** ACL 2017 (short papers) (checked via: arXiv comment)
5. **DOI / link:** arXiv [1705.00648](https://arxiv.org/abs/1705.00648)
6. **Problem addressed:** Statistical fake-news detection was limited by the lack of large labelled benchmark datasets.
7. **Methodology:** Collected about 12.8K manually labelled short statements from PolitiFact.com over a decade, each with an analysis report and source links. Evaluated detection from surface-level linguistic patterns, and proposed a hybrid convolutional neural network that integrates meta-data with text.
8. **Models used:** Text-only baselines and a hybrid CNN with meta-data.
9. **Dataset:** LIAR (new, public, about 12.8K labelled statements from PolitiFact).
10. **Reported results:** The abstract states that the hybrid approach improves on a text-only deep learning model. Exact scores are in the paper's tables.
11. **Advantages:** Public and human-labelled, with analysis reports and source links for each statement.
12. **Limitations:** Statements are short and political. Labels come from one fact-checking site and reflect its editorial process.
13. **Research gaps:** Text alone gives weak signal on short claims, so evidence retrieval is needed.
14. **Possible improvements:** Link each statement to retrieved evidence; test cross-dataset transfer.
15. **Relevance to this project:** Our external test set (LIAR2, a later benchmark in the same line of work) comes from this family of data. The near-chance score of our article-trained model on it is the main honest finding of the text module.

## 1.3 Automatic Detection of Fake News

1. **Title:** Automatic Detection of Fake News
2. **Authors:** Verónica Pérez-Rosas, Bennett Kleinberg, Alexandra Lefevre, Rada Mihalcea
3. **Year:** 2018
4. **Venue:** COLING 2018, pp. 3391-3401 (checked via: ACL Anthology C18-1287)
5. **DOI / link:** arXiv [1708.07104](https://arxiv.org/abs/1708.07104); ACL Anthology [C18-1287](https://aclanthology.org/C18-1287/)
6. **Problem addressed:** Misleading information in online news makes it hard to find trustworthy sources, which creates the need for computational reliability tools.
7. **Methodology:** Introduced two datasets covering seven news domains and described their collection, annotation and validation. Analysed linguistic differences between fake and legitimate news, ran learning experiments to build detectors, and compared automatic with manual identification.
8. **Models used:** Feature-based classifiers on linguistic features (the paper's own experiments).
9. **Dataset:** Two new datasets across seven news domains (construction is described in the paper).
10. **Reported results:** The COLING abstract reports detectors with accuracies of up to 76%, plus a comparison of automatic and manual identification. The arXiv abstract gives no figure.
11. **Advantages:** Full-length articles across several domains, with linguistic analysis that explains what separates fake from legitimate text.
12. **Limitations:** Linguistic cues found in one collection may reflect how the data was made rather than deception in general. The best reported accuracy (76%) is far below in-distribution scores on larger corpora.
13. **Research gaps:** Generalisation between domains and datasets is raised but not solved.
14. **Possible improvements:** Evaluate across domains and datasets, not only within one collection.
15. **Relevance to this project:** A closer match than LIAR to our training data (full-length articles). It supports our decision to avoid claiming general fake-news detection from article style alone.

## 1.4 Detection of Online Fake News Using N-Gram Analysis and Machine Learning Techniques

1. **Title:** Detection of Online Fake News Using N-Gram Analysis and Machine Learning Techniques
2. **Authors:** Hadeer Ahmed, Issa Traore, Sherif Saad
3. **Year:** 2017
4. **Venue:** Lecture Notes in Computer Science (conference proceedings volume) (checked via: Crossref DOI)
5. **DOI / link:** DOI [10.1007/978-3-319-69155-8_9](https://doi.org/10.1007/978-3-319-69155-8_9)
6. **Problem addressed:** Detect fake news from the text of articles using simple, fast, reproducible methods.
7. **Methodology:** n-gram analysis with two feature-extraction techniques (term frequency and TF-IDF) compared across six classifiers.
8. **Models used:** Six classifiers (named in the paper). The best one in the abstract is a linear SVM.
9. **Dataset:** Not stated in the abstract. See the paper for the corpus used.
10. **Reported results:** The best result in the abstract is TF-IDF with a linear SVM at 92% accuracy.
11. **Advantages:** Cheap and reproducible. Shows a TF-IDF plus linear model is a strong baseline.
12. **Limitations:** The abstract reports one accuracy figure and no test on unrelated data, so it says little about other sources.
13. **Research gaps:** No test on unrelated data, and no explanation of why the features work.
14. **Possible improvements:** Cross-dataset testing and checks for source-style shortcuts.
15. **Relevance to this project:** The same family as our deployed baseline (TF-IDF with logistic regression). We add what this paper does not: removal of source artefacts, an external dataset test, an abstain rule and exact term-level explanations.

## 1.5 Combating Misinformation in the Age of LLMs: Opportunities and Challenges

1. **Title:** Combating Misinformation in the Age of LLMs: Opportunities and Challenges
2. **Authors:** Canyu Chen, Kai Shu
3. **Year:** 2023 (arXiv)
4. **Venue:** arXiv preprint (checked via: arXiv (no venue listed))
5. **DOI / link:** arXiv [2311.05656](https://arxiv.org/abs/2311.05656)
6. **Problem addressed:** LLMs can both help fight misinformation, through world knowledge and reasoning, and generate deceptive misinformation at scale.
7. **Methodology:** A survey of how misinformation was combated before LLMs, then of current work and an outlook on two questions: how to use LLMs against misinformation, and how to combat LLM-generated misinformation.
8. **Models used:** No new model.
9. **Dataset:** No new dataset.
10. **Reported results:** None reported. It is a survey and calls for interdisciplinary work.
11. **Advantages:** Recent, broad (the arXiv version has over 600 references) and frames the two-sided role of LLMs.
12. **Limitations:** A fast-moving field, so parts will date quickly.
13. **Research gaps:** Evaluation of LLM-based detectors and robustness to LLM-written misinformation.
14. **Possible improvements:** Add benchmarks that separate human-written from LLM-written misinformation.
15. **Relevance to this project:** Justifies our statement that text-style detectors trained on older human-written data may fail on LLM-written news, and our plan to keep any LLM component optional and clearly labelled.

## 1.6 Defending Against Neural Fake News

1. **Title:** Defending Against Neural Fake News
2. **Authors:** Rowan Zellers, Ari Holtzman, Hannah Rashkin, Yonatan Bisk, Ali Farhadi, Franziska Roesner, Yejin Choi
3. **Year:** 2019
4. **Venue:** NeurIPS 2019 (checked via: arXiv comment)
5. **DOI / link:** arXiv [1905.12616](https://arxiv.org/abs/1905.12616)
6. **Problem addressed:** Text generators can produce targeted propaganda that mimics real news, so defences must be studied from the adversary's point of view.
7. **Methodology:** Presented Grover, a controllable generator that writes an article from a headline, and studied how well discriminators can detect its output.
8. **Models used:** Grover (generator) and discriminators, including Grover itself as a detector.
9. **Dataset:** News articles used to train Grover, and generated articles for detection experiments.
10. **Reported results:** Best discriminators reach 73% accuracy at telling neural fake news from real news given moderate training data. Grover as its own discriminator reaches 92%. Humans rated Grover's text as more trustworthy than human-written disinformation.
11. **Advantages:** Frames detection as a security problem and shows that the strongest generator is also the best detector.
12. **Limitations:** Tested on 2019-era generators. Detection of newer LLMs is a different problem.
13. **Research gaps:** Detectors depend on access to the generator or similar ones.
14. **Possible improvements:** Evaluate on current LLMs and under paraphrasing attacks.
15. **Relevance to this project:** Warns that detection can depend on generator artefacts. Our text module makes no claim about machine-written text, and the limits text says it was trained on human-labelled articles.

## 1.7 Can LLM-Generated Misinformation Be Detected?

1. **Title:** Can LLM-Generated Misinformation Be Detected?
2. **Authors:** Canyu Chen, Kai Shu
3. **Year:** 2024
4. **Venue:** ICLR 2024 (checked via: arXiv comment)
5. **DOI / link:** arXiv [2309.13788](https://arxiv.org/abs/2309.13788)
6. **Problem addressed:** Is LLM-generated misinformation more harmful than human-written misinformation? The paper studies this through detection difficulty.
7. **Methodology:** Built a taxonomy of LLM-generated misinformation, categorised and validated realistic generation methods, and measured how hard such text is for humans and detectors to identify.
8. **Models used:** Human raters and several detectors.
9. **Dataset:** Misinformation generated with LLMs by the taxonomy's methods, compared with human-written misinformation of the same semantics.
10. **Reported results:** LLM-generated misinformation can be harder to detect for humans and for detectors than human-written misinformation with the same meaning.
11. **Advantages:** Controls for meaning, so the difference comes from style. Peer reviewed at ICLR 2024.
12. **Limitations:** Results depend on the LLMs and prompts used at the time.
13. **Research gaps:** Detectors trained on human-written misinformation do not transfer to LLM-written text.
14. **Possible improvements:** Train and test with mixed human and LLM text.
15. **Relevance to this project:** Directly supports the distribution-shift warning in our limitations. A TF-IDF baseline trained on older articles should not be trusted on LLM-written news.

## 1.8 Bad Actor, Good Advisor: Exploring the Role of Large Language Models in Fake News Detection

1. **Title:** Bad Actor, Good Advisor: Exploring the Role of Large Language Models in Fake News Detection
2. **Authors:** Beizhe Hu, Qiang Sheng, Juan Cao, Yuhui Shi, Yang Li, Danding Wang, Peng Qi
3. **Year:** 2024
4. **Venue:** AAAI 2024 (checked via: arXiv journal_ref, DOI 10.1609/aaai.v38i20.30214)
5. **DOI / link:** DOI [10.1609/aaai.v38i20.30214](https://doi.org/10.1609/aaai.v38i20.30214); arXiv [2309.12247](https://arxiv.org/abs/2309.12247)
6. **Problem addressed:** Small language models (SLMs) lack knowledge and capability for fake-news detection. Do large language models help?
7. **Methodology:** Empirical study of an LLM (GPT-3.5) on fake-news detection, then a proposed adaptive rationale guidance network (ARG) in which an SLM selectively learns from LLM rationales, and a rationale-free version (ARG-D) obtained by distillation.
8. **Models used:** GPT-3.5 as an advisor, a fine-tuned BERT as the baseline SLM, and ARG and ARG-D.
9. **Dataset:** Two real-world datasets (named in the paper).
10. **Reported results:** The LLM exposes fake news and gives multi-perspective rationales but underperforms a fine-tuned BERT. ARG and ARG-D outperform SLM-based, LLM-based and combined baselines on both datasets.
11. **Advantages:** Shows a practical split: the SLM decides and the LLM explains. ARG-D works without querying an LLM, so it suits cost-limited use.
12. **Limitations:** Needs an LLM during training. Evaluated on two datasets only.
13. **Research gaps:** Reliability of LLM rationales is not guaranteed.
14. **Possible improvements:** Verify the rationales against retrieved evidence.
15. **Relevance to this project:** A candidate path for our advanced text model: a fine-tuned small model with an optional, clearly labelled rationale source. We have not built it, and the registry lists no such model.

## 1.9 Ax-to-Grind Urdu: Benchmark Dataset for Urdu Fake News Detection

1. **Title:** Ax-to-Grind Urdu: Benchmark Dataset for Urdu Fake News Detection
2. **Authors:** Sheetal Harris, Jinshuo Liu, Hassan Jalil Hadi, Yue Cao
3. **Year:** 2023
4. **Venue:** IEEE TrustCom 2023 (also arXiv:2403.14037) (checked via: Crossref DOI 10.1109/trustcom60117.2023.00343)
5. **DOI / link:** DOI [10.1109/trustcom60117.2023.00343](https://doi.org/10.1109/trustcom60117.2023.00343); arXiv [2403.14037](https://arxiv.org/abs/2403.14037)
6. **Problem addressed:** Urdu fake-news detection lacks large, public, manually verified datasets. Earlier Urdu datasets are small, domain-restricted, not public, or translated from English.
7. **Methodology:** Curated Ax-to-Grind Urdu and benchmarked it with an ensemble of multilingual transformers.
8. **Models used:** Ensemble of mBERT, XLNet and XLM-RoBERTa.
9. **Dataset:** Ax-to-Grind Urdu: 10,083 fake and real news items in fifteen domains, 2017 to 2023, from Pakistani and Indian Urdu sources and crowdsourcing, annotated by expert journalists.
10. **Reported results:** Reported with F1, accuracy, precision, recall and MCC. The abstract gives no figures. See the paper.
11. **Advantages:** Journalist-annotated, fifteen domains and 2017 to 2023, which the authors present as closing gaps in earlier Urdu datasets.
12. **Limitations:** Licence and availability must be checked before use. The abstract gives no figures, so results must be read from the paper.
13. **Research gaps:** Urdu resources remain small compared with English. Cross-dataset results are not reported in the abstract.
14. **Possible improvements:** Cross-dataset tests with the 2020 FIRE Urdu data.
15. **Relevance to this project:** The natural next step for Urdu support. Our system currently declines Arabic-script text rather than guess, and the planned Urdu baseline would start from this dataset.

## 1.10 Overview of the Shared Task on Fake News Detection in Urdu at FIRE 2020

1. **Title:** Overview of the Shared Task on Fake News Detection in Urdu at FIRE 2020
2. **Authors:** Maaz Amjad, Grigori Sidorov, Alisa Zhila, Alexander Gelbukh, Paolo Rosso
3. **Year:** 2022 (arXiv; the shared task was held in 2020)
4. **Venue:** FIRE 2020 shared-task overview (arXiv preprint) (checked via: arXiv (no venue listed))
5. **DOI / link:** arXiv [2207.11893](https://arxiv.org/abs/2207.11893)
6. **Problem addressed:** No shared benchmark existed for fake-news detection in Urdu.
7. **Methodology:** Overview of the first shared task on Urdu fake-news detection (FIRE 2020), posed as binary real/fake classification. Participants used methods from classical machine learning to neural networks.
8. **Models used:** Participant systems, from feature-based classifiers to BERT-based models.
9. **Dataset:** 900 annotated articles for training and 400 for testing in five domains: health, sports, showbiz, technology, business.
10. **Reported results:** 42 teams registered from 6 countries and 9 submitted results. The best system reached an F-score of 0.90, and the BERT-based approach outperformed other techniques.
11. **Advantages:** Common test set and many independent systems. Gives a realistic picture of what is achievable for Urdu.
12. **Limitations:** Small dataset and five domains. The arXiv record was deposited in 2022 for a 2020 shared task.
13. **Research gaps:** Small scale and limited domains.
14. **Possible improvements:** Larger, more varied data such as Ax-to-Grind Urdu.
15. **Relevance to this project:** Gives a baseline for Urdu work, and shows that multilingual BERT-type models are the standard answer, which differs from our English TF-IDF baseline.

