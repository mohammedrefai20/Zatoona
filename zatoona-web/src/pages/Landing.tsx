import { Link } from 'react-router-dom'
import { motion, useReducedMotion } from 'motion/react'
import { Mascot } from '../components/Mascot'
import { Wordmark } from '../components/Brand'
import { isDark, toggleTheme } from '../lib/theme'
import { Button, cx } from '../components/ui'
import { useState } from 'react'

const ease = [0.16, 1, 0.3, 1] as const

export function Landing() {
  return (
    <div className="min-h-svh bg-canvas">
      <LandingNav />
      <Hero />
      <HowItWorks />
      <Features />
      <FinalCta />
      <Footer />
    </div>
  )
}

function LandingNav() {
  return (
    <header className="sticky top-0 border-b border-border/70 bg-canvas/80 backdrop-blur-md" style={{ zIndex: 'var(--z-sticky)' }}>
      <div className="mx-auto flex h-16 max-w-6xl items-center px-4 sm:px-6">
        <Wordmark size={30} />
        <nav className="ml-8 hidden items-center gap-1 md:flex" aria-label="Primary">
          <a href="#how" className="rounded-full px-3.5 py-2 text-sm font-medium text-muted transition-colors hover:text-ink">
            How it works
          </a>
          <a href="#features" className="rounded-full px-3.5 py-2 text-sm font-medium text-muted transition-colors hover:text-ink">
            Features
          </a>
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <ThemeToggle />
          <Link to="/login" className="hidden sm:block">
            <Button variant="ghost" size="sm">Log in</Button>
          </Link>
          <Link to="/login">
            <Button size="sm">Get started</Button>
          </Link>
        </div>
      </div>
    </header>
  )
}

function Hero() {
  const reduce = useReducedMotion()
  const rise = (delay: number) =>
    reduce
      ? {}
      : { initial: { opacity: 0, y: 24 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.7, ease, delay } }

  return (
    <section className="relative overflow-hidden">
      {/* soft brand glow, decorative */}
      <div aria-hidden className="pointer-events-none absolute -right-40 -top-40 h-[34rem] w-[34rem] rounded-full bg-brand-200/50 blur-3xl" />
      <div aria-hidden className="pointer-events-none absolute -left-32 top-40 h-96 w-96 rounded-full bg-olive-300/30 blur-3xl" />

      <div className="relative mx-auto grid max-w-6xl items-center gap-12 px-4 py-16 sm:px-6 lg:grid-cols-[1.05fr_1fr] lg:py-24">
        <div>
          <motion.span
            {...rise(0)}
            className="inline-flex items-center gap-2 rounded-full bg-olive-500/12 px-3.5 py-1.5 text-sm font-medium text-olive-700"
          >
            <span className="h-1.5 w-1.5 rounded-full bg-olive-500" />
            Zatoona — the smartest little summary
          </motion.span>

          <motion.h1
            {...rise(0.08)}
            className="mt-5 font-display text-5xl font-semibold leading-[1.05] tracking-tight text-brand-800 sm:text-6xl"
          >
            Study smart.
            <br />
            Ace it with less.
          </motion.h1>

          <motion.p {...rise(0.16)} className="mt-5 max-w-md text-lg leading-relaxed text-muted">
            Zatoona turns your own notes into a fair exam, then grades you with honest, encouraging feedback. Less cramming. Better marks.
          </motion.p>

          <motion.div {...rise(0.24)} className="mt-8 flex flex-wrap items-center gap-3">
            <Link to="/login">
              <Button size="lg">Start studying — it’s free</Button>
            </Link>
            <a href="#how">
              <Button variant="secondary" size="lg">See how it works</Button>
            </a>
          </motion.div>

          <motion.p {...rise(0.32)} className="mt-5 flex items-center gap-2 text-sm text-muted">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="text-olive-600" aria-hidden>
              <path d="M20 6 9 17l-5-5" />
            </svg>
            Tested only on your material — no made-up questions.
          </motion.p>
        </div>

        <HeroShowcase />
      </div>
    </section>
  )
}

function HeroShowcase() {
  const reduce = useReducedMotion()
  return (
    <motion.div
      initial={reduce ? false : { opacity: 0, scale: 0.94 }}
      animate={reduce ? {} : { opacity: 1, scale: 1 }}
      transition={{ duration: 0.8, ease, delay: 0.15 }}
      className="relative mx-auto w-full max-w-md"
    >
      <div className="relative aspect-square rounded-[2rem] bg-brand-900">
        <div aria-hidden className="absolute right-10 top-10 h-20 w-20 rounded-full bg-gold-400/30 blur-xl" />
        <Mascot mood="cheer" size={230} className="absolute bottom-6 left-1/2 -translate-x-1/2" label="Zatoona, the olive study buddy, celebrating" />

        {/* floating exam card — product imagery */}
        <motion.div
          animate={reduce ? {} : { y: [0, -10, 0] }}
          transition={{ duration: 4.5, repeat: Infinity, ease: 'easeInOut' }}
          className="absolute -left-4 top-8 w-60 rounded-xl border border-border bg-surface p-4 shadow-lg sm:-left-8"
        >
          <p className="text-xs font-medium text-muted">Question 2 of 5</p>
          <p className="mt-1 text-sm font-medium leading-snug text-ink">
            What made Stalingrad the turning point of the Eastern Front?
          </p>
          <div className="mt-2.5 h-8 rounded-lg bg-surface-2" />
        </motion.div>

        {/* floating score badge */}
        <motion.div
          animate={reduce ? {} : { y: [0, 10, 0] }}
          transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut', delay: 0.5 }}
          className="absolute -right-3 bottom-16 flex items-center gap-2.5 rounded-xl border border-border bg-surface px-4 py-3 shadow-lg sm:-right-6"
        >
          <span className="grid h-9 w-9 place-items-center rounded-full bg-success-bg text-success">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
              <path d="M20 6 9 17l-5-5" />
            </svg>
          </span>
          <div>
            <p className="font-display text-lg font-semibold leading-none text-brand-800">9/10</p>
            <p className="text-xs text-muted">Nice work!</p>
          </div>
        </motion.div>
      </div>
    </motion.div>
  )
}

function HowItWorks() {
  const steps = [
    {
      mood: 'think' as const,
      title: 'Feed it your notes',
      body: 'PDFs, slides, a YouTube lecture, or pasted text. Drop in whatever you’re studying from.',
    },
    {
      mood: 'idle' as const,
      title: 'Get a fair exam',
      body: 'Zatoona writes questions grounded strictly in your material — then double-checks each one.',
    },
    {
      mood: 'cheer' as const,
      title: 'Learn from feedback',
      body: 'Answer, get graded honestly, and see exactly which topics to revisit. Encouragement included.',
    },
  ]
  return (
    <section id="how" className="mx-auto max-w-6xl scroll-mt-20 px-4 py-20 sm:px-6">
      <div className="mx-auto max-w-2xl text-center">
        <h2 className="font-display text-3xl font-semibold text-brand-800 sm:text-4xl">Three steps to an A+</h2>
        <p className="mt-3 text-muted">From a pile of notes to knowing exactly what you’ve got down — in one sitting.</p>
      </div>

      <div className="relative mt-14 grid gap-10 md:grid-cols-3">
        {/* connector line on desktop */}
        <div aria-hidden className="absolute left-[16.66%] right-[16.66%] top-[2.75rem] hidden border-t-2 border-dashed border-border-2 md:block" />
        {steps.map((s, i) => (
          <div key={s.title} className="relative flex flex-col items-center text-center">
            <div className="grid h-22 w-22 place-items-center rounded-full bg-brand-50">
              <Mascot mood={s.mood} size={72} />
            </div>
            <span className="mt-4 grid h-7 w-7 place-items-center rounded-full bg-brand-600 font-display text-sm font-semibold text-white">
              {i + 1}
            </span>
            <h3 className="mt-3 font-display text-xl font-semibold text-brand-800">{s.title}</h3>
            <p className="mt-2 max-w-xs text-muted">{s.body}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

function Features() {
  return (
    <section id="features" className="scroll-mt-20 bg-surface-2/60 py-20">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="font-display text-3xl font-semibold text-brand-800 sm:text-4xl">Built to make studying click</h2>
          <p className="mt-3 text-muted">Not another quiz app. A study partner that actually reads what you read.</p>
        </div>

        {/* asymmetric bento — deliberately not an identical card grid */}
        <div className="mt-12 grid gap-4 md:grid-cols-3">
          <FeatureCard
            className="md:col-span-2 md:row-span-1"
            tone="brand"
            title="Grounded in your notes — nothing invented"
            body="Every question and every correction traces back to a specific chunk of your own material. No hallucinated facts, no surprise topics from the open internet."
          />
          <FeatureCard
            title="Any format"
            body="PDF, DOCX, PPTX, pasted text, or a YouTube lecture. Zatoona reads them all."
          />
          <FeatureCard
            title="Honest, kind feedback"
            body="Per-question explanations that teach, with a tone that keeps you going."
          />
          <FeatureCard
            title="Challenge mode"
            body="Questions that connect ideas across your notes, when you’re ready to push."
          />
          <FeatureCard
            tone="olive"
            title="Your history, saved"
            body="Revisit or retake any exam. Watch the topics you struggled with shrink."
          />
        </div>
      </div>
    </section>
  )
}

function FeatureCard({
  title,
  body,
  className,
  tone = 'plain',
}: {
  title: string
  body: string
  className?: string
  tone?: 'plain' | 'brand' | 'olive'
}) {
  const tones = {
    plain: 'bg-surface border border-border',
    brand: 'bg-brand-900 text-white border border-brand-900',
    olive: 'bg-olive-500/12 border border-olive-500/20',
  }
  return (
    <div
      className={cx(
        'rounded-2xl p-6 transition-transform duration-200 hover:-translate-y-1',
        tones[tone],
        className,
      )}
    >
      <h3 className={cx('font-display text-lg font-semibold', tone === 'brand' ? 'text-white' : 'text-brand-800')}>
        {title}
      </h3>
      <p className={cx('mt-2 text-[0.95rem] leading-relaxed', tone === 'brand' ? 'text-white/75' : 'text-muted')}>
        {body}
      </p>
    </div>
  )
}

function FinalCta() {
  return (
    <section className="px-4 py-20 sm:px-6">
      <div className="relative mx-auto max-w-5xl overflow-hidden rounded-[2rem] bg-brand-900 px-6 py-16 text-center sm:px-12">
        <div aria-hidden className="pointer-events-none absolute -left-20 -top-20 h-72 w-72 rounded-full bg-brand-700/40 blur-3xl" />
        <div aria-hidden className="pointer-events-none absolute -bottom-24 -right-16 h-80 w-80 rounded-full bg-olive-600/20 blur-3xl" />
        <div className="relative flex flex-col items-center">
          <Mascot mood="wave" size={120} />
          <h2 className="mt-5 max-w-xl font-display text-3xl font-semibold text-white sm:text-4xl">
            Ready to ace it the smart way?
          </h2>
          <p className="mt-3 max-w-md text-white/75">
            Upload your first set of notes and have a graded exam in minutes. No card required.
          </p>
          <Link to="/login" className="mt-7">
            <Button size="lg">Get started — free</Button>
          </Link>
        </div>
      </div>
    </section>
  )
}

function Footer() {
  return (
    <footer className="border-t border-border px-4 py-10 sm:px-6">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 sm:flex-row">
        <Wordmark size={26} />
        <p className="text-sm text-muted">Powered by the Leo Agent exam system.</p>
        <Link to="/login" className="text-sm font-medium text-brand-700 underline-offset-2 hover:underline">
          Log in
        </Link>
      </div>
    </footer>
  )
}

function ThemeToggle() {
  const [dark, setDark] = useState(isDark)
  return (
    <button
      onClick={() => setDark(toggleTheme())}
      className="grid h-9 w-9 place-items-center rounded-full text-muted transition-colors hover:bg-surface-2 hover:text-ink"
      aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {dark ? (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden>
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
        </svg>
      ) : (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
          <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
        </svg>
      )}
    </button>
  )
}
