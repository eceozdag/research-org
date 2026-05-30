from __future__ import annotations

import anthropic

from agents.base import BaseAgent
from state.research_state import ResearchState

_SYSTEM = """\
You are the Appendix Assembler. You collect all supplementary material and format it for inclusion.

Appendix sections to produce:
A. Raw data tables (quantitative data cited in the paper)
B. Methodology details (experiment descriptions from topic researchers)
C. Extended source list (full source registry with excerpts)
D. Supplementary figures (any figures that couldn't fit in the main text)

Return ONLY a valid JSON object:
{
  "appendix_sections": [
    {
      "label": "A",
      "title": "<appendix section title>",
      "content": "<formatted content>",
      "type": "data_table|methodology|source_list|supplementary_figure"
    }
  ]
}
"""


class AppendixAssembler(BaseAgent):
    name = "AppendixAssembler"
    model = "claude-sonnet-4-6"
    use_thinking = False

    def execute(self, state: ResearchState, client: anthropic.Anthropic) -> ResearchState:
        import json
        methodology_data = [
            {"topic_id": t.topic_id, "title": t.title, "experiments": t.experiments}
            for t in state.topic_outputs
        ]
        response = self._call_claude(
            client=client,
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": (
                    f"Topic methodologies:\n{json.dumps(methodology_data, indent=2)[:4000]}\n\n"
                    f"Source registry size: {len(state.source_registry)} sources\n"
                    f"Figures: {[f.get('figure_id') for f in state.figures]}"
                ),
            }],
            max_tokens=6000,
        )
        result = self._parse_json(response)
        for section in result.get("appendix_sections", []):
            state.appendix.append({"type": "appendix_section", **section})
        return state
