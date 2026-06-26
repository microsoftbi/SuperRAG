import { ref } from 'vue'

const STORAGE_KEY = 'theme'

const isDark = ref(false)
let initialized = false

function getInitialTheme() {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'dark') return true
  if (stored === 'light') return false
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

function applyTheme(dark) {
  document.documentElement.classList.toggle('dark', dark)
  isDark.value = dark
}

export function useTheme() {
  if (!initialized) {
    initialized = true
    applyTheme(getInitialTheme())

    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    mq.addEventListener('change', (e) => {
      if (!localStorage.getItem(STORAGE_KEY)) {
        applyTheme(e.matches)
      }
    })
  }

  function toggle() {
    const next = !isDark.value
    applyTheme(next)
    localStorage.setItem(STORAGE_KEY, next ? 'dark' : 'light')
  }

  function setTheme(mode) {
    const dark = mode === 'dark'
    applyTheme(dark)
    localStorage.setItem(STORAGE_KEY, mode)
  }

  return { isDark, toggle, setTheme }
}
