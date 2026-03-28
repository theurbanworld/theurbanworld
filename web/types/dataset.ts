/**
 * Dataset configuration types
 *
 * A dataset bundles a spatial data source with its metadata,
 * available features, and content documentation path.
 */

import type { YearEpoch } from './h3'
import type { DataSource } from '../app/composables/useDataSource'

export type DatasetFeature = 'radialProfiles' | 'h3Overlay'

export interface Dataset {
  /** Unique identifier, used as route param and selection key */
  id: string
  /** Display name (e.g. "Urban World") */
  name: string
  /** Version label for display (e.g. "v1", "R2024") */
  version: string
  /** Short description for the dataset picker */
  description: string
  /** Underlying data source for boundary and population data */
  dataSource: DataSource
  /** Filename slug (underscored) for data file URLs */
  slug: string
  /** Features supported by this dataset */
  features: DatasetFeature[]
  /** Content path for the dataset documentation page */
  contentPath: string
  /** Available epoch years */
  epochs: readonly YearEpoch[]
}
