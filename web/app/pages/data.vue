<script setup lang="ts">
definePageMeta({ layout: 'content' })

useSeoMeta({
  title: 'Data — The Urban World',
  description: 'Data sources powering The Urban World observatory.'
})

useSchemaOrg([
  {
    '@type': 'Dataset',
    'name': 'The Urban World — Global City Population Data',
    'description': 'Population, density, and growth data for 13,000+ urban areas worldwide, derived from the European Commission\'s Global Human Settlement Layer (GHSL) Urban Centre Database. Includes H3 hexagonal grid and 1 km raster-based population estimates from 1975 to 2025.',
    'url': 'https://theurban.world/data',
    'license': 'https://creativecommons.org/licenses/by-sa/4.0/',
    'temporalCoverage': '1975/2025',
    'spatialCoverage': {
      '@type': 'Place',
      'name': 'Global'
    },
    'creator': {
      '@type': 'Person',
      'name': 'Jonathan Pichot',
      'url': 'https://pichot.us'
    },
    'isBasedOn': {
      '@type': 'Dataset',
      'name': 'GHS Urban Centre Database R2024A',
      'url': 'https://data.jrc.ec.europa.eu/dataset/1a338be6-7eaf-480c-9664-3a8ade88cbcd',
      'creator': {
        '@type': 'Organization',
        'name': 'European Commission Joint Research Centre',
        'url': 'https://ghsl.jrc.ec.europa.eu/'
      },
      'license': 'https://creativecommons.org/licenses/by/4.0/'
    },
    'keywords': [
      'urbanization',
      'population density',
      'cities',
      'GHSL',
      'urban growth',
      'H3 hexagonal grid'
    ]
  }
])

const { data: sections } = await useAsyncData('data-sections', () =>
  queryCollection('data').order('stem', 'ASC').all()
)
</script>

<template>
  <div>
    <template v-if="sections">
      <ContentRenderer
        v-for="section in sections"
        :key="section.stem"
        :value="section"
        class="prose prose-forest dark:prose-invert max-w-none"
      />
    </template>
  </div>
</template>
