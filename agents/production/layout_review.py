from __future__ import annotations

import openai

from agents.base import BaseAgent
from state.research_state import ResearchState

_SYSTEM = """\
You are the Layout Review Agent. You perform the final structural and formatting check.

Check:
1. Figure numbering — all figures are numbered sequentially (Fig. 1, Fig. 2, ...)
2. Table formatting — all tables have captions and are referenced in text
3. Page structure — abstract, introduction, body, conclusion, references are all present
4. LaTeX/Prism compliance — document structure is valid; no unclosed environments
5. Reference list — every [n] in text has a corresponding bibliography entry

Return ONLY a valid JSON object:
{
  "decision": "approved|rejected",
  "findings": [
    {"severity": "critical|warning|minor", "issue": "<description>"}
  ],
  "structure_check": {
    "abstract": "present|missing",
    "introduction": "present|missing",
    "conclusion": "present|missing",
    "references": "present|missing"
  },
  "overall_notes": "<2-3 sentence assessment>"
}
"""


class LayoutReview(BaseAgent):
    name = "LayoutReview"
    model = "gpt-4o-mini"
    use_thinking = False

    def execute(self, state: ResearchState, client: openai.OpenAI) -> ResearchState:
        latex_block = next(
            (a for a in state.appendix if a.get("type") == "latex_source"), {}
        )
        latex_excerpt = latex_block.get("content", "")[:6000] if latex_block else ""
        section_titles = [s.title for s in state.sections]

        response = self._call_claude(
            client=client,
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": (
                    f"Section titles: {section_titles}\n"
                    f"Figure count: {len(state.figures)}\n"
                    f"Source count: {len(state.source_registry)}\n\n"
                    f"LaTeX source (excerpt):\n{latex_excerpt}"
                ),
            }],
            max_tokens=4096,
        )
        result = self._parse_json(response)
        state.human_checkpoints["layout_review"] = {
            "decision": result.get("decision", "rejected"),
            "findings": result.get("findings", []),
            "structure_check": result.get("structure_check", {}),
            "notes": result.get("overall_notes", ""),
        }
        return state
