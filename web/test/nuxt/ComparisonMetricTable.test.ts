/**
 * Tests for the Standard Urban Model rows in ComparisonMetricTable (U9).
 *
 * Verifies numeric β/R² rows keep larger-value highlighting, categorical label rows
 * do not mis-highlight, and an unreliable city shows a dash on its side.
 */

import { describe, it, expect, vi } from 'vitest'
import { ref } from 'vue'
import { mountSuspended, mockNuxtImport } from '@nuxt/test-utils/runtime'
import type { UrbanModelFitEntry } from '../../app/composables/useUrbanModelFit'

const selectedYear = ref(2020)

// Per-test fit data keyed by city id.
let fitData: Record<string, UrbanModelFitEntry | null> = {}

mockNuxtImport('useSelectedYear', () => () => ({ selectedYear }))
mockNuxtImport('useUrbanModelFit', () => () => ({
  getFit: (cityId: string) => fitData[cityId] ?? null
}))

vi.mock('../../app/composables/useCityStats', () => ({
  useCityStats: () => ({
    isLoading: ref(false),
    populationHumanized: ref('1.0M'),
    populationRaw: ref(1000000),
    densityFormatted: ref('5 K/km2'),
    density: ref(5000),
    areaFormatted: ref('200 km2'),
    area: ref(200)
  })
}))

async function mountTable() {
  const ComparisonMetricTable = (await import('../../app/components/compare/ComparisonMetricTable.vue')).default
  return mountSuspended(ComparisonMetricTable, {
    props: { cityIdA: 'A', cityIdB: 'B' }
  })
}

describe('ComparisonMetricTable fit rows', () => {
  it('shows β/R² and labels for both reliable cities', async () => {
    fitData = {
      A: { D0: 12000, beta: 0.5, r2: 0.95, reliable: true, fitted: [1] },
      B: { D0: 8000, beta: 0.1, r2: 0.5, reliable: true, fitted: [1] }
    }
    const wrapper = await mountTable()
    const text = wrapper.text()

    expect(text).toContain('0.500') // city A β
    expect(text).toContain('0.100') // city B β
    expect(text).toContain('0.95') // city A R²
    expect(text).toContain('Compact') // A compactness label
    expect(text).toContain('Spread') // B compactness label
    expect(text).toContain('Single-center') // A structure
    expect(text).toContain('Multi-centered / Irregular') // B structure
  })

  it('shows a dash on the unreliable side and keeps the other', async () => {
    fitData = {
      A: { D0: 12000, beta: 0.5, r2: 0.95, reliable: true, fitted: [1] },
      B: { D0: 5000, beta: 0.05, r2: 0.15, reliable: false, fitted: null }
    }
    const wrapper = await mountTable()
    const text = wrapper.text()

    expect(text).toContain('0.500') // A still shown
    expect(text).toContain('—') // B dashed
    // B's labels are not rendered as concrete categories.
    expect(text).not.toContain('Spread')
  })

  it('categorical label rows do not use larger-value highlighting', async () => {
    fitData = {
      A: { D0: 12000, beta: 0.5, r2: 0.95, reliable: true, fitted: [1] },
      B: { D0: 8000, beta: 0.1, r2: 0.5, reliable: true, fitted: [1] }
    }
    const wrapper = await mountTable()
    const labelRows = wrapper.findAll('[data-testid="comparison-label-row"]')
    expect(labelRows.length).toBe(2)
    for (const row of labelRows) {
      expect(row.html()).not.toContain('font-semibold')
    }
  })
})
