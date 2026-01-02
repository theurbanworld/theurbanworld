/**
 * deck.gl initialization and layer management
 *
 * Initializes deck.gl MapboxOverlay for interleaved mode with MapLibre.
 * Provides layer management and event forwarding.
 */

import { MapboxOverlay } from '@deck.gl/mapbox'
import type { Layer, PickingInfo } from '@deck.gl/core'
import type maplibregl from 'maplibre-gl'
import type { ShallowRef } from 'vue'

export interface UseDeckGLOptions {
  map: ShallowRef<maplibregl.Map | null>
}

export interface HoverInfo {
  object: unknown
  x: number
  y: number
  coordinate: [number, number] | null
  layerId: string | null
}

export function useDeckGL(options: UseDeckGLOptions) {
  const { map } = options

  const overlay = shallowRef<MapboxOverlay | null>(null)
  const isInitialized = ref(false)
  const hoverInfo = ref<HoverInfo | null>(null)

  // Event callbacks
  const onHoverCallbacks: Array<(info: HoverInfo | null) => void> = []
  const onClickCallbacks: Array<(info: HoverInfo | null) => void> = []

  /**
   * Convert deck.gl pick info to our simplified HoverInfo type
   */
  function toHoverInfo(info: PickingInfo): HoverInfo | null {
    if (!info.picked) return null

    const coord = info.coordinate
    return {
      object: info.object,
      x: info.x,
      y: info.y,
      coordinate: coord && typeof coord[0] === 'number' && typeof coord[1] === 'number'
        ? [coord[0], coord[1]]
        : null,
      layerId: info.layer?.id ?? null
    }
  }

  /**
   * Initialize the deck.gl overlay
   */
  function initializeOverlay(mapInstance: maplibregl.Map) {
    if (overlay.value) return

    const deckOverlay = new MapboxOverlay({
      interleaved: true,
      layers: [],
      onHover: (info: PickingInfo) => {
        hoverInfo.value = toHoverInfo(info)
        // Notify all hover callbacks
        onHoverCallbacks.forEach(cb => cb(hoverInfo.value))
      },
      onClick: (info: PickingInfo) => {
        const clickInfo = toHoverInfo(info)
        // Notify all click callbacks
        onClickCallbacks.forEach(cb => cb(clickInfo))
      }
    })

    mapInstance.addControl(deckOverlay as unknown as maplibregl.IControl)
    overlay.value = deckOverlay
    isInitialized.value = true
  }

  /**
   * Set the layers to render
   */
  function setLayers(layers: Layer[]) {
    if (!overlay.value) {
      console.warn('deck.gl overlay not initialized, cannot set layers')
      return
    }
    overlay.value.setProps({ layers })
  }

  /**
   * Register a hover event callback
   */
  function onHover(callback: (info: HoverInfo | null) => void) {
    onHoverCallbacks.push(callback)
    // Return cleanup function
    return () => {
      const index = onHoverCallbacks.indexOf(callback)
      if (index > -1) {
        onHoverCallbacks.splice(index, 1)
      }
    }
  }

  /**
   * Register a click event callback
   */
  function onClick(callback: (info: HoverInfo | null) => void) {
    onClickCallbacks.push(callback)
    // Return cleanup function
    return () => {
      const index = onClickCallbacks.indexOf(callback)
      if (index > -1) {
        onClickCallbacks.splice(index, 1)
      }
    }
  }

  /**
   * Clean up the overlay
   */
  function cleanup() {
    if (overlay.value && map.value) {
      map.value.removeControl(overlay.value as unknown as maplibregl.IControl)
      overlay.value.finalize()
      overlay.value = null
      isInitialized.value = false
    }
    // Clear callbacks
    onHoverCallbacks.length = 0
    onClickCallbacks.length = 0
  }

  // Watch for map initialization
  watch(
    () => map.value,
    (mapInstance) => {
      if (mapInstance && !overlay.value) {
        // Wait for map to be loaded before adding overlay
        if (mapInstance.loaded()) {
          initializeOverlay(mapInstance)
        } else {
          mapInstance.on('load', () => {
            initializeOverlay(mapInstance)
          })
        }
      }
    },
    { immediate: true }
  )

  // Clean up on unmount
  onUnmounted(() => {
    cleanup()
  })

  return {
    overlay: readonly(overlay),
    isInitialized: readonly(isInitialized),
    hoverInfo: readonly(hoverInfo),
    setLayers,
    onHover,
    onClick
  }
}
