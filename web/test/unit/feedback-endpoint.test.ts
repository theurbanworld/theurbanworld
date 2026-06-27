/**
 * Unit tests for the feedback endpoint core (handleFeedbackRequest).
 *
 * Turnstile verification and Resend delivery are injected as mocks, so these
 * exercise the full validate → verify → send contract without network or Nitro.
 * Covers origin acceptance examples AE2, AE3, AE4, AE5.
 */

import { describe, it, expect, vi } from 'vitest'
import {
  handleFeedbackRequest,
  validateFeedbackPayload,
  buildSubject,
  buildEmailText,
  isValidEmail
} from '../../server/utils/feedback'

const CONFIG = { resendFrom: 'feedback@theurban.world', feedbackToEmail: 'maintainer@example.com' }

function validBody(overrides: Record<string, unknown> = {}) {
  return {
    category: 'Data issue',
    message: 'Population for Lima looks wrong in 2025.',
    email: 'reporter@example.com',
    token: 'turnstile-token',
    context: { url: 'https://theurban.world/city/123' },
    ...overrides
  }
}

function deps(opts: { verify?: boolean, send?: { ok: boolean, status: number } } = {}) {
  return {
    verifyToken: vi.fn(async () => opts.verify ?? true),
    sendEmail: vi.fn(async () => opts.send ?? { ok: true, status: 200 })
  }
}

describe('handleFeedbackRequest', () => {
  // Covers AE4 — valid submission delivers with category in subject + reply_to.
  it('happy path: verifies, sends once, returns 200', async () => {
    const d = deps()
    const res = await handleFeedbackRequest(validBody(), CONFIG, d)

    expect(res.status).toBe(200)
    expect(res.body).toEqual({ ok: true })
    expect(d.verifyToken).toHaveBeenCalledOnce()
    expect(d.sendEmail).toHaveBeenCalledOnce()

    const email = d.sendEmail.mock.calls[0]![0]
    expect(email.to).toBe('maintainer@example.com')
    expect(email.reply_to).toBe('reporter@example.com')
    expect(email.subject).toContain('Data issue')
  })

  // Covers AE5 — failed Turnstile rejects pre-send.
  it('rejects with 403 and never sends when the token is invalid', async () => {
    const d = deps({ verify: false })
    const res = await handleFeedbackRequest(validBody(), CONFIG, d)

    expect(res.status).toBe(403)
    expect(d.sendEmail).not.toHaveBeenCalled()
  })

  // Covers AE2 — full context lands in the email body.
  it('includes url + city/dataset/epoch in the body when context is full', async () => {
    const d = deps()
    await handleFeedbackRequest(
      validBody({
        context: {
          url: 'https://theurban.world/city/123',
          city: { id: '123', name: 'Lima' },
          dataset: 'Urban World v1',
          epoch: 2025
        }
      }),
      CONFIG,
      d
    )

    const text = d.sendEmail.mock.calls[0]![0].text
    expect(text).toContain('https://theurban.world/city/123')
    expect(text).toContain('Lima')
    expect(text).toContain('Urban World v1')
    expect(text).toContain('2025')
  })

  // Covers AE3 — url-only context still sends; no city/dataset/epoch lines.
  it('sends 200 with url-only context and omits city/dataset/epoch lines', async () => {
    const d = deps()
    const res = await handleFeedbackRequest(
      validBody({ context: { url: 'https://theurban.world/' } }),
      CONFIG,
      d
    )

    expect(res.status).toBe(200)
    const text = d.sendEmail.mock.calls[0]![0].text
    expect(text).toContain('https://theurban.world/')
    expect(text).not.toContain('City:')
    expect(text).not.toContain('Dataset:')
    expect(text).not.toContain('Epoch:')
  })

  it('rejects invalid email with 400 and never verifies or sends', async () => {
    const d = deps()
    const res = await handleFeedbackRequest(validBody({ email: 'not-an-email' }), CONFIG, d)

    expect(res.status).toBe(400)
    expect(d.verifyToken).not.toHaveBeenCalled()
    expect(d.sendEmail).not.toHaveBeenCalled()
  })

  it('rejects empty message with 400', async () => {
    const res = await handleFeedbackRequest(validBody({ message: '   ' }), CONFIG, deps())
    expect(res.status).toBe(400)
  })

  it('rejects unknown category with 400', async () => {
    const res = await handleFeedbackRequest(validBody({ category: 'Spam' }), CONFIG, deps())
    expect(res.status).toBe(400)
  })

  it('rejects a missing token with 400 before verifying', async () => {
    const d = deps()
    const res = await handleFeedbackRequest(validBody({ token: '' }), CONFIG, d)
    expect(res.status).toBe(400)
    expect(d.verifyToken).not.toHaveBeenCalled()
  })

  it('returns 502 without leaking details when Resend fails', async () => {
    const d = deps({ send: { ok: false, status: 422 } })
    const res = await handleFeedbackRequest(validBody(), CONFIG, d)

    expect(res.status).toBe(502)
    expect(JSON.stringify(res.body)).not.toContain('resend')
    expect(JSON.stringify(res.body)).not.toContain('Bearer')
  })
})

describe('feedback helpers', () => {
  it('isValidEmail accepts well-formed and rejects malformed addresses', () => {
    expect(isValidEmail('a@b.co')).toBe(true)
    expect(isValidEmail('a@b')).toBe(false)
    expect(isValidEmail('no-at.com')).toBe(false)
    expect(isValidEmail('with space@b.com')).toBe(false)
    expect(isValidEmail(123)).toBe(false)
  })

  it('validateFeedbackPayload trims message and email', () => {
    const result = validateFeedbackPayload({
      category: 'Question',
      message: '  hello  ',
      email: '  q@x.io ',
      token: 't'
    })
    expect(result.ok).toBe(true)
    if (result.ok) {
      expect(result.payload.message).toBe('hello')
      expect(result.payload.email).toBe('q@x.io')
    }
  })

  it('buildSubject surfaces the category', () => {
    expect(buildSubject('Suggestion', 'Add a dark map style please')).toContain('[Feedback · Suggestion]')
  })

  it('buildEmailText includes the message and the from address', () => {
    const text = buildEmailText({
      category: 'Other',
      message: 'nice site',
      email: 'me@x.io',
      token: 't'
    })
    expect(text).toContain('nice site')
    expect(text).toContain('me@x.io')
  })
})
