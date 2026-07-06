/**
 * Tests for the useUrbanModelFit data composable (U5).
 *
 * Verifies on-demand loading, per city-epoch lookup, honest-null passthrough, and
 * graceful 404 handling. $fetch is stubbed so no network is required.
 */

import { describe, it, expect, vi, afterEach } from 'vitest'
import { useUrbanModelFit } from '../../app/composables/useUrbanModelFit'

const SAMPLE = {
  100: {
    2020: { D0: 12000, beta: 0.18, r2: 0.97, reliable: true, fitted: [11000, 9000, 7000] },
    2025: { D0: 5000, beta: 0.05, r2: 0.15, reliable: false, fitted: null }
  }
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('useUrbanModelFit', () => {
  it('getFit returns metrics for a present city-epoch and null for a missing one', async () => {
    vi.stubGlobal('$fetch', vi.fn(async () => SAMPLE))

    const { execute, getFit } = useUrbanModelFit()
    await execute()

    const fit = getFit('100', 2020)
    expect(fit).not.toBeNull()
    expect(fit?.beta).toBe(0.18)
    expect(fit?.r2).toBe(0.97)
    expect(fit?.reliable).toBe(true)
    expect(fit?.fitted).toEqual([11000, 9000, 7000])

    expect(getFit('999', 2020)).toBeNull() // unknown city
    expect(getFit('100', 1975)).toBeNull() // unknown epoch
  })

  it('surfaces a reliable:false entry with fitted:null intact', async () => {
    vi.stubGlobal('$fetch', vi.fn(async () => SAMPLE))

    const { execute, getFit } = useUrbanModelFit()
    await execute()

    const fit = getFit('100', 2025)
    expect(fit?.reliable).toBe(false)
    expect(fit?.fitted).toBeNull()
    // Metrics are retained even when unreliable.
    expect(fit?.D0).toBe(5000)
    expect(fit?.beta).toBe(0.05)
    expect(fit?.r2).toBe(0.15)
  })

  it('resolves a 404 to empty data without throwing', async () => {
    vi.stubGlobal(
      '$fetch',
      vi.fn(async () => {
        throw { statusCode: 404 }
      })
    )

    const { execute, getFit, error } = useUrbanModelFit()
    await execute()

    expect(error.value).toBeFalsy()
    expect(getFit('100', 2020)).toBeNull()
  })
})
