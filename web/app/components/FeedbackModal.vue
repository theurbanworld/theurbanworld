<script setup lang="ts">
/**
 * FeedbackModal — global feedback widget modal.
 *
 * Mounted once in app.vue beside <InfoModal />. Opens via useFeedback().open()
 * from either entry point (desktop button, mobile drawer item). Hosts the
 * minimal form — category pills, message, required email, Turnstile — and the
 * success/error states. Form logic lives in useFeedbackForm; page context is
 * captured at submit time by useFeedbackContext.
 */

const { isOpen, close } = useFeedback()
const {
  category,
  message,
  email,
  token,
  status,
  categories,
  canSubmit,
  showEmailError,
  showMessageError,
  setCategory,
  reset,
  submit
} = useFeedbackForm()

// Re-mount the Turnstile widget after a submit settles so a retry re-solves
// (tokens are single-use) and on each fresh open.
const turnstileKey = ref(0)
watch(status, (value) => {
  if (value === 'success' || value === 'error') turnstileKey.value++
})

// Reset to a clean form each time the modal opens.
watch(isOpen, (open) => {
  if (open) reset()
})

function sendAnother() {
  reset()
  turnstileKey.value++
}
</script>

<template>
  <UModal v-model:open="isOpen">
    <template #content>
      <div class="relative">
        <CloseButton
          class="absolute top-3 right-3 z-10"
          aria-label="Close feedback"
          @click="close"
        />

        <div class="p-6 max-h-[80vh] overflow-y-auto">
          <!-- Success state -->
          <div
            v-if="status === 'success'"
            class="flex flex-col items-center text-center gap-3 py-6"
          >
            <UIcon
              name="i-lucide-check-circle"
              class="w-10 h-10 text-forest-600 dark:text-forest-400"
            />
            <h2 class="text-lg font-semibold text-ink-700 dark:text-ink-200">
              Thanks for the feedback
            </h2>
            <p class="text-sm text-body/60 dark:text-cream/60 max-w-xs">
              Your message is on its way. We read every note and reply by email when one's needed.
            </p>
            <div class="flex gap-2 mt-2">
              <UButton
                variant="soft"
                color="neutral"
                @click="sendAnother"
              >
                Send another
              </UButton>
              <UButton
                color="primary"
                @click="close"
              >
                Done
              </UButton>
            </div>
          </div>

          <!-- Form state -->
          <form
            v-else
            class="flex flex-col gap-4"
            @submit.prevent="submit()"
          >
            <div>
              <h2 class="text-lg font-semibold text-ink-700 dark:text-ink-200">
                Send feedback
              </h2>
              <p class="text-sm text-body/60 dark:text-cream/60">
                Spotted a wrong number, have a question, or an idea? Let us know.
              </p>
            </div>

            <div>
              <span class="block text-xs font-semibold uppercase tracking-wider text-body/60 dark:text-cream/60 mb-1.5">
                Category
              </span>
              <div class="flex flex-wrap gap-2">
                <button
                  v-for="cat in categories"
                  :key="cat"
                  type="button"
                  class="px-3 py-1.5 rounded-full text-sm font-medium border transition-colors cursor-pointer"
                  :class="category === cat
                    ? 'border-forest-500 dark:border-forest-400 bg-forest-50/60 dark:bg-forest-950/40 text-forest-700 dark:text-forest-300 ring-1 ring-forest-500/30'
                    : 'border-ink-200/50 dark:border-ink-800/50 text-body/70 dark:text-cream/70 hover:border-forest-300 dark:hover:border-forest-700 hover:bg-forest-50/30 dark:hover:bg-forest-950/20'"
                  :aria-pressed="category === cat"
                  @click="setCategory(cat)"
                >
                  {{ cat }}
                </button>
              </div>
            </div>

            <UFormField
              label="Message"
              :error="showMessageError ? 'Please enter a message' : undefined"
              required
            >
              <UTextarea
                v-model="message"
                :rows="4"
                class="w-full"
                placeholder="What's on your mind?"
              />
            </UFormField>

            <UFormField
              label="Your email"
              :error="showEmailError ? 'A valid email is required so we can reply' : undefined"
              required
            >
              <UInput
                v-model="email"
                type="email"
                autocomplete="email"
                class="w-full"
                placeholder="you@example.com"
              />
            </UFormField>

            <!-- Mounted only while the modal is open so the Cloudflare script
                 isn't loaded on pages where feedback is never opened. -->
            <NuxtTurnstile
              v-if="isOpen"
              :key="turnstileKey"
              v-model="token"
            />

            <p
              v-if="status === 'error'"
              class="text-sm text-red-600 dark:text-red-400"
            >
              Something went wrong sending your feedback. Please try again.
            </p>

            <UButton
              type="submit"
              block
              color="primary"
              :loading="status === 'submitting'"
              :disabled="!canSubmit"
            >
              Send feedback
            </UButton>
          </form>
        </div>
      </div>
    </template>
  </UModal>
</template>
