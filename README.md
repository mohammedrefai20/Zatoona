<div align="center">

<img src="Zatoona.png" width="170" alt="Zatoona logo" />

# Zatoona 🫒

**Agentic, notes-grounded exam generator & grader** — study smart, ace it with less.

*Turn your own study material into a fair, validated exam, take it, and get honest, encouraging feedback — every question grounded strictly in your notes.*

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?style=flat&logo=langchain&logoColor=white)
![MCP](https://img.shields.io/badge/MCP-FastMCP-6E56CF?style=flat&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-FF6B6B?style=flat&logoColor=white)
![Postgres](https://img.shields.io/badge/Postgres-4169E1?style=flat&logo=postgresql&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?style=flat&logo=react&logoColor=black)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=flat&logo=vite&logoColor=white)
![Tailwind](https://img.shields.io/badge/Tailwind-06B6D4?style=flat&logo=tailwindcss&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat)

[Overview](#-overview) · [Architecture](#-system-architecture) · [How it works](#-how-it-works) · [Quick start](#-quick-start) · [API](#-api-reference) · [Tech stack](#-technology-stack)

</div>

---

> [!NOTE]
> **Zatoona** is Arabic for *olive* — the briefest, smartest summary of a subject. The kind of revision that earns an A+ from a fraction of the effort. This project is that idea as software: study *smart*, not *hard*.

---

## 🎯 Overview

Zatoona is an end-to-end multi-agent system that transforms a student's raw study material into a personalized, validated exam — then grades the student's answers and returns structured, encouraging feedback.

A student uploads notes in almost any format. The material is parsed, chunked, embedded, and stored in a per-session vector database. A self-correcting LangGraph pipeline generates exam questions grounded **strictly** in those notes and validates each one. The student answers through a polished web UI, and a corrector agent grades each answer against the original source chunk — explaining mistakes and flagging topics to review.

The system is two cooperating codebases:

| Component | Stack | Role |
|-----------|-------|------|
| **`Leo-Agent/`** — backend | Python · FastAPI · LangChain/LangGraph · MCP · ChromaDB · Postgres | Ingestion, retrieval, exam generation, grading, auth, REST API behind an nginx gateway |
| **`zatoona-web/`** — frontend | React · Vite · TypeScript · Tailwind v4 · motion | The student-facing web app (landing, auth, upload, exam, results, history) |

---

## 🏗 System Architecture

Everything reaches the backend through a single **nginx gateway** on port 80. Auth is JWT; the main service orchestrates three layers, all of which read note chunks through one **MCP server** — no layer touches ChromaDB directly.

```mermaid
flowchart TD
    U([👩‍🎓 Student]):::pill --> FE[Zatoona Web<br/>React · Vite · Tailwind]:::fe
    FE -->|JWT · REST| GW[nginx API gateway · :80]:::io
    GW --> AUTH[Auth service<br/>FastAPI · JWT]:::io
    GW --> API[Main service<br/>FastAPI]:::io
    AUTH --> PG[(Postgres<br/>users · stored_exams)]:::db
    API --> PG

    API --> L2[Layer 2 · Exam creation<br/>LangGraph: generate ⇄ validate]:::dl
    API --> L3[Layer 3 · Grading & feedback<br/>corrector agent · Groq]:::dl

    subgraph L1 [Layer 1 · Ingestion & Retrieval]
        direction LR
        ING[Parse · chunk · embed]:::ml --> CH[(ChromaDB<br/>per-session)]:::db
        MCP{{MCP server<br/>get_relevant_chunks}}:::mcp
        CH --- MCP
    end

    API --> ING
    L2 -.->|chunks| MCP
    L3 -.->|chunks| MCP

    classDef pill fill:#efe7ec,stroke:#888,color:#3a1f37
    classDef fe fill:#efe2ee,stroke:#7c3aed,color:#3a1f37
    classDef io fill:#d1fae5,stroke:#059669,color:#064e3b
    classDef ml fill:#dbeafe,stroke:#3b82f6,color:#1e3a5f
    classDef dl fill:#ede9fe,stroke:#7c3aed,color:#3b0764
    classDef db fill:#fdf0d5,stroke:#d2a23f,color:#5a3e0a
    classDef mcp fill:#3a1f37,stroke:#3a1f37,color:#fff
```

### Frontend journey

```mermaid
flowchart LR
    LP[Landing] --> LG[Login / Sign up]:::fe --> D[Study desk<br/>upload notes]:::fe --> G[Generate exam]:::fe --> E[Take exam]:::fe --> R[Graded results]:::fe --> H[History]:::fe
    classDef fe fill:#efe2ee,stroke:#7c3aed,color:#3a1f37
```

---

## 🔬 How it works

<details open>
<summary><b>Layer 2 — Exam creation (self-correcting LangGraph loop)</b></summary>

<br/>

A LangGraph state machine fetches the relevant chunks, drafts questions, and validates each one against its source chunk. Rejected questions are regenerated with feedback (approved ones are kept by a programmatic merge), looping up to 3 times until every question is grounded.

```mermaid
flowchart TD
    S([POST /generate-exam]) --> FC[fetch_chunks<br/>via MCP per topic]:::io
    FC --> G[Generator agent<br/>Lightning AI · structured output]:::dl
    G --> V[Validator agent<br/>grounding check per question]:::dl
    V -->|all valid| E([✅ validated ExamObject]):::pill
    V -->|some rejected| G
    V -.->|max 3 iterations| E

    classDef pill fill:#efe7ec,stroke:#888,color:#3a1f37
    classDef io fill:#d1fae5,stroke:#059669,color:#064e3b
    classDef dl fill:#ede9fe,stroke:#7c3aed,color:#3b0764
```

</details>

<details>
<summary><b>Layer 3 — Grading & feedback</b></summary>

<br/>

The corrector agent grades each answer by re-fetching the question's source chunk, explains mistakes from the notes, and produces an encouraging report.

```mermaid
flowchart TD
    A([POST /submit-answer]) --> C[Corrector agent · Groq]:::dl
    C -->|per question| SRC[pull source chunk by id · MCP]:::io
    SRC --> GR[grade · explain · flag topic]:::dl
    GR --> R([Feedback report<br/>score · topics_to_review · per-question feedback · encouragement]):::pill

    classDef pill fill:#efe7ec,stroke:#888,color:#3a1f37
    classDef io fill:#d1fae5,stroke:#059669,color:#064e3b
    classDef dl fill:#ede9fe,stroke:#7c3aed,color:#3b0764
```

</details>

<details>
<summary><b>Layer 1 — Ingestion & hybrid retrieval</b></summary>

<br/>

Almost any source becomes a searchable, **session-isolated** vector store. Each `session_id` maps to its own ChromaDB collection, so users never see each other's material.

```mermaid
flowchart TD
    IN[PDF · DOCX · PPTX · image · audio/video · YouTube · text] --> P{source type}
    P -->|document| DOC[Docling parse<br/>OCR if scanned]
    P -->|audio/video| ASR[faster-whisper / Groq ASR]
    P -->|youtube| YT[captions → transcript]
    P -->|text/notion| TXT[direct]
    DOC --> CK[structure-aware chunking]
    ASR --> CK
    YT --> CK
    TXT --> CK
    CK --> EMB[embed · OpenAI / MiniLM auto-fallback]
    EMB --> CH[(ChromaDB · session-isolated)]
```

Retrieval is hybrid: dense vectors catch meaning, BM25 catches exact terms, RRF fuses them, and a cross-encoder reranks for precision.

```mermaid
flowchart LR
    Q[topic query] --> DENSE[dense vector search]
    Q --> BM[BM25 keyword search]
    DENSE --> RRF[RRF fusion]
    BM --> RRF
    RRF --> RR[cross-encoder rerank]
    RR --> TOPK[top-K NoteChunk\[\]]
```

</details>

---

## 🚀 Quick start

You need **Docker** (backend) and **Node 20+** (frontend).

### 1 · Backend

```bash
cd Leo-Agent
# create the three env files (see Configuration below), then:
docker compose up --build
curl http://localhost/health     # {"status":"UP", ...}
```

The gateway comes up on **http://localhost** (port 80). First run downloads embedding/reranker/OCR models, so give it a few minutes.

### 2 · Frontend

```bash
cd zatoona-web
npm install
npm run dev                      # http://localhost:5173
```

In dev, Vite proxies all API paths to the gateway server-side (no CORS, no preflight). Open **http://localhost:5173** and sign up.

<div align="center">
<br/>
<!-- Drop a screen recording at assets/demo.gif and it renders here -->
<img src="assets/demo.gif" width="720" alt="Zatoona demo" />
<br/><sub>📽️ add <code>assets/demo.gif</code> to show the flow: upload → generate → take → graded results</sub>
</div>

---

## 💻 Frontend (`zatoona-web`)

A polished SPA built around the brand's aubergine olive mascot.

- **Public landing** at `/`, app behind login at `/app` (study desk · exam · results · history).
- **Dark mode** (class-based, no-flash, remembered), **staged loaders** that show named phases during the multi-minute uploads/generation so the wait never looks frozen, and a mascot that reacts to each state.
- **Per-user isolation** of all study state (topics/exam/report are namespaced per account; nothing leaks across users on a shared browser).

See [`zatoona-web/README.md`](zatoona-web/README.md) for component structure and build details.

---

## 🛠 Technology Stack

| Layer | Technology |
|-------|-----------|
| Agent framework | ![LangChain](https://img.shields.io/badge/-LangChain-1C3C3C?logo=langchain&logoColor=white) |
| Orchestration | ![LangGraph](https://img.shields.io/badge/-LangGraph-1C3C3C?logo=langchain&logoColor=white) |
| Agent gateway | ![MCP](https://img.shields.io/badge/-MCP_·_FastMCP-6E56CF?logoColor=white) |
| API server | ![FastAPI](https://img.shields.io/badge/-FastAPI-009688?logo=fastapi&logoColor=white) ![nginx](https://img.shields.io/badge/-nginx-009639?logo=nginx&logoColor=white) |
| Vector store | ![ChromaDB](https://img.shields.io/badge/-ChromaDB-FF6B6B?logoColor=white) |
| Relational DB | ![Postgres](https://img.shields.io/badge/-Postgres-4169E1?logo=postgresql&logoColor=white) |
| Embeddings | ![OpenAI](https://img.shields.io/badge/-OpenAI-412991?logo=openai&logoColor=white) ![Sentence Transformers](https://img.shields.io/badge/-Sentence_Transformers-blue?logoColor=white) |
| Exam-gen LLM | ![Lightning AI](https://img.shields.io/badge/-Lightning_AI-792EE5?logoColor=white) |
| Grading LLM | ![Groq](https://img.shields.io/badge/-Groq-F55036?logoColor=white) |
| Doc parsing | ![Docling](https://img.shields.io/badge/-Docling-4B8BBE?logoColor=white) |
| Transcription | ![faster-whisper](https://img.shields.io/badge/-faster--whisper-FFB000?logoColor=white) |
| Validation | ![Pydantic](https://img.shields.io/badge/-Pydantic-E92063?logo=pydantic&logoColor=white) |
| Frontend | ![React](https://img.shields.io/badge/-React-61DAFB?logo=react&logoColor=black) ![Vite](https://img.shields.io/badge/-Vite-646CFF?logo=vite&logoColor=white) ![TypeScript](https://img.shields.io/badge/-TypeScript-3178C6?logo=typescript&logoColor=white) ![Tailwind](https://img.shields.io/badge/-Tailwind-06B6D4?logo=tailwindcss&logoColor=white) |
| Containerization | ![Docker](https://img.shields.io/badge/-Docker-2496ED?logo=docker&logoColor=white) |
| Tracing | ![LangSmith](https://img.shields.io/badge/-LangSmith-1C3C3C?logoColor=white) |

---

## 🔌 API Reference

Base URL **`http://localhost`**. Auth header: `Authorization: Bearer <access_token>`.

| Step | Method | Path | Auth | Body |
|------|--------|------|------|------|
| Sign up | `POST` | `/auth/signup` | — | form: `username`, `email`, `password` |
| Login | `POST` | `/auth/login` | — | form: `username`, `password` |
| Refresh | `POST` | `/auth/refresh` | — | JSON: `refresh_token` |
| Logout | `POST` | `/auth/logout` | ✅ | form: `refresh_token` (optional) |
| Health | `GET` | `/health` | — | — |
| Upload notes | `POST` | `/upload/` | ✅ | multipart: `topic` + one of `file` / `url` / `text` |
| Generate exam | `POST` | `/generate-exam/` | ✅ | JSON: `topics`, `num_questions`, `difficult` |
| Submit answers | `POST` | `/submit-answer/` | ✅ | JSON: `answers[]` |
| Exam history | `GET` | `/history/` | ✅ | — |
| Get exam | `GET` | `/get-exam/{exam_id}` | ✅ | — |

Full request/response shapes and Streamlit/JS examples live in [`api-doc.md`](api-doc.md).

### Core schemas

```python
class Question(BaseModel):
    question_id: str
    topic: str
    question: str
    correct_answer: str      # never exposed to the student
    source_chunk_id: str     # traceability to the note chunk

class ExamObject(BaseModel):
    session_id: str
    topics: list[str]
    status: Literal["draft", "validated"]
    questions: list[Question]

class FeedbackReport(BaseModel):
    session_id: str
    score: int
    topics_to_review: list[str]
    encouragement: str
    results: list[QuestionResult]   # per-question: is_correct, explanation, source_chunk
```

---

## ⚙️ Configuration

Three env files are read before the first `docker compose up`:

| File | Contains |
|------|----------|
| `Database/.env` | Postgres user / password / db |
| `Authentication/.env` | `SECRET_KEY`, token lifetimes |
| `.env` | `GROQ_API_KEY`, `LIGHTNING_API_KEY`, `OPENAI_API_KEY`, optional `LANGSMITH_*` for tracing |

Key knobs (see `config/settings.py` for the full list):

| Key | Default | Description |
|-----|---------|-------------|
| `EMBEDDING_PROVIDER` | `auto` | `openai` / `local` / `auto` |
| `RETRIEVAL_MODE` | `hybrid` | `hybrid` or `dense` |
| `RERANK_ENABLED` | `true` | cross-encoder reranking |
| `MAX_VALIDATION_ITERATIONS` | `3` | exam self-correction loops |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | grading model |
| `SESSION_RESET_ON_START` | `false` | clears the bound session's chunks on startup |

**Observability.** With `LANGSMITH_*` set, all generator/validator/corrector LLM calls are traced to LangSmith automatically.

---

## 📁 Project Structure

```
.
├── Leo-Agent/                  # backend (FastAPI · LangGraph · MCP · ChromaDB)
│   ├── app.py                  # main service: upload, generate-exam, submit-answer, history
│   ├── agents/                 # generator · validator · corrector
│   ├── graph/                  # LangGraph state machine (nodes · edges · state)
│   ├── mcp_server/             # MCP gateway + retrieval tools
│   ├── vector_db/              # ingestion · chunking · embeddings · hybrid retriever
│   ├── Authentication/         # JWT auth · SQLAlchemy models
│   ├── nginx/                  # API gateway config
│   └── docker-compose.yml
├── zatoona-web/                # frontend (React · Vite · Tailwind)
├── api-doc.md                  # REST contract + examples
└── Zatoona.png                 # the mascot
```

---

## ⚠️ Limitations & 🔭 Future Work

- **Questions are open-text today.** MCQ support is on the roadmap.
- **Topic naming is manual.** An agent that auto-titles uploaded material from its content is planned.
- **Web enrichment** exists in `vector_db/enrichment.py` but is not yet wired end-to-end.
- Exam generation is synchronous (no live progress stream); the frontend simulates staged progress.
- Retrieval quality is bounded by the quality of the uploaded material.

---

## 👥 Team


| Mazen Mohamed | Mahmoud Elgendy | Mohamed Emad | Mohamed Magdy | Mohamed Refai | Ziad Mahmoud |
|:---:|:---:|:---:|:---:|:---:|:---:|
| [![GitHub](https://img.shields.io/badge/-GitHub-181717?logo=github)](https://github.com/Mazen149) | [![GitHub](https://img.shields.io/badge/-GitHub-181717?logo=github)](https://github.com/rklorD456) | [![GitHub](https://img.shields.io/badge/-GitHub-181717?logo=github)](https://github.com/3omdawy11) | [![GitHub](https://img.shields.io/badge/-GitHub-181717?logo=github)](https://github.com/mohamedmagdy9977) | [![GitHub](https://img.shields.io/badge/-GitHub-181717?logo=github)](https://github.com/mohammedrefai20) | [![GitHub](https://img.shields.io/badge/-GitHub-181717?logo=github)](https://github.com/ZeyadMahmoudAmrMohamed) |

<div align="center">
<br/>
<sub>🫒 Zatoona · study smart, ace it with less.</sub>
</div>
