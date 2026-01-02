/**
 * Selected year state management for H3 population visualization
 *
 * Provides centralized state for the currently selected year epoch.
 * Triggers H3 layer data updates when year changes.
 */

import { YEAR_EPOCHS, type YearEpoch } from '../../types/h3'

// Default year to display on initial load
const DEFAULT_YEAR: YearEpoch = 2025

// Singleton reactive state shared across composable instances
const selectedYear = ref<YearEpoch>(DEFAULT_YEAR)

export function useSelectedYear() {
  /**
   * Set the selected year
   * Validates that the year is a valid epoch before setting
   *
   * @param year - Year to select (must be a valid epoch)
   */
  function setYear(year: number) {
    // Validate that the year is a valid epoch
    if (YEAR_EPOCHS.includes(year as YearEpoch)) {
      selectedYear.value = year as YearEpoch
    } else {
      console.warn(`Invalid year epoch: ${year}. Valid epochs are: ${YEAR_EPOCHS.join(', ')}`)
    }
  }

  /**
   * Get the next year epoch (for animation/keyboard navigation)
   * Returns null if already at the last epoch
   */
  function getNextYear(): YearEpoch | null {
    const currentIndex = YEAR_EPOCHS.indexOf(selectedYear.value)
    if (currentIndex >= 0 && currentIndex < YEAR_EPOCHS.length - 1) {
      const nextYear = YEAR_EPOCHS[currentIndex + 1]
      return nextYear !== undefined ? nextYear : null
    }
    return null
  }

  /**
   * Get the previous year epoch (for animation/keyboard navigation)
   * Returns null if already at the first epoch
   */
  function getPreviousYear(): YearEpoch | null {
    const currentIndex = YEAR_EPOCHS.indexOf(selectedYear.value)
    if (currentIndex > 0) {
      const prevYear = YEAR_EPOCHS[currentIndex - 1]
      return prevYear !== undefined ? prevYear : null
    }
    return null
  }

  /**
   * Move to the next year epoch
   * Does nothing if already at the last epoch
   */
  function nextYear() {
    const next = getNextYear()
    if (next !== null) {
      selectedYear.value = next
    }
  }

  /**
   * Move to the previous year epoch
   * Does nothing if already at the first epoch
   */
  function previousYear() {
    const prev = getPreviousYear()
    if (prev !== null) {
      selectedYear.value = prev
    }
  }

  /**
   * Reset to the default year (2025)
   */
  function resetYear() {
    selectedYear.value = DEFAULT_YEAR
  }

  return {
    /** Currently selected year (readonly) */
    selectedYear: readonly(selectedYear),
    /** All available year epochs */
    yearEpochs: YEAR_EPOCHS,
    /** Set the selected year */
    setYear,
    /** Move to next year epoch */
    nextYear,
    /** Move to previous year epoch */
    previousYear,
    /** Reset to default year */
    resetYear
  }
}
