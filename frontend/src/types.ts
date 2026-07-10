export type Role = 'admin' | 'data' | 'researcher' | 'reviewer'

export interface CategorySummary {
  id: number
  code: string
  name: string
  description: string
  aliases: string[]
  included_items: string[]
  excluded_items: string[]
  status: string
  workflow_status: string
  parent_code: string | null
  children: Array<{ id: number; code: string; name: string; workflow_status: string }>
  updated_at: string
}

export interface Evidence {
  id: number
  source_type: string
  source_id: number
  locator: string | null
  source: {
    title?: string
    asin?: string
    brand?: string
    marketplace?: string
    scraped_at?: string
    collected_at?: string
    published_at?: string | null
    source_type?: string
    url?: string | null
  } | null
}

export interface EncyclopediaSection {
  id: number
  section_key: string
  title: string
  content: string
  generation_mode: string
  locked_by_human: boolean
  review_status: string
  updated_by: string | null
  updated_at: string
  evidence: Evidence[]
}

export interface CategoryDetail extends CategorySummary {
  sections: EncyclopediaSection[]
  listing_count: number
  source_count: number
}

export interface Listing {
  id: number
  asin: string
  title: string
  brand: string
  rating_value: number | null
  rating_count: number | null
  current_price: number | null
  currency: string | null
  bsr_rank: number | null
  bsr_category: string | null
  scraped_at: string
  source_url: string | null
}

export interface ImportJob {
  id: number
  status: string
  source_path: string
  requested_directories: string[]
  total_count: number
  inserted_count: number
  duplicate_count: number
  failed_count: number
  skipped_count: number
  errors: Array<{ file: string; reason: string }>
  created_by: string
  created_at: string
}

export interface ImportCatalogItem {
  code: string
  name: string
  directories: string[]
  file_count: number
  json_directory_count: number
}

export interface VersionRecord {
  id: number
  category_id: number
  category_code: string
  category_name: string
  version_number: number
  status: string
  created_by: string
  reviewed_by: string | null
  review_comment: string | null
  created_at: string
  reviewed_at: string | null
  published_at: string | null
}

export interface VersionDetail extends VersionRecord {
  content_snapshot: {
    sections: Array<{
      section_key: string
      title: string
      content: string
      evidence: Array<{ source_type: string; source_id: number; locator: string | null }>
    }>
  }
}

export interface VersionDiff {
  version_id: number
  previous_version_id: number | null
  changes: Array<{ section_key: string; title: string; before: string; after: string }>
}

export interface DraftSuggestion {
  section_key: string
  title: string
  content: string
  evidence_listing_ids: number[]
  evidence_source_ids: number[]
  missing_evidence: boolean
  selected?: boolean
}

export interface SourceMaterial {
  id: number
  source_type: string
  title: string
  url: string | null
  content: string
  published_at: string | null
  collected_at: string
  created_by: string
}

export interface SearchResult {
  kind: 'category' | 'section' | 'listing' | 'source'
  category_code: string
  title: string
  snippet: string
  section_key: string | null
}

export interface HotLink {
  id: number
  section_key: string
  link_type: string
  platform: string
  title: string
  url: string
  description: string
  hotness_score: number | null
  is_hot: boolean
  collected_at: string
}

export interface TrendSignal {
  id: number
  section_key: string
  signal_type: string
  platform: string
  keyword: string
  title: string
  metric_value: number | null
  metric_unit: string | null
  trend_direction: string | null
  summary: string
  collected_at: string
}
