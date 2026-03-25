# Changelog

All notable changes to RAPTOR are documented here.

## [1.1.0] - 2026-03-25

Self-healing pipeline with Sentinel, Diagnostic Agent, and Remediation Engine.

### Added
- **Sentinel** agent wrapper: monitors every agent execution for failures, timeouts, quality degradation, and cost anomalies
- **Diagnostic Agent**: heuristic + LLM error classifier with root cause analysis, severity classification, and recommended actions
- **Remediation Engine**: automatic fix strategies (retry, JSON repair, provider switch, prompt simplification, feedback injection)
- **About page**: structured product documentation with agent roster, pipeline flow, self-healing system, changelog
- **Diagnostics Observatory tab**: healing event timeline, success rates, error distribution
- **Error type hierarchy**: RaptorError base with ParseError, ProviderError, TimeoutError, QualityDegradation, CostAnomaly, ValidationError
- **diagnostic_events DB table**: stores full lifecycle of detection, diagnosis, remediation attempts, and outcomes

### Changed
- Orchestrator uses Sentinel wrapper for all agent executions (configurable via `RAPTOR_SENTINEL_ENABLED`)

## [1.0.0] - 2026-03-22

Initial release: 7-agent research authoring pipeline with full observability.

### Added
- 7-agent pipeline: Research Strategist, Structure Architect, Domain Writer, Visual Architect, Critical Reviewer, Production Agent, Observatory
- 8 pre-built venue profiles: SANS Reading Room, IEEE S&P, ACM CCS, USENIX Security, ACSAC, Dark Reading, LinkedIn Article, CSA Research
- Artifact Envelope Protocol for structured inter-agent communication
- Visual Architect with 12 Mermaid diagram types and professional theming
- Observatory dashboard (Traces, Quality, Cost, Improvement tabs)
- Review gate with revision loops (max 3 cycles)
- In-app document preview with confidence flags and citation rendering
- Dual AI providers: Claude CLI (keychain auth) + Ollama (qwen3.5 local)
- Section-by-section drafting for full outline coverage
- Deterministic Production Agent (100% content preservation)
- Author feedback loop with rubric weight auto-adjustment
- NDA filter with flag/generalize/block modes
- Citation provenance warning for LLM-generated sources
- Performance: self-reflection on Ollama, LLM calls in thread executor, batched DB commits
