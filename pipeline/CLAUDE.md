# In `/pipeline`
- All Python commands should be run with `uv run`
- Use DuckDB cli for data exploration: `duckdb`

## Running pipeline scripts

Scripts are organized by domain under `src/`:

```bash
# Download
uv run python -m src.download.download_ghsl
uv run python -m src.download.download_h3_r8

# Cities
uv run python -m src.cities.extract_attributes extract
uv run python -m src.cities.extract_geometries
uv run python -m src.cities.generate_cities
uv run python -m src.cities.compute_populations
uv run python -m src.cities.compute_rankings

# H3
uv run python -m src.h3.merge_timeseries --local
uv run python -m src.h3.load_to_psql

# Radial
uv run python -m src.radial.compute_profiles

# Tiles
uv run python -m src.tiles.generate_boundaries --local
uv run python -m src.tiles.generate_font_glyphs --local
uv run python -m src.tiles.generate_hover_sprites --local

# Web export (JSON for frontend)
uv run python -m src.web_export.generate_city_index --local
uv run python -m src.web_export.generate_city_populations --local

# Validate
uv run python -m src.validate.validate_cities -v

# Explore (Streamlit)
uv run streamlit run src/explore/app_explore.py
```

## Data Validation

Run validation after any pipeline changes:
```bash
uv run python -m src.validate.validate_cities
uv run python -m src.validate.validate_cities -v  # verbose mode
```

### Adding or Changing Output Data

When modifying pipeline scripts that produce parquet files in `data/processed/cities/`:

1. **Update the Pandera schema** in `src/validate/validate_cities.py`:
   - Add/modify the `DataFrameModel` class for the affected table
   - Use proper types: `str`, `int`, `float` with `Field()` constraints
   - Set `nullable=True` for columns that can have NULL values
   - Add range constraints: `ge=`, `le=`, `gt=`, `lt=` for numeric bounds

2. **Add cross-table validation** if needed:
   - Foreign key checks go in `check_foreign_keys()`
   - New data quality checks get their own function
   - Call the new check in `main()` under "Data Quality Checks"

3. **Run validation** to verify the schema matches actual data

### Known Data Issues (as of 2025-12-27)

| Issue | Cause | Future Fix |
|-------|-------|------------|
| 11 duplicate city_ids | Border cities in multiple countries | Deduplicate in cities/generate_cities |
| 2,648 orphaned city_ids | MTUC vs UCDB city list mismatch | Use UCDB as canonical source |
| 61% NULL growth metrics | Cities didn't exist in 1975 | Expected, document only |
| 19% NULL peer_names | Name lookup failures | Join from cities.parquet |

### Validation Schema Reference

```
cities.parquet           -> CitySchema          (in src/validate/validate_cities.py)
city_populations.parquet -> CityPopulationSchema
city_rankings.parquet    -> CityRankingSchema
city_growth.parquet      -> CityGrowthSchema
city_density_peers.parquet -> CityDensityPeersSchema
```
