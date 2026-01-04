# In `/pipeline`
- All Python commands should be run with `uv run`
- Use DuckDB cli for data exploration: `duckdb`

## Data Validation

Run validation after any pipeline changes:
```bash
uv run python -m src.s99_validate_cities
uv run python -m src.s99_validate_cities -v  # verbose mode
```

### Adding or Changing Output Data

When modifying pipeline scripts that produce parquet files in `data/processed/cities/`:

1. **Update the Pandera schema** in `src/s99_validate_cities.py`:
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
| 11 duplicate city_ids | Border cities in multiple countries | Deduplicate in s02c |
| 2,648 orphaned city_ids | MTUC vs UCDB city list mismatch | Use UCDB as canonical source |
| 61% NULL growth metrics | Cities didn't exist in 1975 | Expected, document only |
| 19% NULL peer_names | Name lookup failures | Join from cities.parquet |

### Validation Schema Reference

```
cities.parquet          → CitySchema
city_populations.parquet → CityPopulationSchema
city_rankings.parquet   → CityRankingSchema
city_growth.parquet     → CityGrowthSchema
city_density_peers.parquet → CityDensityPeersSchema
```
