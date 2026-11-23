# Inference

The inference code is part of the backend so that the API loads each model once and applies the same rules every time:

| Module | Code | Status |
|---|---|---|
| Text | `backend/app/ml/text_detection/` (`preprocess.py`, `service.py`) | trained baseline |
| Image | `backend/app/ml/image_detection/ela.py` | heuristic indicators |
| Video | `backend/app/ml/video_detection/` | planned, no code yet |
| Multimodal | `backend/app/ml/multimodal/` | planned, no code yet |
| Evidence | `backend/app/ml/fact_checking/` | planned, no code yet |
| Explainability | `backend/app/ml/explainability/` | the text explanation is produced inside `text_detection/service.py` |

Trained files live in `ai_models/checkpoints/` (not committed) and their registry entries in `ai_models/model_registry/`.
