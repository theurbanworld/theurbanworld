/**
 * POST /api/feedback
 *
 * Validates a feedback submission, verifies its Cloudflare Turnstile token,
 * and emails it to the maintainer via the Cloudflare Email Service `send_email`
 * binding (configured as `EMAIL` in wrangler.toml). No persistence — the inbox
 * is the system of record. Core flow lives in server/utils/feedback.ts; this
 * handler supplies the real Turnstile verify + email send and reads config via
 * useRuntimeConfig (KTD5).
 */

/** Minimal shape of the Cloudflare Email Service `send_email` binding. */
interface SendEmailBinding {
  send: (message: {
    from: string
    to: string
    replyTo?: string
    subject: string
    text?: string
    html?: string
  }) => Promise<{ messageId: string }>
}

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const config = useRuntimeConfig(event)

  const cloudflare = event.context.cloudflare as { env?: Record<string, unknown> } | undefined
  const emailBinding = cloudflare?.env?.EMAIL as SendEmailBinding | undefined

  // Operator misconfiguration (missing binding or sender/recipient) — fail
  // loudly server-side rather than silently 502-ing every submission.
  if (!emailBinding || !config.feedbackFromEmail || !config.feedbackToEmail) {
    console.error('[feedback] email service not configured; submission rejected')
    throw createError({ statusCode: 500, statusMessage: 'Feedback service is not configured' })
  }

  const result = await handleFeedbackRequest(
    body,
    {
      fromEmail: config.feedbackFromEmail,
      toEmail: config.feedbackToEmail
    },
    {
      verifyToken: async (token) => {
        const res = await verifyTurnstileToken(token, event)
        return res.success === true
      },
      sendEmail: async (email) => {
        try {
          await emailBinding.send(email)
          return { ok: true, status: 200 }
        } catch (err) {
          // CF Email Service throws on send (e.g. unverified destination, or a
          // `from` not on an Email-Routing domain). Log code + message for
          // diagnostics (`wrangler tail`); never surface it to the client.
          const e = err as { code?: string, message?: string }
          console.error('[feedback] email send failed:', e?.code, e?.message)
          return { ok: false, status: 502 }
        }
      }
    }
  )

  if (result.status >= 400) {
    throw createError({
      statusCode: result.status,
      statusMessage: String(result.body.error ?? 'Feedback submission failed')
    })
  }

  setResponseStatus(event, result.status)
  return result.body
})
