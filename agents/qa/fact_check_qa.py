from __future__ import annotations

import json

import openai

from agents.base import BaseAgent
from state.research_state import AuditFinding, ResearchState

_SYSTEM = """\
You are the QA Fact-Check Agent. You verify every claim in the drafted sections against the \
source registry using three-dimensional citation verification:

1. Relevant Content — the cited source topically supports the claim
2. Fact Check — the cited source factually supports the exact claim text
3. Table/Figure data — quantitative values in tables or figures match the source material

Flag any citation where the source_id is not in the registry (orphan citation) as Critical.

Return ONLY a valid JSON object:
{
  "findings": [
    {
      "severity": "critical|warning|minor",
      "description": "<specific failure>",
      "section_id": "<S-xx>",
      "source_id": "<SR-xxx>",
      "dream_dimension": "source_quality"
    }
  ],
  "verified_claims": <int>,
  "failed_claims": <int>
}
"""


class FactCheckQA(BaseAgent):
    name = "FactCheckQA"
    model = "gpt-4o"
    use_thinking = True

    def execute(self, state: ResearchState, client: openai.OpenAI) -> ResearchState:
        sections_data = [
            {
                "section_id": s.section_id,
                "title": s.title,
                "claims": [{"text": c.text, "source_id": c.source_id} for c in s.claims],
            }
            for s in state.sections if s.content
        ]
        registered_ids = [s.source_id for s in state.source_registry]

        response = self._call_claude(
            client=client,
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": (
                    f"Sections with claims:\n{json.dumps(sections_data, indent=2)}\n\n"
                    f"Registered source IDs: {registered_ids}"
                ),
            }],
            max_tokens=6000,
        )
        result = self._parse_json(response)
        for f in result.get("findings", []):
            state.audit_findings.append(AuditFinding(
                finding_id=f"QA-FC-{len(state.audit_findings)+1:03d}",
                severity=f.get("severity", "warning"),
                description=f.get("description", ""),
                section_id=f.get("section_id"),
                source_id=f.get("source_id"),
                dream_dimension="source_quality",
            ))
        return state
