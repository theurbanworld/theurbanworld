"""Climate & Energy domain.

Retains the energy/climate-relevant GHS-UCDB attributes that the pipeline
already extracts into ``ucdb_all.parquet`` but discards when building the
6-column ``cities.parquet``. Surfaces them as a per-city climate profile.

Modules:
  - ``catalog``: the declarative metric catalog (single source of truth)
  - ``build_city_climate``: ``ucdb_all.parquet`` -> ``city_climate.parquet``

The catalog is mirrored on the web side in ``web/types/climate.ts``; the two
must stay aligned (metric keys, temporal classes, methodology paths).
"""
