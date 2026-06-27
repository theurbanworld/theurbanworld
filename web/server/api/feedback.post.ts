/**
 * POST /api/feedback
 *
 * Validates a feedback submission, verifies its Cloudflare Turnstile token,
 * and emails it to the maintainer via Resend. No persistence — the inbox is
 * the system of record. Core flow lives in server/utils/feedback.ts; this
 * handler just supplies the real Turnstile + Resend implementations and reads
 * config/secrets via useRuntimeConfig (KTD5).
 */

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const config = useRuntimeConfig(event)

  const result = await handleFeedbackRequest(
    body,
    {
      resendFrom: config.resendFrom,
      feedbackToEmail: config.feedbackToEmail
    },
    {
      verifyToken: async (token) => {
        const res = await verifyTurnstileToken(token, event)
        return res.success === true
      },
      sendEmail: async (email) => {
        try {
          await $fetch('https://api.resend.com/emails', {
            method: 'POST',
            headers: {
              // Never logged — keeps the API key out of error output.
              'authorization': `Bearer ${config.resendApiKey}`,
              'content-type': 'application/json'
            },
            body: email
          })
          return { ok: true, status: 200 }
        } catch (err) {
          const status = (err as { statusCode?: number, status?: number })?.statusCode
            ?? (err as { status?: number })?.status
            ?? 502
          return { ok: false, status }
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
