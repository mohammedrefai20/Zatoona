import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'motion/react'
import { useAuth } from '../lib/auth'
import { ApiError } from '../lib/api'
import { Mascot } from '../components/Mascot'
import { Wordmark } from '../components/Brand'
import { Alert, Button, Field, Input } from '../components/ui'

type Mode = 'signin' | 'signup'

const perks = [
  'Turn your own notes into a fair exam',
  'Questions grounded strictly in your material',
  'Honest grading with explanations — and encouragement',
]

export function Login() {
  const { signIn, register } = useAuth()
  const navigate = useNavigate()
  const [mode, setMode] = useState<Mode>('signin')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      if (mode === 'signin') await signIn(username.trim(), password)
      else await register(username.trim(), email.trim(), password)
      navigate('/app', { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid min-h-svh lg:grid-cols-[1.05fr_1fr]">
      {/* Brand panel — the one drenched-aubergine moment */}
      <aside className="relative hidden overflow-hidden bg-brand-900 lg:flex lg:flex-col lg:justify-between lg:p-12">
        <div
          aria-hidden
          className="pointer-events-none absolute -right-24 -top-24 h-96 w-96 rounded-full bg-brand-700/40 blur-3xl"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -bottom-32 -left-16 h-96 w-96 rounded-full bg-olive-600/20 blur-3xl"
        />
        <Wordmark size={36} light />

        <div className="relative">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          >
            <Mascot mood="wave" size={180} />
            <h1 className="mt-6 max-w-md font-display text-4xl font-semibold leading-tight text-white">
              Study smart, not hard.
            </h1>
            <p className="mt-3 max-w-sm text-white/75">
              Zatoona is the olive that already read your notes — and made the perfect little exam to prove you know them.
            </p>
          </motion.div>

          <ul className="mt-8 flex flex-col gap-3">
            {perks.map((p) => (
              <li key={p} className="flex items-start gap-2.5 text-sm text-white/80">
                <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-gold-400 text-xs font-bold text-brand-900">
                  ✓
                </span>
                {p}
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-xs text-white/55">Powered by the Leo Agent exam system.</p>
      </aside>

      {/* Form panel */}
      <div className="flex flex-col justify-center px-5 py-10 sm:px-10">
        <div className="mx-auto w-full max-w-sm">
          <div className="mb-8 lg:hidden">
            <Wordmark size={34} />
          </div>

          <h2 className="font-display text-2xl font-semibold text-brand-800">
            {mode === 'signin' ? 'Welcome back' : 'Create your account'}
          </h2>
          <p className="mt-1 text-muted">
            {mode === 'signin' ? 'Pick up where you left off.' : 'Start studying smarter in a minute.'}
          </p>

          <form onSubmit={onSubmit} className="mt-7 flex flex-col gap-4">
            <Field label="Username" htmlFor="username">
              <Input
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                required
                autoFocus
              />
            </Field>

            {mode === 'signup' && (
              <Field label="Email" htmlFor="email">
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                  required
                />
              </Field>
            )}

            <Field label="Password" htmlFor="password">
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete={mode === 'signin' ? 'current-password' : 'new-password'}
                required
                minLength={mode === 'signup' ? 6 : undefined}
              />
            </Field>

            {error && <Alert tone="error">{error}</Alert>}

            <Button type="submit" size="lg" loading={busy} className="mt-1 w-full">
              {mode === 'signin' ? 'Log in' : 'Create account'}
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-muted">
            {mode === 'signin' ? "New to Zatoona?" : 'Already have an account?'}{' '}
            <button
              type="button"
              onClick={() => {
                setMode((m) => (m === 'signin' ? 'signup' : 'signin'))
                setError('')
              }}
              className="font-medium text-brand-700 underline-offset-2 hover:underline"
            >
              {mode === 'signin' ? 'Create an account' : 'Log in'}
            </button>
          </p>
        </div>
      </div>
    </div>
  )
}
