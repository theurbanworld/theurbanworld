/**
 * Standard Urban Model labels — single source of truth.
 *
 * Turns the raw exponential-fit metrics (beta, R^2) into two plain-language axes:
 *   - compactness, from the density gradient beta
 *   - structure, from the goodness-of-fit R^2
 *
 * Every consumer (the city badge, the comparison table, and the rankings filter)
 * derives labels from THIS module so they can never diverge. No threshold literal
 * should appear anywhere else — change the bands or the copy here and all surfaces
 * follow.
 *
 * The thresholds are literature-anchored placeholders (KTD5): the compactness bands
 * sit between Atlanta-like sprawl (beta ~= 0.08) and Paris-like compactness
 * (beta ~= 0.22); the structure cutoff marks where an exponential stops being a good
 * description of the profile. They should be recalibrated against the real fit
 * distribution; doing so only touches this file.
 *
 * Structure describes deviation ONLY. It never asserts a cause (geography, planning,
 * polycentricity) — a poor monocentric fit tells you the textbook curve does not
 * describe the city, not why.
 */

// --- Thresholds (the only place these numbers live) -------------------------

/** beta at or above this is "Compact" (steep gradient, density falls off fast). */
export const COMPACT_BETA_MIN = 0.18

/** beta below this is "Spread" (shallow gradient, density falls off slowly). */
export const SPREAD_BETA_MAX = 0.11

/** R^2 at or above this means the monocentric exponential fits well ("Single-center"). */
export const MONOCENTRIC_R2_CUTOFF = 0.9

// --- Label copy (centralized so wording is editable in one place) -----------

export const COMPACTNESS_LABELS = {
  COMPACT: 'Compact',
  MODERATE: 'Moderate',
  SPREAD: 'Spread'
} as const

export const STRUCTURE_LABELS = {
  SINGLE_CENTER: 'Single-center',
  MULTI_CENTERED: 'Multi-centered / Irregular'
} as const

export type CompactnessLabel = (typeof COMPACTNESS_LABELS)[keyof typeof COMPACTNESS_LABELS]
export type StructureLabel = (typeof STRUCTURE_LABELS)[keyof typeof STRUCTURE_LABELS]

/** All compactness labels, ordered most→least compact (for filter chips). */
export const COMPACTNESS_LABEL_VALUES: CompactnessLabel[] = [
  COMPACTNESS_LABELS.COMPACT,
  COMPACTNESS_LABELS.MODERATE,
  COMPACTNESS_LABELS.SPREAD
]

/** All structure labels (for filter chips). */
export const STRUCTURE_LABEL_VALUES: StructureLabel[] = [
  STRUCTURE_LABELS.SINGLE_CENTER,
  STRUCTURE_LABELS.MULTI_CENTERED
]

// --- Derivations (pure functions; null in → null out) -----------------------

/**
 * Compactness label from the density gradient beta.
 * A larger beta means a steeper fall-off, i.e. a more compact city.
 * Returns null when beta is missing (honest-null upstream).
 */
export function compactnessLabel(beta: number | null | undefined): CompactnessLabel | null {
  if (beta == null || !Number.isFinite(beta)) return null
  if (beta >= COMPACT_BETA_MIN) return COMPACTNESS_LABELS.COMPACT
  if (beta >= SPREAD_BETA_MAX) return COMPACTNESS_LABELS.MODERATE
  return COMPACTNESS_LABELS.SPREAD
}

/**
 * Structure label from the fit quality R^2.
 * Describes how well a single-center exponential describes the profile — and
 * nothing about why it deviates. Returns null when R^2 is missing.
 */
export function structureLabel(r2: number | null | undefined): StructureLabel | null {
  if (r2 == null || !Number.isFinite(r2)) return null
  return r2 >= MONOCENTRIC_R2_CUTOFF
    ? STRUCTURE_LABELS.SINGLE_CENTER
    : STRUCTURE_LABELS.MULTI_CENTERED
}

/** Both axes at once. Either field is null when its input is missing. */
export function classifyFit(
  beta: number | null | undefined,
  r2: number | null | undefined
): { compactness: CompactnessLabel | null, structure: StructureLabel | null } {
  return { compactness: compactnessLabel(beta), structure: structureLabel(r2) }
}

/**
 * Fraction (0..1) of beta within the compactness band range, for bar encoding in
 * the rankings (column-max normalization is meaningless for the narrow beta band).
 * Clamped so Spread→0 and Compact→1.
 */
export function betaBarFraction(beta: number | null | undefined): number {
  if (beta == null || !Number.isFinite(beta)) return 0
  const span = COMPACT_BETA_MIN - SPREAD_BETA_MAX
  if (span <= 0) return 0
  const frac = (beta - SPREAD_BETA_MAX) / span
  return Math.max(0, Math.min(1, frac))
}
