import { useMemo, useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'motion/react'
import { useAuth } from '../lib/auth'
import { useStudy } from '../lib/study'
import { ApiError, submitAnswers } from '../lib/api'
import { StagedBusy } from '../components/StagedBusy'
import { Alert, Button, Card, Chip, Textarea, cx } from '../components/ui'

export function Exam() {
  const { withAuth } = useAuth()
  const { exam, setReport } = useStudy()
  const navigate = useNavigate()

  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const total = exam?.questions.length ?? 0
  const answeredCount = useMemo(
    () => (exam ? exam.questions.filter((q) => (answers[q.question_id] ?? '').trim()).length : 0),
    [exam, answers],
  )

  if (!exam) return <Navigate to="/app" replace />

  async function onSubmit() {
    if (!exam) return
    setError('')
    const firstEmpty = exam.questions.find((q) => !(answers[q.question_id] ?? '').trim())
    if (firstEmpty) {
      setError('Answer every question before submitting — even a guess counts.')
      document.getElementById(`q-${firstEmpty.question_id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      return
    }
    setSubmitting(true)
    try {
      const report = await withAuth((token) =>
        submitAnswers(
          token,
          exam.questions.map((q) => ({
            question_id: q.question_id,
            student_answer: answers[q.question_id].trim(),
          })),
        ),
      )
      setReport(report)
      navigate('/app/results')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not submit your answers. Try again.')
      setSubmitting(false)
    }
  }

  const allAnswered = answeredCount === total

  return (
    <>
      <AnimatePresence>
        {submitting && (
          <StagedBusy
            title="Grading your answers…"
            mood="think"
            stages={[
              'Reading your answers',
              'Checking each against your notes',
              'Writing your feedback',
            ]}
          />
        )}
      </AnimatePresence>

      <header className="mb-7">
        <h1 className="font-display text-3xl font-semibold text-brand-800">Your exam</h1>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <span className="text-sm text-muted">Grounded in</span>
          {exam.topics.map((t) => (
            <Chip key={t}>{t}</Chip>
          ))}
        </div>
      </header>

      <ol className="flex flex-col gap-5 pb-28">
        {exam.questions.map((q, i) => {
          const done = !!(answers[q.question_id] ?? '').trim()
          return (
            <Card as="li" key={q.question_id} className="p-5 sm:p-6" >
              <div id={`q-${q.question_id}`} className="scroll-mt-24">
                <div className="mb-3 flex items-start gap-3">
                  <span
                    className="grid h-7 w-7 shrink-0 place-items-center rounded-full font-display text-sm font-semibold transition-colors"
                    style={
                      done
                        ? { background: 'var(--color-olive-500)', color: '#fff' }
                        : { background: 'var(--color-brand-50)', color: 'var(--color-brand-700)' }
                    }
                  >
                    {i + 1}
                  </span>
                  <p className="pt-0.5 text-[1.05rem] font-medium leading-snug text-ink">{q.question}</p>
                </div>
                {q.question_type === 'mcq' && q.options ? (
                  <fieldset className="ml-10 flex flex-col gap-2">
                    <legend className="sr-only">{`Options for question ${i + 1}`}</legend>
                    {q.options.map((opt) => {
                      const selected = answers[q.question_id] === opt
                      return (
                        <label
                          key={opt}
                          className={cx(
                            'flex cursor-pointer items-center gap-3 rounded-lg border p-3 transition-colors',
                            selected ? 'border-brand-400 bg-brand-50/60' : 'border-border hover:bg-surface-2',
                          )}
                        >
                          <input
                            type="radio"
                            name={q.question_id}
                            value={opt}
                            checked={selected}
                            onChange={() => setAnswers((a) => ({ ...a, [q.question_id]: opt }))}
                            className="h-4 w-4 accent-[var(--color-brand-600)]"
                          />
                          <span className="text-ink">{opt}</span>
                        </label>
                      )
                    })}
                  </fieldset>
                ) : (
                  <Textarea
                    aria-label={`Answer to question ${i + 1}`}
                    value={answers[q.question_id] ?? ''}
                    onChange={(e) => setAnswers((a) => ({ ...a, [q.question_id]: e.target.value }))}
                    placeholder="Type your answer…"
                    className="ml-10 w-[calc(100%-2.5rem)]"
                  />
                )}
              </div>
            </Card>
          )
        })}
      </ol>

      {/* sticky submit bar */}
      <motion.div
        initial={{ y: 80 }}
        animate={{ y: 0 }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        className="fixed inset-x-0 bottom-0 border-t border-border bg-canvas/90 backdrop-blur-md"
        style={{ zIndex: 'var(--z-sticky)' }}
      >
        <div className="mx-auto flex max-w-5xl items-center gap-4 px-4 py-3.5 sm:px-6">
          <div className="flex-1">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium text-ink">
                {answeredCount} of {total} answered
              </span>
              {error && <span className="hidden text-error sm:inline">{error}</span>}
            </div>
            <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-brand-100">
              <motion.div
                className="h-full rounded-full bg-brand-500"
                animate={{ width: `${total ? (answeredCount / total) * 100 : 0}%` }}
                transition={{ duration: 0.3, ease: 'easeOut' }}
              />
            </div>
          </div>
          <Button onClick={onSubmit} size="lg" loading={submitting} disabled={!allAnswered}>
            Submit exam
          </Button>
        </div>
      </motion.div>

      {error && (
        <div className="fixed inset-x-0 bottom-20 mx-auto max-w-5xl px-4 sm:hidden" style={{ zIndex: 'var(--z-sticky)' }}>
          <Alert tone="error">{error}</Alert>
        </div>
      )}
    </>
  )
}
