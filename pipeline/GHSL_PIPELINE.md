# GHSL Data Pipeline Documentation

This document describes how Global Human Settlement Layer (GHSL) data flows through the processing pipeline, from raw downloads to H3-indexed outputs.

## Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         GHSL DATA SOURCES                               │
│   (European Commission JRC - jeodpp.jrc.ec.europa.eu)                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 01: Download (s01_download_ghsl.py)                              │
│  ├── UCDB GeoPackage (urban centers database)                           │
│  ├── GHSL-POP 100m tiles (2020 only, Mollweide projection)              │
│  └── GHSL-POP 1km global files (1975-2020, all epochs)                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
┌──────────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ STAGE 02: Extract    │  │ STAGE 03: 100m  │  │ STAGE 04: 1km   │
│ UCDB                 │  │ Raster → H3     │  │ Raster → H3     │
│ (s02_extract_ucdb.py)│  │ (s03_*.py)      │  │ (s04_*_modal.py)│
└──────────────────────┘  └─────────────────┘  └─────────────────┘
          │                       │                     │
          ▼                       ▼                     ▼
┌──────────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ data/interim/ucdb/   │  │ data/processed/ │  │ data/interim/   │
│ data/interim/        │  │ h3_tiles/       │  │ h3_pop_1km/     │
│ cities.pq            │  │                 │  │                 │
└──────────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## Stage 01: Download GHSL Data

**Script:** `src/s01_download_ghsl.py`

Downloads raw GHSL data from the European Commission JRC servers with retry logic and progress tracking.

### Data Sources

| Dataset | Resolution | Epochs | Projection | Format |
|---------|------------|--------|------------|--------|
| GHSL-UCDB | N/A | 2024 release | Mollweide (ESRI:54009) | GeoPackage + XLSX |
| GHSL-POP | 100m | 2020 only | Mollweide (ESRI:54009) | GeoTIFF (tiled) |
| GHSL-POP | 1km | 1975-2020 (10 epochs) | Mollweide (ESRI:54009) | GeoTIFF (global) |

### Epochs (1km data)
`1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020`

### Test City Tiles

| City | Tile Coordinates |
|------|------------------|
| New York | R5_C11, R5_C12 |
| Paris | R5_C18 |
| Singapore | R8_C27 |
| Lagos | R7_C18 |
| Rio de Janeiro | R8_C13 |
| Geneva | R5_C18 (same as Paris) |

### Outputs

| Output Path | Description |
|-------------|-------------|
| `data/raw/ucdb/*.gpkg` | UCDB R2024A GeoPackage (16 thematic layers) |
| `data/raw/ucdb/*.xlsx` | UCDB schema/index spreadsheet |
| `data/raw/ghsl_pop_100m/*.tif` | 100m population tiles (2020) |
| `data/raw/ghsl_pop_1km/*.tif` | 1km global population files (all epochs) |
| `data/raw/download_progress.json` | Download progress tracking |
| `data/raw/.download_complete` | Sentinel file indicating completion |

---

## Stage 02: Extract UCDB

**Script:** `src/s02_extract_ucdb.py`

Parses the UCDB GeoPackage to extract thematic data, geometries, and urban center metadata for downstream processing.

### UCDB Thematic Layers

| Layer Key | GeoPackage Layer Name | Description |
|-----------|----------------------|-------------|
| GENERAL_CHARACTERISTICS | GHS_UCDB_THEME_GENERAL_CHARACTERISTICS_GLOBE_R2024A | Basic city info (name, country, area, population) |
| GHSL | GHS_UCDB_THEME_GHSL_GLOBE_R2024A | GHSL-derived metrics |
| CLIMATE | GHS_UCDB_THEME_CLIMATE_GLOBE_R2024A | Climate indicators |
| EMISSIONS | GHS_UCDB_THEME_EMISSIONS_GLOBE_R2024A | Emissions data |
| EXPOSURE | GHS_UCDB_THEME_EXPOSURE_GLOBE_R2024A | Exposure metrics |
| GEOGRAPHY | GHS_UCDB_THEME_GEOGRAPHY_GLOBE_R2024A | Geographic features |
| GREENNESS | GHS_UCDB_THEME_GREENNESS_GLOBE_R2024A | Vegetation indices |
| HAZARD_RISK | GHS_UCDB_THEME_HAZARD_RISK_GLOBE_R2024A | Natural hazard risks |
| HEALTH | GHS_UCDB_THEME_HEALTH_GLOBE_R2024A | Health indicators |
| INFRASTRUCTURES | GHS_UCDB_THEME_INFRASTRUCTURES_GLOBE_R2024A | Infrastructure data |
| LULC | GHS_UCDB_THEME_LULC_GLOBE_R2024A | Land use/land cover |
| NATURAL_SYSTEMS | GHS_UCDB_THEME_NATURAL_SYSTEMS_GLOBE_R2024A | Natural system metrics |
| SDG | GHS_UCDB_THEME_SDG_GLOBE_R2024A | UN SDG indicators |
| SOCIOECONOMIC | GHS_UCDB_THEME_SOCIOECONOMIC_GLOBE_R2024A | Socioeconomic data |
| WATER | GHS_UCDB_THEME_WATER_GLOBE_R2024A | Water-related metrics |

### Processing Steps

1. **Schema Extraction** - Parse XLSX Index sheet for column definitions
2. **Theme Extraction** - Extract each thematic layer to Parquet (without geometry)
3. **Theme Merge** - Join all themes on `ID_UC_G0` into wide table
4. **Geometry Extraction** - Export polygons and centroids as GeoParquet (WGS84)
5. **Urban Centers Metadata** - Create lookup table with bbox and required tiles

### Outputs

| Output Path | Description |
|-------------|-------------|
| `data/raw/ucdb/ucdb_schema.json` | Human-readable column definitions |
| `data/interim/ucdb/themes/*.parquet` | 15 thematic tables (one per layer) |
| `data/interim/ucdb/ucdb_all.parquet` | Merged wide table (all themes joined) |
| `data/interim/ucdb/geometries.parquet` | Polygon boundaries (GeoParquet, WGS84) |
| `data/interim/ucdb/centroids.parquet` | Point centroids (GeoParquet, WGS84) |
| `data/interim/cities.parquet` | City metadata with bbox + required tiles |

### Key Join Column
All thematic layers share `ID_UC_G0` as the primary key for joining.

---

## Stage 03: 100m Raster to H3

**Script:** `src/s03_raster_to_h3_100m.py`

Converts 100m GHSL-POP raster tiles to H3 hexagons at resolution 9.

### Processing Flow

```
100m GeoTIFF (Mollweide)
         │
         ▼ reproject
    WGS84 (EPSG:4326)
         │
         ▼ h3ronpy.raster_to_dataframe()
    H3 Resolution 9 cells
         │
         ▼ filter (population > 0)
    Per-tile Parquet
         │
         ▼ DuckDB merge (SUM population by h3_index)
    Merged Parquet
```

### Configuration

| Parameter | Value | Notes |
|-----------|-------|-------|
| H3 Resolution | 9 | ~0.1 km² per cell (matches 100m input) |
| Chunk Size | 2048 x 2048 | For memory-efficient processing |
| Nodata Value | -200.0 | Default if not in raster metadata |

### Outputs

| Output Path | Description |
|-------------|-------------|
| `data/interim/h3_pop_100m/{tile_id}.parquet` | Per-tile H3 cells |
| `data/interim/h3_pop_100m/_progress.json` | Processing progress |
| `data/processed/h3_tiles/h3_pop_2020_res9.parquet` | Merged, deduplicated H3 cells |

### Tile Boundary Handling
H3 cells at tile boundaries may appear in multiple tiles. DuckDB merge sums population for duplicate `h3_index` values.

### Output Schema

| Column | Type | Description |
|--------|------|-------------|
| `h3_index` | UInt64 | H3 cell index |
| `population` | Float64 | Population count |

---

## Stage 04: 1km Raster to H3 (Modal Cloud)

**Script:** `src/s04_raster_to_h3_1km_modal.py`

Processes all 10 epochs in parallel on Modal cloud infrastructure for faster execution.

### Processing Flow

```
1km GeoTIFF (Mollweide) × 10 epochs
         │
         ▼ parallel download in containers
    10 Modal containers (32GB each)
         │
         ▼ reproject to WGS84
         │
         ▼ h3ronpy.raster_to_dataframe()
    H3 Resolution 8 cells (per epoch)
         │
         ▼ DuckDB pivot
    Time series (wide format)
```

### Configuration

| Parameter | Value | Notes |
|-----------|-------|-------|
| H3 Resolution | 8 | ~0.7 km² per cell (matches 1km input) |
| Memory per Container | 32 GB | Processes full raster without tiling |
| Timeout | 30 min | Per epoch processing |
| Parallelism | 10 | One container per epoch |

### Cost Estimate
- **Cloud cost:** ~$0.50-1.00 for all 10 epochs
- **Wall-clock time:** ~5-10 minutes

### Run Modes

| Command | Description |
|---------|-------------|
| `modal run src/s04_raster_to_h3_1km_modal.py` | Full cloud run (all epochs) |
| `modal run src/s04_raster_to_h3_1km_modal.py --test` | Cloud test (2020 only) |
| `modal run src/s04_raster_to_h3_1km_modal.py --local` | Local test (no cloud) |

### Outputs

| Output Path | Description |
|-------------|-------------|
| `data/interim/h3_pop_1km/{epoch}.parquet` | Per-epoch H3 cells |
| `data/interim/h3_pop_1km/time_series.parquet` | Wide-format time series |

### Time Series Schema

| Column | Type | Description |
|--------|------|-------------|
| `h3_index` | UInt64 | H3 cell index |
| `pop_1975` | Float64 | Population in 1975 |
| `pop_1980` | Float64 | Population in 1980 |
| ... | ... | ... |
| `pop_2020` | Float64 | Population in 2020 |

---

## Data Directory Structure

```
data/
├── raw/                              # Original downloaded data
│   ├── ucdb/
│   │   ├── GHS_UCDB_GLOBE_R2024A.gpkg
│   │   ├── GHS_UCDB_GLOBE_R2024A.xlsx
│   │   └── ucdb_schema.json
│   ├── ghsl_pop_100m/
│   │   └── GHS_POP_E2020_*_R{row}_C{col}_*.tif
│   ├── ghsl_pop_1km/
│   │   └── GHS_POP_E{epoch}_*_1000_*.tif
│   └── download_progress.json
│
├── interim/                          # Intermediate processed data
│   ├── ucdb/
│   │   ├── themes/
│   │   │   ├── general_characteristics.parquet
│   │   │   ├── climate.parquet
│   │   │   └── ... (15 theme files)
│   │   ├── ucdb_all.parquet
│   │   ├── geometries.parquet
│   │   └── centroids.parquet
│   ├── cities.parquet
│   ├── h3_pop_100m/
│   │   ├── R{row}_C{col}.parquet
│   │   └── _progress.json
│   └── h3_pop_1km/
│       ├── 1975.parquet
│       ├── ...
│       ├── 2020.parquet
│       └── time_series.parquet
│
└── processed/                        # Final outputs
    └── h3_tiles/
        └── h3_pop_2020_res9.parquet
```

---

## Key Technologies

| Technology | Purpose |
|------------|---------|
| **h3ronpy** | Fast raster-to-H3 conversion (Rust-based) |
| **rioxarray** | Raster I/O with xarray integration |
| **DuckDB** | Efficient merging and deduplication |
| **Polars** | Fast DataFrame operations |
| **Modal** | Serverless cloud compute (Stage 04) |
| **GeoPandas** | Geometry handling for UCDB |

---

## Projection Notes

| Stage | Input CRS | Output CRS |
|-------|-----------|------------|
| Download | N/A | Mollweide (ESRI:54009) |
| UCDB Extract | Mollweide | WGS84 (EPSG:4326) |
| 100m → H3 | Mollweide | WGS84 (required by H3) |
| 1km → H3 | Mollweide | WGS84 (required by H3) |

H3 requires WGS84 coordinates, so all raster data is reprojected before H3 conversion.
