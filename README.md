# The Urban World

[![Code License: MIT](https://img.shields.io/badge/code-MIT-blue.svg)](LICENSE)
[![Data License: CC BY-SA 4.0](https://img.shields.io/badge/data-CC%20BY--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-sa/4.0/)

An observatory of urban complexity — telling the story of global urbanization through data, making visible the shape, density, and growth of cities over time.

**Live:** [theurban.world](https://theurban.world)

## Structure

| Directory | Description |
|-----------|-------------|
| [`web/`](web/) | Nuxt 4 frontend deployed to Cloudflare Workers |
| [`pipeline/`](pipeline/) | Python data pipeline for processing urban datasets |

## Data

Population and built-up area data comes from the [Global Human Settlement Layer (GHSL)](https://ghsl.jrc.ec.europa.eu/) published by the European Commission Joint Research Centre. The pipeline processes this into two canonical datasets:

- **ghsl-grid-1km** — raster pixels at 1 km resolution
- **ghsl-h3-r8** — H3 hexagonal cells at resolution 8

Full provenance diagram: [`pipeline/DATA_LINEAGE.md`](pipeline/DATA_LINEAGE.md).

## Getting Started

### Frontend

```bash
pnpm install
pnpm dev:app
```

See [`web/README.md`](web/README.md) for more.

### Pipeline

```bash
cd pipeline
uv sync
uv run python -m src.<domain>.<script>
```

See [`pipeline/README.md`](pipeline/README.md) for the full script catalog.

## Contributing

Contributions are welcome. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for setup, conventions, and the PR process.

## License

- **Code** — [MIT](LICENSE)
- **Content and derived data** — [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)
- **Upstream data** — GHSL is © European Commission JRC, licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
