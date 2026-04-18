# Urban Data Pipeline

A data processing pipeline that transforms GHSL (Global Human Settlement Layer) raster data into web-ready formats for urban visualization at [theurban.world](https://theurban.world).

## Overview

Processes ~13,000 cities globally from the European Commission's GHSL dataset, generating:
- **H3 hexagonal grids** (resolution 8) for map visualization
- **1 km raster grids** as a parallel canonical dataset
- **City boundary polygons** as PMTiles
- **Radial density profiles** (Bertaud-style analysis)
- **Population time series** (1975–2030)
- **Web-ready JSON** for frontend consumption

Pipeline flow diagram and full provenance: [`DATA_LINEAGE.md`](DATA_LINEAGE.md).

## Quick Start

```bash
# Install dependencies with uv
uv sync

# Download pre-computed H3 data from R2 (fastest path to a working dataset)
uv run python -m src.download.download_h3_r8

# Validate outputs
uv run python -m src.validate.validate_cities --source h3-r8 -v
```

All commands run from the `pipeline/` directory.

## Two Canonical Datasets

The pipeline produces **two canonical population datasets**:

1. **`ghsl-grid-1km`** — pure GHSL raster pixels within city boundaries (1 km² each)
2. **`ghsl-h3-r8`** — H3 hexagonal grid at resolution 8 (~0.55–0.74 km² per cell) derived from GHSL

Scripts that accept `--source` (`h3-r8` or `grid-1km`): `compute_populations`, `compute_rankings`, `generate_city_populations`, `validate_cities`.

Output files include the source in their name, e.g. `city_populations_h3_r8.parquet`, `city_populations_grid_1km.parquet`.

## Pipeline Scripts

Scripts are organized by domain under `src/`:

### download/ — Data retrieval
| Script | Description |
|--------|-------------|
| `download_ghsl.py` | Download GHSL-POP tiles, UCDB, and MTUC from JRC |
| `download_h3_r8.py` | Download pre-computed H3 res-8 population data from R2 |

### cities/ — City extraction and computation
| Script | Description |
|--------|-------------|
| `extract_attributes.py` | Extract city attributes from UCDB GeoPackage |
| `extract_geometries.py` | Extract multi-temporal city boundaries from MTUC |
| `generate_cities.py` | Merge attributes + geometries into `cities.parquet` |
| `compute_populations.py` | Sum populations within city boundaries (`--source`) |
| `compute_rankings.py` | Compute rankings, growth metrics, density peers (`--source`) |
| `density_outliers.py` | Identify / filter cities with unreliable density estimates |
| `match_wikidata.py` | Resolve Wikidata QIDs for city enrichment |

### grid/ — 1 km raster grid extraction
| Script | Description |
|--------|-------------|
| `extract_grid_1km.py` | Extract 1 km pixels from Mollweide rasters per city |

### h3/ — H3 hexagonal grid processing
| Script | Description |
|--------|-------------|
| `modal_raster_to_h3_r8.py` | Convert 1 km rasters to H3 res-8 on Modal cloud |
| `modal_global_h3_r8.py` | Global H3 res-8 rasterization on Modal |
| `modal_extract_city_h3.py` | Extract per-city H3 slices on Modal |
| `merge_h3_r8_timeseries.py` | Merge per-epoch H3 files into a single timeseries |
| `load_h3_r8_to_psql.py` | Load H3 data into PostGIS for QGIS visualization |

### radial/ — Radial density analysis
| Script | Description |
|--------|-------------|
| `generate_radial_profiles.py` | Compute Bertaud-style radial density profiles (H3) |

### tiles/ — Map tile generation
| Script | Description |
|--------|-------------|
| `modal_download_basemap.py` | Download Protomaps planet PMTiles on Modal |
| `generate_boundaries.py` | Generate city boundary PMTiles with tippecanoe |
| `generate_grid_1km_outlines.py` | Generate 1 km grid outline PMTiles |
| `generate_h3_r8_outlines.py` | Generate H3 res-8 outline PMTiles |
| `generate_font_glyphs.py` | Generate MapLibre font glyph PBF files |
| `generate_hover_sprites.py` | Generate hover pattern sprite sheets |

### web_export/ — Frontend JSON generation
| Script | Description |
|--------|-------------|
| `generate_city_index.py` | City metadata JSON for search / navigation |
| `generate_city_populations.py` | Per-epoch population JSON for sidebar (`--source`) |
| `generate_radial_profiles.py` | Radial profile JSON for the frontend |
| `generate_city_cells.py` | Per-city H3 cell JSON |

### validate/ — Data quality checks
| Script | Description |
|--------|-------------|
| `validate_cities.py` | Pandera schema validation across all outputs (`--source`) |

### explore/ — Data exploration
| Script | Description |
|--------|-------------|
| `app_explore.py` | Streamlit app for browsing city data |

## Density Outlier Filtering

GHSL population estimates can produce unrealistically high densities for cities with very small UCDB boundaries. When only a handful of ~1 km cells fall within a city boundary, the density estimate is unreliable and can exceed any real-world city.

The pipeline uses a **median-based two-tier filter** to remove these outliers from rankings and web exports. Median density and cell count are computed across all 12 epochs (1975–2030), which smooths out early-epoch noise and avoids excluding cities that were small historically but grew into legitimate urban areas:
- **Tier 1 — Tiny cities** (median `< 5 cells`): always excluded, persistently too few data points
- **Tier 2 — Small + dense** (median `< 50 cells AND > 20,000/km²`): persistently small cities with implausibly high density are data artifacts

Raw population data (`city_populations_{source}.parquet`) is preserved unfiltered. See `src/cities/density_outliers.py` for details and thresholds.

```bash
# Analyze which cities would be filtered
uv run python -m src.cities.density_outliers --source h3-r8

# Write a JSON report of all excluded cities (auditable record)
uv run python -m src.cities.density_outliers --source h3-r8 --report
# -> data/processed/cities/density_outliers_report.json
```

## Data Sources

- **GHSL-POP R2023A** — population grids at 1 km resolution, 12 epochs (1975–2030)
- **GHSL-UCDB R2024A** — Urban Centre Database with city attributes
- **GHSL-MTUC R2024A** — multi-temporal urban centre boundaries
- Source: [European Commission Joint Research Centre](https://human-settlement.emergency.copernicus.eu/)

## Configuration

Key settings in `src/utils/config.py`:
- `H3_RESOLUTION_MAP = 9` (~0.1 km² cells, used for high-resolution map layers)
- `H3_RESOLUTION_1KM = 8` (~0.55–0.74 km² cells, the canonical `ghsl-h3-r8` dataset)
- `H3_RESOLUTION_RADIAL = 10` (~0.015 km² cells, radial profiles)
- `RADIAL_MAX_DISTANCE_KM = 50` (50 rings at 1 km intervals)
- `BOUNDARY_POPULATION_THRESHOLD = 100` (min pop per cell)

Override via environment variables with `URBAN_` prefix:
```bash
URBAN_H3_RESOLUTION_MAP=8 uv run python -m src.radial.generate_radial_profiles
```

## R2 Upload Configuration

Data is served from Cloudflare R2. To configure uploads:

```bash
# Copy the example env file
cp .env.example .env

# Edit with your R2 credentials (from Cloudflare dashboard)
# R2_ACCOUNT_ID=...
# R2_ACCESS_KEY_ID=...
# R2_SECRET_ACCESS_KEY=...
# R2_BUCKET=...
```

## Project Structure

```
pipeline/
├── pyproject.toml          # Dependencies and entry points
├── AGENTS.md               # Development instructions (for AI coding agents)
├── .env.example            # R2 credentials template
├── src/
│   ├── download/           # Data retrieval from JRC and R2
│   ├── cities/             # City extraction, population, rankings
│   ├── grid/               # 1 km grid extraction
│   ├── h3/                 # H3 hexagonal grid processing
│   ├── radial/             # Radial density profiles
│   ├── tiles/              # Map tiles, fonts, sprites
│   ├── web_export/         # Frontend JSON generation
│   ├── validate/           # Data quality validation
│   ├── explore/            # Streamlit data explorer
│   └── utils/              # Shared config, geometry, H3, R2 upload
└── data/                   # (gitignored)
    ├── raw/                # Downloaded GHSL files
    ├── interim/            # Intermediate outputs
    └── processed/          # Final web-ready files
        ├── tiles/          # PMTiles, JSON, sprites
        └── cities/         # Parquet tables
```

## Hardware Requirements

- **Memory**: 16 GB RAM minimum (32 GB recommended)
- **Storage**: ~150 GB for full dataset
- Optimized for Apple Silicon (M1/M2/M3) with thread-based parallelization.

## License

Pipeline code: [MIT](../LICENSE). Derived data: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Upstream GHSL data is © European Commission JRC under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
