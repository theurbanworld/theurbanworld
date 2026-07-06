/**
 * Standard Urban Model fit data loading
 *
 * Loads urban_model_fit_h3_r8.json from R2 and provides per city-epoch access to
 * the fitted monocentric-exponential metrics (D0, beta, R^2), a reliability flag,
 * and the fitted curve for chart overlay.
 *
 * Data format: Record<city_id, Record<epoch, UrbanModelFitEntry>>
 * Mirrors useRadialProfiles: on-demand load, SSR-safe, 404 → empty.
 */

import type { YearEpoch } from '../../types/h3'

/** Fitted metrics for one city-epoch (mirrors the pipeline JSON export, U3). */
export interface UrbanModelFitEntry {
  /** Fitted central density (people/km²); null when the fit is undefined. */
  D0: number | null
  /** Fitted density gradient (1/km); null when the fit is undefined. */
  beta: number | null
  /** Goodness-of-fit R² on the original scale; null when the fit is undefined. */
  r2: number | null
  /** Whether the fit meets the reliability criteria. */
  reliable: boolean
  /** Model curve per ring (index = ring_index); null when reliable === false. */
  fitted: (number | null)[] | null
}

type UrbanModelFitData = Record<string, Record<string, UrbanModelFitEntry>>

export function useUrbanModelFit() {
  const runtimeConfig = useRuntimeConfig()

  function getDataUrl(): string {
    const r2BaseUrl = runtimeConfig.public.r2BaseUrl
    if (r2BaseUrl) {
      return `${r2BaseUrl}/data/urban_model_fit_h3_r8.json`
    }
    return 'https://data.theurban.world/data/urban_model_fit_h3_r8.json'
  }

  const { data, status, error, execute } = useAsyncData<UrbanModelFitData>(
    'urban-model-fit',
    async () => {
      try {
        return await $fetch<UrbanModelFitData>(getDataUrl())
      } catch (e: unknown) {
        if (e && typeof e === 'object' && 'statusCode' in e && e.statusCode === 404) {
          return {}
        }
        throw e
      }
    },
    {
      immediate: false,
      server: true,
      default: () => ({})
    }
  )

  const isLoading = computed(() => status.value === 'pending')
  const isLoaded = computed(() => status.value === 'success')

  /**
   * Get the fit entry for a city at a specific epoch.
   * Returns null when data is still loading or the city-epoch is absent.
   */
  function getFit(cityId: string, epoch: YearEpoch): UrbanModelFitEntry | null {
    if (!data.value) return null
    return data.value[cityId]?.[String(epoch)] ?? null
  }

  return {
    status: readonly(status),
    isLoading,
    isLoaded,
    error: readonly(error),
    execute,
    getFit
  }
}
