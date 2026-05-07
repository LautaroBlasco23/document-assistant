# LLM Credentials Service

Users can supply their own API keys for external LLM providers. Keys are encrypted at rest — only the last 4 characters are stored in plaintext for display purposes.

```mermaid
sequenceDiagram
    actor User
    participant FE as Settings Page
    participant API as FastAPI /credentials
    participant ENC as EncryptionService
    participant DB as PostgreSQL
    participant LLM as LLM Provider

    %% Store a key
    User->>FE: enter API key for Groq
    FE->>API: POST /api/credentials {provider: "groq", api_key: "gsk_..."}
    API->>LLM: test key (quick validation call)
    LLM-->>API: ok / error
    API->>ENC: encrypt(api_key)
    ENC-->>API: encrypted bytes + last4
    API->>DB: INSERT user_llm_credentials\n{api_key_encrypted, api_key_last4,\n last_test_ok, last_tested_at}
    DB-->>API: credential row
    API-->>FE: {provider, api_key_last4, last_test_ok}
    FE->>FE: show "****<last4>" + status badge

    %% Use key at inference time
    API->>DB: SELECT credential WHERE user_id + provider
    DB-->>API: encrypted bytes
    API->>ENC: decrypt(bytes)
    ENC-->>API: plaintext key
    API->>LLM: inference call with user key
```

## Encryption flow

```mermaid
flowchart LR
    PLAIN[Plaintext API key] --> ENC[EncryptionService\nFernet symmetric encryption]
    ENC --> STORE[(BYTEA in PostgreSQL\napi_key_encrypted)]
    ENC --> LAST4[api_key_last4\nplaintext, display only]

    STORE --> DEC[EncryptionService.decrypt]
    DEC --> PLAIN2[Plaintext key\nused at inference time only]
```

## Data model

```mermaid
erDiagram
    user_llm_credentials {
        UUID id PK
        UUID user_id FK
        string provider "groq|ollama|openrouter|huggingface"
        bytea api_key_encrypted
        string api_key_last4
        timestamp last_tested_at
        bool last_test_ok
        string last_test_error "nullable"
        timestamp created_at
        timestamp updated_at
    }
    agents {
        UUID id PK
        UUID user_id FK
        string name UK
        text prompt
        string model
        string provider
        float temperature
        float top_p
        int max_tokens
        bool is_default
        timestamp created_at
        timestamp updated_at
    }

    user_llm_credentials }o--|| agents : used_by
```

## Agent management

Users can also create custom agents with specific system prompts and generation parameters. A default agent is used when no custom one is selected.

```mermaid
flowchart TD
    USER([User]) -->|create agent| FORM[Agent form\nname · prompt · model · params]
    FORM --> DB[(agents table)]
    DB -->|is_default = true| DEF[default agent\nused for all chats]
    DB -->|is_default = false| CUSTOM[selectable per chat]
```
