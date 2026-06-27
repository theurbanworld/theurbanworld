<script setup lang="ts">
/**
 * ClimateEnergySection — the "Climate & Energy" city-page section.
 *
 * Tiered: the four headline metrics (heat, flood, solar, per-capita carbon) lead;
 * the rest is supporting depth in collapsible lens groups. Each metric dispatches
 * on its temporal class (series / projection / snapshot) via ClimateMetricCard.
 * Per-capita CO₂ composes its sector fingerprint inline (R15 — cannot ship apart).
 *
 * Mounted feature-gated by CityInfoPanel. Per-city absence renders a whole-section
 * unavailable note rather than broken cards (R13).
 */

import { useCityClimate } from '../../composables/useCityClimate'
import type { SectorValue } from '../../../types/climate'
import {
  headlineMetrics,
  supportingMetrics,
  getMetricDescriptor,
  LENS_ORDER,
  LENS_LABELS,
  CARBON_HEADLINE_KEY,
  CO2_SECTOR_FINGERPRINT_KEY
} from '../../../types/climate'

const props = defineProps<{
  cityId: string
}>()

const { open: openInfoModal } = useInfoModal()
const { loadProfile, getClimate, hasCityClimate } = useCityClimate()

// Load the full per-city profile on mount and whenever the city changes.
onMounted(() => {
  loadProfile()
})

const record = computed(() => getClimate(props.cityId))
const covered = computed(() => hasCityClimate(props.cityId) || record.value != null)

const headlines = headlineMetrics()
const carbonKey = CARBON_HEADLINE_KEY
const fingerprintDescriptor = getMetricDescriptor(CO2_SECTOR_FINGERPRINT_KEY)
const fingerprint = computed(
  () => (record.value?.[CO2_SECTOR_FINGERPRINT_KEY] as SectorValue | undefined) ?? null
)

const lensGroups = computed(() =>
  LENS_ORDER.map(lens => ({
    lens,
    label: LENS_LABELS[lens],
    metrics: supportingMetrics(lens)
  })).filter(g => g.metrics.length > 0)
)
</script>

<template>
  <section
    data-testid="climate-energy-section"
    class="border-t border-border/30 dark:border-border/20 pt-4"
  >
    <div class="flex items-center gap-1.5 mb-3">
      <h2 class="text-sm font-medium text-ink-700 dark:text-ink-300">
        Climate &amp; Energy
      </h2>
      <button
        class="text-body/40 dark:text-cream/40 hover:text-ink-600 dark:hover:text-ink-400 transition-colors cursor-pointer"
        aria-label="About the Climate & Energy profile"
        @click="openInfoModal('/methodology/climate-energy')"
      >
        <UIcon
          name="i-lucide-info"
          class="w-3.5 h-3.5"
        />
      </button>
    </div>

    <!-- Whole-section unavailable (R13) -->
    <p
      v-if="!covered"
      data-testid="climate-section-unavailable"
      class="text-xs italic text-body/40 dark:text-cream/40"
    >
      Climate &amp; Energy data is not available for this city.
    </p>

    <template v-else>
      <!-- Headline four -->
      <div
        data-testid="climate-headlines"
        class="flex flex-col gap-4"
      >
        <div
          v-for="metric in headlines"
          :key="metric.key"
        >
          <ClimateMetricCard
            :descriptor="metric"
            :value="record?.[metric.key]"
          />
          <!-- Per-capita CO₂ carries its sector fingerprint inline -->
          <ClimateSectorFingerprint
            v-if="metric.key === carbonKey && fingerprint && fingerprintDescriptor"
            :value="fingerprint"
            class="mt-2"
          />
        </div>
      </div>

      <!-- Supporting lenses (collapsible) -->
      <div class="flex flex-col gap-3 mt-4">
        <ClimateMetricGroup
          v-for="group in lensGroups"
          :key="group.lens"
          :label="group.label"
          :metrics="group.metrics"
          :record="record"
        />
      </div>
    </template>
  </section>
</template>
