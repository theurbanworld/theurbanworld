/**
 * useFeedback — global state for the feedback modal
 *
 * Singleton open/close state so any component (desktop button, mobile drawer
 * item) can open the same feedback modal. Mirrors useInfoModal's shape.
 */

const isOpenState = ref(false)

export function useFeedback() {
  const isOpen = computed({
    get: () => isOpenState.value,
    set: (val: boolean) => {
      isOpenState.value = val
    }
  })

  function open() {
    isOpenState.value = true
  }

  function close() {
    isOpenState.value = false
  }

  return {
    isOpen,
    open,
    close
  }
}
