/**
 * Tests for NativeAxisSparkline + climate formatting helpers (plan U6)
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import NativeAxisSparkline from '../../app/components/ui/NativeAxisSparkline.client.vue'
import {
  hasSeries,
  nativeSparklineData,
  latestValue,
  normalizeSectors,
  formatClimateValue
} from '../../app/utils/climateFormat'

describe('climateFormat helpers', () => {
  it('renders a series on its own (non-epoch) spine, ascending', () => {
    // UTCI 1970–2020 spine — not the population YEAR_EPOCHS (1975–2030)
    const { labels, values } = nativeSparklineData([[2020, 9], [1970, 3], [1990, 5]])
    expect(labels).toEqual(['1970', '1990', '2020'])
    expect(values).toEqual([3, 5, 9])
    expect(labels).not.toContain('2030')
  })

  it('treats single-point / empty series as not renderable', () => {
    expect(hasSeries([])).toBe(false)
    expect(hasSeries([[2000, 1]])).toBe(false)
    expect(hasSeries([[2000, 1], [2010, 2]])).toBe(true)
  })

  it('latestValue returns the last point by year', () => {
    expect(latestValue([[2020, 4.2], [1975, 1]])).toBe(4.2)
    expect(latestValue([])).toBeNull()
  })

  it('normalizeSectors yields shares summing to ~100', () => {
    const shares = normalizeSectors([['Energy', 4], ['Transport', 4], ['Industry', 2]])
    expect(shares.map(s => s.label)).toEqual(['Energy', 'Transport', 'Industry'])
    expect(shares.reduce((s, x) => s + x.pct, 0)).toBeCloseTo(100, 5)
    expect(normalizeSectors([['x', 0]])).toEqual([])
  })

  it('formats shares as percent and counts as integers', () => {
    expect(formatClimateValue(0.123, 'share')).toBe('12.3%')
    expect(formatClimateValue(3, 'count')).toBe('3')
    expect(formatClimateValue(1500, 'kWh/kWp')).toBe('1,500 kWh/kWp')
    expect(formatClimateValue(null, 'share')).toBe('—')
    expect(formatClimateValue('Cfb', null)).toBe('Cfb')
  })
})

describe('NativeAxisSparkline', () => {
  it('renders the empty state for a single-point series (no crash)', () => {
    const wrapper = mount(NativeAxisSparkline, { props: { points: [[2000, 5]] } })
    expect(wrapper.find('[data-testid="native-axis-sparkline-empty"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="native-axis-sparkline"]').exists()).toBe(false)
  })

  it('renders the empty state for an empty series', () => {
    const wrapper = mount(NativeAxisSparkline, { props: { points: [] } })
    expect(wrapper.find('[data-testid="native-axis-sparkline-empty"]').exists()).toBe(true)
  })
})
