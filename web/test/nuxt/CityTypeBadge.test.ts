/**
 * Tests for CityTypeBadge (U7).
 *
 * Covers the three explicit states and AE1: scrubbing the epoch slider from a
 * reliable epoch to an unreliable one swaps the two labels for the honest-null note.
 */

import { describe, it, expect } from 'vitest'
import { ref } from 'vue'
import { mountSuspended, mockNuxtImport } from '@nuxt/test-utils/runtime'
import CityTypeBadge from '../../app/components/city/CityTypeBadge.vue'
import type { UrbanModelFitEntry } from '../../app/composables/useUrbanModelFit'

// Shared reactive epoch + fixture, driven per-test.
const selectedYear = ref(2020)

const FITS: Record<number, UrbanModelFitEntry | null> = {
  2020: { D0: 12000, beta: 0.5, r2: 0.95, reliable: true, fitted: [11000, 9000] },
  2025: { D0: 5000, beta: 0.05, r2: 0.15, reliable: false, fitted: null },
  1975: null // loading / absent
}

mockNuxtImport('useSelectedYear', () => () => ({ selectedYear }))
mockNuxtImport('useUrbanModelFit', () => () => ({
  getFit: (_cityId: string, epoch: number) => FITS[epoch] ?? null
}))

describe('CityTypeBadge', () => {
  it('shows both labels for a reliable city-epoch', async () => {
    selectedYear.value = 2020
    const wrapper = await mountSuspended(CityTypeBadge, { props: { cityId: '100' } })

    expect(wrapper.find('[data-testid="badge-compactness"]').text()).toBe('Compact')
    expect(wrapper.find('[data-testid="badge-structure"]').text()).toBe('Single-center')
    expect(wrapper.find('[data-testid="badge-note"]').exists()).toBe(false)
  })

  it('shows the neutral placeholder and no note while loading/absent', async () => {
    selectedYear.value = 1975
    const wrapper = await mountSuspended(CityTypeBadge, { props: { cityId: '100' } })

    expect(wrapper.find('[data-testid="badge-placeholder"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="badge-note"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="badge-compactness"]').exists()).toBe(false)
  })

  it('Covers AE1. Scrubbing from a reliable to an unreliable epoch swaps labels for the note', async () => {
    selectedYear.value = 2020
    const wrapper = await mountSuspended(CityTypeBadge, { props: { cityId: '100' } })
    expect(wrapper.find('[data-testid="badge-compactness"]').exists()).toBe(true)

    // Scrub to an unreliable epoch.
    selectedYear.value = 2025
    await wrapper.vm.$nextTick()

    expect(wrapper.find('[data-testid="badge-compactness"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="badge-structure"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="badge-note"]').text()).toBe('Fit not reliable here')
  })
})
