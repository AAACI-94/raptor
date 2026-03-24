"""Agent 7: Visual Architect.

Analyzes draft sections and selects the optimal visualization type for each claim,
then generates Mermaid diagrams. Includes a comprehensive visualization selection
framework mapping data patterns to diagram types.
"""

import json
import logging
from typing import Any

from app.agents.base import BaseAgent
from app.models.constants import AgentRole, ArtifactType
from app.models.envelope import ArtifactMetadata
from app.services import artifact_service

logger = logging.getLogger(__name__)

VISUAL_SYSTEM = """Visual Architect for RAPTOR, a multi-agent research authoring platform for cybersecurity.

Your job: Analyze draft sections, identify claims that benefit from visualization, select
the optimal diagram type for each, and generate valid Mermaid markup.

Every figure must earn its place: it communicates something prose alone cannot.

## VISUALIZATION SELECTION FRAMEWORK

Use this decision matrix to select the right diagram type for each claim:

### PROCESS & FLOW (How does something work? What happens in sequence?)
| Pattern | Diagram Type | Mermaid Syntax | When to Use |
|---------|-------------|----------------|-------------|
| Step-by-step process | flowchart TD | `flowchart TD` | Decision trees, attack flows, pipelines, methodology steps |
| Temporal interactions | sequenceDiagram | `sequenceDiagram` | Protocol exchanges, attack sequences, API calls between components, agent-to-agent communication |
| State transitions | stateDiagram-v2 | `stateDiagram-v2` | Lifecycle management, incident states, system modes, alert escalation |
| User experience | journey | `journey` | Analyst workflows, attacker kill chains as user stories, adoption paths |
| Timeline/history | timeline | `timeline` | Vulnerability disclosure timelines, incident chronology, technology evolution |
| Phased work | gantt | `gantt` | Implementation roadmaps, remediation timelines, project phases |

### STRUCTURE & RELATIONSHIPS (How are things organized? What connects to what?)
| Pattern | Diagram Type | Mermaid Syntax | When to Use |
|---------|-------------|----------------|-------------|
| Hierarchical taxonomy | mindmap | `mindmap` | Attack taxonomies, capability trees, organizational structures |
| System architecture | flowchart LR | `flowchart LR` | Component diagrams, network topology, defense-in-depth layers |
| Block architecture | architecture | `architecture` | Cloud architecture, infrastructure layout with icons |
| Type hierarchies | classDiagram | `classDiagram` | Object models, policy inheritance, framework relationships |
| Entity relationships | erDiagram | `erDiagram` | Data models, asset relationships, permission structures |
| Concept maps | mindmap | `mindmap` | Brainstorming visualization, topic decomposition |

### COMPARISON & EVALUATION (How do things compare? Which is better?)
| Pattern | Diagram Type | Mermaid Syntax | When to Use |
|---------|-------------|----------------|-------------|
| Multi-dimensional comparison | radar-beta | `radar-beta` | Comparing tools/frameworks/products across multiple criteria (spider/radar chart) |
| 2x2 strategic positioning | quadrantChart | `quadrantChart` | Risk vs. impact, effort vs. value, severity vs. likelihood, prioritization matrices |
| Before/after contrast | flowchart TD with subgraphs | `flowchart TD` | Architecture improvements, security posture changes, maturity progression |
| Side-by-side feature comparison | xychart with bars | `xychart` | Tool capabilities, benchmark results, score comparisons |

### QUANTITATIVE DATA (What are the numbers? What's the distribution?)
| Pattern | Diagram Type | Mermaid Syntax | When to Use |
|---------|-------------|----------------|-------------|
| Proportional breakdown | pie | `pie` | Budget allocation, incident type distribution, attack vector frequency |
| Trends over time | xychart with line | `xychart` | Detection rates, vulnerability counts, cost trends, adoption metrics |
| Categorical comparison | xychart with bar | `xychart` | Performance benchmarks, survey results, framework scores |
| Combined trend + absolute | xychart with line + bar | `xychart` | Showing both raw counts (bars) and rates/trends (line) |
| Flow volume/allocation | sankey-beta | `sankey-beta` | Budget flows, data flows between systems, traffic distribution |

### STOCK-AND-FLOW (System dynamics: what accumulates, what flows?)
Mermaid has no native stock-and-flow diagram, but approximate with flowchart using conventions:
- Rectangles = stocks (things that accumulate: vulnerabilities, incidents, trained staff)
- Arrows with labels = flows (rates of change: discovery rate, resolution rate, attrition)
- Dashed arrows = feedback loops
- Cloud shapes for sources/sinks
Use `flowchart LR` with styled nodes: `stock["Unpatched\\nVulnerabilities\\n(stock)"]:::stockNode`

## MERMAID SYNTAX REFERENCE

### radar-beta (Spider/Radar Chart)
```
radar-beta
    title Security Framework Comparison
    axis Detect, Prevent, Respond, Recover, Identify
    curve Framework-A["NIST CSF"]{8, 7, 6, 9, 7}
    curve Framework-B["ISO 27001"]{6, 9, 8, 7, 8}
    max 10
    min 0
```

### quadrantChart (4-Quadrant Analysis)
```
quadrantChart
    title Risk Prioritization Matrix
    x-axis Low Likelihood --> High Likelihood
    y-axis Low Impact --> High Impact
    quadrant-1 Critical Priority
    quadrant-2 Monitor Closely
    quadrant-3 Accept Risk
    quadrant-4 Scheduled Fix
    SQL Injection: [0.8, 0.9]
    XSS Stored: [0.6, 0.7]
    Info Disclosure: [0.3, 0.2]
```

### xychart (Line/Bar Charts)
```
xychart
    title Detection Rate Over Time
    x-axis "Quarter" [Q1, Q2, Q3, Q4]
    y-axis "Percentage" 0 --> 100
    line [45, 62, 78, 89]
    bar [40, 58, 73, 85]
```

### sankey-beta (Flow Volume)
```
sankey-beta
    Source A,Target X,25
    Source A,Target Y,15
    Source B,Target X,10
    Source B,Target Y,30
```

### mindmap
```
mindmap
    root((Attack Vectors))
        Network
            Port Scanning
            MITM
        Application
            Injection
            XSS
        Social
            Phishing
            Pretexting
```

### timeline
```
timeline
    title Vulnerability Disclosure Timeline
    2024-01 : Discovery by researcher
    2024-02 : Vendor notification
    2024-04 : Patch released
    2024-05 : Public disclosure
```

### journey (User Journey)
```
journey
    title SOC Analyst Triage Workflow
    section Alert Received
        Review alert: 3: Analyst
        Check context: 4: Analyst
    section Investigation
        Query SIEM: 5: Analyst
        Correlate events: 3: Analyst
    section Response
        Escalate to IR: 4: Analyst, IR Lead
```

## CRITICAL SYNTAX RULES
1. Do NOT use HTML tags like `<br/>` in node labels. Use `\\n` for line breaks in flowchart nodes.
2. Use double quotes around labels with spaces: `A["My Label"]`
3. For subgraph labels with spaces, use quotes: `subgraph sg1["My Subgraph"]`
4. Avoid special characters in node IDs (use alphanumeric + underscores only)
5. Every diagram must be syntactically valid and renderable by mermaid.ink

## VENUE ADAPTATION
- **Academic (IEEE, ACM, USENIX)**: Formal notation, precise labels, grayscale-safe, numbered captions. Prefer: classDiagram, sequenceDiagram, xychart, quadrantChart.
- **Practitioner (SANS, CSA)**: Actionable diagrams, color-coded severity. Before/after comparisons. Prefer: flowchart, radar-beta, xychart, mindmap.
- **Industry (Dark Reading)**: Simple, one takeaway per figure. Prefer: pie, xychart bar, simple flowchart.
- **Self-published (LinkedIn)**: Eye-catching, shareable. Prefer: quadrantChart, pie, mindmap, simple radar.

## CYBERSECURITY CONVENTIONS
- Red/warm colors for threats, blue/cool for defenses
- Dashed lines for potential/optional, solid for confirmed
- Trust boundaries as labeled subgraphs
- MITRE ATT&CK technique IDs where relevant
- Detection points marked in defense diagrams

## OUTPUT FORMAT
Respond with valid JSON:
{
  "figures": [
    {
      "figure_id": "fig-1",
      "title": "Figure 1: Descriptive Title",
      "caption": "Detailed caption explaining what the figure shows...",
      "diagram_type": "sequenceDiagram",
      "selection_rationale": "Why this diagram type was chosen over alternatives",
      "mermaid": "sequenceDiagram\\n    participant A\\n    ...",
      "placement": "Section 3, after the paragraph discussing X",
      "supports_claim": "The specific claim this figure supports",
      "venue_notes": "Any venue-specific formatting notes"
    }
  ],
  "figure_plan": "Overall rationale for figure selection and argument arc support",
  "cross_references": [
    {"figure_id": "fig-1", "section": "Introduction", "reference_text": "as shown in Figure 1"}
  ],
  "total_figures": 4,
  "diagram_type_diversity": "Summary of diagram types used and why variety was chosen",
  "venue_compliance_notes": "How the figure set meets venue expectations"
}

## REJECTION CRITERIA
- Figure doesn't support any claim in the paper text
- Figure duplicates information already clear from prose alone
- Wrong diagram type for the data pattern (e.g., pie chart for temporal data)
- Mermaid syntax is invalid or uses HTML tags in node labels
- Figure count inappropriate for venue
- All figures use the same diagram type when variety would better serve the content
"""

REFLECTION_PROMPT = """For each figure:
1. Does it support a specific claim from the draft?
2. Is the diagram type optimal for the data pattern? (Check against the selection framework)
3. Is the Mermaid syntax valid? (No HTML tags in labels, proper quoting, valid node IDs)
4. Would a different diagram type communicate this better?
5. Is there sufficient diagram type diversity across the figure set?"""


class VisualArchitect(BaseAgent):
    """Generates venue-adapted Mermaid diagrams using a visualization selection framework."""

    role = AgentRole.VISUAL_ARCHITECT
    artifact_type = ArtifactType.FIGURES

    async def execute(self, project: Any, venue: Any) -> Any:
        await self.broadcast_progress(project.id, "Analyzing draft for visualization opportunities...", 5)

        # Get upstream artifacts
        draft = artifact_service.get_latest_artifact(project.id, ArtifactType.SECTION_DRAFT)
        outline = artifact_service.get_latest_artifact(project.id, ArtifactType.OUTLINE)
        research = artifact_service.get_latest_artifact(project.id, ArtifactType.RESEARCH_PLAN)

        if not draft:
            raise ValueError("No draft found. Run drafting stage first.")

        # Build venue-specific figure guidance
        venue_guidance = "General professional figures."
        expected_count = "3-5"
        if venue:
            vtype = venue.venue_type
            if vtype == "academic_conference":
                venue_guidance = f"Academic venue ({venue.display_name}). Formal notation, grayscale-safe, numbered. Prefer: classDiagram, sequenceDiagram, xychart, quadrantChart."
                expected_count = "4-8"
            elif vtype == "practitioner_repository":
                venue_guidance = f"Practitioner venue ({venue.display_name}). Actionable, color-coded. Before/after comparisons. Prefer: flowchart, radar-beta, xychart, mindmap."
                expected_count = "3-6"
            elif vtype == "industry_publication":
                venue_guidance = f"Industry publication ({venue.display_name}). Simple, high-impact. One takeaway per figure. Prefer: pie, xychart bar, simple flowchart."
                expected_count = "2-4"
            elif vtype == "self_published":
                venue_guidance = f"Self-published ({venue.display_name}). Eye-catching, shareable. Prefer: quadrantChart, pie, mindmap, radar."
                expected_count = "1-3"

        draft_summary = json.dumps(draft.payload, indent=2)[:6000]
        outline_summary = json.dumps(outline.payload, indent=2)[:2000] if outline else "No outline"
        contribution = research.payload.get("contribution_claim", "") if research else ""

        await self.broadcast_progress(project.id, "Selecting optimal diagram types...", 15)

        user_msg = f"""## Paper Title: {project.title}

## Contribution Claim
{contribution or 'Not specified'}

## Outline
{outline_summary}

## Draft Sections
{draft_summary}

## Venue Guidance
{venue_guidance}
Expected figure count: {expected_count}

## Instructions
1. Read the draft carefully and identify every claim, comparison, process, taxonomy, or quantitative finding that would benefit from visualization
2. For EACH visualization opportunity, consult the VISUALIZATION SELECTION FRAMEWORK to pick the optimal diagram type. Document your rationale.
3. Generate valid Mermaid markup for each figure. Test that your syntax is correct.
4. Aim for DIAGRAM TYPE DIVERSITY: use at least 3 different diagram types across your figures. Don't default to flowcharts for everything.
5. Follow the CRITICAL SYNTAX RULES (no HTML tags, proper quoting, valid IDs)
6. Write descriptive captions and map each figure to the claim it supports

Respond with the JSON structure from your system prompt."""

        result = await self.complete(
            messages=[{"role": "user", "content": user_msg}],
            system=VISUAL_SYSTEM,
            project_id=project.id,
            operation="generate_figures",
            max_tokens=16384,
            temperature=0.7,
        )

        await self.broadcast_progress(project.id, "Parsing figures...", 70)
        payload = self._parse_output(result["content"])

        # Post-process: sanitize Mermaid syntax
        for fig in payload.get("figures", []):
            mermaid = fig.get("mermaid", "")
            # Replace HTML <br/> with \n (common LLM mistake)
            mermaid = mermaid.replace("<br/>", "\\n").replace("<br>", "\\n")
            fig["mermaid"] = mermaid

        figure_count = len(payload.get("figures", []))
        types_used = list(set(f.get("diagram_type", "unknown") for f in payload.get("figures", [])))

        self.log_decision(
            project.id,
            decision=f"Generated {figure_count} figures using {len(types_used)} diagram types: {', '.join(types_used)}",
            rationale=payload.get("figure_plan", ""),
            confidence=0.85,
            alternatives=[f"Could generate {expected_count} per venue guidelines"],
        )

        # Self-reflection
        await self.broadcast_progress(project.id, "Self-reflection on diagram quality...", 85)
        reflection = await self.self_reflect(
            output=json.dumps(payload, indent=2)[:3000],
            reflection_prompt=REFLECTION_PROMPT,
            project_id=project.id,
        )

        await self.broadcast_progress(project.id, f"Figures complete ({figure_count} across {len(types_used)} types)", 100)

        metadata = ArtifactMetadata(
            model=result["model"],
            input_tokens=result["input_tokens"],
            output_tokens=result["output_tokens"],
            duration_ms=result["duration_ms"],
            estimated_cost_usd=result["cost_usd"],
        )

        return self.build_envelope(
            project_id=project.id,
            payload=payload,
            metadata=metadata,
            target_agent=AgentRole.CRITICAL_REVIEWER,
            reflection_result=reflection,
        )

    def _parse_output(self, content: str) -> dict:
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])
        except json.JSONDecodeError:
            pass
        return {"figures": [], "raw_content": content}
