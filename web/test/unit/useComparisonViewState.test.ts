/**
 * Unit tests for comparison view state management
 *
 * Tests shared zoom sync, independent centers, and feedback loop guards.
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { useComparisonViewState } from '../../app/composables/useComparisonViewState'

describe('useComparisonViewState', () => {
  beforeEach(() => {
    const { reset } = useComparisonViewState()
    reset()
  })

  it('starts with default zoom and centers', () => {
    const { sharedZoom, centerA, centerB } = useComparisonViewState()
    expect(sharedZoom.value).toBe(1.5)
    expect(centerA.value).toEqual({ lng: 0, lat: 15 })
    expect(centerB.value).toEqual({ lng: 0, lat: 15 })
  })

  it('updates shared zoom from map A', () => {
    const { sharedZoom, onZoomChange } = useComparisonViewState()
    onZoomChange(10, 'A')
    expect(sharedZoom.value).toBe(10)
  })

  it('updates shared zoom from map B', () => {
    const { sharedZoom, onZoomChange } = useComparisonViewState()
    onZoomChange(8, 'B')
    expect(sharedZoom.value).toBe(8)
  })

  it('tracks zoom source for feedback loop guard', () => {
    const { onZoomChange, isZoomSource } = useComparisonViewState()
    onZoomChange(10, 'A')
    expect(isZoomSource('A')).toBe(true)
    expect(isZoomSource('B')).toBe(false)
  })

  it('clears zoom source guard', () => {
    const { onZoomChange, isZoomSource, clearZoomSource } = useComparisonViewState()
    onZoomChange(10, 'A')
    expect(isZoomSource('A')).toBe(true)
    clearZoomSource()
    expect(isZoomSource('A')).toBe(false)
  })

  it('updates only map A center on pan', () => {
    const { centerA, centerB, onPanChange } = useComparisonViewState()
    onPanChange({ lng: 139.7, lat: 35.7 }, 'A')
    expect(centerA.value).toEqual({ lng: 139.7, lat: 35.7 })
    expect(centerB.value).toEqual({ lng: 0, lat: 15 }) // unchanged
  })

  it('updates only map B center on pan', () => {
    const { centerA, centerB, onPanChange } = useComparisonViewState()
    onPanChange({ lng: 2.35, lat: 48.85 }, 'B')
    expect(centerA.value).toEqual({ lng: 0, lat: 15 }) // unchanged
    expect(centerB.value).toEqual({ lng: 2.35, lat: 48.85 })
  })

  it('sets center for a specific map', () => {
    const { centerA, setCenter } = useComparisonViewState()
    setCenter({ lng: 100, lat: 50 }, 'A')
    expect(centerA.value).toEqual({ lng: 100, lat: 50 })
  })

  it('gets the correct center ref for a map', () => {
    const { getCenter, setCenter } = useComparisonViewState()
    setCenter({ lng: 10, lat: 20 }, 'A')
    setCenter({ lng: 30, lat: 40 }, 'B')
    expect(getCenter('A').value).toEqual({ lng: 10, lat: 20 })
    expect(getCenter('B').value).toEqual({ lng: 30, lat: 40 })
  })

  it('resets all state', () => {
    const { sharedZoom, centerA, centerB, onZoomChange, onPanChange, reset } = useComparisonViewState()
    onZoomChange(12, 'A')
    onPanChange({ lng: 100, lat: 50 }, 'A')
    onPanChange({ lng: 200, lat: 60 }, 'B')

    reset()

    expect(sharedZoom.value).toBe(1.5)
    expect(centerA.value).toEqual({ lng: 0, lat: 15 })
    expect(centerB.value).toEqual({ lng: 0, lat: 15 })
  })
})
