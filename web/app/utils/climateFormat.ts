/**
 * Pure formatting/shaping helpers for the Climate & Energy section.
 *
 * Kept framework-free so the temporal-class rendering logic is unit-testable
 * without mounting Chart.js / canvas.
 */

export type SeriesPoint = [number, number]

/** A series is renderable as a line only with at least two points. */
export function hasSeries(points: SeriesPoint[] | undefined | null): boolean {
  return Array.isArray(points) && points.length >= 2
}

/**
 * Shape a metric's own {year, value} points for a native-axis sparkline.
 * Years come from the points themselves (variable spine), NOT YEAR_EPOCHS —
 * so misaligned climate spines (UTCI 1970–2020, greenness 1985–2025) never snap
 * onto the population epoch slider.
 */
export function nativeSparklineData(points: SeriesPoint[]): { labels: string[], values: number[] } {
  const ordered = [...points].sort((a, b) => a[0] - b[0])
  return {
    labels: ordered.map(p => String(p[0])),
    values: ordered.map(p => p[1])
  }
}

/** The latest (last) value of a series, or null if empty. */
export function latestValue(points: SeriesPoint[] | undefined | null): number | null {
  if (!points || points.length === 0) return null
  const ordered = [...points].sort((a, b) => a[0] - b[0])
  return ordered[ordered.length - 1]![1]
}

export interface SectorShare {
  label: string
  value: number
  /** Percentage of the total, 0–100. */
  pct: number
}

/**
 * Normalize sector fingerprint shares to percentages summing to ~100.
 * Non-positive totals yield an empty array (renders nothing, not NaN widths).
 */
export function normalizeSectors(sectors: [string, number][]): SectorShare[] {
  const total = sectors.reduce((sum, [, v]) => sum + (v > 0 ? v : 0), 0)
  if (total <= 0) return []
  return sectors
    .filter(([, v]) => v > 0)
    .map(([label, value]) => ({ label, value, pct: (value / total) * 100 }))
}

/**
 * Format a climate value for display by unit.
 * - 'share' renders as a percentage (UCDB stores these as 0–100 already)
 * - 'count' renders as an integer
 * - otherwise a compact number with the unit appended
 */
export function formatClimateValue(value: number | string | null, unit: string | null): string {
  if (value === null) return '—'
  if (typeof value === 'string') return value
  if (unit === 'share') return `${value.toFixed(1)}%`
  if (unit === 'count') return Math.round(value).toLocaleString()

  const abs = Math.abs(value)
  const num = abs >= 1000 ? Math.round(value).toLocaleString() : value.toFixed(abs >= 1 ? 1 : 2)
  return unit ? `${num} ${unit}` : num
}

/** The standard, catalog-driven honesty qualifier for modeled metrics. */
export const MODELED_QUALIFIER = 'modeled, not measured'
