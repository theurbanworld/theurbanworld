/**
 * Tests for city statistics composable
 *
 * Tests useCityStats composable for city population, density, area,
 * and trend calculations with epoch reactivity.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { ref, nextTick } from 'vue'
import { useCityStats } from '../../app/composables/useCityStats'
import { useSelectedYear } from '../../app/composables/useSelectedYear'

// Mock the useCitiesIndex composable
vi.mock('../../app/composables/useCitiesIndex', () => ({
  useCitiesIndex: () => ({
    isLoaded: ref(true),
    isLoading: ref(false),
    error: ref(null),
    loadIndex: vi.fn(),
    getCity: (cityId: string) => {
      // Mock city data for testing
      const mockCities: Record<string, { id: string, name: string, country: string, country_code: string, centroid: [number, number], bbox: [number, number, number, number], population: number }> = {
        10933: {
          id: '10933',
          name: 'Guangzhou',
          country: 'China',
          country_code: 'CHN',
          centroid: [113.606742, 22.881047],
          bbox: [112.873929, 22.445939, 114.398154, 23.380635],
          population: 42987704
        },
        5929: {
          id: '5929',
          name: 'Tokyo',
          country: 'Japan',
          country_code: 'JPN',
          centroid: [139.653618, 35.66459],
          bbox: [139.085831, 35.172611, 140.291773, 36.214155],
          population: 33155906
        }
      }
      return mockCities[cityId]
    },
    getCityName: (cityId: string) => {
      const names: Record<string, string> = { 10933: 'Guangzhou', 5929: 'Tokyo' }
      return names[cityId]
    },
    hasCity: (cityId: string) => ['10933', '5929'].includes(cityId)
  })
}))

// Mock useCityPopulations composable
vi.mock('../../app/composables/useCityPopulations', () => ({
  useCityPopulations: () => ({
    isLoaded: ref(true),
    isLoading: ref(false),
    error: ref(null),
    loadData: vi.fn(),
    getCityPopulationData: (cityId: string, epoch: number) => {
      // Mock population data for testing (based on actual data structure)
      const mockData: Record<string, Record<number, { population: number, area_km2: number, density_per_km2: number }>> = {
        10933: {
          1975: { population: 1986150, area_km2: 390.26, density_per_km2: 5089.30 },
          1980: { population: 2737324, area_km2: 587.71, density_per_km2: 4657.60 },
          1985: { population: 3633898, area_km2: 779.96, density_per_km2: 4659.06 },
          1990: { population: 5586632, area_km2: 1258.76, density_per_km2: 4438.21 },
          1995: { population: 12500992, area_km2: 2913.71, density_per_km2: 4290.41 },
          2000: { population: 27309888, area_km2: 4804.61, density_per_km2: 5684.10 },
          2005: { population: 32605514, area_km2: 5445.49, density_per_km2: 5987.61 },
          2010: { population: 36255260, area_km2: 5766.25, density_per_km2: 6287.49 },
          2015: { population: 38410885, area_km2: 6071.76, density_per_km2: 6326.15 },
          2020: { population: 40760332, area_km2: 6221.69, density_per_km2: 6551.33 },
          2025: { population: 42610674, area_km2: 6420.48, density_per_km2: 6636.68 },
          2030: { population: 43986518, area_km2: 6492.52, density_per_km2: 6774.96 }
        },
        5929: {
          1975: { population: 23909742, area_km2: 4541.90, density_per_km2: 5264.26 },
          1980: { population: 25667611, area_km2: 4649.62, density_per_km2: 5520.37 },
          1985: { population: 27197684, area_km2: 4695.64, density_per_km2: 5792.12 },
          1990: { population: 28585453, area_km2: 4776.30, density_per_km2: 5984.85 },
          1995: { population: 29081569, area_km2: 4865.27, density_per_km2: 5977.39 },
          2000: { population: 30171090, area_km2: 4922.21, density_per_km2: 6129.58 },
          2005: { population: 31274585, area_km2: 5030.17, density_per_km2: 6217.40 },
          2010: { population: 32437505, area_km2: 5095.89, density_per_km2: 6365.42 },
          2015: { population: 33053051, area_km2: 5141.04, density_per_km2: 6429.26 },
          2020: { population: 33374564, area_km2: 5181.77, density_per_km2: 6440.77 },
          2025: { population: 33034214, area_km2: 5153.33, density_per_km2: 6410.27 },
          2030: { population: 32558951, area_km2: 5089.71, density_per_km2: 6397.02 }
        }
      }
      return mockData[cityId]?.[epoch]
    },
    hasData: () => true
  })
}))

describe('useCityStats', () => {
  beforeEach(() => {
    // Reset year to default before each test
    const { setYear } = useSelectedYear()
    setYear(2025)
  })

  describe('population lookup by city_id and epoch year', () => {
    it('returns correct population for a city at 2025 epoch', () => {
      const { setYear } = useSelectedYear()
      setYear(2025)

      const { populationRaw } = useCityStats('10933')

      // Guangzhou 2025 population
      expect(populationRaw.value).toBe(42610674)
    })

    it('returns correct population for a different city', () => {
      const { setYear } = useSelectedYear()
      setYear(2025)

      const { populationRaw } = useCityStats('5929')

      // Tokyo 2025 population
      expect(populationRaw.value).toBe(33034214)
    })

    it('returns correct population for historical epoch', () => {
      const { setYear } = useSelectedYear()
      setYear(1975)

      const { populationRaw } = useCityStats('10933')

      // Guangzhou 1975 population
      expect(populationRaw.value).toBe(1986150)
    })
  })

  describe('density calculation (population / area)', () => {
    it('returns correct density for a city', () => {
      const { setYear } = useSelectedYear()
      setYear(2025)

      const { density } = useCityStats('10933')

      // Guangzhou 2025 density: ~6636.68/km2
      expect(density.value).toBeCloseTo(6636.68, 0)
    })

    it('formats density correctly for high values', () => {
      const { setYear } = useSelectedYear()
      setYear(2025)

      const { densityFormatted } = useCityStats('10933')

      // Should be formatted as "6.6 K/km2"
      expect(densityFormatted.value).toMatch(/^\d+\.?\d* K\/km2$/)
    })
  })

  describe('epoch reactivity: changing selectedYear updates stats', () => {
    it('updates population when epoch changes', async () => {
      const { setYear } = useSelectedYear()
      setYear(2025)

      const { populationRaw } = useCityStats('10933')
      expect(populationRaw.value).toBe(42610674)

      // Change to 2020
      setYear(2020)
      await nextTick()

      expect(populationRaw.value).toBe(40760332)
    })

    it('updates density when epoch changes', async () => {
      const { setYear } = useSelectedYear()
      setYear(2025)

      const { density } = useCityStats('10933')
      expect(density.value).toBeCloseTo(6636.68, 0)

      // Change to 1975
      setYear(1975)
      await nextTick()

      expect(density.value).toBeCloseTo(5089.30, 0)
    })

    it('updates area when epoch changes', async () => {
      const { setYear } = useSelectedYear()
      setYear(2025)

      const { area } = useCityStats('10933')
      expect(area.value).toBeCloseTo(6420.48, 0)

      // Change to 1975 (smaller urban area)
      setYear(1975)
      await nextTick()

      expect(area.value).toBeCloseTo(390.26, 0)
    })
  })

  describe('trend calculation (previous/next epoch growth rates)', () => {
    it('calculates annualized population trend from previous epoch', () => {
      const { setYear } = useSelectedYear()
      setYear(2025)

      const { populationTrendPrevious } = useCityStats('10933')

      // 2020->2025: (42610674 - 40760332) / 40760332 * 100 = 4.54% over 5 years
      // Annualized: ~0.89%
      expect(populationTrendPrevious.value).toBeCloseTo(0.89, 1)
    })

    it('calculates annualized population trend to next epoch', () => {
      const { setYear } = useSelectedYear()
      setYear(2025)

      const { populationTrendNext } = useCityStats('10933')

      // 2025->2030: (43986518 - 42610674) / 42610674 * 100 = 3.23% over 5 years
      // Annualized: ~0.64%
      expect(populationTrendNext.value).toBeCloseTo(0.64, 1)
    })

    it('returns null for trendPrevious at first epoch (1975)', () => {
      const { setYear } = useSelectedYear()
      setYear(1975)

      const { populationTrendPrevious } = useCityStats('10933')
      expect(populationTrendPrevious.value).toBeNull()
    })

    it('returns null for trendNext at last epoch (2030)', () => {
      const { setYear } = useSelectedYear()
      setYear(2030)

      const { populationTrendNext } = useCityStats('10933')
      expect(populationTrendNext.value).toBeNull()
    })

    it('calculates density trend from previous epoch', () => {
      const { setYear } = useSelectedYear()
      setYear(2025)

      const { densityTrendPrevious } = useCityStats('10933')

      // 2020->2025: (6636.68 - 6551.33) / 6551.33 * 100 = 1.30% over 5 years
      // Annualized: ~0.26%
      expect(densityTrendPrevious.value).toBeCloseTo(0.26, 1)
    })
  })

  describe('humanization of population values', () => {
    it('humanizes large population values correctly', () => {
      const { setYear } = useSelectedYear()
      setYear(2025)

      const { populationHumanized } = useCityStats('10933')

      // 42.6 million
      expect(populationHumanized.value).toBe('42.6 million')
    })

    it('humanizes smaller population values correctly', () => {
      const { setYear } = useSelectedYear()
      setYear(1975)

      const { populationHumanized } = useCityStats('10933')

      // 2 million (1986150)
      expect(populationHumanized.value).toBe('2 million')
    })
  })

  describe('city metadata from cities index', () => {
    it('returns city name from index', () => {
      const { cityName } = useCityStats('10933')
      expect(cityName.value).toBe('Guangzhou')
    })

    it('returns country name from index', () => {
      const { countryName } = useCityStats('10933')
      expect(countryName.value).toBe('China')
    })

    it('returns area with formatted suffix', () => {
      const { setYear } = useSelectedYear()
      setYear(2025)

      const { areaFormatted } = useCityStats('10933')
      expect(areaFormatted.value).toMatch(/km2$/)
    })
  })
})
