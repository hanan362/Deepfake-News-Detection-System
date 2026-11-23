# Entity-relationship diagram

Generated from the SQLAlchemy models, so it matches the migrations (a test compares models and migrations). Rendered by any Mermaid viewer, including GitHub and VS Code.

```mermaid
erDiagram
    analysis_results {
        integer id PK
        integer user_id FK
        integer submission_id FK
        string_20 analysis_type
        string_60 verdict
        float confidence
        string_20 status
        integer model_version_id FK
        json details
        text limitations
        boolean is_demo
        datetime created_at
    }
    audit_logs {
        integer id PK
        integer user_id FK
        string_60 action
        string_40 entity
        string_40 entity_id
        string_64 ip_address
        json detail
        datetime created_at
    }
    claims {
        integer id PK
        integer analysis_id FK
        text claim_text
        string_60 verdict
    }
    dataset_versions {
        integer id PK
        string_120 name
        string_60 version
        string_255 source
        string_20 language
        integer num_samples
        json label_distribution
        text notes
        datetime created_at
    }
    evidence_sources {
        integer id PK
        integer claim_id FK
        string_1000 url
        string_500 title
        datetime published_at
        string_20 stance
        float relevance
    }
    image_predictions {
        integer id PK
        integer analysis_id FK,UK
        integer width
        integer height
        string_10 image_format
        float ela_mean
        float ela_max
        float ela_block_cv
        string_255 heatmap_filename
        json metadata_summary
    }
    model_versions {
        integer id PK
        string_40 module
        string_120 name
        string_60 version
        string_30 status
        string_255 artifact_path
        json metrics
        integer dataset_version_id FK
        boolean is_active
        datetime created_at
    }
    news_submissions {
        integer id PK
        integer user_id FK
        string_20 submission_type
        string_500 headline
        text content
        string_64 content_sha256
        string_255 media_filename
        string_255 original_filename
        string_1000 source_url
        datetime created_at
    }
    password_reset_tokens {
        integer id PK
        integer user_id FK
        string_64 token_hash UK
        datetime expires_at
        datetime used_at
        datetime created_at
    }
    revoked_tokens {
        string_64 jti PK
        datetime expires_at
    }
    roles {
        string_20 name PK
        string_255 description
    }
    system_settings {
        string_80 key PK
        text value
        datetime updated_at
    }
    text_predictions {
        integer id PK
        integer analysis_id FK,UK
        float prob_fake
        float prob_real
        integer token_count
        string_20 language
        json top_features
    }
    user_feedback {
        integer id PK
        integer user_id FK
        integer analysis_id FK
        string_30 category
        text message
        string_20 status
        integer reviewed_by FK
        datetime reviewed_at
        datetime created_at
    }
    users {
        integer id PK
        string_255 email UK
        string_50 username UK
        string_120 full_name
        string_255 hashed_password
        string_20 role FK
        boolean is_active
        string_255 avatar_path
        datetime created_at
        datetime last_login_at
        datetime password_changed_at
    }
    users ||--o{ analysis_results : "user_id"
    news_submissions ||--o{ analysis_results : "submission_id"
    model_versions |o--o{ analysis_results : "model_version_id"
    users |o--o{ audit_logs : "user_id"
    analysis_results ||--o{ claims : "analysis_id"
    claims ||--o{ evidence_sources : "claim_id"
    analysis_results ||--o| image_predictions : "analysis_id"
    dataset_versions |o--o{ model_versions : "dataset_version_id"
    users ||--o{ news_submissions : "user_id"
    users ||--o{ password_reset_tokens : "user_id"
    analysis_results ||--o| text_predictions : "analysis_id"
    users ||--o{ user_feedback : "user_id"
    analysis_results |o--o{ user_feedback : "analysis_id"
    users |o--o{ user_feedback : "reviewed_by"
    roles ||--o{ users : "role"
```

Reading the diagram: the parent side is `||` (exactly one) when the foreign key is required and `|o` (zero or one) when it can be empty. The child side is `o{` (zero or more) or `o|` (zero or one, used for the one-to-one prediction rows).

