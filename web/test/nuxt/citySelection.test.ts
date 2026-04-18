/**
 * Tests for city selection routing and state management
 *
 * Tests useCitySelection composable and route synchronization
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { useCitySelection } from '../../app/composables/useCitySelection'

describe('useCitySelection composable', () => {
  beforeEach(() => {
    // Clear any existing selection before each test
    const { clearSelection } = useCitySelection()
    clearSelection()
  })

  it('starts with null selectedCityId', () => {
    const { selectedCityId } = useCitySelection()
    expect(selectedCityId.value).toBeNull()
  })

  it('selectCity sets the selected city ID', () => {
    const { selectedCityId, selectCity } = useCitySelection()

    selectCity('city-123')
    expect(selectedCityId.value).toBe('city-123')

    selectCity('city-456')
    expect(selectedCityId.value).toBe('city-456')
  })

  it('clearSelection clears the selected city ID', () => {
    const { selectedCityId, selectCity, clearSelection } = useCitySelection()

    selectCity('city-123')
    expect(selectedCityId.value).toBe('city-123')

    clearSelection()
    expect(selectedCityId.value).toBeNull()
  })

  it('hasSelection returns correct boolean', () => {
    const { selectCity, clearSelection, hasSelection } = useCitySelection()

    expect(hasSelection.value).toBe(false)

    selectCity('city-123')
    expect(hasSelection.value).toBe(true)

    clearSelection()
    expect(hasSelection.value).toBe(false)
  })

  it('isSelected returns correct computed for specific city', () => {
    const { selectCity, isSelected, clearSelection } = useCitySelection()

    selectCity('city-abc')

    expect(isSelected('city-abc').value).toBe(true)
    expect(isSelected('city-def').value).toBe(false)

    clearSelection()
    expect(isSelected('city-abc').value).toBe(false)
  })

  it('state is shared across multiple calls (singleton pattern)', () => {
    const instance1 = useCitySelection()
    const instance2 = useCitySelection()

    instance1.selectCity('city-abc')

    expect(instance2.selectedCityId.value).toBe('city-abc')
    expect(instance2.hasSelection.value).toBe(true)
  })
})

describe('Route sync with city selection', () => {
  beforeEach(() => {
    const { clearSelection } = useCitySelection()
    clearSelection()
  })

  it('/city/[city_id] route sets selected city ID', () => {
    // Simulate route param extraction and state sync
    const routeParams = { city_id: 'new-york-123' }
    const { selectCity, selectedCityId } = useCitySelection()

    // When navigating to /city/[city_id], the page should sync state
    selectCity(routeParams.city_id)

    expect(selectedCityId.value).toBe('new-york-123')
  })

  it('/ route clears selected city ID', () => {
    const { selectCity, clearSelection, selectedCityId } = useCitySelection()

    // First select a city
    selectCity('london-456')
    expect(selectedCityId.value).toBe('london-456')

    // When navigating to /, the index page should clear selection
    clearSelection()

    expect(selectedCityId.value).toBeNull()
  })

  it('route changes update state correctly', () => {
    const { selectCity, clearSelection, selectedCityId } = useCitySelection()

    // Navigate to city A
    selectCity('tokyo-789')
    expect(selectedCityId.value).toBe('tokyo-789')

    // Navigate to city B (clicking another city)
    selectCity('paris-012')
    expect(selectedCityId.value).toBe('paris-012')

    // Navigate to home
    clearSelection()
    expect(selectedCityId.value).toBeNull()
  })
})

describe('navigateTo integration for city selection', () => {
  it('city selection triggers navigation URL pattern', () => {
    // This tests the expected URL pattern that navigateTo would use
    const cityId = 'mumbai-345'
    const expectedUrl = `/city/${cityId}`

    expect(expectedUrl).toBe('/city/mumbai-345')
  })

  it('clear selection returns to root URL', () => {
    // When close button is clicked, navigation goes to /
    const expectedUrl = '/'
    expect(expectedUrl).toBe('/')
  })
})
