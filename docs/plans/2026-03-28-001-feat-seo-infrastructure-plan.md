---
title: "feat: Add SEO infrastructure — sitemap, robots, schema.org, Wikidata linking"
type: feat
status: active
date: 2026-03-28
---

# SEO Infrastructure: Sitemap, Robots, Schema.org, and Wikidata

## Overview

Add comprehensive SEO infrastructure to make 13k+ city pages discoverable by search engines, connect city entities to the knowledge graph via Wikidata, and provide structured data for Google Dataset Search.

## Problem Frame

The site has good content (13k city pages with population data, density profiles, outlines) but almost zero search engine discoverability. There is no sitemap, no robots.txt, no structured data, and no external entity links. City pages are invisible to Google because there's no sitemap telling crawlers they exist.

## Requirements Trace

- R0. Fix SSR data availability for city pages so meta tags, OG images, and schema.org render correctly for crawlers
- R1. Generate a sitemap with all city routes + static pages
- R2. Serve a robots.txt with sitemap reference
- R3. Add JSON-LD schema.org markup: WebSite, City/Place (per city page), Dataset (on /data page)
- R4. Link city entities to Wikidata via `sameAs` in structured data
- R5. Add `wikidata_id` to the pipeline's city data and frontend index

## Scope Boundaries

- No prerendering strategy (separate concern)
- No Twitter card meta (X reads OG tags as fallback — already covered)
- No i18n / hreflang (single language site)
- No link checker setup (can add later)
- Wikidata matching will be best-effort — some cities won't match and that's fine
- The heavy composables (`useCitiesIndex`, `useCityPopulations`) stay `server: false` for the interactive map/search — only the lightweight per-city metadata gets SSR'd

## Context & Research

### Relevant Code and Patterns

- `web/nuxt.config.ts` — module registration, `site.url` already configured
- `web/app/pages/city/[city_id].vue` — city page with `useSeoMeta` and `defineOgImage`
- `web/app/composables/useCitiesIndex.ts` — city data composable, fetches from R2, `server: false`
- `pipeline/src/web_export/generate_city_index.py` — generates `cities_index.json` with id, name, country, country_code, centroid, bbox, population
- `pipeline/src/cities/generate_cities.py` — source of truth for city metadata from UCDB GeoPackage

### Critical SSR Issue

City data is loaded with `server: false` and `immediate: false` in `useCitiesIndex`. During SSR:

1. **Meta tags** — `useSeoMeta` uses reactive getters (`() => city.value ? ...`), but `city.value` is `undefined` during SSR. Crawlers see `<title>City — The Urban World</title>` instead of the actual city name.
2. **OG images** — `defineOgImage` passes `.value` directly (not reactive getters), so the Satori renderer gets `undefined` for city name, country, population. Social shares show a broken preview.
3. **Schema.org** — `useSchemaOrg` runs during SSR. City JSON-LD would render with empty data.

**Solution**: Create a lightweight server route (`server/api/city/[id].ts`) that looks up a single city from the cached cities index. The city page does a server-compatible `useAsyncData` call for just that city's metadata (~200 bytes), which is tiny enough to serialize into SSR payload. The heavy composables stay `server: false` for the interactive UI.

This is a prerequisite for the entire SEO plan — without it, schema.org, meta tags, and OG images are all broken for crawlers. The sitemap endpoint (Unit 2) shares the same server-side R2 fetch pattern, so the caching utility is reused.

### External References

- [Nuxt SEO (`@nuxtjs/seo`)](https://nuxtseo.com) — meta-package bundling sitemap, robots, schema-org, og-image
- [nuxt-schema-org `useSchemaOrg`](https://nuxtseo.com/docs/schema-org/api/use-schema-org) — `definePlace`, `defineWebSite`, raw JSON-LD for Dataset
- [Wikidata Reconciliation API](https://wikidata.reconci.link/) — bulk city matching
- [Google Dataset Structured Data](https://developers.google.com/search/docs/appearance/structured-data/dataset)

## Key Technical Decisions

- **Server-side city metadata via Nitro route + cached R2 fetch**: Rather than making the full 1.2 MB cities index SSR-compatible (which would bloat every page response), create a server route that returns a single city's metadata (~200 bytes). The cities index is fetched from R2 once and cached in-memory on the server. The city page calls this via a server-compatible `useAsyncData` (no `server: false`), so meta tags, OG images, and schema.org all render correctly during SSR. The existing `useCitiesIndex` composable stays `server: false` for the interactive map/search — two data paths for two concerns.

- **`@nuxtjs/seo` meta-package over individual modules**: Bundles sitemap, robots, schema-org, and replaces standalone `nuxt-og-image`. Single install, modules designed to work together. The project already has `nuxt-og-image` v5 — the meta-package pulls in v6+, so the standalone dep gets removed.

- **Runtime sitemap generation (not build-time)**: City data lives on R2 and changes independently of deploys. Runtime generation with SWR caching fits the Cloudflare Workers model. The `zeroRuntime` mode won't work because it requires static routes at build time.

- **Chunked multi-sitemaps**: 13k URLs exceeds practical single-file limits. Chunk into pages + cities sitemaps. The sitemap module handles this with `chunks: true`.

- **Nitro server endpoint for sitemap data**: Create `server/api/__sitemap__/cities.ts` that fetches `cities_index.json` from R2 and returns URL entries. This runs server-side only and doesn't bloat the client bundle.

- **Schema.org `City` type (not `Place`)**: `City` extends `Place > AdministrativeArea > City`. More specific, better Knowledge Graph signal.

- **Wikidata matching via SPARQL bulk + reconciliation API**: Download all Wikidata cities via SPARQL (paginated by country to avoid 60s timeout), spatial+name join locally, then reconciliation API for residuals. Expected ~70-80% match rate from spatial join, remainder via API.

- **`wikidata_id` as optional field**: Not all 13k cities will match. The field is nullable in the pipeline and omitted from JSON when absent. Schema.org markup skips `sameAs` when no Wikidata ID exists.

- **`blockAiBots: true` in robots config**: Block GPTBot, CCBot, etc. from scraping content for AI training. Standard practice for content sites.

## Open Questions

### Resolved During Planning

- **KV binding for sitemap cache?** No — skip for now. Default in-memory cache with SWR is sufficient. KV adds deployment complexity and the sitemap data is small enough that regeneration on Worker cold starts is fast.

- **Should schema.org identity be Person or Organization?** Person (`Jonathan Pichot`). This is a personal project, not an org. Use `definePerson` in schema config.

### Deferred to Implementation

- **Exact SPARQL pagination strategy**: The Wikidata SPARQL endpoint times out at 60s for a full global city dump. Implementation will determine whether to paginate by country, region, or population range.

- **Match confidence threshold**: The spatial join needs a distance threshold (likely 25km) and fuzzy name similarity threshold. These need tuning during implementation based on actual match quality.

- **Wikipedia URL derivation**: Once Wikidata IDs exist, Wikipedia article URLs can be derived via the Wikidata API. Whether to store them or derive at runtime is an implementation choice.

## Implementation Units

- [ ] **Unit 0: Server-side city metadata for SSR**

**Goal:** Make individual city metadata available during SSR so that meta tags, OG images, and schema.org render correctly for crawlers and social media.

**Requirements:** R0

**Dependencies:** None

**Files:**
- Create: `web/server/utils/citiesIndex.ts` (cached R2 fetch utility)
- Create: `web/server/api/city/[id].ts` (single-city lookup endpoint)
- Modify: `web/app/pages/city/[city_id].vue` (add SSR-compatible city metadata fetch, fix `defineOgImage`)

**Approach:**
- **Server utility** (`server/utils/citiesIndex.ts`): Fetch `cities_index.json` from R2 (using `r2BaseUrl` from runtime config with fallback to `data.theurban.world`). Cache the result in a module-level variable with a TTL (e.g., 1 hour). Build a `Map<string, CityIndexEntry>` for O(1) lookups. Export `getCityById(id: string)` and `getAllCities()` functions. This utility is reused by the sitemap endpoint in Unit 2.
- **API route** (`server/api/city/[id].ts`): Use `defineEventHandler`, read `id` from route params, call `getCityById()`, return the city entry or 404. Response is ~200 bytes.
- **City page update**: Add a new `useAsyncData` call (SSR-compatible, no `server: false`) that fetches `/api/city/${cityId}` for the current city. This provides `cityMeta` during SSR. Use `cityMeta` for `useSeoMeta` and `defineOgImage` instead of the client-only `city` computed. Fix `defineOgImage` to use reactive getters or computed values that resolve from `cityMeta`.
- The existing `useCitiesIndex` composable and its `server: false` fetch are untouched — they continue powering the interactive map and search client-side.

**Patterns to follow:**
- `web/app/composables/useCitiesIndex.ts` for the `CityIndexEntry` type and R2 URL construction
- Nitro server utils pattern: module-level cache, exported functions

**Test scenarios:**
- Happy path: `GET /api/city/1234` returns `{ id, name, country, country_code, centroid, bbox, population }` with 200 status
- Happy path: SSR HTML for `/city/1234` contains `<title>CityName, Country — The Urban World</title>` (not the fallback)
- Happy path: OG image for a city page renders with correct city name and stats
- Error path: `GET /api/city/nonexistent` returns 404
- Edge case: first request triggers R2 fetch and caches; subsequent requests use cache

**Verification:**
- `curl -s localhost:3000/city/1234 | grep '<title>'` shows actual city name
- OG image preview (via `/__og-image__/image/city/1234`) shows city-specific data
- No increase in client bundle size (server utility is server-only)

---

- [ ] **Unit 1: Install `@nuxtjs/seo` and configure base modules**

**Goal:** Replace standalone `nuxt-og-image` with the `@nuxtjs/seo` meta-package. Configure robots, sitemap skeleton, and schema.org identity.

**Requirements:** R1, R2

**Dependencies:** None

**Files:**
- Modify: `web/package.json`
- Modify: `web/nuxt.config.ts`

**Approach:**
- `pnpm add @nuxtjs/seo` and `pnpm remove nuxt-og-image`
- Replace `'nuxt-og-image'` with `'@nuxtjs/seo'` in modules array. Ensure it comes before `@nuxt/content`.
- Add `site.name` and `site.description` to existing `site` config
- Add `robots` config with `blockAiBots: true`
- Add `sitemap` config with `sitemaps` structure (pages + cities), chunking enabled, but don't create the server endpoint yet
- Add `schemaOrg` config with `identity` as Person (Jonathan Pichot)
- Verify the app still builds and serves correctly

**Patterns to follow:**
- Existing `nuxt.config.ts` structure

**Test scenarios:**
- Happy path: `pnpm dev:app` starts without errors after module swap
- Happy path: `/robots.txt` returns valid robots.txt with `Sitemap:` directive
- Edge case: OG images still generate correctly after `nuxt-og-image` version bump

**Verification:**
- Dev server starts, robots.txt is served, no console errors

---

- [ ] **Unit 2: Sitemap server endpoint for city URLs**

**Goal:** Create a Nitro server endpoint that returns all city URLs for the sitemap module.

**Requirements:** R1

**Dependencies:** Unit 0 (reuses `server/utils/citiesIndex.ts`), Unit 1

**Files:**
- Create: `web/server/api/__sitemap__/cities.ts`

**Approach:**
- Use `defineSitemapEventHandler` from `#imports`
- Call `getAllCities()` from the shared `server/utils/citiesIndex.ts` (already fetches and caches from R2)
- Map each city to `{ loc: '/city/${city.id}', changefreq: 'monthly', priority: 0.6 }`
- Static pages (`/`, `/about`, `/data`, `/methodology`) are auto-discovered by `includeAppSources: true`

**Patterns to follow:**
- `web/server/utils/citiesIndex.ts` from Unit 0 for data access

**Test scenarios:**
- Happy path: endpoint returns 13k+ URL entries with correct `/city/{id}` paths
- Happy path: `/sitemap_index.xml` lists pages sitemap and chunked cities sitemaps
- Error path: if R2 fetch fails, endpoint returns empty array (sitemap still valid, just incomplete)

**Verification:**
- Visit `/sitemap_index.xml` in dev — shows sitemap index with multiple chunked city sitemaps
- Visit a city sitemap chunk — contains valid `<url>` entries

---

- [ ] **Unit 3: Schema.org markup — WebSite + Dataset**

**Goal:** Add site-wide WebSite schema and Dataset schema on the /data page.

**Requirements:** R3

**Dependencies:** Unit 1

**Files:**
- Modify: `web/app/app.vue` (WebSite schema)
- Modify: `web/app/pages/data.vue` (Dataset schema)

**Approach:**
- In `app.vue`, add `useSchemaOrg([defineWebSite({ name, description, inLanguage: 'en' })])`. The module auto-generates a WebPage node per page.
- In `data.vue`, add `useSchemaOrg` with a raw `Dataset` object (no `defineDataset` helper exists). Include: name, description, license (CC BY-SA 4.0), temporalCoverage (1975/2025), spatialCoverage (Global), creator (Jonathan Pichot), and `isBasedOn` referencing the GHSL UCDB dataset with its JRC Data Catalogue DOI and CC BY 4.0 license.

**Patterns to follow:**
- Existing `useSeoMeta` calls in each page

**Test scenarios:**
- Happy path: view page source of `/` — contains `<script type="application/ld+json">` with WebSite node
- Happy path: view page source of `/data` — contains Dataset node with GHSL attribution
- Happy path: Dataset JSON-LD passes [Google Rich Results Test](https://search.google.com/test/rich-results)

**Verification:**
- JSON-LD appears in rendered HTML source for both pages

---

- [ ] **Unit 4: Schema.org markup — City pages**

**Goal:** Add City schema with geo, population, and containedInPlace on each city page.

**Requirements:** R3, R4

**Dependencies:** Unit 0 (SSR city data), Unit 1

**Files:**
- Modify: `web/app/pages/city/[city_id].vue`

**Approach:**
- Use the SSR-compatible `cityMeta` from Unit 0 (available during SSR via the server API route).
- Add `useSchemaOrg` with a City node using `cityMeta` data.
- Use `@type: 'City'` with `geo` (GeoCoordinates from centroid), `containedInPlace` (Country with name), and `additionalProperty` for population.
- Conditionally add `sameAs` array with Wikidata URL when `wikidata_id` exists (will be empty until Unit 6 adds the field).
- Use `identifier` with `PropertyValue` to expose the UCDB city_id.
- Since Unit 0 makes city data available during SSR, the JSON-LD will render correctly in the initial HTML for crawlers.

**Patterns to follow:**
- Existing `useSeoMeta` pattern in the same file
- `cityMeta` ref pattern established in Unit 0

**Test scenarios:**
- Happy path: view SSR HTML source of a city page — contains `<script type="application/ld+json">` with City node including name, geo, population
- Happy path: `containedInPlace` shows country name
- Edge case: city without population — schema still valid, population property omitted
- Edge case: city without wikidata_id — `sameAs` array omitted

**Verification:**
- `curl -s localhost:3000/city/1234 | grep 'application/ld+json'` contains City schema with real data (not empty)

---

- [ ] **Unit 5: Pipeline — Wikidata matching script**

**Goal:** Create a pipeline script that matches UCDB cities to Wikidata entities and adds `wikidata_id` to city data.

**Requirements:** R5

**Dependencies:** None (independent of frontend units)

**Files:**
- Create: `pipeline/src/cities/match_wikidata.py`
- Modify: `pipeline/src/web_export/generate_city_index.py` (include `wikidata_id` in output)
- Modify: `pipeline/src/cities/generate_cities.py` (add `wikidata_id` column)

**Approach:**
- **Step 1 — SPARQL bulk download**: Query `query.wikidata.org/sparql` for all entities that are instances of city (Q515) or subclasses, with coordinates (P625), country (P17/P297 for ISO code), and population (P1082). Paginate by country to stay under 60s timeout.
- **Step 2 — Local spatial + name join**: For each UCDB city, find Wikidata candidates with same country code and centroid within 25km. Score by fuzzy name similarity (using `rapidfuzz`). Accept matches above a confidence threshold.
- **Step 3 — Reconciliation API for residuals**: Unmatched cities go through `wikidata.reconci.link/en/api` in batches of ~50, using city name + type Q515 + country property + coordinates.
- **Step 4 — Output**: Save matched results as a lookup table (`wikidata_matches.parquet` with `city_id`, `wikidata_id`, `match_confidence`, `match_method`). Merge into `cities.parquet` during `generate_cities`.
- Add `rapidfuzz` and `SPARQLWrapper` to pipeline dependencies.

**Patterns to follow:**
- Existing pipeline script structure: `main()` function with argparse, print progress, Path-based I/O
- Data processing patterns from `src/cities/compute_populations.py`

**Test scenarios:**
- Happy path: SPARQL query returns cities for a test country (e.g., Iceland — small, well-mapped in Wikidata)
- Happy path: spatial join matches Tokyo (Q1490), Paris (Q90), New York (Q60) correctly
- Edge case: city with ambiguous name (Springfield) — resolved by coordinates, not just name
- Edge case: city not in Wikidata — `wikidata_id` is null, script continues
- Error path: SPARQL timeout — retry with smaller country batch

**Verification:**
- Script produces `wikidata_matches.parquet` with >8k matched cities
- Spot-check 20 well-known cities have correct Wikidata Q-IDs
- `cities_index.json` includes `wikidata_id` field for matched cities

---

- [ ] **Unit 6: Wire Wikidata IDs into frontend schema.org**

**Goal:** Update the city page schema.org markup to use Wikidata IDs from the city index.

**Requirements:** R4

**Dependencies:** Unit 4, Unit 5

**Files:**
- Modify: `web/app/composables/useCitiesIndex.ts` (add `wikidata_id` to `CityIndexEntry` interface)
- Modify: `web/app/pages/city/[city_id].vue` (add `sameAs` to City schema)

**Approach:**
- Add optional `wikidata_id?: string` to `CityIndexEntry`
- In the City schema.org block, conditionally build `sameAs` array: `['https://www.wikidata.org/wiki/${wikidata_id}']` when present
- Optionally derive Wikipedia URL from Wikidata ID for a second `sameAs` entry (implementation decision)

**Patterns to follow:**
- Existing optional fields in `CityIndexEntry` (population is already conditionally included)

**Test scenarios:**
- Happy path: city with wikidata_id — JSON-LD contains `sameAs` with Wikidata URL
- Edge case: city without wikidata_id — no `sameAs` in JSON-LD, no error

**Verification:**
- City page for a known city (e.g., Tokyo) includes `sameAs: ["https://www.wikidata.org/wiki/Q1490"]`

## System-Wide Impact

- **New server layer**: Creates `web/server/` directory with utils and API routes. First server-side code in the project. The city metadata API route adds one R2 fetch (cached) to the SSR critical path for city pages.
- **SSR payload change**: City pages go from ~0 bytes of SSR data to ~200 bytes per city. Negligible impact on response size, but meta tags and OG images now render correctly.
- **Two data paths for cities**: The server-side `citiesIndex.ts` utility caches the full index in-memory for lookups. The client-side `useCitiesIndex` composable continues its `server: false` pattern for the interactive UI. These are independent — the server cache has a TTL, the client fetches on demand.
- **Module swap (nuxt-og-image → @nuxtjs/seo)**: OG image behavior may change with the version bump. Needs visual verification.
- **Pipeline data schema**: Adding `wikidata_id` to `cities.parquet` and `cities_index.json` is additive — no existing consumers break.
- **Bundle size**: `@nuxtjs/seo` adds server-side sitemap/robots generation code. Client bundle impact should be minimal (schema.org renders in `<head>`, no UI components).
- **Cloudflare Workers memory**: Server-side cities index cache holds ~1.2 MB in-memory. Well within the 128MB Worker limit.

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| `@nuxtjs/seo` compatibility with Nuxt 4.4.2 | Known issue with 4.1.3 was fixed. Test during Unit 1 — if incompatible, install individual modules instead of meta-package |
| OG image breakage from nuxt-og-image v5→v6 | Visual check OG images after module swap. The City.vue and Default.vue templates use Satori, which is stable across versions |
| Wikidata SPARQL timeouts | Paginate by country. If still timing out, paginate by region or use Wikidata data dumps |
| Wikidata match quality | Accept only high-confidence matches. Unmatched cities simply won't have `sameAs` — no harm |
| R2 fetch latency on SSR critical path | Cities index is cached in-memory with TTL. First request per Worker instance has ~100-200ms overhead; subsequent requests are instant. Cold starts are infrequent on Cloudflare Workers |
| Two data paths for cities (server cache + client composable) | Intentional separation of concerns. Server cache is read-only metadata for SEO. Client composable is the interactive data layer. They use the same upstream JSON but are independently managed |

## Sources & References

- [Nuxt SEO documentation](https://nuxtseo.com)
- [Wikidata SPARQL endpoint](https://query.wikidata.org/sparql)
- [Wikidata Reconciliation API](https://wikidata.reconci.link/)
- [Google Dataset structured data](https://developers.google.com/search/docs/appearance/structured-data/dataset)
- [GHSL UCDB R2024A](https://human-settlement.emergency.copernicus.eu/ghs_ucdb_2024.php)
- [JRC Data Catalogue — UCDB](https://data.jrc.ec.europa.eu/dataset/1a338be6-7eaf-480c-9664-3a8ade88cbcd)
