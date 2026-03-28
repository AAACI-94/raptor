// Version is now fetched from the backend /api/health endpoint.
// This constant is a fallback only, displayed while the API call is in flight.
export const APP_VERSION_FALLBACK = '1.2.2';

export interface AgentInfo {
  name: string;
  role: string;
  description: string;
  model: string;
  color: string;
}

export const agents: AgentInfo[] = [
  { name: 'Research Strategist', role: 'research_strategist', description: 'Produces research plans with grounded sources via agentic RAG. Classifies sources as primary/secondary/tertiary. Applies two-source rule and bias detection per journalistic standards.', model: 'Sonnet', color: '#0c93e9' },
  { name: 'Structure Architect', role: 'structure_architect', description: 'Generates publication-appropriate outlines with section-level acceptance criteria and word count targets.', model: 'Sonnet', color: '#8b5cf6' },
  { name: 'Domain Writer', role: 'domain_writer', description: 'Drafts each section individually with Toulmin-structured arguments, confidence flags, source filtering per section, and cross-project learned patterns.', model: 'Sonnet', color: '#10b981' },
  { name: 'Visual Architect', role: 'visual_architect', description: 'Generates professional Mermaid diagrams. 12+ diagram types with data-pattern-matched selection framework.', model: 'Sonnet', color: '#f59e0b' },
  { name: 'Critical Reviewer', role: 'critical_reviewer', description: 'Evaluates against publication-specific rubrics with journalistic verification audit, Toulmin completeness check, logical fallacy detection, and Mill\'s Methods for causal claims.', model: 'Opus', color: '#ef4444' },
  { name: 'Production Agent', role: 'production_agent', description: 'Deterministic document assembly. Formats bibliography, generates submission checklist. Zero content loss guaranteed.', model: 'Sonnet', color: '#06b6d4' },
  { name: 'Observatory', role: 'observatory', description: 'Meta-agent: traces decisions, quality metrics, cost tracking, improvement insights, diagnostic events.', model: 'Haiku', color: '#64748b' },
];

export const selfHealingComponents = [
  { name: 'Sentinel', description: 'Wraps every agent execution. Detects failures, timeouts, quality degradation, cost anomalies, and parse errors before they cascade.', icon: 'Shield' },
  { name: 'Diagnostic Agent', description: 'Classifies errors using heuristic rules (80% of cases) and Ollama LLM (ambiguous cases). Produces root cause, severity, and recommended actions.', icon: 'Search' },
  { name: 'Remediation Engine', description: 'Executes automatic fixes: retry with backoff, JSON repair, provider switching, prompt simplification, feedback injection. Max 3 attempts before user escalation.', icon: 'Wrench' },
];

export const qualityStandards = [
  { name: 'Journalistic Verification (SPJ/Reuters)', items: ['Two-source rule for factual claims', 'Source transparency (show HOW you know)', 'Primary vs secondary source classification', 'Hedging for uncertainty', 'Conflict of interest detection'] },
  { name: 'Logical Rigor (Toulmin Model)', items: ['Claim + Data + Warrant + Qualifier + Rebuttal', 'Missing warrants flagged (most common weakness)', 'Counterarguments steel-manned, not straw-manned', 'Scope consistency throughout paper'] },
  { name: 'Fallacy Detection (13 types)', items: ['Causal: post hoc, correlation/causation, single cause, wrong direction', 'Argumentative: appeal to authority, hasty generalization, false dichotomy, straw man', 'Evidence: cherry-picking, survivorship bias, ecological fallacy, circular reasoning, moving goalposts'] },
  { name: 'Causal Inference (Mill\'s Methods)', items: ['Method of difference (comparison group?)', 'Confounding variables addressed?', 'Causal mechanism explained?', 'Dose-response relationship checked?', 'Temporal precedence established?', 'Alternative explanations considered?'] },
];

export const pipelineStages = [
  { name: 'Topic & Target', description: 'Author provides topic, selects publication target, configures NDA settings' },
  { name: 'Research', description: 'Research Strategist builds a grounded research plan with sources classified by tier and bias' },
  { name: 'Structure', description: 'Structure Architect generates a publication-appropriate outline with section acceptance criteria' },
  { name: 'Drafting', description: 'Domain Writer drafts each section individually with Toulmin arguments and filtered sources' },
  { name: 'Figures', description: 'Visual Architect generates professional diagrams matched to data patterns in the draft' },
  { name: 'Review', description: 'Critical Reviewer evaluates against rubric plus journalistic verification and logical rigor audits' },
  { name: 'Production', description: 'Production Agent formats the document deterministically, generates bibliography and submission checklist' },
];

export const publicationTargetTypes = [
  { name: 'Practitioner Repository', example: 'SANS Reading Room', focus: 'Practitioner utility, actionable recommendations' },
  { name: 'Academic Conference', example: 'IEEE S&P, ACM CCS, USENIX', focus: 'Novelty, rigor, formal evaluation' },
  { name: 'Industry Publication', example: 'Dark Reading', focus: 'Accessibility, hook-driven, broad appeal' },
  { name: 'Industry Research', example: 'CSA Research', focus: 'Framework-oriented, governance focus' },
  { name: 'Self-Published', example: 'LinkedIn Article', focus: 'Thought leadership, personal voice' },
];

export const contextEngineering = [
  { name: 'Source Filtering', description: 'Writer receives only assigned sources per section (not entire corpus), reducing input tokens by 60%+' },
  { name: 'Full Draft Review', description: 'Reviewer sees condensed prose (not truncated JSON), enabling evaluation of the complete paper' },
  { name: 'Cross-Project Learning', description: 'Recurring revision patterns from past reviews auto-inject into Writer prompts for future projects' },
  { name: 'Reflection on Ollama', description: 'All self-reflection checkpoints route to local Ollama (free, fast) regardless of primary provider' },
  { name: 'Minimal Viable Context', description: 'Each agent receives only the context needed for its role, not the full project state' },
];

export const techStack = [
  { name: 'Backend', tech: 'Python 3.11+ / FastAPI' },
  { name: 'Frontend', tech: 'React 18 / TypeScript / Tailwind CSS / Recharts' },
  { name: 'Database', tech: 'SQLite with WAL mode (13 tables)' },
  { name: 'AI Providers', tech: 'Claude CLI (keychain auth) + Ollama (qwen3.5 local)' },
  { name: 'Observability', tech: 'OpenTelemetry GenAI conventions + Jaeger' },
  { name: 'Diagrams', tech: 'Mermaid.js (bundled, 12+ diagram types, professional theme)' },
  { name: 'Containerization', tech: 'Docker Compose (API + Frontend + Jaeger)' },
  { name: 'Self-Healing', tech: 'Sentinel + Diagnostic Agent + Remediation Engine' },
];
