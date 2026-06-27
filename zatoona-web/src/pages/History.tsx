import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'motion/react'
import { useAuth } from '../lib/auth'
import { useStudy } from '../lib/study'
import { ApiError, getHistory } from '../lib/api'
import type { Exam } from '../lib/types'
import { Mascot } from '../components/Mascot'
import { Alert, Button, Card, Chip, cx } from '../components/ui'

function formatDate(iso?: string) {
  if (!iso) return ''
  const d = new Date(iso)
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) +
        ' · ' +
        d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
}

export function History() {
  const { withAuth } = useAuth()
  const { setExam, setReport } = useStudy()
  const navigate = useNavigate()

  const [exams, setExams] = useState<Exam[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let alive = true
    withAuth((token) => getHistory(token))
      .then((data) => alive && setExams(data))
      .catch((err) => {
        if (!alive) return
        if (err instanceof ApiError && err.status === 404) setExams([]) // no exams yet
        else setError(err instanceof ApiError ? err.message : 'Could not load your history.')
      })
    return () => {
      alive = false
    }
  }, [withAuth])

  function retake(exam: Exam) {
    setReport(null)
    setExam(exam)
    navigate('/app/exam')
  }

  return (
    <div>
      <header className="mb-7">
        <h1 className="font-display text-3xl font-semibold text-brand-800">Your exams</h1>
        <p className="mt-1 text-muted">Every exam you’ve generated, newest first.</p>
      </header>

      {error && <Alert tone="error">{error}</Alert>}

      {!error && exams === null && (
        <ul className="flex flex-col gap-3" aria-hidden>
          {[0, 1, 2].map((i) => (
            <li key={i} className="h-24 animate-pulse rounded-xl border border-border bg-surface-2" />
          ))}
        </ul>
      )}

      {!error && exams?.length === 0 && (
        <Card className="flex flex-col items-center px-6 py-14 text-center">
          <Mascot mood="peek" size={104} />
          <p className="mt-4 font-display text-lg font-semibold text-brand-800">No exams yet</p>
          <p className="mt-1 max-w-xs text-muted">Generate your first exam and it’ll show up here.</p>
          <Button onClick={() => navigate('/app')} className="mt-5">
            Go to your desk
          </Button>
        </Card>
      )}

      {exams && exams.length > 0 && (
        <ul className="flex flex-col gap-3">
          {exams.map((exam, i) => (
            <HistoryRow key={exam.exam_id ?? i} exam={exam} index={i} onRetake={() => retake(exam)} />
          ))}
        </ul>
      )}
    </div>
  )
}

function HistoryRow({ exam, index, onRetake }: { exam: Exam; index: number; onRetake: () => void }) {
  const [open, setOpen] = useState(false)
  return (
    <motion.li
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: Math.min(index * 0.04, 0.3) }}
    >
      <Card className="overflow-hidden">
        <div className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="font-display font-semibold text-brand-800">
                Exam #{exam.exam_id ?? index + 1}
              </span>
              <span
                className={cx(
                  'rounded-full px-2 py-0.5 text-xs font-medium',
                  exam.status === 'validated' ? 'bg-success-bg text-success' : 'bg-surface-2 text-muted',
                )}
              >
                {exam.status}
              </span>
            </div>
            <p className="mt-1 text-sm text-muted">
              {exam.questions.length} question{exam.questions.length === 1 ? '' : 's'} · {formatDate(exam.created_at)}
            </p>
            <div className="mt-2.5 flex flex-wrap gap-1.5">
              {exam.topics.map((t) => (
                <Chip key={t}>{t}</Chip>
              ))}
            </div>
          </div>
          <div className="flex shrink-0 gap-2">
            <Button variant="secondary" size="sm" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
              {open ? 'Hide' : 'Review'}
            </Button>
            <Button size="sm" onClick={onRetake}>
              Retake
            </Button>
          </div>
        </div>

        <AnimatePresence initial={false}>
          {open && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
              className="overflow-hidden"
            >
              <ol className="space-y-2.5 border-t border-border px-5 py-4">
                {exam.questions.map((q, qi) => (
                  <li key={q.question_id} className="flex gap-2.5 text-sm">
                    <span className="font-display font-semibold text-brand-600">{qi + 1}.</span>
                    <span className="text-ink">{q.question}</span>
                  </li>
                ))}
              </ol>
            </motion.div>
          )}
        </AnimatePresence>
      </Card>
    </motion.li>
  )
}
