/**
 * H3 hexagon data types
 *
 * Types for H3 population data loaded from parquet files.
 */

/**
 * Year epochs available in the population timeseries
 */
export const YEAR_EPOCHS = [
  1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025, 2030
] as const

export type YearEpoch = typeof YEAR_EPOCHS[number]

/**
 * Raw H3 hexagon record from parquet file
 * Contains h3_index as BigInt and population columns for each epoch
 */
export interface H3RawRecord {
  h3_index: bigint
  pop_1975: number | null
  pop_1980: number | null
  pop_1985: number | null
  pop_1990: number | null
  pop_1995: number | null
  pop_2000: number | null
  pop_2005: number | null
  pop_2010: number | null
  pop_2015: number | null
  pop_2020: number | null
  pop_2025: number | null
  pop_2030: number | null
}

/**
 * Processed H3 hexagon for deck.gl rendering
 * Uses hex string for h3_index (deck.gl format)
 */
export interface H3Hexagon {
  /** H3 index as hex string (e.g., "882a100001fffff") */
  h3Index: string
  /** Population value for the selected year */
  population: number
}

/**
 * Column name mapping for population by year
 */
export type PopulationColumnKey = `pop_${YearEpoch}`

/**
 * Get the population column key for a given year
 */
export function getPopulationColumnKey(year: YearEpoch): PopulationColumnKey {
  return `pop_${year}` as PopulationColumnKey
}

/**
 * Color as RGBA tuple for deck.gl
 */
export type RGBAColor = [number, number, number, number]
