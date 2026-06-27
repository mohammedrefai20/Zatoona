import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { ApiError, login as apiLogin, refreshTokens, signup as apiSignup, logout as apiLogout } from './api'
import type { Tokens } from './types'

interface Session {
  accessToken: string
  refreshToken: string
  username: string
}

interface AuthValue {
  session: Session | null
  isAuthed: boolean
  signIn: (username: string, password: string) => Promise<void>
  register: (username: string, email: string, password: string) => Promise<void>
  signOut: () => void
  /** Run an API call with the current token; auto-refreshes once on 401. */
  withAuth: <T>(fn: (token: string) => Promise<T>) => Promise<T>
}

const STORAGE_KEY = 'zatoona.session'
const AuthContext = createContext<AuthValue | null>(null)

function load(): Session | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as Session) : null
  } catch {
    return null
  }
}

function persist(s: Session | null) {
  if (s) localStorage.setItem(STORAGE_KEY, JSON.stringify(s))
  else localStorage.removeItem(STORAGE_KEY)
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(load)

  const setFromTokens = useCallback((t: Tokens, username: string) => {
    const s: Session = { accessToken: t.access_token, refreshToken: t.refresh_token, username }
    persist(s)
    setSession(s)
    return s
  }, [])

  const signIn = useCallback(
    async (username: string, password: string) => {
      const t = await apiLogin(username, password)
      setFromTokens(t, username)
    },
    [setFromTokens],
  )

  const register = useCallback(
    async (username: string, email: string, password: string) => {
      await apiSignup(username, email, password)
      // Smooth path: sign the new user straight in.
      const t = await apiLogin(username, password)
      setFromTokens(t, username)
    },
    [setFromTokens],
  )

  const signOut = useCallback(() => {
    const cur = session
    persist(null)
    setSession(null)
    if (cur) void apiLogout(cur.accessToken, cur.refreshToken)
  }, [session])

  const withAuth = useCallback(
    async <T,>(fn: (token: string) => Promise<T>): Promise<T> => {
      const cur = session
      if (!cur) throw new ApiError(401, 'Please log in.')
      try {
        return await fn(cur.accessToken)
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) {
          try {
            const t = await refreshTokens(cur.refreshToken)
            const next = setFromTokens(t, cur.username)
            return await fn(next.accessToken)
          } catch {
            persist(null)
            setSession(null)
            throw new ApiError(401, 'Your session expired — please log in again.')
          }
        }
        throw e
      }
    },
    [session, setFromTokens],
  )

  const value = useMemo<AuthValue>(
    () => ({ session, isAuthed: !!session, signIn, register, signOut, withAuth }),
    [session, signIn, register, signOut, withAuth],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
