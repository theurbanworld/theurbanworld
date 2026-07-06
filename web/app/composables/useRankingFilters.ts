/**
 * Shared ranking filter state
 *
 * Singleton state for the active stat, country filter, and the Standard Urban Model
 * city-type filter, shared between the filter controls (sidebar header) and the
 * rankings list (sidebar content).
 */

import {
  COMPACTNESS_LABEL_VALUES,
  STRUCTURE_LABEL_VALUES,
  type CompactnessLabel,
  type StructureLabel
} from '~/utils/urbanModelLabels'

export type RankingStat = 'population' | 'density' | 'area' | 'growth' | 'beta' | 'r2'
export type GrowthMode = 'rate' | 'abs'
export type SortDirection = 'desc' | 'asc'

const activeStat = ref<RankingStat>('population')
const growthMode = ref<GrowthMode>('abs')
const countryFilter = ref('')
const sortDirection = ref<SortDirection>('desc')

// City-type filter: multi-select chips, all selected by default (no constraint).
const compactnessFilter = ref<CompactnessLabel[]>([...COMPACTNESS_LABEL_VALUES])
const structureFilter = ref<StructureLabel[]>([...STRUCTURE_LABEL_VALUES])

export function useRankingFilters() {
  return {
    activeStat,
    growthMode,
    countryFilter,
    sortDirection,
    compactnessFilter,
    structureFilter
  }
}
