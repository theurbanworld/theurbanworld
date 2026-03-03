# Data Lineage

Developer quick-reference for every pipeline script and its data dependencies. For the public-facing provenance visualization, see [theurban.world/data](https://theurban.world/data).

Full data flow from raw GHSL sources through the pipeline to R2 and frontend composables.

> All pipeline scripts must be run from the `pipeline/` directory (CWD dependency for standalone scripts using relative `Path("data/...")` paths).

## Pipeline Flow

```mermaid
graph TD
    subgraph "Raw Sources"
        GHSL_POP["GHSL-POP R2023A<br/>1km population rasters<br/>12 epochs (1975-2030)"]
        GHSL_UCDB["GHSL-UCDB R2024A<br/>City attributes (GeoPackage)"]
        GHSL_MTUC["GHSL-MTUC R2024A<br/>Multi-temporal boundaries"]
        PROTOMAPS["Protomaps basemap<br/>~120GB PMTiles"]
    end

    subgraph "download/"
        DL_GHSL["download_ghsl.py"]
        DL_H3["download_h3_r8.py"]
    end

    subgraph "cities/"
        EXT_ATTR["extract_attributes.py"]
        EXT_GEOM["extract_geometries.py"]
        GEN_CITY["generate_cities.py"]
        COMP_POP["compute_populations.py<br/>--source h3-r8 | grid-1km"]
        COMP_RANK["compute_rankings.py<br/>--source h3-r8 | grid-1km"]
    end

    subgraph "grid/"
        EXT_GRID["extract_grid_1km.py<br/>(local)"]
    end

    subgraph "h3/"
        MODAL_H3["modal_raster_to_h3_r8.py<br/>(Modal cloud)"]
        MERGE_TS["merge_h3_r8_timeseries.py"]
        LOAD_PG["load_h3_r8_to_psql.py<br/>(optional, QGIS)"]
    end

    subgraph "radial/"
        GEN_RAD["generate_radial_profiles.py"]
    end

    subgraph "tiles/"
        MODAL_BM["modal_download_basemap.py<br/>(Modal cloud)"]
        GEN_BNDY["generate_boundaries.py"]
        GEN_GRID_OUT["generate_grid_1km_outlines.py"]
        GEN_H3_OUT["generate_h3_r8_outlines.py"]
        GEN_FONT["generate_font_glyphs.py"]
        GEN_SPR["generate_hover_sprites.py"]
    end

    subgraph "web_export/"
        GEN_IDX["generate_city_index.py"]
        GEN_POP["generate_city_populations.py<br/>--source h3-r8 | grid-1km"]
        GEN_CELLS["generate_city_cells.py"]
        GEN_RAD_EXP["generate_radial_profiles.py"]
    end

    subgraph "validate/"
        VAL["validate_cities.py<br/>--source h3-r8 | grid-1km"]
    end

    %% Download flow
    GHSL_POP --> DL_GHSL
    GHSL_UCDB --> DL_GHSL
    GHSL_MTUC --> DL_GHSL

    %% City extraction
    DL_GHSL -->|ucdb.gpkg| EXT_ATTR
    DL_GHSL -->|mtuc.gpkg| EXT_GEOM
    EXT_ATTR -->|ucdb_*.parquet| GEN_CITY
    EXT_GEOM -->|mtuc_*.parquet| GEN_CITY
    GEN_CITY -->|cities.parquet| COMP_POP
    GEN_CITY -->|cities.parquet| GEN_IDX

    %% Grid flow
    GHSL_POP -->|1km Mollweide rasters| EXT_GRID
    EXT_GEOM -->|geometries_by_epoch.parquet| EXT_GRID
    EXT_GRID -->|grid_1km_pop_*.parquet| COMP_POP
    EXT_GRID -->|grid_1km_pop_*.parquet| GEN_GRID_OUT

    %% H3 flow
    GHSL_POP --> MODAL_H3
    MODAL_H3 -->|R2: ghsl-pop-1km/*.parquet| DL_H3
    DL_H3 -->|h3_r8_pop_*.parquet| COMP_POP
    DL_H3 -->|h3_r8_pop_*.parquet| MERGE_TS
    DL_H3 -->|h3_r8_pop_*.parquet| LOAD_PG
    DL_H3 -->|h3_r8_pop_*.parquet| GEN_RAD
    DL_H3 -->|h3_r8_pop_*.parquet| GEN_H3_OUT

    %% City computation
    COMP_POP -->|city_populations_{source}.parquet| COMP_RANK
    COMP_POP -->|city_populations_{source}.parquet| GEN_POP
    COMP_POP -->|city_populations_{source}.parquet| GEN_BNDY
    COMP_RANK -->|city_rankings_{source}.parquet<br/>city_growth_{source}.parquet<br/>city_density_peers_{source}.parquet| GEN_BNDY

    %% Outlines need rankings for trend attributes
    COMP_RANK -->|city_rankings_grid_1km.parquet| GEN_GRID_OUT
    COMP_RANK -->|city_rankings_h3_r8.parquet| GEN_H3_OUT

    %% Tiles
    PROTOMAPS --> MODAL_BM

    %% Validation
    GEN_CITY -.->|cities.parquet| VAL
    COMP_POP -.->|city_populations_{source}.parquet| VAL
    COMP_RANK -.->|city_rankings_{source}.parquet| VAL
    GEN_RAD -.->|radial_profiles_h3_r8.parquet| VAL

    subgraph "R2 (data.theurban.world)"
        R2_BM["tiles/20260101.pmtiles"]
        R2_BNDY["tiles/city_boundaries.pmtiles"]
        R2_GRID_OUT["tiles/grid_1km_outlines.pmtiles"]
        R2_H3_OUT["tiles/h3_r8_outlines.pmtiles"]
        R2_H3["data/h3_r8_pop_timeseries.parquet"]
        R2_IDX["data/cities_index.json"]
        R2_POP_GRID["data/city_populations_grid_1km.json"]
        R2_POP_H3["data/city_populations_h3_r8.json"]
        R2_FONT["fonts/{fontstack}/{range}.pbf"]
        R2_SPR["sprites/patterns*"]
    end

    MODAL_BM --> R2_BM
    GEN_BNDY --> R2_BNDY
    GEN_GRID_OUT --> R2_GRID_OUT
    GEN_H3_OUT --> R2_H3_OUT
    MERGE_TS --> R2_H3
    GEN_IDX --> R2_IDX
    GEN_POP -->|--source grid-1km| R2_POP_GRID
    GEN_POP -->|--source h3-r8| R2_POP_H3
    GEN_FONT --> R2_FONT
    GEN_SPR --> R2_SPR

    %% City cells and radial profile exports
    DL_H3 -->|h3_r8_pop_*.parquet| GEN_CELLS
    EXT_GRID -->|grid_1km_pop_*.parquet| GEN_CELLS
    GEN_RAD -->|radial_profiles_h3_r8.parquet| GEN_RAD_EXP

    subgraph "Frontend Composables"
        USE_MAP["useMap"]
        USE_H3["useH3Data"]
        USE_CI["useCitiesIndex"]
        USE_CP["useCityPopulations"]
    end

    R2_BM --> USE_MAP
    R2_BNDY --> USE_MAP
    R2_GRID_OUT --> USE_MAP
    R2_H3_OUT --> USE_MAP
    R2_FONT --> USE_MAP
    R2_SPR --> USE_MAP
    R2_H3 --> USE_H3
    R2_IDX --> USE_CI
    R2_POP_GRID --> USE_CP
    R2_POP_H3 --> USE_CP
```

## R2 Artifact Mapping

| R2 Key | Pipeline Source | Content Type | Web Consumer | Notes |
|--------|---------------|--------------|--------------|-------|
| `tiles/20260101.pmtiles` | `tiles/modal_download_basemap.py` | `application/octet-stream` | `useMap` (basemap style) | ~120GB, updated monthly |
| `tiles/city_boundaries.pmtiles` | `tiles/generate_boundaries.py` | `application/octet-stream` | `useMap` (MTUC boundary layer) | Per-epoch features with pop/density/trends |
| `tiles/grid_1km_outlines.pmtiles` | `tiles/generate_grid_1km_outlines.py` | `application/octet-stream` | `useMap` (grid mode) | Dissolved 1km pixel outlines per city |
| `tiles/h3_r8_outlines.pmtiles` | `tiles/generate_h3_r8_outlines.py` | `application/octet-stream` | `useMap` (H3 mode) | Dissolved H3 cell outlines per city |
| `data/h3_r8_pop_timeseries.parquet` | `h3/merge_h3_r8_timeseries.py` | `application/vnd.apache.parquet` | `useH3Data` | Wide format, snappy compression for browser |
| `data/cities_index.json` | `web_export/generate_city_index.py` | `application/json` | `useCitiesIndex` | Static city metadata, search/lookup |
| `data/city_populations_grid_1km.json` | `web_export/generate_city_populations.py --source grid-1km` | `application/json` | `useCityPopulations` | Per-epoch pop/area/density (grid) |
| `data/city_populations_h3_r8.json` | `web_export/generate_city_populations.py --source h3-r8` | `application/json` | `useCityPopulations` | Per-epoch pop/area/density (H3) |
| `fonts/{fontstack}/{range}.pbf` | `tiles/generate_font_glyphs.py` | `application/x-protobuf` | `useMap` (text labels) | MapLibre glyph protocol |
| `sprites/patterns*` | `tiles/generate_hover_sprites.py` | `image/png`, `application/json` | `useMap` (hover sprites) | Diagonal stripe patterns |

## Citation and Methodology

| Dataset | Source | Methodology | Frontend Consumer |
|---------|--------|-------------|-------------------|
| Population per H3 cell | GHSL-POP R2023A (JRC) | 1km raster resampled to H3 res-8 via modal assignment. Each raster pixel contributes to the H3 cell containing its centroid. | `useH3Data` -> `H3PopulationLayer` |
| Population per grid pixel | GHSL-POP R2023A (JRC) | 1km Mollweide raster pixels extracted within MTUC city boundaries. Each pixel = exactly 1 km². | (planned) |
| City population (H3) | GHSL-POP + GHSL-MTUC R2024A | Sum of H3 res-8 cell populations within MTUC city boundary at each epoch. Area = sum of exact H3 cell areas. | `useCityPopulations` -> `CityInfoPanel` |
| City population (grid) | GHSL-POP + GHSL-MTUC R2024A | Sum of 1km pixel populations within MTUC city boundary at each epoch. Area = pixel count (equal-area Mollweide). | `useCityPopulations` -> `CityInfoPanel` |
| City boundaries | GHSL-MTUC R2024A | Multi-temporal urban center boundaries, one polygon per city per epoch. | `useMap` -> boundary layer |
| Radial density profiles | GHSL-POP + computed centroids | Bertaud-style: population-weighted centroid, 1km concentric rings out to 50km, density per ring. H3 source only. | TBD |
| City metadata (name, country) | GHSL-UCDB R2024A | Thematic attributes extracted from GeoPackage. ISO country codes via pycountry. | `useCitiesIndex` -> `CitySearch` |
