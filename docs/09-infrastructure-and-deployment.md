# Infrastructure & Deployment

Shows how all services are wired together in both development and production modes.

## Development setup

```mermaid
flowchart TD
    subgraph Host["Developer machine"]
        MAKE[make dev / make start]

        subgraph Docker["Docker Compose"]
            PG[(PostgreSQL\nport 5432)]
        end

        subgraph Processes["Local processes"]
            BE[FastAPI backend\nuvicorn · port 8000]
            FE[Vite dev server\nport 5173]
        end
    end

    BROWSER([Browser]) -->|http://localhost:5173| FE
    FE -->|proxy /api → port 8000| BE
    BE -->|psycopg| PG
    BE -->|HTTPS| GROQ[Groq API]
    BE -.->|optional| OLLAMA[Ollama\nlocalhost:11434]
```

## Production / Docker Compose setup

```mermaid
flowchart TD
    BROWSER([Browser]) -->|port 80| NGINX[nginx\nreverse proxy]

    subgraph Docker["Docker Compose"]
        NGINX -->|/api/*| BE[FastAPI backend\ncontainer · port 8000]
        NGINX -->|/*| FE[Frontend\nstatic files · nginx · port 80]
        BE -->|psycopg| PG[(PostgreSQL\ncontainer · port 5432)]
    end

    BE -->|HTTPS| GROQ[Groq API]
    BE -.->|optional| OLLAMA[Ollama\nhost-installed]
```

## Service dependency order

```mermaid
flowchart LR
    PG[(PostgreSQL)] -->|healthy| BE[Backend]
    BE -->|schema auto-applied| READY[API ready]
    FE[Frontend] -->|independent build| NGINX[nginx]
    READY --> NGINX
```

## Configuration layers

```mermaid
flowchart TD
    YAML[config/default.yml\nbase config] --> CFG[pydantic-settings\nconfig loader]
    ENV[Environment variables\nDOCASSIST_*] --> CFG
    CFG --> APP[Application\nservices.py singleton]

    APP --> LLM[LLM factory]
    APP --> DB[PostgreSQL pool]
    APP --> ENC[EncryptionService]
    APP --> JWT[JWT handler]
```

## Key ports

| Service | Port | Protocol |
|---------|------|----------|
| PostgreSQL | 5432 | TCP |
| FastAPI backend | 8000 | HTTP |
| Vite dev server | 5173 | HTTP |
| nginx (prod) | 80 | HTTP |
| Ollama (optional) | 11434 | HTTP |

## Schema migrations

```mermaid
flowchart LR
    START[Backend startup] --> POOL[PostgresPool init]
    POOL --> SCHEMA[apply schema.sql\nidempotent CREATE IF NOT EXISTS]
    SCHEMA --> MIGS[run migrations/\nin order — idempotent SQL]
    MIGS --> READY[DB ready]
```
