from __future__ import annotations

import json

import openai

from agents.base import BaseAgent
from state.research_state import AuditFinding, ResearchState

_SYSTEM = """\
You are the Consistency Audit Agent. You check for internal contradictions across all research \
topic outputs and detect cascade contamination — where a flawed claim in one topic has been \
repeated or built upon in another.

Check:
1. Cross-topic contradictions — two topics making incompatible factual claims
2. Terminology inconsistency — same concept named differently across topics
3. Quantitative conflicts — different numbers cited for the same metric across topics

Return ONLY a valid JSON object:
{
  "findings": [
    {
      "severity": "critical|warning|minor",
      "description": "<what conflicts>",
      "topic_id": "<primary topic>",
      "related_topic_id": "<conflicting topic>",
      "dream_dimension": "analytical_depth"
    }
  ],
  "consistency_matrix": {
    "<T-01 vs T-02>": "consistent|conflict|overlap"
  },
  "cascade_risks": ["<description of potential cascade if finding propagates>"]
}
"""


class ConsistencyAudit(BaseAgent):
    name = "ConsistencyAudit"
    model = "gpt-4o"
    use_thinking = True

    def execute(self, state: ResearchState, client: openai.OpenAI) -> ResearchState:
        topic_contents = [
            {"topic_id": t.topic_id, "title": t.title, "content": t.content[:1000]}
            for t in state.topic_outputs
        ]
        response = self._call_claude(
            client=client,
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": f"Topic outputs to cross-check:\n{json.dumps(topic_contents, indent=2)}",
            }],
            max_tokens=6000,
        )
        result = self._parse_json(response)
        for f in result.get("findings", []):
            state.audit_findings.append(AuditFinding(
                finding_id=f"CON-{len(state.audit_findings)+1:03d}",
                severity=f.get("severity", "warning"),
                description=f.get("description", ""),
                topic_id=f.get("topic_id"),
                dream_dimension=f.get("dream_dimension", "analytical_depth"),
            ))
        return state
