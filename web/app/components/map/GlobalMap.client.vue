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
      class="absolute inset-0 flex items-center justify-center bg-parchment/90 z-10"
    >
      <div class="flex flex-col items-center text-center">
        <UIcon
          name="i-lucide-loader-2"
          class="animate-spin text-4xl text-ink-600"
        />
        <p class="mt-2 text-body">
          Loading map...
        </p>
      </div>
    </div>

    <!-- Loading indicator for overlay data -->
    <div
      v-if="(isLoadingRadialCells || isLoadingH3) && !isMapLoading"
      class="absolute bottom-20 left-1/2 -translate-x-1/2 z-10
             bg-parchment/95 rounded-lg px-4 py-2.5 shadow-lg
             flex items-center gap-2.5"
    >
      <UIcon
        name="i-lucide-loader-2"
        class="animate-spin text-lg text-ink-600 dark:text-ink-400"
      />
      <span class="text-sm text-body dark:text-cream font-medium">
        {{ isLoadingH3 ? 'Loading population data...' : 'Loading radial cells...' }}
      </span>
    </div>

    <!-- Error display -->
    <div
      v-if="displayError"
      class="absolute inset-0 flex items-center justify-center bg-parchment/90 z-10"
    >
      <div class="flex flex-col items-center text-center">
        <UIcon
          name="i-lucide-alert-triangle"
          class="text-4xl text-red-500"
        />
        <p class="mt-2 text-body">
          {{ displayError.message }}
        </p>
      </div>
    </div>

    <!-- Map attribution -->
    <DataAttribution />
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
import { useMap } from '~/lib/map/useMap'
import { useDeckGL } from '~/lib/map/useDeckGL'
import { useRadialLayer } from '~/lib/map/useRadialLayer'
import { usePopulationLayer } from '~/lib/map/usePopulationLayer'

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
const { viewState, onViewStateChange, shouldAnimate, animationDuration, clearAnimationFlag } = useViewState()

// Radial layer (activated when sidebar toggle is clicked)
const { selectedCityId } = useCitySelection()
const { selectedYear } = useSelectedYear()
const { getProfile, getMaxDensity } = useRadialProfiles()
const densityProfile = computed(() => selectedCityId.value ? getProfile(selectedCityId.value, selectedYear.value) : null)
const radialMaxDensity = computed(() => selectedCityId.value ? getMaxDensity(selectedCityId.value, selectedYear.value) : 0)
const { layer: radialLayer, isLoadingCells: isLoadingRadialCells } = useRadialLayer({
  densityProfile,
  maxDensity: radialMaxDensity,
})
const { isRadialLayerActive } = useRadialHighlight()

// Population heatmap layer (activated when sidebar toggle is clicked)
const { layer: populationLayer } = usePopulationLayer({
  isDarkMode: computed(() => props.isDarkMode ?? false),
})
const { isPopulationLayerActive, isLoadingH3 } = usePopulationHighlight()

// Boundary layer IDs to toggle when radial layer is active
const BOUNDARY_LAYERS = [
  'city-boundaries-hover-pattern',
  'city-boundaries-line',
  'city-labels'
]

// Local state for dark mode (can be controlled via prop or internal)
const _isDarkMode = computed(() => props.isDarkMode ?? false)

// Error display
const displayError = computed(() => mapError.value)

// Current layers array for deck.gl
const currentLayer = shallowRef<Layer | null>(null)

// Track if we're programmatically updating the map (to avoid feedback loop)
let isUpdatingFromViewState = false

// Zoom constants
const ZOOM_STEP = 0.5
const MIN_ZOOM = 0.5
const MAX_ZOOM = 18

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

// Watch overlay layers (radial + population) and update deck.gl
watch([radialLayer, populationLayer], ([radial, population]) => {
  if (!isDeckInitialized.value) return
  const layers: Layer[] = []
  if (currentLayer.value) layers.push(currentLayer.value)
  if (radial) layers.push(radial)
  if (population) layers.push(population)
  setLayers(layers)
})

// Toggle boundary layer visibility when overlay layers are active
watch([isRadialLayerActive, isPopulationLayerActive], ([radialActive, popActive]) => {
  const mapInstance = map.value
  if (!mapInstance) return
  const visibility = (radialActive || popActive) ? 'none' : 'visible'
  for (const layerId of BOUNDARY_LAYERS) {
    if (mapInstance.getLayer(layerId)) {
      mapInstance.setLayoutProperty(layerId, 'visibility', visibility)
    }
  }
})

// Watch for view state changes and update map
watch(
  () => viewState.value,
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
      if (shouldAnimate.value) {
        // Smooth animated transition for snap-to-level actions
        map.value.easeTo({
          center: [newViewState.longitude, newViewState.latitude],
          zoom: newViewState.zoom,
          duration: animationDuration
        })
        clearAnimationFlag()
      } else {
        // Instant transition for slider dragging
        map.value.jumpTo({
          center: [newViewState.longitude, newViewState.latitude],
          zoom: newViewState.zoom
        })
      }
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

    // Real-time zoom sync for smooth slider updates during zooming
    mapInstance.on('zoom', () => {
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
