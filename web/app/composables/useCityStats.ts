/**
 * City statistics composable
 *
 * Provides reactive city statistics including population, density, and area
 * that update based on the selected epoch year.
 *
 * Uses useCitiesIndex for city metadata and useCityPopulations for
 * epoch-specific population data with fallback to cities index data.
 */

import type { YearEpoch } from '../../types/h3'
import { useCitiesIndex } from './useCitiesIndex'
import { useCityPopulations } from './useCityPopulations'
import { useSelectedYear } from './useSelectedYear'
import { humanizeNumber, toAnnualRate, YEAR_EPOCHS } from './useGlobalStats'
import { formatDensity, formatArea } from '../utils/formatNumber'

/**
 * City statistics for the selected epoch
 */
export interface CityStats {
  /** Whether data is currently loading */
  isLoading: ComputedRef<boolean>
  /** Error if loading failed */
  error: ComputedRef<Error | undefined>
  /** City name from cities index */
  cityName: ComputedRef<string>
  /** Country name from cities index */
  countryName: ComputedRef<string>
  /** Raw population number for selected epoch */
  populationRaw: ComputedRef<number>
  /** Humanized population string (e.g., "42.6 million") */
  populationHumanized: ComputedRef<string>
  /** Area in km2 for selected epoch */
  area: ComputedRef<number>
  /** Formatted area with suffix (e.g., "6,420 km2") */
  areaFormatted: ComputedRef<string>
  /** Density (population / area) for selected epoch */
  density: ComputedRef<number>
  /** Formatted density (e.g., "6.6 K/km2") */
  densityFormatted: ComputedRef<string>
  /** Annualized population growth rate from previous epoch (null at 1975) */
  populationTrendPrevious: ComputedRef<number | null>
  /** Annualized population growth rate to next epoch (null at 2030) */
  populationTrendNext: ComputedRef<number | null>
  /** Annualized density growth rate from previous epoch (null at 1975) */
  densityTrendPrevious: ComputedRef<number | null>
  /** Annualized density growth rate to next epoch (null at 2030) */
  densityTrendNext: ComputedRef<number | null>
  /** Whether city data is available */
  isAvailable: ComputedRef<boolean>
  /** City bounding box [minx, miny, maxx, maxy] */
  bbox: ComputedRef<[number, number, number, number] | null>
}

/**
 * Get city statistics for a specific city
 *
 * Statistics are reactive and update when the selected epoch changes.
 * Falls back to cities index data if per-epoch population data is not available.
 *
 * @param cityId - City ID to get statistics for (reactive or string)
 * @returns Reactive city statistics
 */
export function useCityStats(cityId: MaybeRef<string>): CityStats {
  const citiesIndex = useCitiesIndex()
  const cityPopulations = useCityPopulations()
  const { selectedYear } = useSelectedYear()

  // Aggregate loading/error states from both data sources
  const isLoading = computed(() => citiesIndex.isLoading.value || cityPopulations.isLoading.value)
  const error = computed(() => citiesIndex.error.value || cityPopulations.error.value)

  // Convert cityId to a computed for reactivity
  const cityIdRef = computed(() => toValue(cityId))

  // Get city metadata from index
  const city = computed(() => citiesIndex.getCity(cityIdRef.value))

  // Check if city data is available
  const isAvailable = computed(() => city.value !== undefined)

  // City name from index
  const cityName = computed(() => city.value?.name ?? 'Unknown City')

  // Country name from index
  const countryName = computed(() => city.value?.country ?? 'Unknown')

  // Bounding box from index
  const bbox = computed((): [number, number, number, number] | null => {
    return city.value?.bbox ?? null
  })

  /**
   * Get population data for the current epoch
   * Falls back to cities index population (2025) if per-epoch data unavailable
   */
  const epochData = computed(() => {
    const popData = cityPopulations.getCityPopulationData(cityIdRef.value, selectedYear.value)
    if (popData) {
      return popData
    }

    // Fallback: use cities index population (assumed to be 2025 data)
    // Calculate approximate area from bbox if not available
    if (city.value) {
      const bboxData = city.value.bbox
      // Rough area calculation from bbox (not accurate but provides fallback)
      const width = bboxData[2] - bboxData[0]
      const height = bboxData[3] - bboxData[1]
      // Convert degrees to approximate km (at equator, 1 degree ~ 111 km)
      const avgLat = (bboxData[1] + bboxData[3]) / 2
      const latFactor = Math.cos(avgLat * Math.PI / 180)
      const widthKm = width * 111 * latFactor
      const heightKm = height * 111
      const area = widthKm * heightKm

      return {
        population: city.value.population,
        area_km2: area,
        density_per_km2: city.value.population / area
      }
    }

    return null
  })

  /**
   * Get population data for a specific epoch
   */
  function getEpochData(epoch: YearEpoch) {
    const popData = cityPopulations.getCityPopulationData(cityIdRef.value, epoch)
    if (popData) {
      return popData
    }

    // Fallback for missing epoch data
    if (city.value && epochData.value) {
      // Return current epoch data as approximation
      return epochData.value
    }
    return null
  }

  // Raw population for selected epoch
  const populationRaw = computed(() => {
    return epochData.value?.population ?? 0
  })

  // Humanized population
  const populationHumanized = computed(() => {
    return humanizeNumber(populationRaw.value)
  })

  // Area in km2
  const area = computed(() => {
    return epochData.value?.area_km2 ?? 0
  })

  // Formatted area
  const areaFormatted = computed(() => {
    return formatArea(area.value)
  })

  // Density (population / area)
  const density = computed(() => {
    return epochData.value?.density_per_km2 ?? 0
  })

  // Formatted density
  const densityFormatted = computed(() => {
    return formatDensity(density.value)
  })

  /**
   * Calculate annualized growth rate from previous epoch
   */
  const populationTrendPrevious = computed((): number | null => {
    const currentIndex = YEAR_EPOCHS.indexOf(selectedYear.value)
    if (currentIndex <= 0) return null

    const prevYear = YEAR_EPOCHS[currentIndex - 1]!
    const prevData = getEpochData(prevYear)
    const currData = epochData.value

    if (!prevData || !currData) return null

    const fiveYearRate = ((currData.population - prevData.population) / prevData.population) * 100
    return toAnnualRate(fiveYearRate)
  })

  /**
   * Calculate annualized growth rate to next epoch
   */
  const populationTrendNext = computed((): number | null => {
    const currentIndex = YEAR_EPOCHS.indexOf(selectedYear.value)
    if (currentIndex >= YEAR_EPOCHS.length - 1) return null

    const nextYear = YEAR_EPOCHS[currentIndex + 1]!
    const nextData = getEpochData(nextYear)
    const currData = epochData.value

    if (!nextData || !currData) return null

    const fiveYearRate = ((nextData.population - currData.population) / currData.population) * 100
    return toAnnualRate(fiveYearRate)
  })

  /**
   * Calculate annualized density growth rate from previous epoch
   */
  const densityTrendPrevious = computed((): number | null => {
    const currentIndex = YEAR_EPOCHS.indexOf(selectedYear.value)
    if (currentIndex <= 0) return null

    const prevYear = YEAR_EPOCHS[currentIndex - 1]!
    const prevData = getEpochData(prevYear)
    const currData = epochData.value

    if (!prevData || !currData) return null

    const fiveYearRate = ((currData.density_per_km2 - prevData.density_per_km2) / prevData.density_per_km2) * 100
    return toAnnualRate(fiveYearRate)
  })

  /**
   * Calculate annualized density growth rate to next epoch
   */
  const densityTrendNext = computed((): number | null => {
    const currentIndex = YEAR_EPOCHS.indexOf(selectedYear.value)
    if (currentIndex >= YEAR_EPOCHS.length - 1) return null

    const nextYear = YEAR_EPOCHS[currentIndex + 1]!
    const nextData = getEpochData(nextYear)
    const currData = epochData.value

    if (!nextData || !currData) return null

    const fiveYearRate = ((nextData.density_per_km2 - currData.density_per_km2) / currData.density_per_km2) * 100
    return toAnnualRate(fiveYearRate)
  })

  return {
    isLoading,
    error,
    cityName,
    countryName,
    populationRaw,
    populationHumanized,
    area,
    areaFormatted,
    density,
    densityFormatted,
    populationTrendPrevious,
    populationTrendNext,
    densityTrendPrevious,
    densityTrendNext,
    isAvailable,
    bbox
  }
}
