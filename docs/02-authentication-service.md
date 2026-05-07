# Authentication Service

Handles user registration, login, JWT issuance, and plan assignment. All knowledge tree endpoints require a valid Bearer token.

```mermaid
sequenceDiagram
    actor User
    participant FE as React Frontend
    participant API as FastAPI /auth
    participant DB as PostgreSQL

    %% Registration
    User->>FE: fill register form
    FE->>API: POST /api/auth/register {email, password, display_name}
    API->>API: bcrypt hash password
    API->>DB: INSERT users + assign free plan (user_subscriptions)
    DB-->>API: new user row
    API->>API: sign JWT (7-day expiry)
    API-->>FE: {access_token, expires_in_days}
    FE->>FE: store token in localStorage

    %% Login
    User->>FE: fill login form
    FE->>API: POST /api/auth/login {email, password}
    API->>DB: SELECT user by email
    DB-->>API: user row (password_hash)
    API->>API: bcrypt verify password
    API->>API: sign JWT
    API-->>FE: {access_token, expires_in_days}

    %% Authenticated request
    User->>FE: navigate to protected page
    FE->>API: GET /api/knowledge-trees (Authorization: Bearer <token>)
    API->>API: validate JWT → extract user_id
    API->>DB: SELECT trees WHERE user_id = ?
    DB-->>API: rows
    API-->>FE: trees list
```

## Data model

```mermaid
erDiagram
    users {
        UUID id PK
        string email UK
        string password_hash
        string display_name
        bool is_active
        timestamp created_at
        timestamp updated_at
    }
    subscription_plans {
        UUID id PK
        string slug UK
        string name
        int max_documents
        int max_knowledge_trees
    }
    user_subscriptions {
        UUID id PK
        UUID user_id FK
        UUID plan_id FK
        timestamp assigned_at
    }

    users ||--o| user_subscriptions : has
    subscription_plans ||--o{ user_subscriptions : grants
```

## Plan limit enforcement

```mermaid
flowchart LR
    REQ[Incoming write request] --> CHECK{limit_checks.py}
    CHECK -->|within limits| HANDLER[Router handler]
    CHECK -->|exceeded| ERR[403 PlanLimitExceeded]
    HANDLER --> DB[(PostgreSQL)]
```
