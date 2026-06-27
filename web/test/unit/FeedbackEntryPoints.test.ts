/**
 * Unit tests for the feedback entry points (U6).
 *
 * Mounts the real FeedbackButton and AppHeader with light stubs to verify both
 * entry points open the shared modal (R1/R2/R3) and the desktop button is
 * desktop-only, while the mobile drawer item also closes the drawer.
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import FeedbackButton from '../../app/components/FeedbackButton.vue'
import AppHeader from '../../app/components/layout/AppHeader.vue'
import { useFeedback } from '../../app/composables/useFeedback'

// Renders a real <button> that forwards clicks and inherits attrs (class, aria-label).
const UButtonStub = defineComponent({
  name: 'UButton',
  emits: ['click'],
  setup(_, { slots, emit }) {
    return () => h('button', { onClick: () => emit('click') }, slots.default?.())
  }
})

// Records its `open` prop and renders default + body slots so drawer content mounts.
const UDrawerStub = defineComponent({
  name: 'UDrawer',
  props: { open: { type: Boolean, default: false } },
  emits: ['update:open'],
  setup(props, { slots }) {
    return () => h('div', { 'data-drawer-open': String(props.open) }, [
      slots.default?.(),
      slots.body?.()
    ])
  }
})

const NuxtLinkStub = defineComponent({
  name: 'NuxtLink',
  props: { to: { type: String, default: '' } },
  setup(_, { slots }) {
    return () => h('a', {}, slots.default?.())
  }
})

const headerStubs = {
  UButton: UButtonStub,
  UDrawer: UDrawerStub,
  NuxtLink: NuxtLinkStub,
  CitySearch: true,
  AppLogo: true,
  DarkModeToggle: true
}

describe('FeedbackButton (desktop)', () => {
  beforeEach(() => useFeedback().close())

  it('opens the feedback modal when clicked', async () => {
    const wrapper = mount(FeedbackButton, { global: { stubs: { UButton: UButtonStub } } })
    expect(useFeedback().isOpen.value).toBe(false)

    await wrapper.find('button').trigger('click')

    expect(useFeedback().isOpen.value).toBe(true)
  })

  it('is hidden on mobile breakpoints (max-sm:hidden) and fixed-positioned', () => {
    const wrapper = mount(FeedbackButton, { global: { stubs: { UButton: UButtonStub } } })
    const classes = wrapper.find('button').classes()
    expect(classes).toContain('max-sm:hidden')
    expect(classes).toContain('fixed')
  })
})

describe('AppHeader mobile drawer feedback item', () => {
  beforeEach(() => useFeedback().close())

  it('opens the modal and closes the drawer when the feedback item is clicked', async () => {
    const wrapper = mount(AppHeader, { global: { stubs: headerStubs } })

    // Open the drawer via the hamburger (aria-label="Open menu").
    const hamburger = wrapper.findAll('button').find(b => b.attributes('aria-label') === 'Open menu')
    expect(hamburger).toBeTruthy()
    await hamburger!.trigger('click')
    expect(wrapper.find('[data-drawer-open]').attributes('data-drawer-open')).toBe('true')

    // Click the Feedback item inside the drawer body.
    const feedbackItem = wrapper.findAll('button').find(b => b.text() === 'Feedback')
    expect(feedbackItem).toBeTruthy()
    await feedbackItem!.trigger('click')

    expect(useFeedback().isOpen.value).toBe(true)
    expect(wrapper.find('[data-drawer-open]').attributes('data-drawer-open')).toBe('false')
  })
})
