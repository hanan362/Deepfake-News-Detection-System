# Research documentation

This folder holds the research side of the Deepfake News Detection System. Everything here is meant to be read next to the code: where a document says "we measured", the number comes from `ai_models/evaluation/results/` and is shown in the app on the Models page.

## What is in this folder

| File | What it contains |
|---|---|
| `member1_nlp_text_papers.md` | 10 verified papers on text fake-news detection, datasets, LLM-era misinformation and Urdu |
| `member2_image_video_papers.md` | 10 verified papers on deepfake video, AI-generated image detection and benchmarks |
| `member3_multimodal_evidence_xai_papers.md` | 10 verified papers on evidence-based fact checking, image-text consistency and explainability |
| `member4_engineering_ai_papers.md` | 10 verified papers on model and dataset documentation, calibration, abstention, interface effects and efficient models |
| `references.md` | All 40 references in one list |
| `literature_review.md` | Narrative review that connects the 40 papers |
| `comparative_analysis.md` | Side-by-side comparison of the approach families and where this project sits |
| `research_gap.md` | The gaps the literature leaves open, each tied to papers and to our own measurements |
| `proposed_contribution.md` | What this project contributes and what it does not claim |
| `research_methodology.md` | How the work is evaluated and what threats to validity remain |
| `feasibility_analysis.md` | Technical, economic, operational, schedule, legal and ethical feasibility |

## How the papers were verified

1. Every paper was looked up by DOI or arXiv number. Title, authors, year and venue were taken from the record, not from memory.
2. The venue was checked a second time against an independent page: the arXiv journal reference or comment, the publisher, the proceedings (CVF, ACL Anthology, PMLR, NeurIPS) or Crossref. Each entry names which page confirmed its venue.
3. Entries marked "arXiv preprint" have no peer-reviewed venue that we could confirm. We did not guess one.
4. The "problem", "methodology", "dataset" and "reported results" fields stay inside what the abstract or the cited page says. Where an abstract gives no number, the entry says so. Numbers in the text of a paper that we did not read in full are not quoted.
5. The "advantages", "limitations", "gaps", "improvements" and "relevance" fields are our own reading and are labelled as analysis in each file.

No paper in this folder was invented, and no result is quoted that we could not trace. If you find an error, treat the DOI or arXiv link in the entry as the authority and correct the entry.

## Team mapping

| Member | Area | Paper file |
|---|---|---|
| Member 1 | NLP, text datasets, evaluation | `member1_nlp_text_papers.md` |
| Member 2 | Image and video computer vision | `member2_image_video_papers.md` |
| Member 3 | Multimodal fusion, evidence, XAI, research integration | `member3_multimodal_evidence_xai_papers.md` |
| Member 4 | Frontend, UI/UX, backend, database, deployment and responsible-AI engineering | `member4_engineering_ai_papers.md` |

The team and supervisor are listed in [../TEAM.md](../TEAM.md) and shown in the app (`frontend/src/config/project.ts`).
