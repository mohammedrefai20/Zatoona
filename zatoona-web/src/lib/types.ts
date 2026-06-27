// Mirrors the Leo Agent API contract (see api-doc.md).

export interface Tokens {
  access_token: string
  refresh_token: string
  token_type?: string
  expires_in?: number
}

export type QuestionType = 'open' | 'mcq'

export interface Question {
  question_id: string
  topic: string
  question: string
  question_type?: QuestionType // defaults to 'open' for older exams
  options?: string[] | null // present for mcq
}

export type ExamStatus = 'draft' | 'validated'

export interface Exam {
  session_id: string
  topics: string[]
  status: ExamStatus
  questions: Question[]
  // present only on /history and /get-exam
  exam_id?: number
  created_at?: string
  updated_at?: string
}

export interface AnswerInput {
  question_id: string
  student_answer: string
}

export interface QuestionResult {
  question_id: string
  question: string
  student_answer: string
  is_correct: boolean
  explanation: string
  source_chunk: string
}

export interface FeedbackReport {
  session_id: string
  score: number
  topics_to_review: string[]
  encouragement: string
  results: QuestionResult[]
}

export interface UploadResult {
  topic: string
  chunks_stored: number
  message: string
}

export interface GenerateExamInput {
  topics: string[]
  num_questions: number
  difficult: boolean
  question_type?: 'open' | 'mcq' | 'mixed'
}

// ── Web enrichment ──
export interface Proposal {
  title: string
  url: string
  snippet: string
  topic: string
}

export interface EnrichOutcome {
  url: string
  stored_count: number | null
  status: string
  reason?: string
}

export interface EnrichItem {
  chunk_id: string
  url: string | null
  title: string | null
  topic: string | null
}
