import { StrictMode, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import './index.css'
import { AuthProvider, useAuth } from './lib/auth'
import { StudyProvider } from './lib/study'
import { Layout } from './components/Layout'
import { Landing } from './pages/Landing'
import { Login } from './pages/Login'
import { Home } from './pages/Home'
import { Exam } from './pages/Exam'
import { Results } from './pages/Results'
import { History } from './pages/History'

function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthed } = useAuth()
  return isAuthed ? <>{children}</> : <Navigate to="/login" replace />
}

function PublicOnly({ children }: { children: ReactNode }) {
  const { isAuthed } = useAuth()
  return isAuthed ? <Navigate to="/app" replace /> : <>{children}</>
}

// Public landing for logged-out visitors; logged-in users go straight to the desk.
function RootRoute() {
  const { isAuthed } = useAuth()
  return isAuthed ? <Navigate to="/app" replace /> : <Landing />
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider>
      <StudyProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<RootRoute />} />
            <Route path="/login" element={<PublicOnly><Login /></PublicOnly>} />
            <Route
              path="/app"
              element={
                <RequireAuth>
                  <Layout />
                </RequireAuth>
              }
            >
              <Route index element={<Home />} />
              <Route path="exam" element={<Exam />} />
              <Route path="results" element={<Results />} />
              <Route path="history" element={<History />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </StudyProvider>
    </AuthProvider>
  </StrictMode>,
)
