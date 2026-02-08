# Data Lineage

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
        COMP_POP["compute_populations.py"]
        COMP_RANK["compute_rankings.py"]
    end

    subgraph "h3/"
        MODAL_H3["modal_raster_to_h3.py<br/>(Modal cloud)"]
        MERGE_TS["merge_timeseries.py"]
        LOAD_PG["load_to_psql.py<br/>(optional, QGIS)"]
    end

    subgraph "radial/"
        COMP_RAD["compute_profiles.py"]
    end

    subgraph "tiles/"
        MODAL_BM["modal_download_basemap.py<br/>(Modal cloud)"]
        GEN_BNDY["generate_boundaries.py"]
        GEN_FONT["generate_font_glyphs.py"]
        GEN_SPR["generate_hover_sprites.py"]
    end

    subgraph "web_export/"
        GEN_IDX["generate_city_index.py"]
        GEN_POP["generate_city_populations.py"]
    end

    subgraph "validate/"
        VAL["validate_cities.py"]
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

    %% H3 flow
    GHSL_POP --> MODAL_H3
    MODAL_H3 -->|R2: ghsl-pop-1km/*.parquet| DL_H3
    DL_H3 -->|h3_r8_pop_*.parquet| COMP_POP
    DL_H3 -->|h3_r8_pop_*.parquet| MERGE_TS
    DL_H3 -->|h3_r8_pop_*.parquet| LOAD_PG

    %% City computation
    COMP_POP -->|city_populations.parquet| COMP_RANK
    COMP_POP -->|city_populations.parquet| GEN_POP
    COMP_POP -->|city_populations.parquet| COMP_RAD
    COMP_RANK -->|city_rankings.parquet<br/>city_growth.parquet<br/>city_density_peers.parquet| GEN_BNDY
    COMP_POP -->|city_populations.parquet| GEN_BNDY

    %% Tiles
    PROTOMAPS --> MODAL_BM

    %% Validation
    GEN_CITY -.->|cities.parquet| VAL
    COMP_POP -.->|city_populations.parquet| VAL
    COMP_RANK -.->|city_rankings.parquet| VAL

    subgraph "R2 (data.theurban.world)"
        R2_BM["tiles/20260101.pmtiles"]
        R2_BNDY["tiles/city_boundaries.pmtiles"]
        R2_H3["data/h3_r8_pop_timeseries.parquet"]
        R2_IDX["data/cities_index.json"]
        R2_POP["data/city_populations.json"]
        R2_FONT["fonts/{fontstack}/{range}.pbf"]
        R2_SPR["sprites/patterns*"]
    end

    MODAL_BM --> R2_BM
    GEN_BNDY --> R2_BNDY
    MERGE_TS --> R2_H3
    GEN_IDX --> R2_IDX
    GEN_POP --> R2_POP
    GEN_FONT --> R2_FONT
    GEN_SPR --> R2_SPR

    subgraph "Frontend Composables"
        USE_MAP["useMap"]
        USE_H3["useH3Data"]
        USE_CI["useCitiesIndex"]
        USE_CP["useCityPopulations"]
    end

    R2_BM --> USE_MAP
    R2_BNDY --> USE_MAP
    R2_FONT --> USE_MAP
    R2_SPR --> USE_MAP
    R2_H3 --> USE_H3
    R2_IDX --> USE_CI
    R2_POP --> USE_CP
```

## R2 Artifact Mapping

| R2 Key | Pipeline Source | Content Type | Web Consumer | Notes |
|--------|---------------|--------------|--------------|-------|
| `tiles/20260101.pmtiles` | `tiles/modal_download_basemap.py` | `application/octet-stream` | `useMap` (basemap style) | ~120GB, updated monthly |
| `tiles/city_boundaries.pmtiles` | `tiles/generate_boundaries.py` | `application/octet-stream` | `useMap` (boundary layer) | Per-epoch features with pop/density/trends |
| `data/h3_r8_pop_timeseries.parquet` | `h3/merge_timeseries.py` | `application/vnd.apache.parquet` | `useH3Data` | Wide format, snappy compression for browser |
| `data/cities_index.json` | `web_export/generate_city_index.py` | `application/json` | `useCitiesIndex` | Static city metadata, search/lookup |
| `data/city_populations.json` | `web_export/generate_city_populations.py` | `application/json` | `useCityPopulations` | Per-epoch pop/area/density |
| `fonts/{fontstack}/{range}.pbf` | `tiles/generate_font_glyphs.py` | `application/x-protobuf` | `useMap` (text labels) | MapLibre glyph protocol |
| `sprites/patterns*` | `tiles/generate_hover_sprites.py` | `image/png`, `application/json` | `useMap` (hover sprites) | Diagonal stripe patterns |

## Citation and Methodology

| Dataset | Source | Methodology | Frontend Consumer |
|---------|--------|-------------|-------------------|
| Population per H3 cell | GHSL-POP R2023A (JRC) | 1km raster resampled to H3 res-8 via modal assignment. Each raster pixel contributes to the H3 cell containing its centroid. | `useH3Data` -> `H3PopulationLayer` |
| City population | GHSL-POP + GHSL-MTUC R2024A | Sum of H3 res-8 cell populations within MTUC city boundary at each epoch. | `useCityPopulations` -> `CityInfoPanel` |
| City area | H3 cell areas | Sum of exact H3 res-8 cell areas (km2) within MTUC boundary. More accurate than bbox approximation. | `useCityPopulations` -> `CityInfoPanel` |
| City density | Derived | City population / city area (per km2). | `useCityPopulations` -> `CityInfoPanel` |
| City boundaries | GHSL-MTUC R2024A | Multi-temporal urban center boundaries, one polygon per city per epoch. | `useMap` -> boundary layer |
| Radial density profiles | GHSL-POP + computed centroids | Bertaud-style: population-weighted centroid, 1km concentric rings out to 50km, density per ring. | TBD |
| City metadata (name, country) | GHSL-UCDB R2024A | Thematic attributes extracted from GeoPackage. ISO country codes via pycountry. | `useCitiesIndex` -> `CitySearch` |
