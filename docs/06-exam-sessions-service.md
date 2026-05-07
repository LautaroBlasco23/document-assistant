# Exam Sessions Service

Tracks quiz results per chapter. Users generate questions, take an exam in the browser, and the results are persisted for progress tracking.

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend
    participant API as FastAPI
    participant DB as PostgreSQL

    %% Question generation (prerequisite)
    User->>FE: "Generate Questions" for chapter N
    FE->>API: POST /api/knowledge-trees/{id}/chapters/{n}/questions
    API-->>FE: {task_id}
    FE->>FE: poll until done

    %% Taking the exam
    User->>FE: "Start Exam"
    FE->>API: GET /api/knowledge-trees/{id}/chapters/{n}/questions
    API->>DB: SELECT knowledge_tree_questions WHERE chapter_id = ?
    DB-->>API: questions (JSONB)
    API-->>FE: questions list
    FE->>FE: render quiz UI\n(true/false · MCQ · matching · checkbox)

    User->>FE: answer each question
    FE->>FE: evaluate locally → compute score

    User->>FE: submit exam
    FE->>API: POST /api/knowledge-trees/{id}/chapters/{n}/exam-sessions\n{score, total_questions, correct_count,\n question_ids[], results{}}
    API->>DB: INSERT exam_sessions
    DB-->>API: session row
    API-->>FE: {session_id, score, ...}

    %% Reviewing history
    User->>FE: view past sessions
    FE->>API: GET /api/knowledge-trees/{id}/chapters/{n}/exam-sessions
    API->>DB: SELECT exam_sessions ORDER BY created_at DESC
    DB-->>API: sessions list
    API-->>FE: sessions
```

## Question types rendered in the exam UI

```mermaid
flowchart LR
    Q[Question from DB]
    Q -->|question_type| TF[true_false\nTwo buttons: True / False]
    Q --> MC[multiple_choice\nRadio list]
    Q --> MT[matching\nDrag-and-drop pairs]
    Q --> CB[checkbox\nMulti-select list]
```

## Data model

```mermaid
erDiagram
    knowledge_tree_questions {
        UUID id PK
        UUID tree_id FK
        UUID chapter_id FK
        string question_type "true_false|multiple_choice|matching|checkbox"
        jsonb question_data
        timestamp created_at
    }
    exam_sessions {
        UUID id PK
        UUID tree_id FK
        UUID chapter_id FK
        float score "0–100"
        int total_questions
        int correct_count
        jsonb question_ids
        jsonb results "per-question detail"
        timestamp created_at
    }

    knowledge_tree_questions }o--|| exam_sessions : referenced_in
```

## Score calculation

Score is computed client-side before submission:

```
score = (correct_count / total_questions) × 100
```

Per-question results are stored as a JSONB map `{question_id: {correct: bool, user_answer: …}}` for future review.
