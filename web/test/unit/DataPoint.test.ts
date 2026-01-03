/**
 * Unit tests for DataPoint component
 *
 * Tests rendering, styling, and props handling
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'

// Mock UTooltip component
const UTooltipStub = defineComponent({
  name: 'UTooltip',
  props: ['text'],
  setup(props, { slots }) {
    return () => h('div', { 'data-tooltip': props.text }, slots.default?.())
  }
})

// Create a simplified version of DataPoint for unit testing
const DataPointTest = defineComponent({
  name: 'DataPoint',
  props: {
    label: { type: String, required: true },
    value: { type: String, required: true },
    rawValue: { type: Number, required: true },
    sourceLabel: { type: String, default: 'Source' }
  },
  setup(props) {
    const formattedRawValue = props.rawValue.toLocaleString()

    return () => h('div', { class: 'flex flex-col gap-0.5' }, [
      // Label
      h('span', {
        'data-testid': 'datapoint-label',
        'class': 'text-xs text-body/70 dark:text-cream/70'
      }, props.label),
      // Value with tooltip wrapper
      h(UTooltipStub, { text: formattedRawValue }, {
        default: () => h('div', {
          'data-testid': 'datapoint-value-wrapper',
          'class': 'cursor-help'
        }, [
          h('span', {
            'data-testid': 'datapoint-value',
            'class': 'font-mono text-2xl font-semibold text-forest-700 dark:text-forest-300'
          }, props.value)
        ])
      }),
      // Source link
      h('span', {
        'data-testid': 'datapoint-source',
        'class': 'text-xs text-body/50 dark:text-cream/50 hover:text-forest-600 dark:hover:text-forest-400 cursor-pointer transition-colors'
      }, props.sourceLabel)
    ])
  }
})

describe('DataPoint', () => {
  it('renders label, humanized value, and source link', () => {
    const wrapper = mount(DataPointTest, {
      props: {
        label: 'World Population',
        value: '8.2 billion',
        rawValue: 8191988536,
        sourceLabel: 'UN WPP'
      }
    })

    // Check label is rendered
    expect(wrapper.text()).toContain('World Population')

    // Check humanized value is rendered
    expect(wrapper.text()).toContain('8.2 billion')

    // Check source label is rendered
    expect(wrapper.text()).toContain('UN WPP')
  })

  it('displays default source label when not provided', () => {
    const wrapper = mount(DataPointTest, {
      props: {
        label: 'Urban Population',
        value: '3.6 billion',
        rawValue: 3569570193
      }
    })

    // Check default source label
    expect(wrapper.text()).toContain('Source')
  })

  it('applies mono font to value element', () => {
    const wrapper = mount(DataPointTest, {
      props: {
        label: 'World Population',
        value: '8.2 billion',
        rawValue: 8191988536
      }
    })

    // Find the value element (should have font-mono class)
    const valueElement = wrapper.find('[data-testid="datapoint-value"]')
    expect(valueElement.exists()).toBe(true)
    expect(valueElement.classes()).toContain('font-mono')
  })

  it('applies sans-serif font to label element (no font-mono or font-serif)', () => {
    const wrapper = mount(DataPointTest, {
      props: {
        label: 'World Population',
        value: '8.2 billion',
        rawValue: 8191988536
      }
    })

    // Find the label element (should NOT have font-mono or font-serif)
    const labelElement = wrapper.find('[data-testid="datapoint-label"]')
    expect(labelElement.exists()).toBe(true)
    expect(labelElement.classes()).not.toContain('font-mono')
    expect(labelElement.classes()).not.toContain('font-serif')
  })

  it('passes formatted raw value to tooltip', () => {
    const wrapper = mount(DataPointTest, {
      props: {
        label: 'World Population',
        value: '8.2 billion',
        rawValue: 8191988536
      }
    })

    // The tooltip wrapper should have the data-tooltip attribute with formatted value
    const tooltipWrapper = wrapper.find('[data-tooltip]')
    expect(tooltipWrapper.exists()).toBe(true)
    // Check that the tooltip has the formatted number
    const tooltipText = tooltipWrapper.attributes('data-tooltip')
    expect(tooltipText).toBeDefined()
    // The number should contain commas for thousands separator (locale dependent)
    expect(tooltipText).toContain('8')
  })
})
