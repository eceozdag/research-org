from __future__ import annotations

import json

import openai

from agents.base import BaseAgent
from state.research_state import Claim, ResearchState, Section

_SYSTEM = """\
You are a Section Writer. You write one section of a scientific white paper. You are READ-ONLY — \
you work only from the research provided; you do not search, retrieve, or invent sources.

Rules:
- Every factual claim must reference a source_id from the source registry
- Write in formal academic prose, third person
- Vancouver [n] citation style — cite inline as [1], [2], etc.
- Attach claim metadata: source_id + sentence_offset for every claim

Return ONLY a valid JSON object:
{
  "section_id": "<id>",
  "content": "<full section text with [n] citations>",
  "claims": [
    {
      "claim_id": "C-<section_id>-001",
      "text": "<exact claim sentence>",
      "source_id": "<SR-xxx>",
      "sentence_offset": <0-indexed position in content>,
      "confidence": <0.0-1.0>
    }
  ],
  "citation_map": {"[1]": "SR-001", "[2]": "SR-002"}
}
"""


class SectionWriter(BaseAgent):
    name = "SectionWriter"
    model = "gpt-4o-mini"
    use_thinking = False

    def __init__(self, section_id: str):
        self.section_id = section_id

    def execute(self, state: ResearchState, client: openai.OpenAI) -> ResearchState:
        section_spec = next(
            (s for s in state.section_map.get("sections", []) if s["section_id"] == self.section_id),
            None,
        )
        if not section_spec:
            return state

        topic_ids = section_spec.get("topic_ids", [])
        relevant_topics = [t for t in state.topic_outputs if t.topic_id in topic_ids]
        relevant_sources = [
            s for s in state.source_registry
            if s.retrieved_by in [f"TopicResearcher-{t.topic_id}" for t in relevant_topics]
        ]

        response = self._call_claude(
            client=client,
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": (
                    f"Section specification:\n{json.dumps(section_spec, indent=2)}\n\n"
                    f"Research content:\n"
                    + "\n\n".join(f"[{t.topic_id}] {t.title}:\n{t.content}" for t in relevant_topics)
                    + f"\n\nAvailable sources (cite as source_id):\n{json.dumps([{'id': s.source_id, 'excerpt': s.raw_excerpt[:200]} for s in relevant_sources], indent=2)}"
                ),
            }],
            max_tokens=6000,
        )
        result = self._parse_json(response)
        if not result:
            return state

        section = state.get_section(self.section_id)
        if section:
            section.content = result.get("content", "")
            section.status = "draft"
            section.claims = [
                Claim(
                    claim_id=c["claim_id"],
                    text=c["text"],
                    source_id=c.get("source_id", ""),
                    sentence_offset=c.get("sentence_offset", 0),
                    confidence=c.get("confidence", 1.0),
                )
                for c in result.get("claims", [])
            ]
        return state
