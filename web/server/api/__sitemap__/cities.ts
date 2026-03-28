/**
 * Sitemap source for city URLs.
 *
 * Returns all city routes for the sitemap module.
 * Uses the shared citiesIndex utility for cached R2 data.
 */
import { defineSitemapEventHandler } from '#imports'

export default defineSitemapEventHandler(async () => {
  const cities = await getAllCities()

  return cities.map(city => ({
    loc: `/city/${city.id}`,
    changefreq: 'monthly' as const,
    priority: 0.6
  }))
})
