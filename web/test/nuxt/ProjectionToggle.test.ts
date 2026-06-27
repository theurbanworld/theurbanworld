/**
 * Tests for ProjectionToggle (plan U6)
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ProjectionToggle from '../../app/components/ui/ProjectionToggle.vue'
import { MODELED_QUALIFIER } from '../../app/utils/climateFormat'

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
})
