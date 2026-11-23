# Future work

The items follow `docs/ROADMAP.md`. Each module moves from *experimental* to a validated status only after it passes the gate in `docs/research/research_methodology.md`: a held-out test, a cross-dataset test, calibration, robustness checks and error analysis.

## 1. Close the verification gaps first (month 5)

1. Build and run the Docker images and Compose stack on a machine with Docker.
2. Run the migrations and the test suite against a standard PostgreSQL installation and the Compose service (the suite already passed on an embedded PostgreSQL 16 build).
3. Run the PowerShell scripts on native Windows.
4. Run an automated accessibility audit and fix what it finds.

## 2. Improve the models

| Item | Why | How |
|---|---|---|
| Fairer external evaluation | LIAR2 is a different task, so the gap is hard to interpret | Add an external set of full articles with independent labels |
| Threshold and coverage analysis | The 0.80 default is untuned | Choose it on validation data with a coverage-risk curve |
| Transformer baseline | Compare with a pretrained language model | Fine-tune a small distilled model, with the same split and the same external test |
| Repeated runs | No intervals on the scores | Several seeds, report the spread |
| Urdu text | Experimental, one collection | A second Urdu collection (Ax-to-Grind, FIRE 2020) for a cross-dataset test, and a multilingual model |
| Learned image detector | ELA cannot detect generated images | Pretrained-feature detector on a labelled set, tested across generators and after recompression |

## 3. Deepen the modules that now exist

| Module | Plan |
|---|---|
| Video | Done as a frame-based pipeline with a third-party model. Next: train and test on large sets (FaceForensics++, DFDC, with access granted), add a model that learns motion and timing, add audio, and move decoding into a sandboxed worker |
| Multimodal | Done with CLIP and a written rule, measured on Flickr30k. Next: thresholds measured on NewsCLIPpings and a hand-checked sample of real out-of-context news images |
| Evidence | Done with Wikipedia retrieval and a pretrained stance model, stored with sources. Next: a hand-checked claim set to measure retrieval end to end, news-source retrieval and a multilingual stance model |
| URL credibility | Done with a small hand-made list and rules. Next: a documented source-reliability list with a stated policy about who decides, and a way to read pages that need a script |

## 4. Product and operations

| Item | Note |
|---|---|
| Reset by e-mail | Add a mail service and a token delivery page |
| Shared rate limiter | Use a shared store such as Redis when running several workers |
| Background jobs | Move long analyses to a queue when video arrives |
| Retention rules | Automatic deletion of old uploads and analyses |
| Continuous integration | Run the three test suites on every change |
| Explanation faithfulness study | Test whether highlighted terms and listed sources help readers, with consent |
| Report conversion | Assemble `docs/` into a Word or PDF report |

## 5. Research questions that the platform can now support

1. How does the abstention threshold trade coverage for risk on text from other sources?
2. Which cheap features, if any, separate the two datasets, and are they source shortcuts?
3. Does showing a constant-answer baseline and an external score change how much readers trust a verdict?
