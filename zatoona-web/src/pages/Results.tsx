import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'motion/react'
import { useStudy } from '../lib/study'
import type { QuestionResult } from '../lib/types'
import { Mascot, type Mood } from '../components/Mascot'
import { Button, Card, Chip, cx } from '../components/ui'

export function Results() {
  const { report, resetSession } = useStudy()
  const navigate = useNavigate()

  if (!report) return <Navigate to="/app" replace />

  const total = report.results.length
  const pct = total ? report.score / total : 0
  const mood: Mood = pct >= 0.8 ? 'cheer' : pct >= 0.5 ? 'wave' : 'sad'

  function newExam() {
    resetSession()
    navigate('/app')
  }

  return (
    <div className="pb-4">
      {/* Score hero */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="flex flex-col items-center text-center"
      >
        <Mascot mood={mood} size={130} />
        <p className="mt-4 text-sm font-medium uppercase tracking-wide text-muted">You scored</p>
        <p className="font-display text-6xl font-semibold leading-none text-brand-800">
          {report.score}
          <span className="text-3xl text-faint"> / {total}</span>
        </p>
        <p className="mt-4 max-w-prose text-lg text-ink">{report.encouragement}</p>

        {report.topics_to_review.length > 0 && (
          <div className="mt-6 w-full max-w-md rounded-xl bg-gold-400/12 px-5 py-4">
            <p className="text-sm font-semibold text-brand-800">Worth another look</p>
            <div className="mt-2.5 flex flex-wrap justify-center gap-2">
              {report.topics_to_review.map((t) => (
                <Chip key={t}>{t}</Chip>
              ))}
            </div>
          </div>
        )}

        <Button onClick={newExam} size="lg" className="mt-7">
          Start a new exam
        </Button>
      </motion.div>

      {/* Per-question breakdown */}
      <h2 className="mb-4 mt-12 font-display text-xl font-semibold text-brand-800">Question by question</h2>
      <ol className="flex flex-col gap-3">
        {report.results.map((r, i) => (
          <ResultRow key={r.question_id} result={r} index={i} />
        ))}
      </ol>
    </div>
  )
}

function ResultRow({ result, index }: { result: QuestionResult; index: number }) {
  const [open, setOpen] = useState(false)
  const correct = result.is_correct

  return (
    <motion.li
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: Math.min(index * 0.05, 0.4), ease: [0.16, 1, 0.3, 1] }}
    >
      <Card className="overflow-hidden">
        <button
          onClick={() => setOpen((o) => !o)}
          className="flex w-full items-start gap-3 px-4 py-4 text-left transition-colors hover:bg-surface-2 sm:px-5"
          aria-expanded={open}
        >
          <StatusIcon correct={correct} />
          <span className="flex-1">
            <span className="block font-medium leading-snug text-ink">{result.question}</span>
            <span className={cx('mt-0.5 block text-sm font-medium', correct ? 'text-success' : 'text-error')}>
              {correct ? 'Correct' : 'Needs review'}
            </span>
          </span>
          <motion.span animate={{ rotate: open ? 180 : 0 }} className="mt-1 text-faint" aria-hidden>
            ⌄
          </motion.span>
        </button>

        <AnimatePresence initial={false}>
          {open && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
              className="overflow-hidden"
            >
              <div className="space-y-4 border-t border-border px-4 py-4 sm:px-5">
                <Detail label="Your answer">
                  <p className="text-ink">{result.student_answer || <span className="text-faint">— left blank —</span>}</p>
                </Detail>
                <Detail label="Feedback">
                  <p className="text-ink">{result.explanation}</p>
                </Detail>
                {result.source_chunk && (
                  <Detail label="From your notes">
                    <p className="rounded-lg bg-surface-2 px-3.5 py-3 text-sm leading-relaxed text-muted">
                      {result.source_chunk}
                    </p>
                  </Detail>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </Card>
    </motion.li>
  )
}

function Detail({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-faint">{label}</p>
      {children}
    </div>
  )
}

function StatusIcon({ correct }: { correct: boolean }) {
  return (
    <span
      className={cx(
        'mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full text-sm font-bold',
        correct ? 'bg-success-bg text-success' : 'bg-error-bg text-error',
      )}
      aria-hidden
    >
      {correct ? '✓' : '✕'}
    </span>
  )
}
