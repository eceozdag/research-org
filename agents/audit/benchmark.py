from __future__ import annotations

import json

import anthropic

from agents.base import BaseAgent
from state.research_state import AuditFinding, DreamScores, ResearchState

_SYSTEM = """\
You are the Benchmark Audit Agent. You compare the research outputs against external standards \
and score the work on the DREAM evaluation framework.

Check:
1. Quantitative data baselines — are the numbers cited within expected ranges for this domain?
2. Prior versions/related papers — does this research improve on or differentiate from prior work?
3. Novelty delta — what is the measurable contribution beyond the existing literature?

Score on DREAM dimensions (0-10 each):
- Presentation Quality: logical structure, clear argument flow
- Task Compliance: does the research address the stated research questions?
- Analytical Depth: rigor of reasoning, depth of evidence treatment
- Source Quality: credibility, recency, relevance of citations

Return ONLY a valid JSON object:
{
  "findings": [
    {
      "severity": "critical|warning|minor",
      "description": "<benchmark deviation or gap>",
      "topic_id": "<if specific to a topic>",
      "dream_dimension": "presentation_quality|task_compliance|analytical_depth|source_quality"
    }
  ],
  "dream_scores": {
    "presentation_quality": <0-10>,
    "task_compliance": <0-10>,
    "analytical_depth": <0-10>,
    "source_quality": <0-10>
  },
  "novelty_assessment": "<how this paper advances the field>",
  "benchmark_summary": "<2-3 sentences on overall benchmark compliance>"
}
"""


class BenchmarkAudit(BaseAgent):
    name = "BenchmarkAudit"
    model = "claude-opus-4-7"
    use_thinking = True

    def execute(self, state: ResearchState, client: anthropic.Anthropic) -> ResearchState:
        topic_contents = [
            {"topic_id": t.topic_id, "title": t.title, "content": t.content[:800]}
            for t in state.topic_outputs
        ]
        existing_body = state.scout_report.get("existing_body", [])
        response = self._call_claude(
            client=client,
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": (
                    f"Research questions: {state.refined_outline.get('research_questions', [])}\n\n"
                    f"Topic outputs:\n{json.dumps(topic_contents, indent=2)}\n\n"
                    f"Existing body of research (for comparison):\n{json.dumps(existing_body, indent=2)}"
                ),
            }],
            max_tokens=6000,
        )
        result = self._parse_json(response)
        for f in result.get("findings", []):
            state.audit_findings.append(AuditFinding(
                finding_id=f"BEN-{len(state.audit_findings)+1:03d}",
                severity=f.get("severity", "warning"),
                description=f.get("description", ""),
                topic_id=f.get("topic_id"),
                dream_dimension=f.get("dream_dimension"),
            ))
        scores = result.get("dream_scores", {})
        state.dream_scores = DreamScores(
            presentation_quality=scores.get("presentation_quality", 5.0),
            task_compliance=scores.get("task_compliance", 5.0),
            analytical_depth=scores.get("analytical_depth", 5.0),
            source_quality=scores.get("source_quality", 5.0),
        )
        state.benchmark_report = {
            "novelty_assessment": result.get("novelty_assessment", ""),
            "benchmark_summary": result.get("benchmark_summary", ""),
        }
        return state
