# Conclusion

This project set out to build a complete, honest platform for checking news content, and to document it in the way a university research project requires.

**What was achieved.** A working web platform with accounts and roles, a database with migrations, text analysis in English (with exact explanations and an abstention rule) and experimentally in Urdu, an image forensic-indicator module, a guarded news-address and website check, an evidence check with listed sources, an image-with-headline consistency check, a frame-based video module, a history with PDF reports, a dashboard computed from real data, an administration area, an administrator-only model registry, and deployment files. It is covered by 263 back-end tests (also run on PostgreSQL 16), 24 front-end unit tests and 48 browser test runs, whose results are in `testing_report.md`. A verified literature review of 40 papers, a research-gap analysis, an evaluation protocol, requirements, architecture, data, API and model documents, user and installation manuals, a 12-month plan and a team plan accompany it.

**What was found.** The text baseline separates its own collection's held-out articles very well (accuracy 0.973) and collapses on a different kind of data (accuracy 0.552, ROC AUC 0.549), below the accuracy that a constant answer gives. The same pattern appeared in the new modules: a first pretrained video classifier was at chance on Celeb-DF, and the video model that was kept scored ROC AUC 0.93 on Celeb-DF but 0.84 on Google DeepFakeDetection, where its decision rule was right on 81% of the videos it decided. The finding is a practical argument for the design of the platform: a tool that reported the first number alone would mislead, so this one reports both, shows the baseline that any model must beat, abstains when it is unsure, and gives indicators, not verdicts, where nothing was validated.

**What was not achieved.** The image module has not been validated as a detector. The video module is frame-based, uses a third-party model, was measured on tens of videos and does not use motion or audio. The image-with-text thresholds come from everyday photographs, not news, and the evidence check's retrieval step was not measured. The news-site check is a short hand-made list. The Urdu model has no independent test collection. Docker was run only once, in a Linux sandbox, and the native Windows PowerShell scripts were never run. Accessibility was not audited. These items are listed in `limitations.md`, with the steps to close them in `future_work.md`.

**Lessons.**

1. A high score on one dataset is a statement about that dataset. Cross-dataset evaluation must come before any claim about detection.
2. Abstention, baselines and visible limits are product features, not footnotes.
3. Tests that check honesty (a missing model gives an error, a video with too few faces gets no verdict, an unknown website is never called fake, an explanation adds up exactly) are as valuable as tests of functionality.
4. A documented gap is better than an invented result.

The platform is a base for the remaining work. Each module has a documented gate, a place in the code and a place in the interface, so that when a stronger model passes its tests it can replace the current one without changing anything else, and the first candidate to try is the one listed for that module in `future_work.md`.
