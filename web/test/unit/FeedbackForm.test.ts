/**
 * Unit tests for useFeedbackForm — feedback form state, validation, submission.
 *
 * $fetch is stubbed globally to assert the POST contract and success/error
 * transitions. Covers origin acceptance example AE1 (email required to submit).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useFeedbackForm } from '../../app/composables/useFeedbackForm'

describe('useFeedbackForm', () => {
  let fetchMock: ReturnType<typeof vi.fn>

  beforeEach(() => {
    fetchMock = vi.fn(async () => ({ ok: true }))
    vi.stubGlobal('$fetch', fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // Covers AE1 — message typed, email empty → submit blocked, email flagged, no POST.
  it('blocks submit and flags email when message is present but email is empty', async () => {
    const form = useFeedbackForm()
    form.message.value = 'The 2025 number looks off.'
    form.email.value = ''

    expect(form.canSubmit.value).toBe(false)

    await form.submit()

    expect(form.showEmailError.value).toBe(true)
    expect(fetchMock).not.toHaveBeenCalled()
    expect(form.status.value).toBe('idle')
  })

  it('enables submit only when the email is syntactically valid', () => {
    const form = useFeedbackForm()
    form.message.value = 'Hello'

    form.email.value = 'nope'
    expect(form.canSubmit.value).toBe(false)

    form.email.value = 'user@example.com'
    expect(form.canSubmit.value).toBe(true)
  })

  it('records the selected category and sends it in the payload', async () => {
    const form = useFeedbackForm()
    form.message.value = 'A suggestion'
    form.email.value = 'user@example.com'
    form.setCategory('Suggestion')

    expect(form.category.value).toBe('Suggestion')

    await form.submit()

    const body = fetchMock.mock.calls[0]![1].body
    expect(body.category).toBe('Suggestion')
  })

  it('posts the captured context and transitions to success on 200', async () => {
    const form = useFeedbackForm()
    form.message.value = 'Looks great'
    form.email.value = 'user@example.com'
    form.token.value = 'tok-123'

    await form.submit()

    expect(fetchMock).toHaveBeenCalledOnce()
    const [url, opts] = fetchMock.mock.calls[0]!
    expect(url).toBe('/api/feedback')
    expect(opts.method).toBe('POST')
    expect(opts.body.context).toBeDefined()
    expect(typeof opts.body.context.url).toBe('string')
    expect(form.status.value).toBe('success')
  })

  it('includes the Turnstile token and clears it after submit', async () => {
    const form = useFeedbackForm()
    form.message.value = 'Token test'
    form.email.value = 'user@example.com'
    form.token.value = 'turnstile-abc'

    await form.submit()

    expect(fetchMock.mock.calls[0]![1].body.token).toBe('turnstile-abc')
    expect(form.token.value).toBe('')
  })

  it('transitions to error and stays recoverable when the POST fails', async () => {
    fetchMock.mockRejectedValueOnce(new Error('500'))
    const form = useFeedbackForm()
    form.message.value = 'Will fail'
    form.email.value = 'user@example.com'

    await form.submit()

    expect(form.status.value).toBe('error')
    // Still recoverable — fields retained, can resubmit.
    expect(form.message.value).toBe('Will fail')
    expect(form.canSubmit.value).toBe(true)
  })

  it('reset() clears all fields and status', () => {
    const form = useFeedbackForm()
    form.message.value = 'x'
    form.email.value = 'a@b.co'
    form.setCategory('Other')
    form.status.value = 'success'

    form.reset()

    expect(form.message.value).toBe('')
    expect(form.email.value).toBe('')
    expect(form.category.value).toBe('Data issue')
    expect(form.status.value).toBe('idle')
  })
})
