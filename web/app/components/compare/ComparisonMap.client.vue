<script setup lang="ts">
/**
 * ComparisonMap - A single map panel for the comparison view
 *
 * Creates a MapLibre instance with:
 * - Shared zoom via useComparisonViewState (R4)
 * - Independent center per map (R5)
 * - City boundary highlighting for its assigned city
 * - No deck.gl (no H3 heatmap or radial ring overlay)
 * - No click navigation (stays in comparison mode)
 * - City name label overlay in top-left corner
 */

import { CITY_A_COLOR, CITY_B_COLOR } from '~/utils/comparisonColors'

const props = defineProps<{
  cityId: string
  mapId: 'A' | 'B'
  isDarkMode: boolean
}>()

const mapContainer = shallowRef<HTMLElement | null>(null)

// Initialize map with comparison-mode overrides
const { map, isLoading: isMapLoading, error: mapError } = useMap({
  container: mapContainer,
  cityId: props.cityId,
  disableClickNavigation: true,
  disableSelectionWatch: true,
  disableHoverSync: true,
  rightPanelWidth: 0 // No right panel overlap in comparison maps
})

// Comparison view state for zoom sync
const {
  sharedZoom,
  onZoomChange,
  onPanChange,
  isZoomSource,
  clearZoomSource,
  setCenter
} = useComparisonViewState()

// City info for the label
const { getCity } = useCitiesIndex()
const city = computed(() => getCity(props.cityId))
const identityColor = computed(() => props.mapId === 'A' ? CITY_A_COLOR : CITY_B_COLOR)

// Track whether we're currently applying a zoom change from the other map
let isSyncingZoom = false

// Sync zoom from this map to the shared state
function setupZoomSync(mapInstance: maplibregl.Map) {
  // Use 'zoom' event (fires continuously during zoom) for real-time sync
  mapInstance.on('zoom', () => {
    if (isSyncingZoom) return
    onZoomChange(mapInstance.getZoom(), props.mapId)
  })

  // Sync pan (center) from this map to comparison state
  mapInstance.on('moveend', () => {
    const center = mapInstance.getCenter()
    onPanChange({ lng: center.lng, lat: center.lat }, props.mapId)
  })
}

// Watch shared zoom changes from the other map and apply instantly
watch(sharedZoom, (newZoom) => {
  if (!map.value) return
  if (isZoomSource(props.mapId)) return

  const currentZoom = map.value.getZoom()
  if (Math.abs(currentZoom - newZoom) < 0.01) return

  // Use jumpTo for instant sync — no animation delay
  isSyncingZoom = true
  map.value.jumpTo({ zoom: newZoom })
  isSyncingZoom = false
})

// Set initial center from city bbox after map loads
watch(map, (mapInstance) => {
  if (!mapInstance) return

  mapInstance.once('load', () => {
    const center = mapInstance.getCenter()
    setCenter({ lng: center.lng, lat: center.lat }, props.mapId)

    // Set initial shared zoom from the first map to load
    onZoomChange(mapInstance.getZoom(), props.mapId)

    setupZoomSync(mapInstance)
  })

  // If map already loaded (race condition), set up immediately
  if (mapInstance.loaded()) {
    const center = mapInstance.getCenter()
    setCenter({ lng: center.lng, lat: center.lat }, props.mapId)
    onZoomChange(mapInstance.getZoom(), props.mapId)
    setupZoomSync(mapInstance)
  }
})
</script>

<template>
  <div class="absolute inset-0 w-full h-full overflow-hidden">
    <!-- Map container -->
    <div
      ref="mapContainer"
      class="w-full h-full"
    />

    <!-- City name label overlay -->
    <div
      v-if="city"
      class="absolute top-3 left-3 z-10 px-3 py-1.5 rounded-lg
             bg-parchment/90 dark:bg-forest-950/90 backdrop-blur-sm shadow-sm
             flex items-center gap-2"
    >
      <span
        class="w-2.5 h-2.5 rounded-full shrink-0"
        :class="identityColor.dotClass"
      />
      <span class="text-sm font-medium text-body dark:text-cream leading-tight">
        {{ city.name }}
        <span class="text-body/50 dark:text-cream/50 font-normal">, {{ city.country }}</span>
      </span>
    </div>

    <!-- Loading indicator -->
    <div
      v-if="isMapLoading"
      class="absolute inset-0 flex items-center justify-center bg-parchment/90 z-10"
    >
      <UIcon
        name="i-lucide-loader-2"
        class="animate-spin text-2xl text-forest-600"
      />
    </div>

    <!-- Error display -->
    <div
      v-if="mapError"
      class="absolute inset-0 flex items-center justify-center bg-parchment/90 z-10"
    >
      <p class="text-sm text-red-500">{{ mapError.message }}</p>
    </div>
  </div>
</template>
