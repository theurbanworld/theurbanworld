# The Urban World

An observatory of urban complexity — telling the story of global urbanization through data, making visible the shape, density, and growth of cities over time.

## Structure

| Directory | Description |
|-----------|-------------|
| `web/` | Nuxt 3 frontend deployed to Cloudflare Workers |
| `pipeline/` | Python data pipeline for processing urban datasets |

## Data Sources

Population and built-up area data comes from the [Global Human Settlement Layer (GHSL)](https://ghsl.jrc.ec.europa.eu/) published by the European Commission Joint Research Centre. The pipeline processes this into two canonical datasets:

- **ghsl-grid-1km** — raster pixels at 1 km resolution
- **ghsl-h3-r8** — H3 hexagonal cells at resolution 8

## Getting Started

### Frontend

```bash
pnpm install
pnpm dev:app
```

### Pipeline

```bash
cd pipeline
uv sync
uv run python -m src.<domain>.<script>
```

See [`pipeline/README.md`](pipeline/README.md) for detailed pipeline documentation.

## License

Code is [MIT](LICENSE). Content and data are [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
