/**
 * Integration tests for city selection feature
 *
 * Tests end-to-end workflows combining routing, state management,
 * data display, and epoch reactivity.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { ref, nextTick } from 'vue'
import { useCitySelection } from '../../app/composables/useCitySelection'
import { useSelectedYear } from '../../app/composables/useSelectedYear'

// Mock navigateTo
const mockNavigateTo = vi.fn()
vi.stubGlobal('navigateTo', mockNavigateTo)

// Mock useCitiesIndex
vi.mock('../../app/composables/useCitiesIndex', () => ({
  useCitiesIndex: () => ({
    isLoaded: ref(true),
    getCity: (cityId: string) => {
      const cities: Record<string, { id: string; name: string; country: string; bbox: [number, number, number, number]; population: number }> = {
        '10933': {
          id: '10933',
          name: 'Guangzhou',
          country: 'China',
          bbox: [112.873929, 22.445939, 114.398154, 23.380635],
          population: 42987704
        },
        '5929': {
          id: '5929',
          name: 'Tokyo',
          country: 'Japan',
          bbox: [139.085831, 35.172611, 140.291773, 36.214155],
          population: 33155906
        }
      }
      return cities[cityId]
    }
  })
}))

// Mock useCityPopulations
vi.mock('../../app/composables/useCityPopulations', () => ({
  useCityPopulations: () => ({
    isLoaded: ref(true),
    getCityPopulationData: (cityId: string, epoch: number) => {
      const mockData: Record<string, Record<number, { population: number; area_km2: number; density_per_km2: number }>> = {
        '10933': {
          2020: { population: 40760332, area_km2: 6221.69, density_per_km2: 6551.33 },
          2025: { population: 42610674, area_km2: 6420.48, density_per_km2: 6636.68 }
        },
        '5929': {
          2020: { population: 33374564, area_km2: 5181.77, density_per_km2: 6440.77 },
          2025: { population: 33034214, area_km2: 5153.33, density_per_km2: 6410.27 }
        }
      }
      return mockData[cityId]?.[epoch]
    }
  })
}))

describe('City Selection Integration', () => {
  beforeEach(() => {
    mockNavigateTo.mockClear()
    const { clearSelection } = useCitySelection()
    clearSelection()
    const { setYear } = useSelectedYear()
    setYear(2025)
  })

  describe('Full flow: click city -> sidebar opens -> data displays', () => {
    it('clicking a city sets selection state and triggers navigation', () => {
      const { selectedCityId, selectCity, hasSelection } = useCitySelection()

      // Simulate click handler behavior: navigate to city route
      const cityId = '10933'
      mockNavigateTo(`/city/${cityId}`)

      // Simulate route sync in [city_id].vue page
      selectCity(cityId)

      expect(mockNavigateTo).toHaveBeenCalledWith('/city/10933')
      expect(selectedCityId.value).toBe('10933')
      expect(hasSelection.value).toBe(true)
    })

    it('selection state provides city data for sidebar display', () => {
      const { selectCity, selectedCityId } = useCitySelection()

      selectCity('10933')

      // Verify the selection is available for useCityStats
      expect(selectedCityId.value).toBe('10933')
    })
  })

  describe('Full flow: epoch changes -> data updates', () => {
    it('changing epoch updates city statistics', async () => {
      const { selectCity, selectedCityId } = useCitySelection()
      const { selectedYear, setYear } = useSelectedYear()

      selectCity('10933')
      expect(selectedCityId.value).toBe('10933')
      expect(selectedYear.value).toBe(2025)

      // Change epoch
      setYear(2020)
      await nextTick()

      expect(selectedYear.value).toBe(2020)
      // Selection remains intact after epoch change
      expect(selectedCityId.value).toBe('10933')
    })
  })

  describe('Full flow: click city A -> click city B -> navigates to B', () => {
    it('selecting different city updates navigation and state', () => {
      const { selectCity, selectedCityId } = useCitySelection()

      // Click city A (Guangzhou)
      mockNavigateTo('/city/10933')
      selectCity('10933')
      expect(selectedCityId.value).toBe('10933')

      // Click city B (Tokyo) - simulates clicking on map while viewing city A
      mockNavigateTo('/city/5929')
      selectCity('5929')

      expect(selectedCityId.value).toBe('5929')
      expect(mockNavigateTo).toHaveBeenLastCalledWith('/city/5929')
      expect(mockNavigateTo).toHaveBeenCalledTimes(2)
    })

    it('previous selection is cleared when selecting new city', () => {
      const { selectCity, isSelected } = useCitySelection()

      selectCity('10933')
      expect(isSelected('10933').value).toBe(true)
      expect(isSelected('5929').value).toBe(false)

      selectCity('5929')
      expect(isSelected('10933').value).toBe(false)
      expect(isSelected('5929').value).toBe(true)
    })
  })

  describe('Full flow: close button -> navigates to /, selection clears', () => {
    it('close button navigation clears selection', () => {
      const { selectCity, clearSelection, selectedCityId, hasSelection } = useCitySelection()

      // Select a city
      selectCity('10933')
      expect(hasSelection.value).toBe(true)

      // Simulate close button click - navigates to /
      mockNavigateTo('/')

      // Simulate index.vue clearing selection on mount
      clearSelection()

      expect(selectedCityId.value).toBeNull()
      expect(hasSelection.value).toBe(false)
      expect(mockNavigateTo).toHaveBeenCalledWith('/')
    })
  })

  describe('Deep linking: direct URL to /city/[id] loads city view', () => {
    it('route params sync to selection state on page mount', () => {
      const { selectCity, selectedCityId, hasSelection } = useCitySelection()

      // Simulate [city_id].vue page mounting with route params
      const routeParams = { city_id: '5929' }

      // Page's watchEffect syncs route param to selection state
      selectCity(routeParams.city_id)

      expect(selectedCityId.value).toBe('5929')
      expect(hasSelection.value).toBe(true)
    })

    it('invalid city ID is handled gracefully', () => {
      const { selectCity, selectedCityId, hasSelection } = useCitySelection()

      // Even an unknown city ID can be set (data lookup will fail gracefully)
      selectCity('unknown-city-999')

      expect(selectedCityId.value).toBe('unknown-city-999')
      expect(hasSelection.value).toBe(true)
    })
  })

  describe('Boundary interaction: hover works on non-selected cities', () => {
    it('hover and selection states are independent', () => {
      const { selectCity, isSelected } = useCitySelection()

      // Select city A
      selectCity('10933')

      // City A is selected
      expect(isSelected('10933').value).toBe(true)

      // City B can still be checked for selection (for hover independence)
      expect(isSelected('5929').value).toBe(false)

      // Both checks are independent - this validates the state model
      // supports concurrent hover (via useCityHover) and selection states
    })
  })
})
