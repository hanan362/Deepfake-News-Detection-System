# Results and discussion

Every number here is read from `ai_models/evaluation/results/text_baseline_en_metrics.json` (written by the training script) or from a test run recorded in `testing_report.md`. The figures are from the run on the development container (Python 3.13, scikit-learn 1.9.1). A second training run on another machine gives the same pipeline with its own metrics file.

## 1. Text model

### 1.1 Results

| Set | n | Accuracy | F1 (fake) | ROC AUC | Accuracy of a constant answer |
|---|---|---|---|---|---|
| Validation (same collection) | 8,083 | 0.975 | 0.973 | 0.996 | not computed |
| Test (same collection) | 8,084 | 0.973 | 0.972 | 0.995 | 0.536 |
| LIAR2 (different collection) | 2,296 | 0.552 | 0.643 | 0.549 | 0.576 |

| Calibration of the deployed model | Test | LIAR2 |
|---|---|---|
| Expected calibration error | 0.030 | 0.129 |
| Brier score | 0.022 | 0.265 |

### 1.2 Four classifiers on the same features

| Classifier | Test acc. | Test F1 | LIAR2 acc. | LIAR2 F1 | LIAR2 AUC |
|---|---|---|---|---|---|
| Logistic regression (deployed) | 0.973 | 0.972 | 0.552 | 0.643 | 0.549 |
| Linear SVM | 0.977 | 0.975 | 0.548 | 0.645 | 0.540 |
| Naive Bayes | 0.941 | 0.937 | 0.584 | 0.638 | 0.605 |
| Random forest | 0.960 | 0.957 | 0.577 | 0.682 | 0.564 |

### 1.3 Discussion

**The in-collection result is excellent and tells us little.** Four different classifiers all reach 0.94 to 0.98 on held-out articles of their own collection. When four unrelated algorithms agree this closely, the data is probably easy to separate by surface features, such as vocabulary and style of the sources it was gathered from. The dataset card does not document those sources (see the manifest), and the label check could only confirm which label means *real*, not that the articles were independently fact-checked.

**The external result shows that the model did not learn a general ability.** On LIAR2 the deployed model scores an AUC of 0.549, where 0.5 is chance. Its accuracy of 0.552 is below the 0.576 that answering "fake" every time would give, and its F1 of 0.643 is below the 0.731 of an "always fake" answer. It labels 67.8% of the statements fake and recognises only 35% of the true-ish ones. No classifier in the comparison reaches 0.731. The in-collection to external gap (accuracy 0.973 to 0.552) is the main finding.

**Caution about that comparison.** LIAR2 is not the same task. Its items are short political statements and its labels come from fact-checker ratings that were mapped to two classes, while the training data are full articles labelled by source collection. A weak transfer is expected. It supports the narrow claim that this model should not be trusted outside its training distribution. It does not measure how well the model would do on a fair external set of full articles, which was not available.

**Calibration follows the same pattern.** The probabilities are well calibrated in-collection (ECE 0.030) and poorly externally (0.129). The 0.80 abstention threshold is a configuration default that was not tuned, so the share of *Unverified* answers on real articles is unknown. Section 5 of `docs/research/research_methodology.md` describes the coverage-risk analysis that would set it.

**The explanation is exact but narrow.** For logistic regression the per-term contributions add up to the model's log-odds, and a test checks it. That makes the explanation faithful to the model. It does not make it a good reason to believe an article is fake: the terms that matter are the ones the training collection rewards.

**Why logistic regression was deployed.** The linear SVM is slightly more accurate in-collection and the random forest has the best LIAR2 F1, but neither gives exact term contributions with calibrated probabilities. The choice was made for explainability. No classifier was selected using LIAR2, so the external set stays unseen.

### 1.4 Threats to validity

| Threat | Effect |
|---|---|
| Dataset provenance is undocumented | In-collection scores may reflect source style, not deception |
| One training collection and one external set | The size of the gap may differ on other sets |
| Label mapping on LIAR2 | Different meaning of the labels. Treat the external result as a stress test |
| No repeated runs with different seeds | No confidence interval on the scores. The split is fixed |
| Untuned threshold | Abstention rate unknown |
| Time drift | The collections come from a limited period |

## 2. Image module

The image module is a measurement tool, not a classifier, so it has no accuracy. What was verified:

| Check | Result |
|---|---|
| A flat image recompresses almost without error | Test passes |
| Random noise gives an error more than five times higher | Test passes |
| The error map is not blank | Test passes |
| Content, not file name, decides whether a file is accepted | Test passes |
| Size and pixel limits are enforced | Test passes |
| No verdict and no confidence value is returned | Test passes and e2e |

Not verified: whether the measurements separate edited from authentic images, or detect generated images. No labelled set was used. The literature (Wang et al., 2020; Corvi et al., 2023; Li et al., 2025) suggests that even trained detectors degrade after recompression, so a single threshold on ELA would be unjustified. The module reports indicators and says so.

## 3. Platform

| Area | Outcome |
|---|---|
| Accounts and security | Registration, login, logout, reset, change of password, token revocation, roles, rate limits, audit log. Tests cover wrong credentials, disabled accounts, expired and reused tokens, and another user's data |
| Data layer | Migrations create and remove every table. A test confirms that models and migrations agree and that existing accounts survive the roles migration |
| Records | History with search, filters and paging, owner-only access, deletion of records and files, PDF reports including non-Latin text |
| Honest behaviour | Short text and unsupported scripts are declined. A missing or mismatched model gives a clear `503` or a result that says which part was not assessed, and is never replaced by a guess. A video without enough faces gets no verdict. Evidence with nothing reliable is *Insufficient Evidence*. An unknown website is never called fake |
| Interface | 23 routes, light and dark themes, responsive, 48 browser tests including two-user isolation and the full register to report to logout flow |

## 4. What the results mean for the project goals

| Goal | Result |
|---|---|
| Real inference only | Achieved. Every result comes from a model or a measurement, and tests refuse an unavailable model |
| Honest limits | Achieved in the interface and in the documents. The weak external score is shown on the administrators' Models page, and every text result carries a plain-language limits box and the sentence that it does not check facts. Ordinary readers are not shown the percentage itself |
| A complete platform | Achieved for the implemented modules |
| Broader detection | Achieved in a limited, measured form: Urdu text (experimental), news web addresses, evidence retrieval with a stance model, image-with-text consistency and frame-based video. Each was measured on small or non-news data (section 6) and none is a validated detector |
| A learned image detector | Not achieved |
| Native Windows, Docker and PostgreSQL verification | Not achieved in this build. See `limitations.md` |

## 5. The additional modules

| Module | Measured on | Result | What it does not show |
|---|---|---|---|
| Urdu text | 260 held-out articles of the one available collection | Accuracy 0.862, ROC AUC 0.911, constant answer 0.569 | Anything about Urdu news from other sources |
| Evidence stance | 1,200 FEVER claims with gold evidence | 85.0% forced choice; 93.7% correct on the 72.5% it decides | Recent news, claims that are neither supported nor refuted |
| Evidence, whole check | 40 true and 40 false short claims (Wikipedia retrieval, stance and verdict); SET_B of 40 was held out | SET_B: 32 right, 2 wrong, 6 no call (before the changes: 21 right, 9 wrong) | News claims, recent events; the sets are small and written by the developers |
| Text against headline | 70 real articles on which the rules were set, 58 and 55 more that were used once and then looked at, and 59 more (whole texts) read only after the rules were frozen; 32 texts written by the developers | **Fresh set: a real article got Contradicts or Different details in 8 of 59 (14%, 7% to 25%) and Unrelated in 0 of 59**; over four sets Unrelated 1 of 242 real articles and 230 of 242 texts of another story. Changed numbers 14 of 19 and names 27 of 45 were flagged (strict policy). Earlier set: written to say the opposite 15 of 16, **written to agree and add invented details 0 of 16 flagged** | A true or false text that agrees with its headline in its first sentences; real disinformation; other languages; small samples; with the default policy a changed version of the same story is only a warning (section 5b) |
| Headline check | Two independent sets collected after the rules were fixed: 126 real headlines, 39 distorted and 12 invented; 76 on which the thresholds were chosen; 60 older ones | Real headline found at a listed outlet 94 of 126 (75%, 66% to 81%), 19 of 126 (15%) when the outlet it came from is not counted; distorted 0 of 39 corroborated (19 flagged as different); invented 0 of 12. One real headline of 126 was wrongly flagged as different. Older real headlines 1 of 30 | Real fake news, article text, local outlets, paraphrased or older stories, name spellings that differ between outlets (section 5a) |
| Image-text similarity | 300 held-out Flickr30k images | ROC AUC 0.995 (random mismatch), 0.899 (hard mismatch); 11% of matching captions flagged | News photographs |
| Video | 120 calibration, 48 held-out Celeb-DF and 40 Google DeepFakeDetection videos | ROC AUC 0.907, 0.933 (optimistic) and 0.843 (0.71 to 0.95); rule right on 80.7% of decided videos on the other dataset | Other generators, news footage, compression, audio, motion |

One negative result deserves mention: the first pretrained video frame classifier tried scored at chance on Celeb-DF (frame ROC AUC 0.47) and had to be dropped, which is the same pattern as the text model: a detector that looks accurate in the setting it was built for can fail on another. The model that was kept was chosen afterwards while looking at part of the Celeb-DF test sample, so that sample's result is optimistic, and on a second dataset it is clearly weaker. That is why the video module is labelled experimental, shows the per-frame scores behind every verdict, and says it is frame-based.

### 5a. The headline check and the "real news comes out Unverified" problem

The writing-style model cannot recognise true news (its accuracy on another collection is no better than a constant answer), so a true article often came out *Unverified*. The headline check addresses that from another side: it asks whether a well-known outlet runs the same headline. On 126 fresh real headlines (two independent sets) it found one at a listed outlet in 75% of cases while corroborating none of 12 invented and none of 39 distorted headlines (the third set showed one distorted headline being confirmed, "Iraq" for "Iran"; a rule that requires the names and numbers to match was added, which lowered the real-headline rate from 79% to 74% on the held-out set), so on these small tests it told reported headlines from invented or edited ones, which the writing style could not do on another collection. It has three limits that decide how much to rely on it. First, the hits are largely the outlet's own page found again (the headlines were read from that outlet's feed): with that outlet excluded only 15% remain, which is why web addresses use a separate rule (a page served from a listed outlet's own website is lifted from *Unverified* to *Likely Real*, meaning "published by"). Second, it sees only headlines, so a copied real headline above a false body passes the headline check itself; section 5b describes the check that reads the body. Third, old, local and paraphrased stories are not found (3% of older real headlines; when nothing matches, related headlines of listed outlets are shown for the reader to compare). The honest summary is that the system now marks about three in four fresh, well-reported headlines as reported by a listed outlet (when that outlet itself counts), and still cannot say that any claim is true.

### 5b. A real headline over a false text

The headline check cannot see the text, so a real headline pasted over something else would be confirmed. A second check reads the first ten sentences of the text against the headline (technical documentation, section 6b). It was measured on four sets of real articles, with three versions of its rules; only the last set (59 articles with their whole texts, collected from several news sections and not read until the rules were frozen) is an independent measurement.

Two of its five results are reliable and three are not. *The text is about something else* was given to 1 real article in 242 over four sets (0.4%) and to 230 of 242 texts taken from a different story (95%). *The text says something different* and *Names or numbers do not match* were given to 8 of 59 real articles on the fresh set (14%, 7% to 25%), against 4 of 58 (7%) on the earlier set before its false alarms were used to adjust the rules, and about the same share of real articles was flagged by every version that had not been tuned on the articles it was measured on. They catch most texts whose names or numbers were machine-altered (27 of 45 and 14 of 19 on the fresh set) and 15 of 16 hand-written opposite texts, but their false alarms are as common as the real changes they find, so they are shown as a warning and do not change the verdict. The application therefore withholds a *Likely Real* only when the text is about another story, and it does nothing to a web page from a listed outlet's own website, where the outlet wrote both parts. The consequence is that a person who keeps a real headline and writes about the same event with other names or numbers is **not** caught, and a person who restates the headline and then adds false details is not caught either (0 of 16 hand-written texts flagged). The check answers "is the text about the same thing as the headline", not "is the text true". The altered texts were machine-made or written by the developers, so the figures show that the rules do what they were written to do and not how well they would do against a real deceiver. `TEXT_MATCH_STRICT=true` lets every difference stop a *Likely Real* (about one real article in seven then becomes *Unverified*). Its effect on a verdict is one-sided: it can only turn *Likely Real* into *Unverified*.

## 6. Comparison with related work

The project does not claim better performance than any published system. The text baseline follows the n-gram and linear-model approach described by Ahmed et al. (2017) and Pérez-Rosas et al. (2018). Its in-collection score is in the range such methods obtain, and its external collapse agrees with the generalisation problem that the detection literature reports. The project's difference is in presentation: the external result and a constant-answer baseline are shown beside the headline score, and the system abstains. See `docs/research/proposed_contribution.md` for the limited contribution claimed.
