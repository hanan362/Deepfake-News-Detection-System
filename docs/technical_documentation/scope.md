# Scope

## In scope (implemented)

| Area | Included |
|---|---|
| Accounts | Register, sign in with e-mail or username, sign out, forgot and reset password (token delivered by the operator), profile, avatar, password change |
| Roles | `user` and `admin`, stored in a `roles` table |
| Text analysis | English articles, scored by a trained baseline with exact term explanations and an abstention rule |
| Image analysis | JPEG, PNG and WEBP up to 10 MB and 40 million pixels: Error Level Analysis, a heat map and EXIF metadata, with no verdict |
| Urdu text | A separate experimental model for Urdu articles (Arabic script), chosen automatically from the script |
| News web address | The server fetches a public news page under strict limits, extracts the article, scores it with the text model, and shows a rule-based check of the website |
| Evidence check | Claim selection, retrieval of Wikipedia passages (and published fact-checks with an optional key), and a pretrained stance model; always lists its sources and says *Insufficient Evidence* when nothing reliable is found |
| Image with text | Text model, image forensics and a CLIP image-text similarity, each reported on their own and combined by a fixed written rule; any input may be left out |
| Video | MP4, MOV, WebM or AVI up to 100 MB and 180 seconds: frame sampling, face detection, a per-frame classifier, a summary over time, thumbnails and playback |
| Records | Analysis history with search and filters, deletion, PDF report, print view |
| Platform | Dashboard from the database, feedback and contact flow, admin overview, user management, audit log, an administrator-only model registry and evaluation numbers, and a public list of which checks run |
| Security | bcrypt, token revocation, rate limits, security headers, content-checked uploads, owner-only analyses |
| Operations | Local scripts, Dockerfile, Compose, nginx, `.env` template, Alembic migrations |
| Quality | Back-end, front-end and browser test suites |
| Research | Literature review, gaps, methodology, feasibility, model documentation |

The exact text limits are: at least 60 words, at most 50,000 characters, English or Urdu (other scripts are declined). The web form stops each case before sending. The API answers *Unverified* for text that is too short or in an unsupported script, and refuses text over 50,000 characters with `413 PAYLOAD_TOO_LARGE`.

## Specified, implemented only in part

| Area | What is missing |
|---|---|
| Video deepfake detection | The classifier is frame-based and third-party; there is no model that learns motion, timing, lip-sync or audio. Measured on tens of videos only |
| Multimodal consistency | No labelled news data (NewsCLIPpings) was available; thresholds come from Flickr30k photos |
| Evidence retrieval and fact checking | Only the stance step was measured, on FEVER gold evidence. Wikipedia is the only source without a Google key. No claim-level truth verdict is given |
| News-URL and source credibility | JavaScript-only and paywalled pages cannot be read. The website check uses a small hand-made list and rules, not a trained model |
| Urdu text | One small training collection and no second collection to test on, so the model is labelled experimental |
| Learned image detector | Not built. Images get forensic indicators only |

## Out of scope

| Item | Reason |
|---|---|
| Deciding whether a claim is true | Needs evidence and judgement, which the system does not have |
| Social-network analysis and propagation | Needs data the project does not have |
| Real-time monitoring of social media | Platform terms, scale and legal issues |
| Detecting machine-written text | Not covered by the training data |
| A mobile application | The web interface is responsive instead |
| Sending e-mail | No mail service is configured, so reset tokens are delivered by the operator |
| Multi-instance deployment features | The rate limiter and cache are in memory, per process |

## Assumptions

1. The user runs the system for study or research and checks important claims elsewhere.
2. Datasets are used for academic research under their own terms, and none is redistributed. The video samples are downloaded by a script and are not part of the repository.
3. The deployed text model is trained on the same machine that serves it.
4. Test environments are Linux (Python 3.10 and 3.13) with Node 22. Native Windows and Docker were not verified.
5. The machine-learning modules need the optional packages in `backend/requirements-ml.txt`; the base install works without them.
