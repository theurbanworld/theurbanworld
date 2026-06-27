/**
 * useFeedbackForm — form state, validation, and submission for the feedback widget.
 *
 * Holds the three fields (category, message, email) plus the Turnstile token,
 * gates submission on a syntactically valid email + non-empty message (R6/AE1),
 * attaches best-effort page context (R8/R9), and posts to /api/feedback,
 * surfacing success/error states (R12). Kept separate from the .vue so the
 * logic is unit-testable without mounting the modal.
 *
 * The category list is defined independently here from the server's copy —
 * the endpoint never trusts the client, so the trust boundary is intentional.
 */

export const FEEDBACK_CATEGORIES = ['Data issue', 'Question', 'Suggestion', 'Other'] as const
export type FeedbackCategory = (typeof FEEDBACK_CATEGORIES)[number]

export type FeedbackStatus = 'idle' | 'submitting' | 'success' | 'error'

/** Pragmatic syntactic email check — mirrors the server's isValidEmail. */
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export function useFeedbackForm() {
  const { captureContext } = useFeedbackContext()

  const category = ref<FeedbackCategory>('Data issue')
  const message = ref('')
  const email = ref('')
  const token = ref('')
  const status = ref<FeedbackStatus>('idle')
  const attemptedSubmit = ref(false)

  const emailValid = computed(() => EMAIL_RE.test(email.value.trim()))
  const messageValid = computed(() => message.value.trim().length > 0)

  /** Submit is gated on a valid message + email (R6); never on the token. */
  const canSubmit = computed(() =>
    messageValid.value && emailValid.value && status.value !== 'submitting'
  )

  // Field-level errors only surface after a submit attempt (AE1).
  const showEmailError = computed(() => attemptedSubmit.value && !emailValid.value)
  const showMessageError = computed(() => attemptedSubmit.value && !messageValid.value)

  function setCategory(value: FeedbackCategory) {
    category.value = value
  }

  /** Clear the form for a fresh open or a "send another". */
  function reset() {
    category.value = 'Data issue'
    message.value = ''
    email.value = ''
    token.value = ''
    status.value = 'idle'
    attemptedSubmit.value = false
  }

  async function submit() {
    attemptedSubmit.value = true
    // R6 / AE1 — block the POST until message + email are valid.
    if (!messageValid.value || !emailValid.value) return

    status.value = 'submitting'
    try {
      await $fetch('/api/feedback', {
        method: 'POST',
        body: {
          category: category.value,
          message: message.value.trim(),
          email: email.value.trim(),
          token: token.value,
          context: captureContext()
        }
      })
      status.value = 'success'
    } catch {
      status.value = 'error'
    } finally {
      // Turnstile tokens are single-use; clear so a retry re-solves (U5 risk).
      token.value = ''
    }
  }

  return {
    category,
    message,
    email,
    token,
    status,
    categories: FEEDBACK_CATEGORIES,
    emailValid,
    messageValid,
    canSubmit,
    showEmailError,
    showMessageError,
    setCategory,
    reset,
    submit
  }
}
