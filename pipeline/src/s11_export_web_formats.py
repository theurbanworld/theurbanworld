"""
Export web-ready formats for frontend.

Purpose: Generate final JSON and GeoParquet files for web serving
Input:
  - data/interim/cities.parquet
  - data/interim/h3_pop_1km/h3_r8_pop_timeseries.parquet
  - data/interim/city_boundaries/{city_id}.parquet
  - data/interim/radial_profiles/{city_id}.json
  - data/processed/h3_tiles/h3_r9_pop_2025.parquet
Output:
  - data/processed/cities/{city_id}.json (per-city files)
  - data/processed/city_index.json (search index)
  - data/processed/h3_tiles/h3_r9_pop_2025.geoparquet (with geometry)

Decision log:
  - City JSONs contain all data for single-city views
  - City index is lightweight for search/autocomplete
  - H3 boundaries stored as cell ID arrays (efficient encoding)
  - Include metadata for data provenance
Date: 2024-12-08
"""
