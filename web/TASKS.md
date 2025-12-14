# Urban Data Platform - Development Tasks

## Project Setup
- [x] Install dependencies (deck.gl, maplibre-gl, pmtiles, loaders.gl)
- [x] Install search/chart dependencies (fuse.js, chart.js, vue-chartjs)
- [ ] Configure Tailwind (extend theme with density color scale)
- [ ] Configure TypeScript strict mode
- [ ] Set up environment variables (.env.example)
- [ ] Configure Cloudflare Pages deployment
- [ ] Migrate from protomaps-themes-base to @protomaps/basemaps (deprecated)

## Types & Utilities
- [ ] Define City types (CityIndex, CityDetail)
- [ ] Define H3 types (H3Hexagon, H3DataSet)
- [ ] Define Map types (ViewState, Viewport)
- [ ] Implement constants (R2 URLs, color scales, defaults)
- [ ] Implement formatters (population, density, area)

## Map Foundation
- [ ] Implement useMap composable (MapLibre + PMTiles)
- [ ] Implement useDeckGL composable
- [ ] Implement useViewState composable
- [ ] Create GlobalMap component
- [ ] Create MapControls component
- [ ] Verify basemap renders correctly
- [ ] Test deck.gl overlay integration

## Data Loading
- [ ] Implement useH3Data composable (GeoParquet loading)
- [ ] Implement useCitySearch composable (Fuse.js)
- [ ] Implement useCityData composable (city detail JSON)
- [ ] Create H3PopulationLayer component
- [ ] Test H3 hexagon rendering
- [ ] Verify color scale looks good

## City Selection & Search
- [ ] Create CitySearch component (CommandPalette)
- [ ] Wire up keyboard shortcut (Cmd+K)
- [ ] Implement fly-to animation on city select
- [ ] Test search performance with 13k cities

## City Detail Panel
- [ ] Create CityPanel component (Slideover)
- [ ] Create CityStats component
- [ ] Create CityTimeSeries chart
- [ ] Create RadialDensityChart
- [ ] Wire up panel open/close with city selection
- [ ] Test charts render correctly

## UI Polish
- [ ] Create LoadingOverlay component
- [ ] Create DataAttribution component
- [ ] Implement default layout with header
- [ ] Create About page content
- [ ] Mobile responsive testing
- [ ] Dark mode support (optional)

## Integration Testing
- [ ] Test full flow: search → select → view details
- [ ] Test with real data from R2
- [ ] Performance testing (load time < 2s)
- [ ] Cross-browser testing

## Deployment
- [ ] Configure Cloudflare Pages
- [ ] Set up production environment variables
- [ ] Deploy to preview URL
- [ ] Test with production R2 data
- [ ] Final deploy to production URL

## Documentation
- [ ] Write README with setup instructions
- [ ] Document environment variables
- [ ] Write About page methodology content

## Future / Deferred
- [ ] Multi-city comparison
- [ ] Multiple time periods in UI
- [ ] Custom area selection
- [ ] Social sharing
- [ ] Data download functionality
