export interface AIModeProduct {
  id: string;
  title: string;
  description?: string;
  price: number;
  compare_at_price?: number | null;
  currency: string;
  category: string;
  tags: string[];
  images: string[];
  in_stock: boolean;
  total_inventory: number;
  source_url?: string | null;
  score?: number | null;
  attributes: Record<string, any>;
  variants: Array<Record<string, any>>;
  highlights: string[];
}

export interface AIModeSearchPlan {
  original_query: string;
  clean_query: string;
  intent: string;
  price_min?: number | null;
  price_max?: number | null;
  sort_by?: string | null;
  attributes_filter: Record<string, any>;
  is_conversational_follow_up: boolean;
  comparison_targets: string[];
}

export interface AIModeSearchResponse {
  query: string;
  search_plan: AIModeSearchPlan;
  products: AIModeProduct[];
  total_matches: number;
  page: number;
  page_size: number;
  has_more: boolean;
  ai_summary: string;
  suggestions: string[];
  retrieval_metrics: Record<string, any>;
}

export interface AIModeChatResponse {
  conversation_id: string;
  message_id: string;
  response: string;
  intent: string;
  products: AIModeProduct[];
  comparison_matrix?: {
    products: AIModeProduct[];
    comparison_table: Array<Record<string, any>>;
    ai_summary: string;
    best_for: Record<string, string>;
    verdict: string;
  } | null;
  suggestions: string[];
  pagination?: {
    page: number;
    page_size: number;
    total_matches: number;
    has_more: boolean;
  } | null;
  search_plan?: Record<string, any> | null;
  status: string;
}

export interface AIModeKnowledgeSource {
  id: string;
  name: string;
  source_type: string;
  status: 'PENDING' | 'SYNCING' | 'READY' | 'ERROR';
  document_count: number;
  chunk_count: number;
  error_message?: string | null;
  last_synced_at?: string | null;
  config: Record<string, any>;
  created_at?: string | null;
}

export interface AIModeDeployment {
  id: string;
  workspace_id: string;
  name: string;
  public_widget_id: string;
  status: 'ACTIVE' | 'INACTIVE';
  allowed_domains: string[];
  theme_config: Record<string, any>;
  welcome_message: string;
  launcher_text: string;
  embed_code: string;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface AIModeConfig {
  workspace_id: string;
  is_enabled: boolean;
  brand_name: string;
  system_prompt: string;
  model_name: string;
  temperature: number;
  search_threshold: number;
  rerank_enabled: boolean;
  settings: Record<string, any>;
}
