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
  parent_code: string | null
  children: Array<{ id: number; code: string; name: string; status: string }>
  updated_at: string
}

export interface Evidence {
  id: number
  source_type: string
  source_id: number
  locator: string | null
  source: {
    title?: string
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
  title_zh: string | null
  url: string
  description: string
  description_zh: string | null
  hotness_score: number | null
  is_hot: boolean
  collected_at: string
}

export interface ListingSuggestionItem {
  evidence_ids: number[]
  keyword?: string
  headline?: string
  pain_point?: string
  reason?: string
  suggestion?: string
}

export interface ListingSuggestionPreview {
  product_id: number
  basis: 'cross_platform_category_insights'
  keyword_directions: ListingSuggestionItem[]
  selling_points: ListingSuggestionItem[]
  improvement_points: ListingSuggestionItem[]
  limitations: string[]
  evidence: Array<{
    id: number
    platform: string
    title: string
    url: string
  }>
}

export interface TrendSignal {
  id: number
  category_code: string
  section_key: string
  signal_type: string
  platform: string
  keyword: string
  title: string
  title_zh: string | null
  metric_value: number | null
  metric_unit: string | null
  trend_direction: string | null
  summary: string
  summary_zh: string | null
  collected_at: string
}

export interface ProductDiscovery {
  id: number
  scan_id: number
  product_name: string
  category_code: string | null
  opportunity_type: string
  opportunity_score: number | null
  reasoning: string
  market_signals: Record<string, unknown>
  keywords: string[]
  source_links: Array<{ title: string; url: string; platform: string }>
  status: string
  user_note: string | null
  created_at: string
}

export interface AgentMessage {
  id: number
  role: string
  content: string
  created_at: string
}

export interface AgentScan {
  id: number
  scan_type: string
  category_code: string | null
  topic: string | null
  status: string
  triggered_by: string
  is_pinned: boolean
  report: {
    summary?: string
    market_overview?: Record<string, unknown>
    recommendations?: string[]
    insight_mode?: string
    user_notice?: string
    topic_query_terms?: string[]
  }
  stats: Record<string, unknown>
  error_message: string | null
  created_at: string
  completed_at: string | null
  discoveries?: ProductDiscovery[]
  messages?: AgentMessage[]
}
