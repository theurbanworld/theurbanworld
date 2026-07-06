/**
 * Tests for useCityClimate (plan U5)
 *
 * Verifies R2 load (summary + per-city profile), partial coverage, and graceful
 * 404 (R13). The profile is fetched per-city (climate/{id}.json), matching the
 * split export.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useCityClimate, __clearClimateProfileCache } from '../../app/composables/useCityClimate'
import {
  SOLAR_HEADLINE_KEY,
  CARBON_HEADLINE_KEY,
  HEAT_HEADLINE_KEY
} from '../../types/climate'

const summary = {
  100: { [SOLAR_HEADLINE_KEY]: 1500, [CARBON_HEADLINE_KEY]: 4.2 },
  200: { [SOLAR_HEADLINE_KEY]: 1320 } // partial: only solar
}
const records: Record<string, object> = {
  100: {
    [SOLAR_HEADLINE_KEY]: { value: 1500 },
    [CARBON_HEADLINE_KEY]: { points: [[1975, 1], [2020, 4.2]] }
  },
  200: { [SOLAR_HEADLINE_KEY]: { value: 1320 } }
}

function cityIdFromUrl(url: string): string | null {
  const m = url.match(/climate\/(\w+)\.json/)
  return m ? m[1]! : null
}

function stubFetch() {
  vi.stubGlobal('$fetch', vi.fn((url: string) => {
    if (url.includes('climate_summary')) return Promise.resolve(summary)
    const id = cityIdFromUrl(url)
    if (id && records[id]) return Promise.resolve(records[id])
    return Promise.reject({ statusCode: 404 })
  }))
}

describe('useCityClimate', () => {
  beforeEach(() => {
    clearNuxtData('climate-summary')
    __clearClimateProfileCache()
    vi.unstubAllGlobals()
  })

  it('loads summary + per-city profile and returns the record for a covered city', async () => {
    stubFetch()
    const c = useCityClimate()
    await c.loadSummary()
    await c.loadCityProfile('100')

    expect(c.hasCityClimate('100')).toBe(true)
    expect(c.getHeadline('100', SOLAR_HEADLINE_KEY)).toBe(1500)
    expect(c.getClimate('100')?.[CARBON_HEADLINE_KEY]).toEqual({ points: [[1975, 1], [2020, 4.2]] })
    expect([...c.climateCities.value].sort()).toEqual(['100', '200'])
  })

  it('reports partial coverage and an uncovered city without error (R13)', async () => {
    stubFetch()
    const c = useCityClimate()
    await c.loadSummary()
    await c.loadCityProfile('200')
    await c.loadCityProfile('999')

    expect(c.hasCityClimate('200')).toBe(true)
    expect(c.getHeadline('200', SOLAR_HEADLINE_KEY)).toBe(1320)
    expect(c.getHeadline('200', HEAT_HEADLINE_KEY)).toBeUndefined()
    expect(c.isCityLoaded('999')).toBe(true) // fetch resolved...
    expect(c.hasCityClimate('999')).toBe(false) // ...as not covered
    expect(c.getClimate('999')).toBeNull()
  })

  it('degrades to null on a 404 profile fetch, no throw', async () => {
    stubFetch()
    const c = useCityClimate()
    await c.loadCityProfile('404')
    expect(c.getClimate('404')).toBeNull()
    expect(c.hasCityClimate('404')).toBe(false)
  })
})
