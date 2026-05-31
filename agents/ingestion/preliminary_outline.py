from __future__ import annotations

import json

import openai

from agents.base import BaseAgent
from state.research_state import ResearchState

_SYSTEM = """\
You are the Preliminary Outline Agent. You have access to a synthesized research memo AND the \
raw parsed inputs (Excel models, drafts, notes, charts). Your job is to draft the first \
structural blueprint for the paper — a preliminary outline that reflects:

1. The research's natural structure as evidenced by the materials provided
2. Sections that are already data-rich (the user has material for these)
3. Sections that are thin and will need the research lab to fill gaps
4. The logical argument arc from introduction to conclusion

This outline is PRELIMINARY — it will be reviewed, validated against existing literature, \
and refined by the Alignment Agent in the next phase. Your job is to make the best possible \
first draft given what the user has already built.

For each section, indicate:
- What existing material from the inputs supports it
- How complete the user's existing work is (rich / partial / gap)
- What a researcher would need to add

Return ONLY a valid JSON object:
{
  "title": "<proposed paper title>",
  "thesis": "<the central argument or finding in one sentence>",
  "abstract_direction": "<2-3 sentence summary of what the paper will argue>",
  "sections": [
    {
      "section_id": "S-01",
      "title": "<section title>",
      "objective": "<what this section must establish>",
      "key_topics": ["topic1", "topic2"],
      "existing_material": "<what from the user's inputs supports this section>",
      "completeness": "rich|partial|gap",
      "estimated_pages": <2-8>
    }
  ],
  "data_assets": [
    {
      "file": "<filename>",
      "key_value": "<most important data point or finding from this file>",
      "used_in_section": "S-xx"
    }
  ],
  "research_questions": ["RQ1", "RQ2", "RQ3"],
  "gaps_identified": ["gap1", "gap2"]
}
"""


class PreliminaryOutlineAgent(BaseAgent):
    name = "PreliminaryOutlineAgent"
    model = "gpt-4o"
    use_thinking = True

    def execute(self, state: ResearchState, client: openai.OpenAI) -> ResearchState:
        # Build a compact summary of what was parsed
        input_inventory = "\n".join(
            f"- {inp.file_name} ({inp.file_type.upper()}): "
            f"{len(inp.content)} chars extracted"
            + (f", sheets: {inp.metadata.get('sheets', [])}" if inp.metadata.get("sheets") else "")
            + (f", {inp.metadata.get('page_count', '')} pages" if inp.metadata.get("page_count") else "")
            for inp in state.raw_inputs
        )

        # Include excerpts from each file (first 1500 chars each) for outline context
        excerpts = "\n\n".join(
            f"[{inp.file_name}]\n{inp.content[:1500]}"
            + ("..." if len(inp.content) > 1500 else "")
            for inp in state.raw_inputs
        )

        response = self._call_claude(
            client=client,
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": (
                    f"Synthesized research memo:\n\n{state.synthesized_memo}\n\n"
                    f"Input inventory:\n{input_inventory}\n\n"
                    f"Excerpts from each file:\n{excerpts}"
                ),
            }],
            max_tokens=6000,
        )

        result = self._parse_json(response)
        if not result:
            result = {
                "title": "Untitled Research Paper",
                "thesis": "",
                "abstract_direction": "",
                "sections": [],
                "data_assets": [],
                "research_questions": [],
                "gaps_identified": [],
            }

        state.preliminary_outline = result

        # Seed memo_text with the thesis + abstract direction for Phase 0 agents
        if not state.memo_text or state.memo_text == state.synthesized_memo:
            state.memo_text = state.synthesized_memo

        return state
