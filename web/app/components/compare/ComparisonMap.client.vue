<script setup lang="ts">
/**
 * ComparisonMap - A single map panel for the comparison view
 *
 * Creates a MapLibre instance with:
 * - Shared zoom via useComparisonViewState (R4)
 * - Independent center per map (R5)
 * - City boundary highlighting for its assigned city
 * - deck.gl radial density layer (shared color scale across both maps)
 * - No click navigation (stays in comparison mode)
 * - City name label overlay in bottom-left corner
 */

import type { ShallowRef } from 'vue'
import type maplibregl from 'maplibre-gl'
import { CITY_A_COLOR, CITY_B_COLOR } from '~/utils/comparisonColors'
import { useMap } from '~/lib/map/useMap'
import { useDeckGL } from '~/lib/map/useDeckGL'
import { useRadialLayer } from '~/lib/map/useRadialLayer'

const props = defineProps<{
  cityId: string
  mapId: 'A' | 'B'
  isDarkMode: boolean
  sharedMaxDensity?: number
}>()

const mapContainer = shallowRef<HTMLElement | null>(null)

// Identity color for this map panel
const identityColor = computed(() => props.mapId === 'A' ? CITY_A_COLOR : CITY_B_COLOR)

// Initialize map with comparison-mode overrides
const { map, isLoading: isMapLoading, error: mapError } = useMap({
  container: mapContainer,
  cityId: props.cityId,
  disableClickNavigation: true,
  disableSelectionWatch: true,
  disableHoverSync: true,
  rightPanelWidth: 0, // No right panel overlap in comparison maps
  boundaryColor: identityColor.value.primary // Color boundaries with city identity
})

// deck.gl overlay for radial density layer
const { isInitialized: isDeckInitialized, setLayers } = useDeckGL({
  map: map as unknown as ShallowRef<maplibregl.Map | null>
})

// Radial density layer (toggled from ComparisonPanel)
const { isComparisonRadialActive } = useComparisonRadial()
const { selectedYear } = useSelectedYear()
const { getProfile } = useRadialProfiles()
const cityIdRef = computed(() => props.cityId)
const densityProfile = computed(() => getProfile(props.cityId, selectedYear.value))
const maxDensityRef = computed(() => props.sharedMaxDensity ?? 0)

const { layer: radialLayer } = useRadialLayer({
  cityId: cityIdRef,
  densityProfile,
  maxDensity: maxDensityRef,
  layerIdSuffix: props.mapId,
  alwaysActive: isComparisonRadialActive,
  disableHover: true,
})

// Push radial layer to deck.gl when ready
watch([radialLayer, isDeckInitialized], ([layer, initialized]) => {
  if (!initialized) return
  setLayers(layer ? [layer] : [])
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

    <!-- City name label overlay — bottom-left, colored with identity -->
    <div
      v-if="city"
      class="absolute bottom-3 left-3 z-10 px-3 py-1.5 rounded-lg
             bg-parchment/90 dark:bg-forest-950/90 backdrop-blur-sm shadow-sm
             flex items-center gap-2"
    >
      <span
        class="w-2.5 h-2.5 rounded-full shrink-0"
        :style="{ backgroundColor: identityColor.primary }"
      />
      <span class="text-sm font-medium leading-tight" :style="{ color: identityColor.primary }">
        {{ city.name }}<span class="opacity-50 font-normal">, {{ city.country }}</span>
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
