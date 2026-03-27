export interface ChangelogItem {
  title: string;
  badge?: 'pipeline' | 'agents' | 'ui' | 'observatory' | 'healing' | 'api' | 'infra' | 'quality' | 'library' | 'context';
  description?: string;
}

export interface ChangelogEntry {
  version: string;
  date: string;
  summary: string;
  added?: (string | ChangelogItem)[];
  changed?: (string | ChangelogItem)[];
  fixed?: (string | ChangelogItem)[];
}

export const changelog: ChangelogEntry[] = [
  {
    version: '1.2.0',
    date: '2026-03-26',
    summary: 'Research Library, Publication Targets rename, journalistic standards, and context engineering',
    added: [
      { title: 'Research Library', badge: 'library', description: 'Searchable, filterable library of all research projects with tags, categories, starring, and quality/cost metadata' },
      { title: 'Auto-tagging from research output', badge: 'library', description: 'Research Strategist output auto-generates tags from contribution claims, source types, and publication target' },
      { title: 'Library search API', badge: 'api', description: 'Full-text search across titles, topics, tags, abstracts with filtering by publication target, category, status, starred' },
      { title: 'Journalistic verification standards', badge: 'quality', description: 'Two-source rule, source transparency, primary/secondary classification, hedging, conflict-of-interest detection' },
      { title: 'Logical rigor framework', badge: 'quality', description: 'Toulmin model (claim+data+warrant+qualifier+rebuttal), 13 logical fallacy detectors, Mill\'s Methods for causal claims' },
      { title: 'Argumentative rigor rubric dimension', badge: 'quality', description: 'New quality dimension across all publication targets: evaluates logical coherence, fallacy absence, causal validity' },
      { title: 'Context engineering: source filtering', badge: 'context', description: 'Writer receives only assigned sources per section, reducing input tokens by 60%+' },
      { title: 'Context engineering: full draft review', badge: 'context', description: 'Reviewer receives condensed prose format instead of truncated JSON, seeing the complete paper' },
      { title: 'Context engineering: cross-project learning', badge: 'context', description: 'Recurring revision patterns from past reviews auto-inject into Writer prompts for new projects' },
      { title: 'Citation provenance warning', badge: 'quality', description: 'All LLM-generated sources marked as unverified; authors warned to verify before submission' },
      { title: 'Source tier classification', badge: 'quality', description: 'Research Strategist classifies sources as primary/secondary/tertiary per journalistic standards' },
    ],
    changed: [
      { title: '"Venue" renamed to "Publication Target"', badge: 'ui', description: 'All user-facing labels, nav items, prompts, and API routes updated. /api/publications is now primary; /api/venues kept as alias' },
      { title: 'Reviewer prompt expanded with rigor audits', badge: 'agents', description: 'Critical Reviewer now applies journalistic verification audit + logical rigor audit + causal inference standards on every review' },
      { title: 'Writer prompt includes Toulmin model', badge: 'agents', description: 'Domain Writer instructed to structure every major claim as claim+data+warrant+qualifier+rebuttal' },
      { title: 'All publication target rubrics updated', badge: 'pipeline', description: 'argumentative_rigor dimension added to SANS (15%), IEEE (15%), Industry (15%), Self-Published (15%)' },
    ],
    fixed: [
      { title: 'Reviewer context window', badge: 'pipeline', description: 'Reviewer now receives full draft as condensed prose instead of truncated [:8000] JSON blob' },
      { title: 'Review gate enforcement', badge: 'pipeline', description: 'Reviewer REVISE recommendation now correctly triggers REVISION_REQUESTED instead of auto-advancing' },
      { title: 'Writer source waste', badge: 'context', description: 'Writer no longer sends entire source corpus to every section; only assigned sources per section' },
    ],
  },
  {
    version: '1.1.0',
    date: '2026-03-25',
    summary: 'Self-healing pipeline, performance optimizations, Visual Architect quality fixes',
    added: [
      { title: 'Sentinel agent wrapper', badge: 'healing', description: 'Monitors every agent execution for failures, timeouts, quality degradation, and cost anomalies' },
      { title: 'Diagnostic Agent', badge: 'healing', description: 'Heuristic + LLM error classifier that determines root cause, severity, and recommended fix' },
      { title: 'Remediation Engine', badge: 'healing', description: 'Automatic fix strategies: retry, JSON repair, provider switch, prompt simplification, feedback injection' },
      { title: 'About page', badge: 'ui', description: 'Structured product documentation with agent roster, pipeline flow, and changelog' },
      { title: 'Diagnostics Observatory tab', badge: 'observatory', description: 'Healing event timeline, success rates, error distribution' },
      { title: 'diagnostic_events DB table', badge: 'infra', description: 'Full lifecycle of detection, diagnosis, remediation attempts, and outcomes' },
    ],
    changed: [
      { title: 'Orchestrator uses Sentinel wrapper', badge: 'pipeline', description: 'All agent.execute() calls now protected by Sentinel when enabled' },
      { title: 'Docker Compose optimized', badge: 'infra', description: 'Memory limits (2G API, 512M Jaeger), health checks, Ollama host networking, 2 uvicorn workers' },
    ],
    fixed: [
      { title: 'QuadrantChart rendering', badge: 'agents', description: 'Sanitizer strips parentheses/slashes from quadrant labels and point names; prompt shows CORRECT/WRONG examples' },
      { title: 'Claude CLI tool-call suppression', badge: 'infra', description: '--allowedTools "" + "no tools" prompt injection stops Claude from emitting XML tool calls instead of JSON' },
      { title: 'Visual Architect JSON parser', badge: 'agents', description: 'Targeted "figures" key search instead of naive first-brace matching; handles tool-call preamble' },
      { title: 'Journey diagram colon sanitizer', badge: 'agents', description: 'Strips colons from journey section labels that break Mermaid parser' },
      { title: 'Production Agent content preservation', badge: 'agents', description: 'Deterministic assembly: draft content passes through verbatim, LLM only for bibliography + checklist' },
      { title: 'Section-by-section drafting', badge: 'agents', description: 'Writer drafts each outline section individually instead of all-at-once; ensures full outline coverage' },
      { title: 'Self-reflect model variable fix', badge: 'pipeline', description: 'UnboundLocalError in self_reflect when using Ollama path; model variable now properly scoped' },
      { title: 'Reflection on Ollama', badge: 'infra', description: 'All self-reflection checkpoints route to local Ollama ($0.00) regardless of primary provider' },
      { title: 'LLM calls in thread executor', badge: 'infra', description: 'Blocking subprocess calls wrapped in run_in_executor; event loop stays responsive during LLM calls' },
      { title: 'Delete cascade for diagnostic_events', badge: 'infra', description: 'Project deletion now cascades to diagnostic_events table' },
    ],
  },
  {
    version: '1.0.0',
    date: '2026-03-22',
    summary: 'Initial release: 7-agent research authoring pipeline with full observability',
    added: [
      { title: '7-agent pipeline', badge: 'agents', description: 'Research Strategist, Structure Architect, Domain Writer, Visual Architect, Critical Reviewer, Production Agent, Observatory' },
      { title: '8 publication target profiles', badge: 'pipeline', description: 'SANS Reading Room, IEEE S&P, ACM CCS, USENIX Security, ACSAC, Dark Reading, LinkedIn Article, CSA Research' },
      { title: 'Artifact Envelope Protocol', badge: 'pipeline', description: 'Structured JSON contract for all inter-agent communication with versioning and rejection chains' },
      { title: 'Visual Architect with 12 diagram types', badge: 'agents', description: 'Professional Mermaid diagrams: flowchart, sequence, class, state, mindmap, quadrant, xychart, pie, radar, sankey, timeline, gantt' },
      { title: 'Observatory dashboard', badge: 'observatory', description: '4-tab dashboard: Traces, Quality radar, Cost breakdown, Improvement insights' },
      { title: 'Review gate with revision loops', badge: 'pipeline', description: 'Critical Reviewer can reject drafts, triggering automatic re-draft up to 3 cycles' },
      { title: 'Document preview', badge: 'ui', description: 'In-app markdown preview with confidence flags, citation rendering, and word count' },
      { title: 'Dual AI providers', badge: 'infra', description: 'Claude CLI (keychain auth) + Ollama (local qwen3.5) with auto-detection' },
      { title: 'Author feedback loop', badge: 'observatory', description: 'Rubric weight auto-adjustment based on author/system rating divergence' },
      { title: 'NDA filter', badge: 'pipeline', description: 'Cross-cutting content sensitivity detection with flag/generalize/block modes' },
      { title: 'Export: DOCX + Markdown + JSON', badge: 'ui', description: 'Document export in multiple formats with venue-appropriate formatting' },
      { title: 'Docker Compose deployment', badge: 'infra', description: 'Three-container setup: API + Frontend (nginx) + Jaeger' },
      { title: 'SQLite with WAL mode', badge: 'infra', description: '11 tables with full indexing, WAL journaling, foreign keys' },
      { title: 'OpenTelemetry instrumentation', badge: 'infra', description: 'GenAI semantic conventions on every LLM call; traces exportable to Jaeger' },
    ],
  },
];
