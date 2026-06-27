/**
 * Tests for the Standard Urban Model fit metric in CityInfoPanel (U8).
 *
 * Verifies the R² headline (with β / D₀ detail) for a reliable city-epoch, the
 * honest-null dash for an unreliable one, and reactivity to the epoch slider.
 */

import { describe, it, expect, vi } from 'vitest'
import { ref, computed } from 'vue'
import { mountSuspended, mockNuxtImport } from '@nuxt/test-utils/runtime'
import type { UrbanModelFitEntry } from '../../app/composables/useUrbanModelFit'

const selectedYear = ref(2020)

const FITS: Record<number, UrbanModelFitEntry | null> = {
  2020: { D0: 12000, beta: 0.182, r2: 0.95, reliable: true, fitted: [11000, 9000] },
  2025: { D0: 5000, beta: 0.05, r2: 0.15, reliable: false, fitted: null }
}

mockNuxtImport('useSelectedYear', () => () => ({ selectedYear }))
mockNuxtImport('useUrbanModelFit', () => () => ({
  getFit: (_cityId: string, epoch: number) => FITS[epoch] ?? null
}))

// CityInfoPanel imports useCityStats / useDataset explicitly (relative path).
vi.mock('../../app/composables/useCityStats', () => ({
  useCityStats: () => ({
    isLoading: ref(false),
    error: ref(null),
    cityName: ref('Testville'),
    countryName: ref('Testland'),
    populationRaw: ref(1000000),
    populationHumanized: ref('1.0M'),
    populationTrendPrevious: ref(null),
    populationTrendNext: ref(null),
    density: ref(5000),
    densityFormatted: ref('5 K/km2'),
    densityTrendPrevious: ref(null),
    densityTrendNext: ref(null),
    area: ref(200),
    areaFormatted: ref('200 km2'),
    birthYear: ref(1975),
    deathYear: ref(null),
    isPreCity: ref(false),
    isActiveCity: ref(true),
    cityStateMessage: ref('')
  })
}))

vi.mock('../../app/composables/useDataset', () => ({
  useDataset: () => ({ hasFeatureComputed: () => computed(() => true) })
}))

const STUBS = {
  EpochSparkline: true,
  DistributionStrip: true,
  PopulationHeatmapSection: true,
  RadialProfileSection: true,
  CompareSearchModal: true,
  CityTypeBadge: true,
  // UTooltip (reka-ui) needs a TooltipProvider ancestor absent in a bare mount.
  UTooltip: { template: '<div><slot /></div>' },
  UIcon: { template: '<span />' }
}

async function mountPanel() {
  const CityInfoPanel = (await import('../../app/components/city/CityInfoPanel.vue')).default
  return mountSuspended(CityInfoPanel, {
    props: { cityId: '100' },
    global: { stubs: STUBS }
  })
}

describe('CityInfoPanel model-fit metric', () => {
  it('shows formatted R² and β / D₀ for a reliable city-epoch', async () => {
    selectedYear.value = 2020
    const wrapper = await mountPanel()

    const dp = wrapper.find('[data-testid="model-fit-datapoint"]')
    expect(dp.exists()).toBe(true)
    expect(dp.find('[data-testid="datapoint-value"]').text()).toBe('0.95')

    const detail = dp.find('[data-testid="model-fit-detail"]').text()
    expect(detail).toContain('β 0.182')
    expect(detail).toContain('D₀')
  })

  it('shows a dash and a not-reliable note for an unreliable city-epoch', async () => {
    selectedYear.value = 2025
    const wrapper = await mountPanel()

    const dp = wrapper.find('[data-testid="model-fit-datapoint"]')
    expect(dp.find('[data-testid="datapoint-value"]').text()).toBe('—')
    const detail = dp.find('[data-testid="model-fit-detail"]').text()
    expect(detail).toContain('Fit not reliable at this epoch')
    expect(detail).not.toContain('β')
  })

  it('updates the metric when the epoch changes', async () => {
    selectedYear.value = 2020
    const wrapper = await mountPanel()
    expect(wrapper.find('[data-testid="model-fit-datapoint"] [data-testid="datapoint-value"]').text()).toBe('0.95')

    selectedYear.value = 2025
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-testid="model-fit-datapoint"] [data-testid="datapoint-value"]').text()).toBe('—')
  })
})
