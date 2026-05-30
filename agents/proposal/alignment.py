from __future__ import annotations

import anthropic

from agents.base import BaseAgent
from state.research_state import ResearchState

_SYSTEM = """\
You are the Alignment Agent in an agentic research organization. You take a research memo, its \
proposal review, and the Scout Agent's landscape scan, then produce a refined, factually-grounded \
outline that can be approved for full research.

Your job:
1. Incorporate the Scout's contradiction findings — revise or drop memo claims that conflict with evidence
2. Address gaps identified by the proposal reviewer — add missing context to the outline
3. Structure the paper around the Scout's recommended depth areas
4. Produce a section-by-section outline with clear scope for each section

Return ONLY a valid JSON object:
{
  "title": "<proposed paper title>",
  "abstract_direction": "<2-3 sentences on what the paper will argue/demonstrate>",
  "sections": [
    {
      "section_id": "S-01",
      "title": "<section title>",
      "objective": "<what this section must establish>",
      "key_topics": ["topic1", "topic2"],
      "estimated_pages": <2-8>,
      "depends_on": ["S-01"]
    }
  ],
  "scope_boundaries": {
    "in_scope": ["what the paper covers"],
    "out_of_scope": ["what it explicitly does not cover"]
  },
  "contradictions_resolved": [
    {"original_claim": "<memo claim>", "resolution": "<how it was addressed in the outline>"}
  ],
  "research_questions": ["RQ1", "RQ2", "RQ3"]
}
"""


class AlignmentAgent(BaseAgent):
    name = "AlignmentAgent"
    model = "claude-opus-4-7"
    use_thinking = True

    def execute(self, state: ResearchState, client: anthropic.Anthropic) -> ResearchState:
        import json

        response = self._call_claude(
            client=client,
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": (
                    f"Research memo:\n\n{state.memo_text}\n\n"
                    f"Proposal review:\n{json.dumps(state.proposal_review, indent=2)}\n\n"
                    f"Scout landscape scan:\n{json.dumps(state.scout_report, indent=2)}"
                ),
            }],
            max_tokens=8096,
        )
        result = self._parse_json(response)
        if not result:
            result = {
                "title": "Untitled Research Paper",
                "abstract_direction": "",
                "sections": [],
                "scope_boundaries": {"in_scope": [], "out_of_scope": []},
                "contradictions_resolved": [],
                "research_questions": [],
            }
        state.refined_outline = result
        return state
