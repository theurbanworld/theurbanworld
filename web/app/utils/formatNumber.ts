/**
 * Number formatting utilities
 *
 * Provides consistent number formatting throughout the app.
 * Includes compact notation (1.2M, 543K) and locale-aware formatting.
 */

/**
 * Format a number in compact notation (7.2M, 149.7K)
 *
 * Always shows one decimal place for M and K values.
 *
 * Examples:
 * - 1,234,567 → "1.2M"
 * - 12,345,678 → "12.3M"
 * - 543,210 → "543.2K"
 * - 54,321 → "54.3K"
 * - 5,432 → "5.4K"
 * - 543 → "543"
 */
export function formatCompactNumber(num: number): string {
  if (num >= 1_000_000) {
    const millions = num / 1_000_000
    return `${millions.toFixed(1)}M`
  }
  if (num >= 1_000) {
    const thousands = num / 1_000
    return `${thousands.toFixed(1)}K`
  }
  // Below 1000, show full number with locale separators
  return num.toLocaleString()
}

/**
 * Format a number with locale-specific thousand separators
 *
 * Examples:
 * - 1234567 → "1,234,567" (en-US)
 * - 1234567 → "1.234.567" (de-DE)
 */
export function formatNumber(num: number): string {
  return num.toLocaleString()
}

/**
 * Format a population number for display
 * Alias for formatCompactNumber, specifically for population values
 */
export function formatPopulation(population: number): string {
  return formatCompactNumber(population)
}
