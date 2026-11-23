# Datasets

No dataset is committed to Git. The training script downloads what it needs, checks it, and writes a manifest that records where the data came from and how it was cleaned.

| Folder | Content | In Git? |
|---|---|---|
| `raw/` | Files exactly as downloaded | No (only `.gitkeep`) |
| `processed/` | Cleaned and split files made by the script | No (only `.gitkeep`) |
| `manifests/` | One JSON file per dataset: source, licence statement, row counts, removed rows, label checks, file hashes | Yes |

## Datasets used by the current build

### GonzaloA/fake_news (training)

- Source: https://huggingface.co/datasets/GonzaloA/fake_news
- Used for: training and validating the English text baseline.
- Size after cleaning: 24,261 train, 8,083 validation, 8,084 test rows (156 empty or very short rows and 3 duplicate or cross-split rows were removed).
- Licence: **the dataset card does not state one.** The manifest records this and the data is used for academic research only. Do not redistribute it.
- Provenance: the card says it mixes Kaggle fake-news collections and does not document the sources or the annotation. The label direction (1 = real) was checked by us: 95.9% of label-1 articles carry a wire-agency tag against 0.04% of label-0 articles.
- Known weakness: articles of this kind differ in style by source. Datelines such as "(Reuters)" are removed before training, but other source-style shortcuts may remain. This is why the model is also tested on a different collection.

### LIAR2 test set (external evaluation only)

- Source: https://huggingface.co/datasets/chengxuphd/liar2
- Licence on the dataset card: apache-2.0.
- Size: 2,296 rows used, 57.6% fake-ish.
- Label mapping: pants-fire, false and barely-true are treated as fake-ish, half-true, mostly-true and true as true-ish.
- Used for: measuring how well the text model transfers to short political statements. It is never used to train or tune anything.

### Bend the Truth, Urdu (Urdu text model)

- Source: https://huggingface.co/datasets/community-datasets/urdu_fake_news (Amjad et al., 2020, Journal of Intelligent & Fuzzy Systems).
- Used for: training and testing the experimental Urdu model (`bash scripts/training/train_text_urdu.sh`).
- Size after cleaning: 634 train and 260 test articles (4 duplicates removed from train, 2 test articles that also occur in train removed).
- Licence: **unknown on the dataset card**; used for academic research only. Do not redistribute it.
- Known weakness: nearly every fake training article has a near-identical real partner, so cross-validation is grouped by pair. It is the only Urdu collection used, so there is no second collection to test on.

### FEVER with gold evidence (evidence stance measurement)

- Source: https://huggingface.co/datasets/copenlu/fever_gold_evidence (FEVER, Thorne et al., 2018, built on Wikipedia).
- Licence: CC BY-SA 3.0.
- Used for: measuring the stance step of the evidence module on 1,200 claims (600 supports, 600 refutes) with their gold evidence. Retrieval is not measured. Run with `scripts/evaluation/evaluate_evidence.sh`.

### Flickr30k 1k test split (image-text similarity thresholds)

- Source: https://huggingface.co/datasets/nlphuji/flickr_1k_test_image_text_retrieval
- Licence: Flickr30k terms, research use only.
- Used for: measuring CLIP similarity of matching and moved captions on 600 images and choosing the thresholds (300 images for the thresholds, 300 held out). These are everyday photographs, not news. Run with `scripts/evaluation/evaluate_clip.sh`.

### Celeb-DF v2 and Google DeepFakeDetection samples (video evaluation)

- Sources (public Hugging Face mirrors): `gonnerthetooner/deepfake_video_data` for Celeb-DF v2 (Li et al., 2020) and `angads24/deepfake-video` for Google's DeepFakeDetection set.
- Used for: calibrating and testing the video module on small seeded samples (120 and 48 Celeb-DF videos and 40 DeepFakeDetection videos). `ai_models/training/prepare_video_data.py` selects the same videos every time. Run with `scripts/evaluation/evaluate_video.sh`.
- The video samples have no manifest file; the seeded selection and the results are recorded in `ai_models/evaluation/results/video_frame_model.json`.
- Terms: the videos are for research use. Nothing is redistributed; they are downloaded into `raw/` and are not in Git. The mirrors' own licence statements were not independently verified.

## How to download and prepare

```bash
bash scripts/training/train_text_model.sh download     # fetch both datasets into datasets/raw/
bash scripts/training/train_text_model.sh prepare      # clean, de-duplicate, split
bash scripts/training/train_text_model.sh all          # everything, including training and evaluation
```

On Windows use `scripts\training\train_text_model.ps1` with the same stage names. Downloading needs internet access once. After that, the text training runs offline.

## Datasets discussed in the research but not used

These are named in `docs/research/` as candidates for larger or stronger versions of the modules. None is downloaded by this repository, and their licences or access forms must be checked before use.

| Dataset | Intended use | Reference |
|---|---|---|
| FaceForensics++ | Training a video detector (the pretrained video model was trained on it by a third party) | Rössler et al. (2019) |
| DFDC | Video deepfake detection, a larger test | Dolhansky et al. (2020) |
| NewsCLIPpings | Image-text consistency on news | Luo et al. (2021) |
| Ax-to-Grind Urdu, FIRE 2020 Urdu | A second Urdu collection for a cross-dataset test | Harris et al. (2024) |
| RRDataset, AI-GenBench | Image detector evaluation | Li et al. (2025), Pellegrini et al. (2025) |

## Rules for adding a dataset

1. Record the source URL and the licence exactly as stated. If none is stated, write that.
2. Write a manifest in `manifests/` with row counts, removed rows and a file hash.
3. Check for duplicates and leaks between splits.
4. Check what the labels mean and say so in the manifest.
5. Never commit raw data, private data or personal data.
