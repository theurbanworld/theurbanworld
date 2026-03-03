export interface ProvenanceNode {
  id: string
  label: string
  description: string
  stage: number
  type: 'source' | 'grid' | 'derived' | 'output'
  source?: string
}

export interface ProvenanceEdge {
  from: string
  to: string
  type?: 'default' | 'h3' | 'grid'
}

export const nodes: ProvenanceNode[] = [
  // Column 0 — Data Sources
  {
    id: 'pop-rasters',
    label: 'Population Rasters',
    description: '1 km resolution, Mollweide projection. 12 epochs from 1975 to 2030.',
    stage: 0,
    type: 'source',
    source: 'GHSL-POP R2023A, JRC',
  },
  {
    id: 'city-attributes',
    label: 'City Attributes',
    description: 'Thematic attributes for ~10,000 urban centres worldwide.',
    stage: 0,
    type: 'source',
    source: 'GHSL-UCDB R2024A, JRC',
  },
  {
    id: 'city-boundaries',
    label: 'City Boundaries',
    description: 'Multi-temporal polygons tracking urban extent per epoch.',
    stage: 0,
    type: 'source',
    source: 'GHSL-MTUC R2024A, JRC',
  },

  // Column 1 — Spatial Grids
  {
    id: 'h3-grid',
    label: 'H3 Hexagonal Grid',
    description: 'Resolution 8 (~0.55\u20130.74 km\u00B2 per cell). Raster pixel centroids assigned to H3 cells.',
    stage: 1,
    type: 'grid',
  },
  {
    id: 'regular-grid',
    label: '1 km Regular Grid',
    description: 'Equal-area Mollweide projection. Each pixel = exactly 1 km\u00B2.',
    stage: 1,
    type: 'grid',
  },

  // Column 2 — Derived Datasets
  {
    id: 'city-populations',
    label: 'City Populations',
    description: 'Sum of cell populations within boundaries at each epoch.',
    stage: 2,
    type: 'derived',
  },
  {
    id: 'rankings',
    label: 'Rankings & Growth',
    description: 'Growth rates, density rankings, peer comparisons across epochs.',
    stage: 2,
    type: 'derived',
  },
  {
    id: 'radial-profiles',
    label: 'Radial Density Profiles',
    description: 'Bertaud-style: pop-weighted centroid, 1 km concentric rings to 50 km.',
    stage: 2,
    type: 'derived',
  },

  // Column 3 — What You See
  {
    id: 'density-map',
    label: 'Population Density Map',
    description: 'Choropleth of H3 or grid cells with 6-step density gradient.',
    stage: 3,
    type: 'output',
  },
  {
    id: 'city-info',
    label: 'City Information',
    description: 'Population, area, density time series per city.',
    stage: 3,
    type: 'output',
  },
  {
    id: 'city-rankings',
    label: 'City Rankings',
    description: 'Sortable rankings by population, density, growth.',
    stage: 3,
    type: 'output',
  },
  {
    id: 'profile-charts',
    label: 'Density Profile Charts',
    description: 'Radial charts showing density gradient from centre.',
    stage: 3,
    type: 'output',
  },
]

export const edges: ProvenanceEdge[] = [
  // Sources → Grids
  { from: 'pop-rasters', to: 'h3-grid', type: 'h3' },
  { from: 'pop-rasters', to: 'regular-grid', type: 'grid' },

  // Grids + Boundaries → City Populations
  { from: 'h3-grid', to: 'city-populations', type: 'h3' },
  { from: 'regular-grid', to: 'city-populations', type: 'grid' },
  { from: 'city-boundaries', to: 'city-populations' },

  // City Populations + Attributes → Rankings
  { from: 'city-populations', to: 'rankings' },
  { from: 'city-attributes', to: 'rankings' },

  // H3 → Radial Profiles
  { from: 'h3-grid', to: 'radial-profiles', type: 'h3' },

  // → What You See
  { from: 'h3-grid', to: 'density-map', type: 'h3' },
  { from: 'regular-grid', to: 'density-map', type: 'grid' },
  { from: 'city-populations', to: 'city-info' },
  { from: 'rankings', to: 'city-rankings' },
  { from: 'radial-profiles', to: 'profile-charts' },
]
