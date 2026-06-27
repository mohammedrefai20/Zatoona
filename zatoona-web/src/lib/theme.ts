// Tiny theme helper. The initial class is set pre-paint by an inline script in index.html.
const KEY = 'zatoona.theme'

export function isDark() {
  return document.documentElement.classList.contains('dark')
}

export function toggleTheme() {
  const next = !isDark()
  document.documentElement.classList.toggle('dark', next)
  localStorage.setItem(KEY, next ? 'dark' : 'light')
  return next
}
