from __future__ import annotations

import openai

from agents.base import BaseAgent
from state.research_state import ResearchState

_SYSTEM = """\
You are the Graph Generation Agent. You identify all quantitative data in the paper that should \
be visualized and specify the exact figure for each. You produce Python/matplotlib specifications \
(not the actual rendered image — that is handled downstream).

For each figure, specify:
- Type: time-series | comparison_table | heatmap | architecture_diagram | geospatial
- Data: the exact values or data structure to plot
- Title, axis labels, caption
- The section_id it belongs to

Return ONLY a valid JSON object:
{
  "figures": [
    {
      "figure_id": "FIG-01",
      "type": "time-series|comparison_table|heatmap|architecture_diagram|geospatial",
      "title": "<figure title>",
      "caption": "<figure caption with citation>",
      "section_id": "S-xx",
      "data_spec": "<Python dict or description of data to plot>",
      "axis_labels": {"x": "<label>", "y": "<label>"},
      "source_ids": ["SR-xxx"]
    }
  ]
}
"""


class GraphGeneration(BaseAgent):
    name = "GraphGeneration"
    model = "gpt-4o-mini"
    use_thinking = False

    def execute(self, state: ResearchState, client: openai.OpenAI) -> ResearchState:
        quantitative_content = "\n\n".join(
            f"[{s.section_id}] {s.title}:\n{s.content[:600]}"
            for s in state.sections if s.content
        )
        response = self._call_claude(
            client=client,
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": f"Paper sections (look for quantitative data to visualize):\n\n{quantitative_content}",
            }],
            max_tokens=6000,
        )
        result = self._parse_json(response)
        state.figures.extend(result.get("figures", []))
        return state
