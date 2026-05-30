from __future__ import annotations

import openai

from agents.base import BaseAgent
from state.research_state import AuditFinding, ResearchState

_SYSTEM = """\
You are the Citation Auditor. You verify all citations in the paper meet the Vancouver [n] \
numbered inline style standard and that every citation is traceable to a source in the registry.

Check:
1. Format compliance — all citations use [n] style; no author-date format, no footnotes
2. Orphan citations — [n] references that don't map to any source_id in the registry
3. Sentence-level accuracy — cited sources are referenced at the correct sentence, not section level
4. Broken references — any [n] that appears in text but has no entry in the bibliography

Return ONLY a valid JSON object:
{
  "findings": [
    {
      "severity": "critical|warning|minor",
      "description": "<specific citation issue>",
      "section_id": "<S-xx if known>",
      "dream_dimension": "source_quality"
    }
  ],
  "total_citations": <int>,
  "compliant_citations": <int>,
  "bibliography_entries": <int>
}
"""


class CitationAuditor(BaseAgent):
    name = "CitationAuditor"
    model = "gpt-4o-mini"
    use_thinking = False

    def execute(self, state: ResearchState, client: openai.OpenAI) -> ResearchState:
        all_content = "\n\n".join(
            f"[{s.section_id}] {s.title}:\n{s.content[:1000]}" for s in state.sections if s.content
        )
        registered_ids = [s.source_id for s in state.source_registry]

        response = self._call_claude(
            client=client,
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": (
                    f"Paper content (excerpt per section):\n{all_content}\n\n"
                    f"Source registry IDs: {registered_ids}"
                ),
            }],
            max_tokens=4096,
        )
        result = self._parse_json(response)
        for f in result.get("findings", []):
            state.audit_findings.append(AuditFinding(
                finding_id=f"CITE-{len(state.audit_findings)+1:03d}",
                severity=f.get("severity", "warning"),
                description=f.get("description", ""),
                section_id=f.get("section_id"),
                dream_dimension="source_quality",
            ))
        return state
