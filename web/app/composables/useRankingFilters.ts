/**
 * Shared ranking filter state
 *
 * Singleton state for the active stat and country filter,
 * shared between the filter controls (sidebar header) and
 * the rankings list (sidebar content).
 */

import {
  HEAT_HEADLINE_KEY,
  FLOOD_HEADLINE_KEY,
  SOLAR_HEADLINE_KEY,
  CARBON_HEADLINE_KEY,
  type HeadlineKey
} from '../../types/climate'

export type ClimateRankingStat = 'climate_heat' | 'climate_flood' | 'climate_solar' | 'climate_carbon'
export type RankingStat = 'population' | 'density' | 'area' | 'growth' | ClimateRankingStat
export type GrowthMode = 'rate' | 'abs'
export type SortDirection = 'desc' | 'asc'

/** Maps a climate ranking stat to the headline metric key it ranks on. */
export const CLIMATE_STAT_KEYS: Record<ClimateRankingStat, HeadlineKey> = {
  climate_heat: HEAT_HEADLINE_KEY,
  climate_flood: FLOOD_HEADLINE_KEY,
  climate_solar: SOLAR_HEADLINE_KEY,
  climate_carbon: CARBON_HEADLINE_KEY
}

export function isClimateStat(stat: RankingStat): stat is ClimateRankingStat {
  return stat in CLIMATE_STAT_KEYS
}

const activeStat = ref<RankingStat>('population')
const growthMode = ref<GrowthMode>('abs')
const countryFilter = ref('')
const sortDirection = ref<SortDirection>('desc')

export function useRankingFilters() {
  return {
    activeStat,
    growthMode,
    countryFilter,
    sortDirection
  }
}
