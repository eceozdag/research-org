from __future__ import annotations

import json

import openai

from agents.base import BaseAgent
from state.research_state import ResearchState, Section

_SYSTEM = """\
You are the Structure & Editorial Agent. You take the approved outline and all viable topic \
outputs and produce a locked section map — the definitive blueprint for the Section Writers.

For each section:
- Define exactly what must be written (not how — that is the writer's job)
- Assign which topic outputs feed into it
- Specify the argument it must make and the evidence it must cite
- Set the target length

Return ONLY a valid JSON object:
{
  "sections": [
    {
      "section_id": "S-01",
      "title": "<section title>",
      "objective": "<what this section must establish>",
      "topic_ids": ["T-01", "T-02"],
      "argument": "<the core argument or point to make>",
      "required_evidence": ["evidence item 1", "evidence item 2"],
      "target_words": <500-2000>,
      "position": <1-N>
    }
  ],
  "paper_flow": "<narrative description of how sections connect and build on each other>"
}
"""


class StructureEditorial(BaseAgent):
    name = "StructureEditorial"
    model = "gpt-4o"
    use_thinking = True

    def execute(self, state: ResearchState, client: openai.OpenAI) -> ResearchState:
        topic_titles = [{"id": t.topic_id, "title": t.title} for t in state.topic_outputs if t.status == "viable"]
        response = self._call_claude(
            client=client,
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": (
                    f"Approved outline:\n{json.dumps(state.refined_outline, indent=2)}\n\n"
                    f"Viable topics:\n{json.dumps(topic_titles, indent=2)}\n\n"
                    f"Research questions: {state.refined_outline.get('research_questions', [])}"
                ),
            }],
            max_tokens=6000,
        )
        result = self._parse_json(response)
        if not result or "sections" not in result:
            return state

        state.section_map = result
        state.sections = []
        for s in result["sections"]:
            state.sections.append(Section(
                section_id=s["section_id"],
                title=s["title"],
                status="pending",
            ))
        return state
