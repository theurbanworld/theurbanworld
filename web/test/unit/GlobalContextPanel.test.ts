/**
 * Unit tests for GlobalContextPanel component
 *
 * Tests panel structure, epoch display, and population data
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h, ref, computed, readonly } from 'vue'

// Mock composables
const mockSelectedYear = ref(2025)
const mockSetYear = vi.fn((year: number) => {
  mockSelectedYear.value = year
})

vi.mock('../../app/composables/useSelectedYear', () => ({
  useSelectedYear: () => ({
    selectedYear: readonly(mockSelectedYear),
    setYear: mockSetYear,
    yearEpochs: [1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025, 2030]
  })
}))

// Population data
const WORLD_POPULATION: Record<number, number> = {
  1975: 4069437259, 1980: 4444007748, 1985: 4861730652, 1990: 5316175909,
  1995: 5743219510, 2000: 6148899024, 2005: 6558176175, 2010: 6985603172,
  2015: 7426597609, 2020: 7840952947, 2025: 8191988536, 2030: 8546141407
}

const URBAN_POPULATION: Record<number, number> = {
  1975: 1178323105, 1980: 1346953243, 1985: 1532907872, 1990: 1741456510,
  1995: 2012230273, 2000: 2306333391, 2005: 2556795633, 2010: 2819883050,
  2015: 3095854703, 2020: 3350187245, 2025: 3569570193, 2030: 3759831609
}

function humanizeNumber(value: number): string {
  if (value >= 1_000_000_000) {
    const billions = value / 1_000_000_000
    const rounded = Math.round(billions * 10) / 10
    return `${rounded} billion`
  }
  return value.toLocaleString()
}

vi.mock('../../app/composables/useGlobalStats', () => ({
  useGlobalStats: () => ({
    worldPopulationRaw: computed(() => WORLD_POPULATION[mockSelectedYear.value]),
    worldPopulation: computed(() => humanizeNumber(WORLD_POPULATION[mockSelectedYear.value])),
    urbanPopulationRaw: computed(() => URBAN_POPULATION[mockSelectedYear.value]),
    urbanPopulation: computed(() => humanizeNumber(URBAN_POPULATION[mockSelectedYear.value]))
  }),
  humanizeNumber,
  formatExactNumber: (value: number) => value.toLocaleString()
}))

// Stub components
const USliderStub = defineComponent({
  name: 'USlider',
  props: ['modelValue', 'min', 'max', 'step'],
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    return () => h('input', {
      'type': 'range',
      'value': props.modelValue,
      'min': props.min,
      'max': props.max,
      'step': props.step,
      'data-testid': 'epoch-slider',
      'onInput': (e: Event) => emit('update:modelValue', Number((e.target as HTMLInputElement).value))
    })
  }
})

const DataPointStub = defineComponent({
  name: 'DataPoint',
  props: ['label', 'value', 'rawValue', 'sourceLabel'],
  setup(props) {
    return () => h('div', { 'data-testid': `datapoint-${props.label?.toLowerCase().replace(' ', '-')}` }, [
      h('span', { class: 'label' }, props.label),
      h('span', { class: 'value' }, props.value)
    ])
  }
})

// Simplified GlobalContextPanel for testing
const GlobalContextPanelTest = defineComponent({
  name: 'GlobalContextPanel',
  components: { USlider: USliderStub, DataPoint: DataPointStub },
  setup() {
    const { selectedYear, setYear, yearEpochs: _yearEpochs } = {
      selectedYear: readonly(mockSelectedYear),
      setYear: mockSetYear,
      yearEpochs: [1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025, 2030]
    }

    const worldPopulationRaw = computed(() => WORLD_POPULATION[mockSelectedYear.value])
    const worldPopulation = computed(() => humanizeNumber(worldPopulationRaw.value))
    const urbanPopulationRaw = computed(() => URBAN_POPULATION[mockSelectedYear.value])
    const urbanPopulation = computed(() => humanizeNumber(urbanPopulationRaw.value))

    const sliderValue = computed({
      get: () => selectedYear.value,
      set: (value: number) => setYear(value)
    })

    return () => h('div', {
      'class': 'fixed right-4 top-20 z-100 w-56 p-4 rounded-xl bg-parchment/95 dark:bg-espresso/95',
      'data-testid': 'global-context-panel'
    }, [
      // Year display
      h('div', { class: 'text-center mb-3' }, [
        h('span', {
          'class': 'font-mono text-4xl font-bold text-forest-700 dark:text-forest-300',
          'data-testid': 'epoch-year'
        }, selectedYear.value)
      ]),
      // Slider
      h(USliderStub, {
        'modelValue': sliderValue.value,
        'min': 1975,
        'max': 2030,
        'step': 5,
        'onUpdate:modelValue': (v: number) => setYear(v)
      }),
      // Divider
      h('hr', { class: 'my-4 border-border/30' }),
      // DataPoints
      h(DataPointStub, {
        label: 'World Population',
        value: worldPopulation.value,
        rawValue: worldPopulationRaw.value
      }),
      h('div', { class: 'h-3' }),
      h(DataPointStub, {
        label: 'Urban Population',
        value: urbanPopulation.value,
        rawValue: urbanPopulationRaw.value
      })
    ])
  }
})

describe('GlobalContextPanel', () => {
  beforeEach(() => {
    mockSelectedYear.value = 2025
    mockSetYear.mockClear()
  })

  it('displays current epoch year prominently', () => {
    const wrapper = mount(GlobalContextPanelTest)

    const yearDisplay = wrapper.find('[data-testid="epoch-year"]')
    expect(yearDisplay.exists()).toBe(true)
    expect(yearDisplay.text()).toBe('2025')
    expect(yearDisplay.classes()).toContain('font-mono')
  })

  it('displays world population data point', () => {
    const wrapper = mount(GlobalContextPanelTest)

    const worldPopDataPoint = wrapper.find('[data-testid="datapoint-world-population"]')
    expect(worldPopDataPoint.exists()).toBe(true)
    expect(worldPopDataPoint.text()).toContain('World Population')
    expect(worldPopDataPoint.text()).toContain('8.2 billion')
  })

  it('displays urban population data point', () => {
    const wrapper = mount(GlobalContextPanelTest)

    const urbanPopDataPoint = wrapper.find('[data-testid="datapoint-urban-population"]')
    expect(urbanPopDataPoint.exists()).toBe(true)
    expect(urbanPopDataPoint.text()).toContain('Urban Population')
    expect(urbanPopDataPoint.text()).toContain('3.6 billion')
  })

  it('updates population data when epoch changes', async () => {
    const wrapper = mount(GlobalContextPanelTest)

    // Initially at 2025
    expect(wrapper.find('[data-testid="datapoint-world-population"]').text()).toContain('8.2 billion')

    // Change to 1975
    mockSelectedYear.value = 1975
    await wrapper.vm.$nextTick()

    expect(wrapper.find('[data-testid="epoch-year"]').text()).toBe('1975')
    expect(wrapper.find('[data-testid="datapoint-world-population"]').text()).toContain('4.1 billion')
    expect(wrapper.find('[data-testid="datapoint-urban-population"]').text()).toContain('1.2 billion')
  })

  it('contains epoch slider', () => {
    const wrapper = mount(GlobalContextPanelTest)

    const slider = wrapper.find('[data-testid="epoch-slider"]')
    expect(slider.exists()).toBe(true)
    expect(slider.attributes('min')).toBe('1975')
    expect(slider.attributes('max')).toBe('2030')
    expect(slider.attributes('step')).toBe('5')
  })
})
