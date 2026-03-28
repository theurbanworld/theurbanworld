/**
 * Shared ranking filter state
 *
 * Singleton state for the active stat and country filter,
 * shared between the filter controls (sidebar header) and
 * the rankings list (sidebar content).
 */

export type RankingStat = 'population' | 'density' | 'area' | 'growth'
export type SortDirection = 'desc' | 'asc'

const activeStat = ref<RankingStat>('population')
const countryFilter = ref('')
const sortDirection = ref<SortDirection>('desc')

export function useRankingFilters() {
  return {
    activeStat,
    countryFilter,
    sortDirection
  }
}
