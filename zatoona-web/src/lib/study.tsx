import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { useAuth } from './auth'
import type { Exam, FeedbackReport, UploadResult } from './types'

export interface UploadedTopic {
  topic: string
  chunks: number
}

interface StudyValue {
  exam: Exam | null
  report: FeedbackReport | null
  topics: UploadedTopic[]
  setExam: (e: Exam | null) => void
  setReport: (r: FeedbackReport | null) => void
  addTopic: (u: UploadResult) => void
  resetSession: () => void
}

const StudyContext = createContext<StudyValue | null>(null)

// All study state is namespaced per-user so one account never sees another's
// topics/exams on a shared browser. topics persist across logins (localStorage,
// matching the per-user chunks that persist in Chroma); exam/report are transient.
function read<T>(store: Storage, base: string, uid: string): T | null {
  try {
    const raw = store.getItem(`zatoona.${base}.${uid}`)
    return raw ? (JSON.parse(raw) as T) : null
  } catch {
    return null
  }
}
function write(store: Storage, base: string, uid: string, val: unknown) {
  const key = `zatoona.${base}.${uid}`
  if (val == null) store.removeItem(key)
  else store.setItem(key, JSON.stringify(val))
}

/** Remounts the inner provider whenever the user changes, giving each account a clean slate. */
export function StudyProvider({ children }: { children: ReactNode }) {
  const { session } = useAuth()
  const uid = session?.username ?? 'anon'
  return (
    <StudyProviderInner key={uid} uid={uid}>
      {children}
    </StudyProviderInner>
  )
}

function StudyProviderInner({ uid, children }: { uid: string; children: ReactNode }) {
  const [exam, setExamState] = useState<Exam | null>(() => read(sessionStorage, 'exam', uid))
  const [report, setReportState] = useState<FeedbackReport | null>(() =>
    read(sessionStorage, 'report', uid),
  )
  const [topics, setTopics] = useState<UploadedTopic[]>(
    () => read<UploadedTopic[]>(localStorage, 'topics', uid) ?? [],
  )

  useEffect(() => write(sessionStorage, 'exam', uid, exam), [exam, uid])
  useEffect(() => write(sessionStorage, 'report', uid, report), [report, uid])
  useEffect(() => write(localStorage, 'topics', uid, topics), [topics, uid])

  const setExam = useCallback((e: Exam | null) => setExamState(e), [])
  const setReport = useCallback((r: FeedbackReport | null) => setReportState(r), [])

  const addTopic = useCallback((u: UploadResult) => {
    setTopics((prev) => {
      const existing = prev.find((t) => t.topic === u.topic)
      const others = prev.filter((t) => t.topic !== u.topic)
      const chunks = (existing?.chunks ?? 0) + (u.chunks_stored ?? 0)
      return [...others, { topic: u.topic, chunks }]
    })
  }, [])

  const resetSession = useCallback(() => {
    setExamState(null)
    setReportState(null)
  }, [])

  const value = useMemo<StudyValue>(
    () => ({ exam, report, topics, setExam, setReport, addTopic, resetSession }),
    [exam, report, topics, setExam, setReport, addTopic, resetSession],
  )

  return <StudyContext.Provider value={value}>{children}</StudyContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useStudy() {
  const ctx = useContext(StudyContext)
  if (!ctx) throw new Error('useStudy must be used within StudyProvider')
  return ctx
}
