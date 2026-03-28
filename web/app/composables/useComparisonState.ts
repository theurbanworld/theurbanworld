/**
 * Comparison state management
 *
 * Parses the comparison route parameter (e.g., "123+456") into two city IDs,
 * validates them against the cities index, and provides reactive state
 * for the comparison view.
 *
 * Handles canonical URL ordering (lower ID first), same-city redirects,
 * and invalid ID detection.
 */

export interface ComparisonParsed {
  /** Lower city ID (left map) */
  cityA: string
  /** Higher city ID (right map) */
  cityB: string
}

export interface ComparisonRedirect {
  type: 'canonical' | 'same-city'
  target: string
}

/**
 * Parse a comparison route parameter into two city IDs.
 *
 * @param pair - Route parameter string (e.g., "123+456")
 * @returns Parsed city IDs, redirect info, or null if invalid
 */
export function parseComparisonParam(pair: string): {
  parsed: ComparisonParsed | null
  redirect: ComparisonRedirect | null
  error: string | null
} {
  if (!pair || !pair.includes('+')) {
    return { parsed: null, redirect: null, error: 'Missing separator' }
  }

  const parts = pair.split('+')
  if (parts.length !== 2) {
    return { parsed: null, redirect: null, error: 'Invalid format' }
  }

  const [rawA, rawB] = parts as [string, string]

  // Validate both are numeric
  if (!/^\d+$/.test(rawA) || !/^\d+$/.test(rawB)) {
    return { parsed: null, redirect: null, error: 'Non-numeric city ID' }
  }

  // Same city — redirect to single city view
  if (rawA === rawB) {
    return {
      parsed: null,
      redirect: { type: 'same-city', target: `/city/${rawA}` },
      error: null
    }
  }

  // Canonical ordering — lower numeric ID first
  const numA = parseInt(rawA, 10)
  const numB = parseInt(rawB, 10)
  const [idA, idB] = numA < numB ? [rawA, rawB] : [rawB, rawA]

  if (idA !== rawA || idB !== rawB) {
    return {
      parsed: null,
      redirect: { type: 'canonical', target: `/compare/${idA}+${idB}` },
      error: null
    }
  }

  return {
    parsed: { cityA: idA, cityB: idB },
    redirect: null,
    error: null
  }
}

export function useComparisonState() {
  const route = useRoute()
  const { isLoaded, hasCity } = useCitiesIndex()

  // Parse the route parameter reactively
  const pairParam = computed(() => {
    const p = route.params.pair
    return Array.isArray(p) ? p[0] : p
  })

  const parseResult = computed(() => {
    if (!pairParam.value) {
      return { parsed: null, redirect: null, error: 'No pair parameter' }
    }
    return parseComparisonParam(pairParam.value)
  })

  // Expose parsed city IDs (null until validated)
  const cityA = computed(() => parseResult.value.parsed?.cityA ?? null)
  const cityB = computed(() => parseResult.value.parsed?.cityB ?? null)

  // Validation against the cities index (only after index loads)
  const isValid = computed(() => {
    if (!parseResult.value.parsed) return false
    if (!isLoaded.value) return false
    return hasCity(parseResult.value.parsed.cityA) && hasCity(parseResult.value.parsed.cityB)
  })

  // Whether we're still waiting for the index to validate
  const isLoading = computed(() => {
    return !!parseResult.value.parsed && !isLoaded.value
  })

  // Whether both IDs are present but at least one is unknown
  const hasInvalidCities = computed(() => {
    if (!parseResult.value.parsed) return false
    if (!isLoaded.value) return false
    return !hasCity(parseResult.value.parsed.cityA) || !hasCity(parseResult.value.parsed.cityB)
  })

  // Redirect target (canonical reorder or same-city)
  const redirect = computed(() => parseResult.value.redirect)

  // Parse error (missing separator, non-numeric, etc.)
  const parseError = computed(() => parseResult.value.error)

  return {
    /** City A ID (lower numeric, left map) */
    cityA,
    /** City B ID (higher numeric, right map) */
    cityB,
    /** Whether both city IDs are valid and found in the index */
    isValid,
    /** Whether we're waiting for the cities index to validate */
    isLoading,
    /** Whether parsed IDs exist but are not in the cities index */
    hasInvalidCities,
    /** Redirect info if URL needs rewriting */
    redirect,
    /** Parse error message if the URL format is wrong */
    parseError
  }
}
