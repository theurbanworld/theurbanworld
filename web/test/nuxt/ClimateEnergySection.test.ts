/**
 * Integration tests for ClimateEnergySection (plan U7 + U8)
 *
 * Covers tiered layout, temporal-class dispatch, inline sector fingerprint,
 * per-metric unavailable states, modeled qualifier, and methodology modal links.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import ClimateEnergySection from '../../app/components/city/ClimateEnergySection.vue'
import { useInfoModal } from '../../app/composables/useInfoModal'
import { __clearClimateProfileCache } from '../../app/composables/useCityClimate'

const record100 = {
  heat_warm_days: { now: 30, future: 60 },
  flood_100yr_share: { points: [[1975, 0.05], [2030, 0.12]] },
  solar_pv_potential: { value: 1500 },
  co2_per_capita: { points: [[1975, 1], [2020, 4.2]] },
  co2_sector_fingerprint: {
    sectors: [['Energy', 4], ['Transport', 3], ['Industry', 2], ['Residential', 1]]
  },
  flood_coastal_lec: { points: [[1975, 0.1], [2030, 0.2]] }, // makes the flood group render
  greenness_built: { points: [[1985, 0.3], [2025, 0.5]] }
  // sea_level_rise intentionally absent -> marine metric unavailable
}

function stubFetch() {
  // Per-city profile fetch: climate/100.json -> record100; everything else 404.
  vi.stubGlobal('$fetch', vi.fn((url: string) => {
    if (url.includes('climate/100.json')) return Promise.resolve(record100)
    return Promise.reject({ statusCode: 404 })
  }))
}

async function mountSection(cityId: string) {
  const wrapper = mount(ClimateEnergySection, { props: { cityId } })
  await flushPromises()
  await flushPromises()
  return wrapper
}

describe('ClimateEnergySection', () => {
  beforeEach(() => {
    clearNuxtData('climate-summary')
    __clearClimateProfileCache()
    vi.unstubAllGlobals()
    useInfoModal().close()
  })

  it('renders headline four first, then collapsed lens groups', async () => {
    stubFetch()
    const wrapper = await mountSection('100')

    expect(wrapper.find('[data-testid="climate-energy-section"]').exists()).toBe(true)
    const headlines = wrapper.find('[data-testid="climate-headlines"]')
    expect(headlines.exists()).toBe(true)
    for (const key of ['heat_warm_days', 'flood_100yr_share', 'solar_pv_potential', 'co2_per_capita']) {
      expect(wrapper.find(`[data-metric="${key}"]`).exists()).toBe(true)
    }
    expect(wrapper.findAll('[data-testid="climate-metric-group"]').length).toBeGreaterThan(0)
  })

  it('renders the sector fingerprint alongside the per-capita CO₂ headline', async () => {
    stubFetch()
    const wrapper = await mountSection('100')
    expect(wrapper.find('[data-testid="sector-fingerprint"]').exists()).toBe(true)
  })

  it('dispatches each temporal class to its primitive', async () => {
    stubFetch()
    const wrapper = await mountSection('100')
    // projection -> toggle (heat); series -> native sparkline (flood/carbon)
    expect(wrapper.find('[data-testid="projection-value"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="native-axis-sparkline"]').exists()).toBe(true)
  })

  it('shows the modeled qualifier for modeled metrics', async () => {
    stubFetch()
    const wrapper = await mountSection('100')
    expect(wrapper.find('[data-testid="climate-metric-modeled"]').exists()).toBe(true)
  })

  it('shows the unavailable state for an absent marine metric while others render', async () => {
    stubFetch()
    const wrapper = await mountSection('100')
    const marine = wrapper.find('[data-metric="sea_level_rise"]')
    expect(marine.exists()).toBe(true)
    expect(marine.find('[data-testid="climate-metric-unavailable"]').exists()).toBe(true)
  })

  it('shows a whole-section unavailable note for an uncovered city', async () => {
    stubFetch()
    const wrapper = await mountSection('999')
    expect(wrapper.find('[data-testid="climate-section-unavailable"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="climate-headlines"]').exists()).toBe(false)
  })

  it('opens the methodology modal when a metric source is clicked', async () => {
    stubFetch()
    const wrapper = await mountSection('100')
    const source = wrapper.find('[data-metric="solar_pv_potential"] [data-testid="climate-metric-source"]')
    expect(source.exists()).toBe(true)
    await source.trigger('click')
    expect(useInfoModal().activePath.value).toBe('/data/source-solar-atlas')
  })
})
