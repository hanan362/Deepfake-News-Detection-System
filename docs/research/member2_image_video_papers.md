# Member 2: Image and video computer vision

Ten verified papers for this area. Bibliographic details (title, authors, venue, DOI or arXiv number) were checked against Crossref, arXiv, publisher or proceedings pages, and the source of each venue is named in the entry.

How to read each entry: fields 1 to 5 are bibliographic facts. Fields 6 to 10 (problem, methodology, models, dataset, reported results) stay within what the abstract or the cited page states; where an abstract gives no number the entry says so instead of guessing. Fields 11 to 15 (advantages, limitations, gaps, improvements, relevance) are our own assessment.

## 2.1 FaceForensics++: Learning to Detect Manipulated Facial Images

1. **Title:** FaceForensics++: Learning to Detect Manipulated Facial Images
2. **Authors:** Andreas Rössler, Davide Cozzolino, Luisa Verdoliva, Christian Riess, Justus Thies, Matthias Nießner
3. **Year:** 2019
4. **Venue:** ICCV 2019 (checked via: ICCV page and project page)
5. **DOI / link:** arXiv [1901.08971](https://arxiv.org/abs/1901.08971)
6. **Problem addressed:** Realistic image manipulation threatens trust in digital content and can spread fake news. How realistic is it, and how hard is it to detect?
7. **Methodology:** Built an automated benchmark for facial manipulation detection based on four methods (DeepFakes, Face2Face, FaceSwap, NeuralTextures) at random compression levels and sizes, then analysed data-driven forgery detectors.
8. **Models used:** Learned forgery detectors, including ones that use domain-specific knowledge such as face tracking, compared with human observers.
9. **Dataset:** FaceForensics++: a public benchmark with a hidden test set and over 1.8 million manipulated images, more than an order of magnitude larger than comparable forgery datasets.
10. **Reported results:** Using domain-specific knowledge improves detection accuracy even under strong compression and clearly outperforms human observers.
11. **Advantages:** Standard benchmark with controlled compression levels, which matches how video is shared.
12. **Limitations:** Covers four face-manipulation methods from its era. Detectors trained here often generalise poorly to newer methods.
13. **Research gaps:** Generalisation to unseen manipulation methods.
14. **Possible improvements:** Cross-dataset and cross-method evaluation as the default.
15. **Relevance to this project:** The reference dataset for the planned video module. It is not built, and the registry lists video as planned.

## 2.2 Celeb-DF: A Large-scale Challenging Dataset for DeepFake Forensics

1. **Title:** Celeb-DF: A Large-scale Challenging Dataset for DeepFake Forensics
2. **Authors:** Yuezun Li, Xin Yang, Pu Sun, Honggang Qi, Siwei Lyu
3. **Year:** 2020
4. **Venue:** CVPR 2020, pp. 3207-3216 (checked via: CVF open access)
5. **DOI / link:** arXiv [1909.12962](https://arxiv.org/abs/1909.12962)
6. **Problem addressed:** Existing DeepFake datasets have low visual quality and do not resemble DeepFakes circulating on the internet.
7. **Methodology:** Created a dataset with an improved synthesis process and evaluated existing detection methods and datasets on it.
8. **Models used:** Existing detectors evaluated on the new data.
9. **Dataset:** Celeb-DF: 5,639 high-quality DeepFake videos of celebrities.
10. **Reported results:** The evaluation shows the escalated difficulty Celeb-DF poses to current detection methods and datasets. See the paper for scores.
11. **Advantages:** Higher visual quality, so a more demanding test than earlier datasets.
12. **Limitations:** Face-swap only and celebrity subjects.
13. **Research gaps:** Detectors that score well on older sets drop on this one, which shows over-fitting to dataset artefacts.
14. **Possible improvements:** Report results across datasets, not a single benchmark.
15. **Relevance to this project:** A harder second test set for any video detector we later add, so we would not report a single in-dataset score.

## 2.3 The DeepFake Detection Challenge (DFDC) Dataset

1. **Title:** The DeepFake Detection Challenge (DFDC) Dataset
2. **Authors:** Brian Dolhansky, Joanna Bitton, Ben Pflaum, Jikuo Lu, Russ Howes, Menglin Wang, Cristian Canton Ferrer
3. **Year:** 2020
4. **Venue:** arXiv preprint (checked via: arXiv (no venue listed))
5. **DOI / link:** arXiv [2006.07397](https://arxiv.org/abs/2006.07397)
6. **Problem addressed:** Counter face-swap deepfakes with training data and a public competition, using consenting subjects.
7. **Methodology:** Built a very large face-swap video dataset, ran the Deepfake Detection Challenge on Kaggle, and analysed the top submissions.
8. **Models used:** Top Kaggle submissions (analysed in the paper) and a model trained only on the dataset.
9. **Dataset:** DFDC: over 100,000 clips from 3,426 paid actors, produced with several Deepfake, GAN-based and non-learned methods.
10. **Reported results:** Detection is extremely difficult and still unsolved. A model trained only on DFDC can generalise to real in-the-wild deepfake videos and can be a useful analysis tool.
11. **Advantages:** Largest public face-swap video dataset at the time, with consent from every subject.
12. **Limitations:** arXiv preprint. The dataset is staged with paid actors, so the abstract's claim about in-the-wild transfer should be read with that in mind.
13. **Research gaps:** Best competition models are heavy ensembles that are impractical for limited hardware.
14. **Possible improvements:** Lightweight models with a competition-grade evaluation.
15. **Relevance to this project:** Supports our stance that a video module must be validated on out-of-distribution clips and must run on modest hardware.

## 2.4 DeepFakes and Beyond: A Survey of Face Manipulation and Fake Detection

1. **Title:** DeepFakes and Beyond: A Survey of Face Manipulation and Fake Detection
2. **Authors:** Ruben Tolosana, Ruben Vera-Rodriguez, Julian Fierrez, Aythami Morales, Javier Ortega-Garcia
3. **Year:** 2020
4. **Venue:** Information Fusion, 2020 (checked via: arXiv journal_ref)
5. **DOI / link:** arXiv [2001.00179](https://arxiv.org/abs/2001.00179)
6. **Problem addressed:** Very realistic fake content can now be generated, with consequences for society. The paper surveys face manipulation and its detection.
7. **Methodology:** A survey of four manipulation types: entire face synthesis, identity swap (DeepFakes), attribute manipulation and expression swap. For each it covers techniques, public databases and key benchmarks, with a summary of results.
8. **Models used:** No new model.
9. **Dataset:** No new dataset. It reviews existing public databases.
10. **Reported results:** No new results. It summarises results from existing evaluations and discusses open issues and future trends.
11. **Advantages:** One map of manipulation types, datasets and benchmarks.
12. **Limitations:** Face-centred, and written in 2020, so diffusion-based generation is not covered.
13. **Research gaps:** Generalisation to unseen manipulations and reliable benchmarks.
14. **Possible improvements:** Update with diffusion-era methods (see Corvi and Ojha).
15. **Relevance to this project:** Background reading for the video and image modules, and for the naming used in our documents.

## 2.5 Decoupling Forgery Semantics for Generalizable Deepfake Detection

1. **Title:** Decoupling Forgery Semantics for Generalizable Deepfake Detection
2. **Authors:** Wei Ye, Xinan He, Feng Ding
3. **Year:** 2024
4. **Venue:** BMVC 2024 (checked via: arXiv comment)
5. **DOI / link:** arXiv [2406.09739](https://arxiv.org/abs/2406.09739)
6. **Problem addressed:** DeepFake detectors over-fit to method-specific forgery traces and content, so they generalise poorly to unseen forgery technologies.
7. **Methodology:** Decouple forgery semantics so that common forgery semantics, shared across methods, can be extracted. Adds an adaptive high-pass module and a two-stage training strategy to improve the independence of decoupled semantics.
8. **Models used:** A decoupling network with an adaptive high-pass module.
9. **Dataset:** Evaluated on FF++, Celeb-DF, DFD and DFDC.
10. **Reported results:** The abstract reports excellent detection and generalisation performance across these four datasets but gives no figures.
11. **Advantages:** Targets the central open problem (generalisation) and is peer reviewed (BMVC 2024). Code is released.
12. **Limitations:** Evaluated on the standard academic datasets, not on social-media-compressed video.
13. **Research gaps:** Robustness to platform compression and new generators.
14. **Possible improvements:** Add compression and re-encoding robustness tests.
15. **Relevance to this project:** A candidate technique for the planned video module and a reminder that cross-dataset results are the figure that counts.

## 2.6 Bridging the Gap Between Ideal and Real-world Evaluation: Benchmarking AI-Generated Image Detection in Challenging Scenarios

1. **Title:** Bridging the Gap Between Ideal and Real-world Evaluation: Benchmarking AI-Generated Image Detection in Challenging Scenarios
2. **Authors:** Chunxiao Li, Xiaoxiao Wang, Meiling Li, Boming Miao, Peng Sun, Yunjian Zhang, Xiangyang Ji, Yao Zhu
3. **Year:** 2025
4. **Venue:** ICCV 2025 (checked via: arXiv comment)
5. **DOI / link:** arXiv [2509.09172](https://arxiv.org/abs/2509.09172)
6. **Problem addressed:** Detectors of AI-generated images are rarely tested under realistic conditions such as re-sharing and re-capture.
7. **Methodology:** Introduced the Real-World Robustness Dataset (RRDataset) with three evaluation dimensions: scenario generalisation (seven scenarios including war, disasters, politics, health), robustness to internet transmission through social platforms, and robustness to re-digitisation. Benchmarked many detectors and vision-language models and ran a human study.
8. **Models used:** 17 detectors and 10 vision-language models, plus 192 human participants.
9. **Dataset:** RRDataset (new).
10. **Reported results:** Benchmarking reveals the limits of current AI-image detectors under real-world conditions, and the paper stresses the value of human adaptability. See the paper for numbers.
11. **Advantages:** Tests the conditions that matter for news images: sharing chains and screen re-capture. ICCV 2025.
12. **Limitations:** Static snapshot of detectors and generators at the time.
13. **Research gaps:** Reliable detection after social-media compression.
14. **Possible improvements:** Include compression chains in training augmentation.
15. **Relevance to this project:** Strong support for refusing to give a verdict on images: shared news images are exactly the case where current detectors are weakest. Our image module reports measurements only.

## 2.7 CNN-generated images are surprisingly easy to spot... for now

1. **Title:** CNN-generated images are surprisingly easy to spot... for now
2. **Authors:** Sheng-Yu Wang, Oliver Wang, Richard Zhang, Andrew Owens, Alexei A. Efros
3. **Year:** 2020
4. **Venue:** CVPR 2020 (checked via: arXiv comment)
5. **DOI / link:** arXiv [1912.11035](https://arxiv.org/abs/1912.11035)
6. **Problem addressed:** Can one detector tell real images from images generated by any CNN, regardless of architecture or dataset?
7. **Methodology:** Collected fake images from 11 CNN-based generators and trained a standard classifier on one generator (ProGAN), with careful pre- and post-processing and data augmentation.
8. **Models used:** A standard image classifier trained on ProGAN images.
9. **Dataset:** Images from 11 generators (ProGAN, StyleGAN, BigGAN, CycleGAN, StarGAN, GauGAN, DeepFakes and others).
10. **Reported results:** The classifier generalises surprisingly well to unseen architectures, datasets and training methods, including StyleGAN2, which suggests shared systematic flaws in CNN-generated images.
11. **Advantages:** Strong simple baseline, with an early demonstration that augmentation matters. CVPR 2020.
12. **Limitations:** GAN-era generators. Later work (Corvi, Ojha) shows the approach weakens against diffusion models.
13. **Research gaps:** Transfer to diffusion and other new generators.
14. **Possible improvements:** Retrain on mixed GAN and diffusion data.
15. **Relevance to this project:** Shows why an image classifier trained today would date quickly, and why we ship forensic measurements instead of a learned verdict.

## 2.8 Towards Universal Fake Image Detectors that Generalize Across Generative Models

1. **Title:** Towards Universal Fake Image Detectors that Generalize Across Generative Models
2. **Authors:** Utkarsh Ojha, Yuheng Li, Yong Jae Lee
3. **Year:** 2023
4. **Venue:** CVPR 2023 (checked via: CVPR page and authors' repository)
5. **DOI / link:** arXiv [2302.10174](https://arxiv.org/abs/2302.10174)
6. **Problem addressed:** Detectors trained to separate real from GAN-fake images fail on newer generative models.
7. **Methodology:** Show that the real-versus-fake classifier is asymmetric (the real class becomes a sink for anything not fake). Propose classifying without learning the task: nearest-neighbour and linear probing in the feature space of a large pretrained vision-language model.
8. **Models used:** Nearest neighbour and linear probe on pretrained (CLIP-style) features.
9. **Dataset:** Fake images from GANs, diffusion and autoregressive models (see paper).
10. **Reported results:** Improves on the state of the art by +15.07 mAP and +25.90% accuracy on unseen diffusion and autoregressive models.
11. **Advantages:** Large generalisation gain, with no task-specific training. CVPR 2023.
12. **Limitations:** Depends on a large pretrained model, which is heavy for limited hardware.
13. **Research gaps:** Robustness to compression and editing is not the focus.
14. **Possible improvements:** Test with small, distilled feature extractors.
15. **Relevance to this project:** A realistic route to a pretrained image detector for our image module. It would need a model download and a validation set, so it is listed as future work.

## 2.9 On the detection of synthetic images generated by diffusion models

1. **Title:** On the detection of synthetic images generated by diffusion models
2. **Authors:** Riccardo Corvi, Davide Cozzolino, Giada Zingarini, Giovanni Poggi, Koki Nagano, Luisa Verdoliva
3. **Year:** 2023
4. **Venue:** ICASSP 2023 (checked via: Crossref DOI 10.1109/icassp49357.2023.10095167)
5. **DOI / link:** DOI [10.1109/icassp49357.2023.10095167](https://doi.org/10.1109/icassp49357.2023.10095167); arXiv [2211.00680](https://arxiv.org/abs/2211.00680)
6. **Problem addressed:** Diffusion models create photorealistic images, and it is unclear whether detectors built for GAN images can detect them, especially after social-network compression and resizing.
7. **Methodology:** Expose the forensic traces left by diffusion models, then test current detectors on diffusion images, including compressed and resized ones.
8. **Models used:** State-of-the-art GAN-image detectors.
9. **Dataset:** Synthetic images from diffusion models with real images, released by the authors.
10. **Reported results:** The abstract states the study aims and does not list figures. See the paper.
11. **Advantages:** Practical test conditions, with code and data released. ICASSP 2023.
12. **Limitations:** A snapshot of 2022-era diffusion models.
13. **Research gaps:** Detection after heavy compression.
14. **Possible improvements:** Continual retraining as generators change.
15. **Relevance to this project:** Supports measuring recompression behaviour (our ELA is a signal of this kind) while not treating it as proof of synthesis.

## 2.10 AI-GenBench: A New Ongoing Benchmark for AI-Generated Image Detection

1. **Title:** AI-GenBench: A New Ongoing Benchmark for AI-Generated Image Detection
2. **Authors:** Lorenzo Pellegrini, Davide Cozzolino, Serafino Pandolfini, Davide Maltoni, Matteo Ferrara, Luisa Verdoliva, Marco Prati, Marco Ramilli
3. **Year:** 2025
4. **Venue:** Verimedia workshop at IJCNN 2025 (checked via: arXiv comment, DOI 10.1109/IJCNN64981.2025.11228377)
5. **DOI / link:** DOI [10.1109/IJCNN64981.2025.11228377](https://doi.org/10.1109/IJCNN64981.2025.11228377); arXiv [2504.20865](https://arxiv.org/abs/2504.20865)
6. **Problem addressed:** Detectors of AI-generated images are usually tested on static datasets with arbitrary splits and unfair comparisons.
7. **Methodology:** A benchmark with a temporal evaluation framework: detectors are trained incrementally on images ordered by the generative model's release, which tests generalisation to new generators such as the shift from GANs to diffusion models.
8. **Models used:** Detection methods evaluated under the protocol.
9. **Dataset:** Ai-GenBench: diverse, high-quality synthetic and real images with a standard protocol.
10. **Reported results:** No headline numbers in the abstract. The contribution is the protocol and data.
11. **Advantages:** Ongoing, reproducible, and designed to keep compute needs practical. Presented at a workshop at IJCNN 2025.
12. **Limitations:** Workshop paper. It is a benchmark, not a detector.
13. **Research gaps:** Standard evaluation for detectors as generators evolve.
14. **Possible improvements:** Use it as the evaluation protocol for any image model we add.
15. **Relevance to this project:** The protocol we would adopt to validate an image classifier before calling it more than an indicator.

