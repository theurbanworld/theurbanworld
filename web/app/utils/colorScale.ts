/**
 * Logarithmic color scale for population density visualization
 *
 * Maps population values to a 6-step sepia gradient using logarithmic scale.
 * Light mode: cream (low) to deep brown (high)
 * Dark mode: inverted - deep brown (low) to cream (high)
 */

/**
 * Color as RGBA tuple for deck.gl
 */
export type RGBAColor = [number, number, number, number]

/**
 * 6-step sepia gradient colors (light mode)
 * From low density (cream) to high density (deep brown)
 */
const SEPIA_GRADIENT_LIGHT: readonly RGBAColor[] = [
  [247, 243, 232, 255], // #F7F3E8 - Level 1: Cream (very low)
  [232, 220, 200, 255], // #E8DCC8 - Level 2: Warm sand (low)
  [212, 196, 168, 255], // #D4C4A8 - Level 3: Tan (medium-low)
  [184, 159, 114, 255], // #B89F72 - Level 4: Ochre (medium-high)
  [139, 115, 85, 255], // #8B7355 - Level 5: Sienna (high)
  [92, 74, 61, 255] // #5C4A3D - Level 6: Deep brown (very high)
] as const

/**
 * 6-step sepia gradient colors (dark mode)
 * Inverted: deep brown (low) to cream (high) for visibility on dark backgrounds
 */
const SEPIA_GRADIENT_DARK: readonly RGBAColor[] = [
  [92, 74, 61, 255], // #5C4A3D - Level 1: Deep brown (very low)
  [139, 115, 85, 255], // #8B7355 - Level 2: Sienna (low)
  [184, 159, 114, 255], // #B89F72 - Level 3: Ochre (medium-low)
  [212, 196, 168, 255], // #D4C4A8 - Level 4: Tan (medium-high)
  [232, 220, 200, 255], // #E8DCC8 - Level 5: Warm sand (high)
  [247, 243, 232, 255] // #F7F3E8 - Level 6: Cream (very high)
] as const

// Default color (cream - lowest density)
const DEFAULT_COLOR: RGBAColor = [247, 243, 232, 255]

/**
 * Population thresholds for logarithmic scale (log10)
 * Based on typical urban population density ranges
 *
 * Thresholds (log10 scale):
 * - Level 1: pop < 10 (log < 1)
 * - Level 2: 10 <= pop < 100 (1 <= log < 2)
 * - Level 3: 100 <= pop < 1000 (2 <= log < 3)
 * - Level 4: 1000 <= pop < 10000 (3 <= log < 4)
 * - Level 5: 10000 <= pop < 100000 (4 <= log < 5)
 * - Level 6: pop >= 100000 (log >= 5)
 */
const LOG_THRESHOLDS: readonly number[] = [1, 2, 3, 4, 5] as const

/**
 * Get the color for a population value using logarithmic scale
 *
 * @param population - Population value (can be 0 or positive)
 * @param isDarkMode - Whether to use dark mode gradient (inverted)
 * @returns RGBA color tuple for deck.gl
 */
export function getColorForPopulation(
  population: number,
  isDarkMode: boolean = false
): RGBAColor {
  const gradient = isDarkMode ? SEPIA_GRADIENT_DARK : SEPIA_GRADIENT_LIGHT

  // Handle zero or negative values (shouldn't happen, but be safe)
  if (population <= 0) {
    return gradient[0] ?? DEFAULT_COLOR
  }

  // Calculate log10 of population
  const logPop = Math.log10(population)

  // Map to gradient level based on thresholds
  let level = 0
  for (let i = 0; i < LOG_THRESHOLDS.length; i++) {
    const threshold = LOG_THRESHOLDS[i]
    if (threshold !== undefined && logPop >= threshold) {
      level = i + 1
    }
  }

  // Ensure level is within bounds and return color
  const safeLevel = Math.min(level, gradient.length - 1)
  return gradient[safeLevel] ?? DEFAULT_COLOR
}

/**
 * Get all gradient colors for legend display
 *
 * @param isDarkMode - Whether to use dark mode gradient
 * @returns Array of RGBA colors from low to high density
 */
export function getGradientColors(isDarkMode: boolean = false): RGBAColor[] {
  const gradient = isDarkMode ? SEPIA_GRADIENT_DARK : SEPIA_GRADIENT_LIGHT
  return [...gradient]
}

/**
 * Population range labels for each gradient level
 */
const POPULATION_LABELS: readonly string[] = [
  '< 10',
  '10 - 100',
  '100 - 1K',
  '1K - 10K',
  '10K - 100K',
  '> 100K'
] as const

/**
 * Get the population range label for a gradient level
 *
 * @param level - Gradient level (0-5)
 * @returns Human-readable label for the population range
 */
export function getPopulationRangeLabel(level: number): string {
  const safeLevel = Math.min(Math.max(level, 0), POPULATION_LABELS.length - 1)
  return POPULATION_LABELS[safeLevel] ?? '< 10'
}

/**
 * Convert hex color string to RGBA tuple
 *
 * @param hex - Hex color string (e.g., "#F7F3E8")
 * @param alpha - Alpha value (0-255), defaults to 255
 * @returns RGBA color tuple
 */
export function hexToRGBA(hex: string, alpha: number = 255): RGBAColor {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
  if (!result) {
    return [0, 0, 0, alpha]
  }
  const r = result[1]
  const g = result[2]
  const b = result[3]
  if (!r || !g || !b) {
    return [0, 0, 0, alpha]
  }
  return [
    parseInt(r, 16),
    parseInt(g, 16),
    parseInt(b, 16),
    alpha
  ]
}
