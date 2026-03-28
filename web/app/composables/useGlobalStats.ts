/**
 * Global population statistics by epoch
 *
 * Provides world population and urban population data for the selected year.
 * Data is stored as static TypeScript constants (not fetched from R2).
 */

import type { YearEpoch } from '../../types/h3'
import { useSelectedYear } from './useSelectedYear'

/**
 * Ordered list of epoch years for trend calculations
 */
export const YEAR_EPOCHS: YearEpoch[] = [1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025, 2030]

/**
 * Trend magnitude levels for visual indicators
 */
export type TrendLevel = 'strong-up' | 'moderate-up' | 'stable' | 'moderate-down' | 'strong-down'

/**
 * Trend display information including icon, color, and rotation
 */
export interface TrendInfo {
  level: TrendLevel
  icon: string
  colorClass: string
  /** Rotation in degrees (-66 to 66) for visual angle */
  rotation: number
}

/**
 * Get trend display info based on annualized percentage change
 *
 * Uses a single icon (i-lucide-move-right) rotated at 5 levels:
 * - Strong up: -40° rotation (emerald)
 * - Moderate up: -20° rotation (green)
 * - Stable: 0° rotation (gray)
 * - Moderate down: +20° rotation (amber)
 * - Strong down: +40° rotation (red)
 *
 * Thresholds (annualized rates):
 * - Strong up: >= 2%
 * - Moderate up: >= 1%
 * - Stable: -0.4% to 1%
 * - Moderate down: -1% to -0.4%
 * - Strong down: < -1%
 */
export function getTrendInfo(percentChange: number): TrendInfo {
  const icon = 'i-lucide-move-right'

  if (percentChange >= 2) {
    return { level: 'strong-up', icon, colorClass: 'text-emerald-600 dark:text-emerald-400', rotation: -40 }
  } else if (percentChange >= 1) {
    return { level: 'moderate-up', icon, colorClass: 'text-green-600 dark:text-green-400', rotation: -20 }
  } else if (percentChange > -0.4) {
    return { level: 'stable', icon, colorClass: 'text-gray-500 dark:text-gray-400', rotation: 0 }
  } else if (percentChange > -1) {
    return { level: 'moderate-down', icon, colorClass: 'text-amber-600 dark:text-amber-400', rotation: 20 }
  } else {
    return { level: 'strong-down', icon, colorClass: 'text-red-600 dark:text-red-400', rotation: 40 }
  }
}

/**
 * Calculate percentage of part relative to whole
 * Returns value rounded to one decimal place (e.g., 43.6)
 */
export function calculatePercentage(part: number, whole: number): number {
  if (whole === 0) return 0
  return Math.round((part / whole) * 1000) / 10
}

/**
 * Convert a 5-year percentage change to annualized rate (CAGR)
 * E.g., 6.55% over 5 years → ~1.27% per year
 */
export function toAnnualRate(fiveYearPercent: number): number {
  return (Math.pow(1 + fiveYearPercent / 100, 1 / 5) - 1) * 100
}

/**
 * World population by epoch year
 * Source: GHSL Table 20 - UN WPP 2022 calibrated (from pipeline WORLD_POPULATION constant)
 */
const WORLD_POPULATION: Record<YearEpoch, number> = {
  1975: 4069437259,
  1980: 4444007748,
  1985: 4861730652,
  1990: 5316175909,
  1995: 5743219510,
  2000: 6148899024,
  2005: 6558176175,
  2010: 6985603172,
  2015: 7426597609,
  2020: 7840952947,
  2025: 8191988536,
  2030: 8546141407
}

/**
 * UN official urban population by epoch year
 * Source: UN World Urbanization Prospects via World Bank (indicator SP.URB.TOTL)
 * Uses national statistical definitions of "urban" — higher than satellite-derived totals
 * 1975-2020 from World Bank; 2025/2030 interpolated from UN WUP 2025 medium-variant
 */
const UN_URBAN_POPULATION: Record<YearEpoch, number> = {
  1975: 1531287659,
  1980: 1751930824,
  1985: 2007728628,
  1990: 2269739806,
  1995: 2541965823,
  2000: 2886168967,
  2005: 3245690391,
  2010: 3623784825,
  2015: 4050109267,
  2020: 4378993944,
  2025: 4693031052,
  2030: 5028207672
}

/**
 * Dataset urban population by epoch year
 * Source: Aggregated from city_populations.parquet (satellite-derived city boundaries)
 * Represents the urban population we can see and measure — a subset of the UN total
 */
const DATASET_URBAN_POPULATION: Record<YearEpoch, number> = {
  1975: 1178323105,
  1980: 1346953243,
  1985: 1532907872,
  1990: 1741456510,
  1995: 2012230273,
  2000: 2306333391,
  2005: 2556795633,
  2010: 2819883050,
  2015: 3095854703,
  2020: 3350187245,
  2025: 3569570193,
  2030: 3759831609
}

/**
 * Humanize a large number for display
 * Converts raw numbers to readable format like "8.2 billion"
 *
 * @param value - Raw numeric value
 * @returns Humanized string representation
 */
export function humanizeNumber(value: number): string {
  if (value >= 1_000_000_000) {
    const billions = value / 1_000_000_000
    // Round to one decimal place
    const rounded = Math.round(billions * 10) / 10
    return `${rounded} billion`
  } else if (value >= 1_000_000) {
    const millions = value / 1_000_000
    const rounded = Math.round(millions * 10) / 10
    return `${rounded} million`
  } else if (value >= 1_000) {
    const thousands = value / 1_000
    const rounded = Math.round(thousands * 10) / 10
    return `${rounded} thousand`
  }
  return value.toLocaleString()
}

/**
 * Format a number with locale-aware thousand separators
 *
 * @param value - Raw numeric value
 * @returns Formatted string with thousand separators
 */
export function formatExactNumber(value: number): string {
  return value.toLocaleString()
}

export function useGlobalStats() {
  const { selectedYear } = useSelectedYear()

  /**
   * Raw world population for selected year
   */
  const worldPopulationRaw = computed(() => {
    return WORLD_POPULATION[selectedYear.value]
  })

  /**
   * Humanized world population for display
   */
  const worldPopulation = computed(() => {
    return humanizeNumber(worldPopulationRaw.value)
  })

  /**
   * Annualized growth rate from previous epoch for world population
   * Returns null if no previous epoch exists (at 1975)
   */
  const worldPopulationTrendPrevious = computed((): number | null => {
    const currentIndex = YEAR_EPOCHS.indexOf(selectedYear.value)
    if (currentIndex <= 0) return null
    const prevYear = YEAR_EPOCHS[currentIndex - 1]!
    const prevValue = WORLD_POPULATION[prevYear]
    const currValue = WORLD_POPULATION[selectedYear.value]
    const fiveYearRate = ((currValue - prevValue) / prevValue) * 100
    return toAnnualRate(fiveYearRate)
  })

  /**
   * Annualized growth rate to next epoch for world population
   * Returns null if no next epoch exists (at 2030)
   */
  const worldPopulationTrendNext = computed((): number | null => {
    const currentIndex = YEAR_EPOCHS.indexOf(selectedYear.value)
    if (currentIndex >= YEAR_EPOCHS.length - 1) return null
    const nextYear = YEAR_EPOCHS[currentIndex + 1]!
    const nextValue = WORLD_POPULATION[nextYear]
    const currValue = WORLD_POPULATION[selectedYear.value]
    const fiveYearRate = ((nextValue - currValue) / currValue) * 100
    return toAnnualRate(fiveYearRate)
  })

  // --- UN official urban population ---

  const urbanPopulationRaw = computed(() => {
    return UN_URBAN_POPULATION[selectedYear.value]
  })

  const urbanPopulation = computed(() => {
    return humanizeNumber(urbanPopulationRaw.value)
  })

  const urbanPopulationTrendPrevious = computed((): number | null => {
    const currentIndex = YEAR_EPOCHS.indexOf(selectedYear.value)
    if (currentIndex <= 0) return null
    const prevYear = YEAR_EPOCHS[currentIndex - 1]!
    const prevValue = UN_URBAN_POPULATION[prevYear]
    const currValue = UN_URBAN_POPULATION[selectedYear.value]
    const fiveYearRate = ((currValue - prevValue) / prevValue) * 100
    return toAnnualRate(fiveYearRate)
  })

  const urbanPopulationTrendNext = computed((): number | null => {
    const currentIndex = YEAR_EPOCHS.indexOf(selectedYear.value)
    if (currentIndex >= YEAR_EPOCHS.length - 1) return null
    const nextYear = YEAR_EPOCHS[currentIndex + 1]!
    const nextValue = UN_URBAN_POPULATION[nextYear]
    const currValue = UN_URBAN_POPULATION[selectedYear.value]
    const fiveYearRate = ((nextValue - currValue) / currValue) * 100
    return toAnnualRate(fiveYearRate)
  })

  const urbanPercentageOfWorld = computed((): number => {
    return calculatePercentage(urbanPopulationRaw.value, worldPopulationRaw.value)
  })

  // --- Dataset urban population (our measured coverage) ---

  const datasetUrbanPopulationRaw = computed(() => {
    return DATASET_URBAN_POPULATION[selectedYear.value]
  })

  const datasetUrbanPopulation = computed(() => {
    return humanizeNumber(datasetUrbanPopulationRaw.value)
  })

  return {
    // World population
    worldPopulationRaw,
    worldPopulation,
    worldPopulationTrendPrevious,
    worldPopulationTrendNext,
    // UN official urban population (headline number)
    urbanPopulationRaw,
    urbanPopulation,
    urbanPopulationTrendPrevious,
    urbanPopulationTrendNext,
    urbanPercentageOfWorld,
    // Dataset urban population (our measured coverage)
    datasetUrbanPopulationRaw,
    datasetUrbanPopulation,
    // Utilities
    humanizeNumber,
    formatExactNumber
  }
}
