/**
 * Tests for useCityClimate (plan U5)
 *
 * Verifies R2 load (summary + profile), partial coverage, and graceful 404 (R13).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useCityClimate } from '../../app/composables/useCityClimate'
import {
  SOLAR_HEADLINE_KEY,
  CARBON_HEADLINE_KEY,
  HEAT_HEADLINE_KEY
} from '../../types/climate'

const summary = {
  100: { [SOLAR_HEADLINE_KEY]: 1500, [CARBON_HEADLINE_KEY]: 4.2 },
  200: { [SOLAR_HEADLINE_KEY]: 1320 } // partial: only solar
}
const profile = {
  100: {
    [SOLAR_HEADLINE_KEY]: { value: 1500 },
    [CARBON_HEADLINE_KEY]: { points: [[1975, 1], [2020, 4.2]] }
  },
  200: { [SOLAR_HEADLINE_KEY]: { value: 1320 } }
}

function stubFetch(impl: (url: string) => Promise<unknown>) {
  vi.stubGlobal('$fetch', vi.fn((url: string) => impl(url)))
}

describe('useCityClimate', () => {
  beforeEach(() => {
    clearNuxtData('climate-summary')
    clearNuxtData('climate-profile')
    vi.unstubAllGlobals()
  })

  it('loads summary + profile and returns the record for a covered city', async () => {
    stubFetch(url =>
      Promise.resolve(url.includes('summary') ? summary : profile)
    )
    const c = useCityClimate()
    await c.loadSummary()
    await c.loadProfile()

    expect(c.hasCityClimate('100')).toBe(true)
    expect(c.getHeadline('100', SOLAR_HEADLINE_KEY)).toBe(1500)
    const record = c.getClimate('100')
    expect(record?.[CARBON_HEADLINE_KEY]).toEqual({ points: [[1975, 1], [2020, 4.2]] })
    expect([...c.climateCities.value].sort()).toEqual(['100', '200'])
  })

  it('reports partial coverage and an uncovered city without error (R13)', async () => {
    stubFetch(url =>
      Promise.resolve(url.includes('summary') ? summary : profile)
    )
    const c = useCityClimate()
    await c.loadSummary()
    await c.loadProfile()

    // city 200 covered (solar only); city 999 not covered at all
    expect(c.hasCityClimate('200')).toBe(true)
    expect(c.getHeadline('200', SOLAR_HEADLINE_KEY)).toBe(1320)
    expect(c.getHeadline('200', HEAT_HEADLINE_KEY)).toBeUndefined()
    expect(c.hasCityClimate('999')).toBe(false)
    expect(c.getClimate('999')).toBeNull()
  })

  it('degrades to null on a 404 fetch, no throw', async () => {
    stubFetch(() => Promise.reject({ statusCode: 404 }))
    const c = useCityClimate()
    await c.loadSummary()
    await c.loadProfile()

    expect(c.hasCityClimate('100')).toBe(false)
    expect(c.getClimate('100')).toBeNull()
    expect(c.climateCities.value.size).toBe(0)
  })
})
