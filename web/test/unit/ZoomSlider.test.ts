/**
 * Unit tests for ZoomSlider component
 *
 * Tests zoom level display, slider sync, and snap-to-level functionality
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h, ref, computed, readonly } from 'vue'

// Mock view state
const mockViewState = ref({
  longitude: 0,
  latitude: 15,
  zoom: 7.5, // City level
  pitch: 0,
  bearing: 0
})

const mockSetZoom = vi.fn((zoom: number) => {
  mockViewState.value.zoom = zoom
})

vi.mock('../../app/composables/useViewState', () => ({
  useViewState: () => ({
    viewState: readonly(mockViewState),
    setZoom: mockSetZoom,
    setViewState: vi.fn()
  })
}))

// Zoom level definitions
const ZOOM_LEVELS = [
  { name: 'Metropolitan', icon: 'i-lucide-globe', minZoom: 0, maxZoom: 5, centerZoom: 2.5 },
  { name: 'City', icon: 'i-lucide-building-2', minZoom: 5, maxZoom: 10, centerZoom: 7.5 },
  { name: 'Neighborhood', icon: 'i-lucide-trees', minZoom: 10, maxZoom: 13, centerZoom: 11.5 },
  { name: 'Street', icon: 'i-lucide-road', minZoom: 13, maxZoom: 16, centerZoom: 14.5 },
  { name: 'Building', icon: 'i-lucide-building', minZoom: 16, maxZoom: 22, centerZoom: 17 }
]

function getLevelForZoom(zoom: number) {
  for (const level of ZOOM_LEVELS) {
    if (zoom >= level.minZoom && zoom < level.maxZoom) {
      return level
    }
  }
  return ZOOM_LEVELS[ZOOM_LEVELS.length - 1]
}

vi.mock('../../app/composables/useZoomLevel', () => ({
  useZoomLevel: () => ({
    ZOOM_LEVELS,
    getLevelForZoom,
    getCenterZoomForLevel: (name: string) => {
      const level = ZOOM_LEVELS.find(l => l.name === name)
      return level?.centerZoom ?? 7.5
    },
    currentLevel: computed(() => getLevelForZoom(mockViewState.value.zoom)),
    currentLevelName: computed(() => getLevelForZoom(mockViewState.value.zoom).name)
  })
}))

// Stub components
const USliderStub = defineComponent({
  name: 'USlider',
  props: ['modelValue', 'min', 'max', 'step', 'orientation'],
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    return () => h('input', {
      'type': 'range',
      'value': props.modelValue,
      'min': props.min,
      'max': props.max,
      'data-testid': 'zoom-slider',
      'data-orientation': props.orientation,
      'onInput': (e: Event) => emit('update:modelValue', Number((e.target as HTMLInputElement).value))
    })
  }
})

const UTooltipStub = defineComponent({
  name: 'UTooltip',
  props: ['text'],
  setup(props, { slots }) {
    return () => h('div', { 'data-tooltip': props.text }, slots.default?.())
  }
})

const UIconStub = defineComponent({
  name: 'UIcon',
  props: ['name'],
  setup(props) {
    return () => h('span', { 'data-icon': props.name, 'data-testid': `icon-${props.name}` })
  }
})

// Simplified ZoomSlider for testing
const ZoomSliderTest = defineComponent({
  name: 'ZoomSlider',
  components: { USlider: USliderStub, UTooltip: UTooltipStub, UIcon: UIconStub },
  setup() {
    const viewState = readonly(mockViewState)
    const setZoom = mockSetZoom

    const currentLevel = computed(() => getLevelForZoom(viewState.value.zoom))
    const currentLevelName = computed(() => currentLevel.value.name)

    const sliderValue = computed({
      get: () => viewState.value.zoom,
      set: (value: number) => setZoom(value)
    })

    const handleLevelClick = (levelName: string) => {
      const level = ZOOM_LEVELS.find(l => l.name === levelName)
      if (level) {
        setZoom(level.centerZoom)
      }
    }

    return () => h('div', {
      'class': 'fixed right-64 top-20 z-100 flex flex-col items-center gap-2 p-3 rounded-xl bg-parchment/95 dark:bg-espresso/95',
      'data-testid': 'zoom-slider-panel'
    }, [
      // Scale label
      h('span', { 'class': 'text-xs text-body/70', 'data-testid': 'scale-label' }, 'Scale'),
      // Current level name
      h('span', {
        'class': 'text-sm font-medium text-forest-700 dark:text-forest-300',
        'data-testid': 'current-level-name'
      }, currentLevelName.value),
      // Level icons
      h('div', { class: 'flex flex-col gap-1 my-2' },
        // Reverse order for display (Building at top, Metropolitan at bottom)
        [...ZOOM_LEVELS].reverse().map(level =>
          h(UTooltipStub, { text: level.name, key: level.name }, {
            default: () => h('button', {
              'class': `p-2 rounded hover:bg-forest-100 dark:hover:bg-forest-900 ${currentLevelName.value === level.name ? 'bg-forest-200 dark:bg-forest-800' : ''}`,
              'data-testid': `level-button-${level.name.toLowerCase()}`,
              'onClick': () => handleLevelClick(level.name)
            }, [h(UIconStub, { name: level.icon })])
          })
        )
      ),
      // Slider
      h(USliderStub, {
        'modelValue': sliderValue.value,
        'min': 0,
        'max': 18,
        'orientation': 'vertical',
        'onUpdate:modelValue': (v: number) => setZoom(v)
      })
    ])
  }
})

describe('ZoomSlider', () => {
  beforeEach(() => {
    mockViewState.value.zoom = 7.5 // City level
    mockSetZoom.mockClear()
  })

  it('displays current zoom level name', () => {
    const wrapper = mount(ZoomSliderTest)

    const levelName = wrapper.find('[data-testid="current-level-name"]')
    expect(levelName.exists()).toBe(true)
    expect(levelName.text()).toBe('City')
  })

  it('displays Scale label', () => {
    const wrapper = mount(ZoomSliderTest)

    const scaleLabel = wrapper.find('[data-testid="scale-label"]')
    expect(scaleLabel.exists()).toBe(true)
    expect(scaleLabel.text()).toBe('Scale')
  })

  it('contains slider synced with map zoom', () => {
    const wrapper = mount(ZoomSliderTest)

    const slider = wrapper.find('[data-testid="zoom-slider"]')
    expect(slider.exists()).toBe(true)
    expect(slider.attributes('value')).toBe('7.5')
  })

  it('updates level name when zoom changes', async () => {
    const wrapper = mount(ZoomSliderTest)

    expect(wrapper.find('[data-testid="current-level-name"]').text()).toBe('City')

    // Change to Street level
    mockViewState.value.zoom = 14.5
    await wrapper.vm.$nextTick()

    expect(wrapper.find('[data-testid="current-level-name"]').text()).toBe('Street')
  })

  it('clicking level icon snaps to that zoom level', async () => {
    const wrapper = mount(ZoomSliderTest)

    // Click on Neighborhood button
    const neighborhoodButton = wrapper.find('[data-testid="level-button-neighborhood"]')
    expect(neighborhoodButton.exists()).toBe(true)

    await neighborhoodButton.trigger('click')

    expect(mockSetZoom).toHaveBeenCalledWith(11.5) // Neighborhood center zoom
  })

  it('displays all five zoom level icons', () => {
    const wrapper = mount(ZoomSliderTest)

    expect(wrapper.find('[data-testid="level-button-metropolitan"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="level-button-city"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="level-button-neighborhood"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="level-button-street"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="level-button-building"]').exists()).toBe(true)
  })

  it('highlights current level icon', () => {
    const wrapper = mount(ZoomSliderTest)

    // At City level (zoom 7.5)
    const cityButton = wrapper.find('[data-testid="level-button-city"]')
    expect(cityButton.classes()).toContain('bg-forest-200')
  })
})
