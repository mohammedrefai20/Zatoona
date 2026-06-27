import { useEffect, useState } from 'react'
import { motion } from 'motion/react'
import { Mascot, type Mood } from './Mascot'
import { cx } from './ui'

interface Props {
  title: string
  stages: string[]
  mood?: Mood
  /** ms each stage shows before advancing; the last stage holds until unmount */
  stageMs?: number
}

/**
 * Full-screen staged wait. The backend calls are synchronous (no progress stream),
 * so we advance through named phases on a timer and PARK on the last one until the
 * real response resolves and the parent unmounts us — activity without lying.
 */
export function StagedBusy({ title, stages, mood = 'think', stageMs = 2600 }: Props) {
  const [i, setI] = useState(0)
  useEffect(() => {
    if (i >= stages.length - 1) return
    const id = setTimeout(() => setI((n) => n + 1), stageMs)
    return () => clearTimeout(id)
  }, [i, stages.length, stageMs])

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 grid place-items-center bg-canvas/95 backdrop-blur-sm px-6"
      style={{ zIndex: 'var(--z-overlay)' }}
      role="status"
      aria-live="polite"
      aria-label={`${title}: ${stages[i]}`}
    >
      <div className="flex w-full max-w-sm flex-col items-center">
        <Mascot mood={mood} size={140} />
        <h2 className="mt-5 text-center font-display text-2xl font-semibold text-brand-800">{title}</h2>

        <ol className="mt-7 flex w-full flex-col gap-2.5">
          {stages.map((stage, idx) => {
            const state = idx < i ? 'done' : idx === i ? 'active' : 'pending'
            return (
              <li key={stage} className="flex items-center gap-3">
                <StageDot state={state} />
                <span
                  className={cx(
                    'text-[0.95rem] transition-colors',
                    state === 'done' && 'text-muted',
                    state === 'active' && 'font-medium text-ink',
                    state === 'pending' && 'text-faint',
                  )}
                >
                  {stage}
                </span>
              </li>
            )
          })}
        </ol>

        <div className="mt-7 h-1.5 w-full overflow-hidden rounded-full bg-brand-100">
          <motion.div
            className="h-full w-1/3 rounded-full bg-brand-500"
            animate={{ x: ['-120%', '320%'] }}
            transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}
          />
        </div>
        <p className="mt-3 text-center text-sm text-muted">This can take a couple of minutes — hang tight.</p>
      </div>
    </motion.div>
  )
}

function StageDot({ state }: { state: 'done' | 'active' | 'pending' }) {
  if (state === 'done')
    return (
      <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-olive-500 text-xs font-bold text-white">
        ✓
      </span>
    )
  if (state === 'active')
    return (
      <span className="relative grid h-6 w-6 shrink-0 place-items-center">
        <motion.span
          className="absolute inset-0 rounded-full bg-brand-400/40"
          animate={{ scale: [1, 1.5, 1], opacity: [0.6, 0, 0.6] }}
          transition={{ duration: 1.4, repeat: Infinity, ease: 'easeOut' }}
        />
        <span className="relative h-3 w-3 rounded-full bg-brand-600" />
      </span>
    )
  return (
    <span className="grid h-6 w-6 shrink-0 place-items-center">
      <span className="h-2.5 w-2.5 rounded-full border-2 border-border-2" />
    </span>
  )
}
