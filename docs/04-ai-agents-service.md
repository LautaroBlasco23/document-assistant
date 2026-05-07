# AI Agents Service

Four specialized agents power the AI features. All share a common base class with JSON-retry logic and accept `GenerationParams` for per-request tuning.

```mermaid
flowchart TD
    subgraph Agents["Application — agents/"]
        BASE[BaseAgent\nJSON retry · GenerationParams]
        FC[FlashcardGeneratorAgent]
        QG[QuestionGeneratorAgent]
        TI[TextImprovementAgent]
        DC[DocumentChatAgent]
    end

    subgraph LLM["infrastructure/llm/"]
        FACTORY[LLM factory]
        GROQ[GroqLLM\nrate limiter]
        OLLAMA[OllamaLLM]
        OR[OpenRouterLLM]
        HF[HuggingFaceLLM]
    end

    BASE --> FC & QG & TI & DC
    FC & QG & TI --> FACTORY
    DC --> FACTORY
    FACTORY --> GROQ & OLLAMA & OR & HF
```

---

## 1 — Flashcard Generator

```mermaid
sequenceDiagram
    participant API
    participant Agent as FlashcardGeneratorAgent
    participant LLM
    participant DB as PostgreSQL

    API->>Agent: generate(chunks, tree_id, chapter_id, params)

    loop batches of ≤3000 words
        Agent->>LLM: prompt → JSON array of {front, back, source_text}
        LLM-->>Agent: raw JSON
        Agent->>Agent: _call_json_with_retry (1 correction if malformed)
        Agent->>Agent: _filter_low_quality\n(short cards, trivial patterns,\nJaccard >0.8 near-duplicates)
    end

    Agent->>DB: INSERT flashcards (bulk)
    Agent-->>API: list[Flashcard]
```

**Quality filter steps:**
1. Remove cards with front or back shorter than threshold
2. Remove pattern-matched trivial questions ("What is …?" with one-word answers)
3. Remove cards where front overlaps back (Jaccard similarity > 0.8)
4. Remove near-duplicate pairs within the batch

---

## 2 — Question Generator

```mermaid
sequenceDiagram
    participant API
    participant Agent as QuestionGeneratorAgent
    participant LLM
    participant DB as PostgreSQL

    API->>Agent: generate(chunks, tree_id, chapter_id, params)

    loop batches of ≤2500 words
        Agent->>LLM: prompt → JSON array of typed questions
        LLM-->>Agent: raw JSON
        Agent->>Agent: per-type schema validation
        note right of Agent: true_false · multiple_choice\nmatching · checkbox\ninvalid questions silently discarded
    end

    Agent->>DB: INSERT knowledge_tree_questions (JSONB)
    Agent-->>API: list[Question]
```

**Supported question types:**

| Type | Structure |
|------|-----------|
| `true_false` | statement + correct boolean |
| `multiple_choice` | question + options[] + correct_index |
| `matching` | pairs[] of {left, right} |
| `checkbox` | question + options[] + correct_indices[] |

---

## 3 — Text Improvement Agent

```mermaid
sequenceDiagram
    actor User
    participant API as PUT /improve
    participant Agent as TextImprovementAgent
    participant LLM
    participant DB as PostgreSQL

    User->>API: improve document
    API->>DB: fetch document.content
    API->>Agent: improve(content, params)
    Agent->>LLM: rewrite prompt (clarity + Markdown formatting)
    LLM-->>Agent: improved text
    Agent-->>API: improved_content
    API->>DB: UPDATE document\n  content = improved\n  original_content = old (if null)
    API-->>User: updated document

    User->>API: revert document
    API->>DB: content = original_content\n  original_content = NULL
    API-->>User: reverted document
```

---

## 4 — Document Chat Agent

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend
    participant API as POST /api/chat
    participant Agent as DocumentChatAgent
    participant LLM

    User->>FE: select text in reader
    FE->>FE: extract PDF/EPUB text client-side\n(extractPdfText util)
    User->>FE: "Ask definition in chat"
    FE->>API: POST /api/chat {message, context: extracted_text}
    API->>Agent: chat(message, context, history, params)
    Agent->>LLM: system prompt (ground in context) + history + message
    LLM-->>Agent: grounded answer
    Agent-->>API: reply
    API-->>FE: {reply}
    FE->>FE: render with react-markdown
```

---

## LLM provider selection & rate limiting

```mermaid
flowchart LR
    ENV[DOCASSIST_LLM_PROVIDER\nenv var] --> FACTORY[LLM factory]
    FACTORY -->|groq| GROQ[GroqLLM]
    FACTORY -->|ollama| OLLAMA[OllamaLLM]
    FACTORY -->|openrouter| OR[OpenRouterLLM]
    FACTORY -->|huggingface| HF[HuggingFaceLLM]

    GROQ --> RL[GroqRateLimiter\nsliding window\n25 req / 30 s]
    RL -->|within limit| GREQ[Groq API call]
    RL -->|approaching limit| SLEEP[proactive sleep]
    GREQ -->|429 received| RETRY[exponential backoff retry]

    FACTORY2[create_fast_llm] -->|bulk tasks| FAST[smaller/faster model]
```

| Provider | Main model | Fast model |
|----------|-----------|-----------|
| groq | llama-3.3-70b-versatile | llama-3.1-8b-instant |
| ollama | qwen2.5:14b-instruct | qwen2.5:3b-instruct |
| openrouter | meta-llama/llama-3.3-70b-instruct:free | qwen/qwen2.5-7b-instruct:free |
| huggingface | Qwen/Qwen2.5-72B-Instruct | — |
