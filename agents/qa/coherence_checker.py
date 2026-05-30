from __future__ import annotations

import anthropic

from agents.base import BaseAgent
from state.research_state import AuditFinding, ResearchState

_SYSTEM = """\
You are the Coherence Checker. You assess the logical and stylistic coherence of the full paper.

Check:
1. Argument flow — each section builds on the previous; conclusions follow from evidence
2. Terminology consistency — the same concept is named consistently throughout
3. Section-to-section logic — transitions are present and logical
4. Abstract ↔ conclusion match — both tell the same story about findings
5. Research question coverage — each research question is addressed somewhere in the paper

Return ONLY a valid JSON object:
{
  "findings": [
    {
      "severity": "critical|warning|minor",
      "description": "<specific coherence issue>",
      "section_id": "<S-xx if localized>",
      "dream_dimension": "presentation_quality|task_compliance|analytical_depth"
    }
  ],
  "coherence_score": <0-10>,
  "rq_coverage": {"RQ1": "covered|partial|missing", "RQ2": "covered|partial|missing"}
}
"""


class CoherenceChecker(BaseAgent):
    name = "CoherenceChecker"
    model = "claude-opus-4-7"
    use_thinking = True

    def execute(self, state: ResearchState, client: anthropic.Anthropic) -> ResearchState:
        draft = "\n\n---\n\n".join(
            f"## {s.title}\n{s.content[:800]}" for s in state.sections if s.content
        )
        abstract = state.benchmark_report.get("abstract", "")
        conclusion = state.benchmark_report.get("conclusion", "")

        response = self._call_claude(
            client=client,
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": (
                    f"Research questions: {state.refined_outline.get('research_questions', [])}\n\n"
                    f"Abstract:\n{abstract}\n\nConclusion:\n{conclusion}\n\n"
                    f"Paper draft:\n{draft}"
                ),
            }],
            max_tokens=6000,
        )
        result = self._parse_json(response)
        for f in result.get("findings", []):
            state.audit_findings.append(AuditFinding(
                finding_id=f"COH-{len(state.audit_findings)+1:03d}",
                severity=f.get("severity", "minor"),
                description=f.get("description", ""),
                section_id=f.get("section_id"),
                dream_dimension=f.get("dream_dimension", "presentation_quality"),
            ))
        return state
