from __future__ import annotations

import json

import openai

from agents.base import BaseAgent
from state.research_state import ResearchState, TopicNote, TopicOutput

_SYSTEM = """\
You are a Topic Researcher in an agentic research organization. You investigate a single research \
topic with the rigor of a PhD researcher, running three experiment types:

1. Adversarial hypothesis testing — assume the opposite of the expected finding; attempt to disprove it
2. Multi-source triangulation — find at least 3 independent sources confirming each key claim
3. Quantitative replication — locate or reconstruct the key quantitative evidence

Before searching, decompose the topic into 4-8 subqueries (dual strategy: one semantic/conceptual, \
one keyword-exact). Document your subquery plan.

After research, run a self-reflection: check your output against:
- Evidential sufficiency: are claims backed by ≥2 independent sources?
- Methodological soundness: are experiments valid?
- Novelty: does this contribute beyond existing literature?

Return ONLY a valid JSON object:
{
  "topic_id": "<id>",
  "subqueries": ["semantic query 1", "keyword query 1", "..."],
  "content": "<comprehensive research synthesis, 500-1500 words>",
  "experiments": {
    "adversarial": "<hypothesis tested and outcome>",
    "triangulation": "<3+ sources and agreement level>",
    "quantitative": "<key figures and their sources>"
  },
  "sources": [
    {"url": "<url or citation>", "excerpt": "<key sentence supporting claim>"}
  ],
  "topic_notes": [
    {
      "subtopic": "<subtopic>",
      "partial_answer": "<what was found>",
      "confidence": <0.0-1.0>,
      "conflicting_sources": ["<source_id if known>"],
      "conflict_resolution": "pending"
    }
  ],
  "self_reflection": {
    "evidential_sufficiency": "<pass|fail>",
    "methodological_soundness": "<pass|fail>",
    "novelty": "<pass|fail>",
    "revision_needed": <true|false>,
    "revision_notes": "<what needs improving>"
  }
}
"""


class TopicResearcher(BaseAgent):
    name = "TopicResearcher"
    model = "gpt-4o"
    use_thinking = True

    def __init__(self, topic_id: str, topic: dict):
        self.topic_id = topic_id
        self.topic = topic

    def execute(self, state: ResearchState, client: openai.OpenAI) -> ResearchState:
        outline_context = json.dumps(state.refined_outline, indent=2)
        existing_output = state.get_topic(self.topic_id)
        revision_notes = ""
        if existing_output and existing_output.viability_record:
            revision_notes = f"\nPrevious reviewer feedback:\n{json.dumps(existing_output.viability_record, indent=2)}"

        response = self._call_claude(
            client=client,
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": (
                    f"Topic to research:\n{json.dumps(self.topic, indent=2)}\n\n"
                    f"Paper outline context:\n{outline_context}"
                    f"{revision_notes}"
                ),
            }],
            max_tokens=8096,
        )
        result = self._parse_json(response)
        if not result:
            result = {"topic_id": self.topic_id, "content": response[:2000], "sources": [], "topic_notes": []}

        # Register sources and build TopicOutput
        source_ids = []
        for src in result.get("sources", []):
            sid = state.add_source(
                url=src.get("url", ""),
                retrieved_by=f"TopicResearcher-{self.topic_id}",
                raw_excerpt=src.get("excerpt", ""),
            )
            source_ids.append(sid)

        for note_data in result.get("topic_notes", []):
            state.topic_notes.append(TopicNote(
                topic_id=self.topic_id,
                subtopic=note_data.get("subtopic", ""),
                partial_answer=note_data.get("partial_answer", ""),
                confidence=note_data.get("confidence", 0.5),
                conflicting_sources=note_data.get("conflicting_sources", []),
                conflict_resolution=note_data.get("conflict_resolution", "pending"),
            ))

        output = TopicOutput(
            topic_id=self.topic_id,
            title=self.topic.get("title", ""),
            status="pending",
            content=result.get("content", ""),
            experiments=result.get("experiments", {}),
            subqueries=result.get("subqueries", []),
        )
        existing = state.get_topic(self.topic_id)
        if existing:
            idx = state.topic_outputs.index(existing)
            state.topic_outputs[idx] = output
        else:
            state.topic_outputs.append(output)

        return state
