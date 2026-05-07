# Task System (Background Processing)

Long-running operations (file import, flashcard generation, question generation) run as background tasks. The frontend polls for status rather than using SSE or WebSockets.

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend
    participant API as FastAPI router
    participant TASKS as tasks.py\n(in-memory registry)
    participant POOL as ThreadPoolExecutor\n(max 2 workers)
    participant DB as PostgreSQL

    User->>FE: trigger long operation\n(import / generate)
    FE->>API: POST request
    API->>TASKS: create Task object (pending)
    API->>DB: INSERT tasks row
    API->>POOL: submit(worker_fn, task)
    API-->>FE: {task_id}

    loop poll every ~2 seconds
        FE->>API: GET /api/tasks/{task_id}
        API->>DB: SELECT tasks WHERE id = task_id
        DB-->>API: {status, progress_pct, progress}
        API-->>FE: task status
        FE->>FE: update progress bar
    end

    POOL->>POOL: worker runs
    POOL->>TASKS: task.progress = "step message"
    POOL->>TASKS: task.progress_pct = 0..100
    POOL->>DB: UPDATE tasks (progress, pct)
    POOL->>DB: write results (documents / flashcards / questions)
    POOL->>DB: UPDATE tasks SET status = 'done' | 'error'

    FE->>FE: detect status == done → refresh data
```

## Task states

```mermaid
stateDiagram-v2
    [*] --> pending : task created
    pending --> running : worker picks up
    running --> done : success
    running --> error : exception
    done --> [*]
    error --> [*]
```

## Task types

| Task type | Trigger endpoint | Worker action |
|-----------|-----------------|---------------|
| `document_import` | POST `/chapters/{n}/documents/import` | load → normalize → chunk → INSERT |
| `youtube_import` | POST `/documents/import-youtube` | fetch transcript → INSERT |
| `tree_import` | POST `/knowledge-trees/import` | full file → chapters + documents |
| `flashcard_generation` | POST `/chapters/{n}/flashcards` | chunk → batch LLM → filter → INSERT |
| `question_generation` | POST `/chapters/{n}/questions` | chunk → batch LLM → validate → INSERT |

## Data model

```mermaid
erDiagram
    tasks {
        string id PK
        string task_type
        string status "pending|running|done|error"
        int progress_pct
        string progress
        jsonb result
        string error
        timestamp created_at
        timestamp updated_at
    }
```
