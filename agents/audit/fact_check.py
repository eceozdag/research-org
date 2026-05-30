from __future__ import annotations

import json

import openai

from agents.base import BaseAgent
from state.research_state import AuditFinding, ResearchState

_SYSTEM = """\
You are the Fact-Check Audit Agent. You verify every key claim in the research topic outputs \
against the source registry using three-dimensional citation verification:

1. Link Works — the source URL/reference is accessible and the content exists
2. Relevant Content — the source topically supports the claim being made
3. Fact Check — the source factually supports the exact claim (not just the topic area)

Also build a claim provenance map: trace each claim back to its source_id.

Return ONLY a valid JSON object:
{
  "findings": [
    {
      "severity": "critical|warning|minor",
      "description": "<what failed>",
      "topic_id": "<topic_id if applicable>",
      "source_id": "<SR-xxx if applicable>",
      "dream_dimension": "source_quality"
    }
  ],
  "claim_provenance_map": {
    "<claim_text_hash>": {
      "topic_id": "<T-xx>",
      "source_id": "<SR-xxx>",
      "confidence": <0.0-1.0>
    }
  },
  "citations_verified": <int>,
  "citations_failed": <int>
}
"""


class FactCheckAudit(BaseAgent):
    name = "FactCheckAudit"
    model = "gpt-4o"
    use_thinking = True

    def execute(self, state: ResearchState, client: openai.OpenAI) -> ResearchState:
        topic_summary = [
            {"topic_id": t.topic_id, "title": t.title, "content_excerpt": t.content[:500]}
            for t in state.topic_outputs
        ]
        source_summary = [
            {"source_id": s.source_id, "url": s.url, "excerpt": s.raw_excerpt[:200]}
            for s in state.source_registry
        ]
        response = self._call_claude(
            client=client,
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": (
                    f"Topic outputs:\n{json.dumps(topic_summary, indent=2)}\n\n"
                    f"Source registry:\n{json.dumps(source_summary, indent=2)}"
                ),
            }],
            max_tokens=8096,
        )
        result = self._parse_json(response)
        for f in result.get("findings", []):
            state.audit_findings.append(AuditFinding(
                finding_id=f"FC-{len(state.audit_findings)+1:03d}",
                severity=f.get("severity", "minor"),
                description=f.get("description", ""),
                topic_id=f.get("topic_id"),
                source_id=f.get("source_id"),
                dream_dimension=f.get("dream_dimension", "source_quality"),
            ))
        if result.get("claim_provenance_map"):
            state.claim_provenance_map.update(result["claim_provenance_map"])
        return state
