from __future__ import annotations

import openai

from agents.base import BaseAgent
from state.research_state import ResearchState

_SYSTEM = """\
You are the Writing Review Agent. You perform the final writing quality check before the paper \
is delivered. You are the last line of defense on content.

Check:
1. Citation completeness — every factual claim has a [n] citation
2. Prose quality — formal academic register; no colloquialisms, no first-person
3. Claim-citation alignment — each [n] citation is placed at the correct claim
4. Section completeness — no section ends abruptly or is missing its conclusion

Return ONLY a valid JSON object:
{
  "decision": "approved|rejected",
  "findings": [
    {"severity": "critical|warning|minor", "section_id": "<id>", "issue": "<description>"}
  ],
  "overall_notes": "<2-3 sentence assessment>"
}
"""


class WritingReview(BaseAgent):
    name = "WritingReview"
    model = "gpt-4o"
    use_thinking = True

    def execute(self, state: ResearchState, client: openai.OpenAI) -> ResearchState:
        draft = "\n\n---\n\n".join(
            f"## {s.title}\n{s.content}" for s in state.sections if s.content
        )
        response = self._call_claude(
            client=client,
            system=_SYSTEM,
            messages=[{"role": "user", "content": f"Review this paper draft:\n\n{draft[:12000]}"}],
            max_tokens=4096,
        )
        result = self._parse_json(response)
        state.human_checkpoints["writing_review"] = {
            "decision": result.get("decision", "rejected"),
            "findings": result.get("findings", []),
            "notes": result.get("overall_notes", ""),
        }
        return state
