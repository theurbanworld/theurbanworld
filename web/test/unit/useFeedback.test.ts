/**
 * Unit tests for useFeedback — global feedback modal state.
 *
 * Verifies open/close toggling and that the singleton state is shared
 * across separate useFeedback() calls (both entry points drive one modal).
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { useFeedback } from '../../app/composables/useFeedback'

describe('useFeedback', () => {
  beforeEach(() => {
    // Reset shared singleton state between tests
    useFeedback().close()
  })

  it('open() sets isOpen true and close() sets it false', () => {
    const { isOpen, open, close } = useFeedback()

    expect(isOpen.value).toBe(false)

    open()
    expect(isOpen.value).toBe(true)

    close()
    expect(isOpen.value).toBe(false)
  })

  it('shares state across two useFeedback() instances (singleton)', () => {
    const a = useFeedback()
    const b = useFeedback()

    a.open()
    expect(b.isOpen.value).toBe(true)

    b.close()
    expect(a.isOpen.value).toBe(false)
  })

  it('isOpen is writable (v-model:open support)', () => {
    const { isOpen } = useFeedback()

    isOpen.value = true
    expect(isOpen.value).toBe(true)

    isOpen.value = false
    expect(isOpen.value).toBe(false)
  })
})
