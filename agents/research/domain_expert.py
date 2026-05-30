from __future__ import annotations

import openai

from agents.base import BaseAgent
from state.research_state import ResearchState

_SYSTEM = """\
You are a Domain Expert agent, dynamically spawned for a specific academic domain. Your role is \
to inject specialist knowledge into a topic researcher's working context — identifying domain-specific \
methodological standards, key terminology, landmark studies, and common pitfalls.

Return ONLY a valid JSON object:
{
  "domain": "<domain name>",
  "landmark_works": ["author/year: brief description"],
  "methodological_standards": ["standard 1", "standard 2"],
  "key_terminology": {"term": "definition"},
  "common_pitfalls": ["pitfall 1", "pitfall 2"],
  "specialist_notes": "<any critical domain context the researcher must know>"
}
"""


class DomainExpert(BaseAgent):
    name = "DomainExpert"
    model = "gpt-4o-mini"
    use_thinking = False

    def __init__(self, domain: str, topic_id: str):
        self.domain = domain
        self.topic_id = topic_id

    def execute(self, state: ResearchState, client: openai.OpenAI) -> ResearchState:
        response = self._call_claude(
            client=client,
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": (
                    f"Provide specialist domain context for:\n"
                    f"Domain: {self.domain}\n"
                    f"Topic: {state.get_topic(self.topic_id).title if state.get_topic(self.topic_id) else ''}"
                ),
            }],
            max_tokens=4096,
        )
        result = self._parse_json(response)
        output = state.get_topic(self.topic_id)
        if output and result:
            output.experiments["domain_expert_context"] = result
        return state
