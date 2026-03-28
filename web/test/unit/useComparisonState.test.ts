/**
 * Unit tests for comparison state parsing
 *
 * Tests the pure parseComparisonParam function which handles
 * URL parameter parsing, canonical ordering, and validation.
 */

import { describe, it, expect } from 'vitest'
import { parseComparisonParam } from '../../app/composables/useComparisonState'

describe('parseComparisonParam', () => {
  // Happy path
  it('parses "123+456" into cityA="123", cityB="456"', () => {
    const result = parseComparisonParam('123+456')
    expect(result.parsed).toEqual({ cityA: '123', cityB: '456' })
    expect(result.redirect).toBeNull()
    expect(result.error).toBeNull()
  })

  it('preserves leading zeros in city IDs', () => {
    const result = parseComparisonParam('0042+1234')
    expect(result.parsed).toEqual({ cityA: '0042', cityB: '1234' })
  })

  // Canonical ordering
  it('returns redirect for non-canonical order "456+123"', () => {
    const result = parseComparisonParam('456+123')
    expect(result.parsed).toBeNull()
    expect(result.redirect).toEqual({
      type: 'canonical',
      target: '/compare/123+456'
    })
    expect(result.error).toBeNull()
  })

  it('returns redirect for "10933+5472" (larger first)', () => {
    const result = parseComparisonParam('10933+5472')
    expect(result.parsed).toBeNull()
    expect(result.redirect).toEqual({
      type: 'canonical',
      target: '/compare/5472+10933'
    })
  })

  // Same city
  it('returns same-city redirect for "123+123"', () => {
    const result = parseComparisonParam('123+123')
    expect(result.parsed).toBeNull()
    expect(result.redirect).toEqual({
      type: 'same-city',
      target: '/city/123'
    })
    expect(result.error).toBeNull()
  })

  // Invalid formats
  it('returns error for "123" (no separator)', () => {
    const result = parseComparisonParam('123')
    expect(result.parsed).toBeNull()
    expect(result.redirect).toBeNull()
    expect(result.error).toBeTruthy()
  })

  it('returns error for empty string', () => {
    const result = parseComparisonParam('')
    expect(result.parsed).toBeNull()
    expect(result.error).toBeTruthy()
  })

  it('returns error for "abc+456" (non-numeric)', () => {
    const result = parseComparisonParam('abc+456')
    expect(result.parsed).toBeNull()
    expect(result.error).toBeTruthy()
  })

  it('returns error for "123+abc" (non-numeric second)', () => {
    const result = parseComparisonParam('123+abc')
    expect(result.parsed).toBeNull()
    expect(result.error).toBeTruthy()
  })

  it('returns error for "12.3+456" (decimal)', () => {
    const result = parseComparisonParam('12.3+456')
    expect(result.parsed).toBeNull()
    expect(result.error).toBeTruthy()
  })

  it('returns error for "123+456+789" (too many parts)', () => {
    const result = parseComparisonParam('123+456+789')
    expect(result.parsed).toBeNull()
    expect(result.error).toBeTruthy()
  })
})
