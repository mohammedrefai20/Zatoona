import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { isDark, toggleTheme } from '../lib/theme'
import { Wordmark } from './Brand'
import { cx } from './ui'

const links = [
  { to: '/app', label: 'Study', end: true },
  { to: '/app/history', label: 'History', end: false },
]

export function Layout() {
  const { session, signOut } = useAuth()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)

  const initial = (session?.username?.[0] ?? '?').toUpperCase()

  return (
    <div className="flex min-h-svh flex-col">
      <header
        className="sticky top-0 border-b border-border bg-canvas/85 backdrop-blur-md"
        style={{ zIndex: 'var(--z-sticky)' }}
      >
        <div className="mx-auto flex h-16 max-w-5xl items-center gap-6 px-4 sm:px-6">
          <NavLink to="/app" className="shrink-0 rounded-lg">
            <Wordmark size={30} />
          </NavLink>

          <nav className="flex items-center gap-1" aria-label="Primary">
            {links.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                end={l.end}
                className={({ isActive }) =>
                  cx(
                    'rounded-full px-3.5 py-2 text-sm font-medium transition-colors',
                    isActive ? 'bg-brand-50 text-brand-700' : 'text-muted hover:bg-surface-2 hover:text-ink',
                  )
                }
              >
                {l.label}
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-1.5">
            <ThemeToggle />
            <div className="relative">
            <button
              onClick={() => setMenuOpen((o) => !o)}
              className="flex items-center gap-2 rounded-full py-1 pl-1 pr-3 transition-colors hover:bg-surface-2"
              aria-haspopup="menu"
              aria-expanded={menuOpen}
            >
              <span className="grid h-9 w-9 place-items-center rounded-full bg-brand-600 text-sm font-semibold text-white">
                {initial}
              </span>
              <span className="hidden max-w-32 truncate text-sm font-medium text-ink sm:inline">
                {session?.username}
              </span>
            </button>

            {menuOpen && (
              <>
                <div className="fixed inset-0" style={{ zIndex: 'var(--z-dropdown)' }} onClick={() => setMenuOpen(false)} />
                <div
                  role="menu"
                  className="absolute right-0 mt-2 w-44 overflow-hidden rounded-xl border border-border bg-surface shadow-lg"
                  style={{ zIndex: 'var(--z-dropdown)' }}
                >
                  <div className="border-b border-border px-3.5 py-2.5">
                    <p className="text-xs text-muted">Signed in as</p>
                    <p className="truncate text-sm font-medium text-ink">{session?.username}</p>
                  </div>
                  <button
                    role="menuitem"
                    onClick={() => {
                      setMenuOpen(false)
                      signOut()
                      navigate('/login')
                    }}
                    className="w-full px-3.5 py-2.5 text-left text-sm text-ink transition-colors hover:bg-surface-2"
                  >
                    Log out
                  </button>
                </div>
              </>
            )}
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6 sm:py-12">
        <Outlet />
      </main>
    </div>
  )
}

function ThemeToggle() {
  const [dark, setDark] = useState(isDark)
  return (
    <button
      onClick={() => setDark(toggleTheme())}
      className="grid h-9 w-9 place-items-center rounded-full text-muted transition-colors hover:bg-surface-2 hover:text-ink"
      aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
      title={dark ? 'Light mode' : 'Dark mode'}
    >
      {dark ? (
        // sun
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden>
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
        </svg>
      ) : (
        // moon
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
          <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
        </svg>
      )}
    </button>
  )
}
