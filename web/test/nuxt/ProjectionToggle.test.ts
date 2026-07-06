/**
 * Tests for ProjectionToggle (plan U6)
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ProjectionToggle from '../../app/components/ui/ProjectionToggle.vue'
import { MODELED_QUALIFIER } from '../../app/utils/climateFormat'
import { koppenLabel } from '../../types/climate'

describe('ProjectionToggle', () => {
  it('shows the now value by default and always the modeled qualifier', () => {
    const wrapper = mount(ProjectionToggle, {
      props: { now: 10, future: 20, unit: 'days/year', futureLabel: '2070, SSP5-8.5' }
    })
    expect(wrapper.find('[data-testid="projection-value"]').text()).toContain('10')
    expect(wrapper.find('[data-testid="projection-modeled"]').text()).toBe(MODELED_QUALIFIER)
  })

  it('switches to the future value on toggle, qualifier still present', async () => {
    const wrapper = mount(ProjectionToggle, {
      props: { now: 10, future: 20, unit: 'days/year', futureLabel: '2070, SSP5-8.5' }
    })
    await wrapper.find('[data-testid="projection-future"]').trigger('click')
    expect(wrapper.find('[data-testid="projection-value"]').text()).toContain('20')
    expect(wrapper.find('[data-testid="projection-modeled"]').text()).toBe(MODELED_QUALIFIER)
  })

  it('passes categorical (Köppen) class strings through unchanged', async () => {
    const wrapper = mount(ProjectionToggle, {
      props: { now: 'Cfb', future: 'Dfb', unit: null, futureLabel: '2071-2099' }
    })
    expect(wrapper.find('[data-testid="projection-value"]').text()).toBe('Cfb')
    await wrapper.find('[data-testid="projection-future"]').trigger('click')
    expect(wrapper.find('[data-testid="projection-value"]').text()).toBe('Dfb')
  })

  it('shows the future label on the toggle button', () => {
    const wrapper = mount(ProjectionToggle, {
      props: { now: 10, future: 20, futureLabel: '2070, SSP5-8.5' }
    })
    expect(wrapper.find('[data-testid="projection-future"]').text()).toBe('2070, SSP5-8.5')
  })

  it('uses a custom format function (e.g. Köppen code → label) for both sides', async () => {
    const wrapper = mount(ProjectionToggle, {
      props: { now: '14.0', future: '15.0', futureLabel: '2070', format: koppenLabel }
    })
    expect(wrapper.find('[data-testid="projection-value"]').text()).toBe('Cfa — Humid subtropical')
    await wrapper.find('[data-testid="projection-future"]').trigger('click')
    expect(wrapper.find('[data-testid="projection-value"]').text()).toBe('Cfb — Oceanic')
  })
})

describe('koppenLabel', () => {
  it('maps numeric class codes (stored as floats) to labelled classes', () => {
    expect(koppenLabel('14.0')).toBe('Cfa — Humid subtropical')
    expect(koppenLabel(3)).toBe('Aw — Tropical savanna')
    expect(koppenLabel('30')).toBe('EF — Ice cap')
  })

  it('echoes an unknown code and renders null as a dash', () => {
    expect(koppenLabel('99')).toBe('99')
    expect(koppenLabel(null)).toBe('—')
  })
})
