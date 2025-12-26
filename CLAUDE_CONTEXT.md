 Urban Data Platform - MVP Project Summary

## Project Vision
An "Our World in Data" for cities and the urban world, starting with the Global Human Settlement Layer (GHSL) as the foundational dataset. Focus on population data, urban expansion, and density analysis.

## Core Philosophy
- Solo project for joy and learning
- Ship something motivating to test interest
- Start simple, strong technical foundation
- Leverage NYC Planning Labs networks for feedback

## MVP Scope (v1)

### Features
1. **Global map** with population density (2025 epoch)
2. **Interactive city selection** showing:
   - Basic statistics (population, area, density)
   - **Radial density profiles** (Bertaud-style analysis)
   - Time series chart (1975-2025 population)
3. **City search** functionality
4. **That's it.** (Resist scope creep)

### Explicitly Deferred
- Multiple time periods in UI
- Administrative boundaries
- Custom area selection
- Social sharing
- User accounts
- Multi-city comparison beyond radial profiles
- Climate/economic overlays

## Technical Stack

### Frontend
- **Nuxt 4** (Vue framework)
- **deck.gl** for map visualization (H3HexagonLayer)
- **Fuse.js** for client-side search (~13k cities)
- **Chart.js** with vue-chartjs for data visualization

### Backend/Hosting
- **Nuxt server routes** (no separate API needed)
- **Cloudflare Pages** for hosting (free tier)
- **Cloudflare R2** for GeoParquet/PMTiles storage ($3-5/month)
- Total cost: **~$3-10/month**

### Data Pipeline
- **Python scripts** (no orchestration framework for MVP)
- **DuckDB** for spatial queries and aggregations
- **Modal** for parallel processing (on-demand cloud functions)
- **Make** for pipeline orchestration

## Data Architecture

### H3 Resolution Strategy
- **Res 9** (~0.1km²): Map visualization, city-wide patterns

### Data Outputs
1. **City index** (`cities.json`): Lightweight for search, ~100-200KB
2. **City details** (`cities/{id}.json`): Metadata + time series + radial profile
3. **H3 hexagons** (GeoParquet on R2): Population by hexagon
4. **PMTiles** (optional): Urban center boundaries

**1km resolution (1975-2025 data):**
- Time series population trends
- Full temporal coverage
- Sufficient resolution for population trends
- Radial density profiles - captures sharp density transitions
- Current map visualization
- H3 res 8 for map tiles and computation


## Application Architecture

```
Nuxt App (Cloudflare Pages)
├── Client-side
│   ├── deck.gl → R2 (GeoParquet/PMTiles direct access)
│   └── Fuse.js search (bundled cities.json)
└── Server Routes
    ├── /api/cities → static JSON
    ├── /api/city/[id] → static JSON
    └── /api/city/[id]/h3/[res] → redirect to R2
```

## Development Timeline (6 weeks)

### Weeks 1-2: Data Pipeline
- Download GHSL datasets
- Extract urban centers
- Raster → H3 conversion
- Compute radial profiles
- Export to web formats

### Week 3: Backend
- Nuxt server routes
- Data serving strategy
- R2 upload workflow

### Weeks 4-5: Frontend
- deck.gl map integration
- City detail panel
- Search implementation
- Charts (time series + radial profiles)

### Week 6: Polish & Deploy
- Methodology documentation
- Data provenance
- Download capabilities
- Deploy to Cloudflare Pages

## Key Technical Decisions

### Why H3?
- Hierarchical zoom levels
- Efficient spatial queries
- Better than raster for web performance

### Why Pre-computation?
- GHSL updates infrequently (every few years)
- Complex calculations (radial profiles) done once
- API becomes simple file server
- Enables static/edge deployment

### Why No Database for City Data?
- ~13k cities = small dataset
- All queries are lookups, no complex joins
- JSON files are fast enough
- Simpler deployment

### Why Fuse.js over Meilisearch?
- MVP scope: 13k cities is manageable client-side
- Zero infrastructure
- Works offline
- Can upgrade later if search becomes primary feature

## Bertaud-Style Analysis

Radial density profiles: measure average population density in concentric rings from city center (0-50km, 1km intervals).

**Insights revealed:**
- Urban form (monocentric vs polycentric)
- Sprawl patterns
- Regulatory boundaries (density cliffs)
- Cross-city comparisons

**Implementation:**
- Pre-compute during pipeline
- Store as JSON array: `[{radius: 0, density: 5000}, ...]`
- Visualize with line charts
- Log scale option for better distribution

## Important GHSL Details

- **Urban Centers** (>50k pop, >1500/km²): ~13k globally
- **Temporal coverage**: 
  - 1km resolution: 1975-2030 (5-year intervals) - used for time series
  - 100m resolution: 2000, 2015, 2020, 2025, 2030 - used for radial profiles
- **Resolution choice**: Hybrid approach balances spatial detail with temporal coverage
- **Methodology changes**: Document across epochs
- **City definition**: Algorithmic, not administrative boundaries
- **Center point**: Use population-weighted centroid, not geometric
- **Data volume**: 100m resolution = ~50-100GB per epoch (vs ~2GB for 1km)

## Quality Bars

### Must Have
- Fast load times (<2s to interactive)
- Mobile-responsive
- Clear methodology documentation
- Professional design
- Data provenance and timestamps

### Motivation Hacks
- Deploy weekly increments
- Share progress on social media
- Keep "discovered insights" log
- Ship something, even if incomplete

## Launch Strategy

### Soft Launch Targets
- 5-10 friendly urbanists (Planning Labs network)
- One detailed city profile blog post
- Civic tech spaces first

### Public Launch
- r/UrbanPlanning
- r/dataisbeautiful
- Hacker News (technical framing)
- Academic Twitter (tag GHSL researchers)
- CityLab/Bloomberg Cities

### Key Metrics
- Beyond-homepage engagement
- Which cities do users search?
- Do radial profiles resonate?

## Migration Path to Scale

**When to add complexity:**
1. **10k+ users**: Full PMTiles, no backend tile generation
2. **Complex queries**: Add PostGIS on Render
3. **Frequent updates**: Add orchestration (Dagster/Modal)
4. **Advanced search**: Upgrade to Meilisearch

Until then: keep it simple.

## Technical Debt to Accept (For Now)

- No user accounts
- No real-time collaboration
- No custom analysis
- Client-side search limitations
- Single epoch in UI
- No mobile app

These can all be added later based on actual user demand.

## Documentation Standards

Inline decision documentation in scripts:
```python
"""
Decision: Use res 7 for global, res 8 for detail
Rationale: Balances detail vs performance
Data size: res 7 = 500MB, res 8 = 4GB
Tested on: NYC, Lagos, Tokyo
Date: 2024-12-08
"""
```

## Next Deep Dives

Potential topics to explore in detail:
1. deck.gl + Vue/Nuxt integration patterns
2. H3 raster conversion optimization
3. Radial profile computation algorithms
4. GeoParquet optimization for web
5. PMTiles vs GeoParquet trade-offs
6. Nuxt deployment to Cloudflare Pages
7. R2 upload and access patterns
8. DuckDB spatial query patterns

## Resources

### Data Sources
- GHSL Population: GHS-POP R2023A
- GHSL Urban Centers: GHS-UCDB R2019A

### Inspiration
- Alain Bertaud's urban analysis methodology
- Our World in Data's approach to data storytelling
- NYC Planning Labs' civic tech philosophy

---

**Project Mantra**: Ship something simple that works, iterate based on real feedback, resist perfectionism.