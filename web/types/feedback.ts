/**
 * Shared feedback types.
 *
 * Lives in the neutral types/ layer so both the client composable
 * (app/composables/useFeedbackContext.ts) and the server util
 * (server/utils/feedback.ts) can reference the same shape without the server
 * typecheck dragging in client-only globals (window, app auto-imports).
 */

export interface FeedbackContext {
  /** Always present — the page the user submitted from. */
  url: string
  /** Present only when a city is selected; name omitted if unresolved. */
  city?: { id: string, name?: string }
  /** Active dataset display label (e.g. "Urban World v1"). */
  dataset?: string
  /** Selected year epoch. */
  epoch?: number
}
