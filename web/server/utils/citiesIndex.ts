/**
 * Server-side cities index with in-memory caching.
 *
 * Fetches cities_index.json from R2 once, caches it in a Map
 * for O(1) lookups. Shared by the city metadata API route
 * and the sitemap endpoint.
 */

export interface CityIndexEntry {
  id: string
  name: string
  country: string
  country_code: string
  centroid: [number, number]
  bbox: [number, number, number, number]
  population?: number
  wikidata_id?: string
}

const CITIES_INDEX_URL = 'https://data.theurban.world/data/cities_index.json'
const CACHE_TTL_MS = 60 * 60 * 1000 // 1 hour

let cachedMap: Map<string, CityIndexEntry> | null = null
let cachedList: CityIndexEntry[] | null = null
let cacheTimestamp = 0

function getDataUrl(): string {
  const config = useRuntimeConfig()
  const r2BaseUrl = config.public.r2BaseUrl
  if (r2BaseUrl) {
    return `${r2BaseUrl}/data/cities_index.json`
  }
  return CITIES_INDEX_URL
}

async function ensureCache(): Promise<void> {
  const now = Date.now()
  if (cachedMap && (now - cacheTimestamp) < CACHE_TTL_MS) {
    return
  }

  const url = getDataUrl()
  const cities = await $fetch<CityIndexEntry[]>(url)

  cachedList = cities
  cachedMap = new Map(cities.map(city => [city.id, city]))
  cacheTimestamp = now
}

export async function getCityById(id: string): Promise<CityIndexEntry | undefined> {
  await ensureCache()
  return cachedMap!.get(id)
}

export async function getAllCities(): Promise<CityIndexEntry[]> {
  await ensureCache()
  return cachedList!
}
