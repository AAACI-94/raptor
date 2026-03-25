export interface ChangelogItem {
  title: string;
  badge?: 'pipeline' | 'agents' | 'ui' | 'observatory' | 'healing' | 'api' | 'infra';
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
    version: '1.1.0',
    date: '2026-03-25',
    summary: 'Self-healing pipeline with Sentinel, Diagnostic Agent, and Remediation Engine',
    added: [
      { title: 'Sentinel agent wrapper', badge: 'healing', description: 'Monitors every agent execution for failures, timeouts, quality degradation, and cost anomalies' },
      { title: 'Diagnostic Agent', badge: 'healing', description: 'Heuristic + LLM error classifier that determines root cause, severity, and recommended fix' },
      { title: 'Remediation Engine', badge: 'healing', description: 'Automatic fix strategies: retry, JSON repair, provider switch, prompt simplification, feedback injection' },
      { title: 'About page', badge: 'ui', description: 'Structured product documentation with agent roster, pipeline flow, and changelog' },
      { title: 'Diagnostics Observatory tab', badge: 'observatory', description: 'Healing event timeline, success rates, error distribution' },
      { title: 'Error type hierarchy', badge: 'pipeline', description: 'RaptorError base with ParseError, ProviderError, TimeoutError, QualityDegradation, CostAnomaly, ValidationError' },
      { title: 'diagnostic_events DB table', badge: 'infra', description: 'Stores full lifecycle of detection, diagnosis, remediation attempts, and outcomes' },
    ],
    changed: [
      { title: 'Orchestrator uses Sentinel wrapper', badge: 'pipeline', description: 'All agent.execute() calls now protected by Sentinel when enabled' },
    ],
  },
  {
    version: '1.0.0',
    date: '2026-03-22',
    summary: 'Initial release: 7-agent research authoring pipeline with full observability',
    added: [
      { title: '7-agent pipeline', badge: 'agents', description: 'Research Strategist, Structure Architect, Domain Writer, Visual Architect, Critical Reviewer, Production Agent, Observatory' },
      { title: '8 venue profiles', badge: 'pipeline', description: 'SANS Reading Room, IEEE S&P, ACM CCS, USENIX Security, ACSAC, Dark Reading, LinkedIn Article, CSA Research' },
      { title: 'Artifact Envelope Protocol', badge: 'pipeline', description: 'Structured JSON contract for all inter-agent communication with versioning and rejection chains' },
      { title: 'Visual Architect with 12 diagram types', badge: 'agents', description: 'Professional Mermaid diagrams: flowchart, sequence, class, state, mindmap, quadrant, xychart, pie, radar, sankey, timeline, gantt' },
      { title: 'Observatory dashboard', badge: 'observatory', description: '4-tab dashboard: Traces, Quality radar, Cost breakdown, Improvement insights' },
      { title: 'Review gate with revision loops', badge: 'pipeline', description: 'Critical Reviewer can reject drafts, triggering automatic re-draft up to 3 cycles' },
      { title: 'Document preview', badge: 'ui', description: 'In-app markdown preview with confidence flags, citation rendering, and word count' },
      { title: 'Dual AI providers', badge: 'infra', description: 'Claude CLI (keychain auth) + Ollama (local qwen3.5) with auto-detection' },
      { title: 'Section-by-section drafting', badge: 'agents', description: 'Domain Writer drafts each outline section individually for full coverage' },
      { title: 'Deterministic production', badge: 'agents', description: 'Production Agent formats without rewriting; 100% content preservation' },
      { title: 'Author feedback loop', badge: 'observatory', description: 'Rubric weight auto-adjustment based on author/system rating divergence' },
      { title: 'NDA filter', badge: 'pipeline', description: 'Cross-cutting content sensitivity detection with flag/generalize/block modes' },
      { title: 'Citation provenance warning', badge: 'agents', description: 'All LLM-generated sources marked as unverified with prominent author warning' },
      { title: 'Performance optimizations', badge: 'infra', description: 'Self-reflection on Ollama, LLM calls in thread executor, batched DB commits' },
    ],
  },
];
