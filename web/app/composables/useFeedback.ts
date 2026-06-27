/**
 * useFeedback — global state for the feedback modal
 *
 * Singleton open/close state so any component (desktop button, mobile drawer
 * item) can open the same feedback modal. Mirrors useInfoModal's shape.
 */

// Module-level singleton — a plain writable ref is enough for `v-model:open`
// and shared open/close from either entry point.
const isOpen = ref(false)

export function useFeedback() {
  function open() {
    isOpen.value = true
  }

  function close() {
    isOpen.value = false
  }

  return {
    isOpen,
    open,
    close
  }
}
