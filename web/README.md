# The Urban World

An "Our World in Data" for cities — explore global urban population density, growth patterns, and urban form.

## Status

Under Development — See [TASKS.md](./TASKS.md) for progress.

## Tech Stack

- **Framework**: Nuxt 4
- **UI**: Nuxt UI 4, Tailwind CSS
- **Mapping**: MapLibre GL JS, deck.gl, PMTiles
- **Data**: H3 hexagons, GeoParquet, Cloudflare R2
- **Charts**: Chart.js (via vue-chartjs)
- **Search**: Fuse.js

## Setup

```bash
# Install dependencies
pnpm install

# Copy environment template
cp .env.example .env

# Start development server
pnpm dev
```

## Environment Variables

See `.env.example` for required environment variables:
- `NUXT_PUBLIC_R2_BASE_URL` - Base URL for R2 bucket containing data
- `NUXT_PUBLIC_PROTOMAPS_KEY` - Protomaps API key (development only)

## Project Structure

```
app/
├── app/
│   ├── components/       # Vue components
│   │   ├── map/          # Map-related (GlobalMap, H3Layer, Controls)
│   │   ├── city/         # City details (Panel, Stats, Charts)
│   │   ├── search/       # City search (CommandPalette)
│   │   └── ui/           # UI utilities (Loading, Attribution)
│   ├── composables/      # Vue composables (useMap, useDeckGL, etc.)
│   ├── pages/            # Route pages (index, about)
│   └── layouts/          # App layouts
├── types/                # TypeScript type definitions
├── utils/                # Utility functions
└── nuxt.config.ts        # Nuxt configuration
```

## Data Sources

- **Population**: [Global Human Settlement Layer (GHSL)](https://ghsl.jrc.ec.europa.eu/) — European Commission JRC
- **Basemap**: [OpenStreetMap](https://www.openstreetmap.org/) via [Protomaps](https://protomaps.com/)

## License

TODO: Add license
