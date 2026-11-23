# AI model documentation

This document follows the model-card idea of Mitchell et al. (2019). Every number comes from a file in `ai_models/evaluation/results/` that a training or evaluation script wrote, and is shown in the app on the administrators' Models page: `text_baseline_en_metrics.json`, `text_baseline_ur_metrics.json`, `evidence_nli_fever.json`, `multimodal_clip_flickr.json`, `video_frame_model.json`, and (for the text-against-headline check, section 6b) `headline_body.json`.

## 1. What is installed

| Module | Name | Version | Status | Needs training or download? |
|---|---|---|---|---|
| Text | `text_baseline_en` | 1.0.0 | `trained_baseline` | Trained here. The checkpoint is not in Git, so each machine trains its own (about 2 minutes after a one-time download) |
| Image | `ela_forensics` | 1.0.0 | `heuristic` | No model. Fixed algorithm (Pillow) |
| Text (Urdu) | `text_baseline_ur` | 1.0.0 | `experimental` | Trained here (about 1 minute, `train_text_urdu.sh`). Not in Git |
| News web address | `source_credibility` | 1.0.0 | `heuristic` | No model: rules and a 51-entry site list shipped in the repository |
| Evidence | `evidence_nli` | 1.0.0 | `pretrained` or `heuristic` | Pretrained `cross-encoder/nli-deberta-v3-small` (Apache-2.0, pinned revision, about 570 MB), downloaded by `scripts/setup/download_models` or on first use (needs `requirements-ml.txt`). Without it, passages are retrieved and shown but their stance is not judged |
| Headline check | `headline_corroboration` | 1.0.0 | `heuristic` | No training: fixed rules, the site list and the evidence model above (needs `requirements-ml.txt`). Searches Google News RSS (unofficial, needs internet); without it the check says it could not run |
| Text against headline | `headline_text_consistency` | 1.0.0 | `heuristic` | No training: fixed rules on the evidence model above (needs `requirements-ml.txt`). Runs on the server and sends nothing out; without the model it says it could not run |
| Image with text | `text_image_consistency` | 1.0.0 | `pretrained` or `heuristic` | Pretrained `openai/clip-vit-base-patch32` (about 600 MB) plus thresholds measured here. Without it, the consistency check is skipped and said to be skipped |
| Video | `video_frame_swin_ffpp` | 1.0.0 | `experimental`, `heuristic` or `unavailable` | Pretrained third-party Swin-Tiny `hchcsuim/FFPP-Raw_1FPS_faces-expand-40-aligned_val-ds-celeb-df` (pinned revision, about 110 MB), the YuNet face detector (committed, 230 KB, MIT) and thresholds measured here. Without torch and transformers: frames and measurements only. Without OpenCV: unavailable |

Only the English and Urdu text models are trained in this project. The others use third-party pretrained networks, which this project did not train and whose training data it did not check. No external API is needed; a Google Fact Check Tools key is an optional extra for the evidence check.

## 2. Text model: `text_baseline_en`

### Model details

| Item | Value |
|---|---|
| Task | Binary classification of an English news article as fake-like or real-like by writing patterns |
| Algorithm | TF-IDF features (unigrams and bigrams, 60,000 features) with logistic regression |
| Library | scikit-learn. The checkpoint stores the version that trained it and is refused by a different version |
| Seed | 42 |
| Output | Probability of fake and real, a verdict, and exact per-term contributions |
| Training time | About 2.4 seconds for the final model, about 90 seconds for the whole script on a CPU |

### Intended use

Giving a reader a quick signal about how much an article's wording resembles the articles in the training collection, with a clear explanation of which words moved the score. It is a teaching and research baseline.

### Out of scope

- Fact checking. A verdict does not say whether claims are true.
- Short claims and social-media posts (the model needs at least 60 words).
- Languages other than English. Arabic-script text such as Urdu is declined.
- Machine-written text and news from after the training data's time.
- Any decision that affects a person's reputation, safety or rights.

### Training data

| Item | Value |
|---|---|
| Dataset | GonzaloA/fake_news (Hugging Face) |
| Clean size | 24,261 train, 8,083 validation, 8,084 test articles (156 empty or short rows and 3 duplicates removed) |
| Fake share | 45.7% train, 46.4% test |
| Licence | Not stated on the dataset card. Used for academic research only |
| Provenance | A mix of Kaggle collections, sources not documented |
| Label check | Label 1 was verified as "real" by the rate of wire-agency tags (95.9% against 0.04%) |
| Cleaning | Empty rows, duplicates and cross-split leaks removed. Source artefacts such as datelines removed before features are built |

### Evaluation

| Set | n | Accuracy | Precision (fake) | Recall (fake) | F1 (fake) | ROC AUC | PR AUC |
|---|---|---|---|---|---|---|---|
| Validation | 8,083 | 0.975 | 0.970 | 0.976 | 0.973 | 0.996 | 0.994 |
| Test (same collection) | 8,084 | 0.973 | 0.968 | 0.975 | 0.972 | 0.995 | 0.994 |
| External: LIAR2 test | 2,296 | 0.552 | 0.595 | 0.700 | 0.643 | 0.549 | 0.620 |

Confusion matrices (rows are the truth, "fake" is the positive class):

| | Predicted real | Predicted fake |
|---|---|---|
| Test, truly real | 4,209 | 121 |
| Test, truly fake | 94 | 3,660 |
| LIAR2, truly true-ish | 342 | 631 |
| LIAR2, truly fake-ish | 397 | 926 |

Calibration: expected calibration error 0.033 (validation), 0.030 (test) and 0.129 (LIAR2). Brier score 0.022 on test and 0.265 on LIAR2.

### Trivial baselines (what a model must beat)

A constant answer needs no model. Its accuracy is the share of the more common label, and an "always fake" answer has precision equal to the fake share and recall 1. Both are worked out from the confusion matrices in the metrics file.

| Set | Fake share | Accuracy of the most common label | F1 (fake) of "always fake" | Deployed model accuracy | Deployed model F1 (fake) |
|---|---|---|---|---|---|
| Test (same collection) | 0.464 | 0.536 | 0.634 | 0.973 | 0.972 |
| LIAR2 (external) | 0.576 | 0.576 | 0.731 | 0.552 | 0.643 |

On LIAR2 the deployed model is **below** both trivial baselines. It labels 67.8% of the statements fake and recognises only 35% of the true-ish ones (specificity 0.351). All four classifiers have a LIAR2 F1 below 0.731, and only Naive Bayes (0.584) and Random forest (0.577) exceed the 0.576 accuracy of a constant answer, by under one percentage point. The application shows the *Constant answer* figure next to every accuracy for this reason.

### How to read the numbers

On its own collection the model is very accurate, and its probabilities are well calibrated. On a different kind of data, short political statements judged by fact-checkers, it is close to chance (ROC AUC 0.549, where 0.5 is chance) and below a constant answer in accuracy, and its probabilities are far less reliable. LIAR2 also has a different label meaning, so this is not a measure of every kind of fake news. The honest conclusion is that the model has learned the style of its training collection.

### Comparison with other classifiers trained on the same features

| Classifier | Test accuracy | Test F1 | LIAR2 accuracy | LIAR2 F1 | LIAR2 ROC AUC |
|---|---|---|---|---|---|
| Logistic regression (deployed) | 0.973 | 0.972 | 0.552 | 0.643 | 0.549 |
| Linear SVM | 0.977 | 0.975 | 0.548 | 0.645 | 0.540 |
| Naive Bayes | 0.941 | 0.937 | 0.584 | 0.638 | 0.605 |
| Random forest | 0.960 | 0.957 | 0.577 | 0.682 | 0.564 |

Logistic regression was chosen because its term contributions are exact, not because of its external score. None of the four transfers well.

### Decision rule at run time

1. Arabic-script text: `Unverified` (unsupported language).
2. Fewer than 60 words: `Unverified` (too short).
3. Otherwise compute the probabilities. If the fake probability is at least 0.80 the verdict is `Likely Fake`. If the real probability is at least 0.80 it is `Likely Real`. Otherwise it is `Unverified`.

The threshold is a configurable default (`TEXT_CONFIDENCE_THRESHOLD`) and was not tuned on data. Because of the external result, a high confidence on text unlike the training articles should not be trusted.

### Explanation

For each term present in the article the contribution is its TF-IDF value times the learned coefficient. The positive and negative sums, with the intercept, give the model's log-odds exactly. A test checks this. The panel therefore shows what moved the score. It does not show whether a claim is true.

### Known risks and limitations

- Source and style shortcuts may remain in the training data after cleaning.
- Time drift: the model knows the vocabulary of its training period.
- Machine-written text is not covered.
- Short or heavily edited text lies outside the training distribution.
- The probabilities are model scores, not the chance that a story is false.

### Reproduce

```bash
bash scripts/training/train_text_model.sh      # download, clean, train four models, evaluate, write the deployed model
python scripts/evaluation/print_text_metrics.py  # print the saved metrics
```

Outputs: `ai_models/checkpoints/text_baseline_en/` (model and metadata, not committed), `ai_models/model_registry/text_baseline_en.json`, `ai_models/evaluation/results/text_baseline_en_metrics.json`, `datasets/manifests/gonzaloa_fake_news.json`.

## 3. Image module: `ela_forensics`

| Item | Value |
|---|---|
| Method | Error Level Analysis: re-save the image as JPEG at quality 90, take the per-pixel difference, summarise it as mean, maximum and block-to-block variation over a 16 by 16 grid. Metadata (EXIF camera, software and dates) is read |
| Output | Numbers, a heatmap, observations in plain language. Verdict `Indicators Only`. No confidence |
| Formats | JPEG, PNG, WEBP, at most 10 MB and 40 million pixels |
| Validation | None as a detector. The unit tests check that the measurements are real (a flat image recompresses almost perfectly, random noise gives an error more than five times higher, and the map is not blank). No accuracy is claimed because no labelled set of edited and authentic images was used |

What it cannot do: ELA responds to recompression, so it can flag harmless things and miss edits, and it cannot detect AI-generated images. The literature (Li et al., 2025; Corvi et al., 2023) shows that learned detectors also lose reliability after sharing, which is why no verdict is given.

## 4. Urdu text model: `text_baseline_ur` (experimental)

| Item | Value |
|---|---|
| Task | Binary classification of an Urdu news article as fake-like or real-like by writing patterns |
| Data | "Bend the Truth" (Amjad et al., 2020), `community-datasets/urdu_fake_news`: 634 training and 260 test articles after removing 4 duplicates in training and 2 test articles that also occur in training. Licence unknown on the dataset card; academic use only. Manifest: `datasets/manifests/urdu_fake_news.json` |
| Method | TF-IDF on character sequences of 2 to 5 characters inside words, with logistic regression (C = 64). Settings were chosen by cross-validation grouped by article pair, because the training split holds near-identical real and fake versions of the same story (nearest neighbour has the opposite label for 90% of articles); ordinary random cross-validation would have put the two versions of a story in different folds and given a misleading ROC AUC of 0.655 against 0.892 when grouped |
| Result | On the held-out split: accuracy 0.862 (95% interval 0.819 to 0.904), ROC AUC 0.911 (0.873 to 0.944); a constant answer gives 0.569 |
| Decision rule | The same 0.80 confidence rule as English: 65% of articles are decided, 91.7% correct when decided |
| Why experimental | One small collection, and no second Urdu collection to test on. The metrics file also holds a text-length-only baseline (accuracy 0.562, ROC AUC 0.597) and per-category accuracy. Nothing shows it works on Urdu news from other sources |

## 5. News web address: `source_credibility` (heuristic)

The page is fetched by the server, so the fetch is restricted: only http and https on ports 80, 443, 8080 and 8443; no credentials in the address; the host name is resolved by the server, every address in the answer must be public (private, loopback, link-local and reserved ranges are refused), and the connection is pinned to the checked address so a second DNS answer cannot redirect it; at most 5 redirects, each checked again; at most 2 MB; 15 seconds in total; only HTML is read. Each user is limited to 10 fetches per minute. The article is extracted with a small rule-based extractor (the largest block of paragraph text, boilerplate such as navigation and footers removed), then scored by the text model of its language.

The website check compares the domain with a list of 51 well-known news sites and satire sites, looks for look-alike spellings of those domains, and reports observable properties (HTTPS, byline, publication date, redirects). It never calls an unfamiliar domain fake: it says the site is not in the list. A page served from a listed organisation's own website can lift an undecided reading to *Likely Real* (section 6a); that rule says who published the page, not that it is accurate. The list was written by hand for this project and is small. This is not a trained model.

## 6. Evidence check: `evidence_nli` (pretrained)

Claims are picked from the text (sentences with names, numbers or places). Passages (the introductions of the best-matching Wikipedia pages) are retrieved and, when `GOOGLE_FACT_CHECK_API_KEY` is set, published fact-checks. A pretrained natural-language-inference model (`cross-encoder/nli-deberta-v3-small`, Apache-2.0) labels the single best-matching sentence of each passage as supporting, contradicting or neither. A stance is only shown when the model is at least 85% certain and the passage overlaps the claim. The claim verdict (*Supported*, *Contradicted*, *Mixed Evidence* or *Insufficient Evidence*) follows fixed rules: support and no contradiction, the reverse, both, or neither. Published fact-checks are listed with the rating their publisher gave and are never turned into a verdict by the system.

Four preparation steps run when pages are retrieved or before a sentence is judged. Each was added after a real failure and measured (see below):

- **Pronunciation guides are removed.** Wikipedia's first sentence often reads "The Eiffel Tower ( EYE-fəl; French: Tour Eiffel [tuʁ ɛfɛl] ) is a lattice tower in Paris, France." The earlier model read that sentence as contradicting "The Eiffel Tower is located in Paris, France" with 99.9% certainty. Only brackets that hold pronunciation symbols are removed; dates in brackets stay.
- **A leading pronoun is replaced by the page title.** "She shared the 1903 Nobel Prize in Physics" says nothing to a model that does not know who "she" is. This is a heuristic and is wrong when the pronoun points to something else.
- **A second search for the claim's subject (23 Nov 2026).** Searching with every word of a claim ("The Eiffel Tower is located in Rome, Italy") ranks pages that share its wrong details, so the page about the subject can be missing. It was: the only page that contradicted the Rome claim was about the tallest buildings, a right verdict resting on an unrelated sentence. The name the claim starts with ("Eiffel Tower") is now also searched on its own, and up to two of those pages are read first (the claim's own search still supplies three). It is a spelling heuristic (capitalised words at the start; "The Wright brothers" gives only "Wright"); a claim that does not start with a name gets no second search, and if the second request fails the first search's pages are used.
- **A page about a namesake is not used.** When both "Eiffel Tower" and "Eiffel Tower (Paris, Texas)" are found, the bracketed page is about another subject unless the claim names its qualifier. It is still listed, labelled *Same name, different subject*.

| Measured | Value |
|---|---|
| Stance step alone | 1,200 claims of the FEVER development set with gold evidence (supports or refutes, balanced). Forced choice: **85.0%** correct. At the 0.85 certainty threshold the model decides **72.5%** of the claims and is right on **93.7%** of those (95% interval 92.1% to 95.3%); a constant answer gives 50%. The previous model (DistilBERT MNLI) gave 79.0%, 71.4% decided and 89.0% correct on the same claims |
| Whole check (retrieval, stance and verdict) | `evaluate_evidence_live.py`: 40 true and 40 false short claims about well-known facts, in two sets of 20 + 20. **SET_A** was used while the steps above were developed, **SET_B** was written afterwards and not looked at until the code was final. A true claim counts as right when *Supported*, a false one when *Contradicted* |
| SET_B (held out), now | 32 of 40 right, 2 wrong (a true claim called *Contradicted*); 6 gave no call (*Mixed Evidence* or *Insufficient Evidence*). 14 of 20 true claims *Supported*, 18 of 20 false claims *Contradicted* |
| SET_B, before the changes | 21 of 40 right, **9 wrong** (7 true claims called *Contradicted*, 2 false claims called *Supported*) |
| SET_A, now and before | 31 right and 3 wrong now (optimistic: it was used for tuning; 32 right before the subject search); 25 right and 3 wrong before |
| Subject search, 23 Nov | Replayed on the same 80 claims (`--no-subject` gives the earlier pipeline). **Verdict counts did not improve:** SET_B 32 right and 2 wrong both ways; SET_A one fewer right (31). Two true claims moved from *Supported* to *Mixed Evidence* (Mona Lisa, Statue of Liberty) because a neighbouring page now also disagrees; one moved from no call to *Supported* (Colosseum). No new wrong call. What improved is the evidence shown: the subject's own page is now read for nearly every claim (for the Rome claim, "Eiffel Tower" now contradicts it), and 72% of the 186 passages that took a stance came from a page whose title shares a word with the subject (63% of 142 before). SET_B was read for this comparison, so it is no longer untouched |
| What the remaining errors look like | A page about a neighbouring subject is read as contradicting ("Blue Nile" for "The Nile flows through Egypt", "Euler's laws of motion" for "Isaac Newton formulated the laws of motion"), and the model sometimes misreads a nearly identical sentence. A rule that ignored pages whose title the claim barely names was tried and rejected: it raised the true claims found but cut the false claims found from 18 to between 6 and 11 of 20 |
| Not measured | Behaviour on news claims, on recent events (Wikipedia lacks them), on claims that are neither supported nor refuted, and on Urdu or other languages. The claim sets are small and written by the developers: they show how the check behaves, not how accurate it is in general |

## 6a. Headline corroboration: `headline_corroboration` (fixed rules on the evidence model)

**What it asks.** "Is this headline also reported by a well-known news organisation?" It is shown as its own result ("Do well-known outlets report it?") next to the writing-style reading. It shows that a story was *reported*, never that it is *true*.

**How it works.** The headline (the Headline box for pasted text; the page's own headline for a web address) is searched in the public RSS feed of Google News search. That feed is not an official, documented interface: Google can change or stop it and its terms apply. Only the headline is sent (cut at 200 characters, a trailing "| Site name" removed); results are kept in memory for 10 minutes; each user may make 10 such searches a minute. After an HTTP 429 answer the search is retried once and, if it is refused again, paused for 60 seconds (a longer `Retry-After` is capped at 5 minutes), so a blocked server does not keep sending requests; the check then says "could not be checked" and the verdict is unchanged. Results from the 43 non-satire organisations of the hand-made directory (`known_sources.json`) are kept; every other site is ignored. For each kept result that shares at least half of the headline's content words, the same pretrained inference model as the evidence check (`cross-encoder/nli-deberta-v3-small`) says whether that headline *entails* or *contradicts* the user's. Only headlines are compared, never article text. English only. A number or a name of the user's headline (a capitalised word) that the other headline does not contain stops that headline from confirming it (see the table). `CORROBORATION_ENABLED=false` switches it off and nothing leaves the server.

| Outcome | Rule (fixed before the held-out set was collected) |
|---|---|
| Corroborated | a listed outlet's headline shares at least 50% of the content words **and** the model is at least 60% sure it says the same |
| Disputed | no outlet corroborates, **and** a listed outlet's headline shares at least 70% of the content words **and** the model is at least 80% sure it says the opposite. Shown as "a listed outlet reports something different", never as a ruling |
| Same names and numbers | added 23 Nov after one failure (below): every number and every name (capitalised word, the first word unless it is a function word; Title Case headlines contribute numbers only) of the user's headline must also appear, stemmed, in the headline that is said to confirm it |
| Not found | anything else. Says nothing against the headline. Headlines of listed outlets that share at least 30% of the content words are then listed as **related coverage** (one per outlet, at most three, labelled as a different claim); this is for the reader and never changes the verdict |
| Not checked / could not be checked | no headline, under 5 words, Urdu, satire site, switched off, rate limit, search or model failure. The reason is shown |

**How it changes the verdict.** Never to *Likely Fake*. Corroborated: *Unverified* becomes *Likely Real*; *Likely Real* stays; *Likely Fake* becomes *Unverified* ("the two readings disagree"). Disputed: *Likely Real* becomes *Unverified*; the others stay. A satire site, an unreadable page and a non-English text keep their own result.

**Web addresses.** The outlet an article was fetched from is not counted as confirming its own headline. Because that leaves few real articles confirmed (below), a second, separate rule applies to addresses only: a page that was actually served from the website of a listed news organisation was published by it, so an undecided reading becomes *Likely Real* with the reason "published by a listed outlet" ("shows who published it, not that what it says is accurate"), a *Likely Fake* reading becomes *Unverified*, and a "Disputed" headline blocks the rule. This is a rule, not a measured model: no test set holds fake articles that were served from a listed site, so its error rate is unknown. Look-alike and unfamiliar addresses get nothing.

**How the thresholds were chosen.** From a grid (4 overlap levels, 4 entailment levels, one or two outlets required) on the 76 headlines of the "current" set below. Word overlap alone accepted 11 of 14 distorted headlines (a changed number, place or verb), so the model's "says the same" check was added: with it, 35 of 42 real headlines and 0 of 14 distorted ones are accepted. Requiring two outlets accepted only 5 of 42 real headlines and was rejected. Because the grid used that set, it is not an independent test; the *held-out* set was collected afterwards.

**Measured** (`ai_models/training/evaluate_corroboration.py` replays saved search results through the production code; results in `ai_models/evaluation/results/corroboration.json`; 95% Wilson intervals):

| Set | Headlines | Corroborated | Disputed | Not found |
|---|---|---|---|---|
| Held-out, real headlines read from outlet feeds, the outlet counted (pasted text) | 42 | **31 (74%, 59% to 85%)** | 0 | 10 (and one under 5 words) |
| Held-out, the same, the outlet it came from **not** counted (web address) | 42 | **5 (12%, 5% to 25%)** | 0 | 36 |
| Held-out, distorted copies of real headlines | 9 | 0 (0% to 30%) | 4 | 5 |
| Held-out, invented headlines | 12 | 0 (0% to 24%) | 0 | 12 |
| **Third set (23 Nov), real, outlet counted** | 84 | **63 (75%, 65% to 83%)** | 1 | 19 (and one under 5 words) |
| Third set, real, outlet **not** counted | 84 | **14 (17%, 10% to 26%)** | 1 | 68 |
| Third set, distorted copies (one number, place or verb changed automatically) | 30 | 0 (0% to 11%) | 15 | 15 |
| **Both independent sets together**, real, outlet counted / not counted | 126 | **94 (75%, 66% to 81%)** / **19 (15%, 10% to 22%)** | 1 / 1 | |
| Both independent sets together, distorted | 39 | 0 (0% to 9%) | 19 | 20 |
| Current (thresholds chosen here), real, outlet counted / not counted | 42 | 32 (76%) / 5 (12%) | 0 / 0 | 10 / 37 |
| Current, distorted | 14 | 0 | 8 | 6 |
| Current, invented | 20 | 0 | 0 | 20 |
| Older news (30 real, 30 fake from the project's text dataset) | 60 | real 1 of 30 (3%), fake 0 of 30 | 0 | 29 and 30 |

**What the third set showed, and what was changed because of it.** It had 84 real headlines (12 from each of seven outlets) and 30 automatically distorted copies. Two results were wrong. (1) A distorted headline, "Iraq wants diplomacy to end war ..." (the original said Iran), was **confirmed** by a Reuters headline: the inference model read the two as the same statement. This is why the "same names and numbers" rule was added. It also removes the confirmation for the right reason (the name that was swapped is missing from the other headline), but it was added after one observation and checked on all sets, so it is a coarse safeguard and the third set's distorted figure is no longer an untouched test of it. **What it costs:** before it, 35 / 33 / 63 real headlines were corroborated in the current / held-out / third set (83% / 79% / 75%), and 8 / 8 / 18 with the outlet not counted; after it, 32 / 31 / 63 and 5 / 5 / 14. Spelling differences between outlets (Araghchi / Araqchi) and a different first noun also block a match. (2) A real headline, "Trafalgar Square Christmas tree felled in Norway", was shown as "a listed outlet reports something different" because a Reuters fact-check headline on the same tree scored as contradicting it (1 of 126 real headlines; nothing was done about it: it is the "different" label, never a ruling, but it does move a *Likely Real* reading to *Unverified*).

**Related coverage.** When nothing matches, listed outlets' headlines on the same subject are listed for the reader. Replaying the saved sets: of the real headlines that were *Not found* with the outlet not counted, related coverage was shown for 14 of 36 (held-out) and 30 of 68 (third set); for invented headlines, 1 of 12 (held-out) and 3 of 20 (current). It also appears next to some distorted headlines (6 of 15 in the third set), so its presence says nothing about whether a headline is true. It is a convenience for checking by hand, not a test.

**What this does not show.** (1) The real headlines were taken from the feeds of the same outlets that are in the directory, so "outlet counted" mostly shows that the search finds the outlet's own page; it is not independent proof. (2) The fake headlines are invented or edited by the developers, not real disinformation; real fake news is often copied from or imitates real reports. A real headline pasted above an invented article body is corroborated by this check, because only the headline is compared; since 23 November a second check reads the text against its headline (section 6b), which stops the *Likely Real* when the text is about something else or says something different, but not when the text agrees with the headline and then adds false details. (3) A news search returns recent news: real headlines older than a few weeks were found in only 10% of cases, so old true stories come out *Not found*. (4) Local and specialist outlets are not in the directory, so a true story reported only by them is *Not found*. (5) The sets are small (9 to 126 per group) and written or collected by the developers; the distorted headlines of the third set were made by a script (one number, place or verb swapped), the invented ones were written by hand. (6) Google News is an unofficial source that can stop working; the check then says so and the rest of the analysis is unchanged.

**Reproduce.** `python ai_models/training/evaluate_corroboration.py` (no internet needed; needs `requirements-ml.txt`). `python ai_models/training/collect_corroboration_data.py` collects a new test set and needs internet access; the feeds change by the hour, so it gives different headlines. The saved files in `ai_models/evaluation/corroboration/` contain short news headlines and outlet names that a search feed returned. They are kept only so the measurement can be repeated; the headlines belong to their outlets, and they are not a dataset this project redistributes or claims rights in. Remove them if that is a concern: only the evaluation script depends on them.

## 6b. Text against its headline: `headline_text_consistency` (fixed rules on the evidence model)

**Why.** The headline check (6a) never reads the article. A real headline pasted over a different or false text would be confirmed by a listed outlet and, without this check, could be called *Likely Real*. This check reads the first sentences of the text and asks whether they say what the headline says.

**How it works.** It splits the text into sentences, drops lines that only repeat the headline or are under five words, and keeps the first ten. Windows of one or two of those sentences are compared with the headline: the inference model (`cross-encoder/nli-deberta-v3-small`, the same one the evidence check uses) gives the probability that the window entails the headline or contradicts it, and the share of the headline's content words that the window contains is counted. Numbers and names of the headline are looked for in the whole text (not only in the ten sentences that were read) after both are normalised ("Five" = 5, "$200m" = "200 million", "U.S." = "United States", possessives and hyphens removed, two words that start with the same five letters count as the same). The first word of a headline counts as a name unless it is a function word, a title before a name ("Envoy", "President", "Ex"), an opener such as "How", "Inside" or "LIVE", or an ordinary English word ("Widowed", "Like": it is capitalised only because it begins the headline; "Iraq" and "Trump" are names); a year is not compared; a headline that is a question is not judged for contradiction; abbreviations of up to three capitals ("US", "PM", "NYT") are ignored because they have too many spellings. A headline in Title Case contributes numbers only. Nothing leaves the server. The rules and thresholds are in `backend/app/ml/corroboration/consistency.py` and are shown in the app under every result.

| Result | Rule |
|---|---|
| Consistent | a window entails the headline (model at least 60% sure) and every number and name of the headline appears in the text |
| Contradicts | not consistent, and a window that shares at least half of the headline's content words is judged, with at least 80% certainty, to say the opposite (not for a headline that is a question) |
| Unrelated | fewer than 25% of the headline's content words appear in the text that was read |
| Different details | at least half of the content words appear, but a number or name of the headline appears nowhere in the text (years are not compared) |
| Not stated | anything else: the text is about the subject, but its first sentences do not state the headline |

**Effect on the verdict.** By default only *Unrelated* (the text is about another story) turns *Likely Real* into *Unverified* (reason `headline_text_mismatch`). *Contradicts* and *Different details* are shown with a warning note (`effect_note`) and change nothing, because they also occurred on about one real article in seven (measured below); with `TEXT_MATCH_STRICT=true` all three stop a *Likely Real*, as the first version did. On a page served from the website of a listed outlet (a web address), no result changes the verdict, because that outlet wrote both the headline and the text, so nobody put a real headline over another text; the difference is shown with a note. The check never produces *Likely Fake*, never lowers *Unverified*, and does not touch *Likely Fake*. The policy is in `text_match_verdict.py`, separate from the comparison rules in `consistency.py`, so that the rules that were measured stay byte for byte as they were. It is skipped when there is no headline (or fewer than four words), when the text is under 30 words, when the language is not English, and for a site that declares itself satire. It can be switched off with `TEXT_MATCH_ENABLED=false`. It applies to pasted text and to web addresses.

**How it was measured.** Real articles were collected from five outlets (BBC, The Guardian, Al Jazeera, The Hindu, The Express Tribune): the headline from the outlet's feed and the article text from the article page, read with the application's own page reader (`collect_headline_body_data.py`). Dawn and The New York Times refuse automated requests and are not in the sets. Every pair goes unchanged through the production function. There were four sets and three versions of the rules. Only a set that was collected before the rules it measures were changed, and not looked at until then, is an independent measurement; that is the last set only.

1. **Development set (70 articles).** The rules (version 1) were written and adjusted on it. The first run wrongly flagged 20 of 70 real articles (spelling differences such as "Korea"/"Korean", possessives, hyphens, abbreviations, headline openers); after fixing them 5 of 70 were flagged.
2. **Second set (58).** Version 1 was frozen before it was read: 4 of 58 real articles were wrongly flagged (7%). Three changes made after looking at those four (an amount written "$200m" equals "200 million", a title before a name is not a name, names and numbers are looked for in the whole text) gave version 2, which flags 2 of 58. This set is therefore no longer independent.
3. **Third set (55).** Version 2 was frozen before it was read: **8 of 55 real articles were wrongly flagged (15%)**. The 7% above had been optimistic, and the changes had not lowered the rate on new articles. Looking at the 8 also showed a fault in the measurement: the sets of the first three rounds held only the first 250 words of each article, while the application compares a headline with the whole text it is given. A name such as "LGBTQ+" that comes late in an article therefore counted as missing in the measurement but not in the application. With the whole text (the same articles, pages read again) version 2 flags 6 of 55. This set is no longer independent either.
4. **Fourth set (59 articles, whole texts, collected from the business, technology, health and national news sections as well as world news; none was read before the rules were frozen).** Version 3 was written after the third round and frozen at 14:57 on 23 November 2026 (checksum of `consistency.py` in `headline_body.json`). Version 3 changes: a headline that is a question cannot be contradicted (it claims nothing); a year is not compared; the first word of a headline is a name only if it is not an ordinary English word (list in `ordinary_words.txt`, taken from the SCOWL word lists, so that "Like" and "Widowed" are not names but "Iraq" and "Trump" are); "ex" and "former" are titles.

Fourth set, version 3 (flagged = Contradicts, Unrelated or Different details, the results that stopped a *Likely Real* in version 1):

| Pair | n | Flagged | 95% interval | Other results |
|---|---|---|---|---|
| Real headline with its own text | 59 | **8 (14%)**: 4 Contradicts, 4 Different details, 0 Unrelated | 7% to 25% | 31 Consistent (53%, 40% to 65%), 20 Not stated |
| Real headline with the text of an article about another story | 59 | 55 (93%), all Unrelated | 84% to 97% | 4 Not stated |
| Numbers of the text replaced (only where the headline's number is in the text) | 19 | 14 (74%) | 51% to 88% | 3 Consistent, 2 Not stated |
| Names of the headline replaced in the text | 45 | 27 (60%): 20 Different details, 5 Contradicts, 2 Unrelated | 45% to 73% | 2 Consistent, 16 Not stated |

The same 59 pairs under version 2: own text 10 of 59 flagged (17%, 9% to 29%), another story 55, numbers 14 of 19, names 28 of 45. So on data that neither version had been tuned on, version 3 removed 2 of 10 false alarms and lost 1 of 28 name catches: **a small gain that is within chance**. On the three earlier sets, where version 3 was written after looking at the false alarms, it removes more (dev 6 to 3, second 2 to 1, third 8 to 3 on 250 words and 6 to 2 on whole texts); those drops show that the changes fix the cases they were made for, not that they generalise. `headline_body_v1.json` and `headline_body_v2.json` hold all sets under versions 1 and 2, and `headline_body.json` under version 3. Hand-written texts exist for the second set only (written by the developer who wrote the rules): to say the opposite 15 of 16 flagged under both versions; to agree and add invented details 1 of 16 flagged under versions 1 and 2 and 0 of 16 under version 3 (15 Consistent). One story and one headline appear in two of the sets.

**What the measurements show, and what the application therefore does.** On the sets that were new to the rules (15%, 14% and, for version 2, 17%), about one real article in seven got Contradicts or Different details, and nothing in the rules separates those from the real alterations they were written to find: the same two parts catch swapped names and numbers. What they react to in real articles is a small model reading a long or compound headline as the opposite of a text that agrees with it (4 of the 8 on the fourth set, for example "attacks hit wartime high" against "reached their highest"), a figure written with different rounding ("$3.8bn" against "$3.79bn"), an ordinal ("23rd") or a typing slip in the headline. These are not fixable by more rules without measuring on yet another new set each time.

Unrelated is different. Real articles got it in 1 of 242 cases over four sets (0.4%, 0.1% to 2.3%), and a text taken from another story got it in 230 of 242 (95%, 92% to 97%). **So by default only Unrelated stops a *Likely Real*; Contradicts and Different details are shown as a warning and change nothing** (`text_match_verdict.py`; `TEXT_MATCH_STRICT=true` restores the first behaviour). The price is stated plainly: with the default, a real headline over a text about the same subject with changed names, numbers or the opposite claim keeps its verdict. Under the default policy such texts were withheld only when they happened to read as Unrelated (7 of 200 name changes, 0 of 19 number changes on the fourth set, 0 of 16 hand-written opposite texts). The warning and the sentences compared are still shown to the reader. On a web address from a listed outlet's own website no result changes the verdict at all, because that outlet wrote both the headline and the text. For pasted text and for sites that are not listed, the false-alarm rate of the default is the 0.4% above (0 of 59 on the fourth set), not the 14%.

**What this does not show.** (1) **The limit that matters most:** a text that agrees with its headline in its first sentences and then adds false details reads as *Consistent*. 14 of 16 such texts did under version 1 and 15 of 16 under version 3, and the check cannot see anything after the first ten sentences. Someone who copies a real headline and restates it in the first sentence passes. (2) The altered texts are machine-altered (numbers, names) or were written by the developer who also wrote the rules (32 texts); a person trying to deceive would write differently, and a text on the same subject written to mislead may share enough words to pass. (3) The real articles are from five outlets that are all in the directory, and they include some page furniture from the reader (captions, dates). (4) Samples are small and the intervals wide; the figures differ between sets by more than the intervals suggest, because the rules were looked at on three of them. (7) By default a text about the same subject with changed names, numbers or the opposite claim is only a warning, so the application catches "a real headline over another story" and little of "a real headline over an altered version of the same story". (5) It compares a text with its headline only; it does not check whether either is true, and a true text under a headline that only roughly summarises it is *Not stated* or, with a figure written differently, may be flagged. (6) English only.

**Reproduce.** `python ai_models/training/evaluate_headline_body.py dev,test,test2,test2_full,test3` (or `both`; no internet needed; needs `requirements-ml.txt`; about 25 minutes on two CPU cores; `HEADLINE_BODY_RESULTS=path` writes elsewhere) rewrites `ai_models/evaluation/results/headline_body.json` and stores the checksum of the rules that produced each set's figures. `headline_body_v1.json` holds the figures of the first version of the rules. `python ai_models/training/collect_headline_body_data.py [seed] [per_outlet] [name]` collects new articles and needs internet access. The saved files in `ai_models/evaluation/headline_body/` contain the first 250 words of articles and the hand-written texts. The article texts belong to their outlets; they are kept only so that the measurement can be repeated, are not a dataset this project redistributes, and can be removed (only the evaluation script depends on them).

## 7. Image with text: `text_image_consistency` (pretrained plus measured thresholds)

The text model, the image forensics and a CLIP image-text similarity each give their own result. A fixed written rule combines them: the base verdict is the text model's (or *Indicators Only* for an image alone, otherwise *Unverified*); if the image and text clearly do not match and the base verdict is not *Likely Fake*, the verdict is *Mismatch Flagged*. Image forensics never changes the verdict. The rule is not a learned model.

| Measured | Value |
|---|---|
| What | 600 Flickr30k test images with their captions, split in half: thresholds chosen on 300, reported on the other 300. Non-matching pairs were made by moving a caption to another image (random) or to the most similar other caption (hard) |
| Separation | ROC AUC 0.995 for matching versus random captions and 0.899 versus hard mismatches |
| Thresholds | Similarity below 0.277 counts as not matching and from 0.333 as matching (95% precision target) |
| Held-out behaviour | Of matching pairs, 40% were called consistent, 49% unclear and 11% inconsistent (a false alarm). Of hard mismatches, 72% were called inconsistent |
| Not measured | News photographs. NewsCLIPpings was not available, so real out-of-context news images are untested |

## 8. Video: `video_frame_swin_ffpp` (experimental)

Pipeline: the video is checked by content (container signature, then OpenCV must open it) and by limits; 16 frames are sampled evenly across the whole video; the largest face in each frame is found with YuNet and cropped with a 40% margin; each crop is scored by the frame classifier; the scores are combined (median) into one video score; two thresholds turn that score into *Likely Fake*, *Likely Real* or *Unverified*. A video is never judged from a single frame: at least 8 frames with a face are required. A frame without a face is reported and not scored.

**Frame-based, not temporal.** Every frame is judged alone. The summary over time (average level, share of flagged frames, longest run, jumps) describes the sequence of scores. Nothing learns motion, flicker, lip-sync or audio. The interface and the API say so in every result.

| Item | Value |
|---|---|
| Frame model | `hchcsuim/FFPP-Raw_1FPS_faces-expand-40-aligned_val-ds-celeb-df`, Swin-Tiny fine-tuned by a third party on FaceForensics++ faces, Apache-2.0, revision pinned. Its model card is nearly empty; the repository name says Celeb-DF was its validation set. Not trained here |
| Choice of model | The first pretrained candidate, `dima806/deepfake_vs_real_image_detection`, scored at chance on Celeb-DF (frame ROC AUC 0.47; its video scores were below chance on 24 test videos, so no thresholds could be set). It was dropped, and the record is `video_candidate_dima806_celebdf.json`. Other candidates were tried informally afterwards and the scores of those that were rejected were not kept in the repository, so none is reported. The chosen model was picked while looking at part of the 48-video Celeb-DF test sample, which makes that sample's result optimistic |
| Calibration | The combining rule (median) and both thresholds (real up to 0.797, fake from 0.962, 90% precision target) were chosen on 120 Celeb-DF v2 videos that are not on the official test list, and never changed afterwards |
| Data | `ai_models/training/prepare_video_data.py` downloads the samples with fixed seeds from public Hugging Face mirrors: Celeb-DF v2 (`gonnerthetooner/deepfake_video_data`) and Google DeepFakeDetection (`angads24/deepfake-video`). Celeb-DF is for research use. Nothing is redistributed |

| Videos | Real / fake | Video ROC AUC (95% bootstrap interval) | One frame only | Decided | Correct when decided |
|---|---|---|---|---|---|
| Calibration: Celeb-DF, not on the test list | 60 / 60 | 0.907 (0.85 to 0.96) | 0.862 | 98 of 120 | 90.8% |
| Held-out Celeb-DF test list (optimistic, see above) | 24 / 24 | 0.933 (0.84 to 0.995) | 0.931 | 42 of 48 | 92.9% |
| **Different dataset: Google DeepFakeDetection** | 20 / 20 | **0.843 (0.71 to 0.95)** | 0.739 | 31 of 40 | **80.7%** |

On the different dataset the decision rule is right about four times in five, below its 90% aim, so the thresholds do not transfer fully. Using many frames helps there (video AUC 0.843 against 0.739 from a single frame). The 95% intervals are wide because each set has only tens of videos.

Not measured: news broadcast footage, heavy re-compression, small or non-frontal faces, manipulation methods other than face swaps, lip-sync and voice fakes. Audio is never analysed. Videos are decoded in the server process with limits on size, length, resolution and time; a sandboxed worker is not built.

## 9. Not built

| Item | What would be needed |
|---|---|
| A model that learns motion and timing across frames, and audio analysis | A video model trained on a large labelled set (FaceForensics++, DFDC, Celeb-DF), with a GPU |
| Image-text consistency on news | NewsCLIPpings or a similar labelled set |
| Evidence retrieval measured end to end | A hand-checked set of claims with the right sources marked |
| A learned image detector | A labelled set of manipulated and authentic images and a validation across generators |
| A trained source-credibility model | A source-reliability list and a policy about who decides |

## 10. Version and registry behaviour

- Each analysis stores the model version that produced it.
- Changing the model means a new version number in the registry and a new row in `model_versions`. Older analyses keep pointing at their version.
- If a different scikit-learn version is installed, the text module reports `unavailable` and the API answers `503` with the retrain command instead of scoring with a possibly broken file.
