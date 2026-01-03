/**
 * Global population statistics by epoch
 *
 * Provides world population and urban population data for the selected year.
 * Data is stored as static TypeScript constants (not fetched from R2).
 */

import type { YearEpoch } from '../../types/h3'
import { useSelectedYear } from './useSelectedYear'

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

  return {
    /** Raw world population value */
    worldPopulationRaw,
    /** Humanized world population string (e.g., "8.2 billion") */
    worldPopulation,
    /** Raw urban population value */
    urbanPopulationRaw,
    /** Humanized urban population string (e.g., "3.6 billion") */
    urbanPopulation,
    /** Helper function to humanize numbers */
    humanizeNumber,
    /** Helper function to format exact numbers */
    formatExactNumber
  }
}
