import type {
  Tokens,
  Exam,
  AnswerInput,
  FeedbackReport,
  UploadResult,
  GenerateExamInput,
  Proposal,
  EnrichOutcome,
  EnrichItem,
} from './types'

// '' => same-origin; in dev that hits the Vite proxy -> nginx gateway (no CORS / preflight).
// Set VITE_API_BASE to the gateway URL for a production build served elsewhere.
export const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? ''

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

interface RequestOpts {
  method?: string
  token?: string
  json?: unknown
  form?: BodyInit // URLSearchParams or FormData
  signal?: AbortSignal
}

async function request<T>(path: string, opts: RequestOpts = {}): Promise<T> {
  const { method = 'GET', token, json, form, signal } = opts
  const headers: Record<string, string> = {}
  if (token) headers.Authorization = `Bearer ${token}`

  let body: BodyInit | undefined
  if (json !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(json)
  } else if (form !== undefined) {
    body = form // browser sets the right Content-Type (incl. multipart boundary)
  }

  let res: Response
  try {
    res = await fetch(API_BASE + path, { method, headers, body, signal })
  } catch (e) {
    if (signal?.aborted) throw e
    throw new ApiError(0, 'Cannot reach the server. Is the backend running?')
  }

  const text = await res.text()
  let data: unknown = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = text
    }
  }

  if (!res.ok) {
    const d = data as { detail?: string; message?: string } | string | null
    const msg =
      (d && typeof d === 'object' && (d.detail || d.message)) ||
      (typeof d === 'string' && d) ||
      `Request failed (${res.status})`
    throw new ApiError(res.status, msg as string)
  }
  return data as T
}

// ── Auth ──
export function login(username: string, password: string) {
  return request<Tokens>('/auth/login', {
    method: 'POST',
    form: new URLSearchParams({ username, password }),
  })
}

export function signup(username: string, email: string, password: string) {
  return request<{ message: string }>('/auth/signup', {
    method: 'POST',
    form: new URLSearchParams({ username, email, password }),
  })
}

export function refreshTokens(refresh_token: string) {
  return request<Tokens>('/auth/refresh', { method: 'POST', json: { refresh_token } })
}

export function logout(token: string, refresh_token?: string) {
  const form = new URLSearchParams()
  if (refresh_token) form.set('refresh_token', refresh_token)
  return request<unknown>('/auth/logout', { method: 'POST', token, form }).catch(() => null)
}

// ── Notes / exams ──
export interface UploadSource {
  topic?: string // optional — backend auto-names from content when blank
  file?: File
  url?: string
  text?: string
}

export function uploadNotes(token: string, src: UploadSource, signal?: AbortSignal) {
  const form = new FormData()
  if (src.topic && src.topic.trim()) form.set('topic', src.topic.trim())
  if (src.file) form.set('file', src.file, src.file.name)
  else if (src.url) form.set('url', src.url)
  else if (src.text) form.set('text', src.text)
  return request<UploadResult>('/upload/', { method: 'POST', token, form, signal })
}

export function generateExam(token: string, input: GenerateExamInput, signal?: AbortSignal) {
  return request<Exam>('/generate-exam/', { method: 'POST', token, json: input, signal })
}

export function submitAnswers(token: string, answers: AnswerInput[], signal?: AbortSignal) {
  return request<FeedbackReport>('/submit-answer/', {
    method: 'POST',
    token,
    json: { answers },
    signal,
  })
}

export function getHistory(token: string) {
  return request<Exam[]>('/history/', { token })
}

// ── Web enrichment ──
export function proposeEnrichment(token: string, limit?: number, signal?: AbortSignal) {
  return request<{ proposals: Proposal[] }>('/enrich/propose/', {
    method: 'POST',
    token,
    json: { limit: limit ?? null },
    signal,
  })
}

export function ingestEnrichment(token: string, approved: Proposal[], signal?: AbortSignal) {
  return request<{ outcomes: EnrichOutcome[] }>('/enrich/ingest/', {
    method: 'POST',
    token,
    json: { approved },
    signal,
  })
}

export function listEnrichment(token: string) {
  return request<{ items: EnrichItem[] }>('/enrich/', { token })
}

export function removeEnrichment(token: string) {
  return request<{ removed: number }>('/enrich/', { method: 'DELETE', token })
}

export function getExam(token: string, examId: number) {
  return request<Exam>(`/get-exam/${examId}`, { token })
}
