from __future__ import annotations

import openai

from agents.base import BaseAgent
from state.research_state import ResearchState

_SYSTEM = """\
You are the LaTeX/Prism Formatter. You take the complete paper content and produce a \
publication-ready LaTeX document.

Requirements:
- Document class: \\documentclass[12pt,a4paper]{article}
- Vancouver bibliography style: \\bibliographystyle{vancouver}
- All figures referenced with \\ref{} and placed with [h!]
- Tables formatted with booktabs
- Section hierarchy: \\section, \\subsection, \\subsubsection
- Abstract in \\begin{abstract} environment
- All citations as \\cite{source_id}

Return ONLY a valid JSON object:
{
  "latex_source": "<complete .tex file content>",
  "bibliography_entries": [
    {
      "source_id": "SR-001",
      "bibtex": "@article{SR-001, author={...}, title={...}, year={...}, ...}"
    }
  ],
  "figure_placements": ["FIG-01 placed in section S-02", "..."]
}
"""


class LaTeXFormatter(BaseAgent):
    name = "LaTeXFormatter"
    model = "gpt-4o"
    use_thinking = False

    def execute(self, state: ResearchState, client: openai.OpenAI) -> ResearchState:
        paper_content = {
            "title": state.refined_outline.get("title", "Untitled"),
            "abstract": state.benchmark_report.get("abstract", ""),
            "sections": [
                {"id": s.section_id, "title": s.title, "content": s.content}
                for s in state.sections
            ],
            "conclusion": state.benchmark_report.get("conclusion", ""),
            "sources": [
                {"id": s.source_id, "url": s.url, "excerpt": s.raw_excerpt[:100]}
                for s in state.source_registry
            ],
            "figures": state.figures,
        }
        import json
        response = self._call_claude(
            client=client,
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": f"Format this paper as LaTeX:\n{json.dumps(paper_content, indent=2)[:12000]}",
            }],
            max_tokens=16000,
        )
        result = self._parse_json(response)
        if result.get("latex_source"):
            state.appendix.append({
                "type": "latex_source",
                "content": result["latex_source"],
            })
            state.appendix.append({
                "type": "bibliography",
                "entries": result.get("bibliography_entries", []),
            })
        return state
