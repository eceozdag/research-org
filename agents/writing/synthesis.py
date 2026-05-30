from __future__ import annotations

import anthropic

from agents.base import BaseAgent
from state.research_state import ResearchState

_SYSTEM = """\
You are the Synthesis Agent. You review all drafted sections as a unified document and produce \
a synthesis pass that ensures:

1. Cross-section flow — sections connect logically; transitions are coherent
2. Duplicate content removed — the same evidence or argument is not made twice
3. Internal references — cross-references between sections are correct and consistent
4. Abstract and conclusion alignment — both reflect the actual content of the paper

Return ONLY a valid JSON object:
{
  "abstract": "<updated abstract, 200-300 words>",
  "conclusion": "<updated conclusion, 300-500 words>",
  "cross_reference_fixes": [
    {"section_id": "<id>", "issue": "<what was inconsistent>", "fix": "<correction>"}
  ],
  "duplicate_removals": [
    {"section_id": "<id>", "removed_content": "<brief description>"}
  ],
  "flow_notes": "<overall assessment of document flow>"
}
"""


class SynthesisAgent(BaseAgent):
    name = "SynthesisAgent"
    model = "claude-opus-4-7"
    use_thinking = True

    def execute(self, state: ResearchState, client: anthropic.Anthropic) -> ResearchState:
        draft_content = "\n\n---\n\n".join(
            f"## {s.title}\n{s.content}" for s in state.sections if s.content
        )
        response = self._call_claude(
            client=client,
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": (
                    f"Paper title: {state.refined_outline.get('title', '')}\n"
                    f"Research questions: {state.refined_outline.get('research_questions', [])}\n\n"
                    f"Full draft:\n\n{draft_content}"
                ),
            }],
            max_tokens=8096,
        )
        result = self._parse_json(response)
        if result:
            state.benchmark_report["abstract"] = result.get("abstract", "")
            state.benchmark_report["conclusion"] = result.get("conclusion", "")
            state.benchmark_report["synthesis_notes"] = result.get("flow_notes", "")
        return state
