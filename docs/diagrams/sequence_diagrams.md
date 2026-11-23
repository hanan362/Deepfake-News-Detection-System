# Sequence diagrams

## 1. Log in and open a protected page

```mermaid
sequenceDiagram
    actor User
    participant UI as React app
    participant API as FastAPI
    participant DB as Database

    User->>UI: Enter e-mail or username and password
    UI->>API: POST /api/v1/auth/login
    API->>DB: Find account by e-mail or username
    API->>API: Check bcrypt hash (a dummy hash is checked when the account is unknown)
    alt wrong credentials or disabled account
        API-->>UI: 401 or 403 error envelope
        UI-->>User: Show message
    else correct
        API->>DB: Save last login time, write audit entry
        API-->>UI: Token (60 min), expiry, user
        UI->>UI: Keep the token for the session
        UI->>API: GET /api/v1/users/me with Bearer token
        API->>DB: Is the token revoked? Is the account active? Was the password changed since?
        API-->>UI: User
        UI-->>User: Show the dashboard
    end
```

## 2. Analyse text

```mermaid
sequenceDiagram
    actor User
    participant UI as React app
    participant API as FastAPI
    participant ML as Text detector
    participant DB as Database

    User->>UI: Paste article, press Analyse
    UI->>API: POST /api/v1/analysis/text (Bearer token)
    API->>API: Authenticate, rate limit, validate length
    API->>ML: analyse(headline, text)
    ML->>ML: Language and length checks
    alt unsupported or too short
        ML-->>API: Unverified with reason
    else scoreable
        ML->>ML: Clean, TF-IDF, predict probabilities
        ML->>ML: Apply 0.80 threshold, compute term contributions
        ML-->>API: Verdict, probabilities, explanation
    end
    API->>DB: Insert submission, analysis result, text prediction
    API-->>UI: 201 with the full result and limitations
    UI-->>User: Verdict, probabilities, highlighted terms, limitations
```

## 3. Analyse an image

```mermaid
sequenceDiagram
    actor User
    participant UI as React app
    participant API as FastAPI
    participant ELA as Image forensics
    participant FS as File storage
    participant DB as Database

    User->>UI: Choose an image
    UI->>UI: Check type and size
    UI->>API: POST /api/v1/analysis/image (multipart)
    API->>ELA: analyse(bytes, pixel limit)
    ELA->>ELA: Decode by content, reject if unsafe or unsupported
    ELA->>ELA: Recompress at quality 90, measure error, read metadata
    ELA-->>API: Measurements, observations, heatmap
    API->>FS: Save image and heatmap under random names
    API->>DB: Insert submission, analysis result, image prediction
    API-->>UI: 201 Indicators Only with limitations
    UI->>API: GET /analysis/{id}/heatmap and /image (Bearer token)
    API->>API: Check that the analysis belongs to this user
    API-->>UI: PNG and original image
    UI-->>User: Measurements, map, observations, limitations
```

## 4. Download a PDF report

```mermaid
sequenceDiagram
    actor User
    participant UI as React app
    participant API as FastAPI
    participant DB as Database

    User->>UI: Press Download report
    UI->>API: GET /api/v1/analysis/{id}/report.pdf
    API->>DB: Load analysis, only if it belongs to the user
    alt not found or someone else's
        API-->>UI: 404
    else owner
        API->>API: Build PDF (text is escaped, non-Latin text is handled)
        API-->>UI: application/pdf
        UI-->>User: File saved
    end
```

## 5. Reset a password

```mermaid
sequenceDiagram
    actor User
    participant UI as React app
    participant API as FastAPI
    participant DB as Database

    User->>UI: Enter e-mail on Forgot password
    UI->>API: POST /auth/forgot-password
    API->>DB: Look up the account
    API->>DB: Store SHA-256 of a new random token with an expiry
    API-->>UI: Same message for any e-mail (token included only when EXPOSE_RESET_TOKEN=true)
    User->>UI: Enter token and a new password
    UI->>API: POST /auth/reset-password
    API->>DB: Token known, unused, unexpired?
    API->>DB: Update password hash, mark token used
    API-->>UI: Message
    Note over API,DB: Tokens issued before the change stop working
```

## 6. Administrator changes a role

```mermaid
sequenceDiagram
    actor Admin
    participant UI as React app
    participant API as FastAPI
    participant DB as Database

    Admin->>UI: Choose a user and a new role
    UI->>API: PATCH /api/v1/admin/users/{id}
    API->>API: Is the caller an administrator?
    API->>API: Is the target the caller with a demotion or disable?
    alt self lockout
        API-->>UI: 400 SELF_LOCKOUT
    else allowed
        API->>DB: Update role (must exist in roles)
        API->>DB: Insert audit log entry
        API-->>UI: Updated user
    end
```
