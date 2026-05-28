// ── Types ──────────────────────────────────────────────────────────────

export interface User {
  id: number;
  email: string;
  name: string;
  role: string;
}

export interface LawSearchResult {
  source: string;
  title: string;
  content: string;
  relevance_score: number;
}

export interface CaseSearchResult {
  source: string;
  title: string;
  court: string;
  date: string;
  content: string;
  relevance_score: number;
}

export interface Case {
  id: number;
  title: string;
  case_type: string;
  status: string;
  description?: string;
  plaintiff?: string;
  defendant?: string;
  court?: string;
  case_number?: string;
  created_at: string;
  updated_at: string;
  document_count?: number;
}

export interface CaseCreate {
  title: string;
  case_type: string;
  plaintiff?: string;
  defendant?: string;
  description?: string;
  court?: string;
}

export interface Document {
  id: number;
  type: string;
  title: string;
  content: string;
  status: string;
  version: number;
  case_id?: number;
  template_id?: number;
  ai_metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Template {
  id: number;
  name: string;
  type: string;
  description?: string;
  structure?: Record<string, unknown>;
  ai_prompt?: string;
  format_rules?: Record<string, unknown>;
  variables?: Record<string, unknown>[];
  is_public: boolean;
  created_at: string;
  updated_at: string;
  sections_preview?: string[];
  field_count?: number;
  supports_structured?: boolean;
  category?: string;
  generation_mode?: string;
  word_export_mode?: string;
}

export interface SearchResults {
  query: string;
  laws: LawSearchResult[];
  cases: CaseSearchResult[];
  total: number;
  sources_used: string[];
}

export type OcrStatus = 'pending' | 'processing' | 'success' | 'failed';

export interface EvidenceItem {
  id: number;
  case_id: number;
  type: string;
  title: string;
  file_path: string | null;
  ocr_text: string | null;
  ocr_status?: OcrStatus;
  ocr_message?: string | null;
  tags: string[] | null;
  sort_order: number;
  analysis: string | null;
  has_file: boolean;
  vault_archived?: boolean | null;
  created_at: string;
}

export type LLMProfileRole = 'text_primary' | 'vision_ocr' | 'vision' | 'other';

export interface LLMSetting {
  id: number;
  name: string;
  base_url: string;
  api_key_masked: string;
  model_name: string;
  max_tokens: number;
  is_default: boolean;
  created_at: string;
  updated_at: string;
  profile_role?: LLMProfileRole;
}

export interface LLMRuntimeSummary {
  text: ActiveLLM;
  vision: ActiveLLM;
  vision_ready: boolean;
}

export interface ConnectivityTestResult {
  success: boolean;
  message: string;
  model: string;
  latency_ms: number;
}

export interface ActiveLLM {
  config_id: number | null;
  config_name: string;
  model_name: string;
  max_tokens: number;
  base_url: string;
  source: 'database' | 'env';
  has_api_key: boolean;
}

export interface ResearchReport {
  id: number;
  query: string;
  report: string;
  sources_used: string[];
  case_id: number | null;
  created_at: string;
  conclusion_level?: string | null;
}

export interface VectorStats {
  cases_count: number;
  statutes_count: number;
  knowledge_count: number;
  connected: boolean;
}

export interface ContractItem {
  id: number;
  case_id: number | null;
  owner_id: number;
  title: string;
  file_path: string | null;
  file_type: string | null;
  parsed_text: string | null;
  clauses: ContractClause[] | null;
  review_report: string | null;
  risk_items: ContractRiskItem[] | null;
  risk_score: number | null;
  status: string;
  has_file: boolean;
  ocr_status?: OcrStatus;
  ocr_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ContractClause {
  type: string;
  text: string;
  position: number;
}

export interface ContractRiskItem {
  dimension: string;
  level: string;
  clause: string;
  issue: string;
  suggestion: string;
}

export interface ChainAnalysisResult {
  chain_report: string;
  completeness_score: number | null;
  chain_status: string;
  missing_evidence: { type: string; purpose: string; urgency: string }[];
  timeline?: { date: string; event: string; evidence_id?: number | null; confidence?: string }[];
  credibility?: { score: number; needs_human_review: boolean; reason: string };
}

export interface KnowledgeItem {
  id: number;
  title: string;
  content: string;
  source: string | null;
  tags: string[] | null;
  embedding_id: string | null;
  owner_id: number | null;
  team_id: number | null;
  created_at: string;
}

export interface KnowledgeStats {
  total: number;
  tags: string[];
}

export interface CrawlSeed {
  id: string;
  name: string;
  keywords: string[];
  tags: string[];
  category: string;
  source_id?: string;
}

export interface CrawlSource {
  id: string;
  name: string;
  provider: string;
  website?: string | null;
  description?: string | null;
  search_keywords?: string[];
  max_items_per_keyword?: number | null;
}

export interface CrawlSeedsResponse {
  description?: string | null;
  sources: CrawlSource[];
  seeds: CrawlSeed[];
}

export interface CrawlLawResult {
  seed_id?: string | null;
  keyword: string;
  title: string;
  source_id?: string | null;
  bbbs?: string | null;
  status: string;
  knowledge_items: number;
  statute_vectors: number;
  message: string;
}

export interface CrawlRunResponse {
  total: number;
  success: number;
  failed: number;
  skipped?: number;
  items: CrawlLawResult[];
}

export interface CrawlScheduleStatus {
  enabled: boolean;
  weekday: number;
  hour: number;
  minute: number;
  last_run_at?: string | null;
  last_run_status?: string | null;
  last_run_summary?: Record<string, unknown> | null;
  next_run_at?: string | null;
  running?: boolean;
}

export interface ExternalApiConfig {
  id: number;
  name: string;
  description: string;
  base_url: string;
  auth_type: string;
  auth_token_masked: string;
  auth_header_name: string;
  auth_username: string;
  auth_password_masked: string;
  custom_headers: string;
  search_law_path: string;
  search_law_method: string;
  search_case_path: string;
  search_case_method: string;
  get_provision_path: string;
  get_provision_method: string;
  health_check_path: string;
  response_mapping: string;
  request_template: string;
  is_enabled: boolean;
  category: string;
  created_at: string;
  updated_at: string;
}

export interface ExternalApiPreset {
  key: string;
  name: string;
  category: string;
  description: string;
  base_url: string;
  auth_type: string;
  search_law_path: string;
  search_law_method: string;
  search_case_path: string;
  search_case_method: string;
  get_provision_path: string;
  get_provision_method: string;
  health_check_path: string;
  response_mapping: string;
  request_template: string;
}

export interface AppConfigItem {
  id: number;
  config_key: string;
  config_value: string;
  description: string;
  category: string;
  created_at: string;
  updated_at: string;
}

export interface LawVerifyResult {
  law_name: string;
  article_number: string;
  quoted_text: string;
  actual_text: string;
  overall_consistent: boolean;
  sources: Record<string, unknown>[];
  recommendation: string;
}
