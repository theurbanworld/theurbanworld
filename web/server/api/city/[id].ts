/**
 * City metadata API route.
 *
 * Returns a single city's metadata for SSR use.
 * The cities index is cached server-side (see server/utils/citiesIndex.ts).
 */

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')
  if (!id) {
    throw createError({ statusCode: 400, statusMessage: 'Missing city id' })
  }

  const city = await getCityById(id)
  if (!city) {
    throw createError({ statusCode: 404, statusMessage: 'City not found' })
  }

  return city
})
