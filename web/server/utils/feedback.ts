/**
 * Feedback submission core logic.
 *
 * Pure, dependency-injected request handling so the validate → verify → send
 * flow can be unit-tested without Nitro, Turnstile, or Resend. The Nitro
 * handler (server/api/feedback.post.ts) is a thin wrapper that supplies the
 * real Turnstile verify and Resend send implementations.
 */

import type { FeedbackContext } from '../../types/feedback'

/** Allowed feedback categories (R4). Server never trusts the client. */
export const FEEDBACK_CATEGORIES = ['Data issue', 'Question', 'Suggestion', 'Other'] as const
export type FeedbackCategory = (typeof FEEDBACK_CATEGORIES)[number]

/** Pragmatic syntactic email check — local@domain.tld with no spaces. */
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

/** Bound the message so a single submission can't bloat the email or burn quota. */
const MAX_MESSAGE_LENGTH = 5000

/** Cap for any single user-supplied context string rendered into the email. */
const MAX_CONTEXT_FIELD = 2000

export interface FeedbackPayload {
  category: FeedbackCategory
  message: string
  email: string
  token: string
  context?: FeedbackContext
}

export interface ResendEmail {
  from: string
  to: string
  reply_to: string
  subject: string
  text: string
}

export interface FeedbackConfig {
  resendFrom: string
  feedbackToEmail: string
}

export interface FeedbackDeps {
  /** Resolve true only when the Turnstile token verifies (R13). */
  verifyToken: (token: string) => Promise<boolean>
  /** Deliver the email; ok=false signals a delivery failure. */
  sendEmail: (email: ResendEmail) => Promise<{ ok: boolean, status: number }>
}

export interface FeedbackResult {
  status: number
  body: Record<string, unknown>
}

export function isValidEmail(email: unknown): email is string {
  return typeof email === 'string' && EMAIL_RE.test(email.trim())
}

/**
 * Validate a raw request body into a typed payload, or return an error reason.
 */
export function validateFeedbackPayload(
  body: unknown
): { ok: true, payload: FeedbackPayload } | { ok: false, error: string } {
  if (!body || typeof body !== 'object') {
    return { ok: false, error: 'Malformed request body' }
  }

  const { category, message, email, token, context } = body as Record<string, unknown>

  if (typeof category !== 'string' || !FEEDBACK_CATEGORIES.includes(category as FeedbackCategory)) {
    return { ok: false, error: 'Invalid category' }
  }
  if (typeof message !== 'string' || message.trim().length === 0) {
    return { ok: false, error: 'Message is required' }
  }
  if (message.trim().length > MAX_MESSAGE_LENGTH) {
    return { ok: false, error: 'Message is too long' }
  }
  if (!isValidEmail(email)) {
    return { ok: false, error: 'A valid email is required' }
  }
  if (typeof token !== 'string' || token.trim().length === 0) {
    return { ok: false, error: 'Missing verification token' }
  }

  return {
    ok: true,
    payload: {
      category: category as FeedbackCategory,
      message: message.trim(),
      email: (email as string).trim(),
      token,
      context: context as FeedbackContext | undefined
    }
  }
}

/** Subject line surfaces the category for inbox triage (R11). */
export function buildSubject(category: FeedbackCategory, message: string): string {
  const snippet = message.replace(/\s+/g, ' ').trim().slice(0, 60)
  return `[Feedback · ${category}] ${snippet}`
}

/** Coerce a user-supplied context value to a bounded string, or drop it. */
function safeField(value: unknown): string | undefined {
  if (typeof value !== 'string') return undefined
  const trimmed = value.trim()
  return trimmed ? trimmed.slice(0, MAX_CONTEXT_FIELD) : undefined
}

/**
 * Render the optional page context as readable lines (only present fields).
 * Context is fully user-controlled, so every field is type-checked and length-
 * capped at runtime — the TypeScript shape is not a runtime guarantee.
 */
export function renderContextText(context?: FeedbackContext): string {
  if (!context || typeof context !== 'object') return ''
  const lines: string[] = []

  const url = safeField(context.url)
  if (url) lines.push(`Page: ${url}`)

  if (context.city && typeof context.city === 'object') {
    const id = safeField(context.city.id)
    const name = safeField(context.city.name)
    if (id || name) {
      lines.push(`City: ${name && id ? `${name} (${id})` : (name ?? id)}`)
    }
  }

  const dataset = safeField(context.dataset)
  if (dataset) lines.push(`Dataset: ${dataset}`)

  if (typeof context.epoch === 'number' && Number.isFinite(context.epoch)) {
    lines.push(`Epoch: ${context.epoch}`)
  }

  return lines.join('\n')
}

/** Compose the full email body: the message plus a context block. */
export function buildEmailText(payload: FeedbackPayload): string {
  const parts = [
    `Category: ${payload.category}`,
    `From: ${payload.email}`,
    '',
    payload.message
  ]
  const context = renderContextText(payload.context)
  if (context) {
    parts.push('', '— Context —', context)
  }
  return parts.join('\n')
}

/**
 * Validate → verify Turnstile → send via Resend. Returns a status + body
 * instead of throwing, so both the handler and tests consume one shape.
 */
export async function handleFeedbackRequest(
  body: unknown,
  config: FeedbackConfig,
  deps: FeedbackDeps
): Promise<FeedbackResult> {
  const validated = validateFeedbackPayload(body)
  if (!validated.ok) {
    return { status: 400, body: { error: validated.error } }
  }
  const payload = validated.payload

  // R13 / AE5 — reject before any email is sent. Fail closed: a verification
  // error (e.g. Cloudflare unreachable) never falls through to sending.
  let verified = false
  try {
    verified = await deps.verifyToken(payload.token)
  } catch {
    return { status: 503, body: { error: 'Could not verify your submission. Please try again.' } }
  }
  if (!verified) {
    return { status: 403, body: { error: 'Verification failed' } }
  }

  const email: ResendEmail = {
    from: config.resendFrom,
    to: config.feedbackToEmail,
    reply_to: payload.email,
    subject: buildSubject(payload.category, payload.message),
    text: buildEmailText(payload)
  }

  const sent = await deps.sendEmail(email)
  if (!sent.ok) {
    return { status: 502, body: { error: 'Could not deliver feedback. Please try again later.' } }
  }

  return { status: 200, body: { ok: true } }
}
