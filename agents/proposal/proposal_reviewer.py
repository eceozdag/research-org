from __future__ import annotations

import openai

from agents.base import BaseAgent
from state.research_state import ResearchState

_SYSTEM = """\
You are the Proposal Reviewer in an agentic research organization. You evaluate research memos \
before any investigation begins, protecting the pipeline from wasted effort on flawed proposals.

Assess the memo on three dimensions and return ONLY a valid JSON object — no prose, no markdown fences:

{
  "clarity_score": <0-10>,
  "feasibility_score": <0-10>,
  "missing_context": ["list of absent critical information"],
  "overall_assessment": "<2-3 sentence summary>",
  "recommended_sections": ["suggested section titles for the paper"],
  "flags": ["any critical concerns that could derail the research"]
}

Clarity (0-10): Does the memo clearly communicate research intent, key questions, and desired contribution?
Feasibility (0-10): Is the scope achievable in a focused scientific white paper (20-40 pages)?
Missing context: Information absent that a researcher would need to proceed confidently.
Flags: Scope creep, contradictory goals, legally sensitive claims, unverifiable assertions.
"""


class ProposalReviewer(BaseAgent):
    name = "ProposalReviewer"
    model = "gpt-4o"
    use_thinking = True

    def execute(self, state: ResearchState, client: openai.OpenAI) -> ResearchState:
        response = self._call_claude(
            client=client,
            system=_SYSTEM,
            messages=[{"role": "user", "content": f"Review this research memo:\n\n{state.memo_text}"}],
            max_tokens=4096,
        )
        result = self._parse_json(response)
        if not result:
            result = {
                "clarity_score": 5,
                "feasibility_score": 5,
                "missing_context": ["Structured review could not be parsed"],
                "overall_assessment": response[:500],
                "recommended_sections": [],
                "flags": [],
            }
        state.proposal_review = result
        return state
