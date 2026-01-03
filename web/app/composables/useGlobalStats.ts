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
 * Get trend display info based on percentage change
 *
 * Uses a single icon (i-lucide-move-right) rotated at 5 levels:
 * - Strong up: -40° rotation (emerald)
 * - Moderate up: -20° rotation (green)
 * - Stable: 0° rotation (gray)
 * - Moderate down: +20° rotation (amber)
 * - Strong down: +40° rotation (red)
 *
 * Thresholds:
 * - Strong up: >= 10%
 * - Moderate up: >= 5%
 * - Stable: -2% to 5%
 * - Moderate down: -5% to -2%
 * - Strong down: < -5%
 */
export function getTrendInfo(percentChange: number): TrendInfo {
  const icon = 'i-lucide-move-right'

  if (percentChange >= 10) {
    return { level: 'strong-up', icon, colorClass: 'text-emerald-600 dark:text-emerald-400', rotation: -40 }
  } else if (percentChange >= 5) {
    return { level: 'moderate-up', icon, colorClass: 'text-green-600 dark:text-green-400', rotation: -20 }
  } else if (percentChange > -2) {
    return { level: 'stable', icon, colorClass: 'text-gray-500 dark:text-gray-400', rotation: 0 }
  } else if (percentChange > -5) {
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
 * Urban population by epoch year
 * Source: Aggregated from city_populations.parquet
 */
const URBAN_POPULATION: Record<YearEpoch, number> = {
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
   * Raw urban population for selected year
   */
  const urbanPopulationRaw = computed(() => {
    return URBAN_POPULATION[selectedYear.value]
  })

  /**
   * Humanized urban population for display
   */
  const urbanPopulation = computed(() => {
    return humanizeNumber(urbanPopulationRaw.value)
  })

  /**
   * Calculate percentage change from previous epoch for urban population
   * Returns null if no previous epoch exists (at 1975)
   */
  const urbanPopulationTrendPrevious = computed((): number | null => {
    const currentIndex = YEAR_EPOCHS.indexOf(selectedYear.value)
    if (currentIndex <= 0) return null
    const prevYear = YEAR_EPOCHS[currentIndex - 1]!
    const prevValue = URBAN_POPULATION[prevYear]
    const currValue = URBAN_POPULATION[selectedYear.value]
    return ((currValue - prevValue) / prevValue) * 100
  })

  /**
   * Calculate percentage change to next epoch for urban population
   * Returns null if no next epoch exists (at 2030)
   */
  const urbanPopulationTrendNext = computed((): number | null => {
    const currentIndex = YEAR_EPOCHS.indexOf(selectedYear.value)
    if (currentIndex >= YEAR_EPOCHS.length - 1) return null
    const nextYear = YEAR_EPOCHS[currentIndex + 1]!
    const nextValue = URBAN_POPULATION[nextYear]
    const currValue = URBAN_POPULATION[selectedYear.value]
    return ((nextValue - currValue) / currValue) * 100
  })

  /**
   * Urban population as percentage of world population
   */
  const urbanPercentageOfWorld = computed((): number => {
    return calculatePercentage(urbanPopulationRaw.value, worldPopulationRaw.value)
  })

  return {
    /** Raw world population value */
    worldPopulationRaw,
    /** Humanized world population string (e.g., "8.2 billion") */
    worldPopulation,
    /** Raw urban population value */
    urbanPopulationRaw,
    /** Humanized urban population string (e.g., "3.6 billion") */
    urbanPopulation,
    /** Percentage change from previous epoch for urban population (null at 1975) */
    urbanPopulationTrendPrevious,
    /** Percentage change to next epoch for urban population (null at 2030) */
    urbanPopulationTrendNext,
    /** Urban population as percentage of world population */
    urbanPercentageOfWorld,
    /** Helper function to humanize numbers */
    humanizeNumber,
    /** Helper function to format exact numbers */
    formatExactNumber
  }
}
