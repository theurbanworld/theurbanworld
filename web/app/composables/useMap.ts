/**
 * MapLibre map initialization and management
 *
 * Initializes MapLibre with PMTiles protocol for basemap tiles.
 * - Development: uses Protomaps CDN
 * - Production: uses self-hosted PMTiles on R2
 *
 * Applies a sepia "old atlas" theme using protomaps-themes-base.
 * Includes city boundaries layer with hover interaction.
 * Supports dark mode theme switching.
 */

import maplibregl from 'maplibre-gl'
import { Protocol } from 'pmtiles'
import { layersWithCustomTheme, namedTheme } from 'protomaps-themes-base'
import type { Theme } from 'protomaps-themes-base'
import { markRaw, type ShallowRef } from 'vue'

// PMTiles protocol singleton to avoid re-registration
let pmtilesProtocolRegistered = false

// City boundaries source and layer IDs
const CITY_BOUNDARIES_SOURCE = 'city-boundaries'
const CITY_BOUNDARIES_HOVER_LAYER = 'city-boundaries-hover-pattern'
const CITY_BOUNDARIES_LAYER = 'city-boundaries-line'
const CITY_LABELS_LAYER = 'city-labels'
const CITY_BOUNDARIES_URL = 'https://data.theurban.world/tiles/city_boundaries.pmtiles'

// Basemap layers to hide (we show only land/water + our city data)
const BASEMAP_LAYERS_TO_HIDE = [
  // Country and admin boundaries (we focus on cities vs natural features)
  'boundaries', 'boundaries_country',

  // City name labels (we show our own from PMTiles)
  'places_locality', 'places_subplace', 'places_region', 'places_country',

  // Road rendering
  'roads_highway', 'roads_highway_casing_early', 'roads_highway_casing_late',
  'roads_major', 'roads_major_casing_early', 'roads_major_casing_late',
  'roads_minor', 'roads_minor_casing', 'roads_minor_service', 'roads_minor_service_casing',
  'roads_link', 'roads_link_casing', 'roads_other', 'roads_pier',

  // Railway and airport infrastructure
  'roads_rail', 'roads_runway', 'roads_taxiway',

  // Tunnel variants
  'roads_tunnels_highway', 'roads_tunnels_highway_casing',
  'roads_tunnels_major', 'roads_tunnels_major_casing',
  'roads_tunnels_minor', 'roads_tunnels_minor_casing',
  'roads_tunnels_link', 'roads_tunnels_link_casing',
  'roads_tunnels_other', 'roads_tunnels_other_casing',

  // Bridge variants
  'roads_bridges_highway', 'roads_bridges_highway_casing',
  'roads_bridges_major', 'roads_bridges_major_casing',
  'roads_bridges_minor', 'roads_bridges_minor_casing',
  'roads_bridges_link', 'roads_bridges_link_casing',
  'roads_bridges_other', 'roads_bridges_other_casing',

  // Road name labels
  'roads_labels_major', 'roads_labels_minor',

  // POIs
  'pois',

  // Landuse features (parks, airports, etc.)
  'landuse_park', 'landuse_urban_green', 'landuse_beach', 'landuse_zoo',
  'landuse_aerodrome', 'landuse_runway', 'landuse_industrial',
  'landuse_school', 'landuse_hospital', 'landuse_pedestrian'
]

/**
 * Create sepia theme based on the light theme with customizations
 * for the "old atlas" aesthetic
 */
function createSepiaTheme(): Theme {
  const lightTheme = namedTheme('light')

  return {
    ...lightTheme,
    // Core basemap colors - parchment land, slate water, warm gray borders
    background: '#F5F1E6', // Parchment land
    earth: '#F5F1E6',
    water: '#B8C5CE', // Slate blue-gray water
    glacier: '#D5E0E5',

    // Natural features with sepia tints
    wood_a: '#E8E0D0',
    wood_b: '#E5DDD0',
    scrub_a: '#E5DDD0',
    scrub_b: '#E2DAC8',
    park_a: '#E8E0D0',
    park_b: '#E5DDD0',
    sand: '#F0E8D8',
    beach: '#F0E8D8',

    // Infrastructure with warm tones
    buildings: '#D8CDB8',
    pier: '#D8CDB8',
    pedestrian: '#EDE5D5',
    aerodrome: '#E8E0D0',
    runway: '#D8CDB8',

    // Roads with subtle warm grays
    highway: '#E8E0D0',
    major: '#EDE5D5',
    minor_a: '#F0E8D8',
    minor_b: '#F2EAD8',
    other: '#F5F0E5',
    minor_service: '#F2EAD8',
    link: '#EDE5D5',

    // Road casings
    highway_casing_early: '#D1C8B8',
    highway_casing_late: '#D1C8B8',
    major_casing_early: '#D8D0C0',
    major_casing_late: '#D8D0C0',
    minor_casing: '#DDD5C5',
    minor_service_casing: '#E0D8C8',
    link_casing: '#DDD5C5',

    // Tunnel versions
    tunnel_highway: '#D8CDB8',
    tunnel_major: '#DDD5C5',
    tunnel_minor: '#E0D8C8',
    tunnel_link: '#DDD5C5',
    tunnel_other: '#E0D8C8',
    tunnel_highway_casing: '#C8BFA8',
    tunnel_major_casing: '#D0C8B8',
    tunnel_minor_casing: '#D5CDB8',
    tunnel_link_casing: '#D5CDB8',
    tunnel_other_casing: '#D8D0C0',

    // Bridge versions
    bridges_highway: '#E0D8C8',
    bridges_major: '#E5DDD0',
    bridges_minor: '#E8E0D5',
    bridges_link: '#E5DDD0',
    bridges_other: '#E8E0D5',
    bridges_highway_casing: '#C8BFA8',
    bridges_major_casing: '#D0C8B8',
    bridges_minor_casing: '#D5CDB8',
    bridges_link_casing: '#D5CDB8',
    bridges_other_casing: '#D8D0C0',

    // Boundaries - warm gray
    boundaries: '#9A9385',

    // Labels - dark sepia
    roads_label_minor: '#5A5248',
    roads_label_minor_halo: '#F5F1E6',
    roads_label_major: '#4A4238',
    roads_label_major_halo: '#F5F1E6',
    ocean_label: '#7A8A90',
    subplace_label: '#5A5248',
    subplace_label_halo: '#F5F1E6',
    city_label: '#4A4238',
    city_label_halo: '#F5F1E6',
    state_label: '#6A6258',
    state_label_halo: '#F5F1E6',
    country_label: '#4A4238',
    peak_label: '#5A5248',
    waterway_label: '#7A8A90',
    address_label: '#6A6258',
    address_label_halo: '#F5F1E6',

    // Railway
    railway: '#B8B0A0',

    // Special areas
    hospital: '#E8E0D0',
    industrial: '#E5DDD0',
    school: '#E8E0D0',
    zoo: '#E5DDD0',
    military: '#E0D8C8',

    // Fonts - use Inter for all basemap labels
    regular: 'Inter Regular',
    italic: 'InterVariable-Italic',
    bold: 'Inter Bold'
  }
}

/**
 * Create dark sepia theme for dark mode
 * Inverted colors with deep brown background
 */
function createDarkSepiaTheme(): Theme {
  const darkTheme = namedTheme('dark')

  return {
    ...darkTheme,
    // Core basemap colors - deep brown land, muted slate water
    background: '#2A2420', // Deep brown background
    earth: '#2A2420',
    water: '#3A4550', // Darker slate blue-gray water
    glacier: '#4A5560',

    // Natural features with dark sepia tints
    wood_a: '#353025',
    wood_b: '#302B22',
    scrub_a: '#302B22',
    scrub_b: '#2D2820',
    park_a: '#353025',
    park_b: '#302B22',
    sand: '#3A3428',
    beach: '#3A3428',

    // Infrastructure with dark warm tones
    buildings: '#3D3530',
    pier: '#3D3530',
    pedestrian: '#383028',
    aerodrome: '#353025',
    runway: '#3D3530',

    // Roads with subtle dark warm grays
    highway: '#4A4238',
    major: '#454035',
    minor_a: '#403830',
    minor_b: '#3D3528',
    other: '#383025',
    minor_service: '#3D3528',
    link: '#454035',

    // Road casings
    highway_casing_early: '#5A5248',
    highway_casing_late: '#5A5248',
    major_casing_early: '#555045',
    major_casing_late: '#555045',
    minor_casing: '#504840',
    minor_service_casing: '#4A4538',
    link_casing: '#504840',

    // Tunnel versions
    tunnel_highway: '#3D3530',
    tunnel_major: '#383228',
    tunnel_minor: '#353025',
    tunnel_link: '#383228',
    tunnel_other: '#353025',
    tunnel_highway_casing: '#4A4238',
    tunnel_major_casing: '#454035',
    tunnel_minor_casing: '#403830',
    tunnel_link_casing: '#403830',
    tunnel_other_casing: '#3D3528',

    // Bridge versions
    bridges_highway: '#504840',
    bridges_major: '#4A4538',
    bridges_minor: '#454035',
    bridges_link: '#4A4538',
    bridges_other: '#454035',
    bridges_highway_casing: '#5A5248',
    bridges_major_casing: '#555045',
    bridges_minor_casing: '#504840',
    bridges_link_casing: '#504840',
    bridges_other_casing: '#4A4538',

    // Boundaries - lighter for visibility
    boundaries: '#6A6258',

    // Labels - light sepia/cream on dark background
    roads_label_minor: '#B8B0A5',
    roads_label_minor_halo: '#2A2420',
    roads_label_major: '#D8D0C5',
    roads_label_major_halo: '#2A2420',
    ocean_label: '#8A9AA0',
    subplace_label: '#B8B0A5',
    subplace_label_halo: '#2A2420',
    city_label: '#E8E0D5',
    city_label_halo: '#2A2420',
    state_label: '#C8C0B5',
    state_label_halo: '#2A2420',
    country_label: '#E8E0D5',
    peak_label: '#B8B0A5',
    waterway_label: '#8A9AA0',
    address_label: '#C8C0B5',
    address_label_halo: '#2A2420',

    // Railway
    railway: '#5A5248',

    // Special areas
    hospital: '#353025',
    industrial: '#302B22',
    school: '#353025',
    zoo: '#302B22',
    military: '#383028',

    // Fonts - use Inter for all basemap labels
    regular: 'Inter Regular',
    italic: 'InterVariable-Italic',
    bold: 'Inter Bold'
  }
}

export interface UseMapOptions {
  container: ShallowRef<HTMLElement | null>
}

export function useMap(options: UseMapOptions) {
  const { container } = options

  const map = shallowRef<maplibregl.Map | null>(null)
  const isLoading = ref(true)
  const error = ref<Error | null>(null)
  const cityBoundariesLoaded = ref(false)

  // Get the view state for initial positioning
  const { viewState } = useViewState()

  // Get city hover state management (for boundary highlighting)
  const { setHoveredCityId, clearHover } = useCityHover()

  // Get dark mode state
  const { isDarkMode } = useDarkMode()

  // Get selected year for filtering city boundaries
  const { selectedYear } = useSelectedYear()

  // Track currently hovered feature for feature state
  let hoveredFeatureId: string | number | null = null

  /**
   * Register PMTiles protocol with MapLibre (once)
   */
  function registerPMTilesProtocol() {
    if (pmtilesProtocolRegistered) return

    const protocol = new Protocol()
    maplibregl.addProtocol('pmtiles', protocol.tile)
    pmtilesProtocolRegistered = true
  }

  /**
   * Generate the tile source URL based on environment
   */
  function getTileSourceUrl(): string {
    // Use production PMTiles hosted on data.theurban.world
    return 'pmtiles://https://data.theurban.world/tiles/20260101.pmtiles'
  }

  /**
   * Get city boundaries PMTiles URL
   */
  function getCityBoundariesUrl(): string {
    return `pmtiles://${CITY_BOUNDARIES_URL}`
  }

  /**
   * Create the map style with appropriate theme
   */
  function createMapStyle(darkMode: boolean = false): maplibregl.StyleSpecification {
    const tileSourceUrl = getTileSourceUrl()
    const isPMTiles = tileSourceUrl.startsWith('pmtiles://')

    // Generate layers with appropriate theme, filtering out unwanted layers
    const theme = darkMode ? createDarkSepiaTheme() : createSepiaTheme()
    const allLayers = layersWithCustomTheme('protomaps', theme, 'en')
    const themeLayers = allLayers.filter(
      layer => !BASEMAP_LAYERS_TO_HIDE.includes(layer.id)
    )

    const style: maplibregl.StyleSpecification = {
      version: 8,
      glyphs: 'https://data.theurban.world/fonts/{fontstack}/{range}.pbf',
      // Custom sprites for hover patterns (includes diagonal stripes)
      sprite: 'https://data.theurban.world/sprites/patterns',
      sources: {
        protomaps: isPMTiles
          ? {
              type: 'vector',
              url: tileSourceUrl
            }
          : {
              type: 'vector',
              tiles: [tileSourceUrl],
              maxzoom: 14
            }
      },
      layers: themeLayers
    }

    return style
  }

  /**
   * Update map style for dark mode toggle
   */
  function updateMapTheme(darkMode: boolean) {
    if (!map.value) return

    const mapInstance = map.value
    const currentCenter = mapInstance.getCenter()
    const currentZoom = mapInstance.getZoom()

    // Create new style
    const newStyle = createMapStyle(darkMode)

    // Set the new style
    mapInstance.setStyle(newStyle)

    // Re-add city boundaries after map is idle (all layers rendered)
    mapInstance.once('idle', () => {
      cityBoundariesLoaded.value = false
      addCityBoundariesLayer(mapInstance, darkMode)
      setupCityHoverEvents(mapInstance)
    })

    // Restore view
    mapInstance.jumpTo({
      center: currentCenter,
      zoom: currentZoom
    })
  }

  /**
   * Add city boundaries source and layer to the map
   * Called after map loads to ensure deck.gl overlay is added first
   */
  function addCityBoundariesLayer(mapInstance: maplibregl.Map, darkMode: boolean = false) {
    if (cityBoundariesLoaded.value) return

    try {
      // Check if source already exists
      if (!mapInstance.getSource(CITY_BOUNDARIES_SOURCE)) {
        // Add city boundaries source
        // promoteId tells MapLibre to use city_id as the feature ID for feature-state
        mapInstance.addSource(CITY_BOUNDARIES_SOURCE, {
          type: 'vector',
          url: getCityBoundariesUrl(),
          promoteId: { city_boundaries: 'city_id' }
        })
      }

      // Check if layers already exist and remove them
      if (mapInstance.getLayer(CITY_LABELS_LAYER)) {
        mapInstance.removeLayer(CITY_LABELS_LAYER)
      }
      if (mapInstance.getLayer(CITY_BOUNDARIES_LAYER)) {
        mapInstance.removeLayer(CITY_BOUNDARIES_LAYER)
      }
      if (mapInstance.getLayer(CITY_BOUNDARIES_HOVER_LAYER)) {
        mapInstance.removeLayer(CITY_BOUNDARIES_HOVER_LAYER)
      }

      // Colors based on dark mode
      const labelColor = darkMode ? '#E8E0D5' : '#4A4238'
      const labelHaloColor = darkMode ? '#2A2420' : '#F5F1E6'

      // Boundary color palettes (hash-based hue, population-based brightness)
      const lightPalette = ['#D4B896', '#96B8D4', '#B8D496', '#D496B8', '#96D4B8', '#B896D4'] as const
      const darkPalette = ['#8B5A2B', '#2B5A8B', '#5A8B2B', '#8B2B5A', '#2B8B5A', '#5A2B8B'] as const
      const defaultLight = darkMode ? '#6B6560' : '#C4B8A8'
      const defaultDark = darkMode ? '#8A8275' : '#6B5A4B'

      // Add hover pattern fill layer (Paradox-style diagonal stripes)
      // Base opacity of 0.15 makes it queryable by queryRenderedFeatures
      // and provides subtle territory feel like Paradox maps
      mapInstance.addLayer({
        'id': CITY_BOUNDARIES_HOVER_LAYER,
        'type': 'fill',
        'source': CITY_BOUNDARIES_SOURCE,
        'source-layer': 'city_boundaries',
        'paint': {
          // Select pattern based on city_id hash (same logic as border color)
          'fill-pattern': [
            'match', ['%', ['to-number', ['slice', ['get', 'city_id'], -3]], 6],
            0, 'diagonal-0', 1, 'diagonal-1', 2, 'diagonal-2',
            3, 'diagonal-3', 4, 'diagonal-4', 5, 'diagonal-5', 'diagonal-0'
          ],
          'fill-opacity': [
            'case',
            ['boolean', ['feature-state', 'hover'], false],
            0.7, // Full pattern on hover
            0.15 // Faint pattern always visible (for queryability + subtle territory fill)
          ]
        }
      })

      // Add city boundaries line layer with hash-based colors
      mapInstance.addLayer({
        'id': CITY_BOUNDARIES_LAYER,
        'type': 'line',
        'source': CITY_BOUNDARIES_SOURCE,
        'source-layer': 'city_boundaries',
        'paint': {
          // Color varies by city_id hash (hue) and population (brightness)
          'line-color': [
            'interpolate', ['linear'], ['get', 'population'],
            // Small cities: lighter colors
            0, ['match', ['%', ['to-number', ['slice', ['get', 'city_id'], -3]], 6],
              0, lightPalette[0], 1, lightPalette[1], 2, lightPalette[2],
              3, lightPalette[3], 4, lightPalette[4], 5, lightPalette[5], defaultLight],
            // Large cities: darker colors
            5000000, ['match', ['%', ['to-number', ['slice', ['get', 'city_id'], -3]], 6],
              0, darkPalette[0], 1, darkPalette[1], 2, darkPalette[2],
              3, darkPalette[3], 4, darkPalette[4], 5, darkPalette[5], defaultDark]
          ],
          'line-width': [
            'case',
            ['boolean', ['feature-state', 'hover'], false],
            4,
            3
          ],
          'line-opacity': 1
        },
        'layout': {
          'line-cap': 'round',
          'line-join': 'round'
        }
      })

      // Add city labels layer with population-based sizing
      // At zoom 8+, shows population below city name in compact format (1.2M, 543K)
      mapInstance.addLayer({
        'id': CITY_LABELS_LAYER,
        'type': 'symbol',
        'source': CITY_BOUNDARIES_SOURCE,
        'source-layer': 'city_boundaries',
        'layout': {
          // Sort by population descending so larger cities' labels take precedence
          'symbol-sort-key': ['*', -1, ['get', 'population']],
          // Text field: name only at low zoom, name + stats at zoom 8+
          // Format at zoom 8+: "City Name\n1.5M ↗ ‧ 2.3K/km² ↘"
          'text-field': [
            'step', ['zoom'],
            // At zoom < 8: just show name
            ['get', 'name'],
            // At zoom >= 8: show name + population trend + density trend
            8, ['format',
              ['get', 'name'], {},
              '\n', {},
              // Stats line: "1.5M ↗ ‧ 2.3K/km² ↘"
              ['concat',
                // Population compact format
                ['case',
                  ['>=', ['get', 'population'], 1000000],
                  ['concat',
                    ['number-format', ['/', ['get', 'population'], 1000000], { 'min-fraction-digits': 1, 'max-fraction-digits': 1 }],
                    'M'
                  ],
                  ['>=', ['get', 'population'], 1000],
                  ['concat',
                    ['number-format', ['/', ['get', 'population'], 1000], { 'min-fraction-digits': 1, 'max-fraction-digits': 1 }],
                    'K'
                  ],
                  ['to-string', ['round', ['get', 'population']]]
                ],
                // Population trend arrow
                ['match', ['get', 'pop_trend'], 1, ' ↗', -1, ' ↘', ' →'],
                // Separator
                ' • ',
                // Density compact format (K/km²)
                ['case',
                  ['>=', ['get', 'density_per_km2'], 1000],
                  ['concat',
                    ['number-format', ['/', ['get', 'density_per_km2'], 1000], { 'min-fraction-digits': 1, 'max-fraction-digits': 1 }],
                    'K/km²'
                  ],
                  ['concat',
                    ['to-string', ['round', ['get', 'density_per_km2']]],
                    '/km²'
                  ]
                ],
                // Density trend arrow
                ['match', ['get', 'density_trend'], 1, ' ↗', -1, ' ↘', ' →']
              ],
              { 'font-scale': 0.6, 'text-font': ['literal', ['JetBrains Mono Regular']] }
            ]
          ],
          // Font weight: bold for megacities, semibold for major cities
          'text-font': [
            'step', ['get', 'population'],
            ['literal', ['Crimson Pro Regular']],
            1000000, ['literal', ['Crimson Pro SemiBold']],
            5000000, ['literal', ['Crimson Pro Bold']]
          ],
          // Size based on population, scaling with zoom (1.5x)
          'text-size': [
            'interpolate', ['linear'], ['zoom'],
            // At zoom 4: smaller sizes
            4, ['step', ['get', 'population'],
              12, // < 100k
              100000, 14,
              500000, 15,
              1000000, 18,
              5000000, 21
            ],
            // At zoom 10: larger sizes
            10, ['step', ['get', 'population'],
              15, // < 100k
              100000, 18,
              500000, 21,
              1000000, 24,
              5000000, 30
            ]
          ],
          'text-anchor': 'center',
          'text-allow-overlap': false,
          'text-ignore-placement': false,
          'symbol-placement': 'point',
          // Moderate padding to reduce duplicate labels while still showing dense areas
          'text-padding': ['interpolate', ['linear'], ['zoom'],
            4, 10,
            8, 20,
            12, 40
          ]
        },
        'paint': {
          'text-color': labelColor,
          'text-halo-color': labelHaloColor,
          'text-halo-width': 1.5
        }
      })

      // Apply epoch filter to boundary layers
      const epochFilter: maplibregl.FilterSpecification = ['==', ['get', 'epoch'], selectedYear.value]
      mapInstance.setFilter(CITY_BOUNDARIES_HOVER_LAYER, epochFilter)
      mapInstance.setFilter(CITY_BOUNDARIES_LAYER, epochFilter)

      // Apply epoch + zoom-based population filter to labels
      // At low zoom, only show cities > 1M to reduce clutter
      const labelFilter: maplibregl.FilterSpecification = [
        'all',
        ['==', ['get', 'epoch'], selectedYear.value],
        ['any',
          ['>=', ['zoom'], 6],
          ['>=', ['get', 'population'], 1000000]
        ]
      ]
      mapInstance.setFilter(CITY_LABELS_LAYER, labelFilter)

      cityBoundariesLoaded.value = true
      console.log('City boundaries and labels added for epoch:', selectedYear.value)
    } catch (e) {
      console.error('Failed to add city boundaries layer:', e)
    }
  }

  /**
   * Update city boundaries and labels filter to show only features for the selected year
   */
  function updateCityBoundariesFilter(year: number) {
    if (!map.value || !cityBoundariesLoaded.value) return

    // Epoch filter for boundary layers
    const epochFilter: maplibregl.FilterSpecification = ['==', ['get', 'epoch'], year]
    map.value.setFilter(CITY_BOUNDARIES_HOVER_LAYER, epochFilter)
    map.value.setFilter(CITY_BOUNDARIES_LAYER, epochFilter)

    // Epoch + zoom-based population filter for labels
    const labelFilter: maplibregl.FilterSpecification = [
      'all',
      ['==', ['get', 'epoch'], year],
      ['any',
        ['>=', ['zoom'], 6],
        ['>=', ['get', 'population'], 1000000]
      ]
    ]
    map.value.setFilter(CITY_LABELS_LAYER, labelFilter)
  }

  /**
   * Set up hover event handlers for city boundaries
   * Uses global mousemove with queryRenderedFeatures for reliable hover detection
   */
  function setupCityHoverEvents(mapInstance: maplibregl.Map) {
    // Use global mousemove instead of layer-specific events
    // This is more reliable as it doesn't depend on layer hit-testing
    mapInstance.on('mousemove', (e) => {
      // Query features at cursor position from both hover and line layers
      const features = mapInstance.queryRenderedFeatures(e.point, {
        layers: [CITY_BOUNDARIES_HOVER_LAYER, CITY_BOUNDARIES_LAYER]
      })

      const feature = features[0]
      if (feature) {
        mapInstance.getCanvas().style.cursor = 'pointer'

        // Clear previous hover state if different feature
        if (hoveredFeatureId !== null && hoveredFeatureId !== feature.id) {
          mapInstance.setFeatureState(
            { source: CITY_BOUNDARIES_SOURCE, sourceLayer: 'city_boundaries', id: hoveredFeatureId },
            { hover: false }
          )
        }

        // Set new hover state
        if (feature.id !== undefined) {
          hoveredFeatureId = feature.id
          mapInstance.setFeatureState(
            { source: CITY_BOUNDARIES_SOURCE, sourceLayer: 'city_boundaries', id: feature.id },
            { hover: true }
          )

          // Set hovered city ID for external use
          const cityId = feature.properties?.city_id as string | undefined
          if (cityId) {
            setHoveredCityId(cityId)
          }
        }
      } else {
        // Clear hover when not over any city
        mapInstance.getCanvas().style.cursor = ''
        if (hoveredFeatureId !== null) {
          mapInstance.setFeatureState(
            { source: CITY_BOUNDARIES_SOURCE, sourceLayer: 'city_boundaries', id: hoveredFeatureId },
            { hover: false }
          )
          hoveredFeatureId = null
          clearHover()
        }
      }
    })
  }

  /**
   * Initialize the map
   */
  function initializeMap() {
    if (!container.value) {
      error.value = new Error('Map container element not found')
      isLoading.value = false
      return
    }

    try {
      registerPMTilesProtocol()

      const mapInstance = new maplibregl.Map({
        container: container.value,
        style: createMapStyle(isDarkMode.value),
        center: [viewState.value.longitude, viewState.value.latitude],
        zoom: viewState.value.zoom,
        pitch: 0, // Locked to 0 for 2D
        bearing: 0, // Locked to 0 (north up)
        minPitch: 0,
        maxPitch: 0, // Prevent pitch changes
        dragRotate: false, // Disable rotation
        touchPitch: false, // Disable touch pitch
        keyboard: true,
        attributionControl: false // We'll add custom attribution
      })

      // Handle map load
      mapInstance.on('load', () => {
        isLoading.value = false

        // Add city boundaries layer after a short delay
        // to ensure deck.gl overlay is added first
        setTimeout(() => {
          addCityBoundariesLayer(mapInstance, isDarkMode.value)
          setupCityHoverEvents(mapInstance)
        }, 100)
      })

      // Handle map errors
      mapInstance.on('error', (e) => {
        console.error('MapLibre error:', e)
        error.value = new Error(e.error?.message || 'Map loading failed')
      })

      map.value = markRaw(mapInstance)
    } catch (e) {
      console.error('Failed to initialize map:', e)
      error.value = e instanceof Error ? e : new Error('Failed to initialize map')
      isLoading.value = false
    }
  }

  /**
   * Clean up map on unmount
   */
  function cleanup() {
    if (map.value) {
      map.value.remove()
      map.value = null
    }
    cityBoundariesLoaded.value = false
    hoveredFeatureId = null
  }

  // Initialize map when container is available
  onMounted(() => {
    if (container.value) {
      initializeMap()
    } else {
      // Wait for container to be available
      const stopWatch = watch(container, (newContainer) => {
        if (newContainer) {
          initializeMap()
          stopWatch()
        }
      })
    }
  })

  // Watch for dark mode changes and update map theme
  watch(isDarkMode, (darkMode) => {
    if (map.value && !isLoading.value) {
      updateMapTheme(darkMode)
    }
  })

  // Watch for selected year changes and update city boundaries filter
  watch(selectedYear, (year) => {
    updateCityBoundariesFilter(year)
  })

  // Clean up on unmount
  onUnmounted(() => {
    cleanup()
  })

  return {
    map: readonly(map),
    isLoading: readonly(isLoading),
    error: readonly(error),
    cityBoundariesLoaded: readonly(cityBoundariesLoaded),
    updateMapTheme
  }
}
