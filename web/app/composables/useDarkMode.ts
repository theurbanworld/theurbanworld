/**
 * Dark mode state management composable
 *
 * Provides centralized dark mode state that persists to localStorage.
 * Used by all components that need to respond to theme changes.
 */

// Storage key for dark mode preference
const STORAGE_KEY = 'urbanworld-dark-mode'

// Singleton reactive state shared across composable instances
const isDarkMode = ref(false)
const isInitialized = ref(false)

export function useDarkMode() {
  /**
   * Apply dark mode class to document
   */
  function applyDarkMode(dark: boolean) {
    if (typeof document !== 'undefined') {
      if (dark) {
        document.documentElement.classList.add('dark')
      } else {
        document.documentElement.classList.remove('dark')
      }
    }
  }

  /**
   * Set dark mode state
   */
  function setDarkMode(dark: boolean) {
    isDarkMode.value = dark
    applyDarkMode(dark)

    // Persist to localStorage
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, dark ? 'dark' : 'light')
    }
  }

  /**
   * Toggle dark mode
   */
  function toggleDarkMode() {
    setDarkMode(!isDarkMode.value)
  }

  /**
   * Initialize dark mode from localStorage or system preference
   * Should be called once on app startup
   */
  function initializeDarkMode() {
    if (isInitialized.value) return
    if (typeof window === 'undefined') return

    // Check localStorage first
    const stored = localStorage.getItem(STORAGE_KEY)

    if (stored) {
      isDarkMode.value = stored === 'dark'
    } else {
      // Fall back to system preference
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
      isDarkMode.value = prefersDark
    }

    applyDarkMode(isDarkMode.value)
    isInitialized.value = true

    // Listen for system preference changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
      // Only auto-update if user hasn't explicitly set a preference
      if (!localStorage.getItem(STORAGE_KEY)) {
        isDarkMode.value = e.matches
        applyDarkMode(e.matches)
      }
    })
  }

  return {
    /** Whether dark mode is currently enabled */
    isDarkMode: readonly(isDarkMode),
    /** Whether dark mode has been initialized */
    isInitialized: readonly(isInitialized),
    /** Set dark mode explicitly */
    setDarkMode,
    /** Toggle dark mode */
    toggleDarkMode,
    /** Initialize dark mode (call once on app startup) */
    initializeDarkMode
  }
}
