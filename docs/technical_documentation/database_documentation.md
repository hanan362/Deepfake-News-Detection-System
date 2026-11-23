# Database documentation

The default database is SQLite (a file at `storage/app.db`), which needs no setup. PostgreSQL 16 is supported for production through `DATABASE_URL=postgresql+psycopg://...`. The schema is defined in `backend/app/models/entities.py` and created by Alembic migrations in `backend/alembic/versions/`.

## Design rules

- Integer primary keys, explicit foreign keys and indexes on the columns used to look rows up.
- `ON DELETE CASCADE` from users to everything they own, so deleting an account removes its data. Audit-log and feedback-review references use `SET NULL` so the history survives.
- All timestamps are stored and returned in UTC. A column type converts values read back from SQLite to timezone-aware UTC.
- Analyses are split into a general row (`analysis_results`) and a one-to-one detail row per module (`text_predictions`, `image_predictions`), so each module keeps its own typed numbers without a sparse wide table.
- A user's media is private: files are stored under random names outside the web root, and routes return them only to the owner.
- No demo rows are created. A new database is empty except for an optional first administrator.

## Tables

See `docs/diagrams/er_diagram.md` for the diagram. Columns are listed below; `PK` primary key, `FK` foreign key, `UK` unique.

### `analysis_results`

One row per analysis: type, verdict, confidence (null when there is none), details, limitations text and the model version used. `is_demo` exists for a future demo mode and is always false in this build.

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | integer | no | PK |
| `user_id` | integer | no | FK to `users.id`, on delete cascade; indexed |
| `submission_id` | integer | no | FK to `news_submissions.id`, on delete cascade |
| `analysis_type` | string(20) | no | indexed |
| `verdict` | string(60) | no | indexed |
| `confidence` | float | yes |  |
| `status` | string(20) | no |  |
| `model_version_id` | integer | yes | FK to `model_versions.id`, on delete set null |
| `details` | json | yes |  |
| `limitations` | text | yes |  |
| `is_demo` | boolean | no |  |
| `created_at` | datetime | no | indexed |

Composite index `ix_analysis_user_created`: user_id, created_at.

### `audit_logs`

Security-relevant events (sign-ins, role changes, deletions) with address and details.

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | integer | no | PK |
| `user_id` | integer | yes | FK to `users.id`, on delete set null; indexed |
| `action` | string(60) | no | indexed |
| `entity` | string(40) | yes |  |
| `entity_id` | string(40) | yes |  |
| `ip_address` | string(64) | yes |  |
| `detail` | json | yes |  |
| `created_at` | datetime | no | indexed |

### `claims`

Claims extracted from a submission by the evidence module, one row per claim, with the verdict the rule gave it. Deleted with the analysis.

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | integer | no | PK |
| `analysis_id` | integer | no | FK to `analysis_results.id`, on delete cascade; indexed |
| `claim_text` | text | no |  |
| `verdict` | string(60) | yes |  |

### `dataset_versions`

Datasets the models were trained or evaluated on (name, version, source, size, label distribution).

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | integer | no | PK |
| `name` | string(120) | no |  |
| `version` | string(60) | no |  |
| `source` | string(255) | yes |  |
| `language` | string(20) | yes |  |
| `num_samples` | integer | yes |  |
| `label_distribution` | json | yes |  |
| `notes` | text | yes |  |
| `created_at` | datetime | no |  |

Unique together: name, version.

### `evidence_sources`

Sources returned for a claim by the evidence module: address, title, publication date when the source gives one, the stance of the passage and its relevance score. Deleted with the claim.

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | integer | no | PK |
| `claim_id` | integer | no | FK to `claims.id`, on delete cascade; indexed |
| `url` | string(1000) | no |  |
| `title` | string(500) | yes |  |
| `published_at` | datetime | yes |  |
| `stance` | string(20) | yes |  |
| `relevance` | float | yes |  |

### `image_predictions`

Image-specific measurements for an analysis: size, format, ELA statistics, heatmap file name, metadata summary.

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | integer | no | PK |
| `analysis_id` | integer | no | FK to `analysis_results.id`, on delete cascade; UK |
| `width` | integer | no |  |
| `height` | integer | no |  |
| `image_format` | string(10) | no |  |
| `ela_mean` | float | yes |  |
| `ela_max` | float | yes |  |
| `ela_block_cv` | float | yes |  |
| `heatmap_filename` | string(255) | yes |  |
| `metadata_summary` | json | yes |  |

### `model_versions`

Versions of each analysis module's model, with status and measured metrics. Each analysis points at the version that produced it.

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | integer | no | PK |
| `module` | string(40) | no | indexed |
| `name` | string(120) | no |  |
| `version` | string(60) | no |  |
| `status` | string(30) | no |  |
| `artifact_path` | string(255) | yes |  |
| `metrics` | json | yes |  |
| `dataset_version_id` | integer | yes | FK to `dataset_versions.id`, on delete set null |
| `is_active` | boolean | no |  |
| `created_at` | datetime | no |  |

Unique together: module, name, version.

### `news_submissions`

What a user submitted: text or an uploaded file (stored under a random name) plus a content hash.

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | integer | no | PK |
| `user_id` | integer | no | FK to `users.id`, on delete cascade; indexed |
| `submission_type` | string(20) | no |  |
| `headline` | string(500) | yes |  |
| `content` | text | yes |  |
| `content_sha256` | string(64) | yes | indexed |
| `media_filename` | string(255) | yes |  |
| `original_filename` | string(255) | yes |  |
| `source_url` | string(1000) | yes |  |
| `created_at` | datetime | no |  |

### `password_reset_tokens`

One row per reset request. Only the SHA-256 of the token is stored, never the token. A token works once and expires.

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | integer | no | PK |
| `user_id` | integer | no | FK to `users.id`, on delete cascade; indexed |
| `token_hash` | string(64) | no | UK |
| `expires_at` | datetime | no |  |
| `used_at` | datetime | yes |  |
| `created_at` | datetime | no |  |

### `revoked_tokens`

Session tokens ended by logout, kept until they would have expired anyway.

| Column | Type | Null | Notes |
|---|---|---|---|
| `jti` | string(64) | no | PK |
| `expires_at` | datetime | no | indexed |

### `roles`

The allowed roles (`user`, `admin`). `users.role` references it, so an account cannot hold a role that does not exist. Rows are created by migration 0002 and checked at every start.

| Column | Type | Null | Notes |
|---|---|---|---|
| `name` | string(20) | no | PK |
| `description` | string(255) | no |  |

### `system_settings`

Key-value settings.

| Column | Type | Null | Notes |
|---|---|---|---|
| `key` | string(80) | no | PK |
| `value` | text | no |  |
| `updated_at` | datetime | no |  |

### `text_predictions`

Text-specific numbers for an analysis: probabilities, word count, language hint, top terms.

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | integer | no | PK |
| `analysis_id` | integer | no | FK to `analysis_results.id`, on delete cascade; UK |
| `prob_fake` | float | no |  |
| `prob_real` | float | no |  |
| `token_count` | integer | no |  |
| `language` | string(20) | yes |  |
| `top_features` | json | yes |  |

### `user_feedback`

Feedback and bug reports from users, with review status.

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | integer | no | PK |
| `user_id` | integer | no | FK to `users.id`, on delete cascade; indexed |
| `analysis_id` | integer | yes | FK to `analysis_results.id`, on delete set null |
| `category` | string(30) | no |  |
| `message` | text | no |  |
| `status` | string(20) | no | indexed |
| `reviewed_by` | integer | yes | FK to `users.id`, on delete set null |
| `reviewed_at` | datetime | yes |  |
| `created_at` | datetime | no |  |

### `users`

Accounts. Passwords are stored only as bcrypt hashes. `role` is a reference to `roles.name`.

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | integer | no | PK |
| `email` | string(255) | no | UK |
| `username` | string(50) | no | UK |
| `full_name` | string(120) | yes |  |
| `hashed_password` | string(255) | no |  |
| `role` | string(20) | no | FK to `roles.name`; indexed |
| `is_active` | boolean | no |  |
| `avatar_path` | string(255) | yes |  |
| `created_at` | datetime | no |  |
| `last_login_at` | datetime | yes |  |
| `password_changed_at` | datetime | yes |  |

## Migrations

```bash
cd backend
python -m app.db.migrate   # create or update the schema (what the scripts and Docker run)
alembic upgrade head      # the same, without the adoption step described below
alembic current           # show the version
alembic downgrade base    # remove everything (development only)
```

The migration test (`backend/tests/test_migrations.py`) builds a database from the migrations, compares it with the models and fails if they differ, so a model change cannot ship without a migration. With SQLite the app creates missing tables on start (`AUTO_CREATE_TABLES=true`). With PostgreSQL or Docker set `AUTO_CREATE_TABLES=false` and let the migrations create the schema.

`python -m app.db.migrate` wraps `alembic upgrade head`. A database that has tables but no `alembic_version` record (for example one that `AUTO_CREATE_TABLES` created) would make a plain upgrade fail with "table already exists". The helper compares such a database with the models. If they match exactly it records the latest revision and keeps all rows. If they differ it changes nothing, prints the first difference and exits with an error. Three tests in `test_migrations.py` cover the adopt, refuse and empty-database cases on SQLite.

## Verification status

- SQLite: used by every test. Migrations are tested up, down and for drift.
- PostgreSQL: the migrations and the whole back-end test suite (269 tests) were run against a real PostgreSQL 16 server, an embedded build in the development container. The Docker Compose PostgreSQL 16 service ran the migrations at start in a sandbox run, but the test suite was not run against it, and the adoption helper was not run against PostgreSQL. Run `python -m app.db.migrate` against your own server before relying on it.

## Backup and reset

SQLite: stop the app and copy `storage/app.db` (and `storage/uploads/`, `storage/reports/`). To reset, delete `storage/app.db` and start again. PostgreSQL: use `pg_dump`.
