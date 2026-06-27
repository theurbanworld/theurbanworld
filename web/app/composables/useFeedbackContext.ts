/**
 * useFeedbackContext — best-effort page-context capture for feedback
 *
 * Gathers the current page URL plus best-effort app state (city / dataset /
 * epoch) into a plain, JSON-serializable object for the submission payload.
 * Absence of any field (e.g. no city selected) must never throw or block.
 *
 * The assembly logic lives in the pure buildFeedbackContext() so it can be
 * unit-tested without a DOM or the singleton composables (mirrors the pure
 * parseComparisonParam helper in useComparisonState).
 */

export interface FeedbackContext {
  /** Always present — the page the user submitted from. */
  url: string
  /** Present only when a city is selected; name omitted if unresolved. */
  city?: { id: string, name?: string }
  /** Active dataset display label (e.g. "Urban World v1"). */
  dataset?: string
  /** Selected year epoch. */
  epoch?: number
}

export interface FeedbackContextInput {
  url: string
  cityId?: string | null
  cityName?: string
  dataset?: string
  epoch?: number
}

/**
 * Assemble a feedback context, omitting any field that isn't resolvable.
 * Pure and side-effect free.
 */
export function buildFeedbackContext(input: FeedbackContextInput): FeedbackContext {
  const ctx: FeedbackContext = { url: input.url }

  if (input.cityId) {
    ctx.city = input.cityName
      ? { id: input.cityId, name: input.cityName }
      : { id: input.cityId }
  }

  if (input.dataset) {
    ctx.dataset = input.dataset
  }

  if (typeof input.epoch === 'number') {
    ctx.epoch = input.epoch
  }

  return ctx
}

export function useFeedbackContext() {
  const { selectedCityId } = useCitySelection()
  const { getCityName } = useCitiesIndex()
  const { activeDatasetLabel } = useDataset()
  const { selectedYear } = useSelectedYear()

  /**
   * Capture the current page context. Best-effort: any field other than
   * `url` may be absent, and resolution never throws.
   */
  function captureContext(): FeedbackContext {
    const cityId = selectedCityId.value
    return buildFeedbackContext({
      url: window.location.href,
      cityId,
      cityName: cityId ? getCityName(cityId) : undefined,
      dataset: activeDatasetLabel.value,
      epoch: selectedYear.value
    })
  }

  return { captureContext }
}
