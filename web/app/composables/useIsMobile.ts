export function useIsMobile(breakpoint = 639) {
  const isMobile = ref(false)

  if (import.meta.client) {
    const mql = window.matchMedia(`(max-width: ${breakpoint}px)`)
    isMobile.value = mql.matches

    mql.addEventListener('change', (e) => {
      isMobile.value = e.matches
    })
  }

  return isMobile
}
