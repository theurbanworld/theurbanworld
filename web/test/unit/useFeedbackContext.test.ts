/**
 * Unit tests for buildFeedbackContext — best-effort context assembly.
 *
 * Exercises the pure assembly helper across selected/unselected city states
 * (origin acceptance examples AE2 / AE3), serialization, and unresolved names.
 */

import { describe, it, expect } from 'vitest'
import { buildFeedbackContext } from '../../app/composables/useFeedbackContext'

describe('buildFeedbackContext', () => {
  // Covers AE2 — city selected, dataset + epoch set.
  it('returns url + city (id, name), dataset, and epoch when all present', () => {
    const ctx = buildFeedbackContext({
      url: 'https://theurban.world/city/123',
      cityId: '123',
      cityName: 'Lima',
      dataset: 'Urban World v1',
      epoch: 2025
    })

    expect(ctx).toEqual({
      url: 'https://theurban.world/city/123',
      city: { id: '123', name: 'Lima' },
      dataset: 'Urban World v1',
      epoch: 2025
    })
  })

  // Covers AE3 — no city selected.
  it('omits city when no city is selected and does not throw', () => {
    const ctx = buildFeedbackContext({
      url: 'https://theurban.world/',
      cityId: null,
      dataset: 'Urban World v1',
      epoch: 2025
    })

    expect(ctx).toEqual({
      url: 'https://theurban.world/',
      dataset: 'Urban World v1',
      epoch: 2025
    })
    expect(ctx.city).toBeUndefined()
  })

  it('carries city id with name absent when the id is unresolved in the index', () => {
    const ctx = buildFeedbackContext({
      url: 'https://theurban.world/city/999',
      cityId: '999',
      cityName: undefined,
      dataset: 'GHSL R2024',
      epoch: 1990
    })

    expect(ctx.city).toEqual({ id: '999' })
    expect(ctx.city?.name).toBeUndefined()
  })

  it('produces a JSON-serializable object that round-trips', () => {
    const ctx = buildFeedbackContext({
      url: 'https://theurban.world/city/123',
      cityId: '123',
      cityName: 'Lima',
      dataset: 'Urban World v1',
      epoch: 2025
    })

    expect(JSON.parse(JSON.stringify(ctx))).toEqual(ctx)
  })

  it('always includes url even when every other field is absent', () => {
    const ctx = buildFeedbackContext({ url: 'https://theurban.world/about' })
    expect(ctx).toEqual({ url: 'https://theurban.world/about' })
  })
})
