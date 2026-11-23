# API reference

The API is a JSON REST API served by FastAPI. The machine-readable description is [`openapi.json`](openapi.json) (OpenAPI 3). When the backend is running, an interactive version is at `http://127.0.0.1:8000/docs` and `http://127.0.0.1:8000/redoc`. A test fails if `openapi.json` no longer matches the application.

## Conventions

| Topic | Rule |
|---|---|
| Base path | `/api/v1` |
| Authentication | `Authorization: Bearer <token>` from `POST /auth/login`. Tokens last 60 minutes by default and carry a unique id. `POST /auth/logout` revokes the token. Changing the password ends all earlier sessions. A disabled account cannot use an old token |
| Roles | `user` and `admin`. Admin routes return 403 for a user. Admins cannot read other users' analyses or media |
| Errors | One envelope for every error: `{"error": {"code", "message", "details"}}`. Validation errors (422) have `details` as a list of `{field, message}` |
| Rate limits | 120 requests per minute per client address in general and 10 per minute on login, registration and password-reset routes (configurable). Over the limit returns 429 |
| Timestamps | ISO 8601 in UTC with an explicit offset, for example `2026-11-21T08:21:37Z` |
| Uploads | `multipart/form-data`. Images: JPEG, PNG or WEBP, at most 10 MB and 40 million pixels. Videos: MP4, MOV, WebM or AVI, at most 100 MB, 180 seconds and 4096 pixels on a side. The type is decided from the file content, not the file name or declared type |
| Text | At least 60 words are needed for a score, English only, at most 50,000 characters. Shorter or non-English text is accepted and answered with an `Unverified` result that explains why |
| Module status | Every analysis names the model that made it. A module whose model or packages are missing answers `503 MODEL_UNAVAILABLE` or returns a result that says which part was not assessed. Nothing is invented |

## Verdict values

| Verdict | Module | Meaning |
|---|---|---|
| Likely Fake | text | The model's probability of the fake class reached the threshold (0.80 by default). Not proof |
| Likely Real | text | The model's probability of the real class reached the threshold. Not proof |
| Unverified | text | Below the threshold, too short, or unsupported script. No verdict was made |
| Indicators Only | image, video, multimodal | Measurements and observations only. There is no confidence value. For video it also means no measured decision rule or no frame classifier is available |
| Likely Fake / Likely Real | video | The video score from the frame classifier is beyond a threshold that was measured on labelled videos. Needs a clear face in at least 8 sampled frames. Not proof |
| Unverified | video | Too few frames with a face, or a score between the two thresholds |
| Mismatch Flagged | multimodal | The image and the text clearly do not match (CLIP similarity below a measured threshold) and the text model did not already say Likely Fake. A flag to look closer |
| Supported, Contradicted, Mixed Evidence, Insufficient Evidence | evidence | Retrieved sources support, contradict, disagree on, or do not settle a claim. Only as reliable as the sources searched |

## Endpoints

### System

| Method | Path | Auth | What it does |
|---|---|---|---|
| GET | `/health` | none | Service health |
| GET | `/modules` | none | Which checks are switched on, a plain description of each, and the size limits (public, no sign-in needed). No model names or measured numbers |
| GET | `/models` | admin | Status of every analysis module and model, with names, versions and measured numbers (administrators only) |
| GET | `/models/evidence/evaluation` | admin | Measured evaluation of the evidence stance model (administrators only) |
| GET | `/models/text-ur/evaluation` | admin | Measured evaluation of the Urdu baseline (administrators only) |
| GET | `/models/text/evaluation` | admin | Measured evaluation of the text baseline (administrators only) |
| GET | `/models/video/evaluation` | admin | Measured evaluation of the video frame model (administrators only) |

### Authentication

| Method | Path | Auth | What it does |
|---|---|---|---|
| POST | `/auth/forgot-password` | none | Start a password reset |
| POST | `/auth/login` | none | Log in with e-mail or username |
| POST | `/auth/logout` | user | End the current session |
| POST | `/auth/register` | none | Create an account |
| POST | `/auth/reset-password` | none | Finish a password reset |

### Profile

| Method | Path | Auth | What it does |
|---|---|---|---|
| GET | `/users/me` | user | Current user |
| PATCH | `/users/me` | user | Update profile |
| DELETE | `/users/me/avatar` | user | Remove your profile picture |
| GET | `/users/me/avatar` | user | Download your profile picture |
| POST | `/users/me/avatar` | user | Upload a profile picture |
| POST | `/users/me/password` | user | Change password |

### Analysis

| Method | Path | Auth | What it does |
|---|---|---|---|
| GET | `/analysis` | user | History of your analyses |
| POST | `/analysis/evidence` | user | Check a claim against Wikipedia and published fact-checks |
| POST | `/analysis/image` | user | Forensic indicators for an image (ELA + metadata) |
| POST | `/analysis/multimodal` | user | An image and its text analysed together (either may be left out) |
| POST | `/analysis/text` | user | Analyse the writing of a news article |
| POST | `/analysis/url` | user | Read a news article from its web address, analyse its text and describe its website |
| POST | `/analysis/video` | user | Frame-based analysis of a video |
| DELETE | `/analysis/{analysis_id}` | user | Delete an analysis and its files |
| GET | `/analysis/{analysis_id}` | user | One analysis with full details |
| GET | `/analysis/{analysis_id}/frames/{index}` | user | A sampled frame of an analysed video, with the face box |
| GET | `/analysis/{analysis_id}/heatmap` | user | Error Level Analysis map (images) |
| GET | `/analysis/{analysis_id}/image` | user | The image you uploaded |
| GET | `/analysis/{analysis_id}/report.pdf` | user | Download a PDF report |
| GET | `/analysis/{analysis_id}/video` | user | The video you uploaded |

### Dashboard

| Method | Path | Auth | What it does |
|---|---|---|---|
| GET | `/dashboard/stats` | user | Your usage statistics |

### Feedback

| Method | Path | Auth | What it does |
|---|---|---|---|
| GET | `/feedback` | user | Your feedback and its review status |
| POST | `/feedback` | user | Send feedback about the system or a result |

### Administration (admin role)

| Method | Path | Auth | What it does |
|---|---|---|---|
| GET | `/admin/audit-logs` | admin | Audit log |
| GET | `/admin/feedback` | admin | All feedback |
| PATCH | `/admin/feedback/{feedback_id}` | admin | Mark feedback as reviewed or dismissed |
| GET | `/admin/models` | admin | Model registry with database records |
| GET | `/admin/stats` | admin | System-wide statistics (counts only, no user content) |
| GET | `/admin/users` | admin | List users |
| PATCH | `/admin/users/{user_id}` | admin | Change a user's role or enable/disable the account |

The analysis routes are `POST /analysis/text`, `/image`, `/url`, `/evidence`, `/multimodal` (multipart: optional `file`, `headline`, `text`; at least one) and `/video`. Each returns the same `Analysis` object with a module-specific `details` part.

## Query parameters

| Route | Parameters |
|---|---|
| `GET /analysis` | `page`, `page_size`, `analysis_type` (`text`, `image`, `url`, `evidence`, `multimodal` or `video`), `verdict`, `q` (search in headline and file name) |
| `GET /admin/users` | `page`, `page_size`, `q` |
| `GET /admin/feedback` | `status` (`new`, `reviewed`, `dismissed`) |
| `GET /admin/audit-logs` | `page`, `page_size`, `action` |

## Request bodies

| Route | Fields |
|---|---|
| `POST /auth/register` | `email`, `username` (3 to 50 of letters, digits, `_`, `.`, `-`), `password` (at least 8 characters with a letter and a digit), optional `full_name` |
| `POST /auth/login` | `identifier` (e-mail or username), `password` |
| `POST /auth/forgot-password` | `email`. The answer is the same whether or not the account exists |
| `POST /auth/reset-password` | `token`, `new_password`. A token works once |
| `PATCH /users/me` | optional `full_name`, `username` |
| `POST /users/me/password` | `current_password`, `new_password` |
| `POST /users/me/avatar` | multipart field `file` (image, re-encoded on the server) |
| `POST /analysis/text` | `text` (required), optional `headline` (at most 500 characters) |
| `POST /analysis/image` | multipart field `file` |
| `POST /analysis/url` | `url` (an http or https address on a public website, at most 1,000 characters). The server fetches the page itself, with limits |
| `POST /analysis/evidence` | `text` (10 to 5,000 characters): a claim, or a passage from which up to five claims are picked |
| `POST /analysis/multimodal` | multipart: optional `file` (image), `headline`, `text`; at least one of them |
| `POST /analysis/video` | multipart field `file` (video) |
| `POST /feedback` | `category` (`bug`, `incorrect_result`, `feature_request`, `other`), `message` (5 to 2,000 characters), optional `analysis_id` |
| `PATCH /admin/users/{id}` | optional `role` (`user` or `admin`), optional `is_active`. An admin cannot demote or disable their own account |
| `PATCH /admin/feedback/{id}` | `status` (`new`, `reviewed`, `dismissed`) |

## Status codes

| Code | Meaning | Error codes |
|---|---|---|
| 200, 201, 204 | Success (204: deleted) | none |
| 400 | Bad request | `WRONG_PASSWORD`, `INVALID_RESET_TOKEN`, `EMPTY_FILE`, `SELF_LOCKOUT` (an admin tried to demote or disable their own account) |
| 401 | Missing, invalid, expired or revoked token, or wrong login | `UNAUTHENTICATED`, `INVALID_TOKEN`, `INVALID_CREDENTIALS` |
| 403 | Not allowed | `FORBIDDEN` (admin role needed), `ACCOUNT_DISABLED` |
| 404 | Not found, or belongs to someone else | `NOT_FOUND` |
| 409 | Already in use | `EMAIL_TAKEN`, `USERNAME_TAKEN` |
| 413 | Upload, text, video length or resolution over the limit | `PAYLOAD_TOO_LARGE` |
| 415 | Not a supported image or video, or not a web page | `UNSUPPORTED_MEDIA_TYPE`, `URL_NOT_A_PAGE` |
| 422 | Validation failed, nothing to analyse, or no checkable claim | `VALIDATION_ERROR`, `NOTHING_TO_ANALYSE`, `NO_CLAIMS_FOUND`, `INVALID_URL`, `URL_NOT_ALLOWED` |
| 429 | Rate limit | `RATE_LIMITED` |
| 502, 504 | The website could not be reached or took too long | `URL_FETCH_FAILED` |
| 503 | A model or package is missing, a feature is switched off, or the server is busy with other videos | `MODEL_UNAVAILABLE`, `URL_FETCH_DISABLED`, `EVIDENCE_DISABLED`, `BUSY` |

## Examples (real responses)

Captured from the running application with a trained text model. Long fields are shortened with `...`.

### Register: `POST /auth/register`

Request:

```json
{
  "email": "sara@example.com",
  "username": "sara",
  "password": "<a password>",
  "full_name": "Sara Khan"
}
```

Response (201):

```json
{
  "id": 1,
  "email": "sara@example.com",
  "username": "sara",
  "full_name": "Sara Khan",
  "role": "user",
  "is_active": true,
  "has_avatar": false,
  "created_at": "2026-11-21T08:24:08.420136Z",
  "last_login_at": null
}
```

### Log in: `POST /auth/login`

Request:

```json
{
  "identifier": "sara",
  "password": "<a password>"
}
```

Response (200):

```json
{
  "access_token": "eyJhbGciOiJI...",
  "token_type": "bearer",
  "expires_at": "2026-11-21T09:24:08.436134Z",
  "user": {
    "id": 1,
    "email": "sara@example.com",
    "username": "sara",
    "full_name": "Sara Khan",
    "role": "user",
    "is_active": true,
    "has_avatar": false,
    "created_at": "2026-11-21T08:24:08.420136Z",
    "last_login_at": "2026-11-21T08:24:08.436451Z"
  }
}
```

### Analyse text: `POST /analysis/text`

Request:

```json
{
  "headline": "City council approves budget",
  "text": "<an article of at least 60 words>"
}
```

Response (201):

```json
{
  "id": 1,
  "analysis_type": "text",
  "verdict": "Likely Real",
  "confidence": 0.9638,
  "status": "completed",
  "headline": "City council approves budget",
  "source_filename": null,
  "submitted_text": "The city council voted on Tuesday evening to approve a new b...",
  "created_at": "2026-11-21T08:24:08.767897Z",
  "model": {
    "module": "text",
    "name": "text_baseline_en",
    "version": "1.0.0",
    "status": "trained_baseline"
  },
  "details": {
    "token_count": 89,
    "script_hint": "latin_or_other",
    "reason": "model_leans_real",
    "probabilities": {
      "fake": 0.0362,
      "real": 0.9638
    },
    "decision_rule": {
      "threshold": 0.8,
      "min_tokens": 60
    },
    "explanation": {
      "method": "TF-IDF value x logistic-regression coefficient (exact for this linear model)",
      "toward_fake": [
        {
          "term": "that the",
          "weight": 0.2018
        },
        {
          "term": "reports",
          "weight": 0.1834
        }
      ],
      "toward_real": [
        {
          "term": "on tuesday",
          "weight": -0.3852
        },
        {
          "term": "said",
          "weight": -0.3505
        }
      ],
      "intercept": 0.0615,
      "caution": "These terms show what moved the score in the training data's statistics. They are not evidence that any claim in the text is true or false."
    }
  },
  "limitations": "This is a writing-pattern baseline, not a fact checker. A verdict does not say whether the...",
  "is_demo": false,
  "has_heatmap": false
}
```

### Text that is too short

Request:

```json
{
  "text": "Too short to analyse."
}
```

Response (201):

```json
{
  "verdict": "Unverified",
  "confidence": null,
  "details": {
    "token_count": 4,
    "script_hint": "latin_or_other",
    "reason": "too_short",
    "message": "The text has 4 words. The model was trained on full articles and needs at least 60 words; shorter claims are outside what it has seen."
  }
}
```

### Analyse an image: `POST /analysis/image` (multipart field `file`)

Response (201):

```json
{
  "id": 3,
  "analysis_type": "image",
  "verdict": "Indicators Only",
  "confidence": null,
  "status": "completed",
  "headline": null,
  "source_filename": "photo.jpg",
  "submitted_text": null,
  "created_at": "2026-11-21T08:24:08.817987Z",
  "model": {
    "module": "image",
    "name": "ela_forensics",
    "version": "1.0.0",
    "status": "heuristic"
  },
  "details": {
    "observations": [
      "No camera metadata (EXIF) found. This is normal for images shared through messaging apps and social media, which strip it, so it says little by itself."
    ],
    "metadata": {
      "has_exif": false
    },
    "image": {
      "width": 160,
      "height": 120,
      "format": "JPEG"
    },
    "ela": {
      "mean": 0.0,
      "max": 0.0,
      "block_cv": 0.0,
      "quality": 90,
      "grid": 16
    },
    "map_note": "The map shows JPEG recompression error. It is not an AI attention map."
  },
  "limitations": "These are forensic indicators, not a verdict. Error Level Analysis and metadata cannot rel...",
  "is_demo": false,
  "has_heatmap": true
}
```

### Analyse a video: `POST /analysis/video` (multipart field `file`)

Response (201):

```json
{
  "id": 1,
  "analysis_type": "video",
  "verdict": "Likely Real",
  "confidence": null,
  "status": "completed",
  "headline": null,
  "source_filename": "clip.mp4",
  "source_url": null,
  "submitted_text": null,
  "created_at": "2026-11-21T10:15:08.827584Z",
  "model": {
    "module": "video",
    "name": "video_frame_swin_ffpp",
    "version": "1.0.0",
    "status": "experimental"
  },
  "details": {
    "video": {
      "width": 1920,
      "height": 1080,
      "fps": 24.0,
      "frame_count": 504,
      "duration_seconds": 21.0,
      "container": "mp4"
    },
    "sampling": {
      "requested": 16,
      "sampled": 16,
      "with_face": 16,
      "min_face_frames": 8
    },
    "frames": [
      {
        "index": 15,
        "t": 0.625,
        "face_found": true,
        "face_size": 0.0901,
        "p_fake": 0.0719,
        "sharpness": 123.9,
        "ela_mean": 1.6644,
        "has_image": true
      },
      {
        "index": 47,
        "t": 1.958,
        "face_found": true,
        "face_size": 0.0849,
        "p_fake": 0.635,
        "sharpness": 129.91,
        "ela_mean": 1.6249,
        "has_image": true
      },
      {
        "...": "one entry per sampled frame"
      }
    ],
    "temporal": {
      "frames_scored": 16,
      "mean": 0.3586,
      "median": 0.2578,
      "min": 0.0222,
      "max": 0.9976,
      "std": 0.3395,
      "flagged_share": 0.3125,
      "longest_flagged_run": 3,
      "jumpiness": 0.3077,
      "aggregator": "median",
      "video_score": 0.2578,
      "suspicious_moments": [
        {
          "t": 1.958,
          "p_fake": 0.635
        },
        {
          "t": 8.5,
          "p_fake": 0.5446
        },
        {
          "t": 17.708,
          "p_fake": 0.9976
        },
        {
          "t": 19.0,
          "p_fake": 0.8964
        },
        {
          "t": 20.333,
          "p_fake": 0.9642
        }
      ]
    },
    "decision": {
      "status": "decided",
      "rule": "Frames are sampled evenly across the video and the largest face in each is scored by an image classifier. The video score is the median of the face-frame scores. At least 8 frames with a face are required. Scores above the 'fake' threshold give Likely Fake, scores below the 'real' threshold give Likely Real, anything between gives Unverified. The thresholds were measured on training videos (see Models).",
      "thresholds": {
        "fake_min": 0.9616,
        "real_max": 0.7969,
        "target_precision": 0.9
      }
    },
    "model": {
      "kind": "frame_based_classifier_with_temporal_aggregation",
      "id": "hchcsuim/FFPP-Raw_1FPS_faces-expand-40-aligned_val-ds-celeb-df",
      "temporal_model": false,
      "note": "Each frame was scored on its own by an image classifier. The summary over time (average level, share of flagged frames, longest run) describes those scores; it is not a model that learns motion or timing.",
      "problem": null
    },
    "observations": []
  },
  "limitations": "This is a frame-based baseline: each frame is scored alone and the scores are summarised over the video. It does not det...",
  "is_demo": false,
  "has_heatmap": false
}
```

This is a real response for one sample video (a face-swap video from the Google DeepFakeDetection set). The frame classifier called it real, which is a miss: it is wrong on about one video in five on samples like this (see the administrators' Models page). `has_image` means a thumbnail can be fetched from `GET /analysis/{id}/frames/{index}`.

### Validation error

Request:

```json
{
  "email": "bad.test",
  "username": "x",
  "password": "123"
}
```

Response (422):

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed.",
    "details": [
      {
        "field": "email",
        "message": "value is not a valid email address: An email address must have an @-sign."
      },
      {
        "field": "username",
        "message": "String should match pattern '^[A-Za-z0-9_.-]{3,50}$'"
      },
      {
        "field": "password",
        "message": "Value error, Password must be at least 8 characters and contain a letter and a digit."
      }
    ]
  }
}
```

### Missing token: `GET /analysis`

Response (401):

```json
{
  "error": {
    "code": "UNAUTHENTICATED",
    "message": "Authentication required.",
    "details": null
  }
}
```

### History page: `GET /analysis?page_size=2`

Response (200):

```json
{
  "items": [
    {
      "id": 3,
      "analysis_type": "image",
      "verdict": "Indicators Only",
      "confidence": null,
      "status": "completed",
      "headline": null,
      "source_filename": "photo.jpg",
      "submitted_text": null,
      "created_at": "2026-11-21T08:24:08.817987Z",
      "model": {
        "module": "image",
        "name": "ela_forensics",
        "version": "1.0.0",
        "status": "heuristic"
      },
      "details": null,
      "limitations": null,
      "is_demo": false,
      "has_heatmap": true
    }
  ],
  "total": 3,
  "page": 1,
  "page_size": 2
}
```

### Which checks run: `GET /modules` (public)

What the interface needs to offer the checks. It carries no model names, algorithms, datasets or measured numbers.

Response (200):

```json
{
  "models": [
    { "module": "text", "status": "trained_baseline", "description": "Reads the wording of an English article and shows how closely it resembles articles known to be real or fake. It does not check facts." },
    { "...": "one entry per module (text, text_ur, image, video, multimodal, evidence, url)" }
  ],
  "limits": {
    "min_text_words": 60,
    "max_text_chars": 50000,
    "max_image_mb": 10,
    "max_image_pixels": 40000000,
    "max_video_mb": 100,
    "max_video_seconds": 180,
    "text_languages": ["en", "ur"]
  }
}
```

A module that cannot run here has the status `unavailable` and the description "This check is not available on this server right now."; the reason (for example "retrain the model") is only in the administrator view.

### Model registry: `GET /models` (administrators only)

Needs an administrator's token: no token gives 401, an ordinary user's token gives 403 `FORBIDDEN`. The `/models/{text,text-ur,evidence,video}/evaluation` routes are protected in the same way.

Response (200):

```json
{
  "models": [
    {
      "module": "text",
      "name": "text_baseline_en",
      "version": "1.0.0",
      "status": "trained_baseline",
      "language": "en",
      "algorithm": "TF-IDF (1-2 grams) + Logistic Regression"
    },
    {
      "...": "one entry per module (text, image, video, multimodal, evidence, url)"
    }
  ],
  "limits": {
    "min_text_words": 60,
    "max_text_chars": 50000,
    "max_image_mb": 10,
    "max_image_pixels": 40000000,
    "text_confidence_threshold": 0.8
  },
  "status_meanings": {
    "trained_baseline": "Trained in this project on a documented dataset, with measured metrics.",
    "pretrained": "A third-party pretrained model used as is.",
    "heuristic": "A rule-based or signal-processing check, not a learned classifier.",
    "experimental": "Runs but has not been validated.",
    "unavailable": "Part of the design but cannot run in this installation.",
    "planned": "Not implemented yet."
  }
}
```

## Downloads

| Route | Returns |
|---|---|
| `GET /analysis/{id}/report.pdf` | A PDF report of the analysis, including its limitations text |
| `GET /analysis/{id}/heatmap` | The Error Level Analysis map as PNG (owner only) |
| `GET /analysis/{id}/image` | The image the owner uploaded (owner only, images and multimodal) |
| `GET /analysis/{id}/video` | The video the owner uploaded, with byte-range support so a player can seek (owner only) |
| `GET /analysis/{id}/frames/{index}` | One sampled frame of an analysed video, with the scored face boxed, as JPEG (owner only) |
| `GET /models/{text,text-ur,evidence,video}/evaluation` | The saved evaluation of that model, as measured by its training or evaluation script (administrators only) |
| `GET /users/me/avatar` | The profile picture (owner only) |

