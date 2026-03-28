/**
 * Dataset selection state management
 *
 * Provides the primary API for selecting and querying the active dataset.
 * Wraps useDataSource internally — existing consumers of useDataSource
 * (useMap, useCityPopulations) continue to work unchanged.
 */

import { YEAR_EPOCHS } from '../../types/h3'
import type { Dataset, DatasetFeature } from '../../types/dataset'

export const DATASETS: Dataset[] = [
  {
    id: 'urban-world-v1',
    name: 'Urban World',
    version: 'v1',
    dataSource: 'h3-r8',
    slug: 'h3_r8',
    features: ['radialProfiles', 'h3Overlay'],
    contentPath: '/data/urban-world-v1',
    epochs: YEAR_EPOCHS
  },
  {
    id: 'ghsl-r2024',
    name: 'GHSL',
    version: 'R2024',
    dataSource: 'grid-1km',
    slug: 'grid_1km',
    features: [],
    contentPath: '/data/ghsl-r2024',
    epochs: YEAR_EPOCHS
  }
]

const DEFAULT_DATASET_ID = 'urban-world-v1'

// Singleton reactive state
const activeDatasetId = ref<string>(DEFAULT_DATASET_ID)

export function useDataset() {
  const { setDataSource } = useDataSource()

  /** The full config object for the active dataset */
  const activeDataset = computed(() => {
    return DATASETS.find(d => d.id === activeDatasetId.value)!
  })

  /** Display label: "Name Version" (e.g. "Urban World v1") */
  const activeDatasetLabel = computed(() => {
    const d = activeDataset.value
    return `${d.name} ${d.version}`
  })

  /**
   * Switch to a different dataset by ID.
   * Ignores unknown IDs.
   */
  function setDataset(id: string) {
    const dataset = DATASETS.find(d => d.id === id)
    if (!dataset) return
    activeDatasetId.value = id
    setDataSource(dataset.dataSource)
  }

  /**
   * Check if the active dataset supports a given feature
   */
  function hasFeature(feature: DatasetFeature): boolean {
    return activeDataset.value.features.includes(feature)
  }

  /** Reactive computed version of hasFeature for template use */
  const hasFeatureComputed = (feature: DatasetFeature) => {
    return computed(() => activeDataset.value.features.includes(feature))
  }

  return {
    /** Active dataset ID (readonly) */
    activeDatasetId: readonly(activeDatasetId),
    /** Full config for the active dataset */
    activeDataset,
    /** Display label for the active dataset */
    activeDatasetLabel,
    /** All available datasets */
    datasets: DATASETS,
    /** Switch to a dataset by ID */
    setDataset,
    /** Check if active dataset supports a feature (imperative) */
    hasFeature,
    /** Check if active dataset supports a feature (reactive computed) */
    hasFeatureComputed
  }
}
