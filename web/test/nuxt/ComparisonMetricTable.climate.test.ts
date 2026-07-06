/**
 * Tests for climate rows in ComparisonMetricTable (plan U10)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import ComparisonMetricTable from '../../app/components/compare/ComparisonMetricTable.vue'

const summary = {
  100: {
    heat_warm_days: 30,
    flood_100yr_share: 0.1,
    solar_pv_potential: 1500,
    co2_per_capita: 4.2
  },
  200: { solar_pv_potential: 1320 } // partial: only solar
}

function stubFetch() {
  // Return the climate summary for the climate URL; empty for everything else.
  vi.stubGlobal('$fetch', vi.fn((url: string) =>
    Promise.resolve(url.includes('climate_summary') ? summary : [])
  ))
}

async function mountTable(a: string, b: string) {
  const wrapper = mount(ComparisonMetricTable, { props: { cityIdA: a, cityIdB: b } })
  await flushPromises()
  await flushPromises()
  return wrapper
}

describe('ComparisonMetricTable (climate)', () => {
  beforeEach(() => {
    clearNuxtData('climate-summary')
    clearNuxtData('climate-profile')
    vi.unstubAllGlobals()
  })

  it('shows headline climate rows when both cities are covered', async () => {
    stubFetch()
    const wrapper = await mountTable('100', '200')
    const text = wrapper.text()
    expect(text).toContain('Solar PV potential')
    expect(text).toContain('1,500 kWh/kWp')
    expect(text).toContain('1,320 kWh/kWp')
  })

  it('shows N/A for the uncovered side of a one-sided metric', async () => {
    stubFetch()
    const wrapper = await mountTable('100', '200')
    const text = wrapper.text()
    // city 200 has no warm-days value -> N/A
    expect(text).toContain('Warm days (TX90p)')
    expect(text).toContain('N/A')
  })

  it('hides a headline row when neither city is covered for it', async () => {
    stubFetch()
    // both cities only have solar -> heat/flood/carbon rows hidden
    const wrapper = await mountTable('200', '200')
    const text = wrapper.text()
    expect(text).toContain('Solar PV potential')
    expect(text).not.toContain('Warm days (TX90p)')
    expect(text).not.toContain('Per-capita CO₂')
  })
})
