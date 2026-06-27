import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { AnimatePresence } from 'motion/react'
import { useAuth } from '../lib/auth'
import { useStudy } from '../lib/study'
import { ApiError, generateExam, uploadNotes } from '../lib/api'
import { Mascot } from '../components/Mascot'
import { StagedBusy } from '../components/StagedBusy'
import { EnrichPanel } from '../components/EnrichPanel'
import { Alert, Button, Card, Chip, Field, Input, Textarea, cx } from '../components/ui'

type Source = 'file' | 'url' | 'text'
const MAX_MB = 20

export function Home() {
  const { withAuth } = useAuth()
  const { topics, addTopic, setExam, setReport } = useStudy()
  const navigate = useNavigate()

  // ── upload state ──
  const [topic, setTopic] = useState('')
  const [source, setSource] = useState<Source>('file')
  const [file, setFile] = useState<File | null>(null)
  const [url, setUrl] = useState('')
  const [text, setText] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [uploadOk, setUploadOk] = useState('')

  // ── generate state ── (default-select any topics already in this session)
  const [selected, setSelected] = useState<Set<string>>(() => new Set(topics.map((t) => t.topic)))
  const [numQuestions, setNumQuestions] = useState(5)
  const [difficult, setDifficult] = useState(false)
  const [questionType, setQuestionType] = useState<'open' | 'mcq' | 'mixed'>('open')
  const [generating, setGenerating] = useState(false)
  const [genError, setGenError] = useState('')

  async function onUpload(e: FormEvent) {
    e.preventDefault()
    setUploadError('')
    setUploadOk('')
    const t = topic.trim()
    if (source === 'file') {
      if (!file) return setUploadError('Choose a file to upload.')
      if (file.size > MAX_MB * 1024 * 1024) return setUploadError(`File is over ${MAX_MB} MB.`)
    }
    if (source === 'url' && !url.trim()) return setUploadError('Paste a YouTube link.')
    if (source === 'text' && text.trim().length < 20)
      return setUploadError('Paste a bit more text (at least 20 characters).')

    setUploading(true)
    try {
      const res = await withAuth((token) =>
        uploadNotes(token, {
          topic: t,
          file: source === 'file' ? file ?? undefined : undefined,
          url: source === 'url' ? url.trim() : undefined,
          text: source === 'text' ? text.trim() : undefined,
        }),
      )
      addTopic(res)
      setSelected((s) => new Set(s).add(res.topic))
      setUploadOk(`Added “${res.topic}” — ${res.chunks_stored} chunks ready.`)
      setFile(null)
      setUrl('')
      setText('')
    } catch (err) {
      setUploadError(err instanceof ApiError ? err.message : 'Upload failed. Try again.')
    } finally {
      setUploading(false)
    }
  }

  async function onGenerate() {
    setGenError('')
    const chosen = topics.map((t) => t.topic).filter((name) => selected.has(name))
    if (chosen.length === 0) return setGenError('Pick at least one topic to be examined on.')
    setGenerating(true)
    try {
      const exam = await withAuth((token) =>
        generateExam(token, { topics: chosen, num_questions: numQuestions, difficult, question_type: questionType }),
      )
      setReport(null)
      setExam(exam)
      navigate('/app/exam')
    } catch (err) {
      setGenError(
        err instanceof ApiError ? err.message : 'Could not generate the exam. Try again.',
      )
      setGenerating(false)
    }
  }

  function toggleTopic(name: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }

  return (
    <>
      <AnimatePresence>
        {generating && (
          <StagedBusy
            title="Cooking up your exam…"
            mood="think"
            stages={[
              'Fetching your notes',
              'Drafting questions from your material',
              'Checking each question is grounded',
              'Finalizing your exam',
            ]}
          />
        )}
        {uploading && (
          <StagedBusy
            title="Adding your material…"
            mood="think"
            stages={[
              'Uploading your material',
              'Reading the document',
              'Splitting into smart chunks',
              'Embedding & storing',
            ]}
          />
        )}
      </AnimatePresence>

      <header className="mb-8 flex items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-semibold text-brand-800">Your study desk</h1>
          <p className="mt-1 text-muted">Add your material, then turn it into an exam.</p>
        </div>
        <Mascot mood="idle" size={84} className="hidden shrink-0 sm:block" />
      </header>

      <div className="grid items-start gap-6 lg:grid-cols-2">
        {/* ── Upload ── */}
        <Card className="p-6">
          <form onSubmit={onUpload}>
            <Step n={1} title="Add your material" />

          <Field
            label="Topic name (optional)"
            htmlFor="topic"
            hint="Leave blank and Zatoona will name it from your notes."
            className="mt-5"
          >
            <Input id="topic" value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="Auto-named from your notes…" />
          </Field>

          <div className="mt-5">
            <div className="mb-2 flex gap-1 rounded-full bg-surface-2 p-1">
              {(['file', 'url', 'text'] as Source[]).map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setSource(s)}
                  className={cx(
                    'flex-1 rounded-full py-1.5 text-sm font-medium capitalize transition-colors',
                    source === s ? 'bg-surface text-brand-700 shadow-sm' : 'text-muted hover:text-ink',
                  )}
                >
                  {s === 'url' ? 'YouTube' : s}
                </button>
              ))}
            </div>

            {source === 'file' && (
              <label
                className={cx(
                  'flex cursor-pointer flex-col items-center justify-center gap-1 rounded-lg border-2 border-dashed border-border-2 px-4 py-7 text-center transition-colors hover:border-brand-400 hover:bg-brand-50/50',
                )}
              >
                <input
                  type="file"
                  accept=".pdf,.docx,.pptx,.md,.txt"
                  className="sr-only"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                />
                <span className="text-sm font-medium text-ink">
                  {file ? file.name : 'Click to choose a file'}
                </span>
                <span className="text-xs text-muted">PDF, DOCX, PPTX · up to {MAX_MB} MB</span>
              </label>
            )}
            {source === 'url' && (
              <Input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://youtube.com/watch?v=…"
                inputMode="url"
              />
            )}
            {source === 'text' && (
              <Textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Paste your notes here…"
                className="min-h-32"
              />
            )}
          </div>

          {uploadError && (
            <div className="mt-4">
              <Alert tone="error">{uploadError}</Alert>
            </div>
          )}
          {uploadOk && (
            <div className="mt-4">
              <Alert tone="success">{uploadOk}</Alert>
            </div>
          )}

          <Button type="submit" loading={uploading} className="mt-5 w-full">
            Add material
          </Button>
          </form>

          {topics.length > 0 && (
            <div className="mt-6 border-t border-border pt-5">
              <p className="mb-2.5 text-sm font-medium text-ink">In this session</p>
              <div className="flex flex-wrap gap-2">
                {topics.map((t) => (
                  <Chip key={t.topic}>
                    {t.topic}
                    <span className="text-olive-600/80">· {t.chunks}</span>
                  </Chip>
                ))}
              </div>
            </div>
          )}
        </Card>

        {/* ── Generate ── */}
        <Card className="p-6">
          <Step n={2} title="Generate your exam" />

          {topics.length === 0 ? (
            <div className="mt-6 flex flex-col items-center rounded-lg bg-surface-2 px-6 py-10 text-center">
              <Mascot mood="peek" size={92} />
              <p className="mt-3 font-medium text-ink">No material yet</p>
              <p className="mt-1 text-sm text-muted">Add some notes on the left and I’ll build you an exam.</p>
            </div>
          ) : (
            <div className="mt-5 flex flex-col gap-6">
              <div>
                <p className="mb-2 text-sm font-medium text-ink">Examine me on</p>
                <div className="flex flex-wrap gap-2">
                  {topics.map((t) => (
                    <Chip key={t.topic} selected={selected.has(t.topic)} onClick={() => toggleTopic(t.topic)}>
                      {t.topic}
                    </Chip>
                  ))}
                </div>
              </div>

              <div>
                <p className="mb-2 text-sm font-medium text-ink">Question type</p>
                <div className="flex gap-1 rounded-full bg-surface-2 p-1">
                  {(['open', 'mcq', 'mixed'] as const).map((qt) => (
                    <button
                      key={qt}
                      type="button"
                      onClick={() => setQuestionType(qt)}
                      className={cx(
                        'flex-1 rounded-full py-1.5 text-sm font-medium capitalize transition-colors',
                        questionType === qt ? 'bg-surface text-brand-700 shadow-sm' : 'text-muted hover:text-ink',
                      )}
                    >
                      {qt === 'mcq' ? 'Multiple choice' : qt}
                    </button>
                  ))}
                </div>
              </div>

              <Field label="Number of questions" htmlFor="numq">
                <div className="flex items-center gap-3">
                  <Stepper value={numQuestions} min={1} max={10} onChange={setNumQuestions} />
                  <span className="text-sm text-muted">{numQuestions === 10 ? 'max' : `1–10`}</span>
                </div>
              </Field>

              <button
                type="button"
                role="switch"
                aria-checked={difficult}
                onClick={() => setDifficult((d) => !d)}
                className="flex items-center justify-between rounded-lg bg-surface-2 px-4 py-3 text-left"
              >
                <span>
                  <span className="block text-sm font-medium text-ink">Challenge mode</span>
                  <span className="block text-xs text-muted">Questions that connect ideas across your notes.</span>
                </span>
                <span
                  className={cx(
                    'relative h-6 w-11 shrink-0 rounded-full transition-colors',
                    difficult ? 'bg-brand-600' : 'bg-border-2',
                  )}
                >
                  <span
                    className={cx(
                      'absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all',
                      difficult ? 'left-[1.375rem]' : 'left-0.5',
                    )}
                  />
                </span>
              </button>

              {genError && <Alert tone="error">{genError}</Alert>}

              <Button onClick={onGenerate} size="lg" loading={generating} className="w-full">
                {generating ? 'Generating…' : 'Generate exam'}
              </Button>
            </div>
          )}
        </Card>
      </div>

      <EnrichPanel hasTopics={topics.length > 0} />
    </>
  )
}

function Step({ n, title }: { n: number; title: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-brand-600 font-display text-sm font-semibold text-white">
        {n}
      </span>
      <h2 className="font-display text-lg font-semibold text-brand-800">{title}</h2>
    </div>
  )
}

function Stepper({
  value,
  min,
  max,
  onChange,
}: {
  value: number
  min: number
  max: number
  onChange: (n: number) => void
}) {
  const btn =
    'grid h-9 w-9 place-items-center rounded-full bg-surface-2 text-lg text-ink transition-colors hover:bg-brand-50 disabled:opacity-40 disabled:hover:bg-surface-2'
  return (
    <div className="inline-flex items-center gap-3">
      <button type="button" className={btn} onClick={() => onChange(Math.max(min, value - 1))} disabled={value <= min} aria-label="Fewer questions">
        −
      </button>
      <span className="w-6 text-center font-display text-lg font-semibold tabular-nums text-brand-800">{value}</span>
      <button type="button" className={btn} onClick={() => onChange(Math.min(max, value + 1))} disabled={value >= max} aria-label="More questions">
        +
      </button>
    </div>
  )
}
