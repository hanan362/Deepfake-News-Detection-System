# Feasibility analysis

## 1. Technical feasibility

| Component | Requirement | Verdict | Evidence |
|---|---|---|---|
| Web application, API, database | Python 3.10 or newer, Node 22, SQLite | Feasible, built | Backend tests pass in a Linux VM on the team's Windows laptop (Python 3.10) and in a Linux container (Python 3.13). The Windows PowerShell scripts are written but were not run natively |
| Text baseline | CPU, few hundred MB of memory | Feasible, built | About 90 seconds to retrain on a CPU |
| Image indicators | CPU, Pillow | Feasible, built | ELA and metadata are pure Python and Pillow |
| Transformer text model | GPU preferred, or a distilled model on CPU | Feasible with limits | Sanh et al. (2019) report a distilled BERT that is 40% smaller and 60% faster. Fine-tuning on a laptop CPU is slow but possible for small data |
| Video deepfake detection | GPU, tens of GB of data | Hard on laptop hardware | Large datasets with access forms. Pretrained detectors need validation before use |
| Image-text consistency | CLIP-sized model, CPU possible for inference | Feasible for inference, uncertain accuracy | Radford et al. (2021) model weights are large downloads |
| Evidence retrieval | Search access, or an offline index | Feasible only with an external source or a curated corpus | Needs a decision about which sources to trust and how to store them |
| Docker deployment | Docker engine | Built and run once in a Linux sandbox (see the testing report); not run on Docker Desktop | See the limitations in the testing report |

## 2. Economic feasibility

The system uses only free and open-source components. No paid API key is required for the implemented features. The text and image modules run on a personal laptop. Costs would appear only if the team chose to rent a GPU for training or use a hosted language model. Both are optional and are not part of the current scope.

## 3. Operational feasibility

| Aspect | Assessment |
|---|---|
| Installation | A short local install (see `docs/user_manual/installation_manual.md`). A Docker route is provided; it was run once in a Linux sandbox, not on Docker Desktop |
| Administration | An admin account is created from environment variables. An admin page manages users, feedback, audit log and shows model status |
| Maintenance | Migrations with a drift test, a version guard on the model file, and a one-command retrain |
| Users | A signed-in user can analyse text and images, review history, download a PDF report and send feedback |
| Support burden | Honest status messages explain why a feature is unavailable, which cuts misunderstanding |

## 4. Schedule feasibility

The 12-month roadmap (`docs/ROADMAP.md`) puts the implemented baseline and application in the first months and keeps the heavier modules for the later months with explicit gates. Video detection and evidence verification are the schedule risks because they depend on data access and hardware. The roadmap allows these to slip without blocking the rest.

## 5. Legal and ethical feasibility

| Issue | Position |
|---|---|
| Dataset licences | The training dataset's card states no licence, so the manifest records that and limits use to academic research. LIAR2 is apache-2.0 on its card. Licences of video datasets must be checked before use |
| Personal data | Uploaded media is private to the owner and is never listed publicly. Passwords are hashed with bcrypt, reset tokens are stored hashed |
| Harm from wrong verdicts | A false "Likely Fake" label could harm a publisher or reader. The system abstains, shows measured accuracy next to its limits, and never says "Misleading" or "Verified" |
| Harm from missing labels | Pennycook et al. (2020) show that unlabelled items may be read as verified. Results without a verdict say so explicitly |
| Misuse | A detector can be used to tune fakes. No generation features are included |
| Public figures | No images of real people are bundled in the repository |

## 6. Risk register

| Risk | Likelihood | Impact | Response |
|---|---|---|---|
| Dataset access refused or slow | Medium | Delays video work | Start with openly downloadable data. Ask early |
| No GPU | High | Limits transformer and video work | Use distilled models and small experiments. Report limits |
| External transfer stays near chance | High for text baseline | Honest negative result | Report it, try a fine-tuned small model, compare |
| Team members change availability | Medium | Schedule slips | Documentation and tests let anyone pick up a module |
| Docker path has an undiscovered fault | Medium | Deployment friction | Verify on a machine with Docker before any demo |
| Over-claiming in demos | Medium | Loss of credibility | The interface and documents state limits. Use the acceptance checklist before a demo |

## 7. Conclusion

The implemented core is feasible and has been built and tested. The heavier modules are feasible as research tasks on a staged schedule, but each depends on data access, hardware or a validation result that is not yet in hand. They are therefore listed as planned and not presented as working.
