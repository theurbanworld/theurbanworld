/**
 * Data source toggle between GHSL Grid 1km and GHSL H3 R8.
 *
 * Controls which population dataset is used for:
 * - City boundary outlines (PMTiles)
 * - City population statistics (JSON)
 */

export type DataSource = 'h3-r8' | 'grid-1km'

const dataSource = ref<DataSource>('h3-r8')

export function useDataSource() {
  function setDataSource(source: DataSource) {
    dataSource.value = source
  }

  function toggleDataSource() {
    dataSource.value = dataSource.value === 'h3-r8' ? 'grid-1km' : 'h3-r8'
  }

  /** Filename slug: 'h3_r8' or 'grid_1km' */
  const sourceSlug = computed(() => dataSource.value.replace('-', '_'))

  return {
    dataSource: readonly(dataSource),
    sourceSlug,
    setDataSource,
    toggleDataSource
  }
}
