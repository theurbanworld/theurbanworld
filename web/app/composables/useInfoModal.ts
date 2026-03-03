/**
 * useInfoModal — global state for the info modal
 *
 * Manages which content path is currently shown in the modal.
 * Any component can open the modal by calling open('/data/source-ghsl').
 */

const activePath = ref<string | null>(null)

export function useInfoModal() {
  const isOpen = computed({
    get: () => activePath.value !== null,
    set: (val: boolean) => {
      if (!val) activePath.value = null
    }
  })

  function open(path: string) {
    activePath.value = path
  }

  function close() {
    activePath.value = null
  }

  return {
    activePath: readonly(activePath),
    isOpen,
    open,
    close
  }
}
