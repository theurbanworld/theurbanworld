import Fuse from 'fuse.js'
import type { CityIndexEntry } from './useCitiesIndex'

interface CitySearchResult {
  city: CityIndexEntry
  score: number
}

export function useCitySearch() {
  const { allCities } = useCitiesIndex()

  const searchTerm = ref('')

  const fuse = computed(() => {
    if (!allCities.value.length) return null
    return new Fuse(allCities.value, {
      keys: [
        { name: 'name', weight: 0.7 },
        { name: 'country', weight: 0.3 }
      ],
      threshold: 0.4,
      includeScore: true
    })
  })

  const results = computed<CitySearchResult[]>(() => {
    const query = searchTerm.value.trim()
    if (!fuse.value || query.length < 2) return []

    const matches = fuse.value.search(query, { limit: 50 })

    return matches
      .map(match => ({
        city: match.item,
        score: match.score ?? 1
      }))
      .sort((a, b) => {
        const scoreDiff = a.score - b.score
        if (Math.abs(scoreDiff) > 0.01) return scoreDiff
        return b.city.population - a.city.population
      })
      .slice(0, 10)
  })

  return {
    searchTerm,
    results
  }
}
