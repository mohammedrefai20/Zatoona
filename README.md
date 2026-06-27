# Team C — Corrector Agent & Feedback System

This module is responsible for the final stage of the Classroom Exam Agent pipeline.
It receives a validated exam from the exam creation pipeline, collects the student's
answers, grades each one using the student's own notes as reference, and returns a
structured feedback report through a Streamlit UI.

---

## What This Module Does

```
Validated exam (from exam pipeline)
        │
        ▼
Student answers questions via UI
        │
        ▼
Corrector Agent grades each answer
  └── retrieves source chunk from MCP server
  └── sends question + answer + chunk to LLM
  └── LLM grades and explains using the notes
        │
        ▼
Encouragement message generated based on score
        │
        ▼
Feedback report returned to student via UI
```

---

## Module Structure

```
agents/
  corrector_agent.py      # core grading logic — grades answers, explains mistakes
  exam_loader.py          # loads exam (mock or real pipeline)
  answer_loader.py        # loads student answers (mock or real UI)

mcp_server/
  mcp_client.py           # connects to MCP server to retrieve note chunks by ID

schemas/
  exam_object.py          # ExamObject and Question — received from exam pipeline
  feedback_report.py      # FeedbackReport and QuestionResult — produced by this module
  note_chunk.py           # NoteChunk — returned by MCP server

ui/
  app.py                  # Streamlit UI — 3 pages: exam, grading, feedback report

utils/
  report_writer.py        # saves and prints feedback reports

tests/team_c/
  test_corrector_agent.py       # end-to-end test for the corrector agent
  mock_mcp_tool.py              # simulates MCP server for local testing
  mock_data/
    mock_exam_object.json       # sample exam for testing
    mock_student_answers.json   # sample answers for testing
    mock_mcp_response.json      # sample note chunks for testing

outputs/
  report_<session_id>.json      # generated feedback reports saved here
```

---

## Corrector Agent Flow

```
For each question in the exam
        │
        ├── get source_chunk_id from exam object
        │
        ├── call MCP: get_chunk_by_id(source_chunk_id)
        │       └── returns the note chunk the question was built from
        │
        ├── send to LLM (Groq):
        │       question + correct answer + student answer + note chunk
        │
        └── LLM returns:
                is_correct: true / false
                explanation: grounded in the student's own notes

After all questions
        └── collect wrong topics
        └── generate encouragement message based on score
        └── build FeedbackReport
```

---

## Feedback Report Schema

```python
class QuestionResult(BaseModel):
    question_id    : str
    question       : str
    student_answer : str
    is_correct     : bool
    explanation    : str       # references the student's notes
    source_chunk   : str       # the note chunk used for grading

class FeedbackReport(BaseModel):
    session_id       : str
    score            : int
    topics_to_review : list[str]
    encouragement    : str
    results          : list[QuestionResult]
```

---

## UI Pages

```
Page 1 — Exam
  Student reads each question
  Types answer in text input
  Submits when all answers are filled

Page 2 — Grading
  Spinner shown while corrector agent runs
  MCP server queried per question
  LLM grades each answer

Page 3 — Feedback Report
  Score + progress bar
  Encouragement message
  Topics to review (if any)
  Per-question expandable cards
    ✅ Correct — short confirmation
    ❌ Wrong   — explanation + reference to notes
  Button to start a new exam
```

---

## Integration Points

```
Depends on                    What we need from them
──────────────────────────────────────────────────────────────
MCP server (Layer 1)          get_chunk_by_id(chunk_id) tool
                              must return NoteChunk with content field

Exam pipeline (Layer 2)       validated ExamObject
                              each question must have source_chunk_id
```

### Switching from mock to real

All integration points are controlled by flags in `.env`:

```
USE_REAL_MCP=false      # true when MCP server is running
USE_REAL_EXAM=false     # true when exam pipeline is connected
USE_REAL_ANSWERS=false  # true when answers come from UI (always true in production)
```

Flip one flag at a time and test before flipping the next.

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Fill in:
```
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile
USE_REAL_MCP=false
USE_REAL_EXAM=false
USE_REAL_ANSWERS=false
```

---

## Running

### Run the corrector agent test (mock mode)

```bash
python -m tests.team_c.test_corrector_agent
```

Output: graded report printed to terminal + saved to `outputs/`

### Run the full end-to-end test (real integrations)

Make sure the MCP server is running in a separate terminal first:

```bash
python -m mcp_server.server
```

Then set flags in `.env`:
```
USE_REAL_MCP=true
USE_REAL_EXAM=true
```

Then run:
```bash
python -m tests.team_c.test_corrector_agent
```

### Run the UI

```bash
streamlit run ui/app.py
```

Opens at `http://localhost:8501`

---

## Testing Strategy

```
Week 1 — mock everything
  USE_REAL_MCP=false
  USE_REAL_EXAM=false
  Run: python -m tests.team_c.test_corrector_agent

Week 2 — integrate one layer at a time
  Step 1: set USE_REAL_MCP=true  → test MCP connection alone
  Step 2: set USE_REAL_EXAM=true → test full pipeline

Week 3 — end-to-end
  All flags true
  Run full pipeline + UI
  streamlit run ui/app.py
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Grading LLM | Groq — llama-3.3-70b-versatile |
| Agent framework | LangChain |
| MCP client | mcp (streamable-http transport) |
| UI | Streamlit |
| Schema validation | Pydantic |
| Environment | python-dotenv |
| Testing | pytest |

---

## Key Design Decisions

```
Decision 1 — Grade by chunk ID not by topic search
  reason: each question already has source_chunk_id
  benefit: direct retrieval, no semantic search needed, faster and more accurate

Decision 2 — Single MCP client file
  reason: one place to swap mock for real
  benefit: changing USE_REAL_MCP is the only change needed

Decision 3 — Session resets between exams
  reason: each exam is tied to one session's notes
  benefit: no cross-session contamination

Decision 4 — Encouragement generated after all grading
  reason: needs the full score and topic list to be personalized
  benefit: one LLM call instead of one per question
```
