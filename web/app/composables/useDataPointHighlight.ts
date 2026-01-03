/**
 * Shared state for DataPoint cross-reference highlighting
 *
 * Enables DataPoints to highlight each other when hovering over
 * percentage labels that reference other DataPoints.
 */

/**
 * Composable for managing DataPoint highlight state
 */
export function useDataPointHighlight() {
  // Global state: which DataPoint ID is currently highlighted
  const highlightedId = useState<string | null>('datapoint-highlight', () => null)

  /**
   * Set the highlighted DataPoint ID
   * @param id - DataPoint ID to highlight, or null to clear
   */
  function setHighlight(id: string | null) {
    highlightedId.value = id
  }

  /**
   * Check if a specific DataPoint is currently highlighted
   * @param id - DataPoint ID to check
   * @returns Computed boolean indicating if this ID is highlighted
   */
  function isHighlighted(id: string) {
    return computed(() => highlightedId.value === id)
  }

  return {
    /** Currently highlighted DataPoint ID (or null) */
    highlightedId,
    /** Set the highlighted DataPoint ID */
    setHighlight,
    /** Check if a specific DataPoint ID is highlighted */
    isHighlighted
  }
}
