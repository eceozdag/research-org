from __future__ import annotations

import json

import anthropic

from agents.base import BaseAgent
from state.research_state import ResearchState

_SYSTEM = """\
You are a Topic Reviewer in an agentic research organization. You independently evaluate a topic \
researcher's output against three viability criteria. You are strict — a "pass" means the output \
is genuinely publication-ready for this topic, not just acceptable.

Viability criteria:
1. Evidential sufficiency — every key claim has ≥2 independent supporting sources
2. Methodological soundness — the experiments are valid and the logic is rigorous
3. Novelty/contribution check — the topic adds something beyond the existing literature cited

Return ONLY a valid JSON object:
{
  "passed": <true|false>,
  "evidential_sufficiency": {"passed": <true|false>, "notes": "<specific failures if any>"},
  "methodological_soundness": {"passed": <true|false>, "notes": "<specific failures if any>"},
  "novelty": {"passed": <true|false>, "notes": "<specific failures if any>"},
  "overall_notes": "<concise feedback for the researcher>",
  "required_changes": ["specific change 1", "specific change 2"]
}
"""


class TopicReviewer(BaseAgent):
    name = "TopicReviewer"
    model = "claude-opus-4-7"
    use_thinking = True

    def __init__(self, topic_id: str):
        self.topic_id = topic_id

    def execute(self, state: ResearchState, client: anthropic.Anthropic) -> ResearchState:
        result = self.check(state, client)
        output = state.get_topic(self.topic_id)
        if output:
            output.viability_record = result
        return state

    def check(self, state: ResearchState, client: anthropic.Anthropic) -> dict:
        output = state.get_topic(self.topic_id)
        if not output:
            return {"passed": False, "overall_notes": "No output found for this topic"}

        response = self._call_claude(
            client=client,
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": (
                    f"Topic output to review:\n\n"
                    f"Topic: {output.title}\n"
                    f"Content:\n{output.content}\n\n"
                    f"Experiments:\n{json.dumps(output.experiments, indent=2)}\n\n"
                    f"Sources in registry for this topic: "
                    f"{[s for s in state.source_registry if s.retrieved_by == f'TopicResearcher-{self.topic_id}']}"
                ),
            }],
            max_tokens=4096,
        )
        result = self._parse_json(response)
        if not result:
            return {"passed": False, "overall_notes": "Could not parse review"}
        return result
