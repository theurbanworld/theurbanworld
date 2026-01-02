<template>
  <div class="absolute inset-0 w-full h-full overflow-hidden">
    <!-- Map container -->
    <div
      ref="mapContainer"
      class="w-full h-full"
    />

    <!-- H3 Population Layer (disabled for debugging hover)
    <H3PopulationLayer
      v-if="isDeckInitialized"
      :is-dark-mode="isDarkMode"
      @layer-update="onH3LayerUpdate"
    />
    -->

    <!-- Loading indicator for map -->
    <div
      v-if="isMapLoading"
      class="absolute inset-0 flex items-center justify-center bg-parchment/90 dark:bg-espresso/90 z-10"
    >
      <div class="flex flex-col items-center text-center">
        <UIcon
          name="i-lucide-loader-2"
          class="animate-spin text-4xl text-forest-600"
        />
        <p class="mt-2 text-body">
          Loading map...
        </p>
      </div>
    </div>

    <!-- Loading indicator for H3 data (disabled)
    <div
      v-else-if="isH3Loading"
      class="absolute inset-0 flex items-center justify-center bg-parchment/85 dark:bg-espresso/85 z-10"
    >
      <div class="flex flex-col items-center text-center min-w-[250px]">
        <UIcon
          name="i-lucide-loader-2"
          class="animate-spin text-4xl text-forest-600"
        />
        <p class="mt-2 text-body font-medium">
          Loading population data...
        </p>
        <div class="w-full h-2 bg-border/30 dark:bg-border/20 rounded overflow-hidden mt-4">
          <div
            class="h-full bg-forest-600 dark:bg-forest-500 rounded transition-[width] duration-300 ease-out"
            :style="{ width: `${h3LoadProgress}%` }"
          />
        </div>
        <p class="mt-2 text-sm text-body opacity-70">
          {{ h3LoadProgress }}% complete
        </p>
      </div>
    </div>
    -->

    <!-- Error display -->
    <div
      v-if="displayError"
      class="absolute inset-0 flex items-center justify-center bg-parchment/90 dark:bg-espresso/90 z-10"
    >
      <div class="flex flex-col items-center text-center">
        <UIcon
          name="i-lucide-alert-triangle"
          class="text-4xl text-red-500"
        />
        <p class="mt-2 text-body">
          {{ displayError.message }}
        </p>
        <UButton
          v-if="h3Error"
          class="mt-4"
          color="primary"
          @click="retryLoadH3Data"
        >
          Retry Loading Data
        </UButton>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * GlobalMap - Main map container component
 *
 * Initializes MapLibre basemap with sepia theme and deck.gl overlay.
 * Integrates H3 population layer with loading states.
 * Includes city boundaries with labels and hover highlighting.
 * Fills entire viewport with position: fixed for no scroll.
 * Supports keyboard shortcuts for zoom (+/- keys).
 */

import type maplibregl from 'maplibre-gl'
import type { Layer } from '@deck.gl/core'
import type { ShallowRef } from 'vue'

// Props for configuration
const props = defineProps<{
  /** Whether dark mode is enabled (for H3 layer color inversion) */
  isDarkMode?: boolean
}>()

// Template ref for map container
const mapContainer = ref<HTMLElement | null>(null)

// Initialize MapLibre map (includes city boundaries layer)
const { map, isLoading: isMapLoading, error: mapError } = useMap({
  container: mapContainer as ShallowRef<HTMLElement | null>
})

// Initialize deck.gl overlay (waits for map to be ready)
const { isInitialized: isDeckInitialized, setLayers } = useDeckGL({
  map: map as unknown as ShallowRef<maplibregl.Map | null>
})

// View state management
const { viewState, onViewStateChange } = useViewState()

// H3 data loading
const {
  isLoading: isH3Loading,
  loadProgress: h3LoadProgress,
  error: h3Error,
  loadData: loadH3Data
} = useH3Data()

// Local state for dark mode (can be controlled via prop or internal)
const isDarkMode = computed(() => props.isDarkMode ?? false)

// Combined error display
const displayError = computed(() => mapError.value || h3Error.value)

// Current layers array for deck.gl
const currentLayer = shallowRef<Layer | null>(null)

// Track if we're programmatically updating the map (to avoid feedback loop)
let isUpdatingFromViewState = false

// Zoom constants
const ZOOM_STEP = 0.5
const MIN_ZOOM = 0.5
const MAX_ZOOM = 18

/**
 * Handle H3 layer updates from the renderless component
 */
function onH3LayerUpdate(layer: Layer | null) {
  console.log('[GlobalMap] onH3LayerUpdate called, layer:', layer ? 'exists' : 'null', 'isDeckInitialized:', isDeckInitialized.value)
  currentLayer.value = layer

  // Update deck.gl layers
  if (isDeckInitialized.value) {
    const layersArray = layer ? [layer] : []
    console.log('[GlobalMap] Calling setLayers with', layersArray.length, 'layers')
    setLayers(layersArray as Layer[])
  }
}

/**
 * Retry loading H3 data after an error
 */
async function retryLoadH3Data() {
  try {
    await loadH3Data()
  } catch {
    // Error is handled in the composable
  }
}

/**
 * Zoom in the map
 */
function zoomIn() {
  const currentZoom = map.value?.getZoom() ?? viewState.value.zoom
  const newZoom = Math.min(currentZoom + ZOOM_STEP, MAX_ZOOM)
  if (map.value) {
    map.value.zoomTo(newZoom, { duration: 200 })
  }
}

/**
 * Zoom out the map
 */
function zoomOut() {
  const currentZoom = map.value?.getZoom() ?? viewState.value.zoom
  const newZoom = Math.max(currentZoom - ZOOM_STEP, MIN_ZOOM)
  if (map.value) {
    map.value.zoomTo(newZoom, { duration: 200 })
  }
}

/**
 * Handle keyboard shortcuts for zoom
 */
function handleKeydown(event: KeyboardEvent) {
  // Ignore if user is typing in an input field
  const target = event.target as HTMLElement
  if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
    return
  }

  // Check for zoom shortcuts
  if (event.key === '+' || event.key === '=') {
    event.preventDefault()
    zoomIn()
  } else if (event.key === '-') {
    event.preventDefault()
    zoomOut()
  }
}

// Watch for deck.gl initialization and update layers
watch(isDeckInitialized, (initialized) => {
  if (initialized && currentLayer.value) {
    setLayers([currentLayer.value] as Layer[])
  }
})

// Start loading H3 data when map is ready (disabled for debugging hover)
// watch(
//   () => isMapLoading.value,
//   (loading) => {
//     if (!loading && !mapError.value) {
//       // Map is loaded, start loading data
//       loadH3Data().catch(() => {
//         // Error is handled in the composable
//       })
//     }
//   },
//   { immediate: true }
// )

// Watch for view state changes and update map
watch(
  viewState,
  (newViewState) => {
    if (!map.value || isUpdatingFromViewState) return

    isUpdatingFromViewState = true

    const currentCenter = map.value.getCenter()
    const currentZoom = map.value.getZoom()

    // Only update if values actually changed (avoid unnecessary updates)
    const centerChanged
      = Math.abs(currentCenter.lng - newViewState.longitude) > 0.0001
        || Math.abs(currentCenter.lat - newViewState.latitude) > 0.0001
    const zoomChanged = Math.abs(currentZoom - newViewState.zoom) > 0.01

    if (centerChanged || zoomChanged) {
      map.value.jumpTo({
        center: [newViewState.longitude, newViewState.latitude],
        zoom: newViewState.zoom
      })
    }

    isUpdatingFromViewState = false
  },
  { deep: true }
)

// Sync map movements back to view state
watch(
  () => map.value,
  (mapInstance) => {
    if (!mapInstance) return

    mapInstance.on('moveend', () => {
      if (isUpdatingFromViewState) return

      const center = mapInstance.getCenter()
      const zoom = mapInstance.getZoom()

      onViewStateChange({
        longitude: center.lng,
        latitude: center.lat,
        zoom: zoom,
        pitch: 0,
        bearing: 0
      })
    })
  },
  { immediate: true }
)

// Register keyboard event listeners
onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})

// Expose map and deck.gl for parent components to use
defineExpose({
  map,
  setLayers,
  isDeckInitialized,
  currentLayer,
  zoomIn,
  zoomOut
})
</script>
