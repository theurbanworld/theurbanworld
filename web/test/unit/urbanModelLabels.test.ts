/**
 * Tests for the shared Standard Urban Model label module (U6).
 *
 * Labels are a pure function of a city's OWN beta/R^2 (not dataset-relative), so the
 * boundary behaviour is deterministic and anchored to the exported thresholds.
 */

import { describe, it, expect } from 'vitest'
import {
  COMPACT_BETA_MIN,
  SPREAD_BETA_MAX,
  MONOCENTRIC_R2_CUTOFF,
  COMPACTNESS_LABELS,
  STRUCTURE_LABELS,
  compactnessLabel,
  structureLabel,
  classifyFit,
  betaBarFraction,
  fitBadgeState
} from '../../app/utils/urbanModelLabels'

describe('compactnessLabel', () => {
  it('returns Compact at and above the compact threshold', () => {
    expect(compactnessLabel(COMPACT_BETA_MIN)).toBe(COMPACTNESS_LABELS.COMPACT)
    expect(compactnessLabel(COMPACT_BETA_MIN + 0.001)).toBe(COMPACTNESS_LABELS.COMPACT)
    expect(compactnessLabel(0.5)).toBe(COMPACTNESS_LABELS.COMPACT) // steep gradient
  })

  it('returns Moderate between the spread and compact thresholds', () => {
    expect(compactnessLabel(COMPACT_BETA_MIN - 0.001)).toBe(COMPACTNESS_LABELS.MODERATE)
    expect(compactnessLabel(SPREAD_BETA_MAX)).toBe(COMPACTNESS_LABELS.MODERATE)
  })

  it('returns Spread below the spread threshold', () => {
    expect(compactnessLabel(SPREAD_BETA_MAX - 0.001)).toBe(COMPACTNESS_LABELS.SPREAD)
    expect(compactnessLabel(0.08)).toBe(COMPACTNESS_LABELS.SPREAD) // Atlanta-like
  })

  it('returns null for null/undefined/non-finite input', () => {
    expect(compactnessLabel(null)).toBeNull()
    expect(compactnessLabel(undefined)).toBeNull()
    expect(compactnessLabel(NaN)).toBeNull()
  })
})

describe('structureLabel', () => {
  it('returns Single-center at or above the monocentric cutoff', () => {
    expect(structureLabel(MONOCENTRIC_R2_CUTOFF)).toBe(STRUCTURE_LABELS.SINGLE_CENTER)
    expect(structureLabel(0.98)).toBe(STRUCTURE_LABELS.SINGLE_CENTER)
  })

  it('returns Multi-centered / Irregular below the cutoff', () => {
    expect(structureLabel(MONOCENTRIC_R2_CUTOFF - 0.001)).toBe(STRUCTURE_LABELS.MULTI_CENTERED)
    expect(structureLabel(0.4)).toBe(STRUCTURE_LABELS.MULTI_CENTERED)
  })

  it('returns null for null/undefined/non-finite input', () => {
    expect(structureLabel(null)).toBeNull()
    expect(structureLabel(undefined)).toBeNull()
    expect(structureLabel(NaN)).toBeNull()
  })

  it('Covers AE2. A low-R^2 label never asserts polycentricity or any cause', () => {
    const label = structureLabel(0.3) as string
    const lowered = label.toLowerCase()
    expect(lowered).not.toContain('polycentric')
    expect(lowered).not.toContain('because')
    expect(lowered).not.toContain('sprawl')
    // It is one of the two allowed, deviation-only descriptions.
    expect(Object.values(STRUCTURE_LABELS)).toContain(label)
  })
})

describe('Covers AE4. label is a pure function of the city own beta', () => {
  it('flips the compactness label when beta crosses a band boundary', () => {
    const justBelow = compactnessLabel(COMPACT_BETA_MIN - 0.001)
    const justAbove = compactnessLabel(COMPACT_BETA_MIN + 0.001)
    expect(justBelow).not.toBe(justAbove)
    expect(justAbove).toBe(COMPACTNESS_LABELS.COMPACT)
    expect(justBelow).toBe(COMPACTNESS_LABELS.MODERATE)
  })

  it('gives the same label for the same beta regardless of any other city', () => {
    // No dataset is passed in — identical beta always yields identical label.
    expect(compactnessLabel(0.15)).toBe(compactnessLabel(0.15))
  })
})

describe('classifyFit', () => {
  it('returns both axes, each null when its input is missing', () => {
    expect(classifyFit(0.5, 0.95)).toEqual({
      compactness: COMPACTNESS_LABELS.COMPACT,
      structure: STRUCTURE_LABELS.SINGLE_CENTER
    })
    expect(classifyFit(null, null)).toEqual({ compactness: null, structure: null })
    expect(classifyFit(0.5, null)).toEqual({
      compactness: COMPACTNESS_LABELS.COMPACT,
      structure: null
    })
  })
})

describe('fitBadgeState', () => {
  it('returns loading when no fit entry exists (pending or absent), not unreliable', () => {
    expect(fitBadgeState(null)).toBe('loading')
    expect(fitBadgeState(undefined)).toBe('loading')
  })

  it('returns unreliable for a reliable:false entry', () => {
    expect(fitBadgeState({ reliable: false })).toBe('unreliable')
  })

  it('returns reliable for a reliable:true entry', () => {
    expect(fitBadgeState({ reliable: true })).toBe('reliable')
  })
})

describe('betaBarFraction', () => {
  it('clamps Spread to 0 and Compact to 1', () => {
    expect(betaBarFraction(SPREAD_BETA_MAX - 0.05)).toBe(0)
    expect(betaBarFraction(COMPACT_BETA_MIN + 0.05)).toBe(1)
  })

  it('returns a mid value within the band', () => {
    const mid = betaBarFraction((SPREAD_BETA_MAX + COMPACT_BETA_MIN) / 2)
    expect(mid).toBeGreaterThan(0.4)
    expect(mid).toBeLessThan(0.6)
  })

  it('returns 0 for missing input', () => {
    expect(betaBarFraction(null)).toBe(0)
    expect(betaBarFraction(NaN)).toBe(0)
  })
})
