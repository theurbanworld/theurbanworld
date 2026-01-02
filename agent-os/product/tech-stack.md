# Tech Stack

## Overview

The Urban World is built as two distinct systems: a Python data pipeline that processes GHSL data into web-ready formats, and a Nuxt frontend that serves the interactive visualization.

---

## Frontend Application

### Framework & Runtime

| Component | Technology | Notes |
|-----------|------------|-------|
| **Framework** | Nuxt 4 | Vue-based meta-framework with SSR/SSG support |
| **Language** | TypeScript | Type-safe development |
| **Runtime** | Node.js | Via Cloudflare Workers edge runtime |
| **Package Manager** | pnpm | Fast, disk-efficient package management |

### UI & Visualization

| Component | Technology | Notes |
|-----------|------------|-------|
| **CSS Framework** | Tailwind CSS | Utility-first styling |
| **UI Components** | Nuxt UI v4 | Component library built on Tailwind |
| **Icons** | Iconify (Lucide, Simple Icons) | SVG icon sets |
| **Charting** | Chart.js + vue-chartjs | Time series and radial profile charts |
| **Mapping** | deck.gl + MapLibre GL | H3 hexagon layers on vector basemap |
| **Basemap Tiles** | Protomaps PMTiles | Self-hosted vector tiles from R2 |

### Data Loading

| Component | Technology | Notes |
|-----------|------------|-------|
| **Search** | Fuse.js | Client-side fuzzy search over city index |
| **Parquet Loading** | @loaders.gl/parquet | Load GeoParquet directly in browser |
| **Tile Protocol** | pmtiles | Efficient range-request access to PMTiles |

### Hosting & Infrastructure

| Component | Technology | Notes |
|-----------|------------|-------|
| **Hosting** | Cloudflare Pages | Edge deployment, free tier |
| **Static Assets** | Cloudflare R2 | GeoParquet, PMTiles, city JSON (~$3-10/month) |
| **Domain** | theurban.world | Managed via Cloudflare |
| **CDN** | Cloudflare | Automatic via Workers/R2 |

---

## Data Pipeline

### Language & Runtime

| Component | Technology | Notes |
|-----------|------------|-------|
| **Language** | Python 3.11+ | Data processing and analysis |
| **Package Manager** | uv | Fast Python package manager |
| **Task Runner** | Make | Pipeline orchestration |
| **Cloud Compute** | Modal | On-demand cloud functions for heavy processing |

### Data Processing

| Component | Technology | Notes |
|-----------|------------|-------|
| **Query Engine** | DuckDB | SQL analytics on Parquet files |
| **Spatial** | H3 (h3-py) | Hexagonal hierarchical spatial index |
| **Raster Processing** | rasterio, numpy | GHSL GeoTIFF processing |
| **Data Validation** | Pandera | Schema validation for pipeline outputs |
| **Geometry** | Shapely, GeoPandas | Vector geometry operations |

### Data Formats

| Format | Usage | Notes |
|--------|-------|-------|
| **Parquet** | Pipeline intermediate and final outputs | Columnar, compressed, efficient |
| **GeoParquet** | H3 population grids for web | Spatial data with geometry column |
| **PMTiles** | Vector tile basemap, city boundaries | Single-file tile archive |
| **JSON** | City metadata, search index | Lightweight, cacheable |

### Data Sources

| Source | Dataset | Notes |
|--------|---------|-------|
| **GHSL-POP** | Population grids R2023A | 100m and 1km resolution, 1975-2030 |
| **GHSL-UCDB** | Urban Centre Database R2024A | ~13,000 cities with attributes |
| **Protomaps** | Planet basemap | OpenStreetMap-derived PMTiles |

---

## Development Tools

### Code Quality

| Tool | Purpose |
|------|---------|
| **ESLint** | JavaScript/TypeScript linting |
| **Ruff** | Python linting and formatting |
| **TypeScript** | Type checking (via vue-tsc) |

### Version Control

| Tool | Purpose |
|------|---------|
| **Git** | Version control |
| **GitHub** | Repository hosting |
| **GitHub Actions** | CI/CD (planned) |

---

## Architecture Decisions

### Why H3 Hexagons?

- Hierarchical zoom levels (res 8 for overview, res 9 for detail)
- Efficient spatial queries and aggregation
- Better visual representation than irregular polygons
- Native deck.gl support via H3HexagonLayer

### Why Pre-computation?

- GHSL updates infrequently (every few years)
- Complex calculations (radial profiles, rankings) done once
- API becomes simple static file serving
- Enables pure edge/CDN deployment

### Why No Database?

- ~13,000 cities is a small dataset
- All queries are key-based lookups
- JSON files are fast enough and simpler to deploy
- DuckDB handles any complex queries in pipeline

### Why Cloudflare?

- Free tier covers expected traffic
- R2 is cost-effective for large static files (~70GB basemap)
- Edge deployment provides global low latency
- Integrated CDN and domain management

### Why Fuse.js over Server Search?

- 13,000 cities is manageable client-side (~200KB index)
- Zero infrastructure complexity
- Works offline
- Can upgrade to Meilisearch if search becomes primary feature

---

## File Structure

```
urbanworld/
├── pipeline/                 # Data processing
│   ├── src/                  # Pipeline scripts (s01-s99)
│   ├── data/
│   │   ├── raw/              # Downloaded GHSL files
│   │   ├── interim/          # Intermediate outputs
│   │   └── processed/        # Final web-ready files
│   ├── pyproject.toml        # Python dependencies
│   └── Makefile              # Pipeline orchestration
│
├── web/                      # Frontend application
│   ├── app/                  # Nuxt app directory
│   ├── public/               # Static assets
│   ├── nuxt.config.ts        # Nuxt configuration
│   └── package.json          # Node dependencies
│
└── agent-os/                 # Project documentation
    ├── product/              # Mission, roadmap, tech stack
    └── standards/            # Coding standards
```

---

## Environment Variables

### Pipeline (.env in /pipeline)

```bash
# R2 Storage
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=

# Modal (optional, for cloud processing)
MODAL_TOKEN_ID=
MODAL_TOKEN_SECRET=
```

### Web (.env in /web)

```bash
# R2 Public URL
NUXT_PUBLIC_R2_URL=https://data.theurban.world

# Feature Flags (optional)
NUXT_PUBLIC_ENABLE_ANALYTICS=false
```
