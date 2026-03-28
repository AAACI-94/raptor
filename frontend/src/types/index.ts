// Domain types mirroring backend Pydantic models

export interface Project {
  id: string;
  title: string;
  topic_description: string;
  author_context: string;
  venue_profile_id: string | null;
  status: ProjectStatus;
  nda_config: NDAConfig | null;
  revision_cycles: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectSummary {
  id: string;
  title: string;
  venue_profile_id: string | null;
  status: ProjectStatus;
  revision_cycles: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  title: string;
  topic_description?: string;
  author_context?: string;
  venue_profile_id?: string;
}

export interface NDAConfig {
  sensitivity_level: string;
  mode: string;
  blocked_terms: string[];
  generalization_rules: Record<string, string>[];
}

export type ProjectStatus =
  | 'TOPIC_SELECTED' | 'RESEARCHING' | 'RESEARCH_COMPLETE'
  | 'STRUCTURING' | 'STRUCTURE_COMPLETE'
  | 'DRAFTING' | 'DRAFT_COMPLETE'
  | 'REVIEWING' | 'REVISION_REQUESTED' | 'REVIEW_PASSED'
  | 'PRODUCING' | 'PRODUCTION_COMPLETE' | 'PUBLISHED';

export interface VenueProfile {
  id: string;
  venue_type: string;
  display_name: string;
  description: string;
  profile_data: VenueProfileData;
  is_custom: boolean;
  created_at: string;
  updated_at: string;
}

export interface VenueProfileData {
  structural_template: StructuralTemplate;
  quality_rubric: QualityRubric;
  tone_profile: ToneProfile;
  citation_format: CitationFormat;
  review_simulation_persona: ReviewPersona;
}

export interface StructuralTemplate {
  required_sections: SectionTemplate[];
  optional_sections: SectionTemplate[];
  section_order_constraints: string;
}

export interface SectionTemplate {
  name: string;
  min_words: number | null;
  max_words: number | null;
  required: boolean;
}

export interface QualityRubric {
  dimensions: RubricDimension[];
  passing_threshold: number;
  scale_min: number;
  scale_max: number;
}

export interface RubricDimension {
  name: string;
  description: string;
  weight: number;
  min_passing: number;
}

export interface ToneProfile {
  register: string;
  person: string;
  voice: string;
  jargon_level: string;
}

export interface CitationFormat {
  style: string;
  format_spec: string;
  minimum_references: number;
}

export interface ReviewPersona {
  description: string;
  common_feedback_patterns: string[];
}

export interface ArtifactSummary {
  id: string;
  artifact_type: string;
  source_agent: string;
  version: number;
  status: string;
  created_at: string;
}

export interface PipelineStatus {
  project_id: string;
  status: ProjectStatus;
  revision_cycles: number;
  max_revision_cycles: number;
  current_agent: string | null;
  artifacts: ArtifactSummary[];
}

export interface PipelineEvent {
  event: string;
  agent?: string;
  stage?: string;
  data?: {
    message?: string;
    progress_pct?: number;
    section_count?: number;
    estimated_seconds?: number;
  };
  artifact_id?: string;
  error?: string;
}

export interface CostSummary {
  project_id: string | null;
  breakdown: CostBreakdownEntry[];
  totals: {
    input_tokens: number;
    output_tokens: number;
    cost_usd: number;
  };
}

export interface CostBreakdownEntry {
  agent: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  calls: number;
}

export interface QualityMetrics {
  project_id: string;
  dimensions: Record<string, {
    avg_score: number;
    min_score: number;
    max_score: number;
    evaluations: number;
  }>;
}

export interface TraceSummary {
  project_id: string;
  traces: Record<string, TraceEntry[]>;
  total_decisions: number;
}

export interface TraceEntry {
  decision: string;
  rationale: string;
  confidence: number;
  timestamp: string;
}
