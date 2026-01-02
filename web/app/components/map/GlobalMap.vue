<template>
  <div class="global-map">
    <!-- Map container -->
    <div
      ref="mapContainer"
      class="map-container"
    />

    <!-- H3 Population Layer (renderless) -->
    <H3PopulationLayer
      v-if="isDeckInitialized"
      :is-dark-mode="isDarkMode"
      @layer-update="onH3LayerUpdate"
    />

    <!-- Loading indicator for map -->
    <div
      v-if="isMapLoading"
      class="loading-overlay"
    >
      <div class="loading-spinner">
        <UIcon
          name="i-lucide-loader-2"
          class="animate-spin text-4xl text-forest-600"
        />
        <p class="mt-2 text-body">
          Loading map...
        </p>
      </div>
    </div>

    <!-- Loading indicator for H3 data -->
    <div
      v-else-if="isH3Loading"
      class="loading-overlay loading-overlay--data"
    >
      <div class="loading-content">
        <UIcon
          name="i-lucide-loader-2"
          class="animate-spin text-4xl text-forest-600"
        />
        <p class="mt-2 text-body font-medium">
          Loading population data...
        </p>
        <div class="progress-bar mt-4">
          <div
            class="progress-fill"
            :style="{ width: `${h3LoadProgress}%` }"
          />
        </div>
        <p class="mt-2 text-sm text-body opacity-70">
          {{ h3LoadProgress }}% complete
        </p>
      </div>
    </div>

    <!-- Error display -->
    <div
      v-if="displayError"
      class="error-overlay"
    >
      <div class="error-content">
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
  currentLayer.value = layer

  // Update deck.gl layers
  if (isDeckInitialized.value) {
    const layersArray = layer ? [layer] : []
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

// Start loading H3 data when map is ready
watch(
  () => isMapLoading.value,
  (loading) => {
    if (!loading && !mapError.value) {
      // Map is loaded, start loading data
      loadH3Data().catch(() => {
        // Error is handled in the composable
      })
    }
  },
  { immediate: true }
)

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

<style scoped>
.global-map {
  position: fixed;
  inset: 0;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}

.map-container {
  width: 100%;
  height: 100%;
}

.loading-overlay,
.error-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(245, 241, 230, 0.9); /* Parchment with opacity */
  z-index: 10;
}

.loading-overlay--data {
  background-color: rgba(245, 241, 230, 0.85);
}

.loading-spinner,
.loading-content,
.error-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.loading-content {
  min-width: 250px;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background-color: rgba(154, 147, 133, 0.3); /* Border color with opacity */
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background-color: var(--color-forest-600, #4A6741);
  border-radius: 4px;
  transition: width 0.3s ease-out;
}

/* Dark mode styles for loading overlays */
:global(.dark) .loading-overlay,
:global(.dark) .error-overlay {
  background-color: rgba(61, 53, 44, 0.9); /* Espresso with opacity */
}

:global(.dark) .loading-overlay--data {
  background-color: rgba(61, 53, 44, 0.85);
}

:global(.dark) .progress-bar {
  background-color: rgba(154, 147, 133, 0.2);
}

:global(.dark) .progress-fill {
  background-color: var(--color-forest-500, #6A8F5E);
}
</style>
