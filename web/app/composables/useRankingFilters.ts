/**
 * Shared ranking filter state
 *
 * Singleton state for the active stat and country filter,
 * shared between the filter controls (sidebar header) and
 * the rankings list (sidebar content).
 */

export type RankingStat = 'population' | 'density' | 'area'

const activeStat = ref<RankingStat>('population')
const countryFilter = ref('')

export function useRankingFilters() {
  return {
    activeStat,
    countryFilter
  }
}
