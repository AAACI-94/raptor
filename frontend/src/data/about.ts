export const APP_VERSION = '1.1.0';

export interface AgentInfo {
  name: string;
  role: string;
  description: string;
  model: string;
  color: string;
}

export const agents: AgentInfo[] = [
  { name: 'Research Strategist', role: 'research_strategist', description: 'Produces research plans with grounded sources via agentic RAG. Plan-Retrieve-Evaluate-Reflect cycle.', model: 'Sonnet', color: '#0c93e9' },
  { name: 'Structure Architect', role: 'structure_architect', description: 'Generates venue-appropriate outlines with section-level acceptance criteria.', model: 'Sonnet', color: '#8b5cf6' },
  { name: 'Domain Writer', role: 'domain_writer', description: 'Drafts each section individually, grounded in research. Confidence flags and NDA annotations.', model: 'Sonnet', color: '#10b981' },
  { name: 'Visual Architect', role: 'visual_architect', description: 'Generates professional Mermaid diagrams. 12 types with venue-adaptive selection.', model: 'Sonnet', color: '#f59e0b' },
  { name: 'Critical Reviewer', role: 'critical_reviewer', description: 'Evaluates against venue-specific rubrics. Can reject and trigger revision loops.', model: 'Opus', color: '#ef4444' },
  { name: 'Production Agent', role: 'production_agent', description: 'Deterministic document assembly. Formats bibliography, generates submission checklist. Zero content loss.', model: 'Sonnet', color: '#06b6d4' },
  { name: 'Observatory', role: 'observatory', description: 'Meta-agent: traces decisions, quality metrics, cost tracking, improvement insights.', model: 'Haiku', color: '#64748b' },
];

export const selfHealingComponents = [
  { name: 'Sentinel', description: 'Wraps every agent execution. Detects failures, timeouts, quality degradation, cost anomalies, and parse errors before they cascade.', icon: 'Shield' },
  { name: 'Diagnostic Agent', description: 'Classifies errors using heuristic rules (80% of cases) and Ollama LLM (ambiguous cases). Produces root cause, severity, and recommended actions.', icon: 'Search' },
  { name: 'Remediation Engine', description: 'Executes automatic fixes: retry with backoff, JSON repair, provider switching, prompt simplification, feedback injection. Max 3 attempts before user escalation.', icon: 'Wrench' },
];

export const pipelineStages = [
  { name: 'Topic & Venue', description: 'Author provides topic, selects target venue, configures NDA settings' },
  { name: 'Research', description: 'Research Strategist builds a grounded research plan with sources and contribution claim' },
  { name: 'Structure', description: 'Structure Architect generates a venue-appropriate outline with section acceptance criteria' },
  { name: 'Drafting', description: 'Domain Writer drafts each section individually against the outline spec' },
  { name: 'Figures', description: 'Visual Architect generates professional diagrams matched to data patterns in the draft' },
  { name: 'Review', description: 'Critical Reviewer evaluates against venue rubric. Can reject and trigger revision loops (max 3)' },
  { name: 'Production', description: 'Production Agent formats the document, generates bibliography and submission checklist' },
];

export const venueTypes = [
  { name: 'Practitioner Repository', example: 'SANS Reading Room', focus: 'Practitioner utility, actionable recommendations' },
  { name: 'Academic Conference', example: 'IEEE S&P, ACM CCS, USENIX', focus: 'Novelty, rigor, formal evaluation' },
  { name: 'Industry Publication', example: 'Dark Reading', focus: 'Accessibility, hook-driven, broad appeal' },
  { name: 'Self-Published', example: 'LinkedIn Article', focus: 'Thought leadership, personal voice' },
];

export const techStack = [
  { name: 'Backend', tech: 'Python 3.11+ / FastAPI' },
  { name: 'Frontend', tech: 'React 18 / TypeScript / Tailwind CSS / Recharts' },
  { name: 'Database', tech: 'SQLite with WAL mode (12 tables)' },
  { name: 'AI Providers', tech: 'Claude CLI (keychain auth) + Ollama (qwen3.5 local)' },
  { name: 'Observability', tech: 'OpenTelemetry GenAI conventions + Jaeger' },
  { name: 'Diagrams', tech: 'Mermaid.js (bundled, 12 diagram types)' },
  { name: 'Containerization', tech: 'Docker Compose (API + Frontend + Jaeger)' },
];
