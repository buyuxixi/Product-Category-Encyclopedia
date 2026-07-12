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
  source_count: number
}

export interface SearchResult {
  kind: 'category' | 'section' | 'hotlink' | 'trend' | 'source'
  category_code: string
  title: string
  snippet: string
  section_key: string | null
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

export interface HotLink {
  id: number
  category_code: string
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
  category_code: string
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
