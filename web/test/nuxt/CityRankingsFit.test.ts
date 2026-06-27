/**
 * Tests for the Standard Urban Model ranking stats + city-type filter (U10).
 *
 * Covers AE3 (epoch-scoped null exclusion), R² ordering, the city-type filter,
 * the empty-result state, and the explained silent-shrink affordance.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { ref } from 'vue'
import { mountSuspended, mockNuxtImport } from '@nuxt/test-utils/runtime'
import type { UrbanModelFitEntry } from '../../app/composables/useUrbanModelFit'
import { useRankingFilters } from '../../app/composables/useRankingFilters'
import { useSelectedYear } from '../../app/composables/useSelectedYear'
import { COMPACTNESS_LABEL_VALUES, STRUCTURE_LABEL_VALUES } from '../../app/utils/urbanModelLabels'

vi.stubGlobal('navigateTo', vi.fn())

const CITIES = [
  { id: 'A', name: 'Alpha', country: 'X' },
  { id: 'B', name: 'Beta', country: 'X' },
  { id: 'C', name: 'Gamma', country: 'X' }
]

// Fit fixtures by epoch then city. C is unreliable at 2020, reliable at 2025.
const FITS: Record<number, Record<string, UrbanModelFitEntry | null>> = {
  2020: {
    A: { D0: 12000, beta: 0.2, r2: 0.95, reliable: true, fitted: [1] },
    B: { D0: 8000, beta: 0.1, r2: 0.6, reliable: true, fitted: [1] },
    C: { D0: 4000, beta: 0.04, r2: 0.1, reliable: false, fitted: null }
  },
  2025: {
    A: { D0: 12000, beta: 0.2, r2: 0.95, reliable: true, fitted: [1] },
    B: { D0: 8000, beta: 0.1, r2: 0.6, reliable: true, fitted: [1] },
    C: { D0: 6000, beta: 0.15, r2: 0.8, reliable: true, fitted: [1] }
  }
}

mockNuxtImport('useCitiesIndex', () => () => ({ allCities: ref(CITIES), isLoaded: ref(true) }))
mockNuxtImport('useCityPopulations', () => () => ({
  isLoaded: ref(true),
  getCityPopulationData: (id: string) => ({
    population: id === 'A' ? 3000000 : id === 'B' ? 2000000 : 1000000,
    area_km2: 200,
    density_per_km2: 5000
  })
}))
mockNuxtImport('useUrbanModelFit', () => () => ({
  getFit: (id: string, epoch: number) => FITS[epoch]?.[id] ?? null
}))
mockNuxtImport('useDataset', () => () => ({ hasFeatureComputed: () => ref(true) }))

async function mountRankings() {
  const CityRankings = (await import('../../app/components/rankings/CityRankings.vue')).default
  return mountSuspended(CityRankings)
}

beforeEach(() => {
  // Reset the shared singleton filter state.
  const f = useRankingFilters()
  f.activeStat.value = 'population'
  f.sortDirection.value = 'desc'
  f.countryFilter.value = ''
  f.compactnessFilter.value = [...COMPACTNESS_LABEL_VALUES]
  f.structureFilter.value = [...STRUCTURE_LABEL_VALUES]
  useSelectedYear().setYear(2020)
})

describe('CityRankings fit stats', () => {
  it('Covers AE3. Compactness sort excludes an unreliable city, included when reliable next epoch', async () => {
    useRankingFilters().activeStat.value = 'beta'
    const wrapper = await mountRankings()

    const text = wrapper.text()
    expect(text).toContain('Alpha')
    expect(text).toContain('Beta')
    expect(text).not.toContain('Gamma') // C unreliable at 2020 → excluded
    expect(text.indexOf('Alpha')).toBeLessThan(text.indexOf('Beta')) // 0.2 before 0.1

    // Scrub to an epoch where C is reliable.
    useSelectedYear().setYear(2025)
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Gamma')
  })

  it('sorts reliable cities by descending R²', async () => {
    useRankingFilters().activeStat.value = 'r2'
    const wrapper = await mountRankings()
    const text = wrapper.text()
    // A (0.95) before B (0.6); C excluded at 2020.
    expect(text.indexOf('Alpha')).toBeLessThan(text.indexOf('Beta'))
    expect(text).not.toContain('Gamma')
  })

  it('shows the explained silent-shrink affordance for fit sorts', async () => {
    useRankingFilters().activeStat.value = 'beta'
    const wrapper = await mountRankings()
    const note = wrapper.find('[data-testid="fit-stat-note"]')
    expect(note.exists()).toBe(true)
    expect(note.text()).toContain('Compactness (at 2020)')
    expect(note.text()).toContain('1 without a reliable fit hidden')
  })

  it('city-type filter narrows the list using the same thresholds as the badge', async () => {
    // Keep population sort; restrict compactness chips to "Compact" only.
    useRankingFilters().compactnessFilter.value = ['Compact']
    const wrapper = await mountRankings()
    const text = wrapper.text()
    expect(text).toContain('Alpha') // β 0.2 → Compact
    expect(text).not.toContain('Beta') // β 0.1 → Spread, filtered out
    expect(text).not.toContain('Gamma') // unreliable, no label
  })

  it('shows the empty-result state when no city matches the filters', async () => {
    useRankingFilters().compactnessFilter.value = [] // nothing selected → nothing matches
    const wrapper = await mountRankings()
    expect(wrapper.find('[data-testid="rankings-empty"]').exists()).toBe(true)
  })
})
