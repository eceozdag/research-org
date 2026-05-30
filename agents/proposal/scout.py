from __future__ import annotations

import anthropic

from agents.base import BaseAgent
from state.research_state import ResearchState

_SYSTEM = """\
You are the Scout Agent in an agentic research organization. Your job is to survey the existing \
body of knowledge on the proposed research topic BEFORE any deep research begins.

Given a research memo and its proposal review, produce a structured landscape scan:

1. Existing body of research — key established works, consensus findings, major frameworks
2. Contradictions vs. the memo — where the memo's assumptions conflict with known evidence
3. Gaps in the literature — areas the memo addresses that are genuinely under-researched
4. Recommended depth areas — topics where more investigation will yield the most novel contribution

Return ONLY a valid JSON object:
{
  "existing_body": [
    {"area": "<topic area>", "summary": "<what is known>", "key_works": ["author/year or concept"]}
  ],
  "contradictions": [
    {"memo_claim": "<what the memo assumes>", "evidence": "<what research shows instead>", "severity": "critical|moderate|minor"}
  ],
  "gaps": [
    {"gap": "<description>", "opportunity": "<why this is valuable to investigate>"}
  ],
  "recommended_depth_areas": ["area1", "area2"],
  "overall_landscape": "<3-5 sentence synthesis of the research landscape>"
}

Base your scan on your training knowledge. Flag anything that requires real-time literature search \
(post-2024 developments, rapidly evolving fields) so downstream agents can prioritize live search.
"""


class ScoutAgent(BaseAgent):
    name = "ScoutAgent"
    model = "claude-opus-4-7"
    use_thinking = True

    def execute(self, state: ResearchState, client: anthropic.Anthropic) -> ResearchState:
        proposal_context = (
            f"Proposal review scores — Clarity: {state.proposal_review.get('clarity_score', 'N/A')}, "
            f"Feasibility: {state.proposal_review.get('feasibility_score', 'N/A')}\n"
            f"Missing context flagged: {state.proposal_review.get('missing_context', [])}\n"
        )
        response = self._call_claude(
            client=client,
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": (
                    f"Research memo:\n\n{state.memo_text}\n\n"
                    f"Proposal review notes:\n{proposal_context}"
                ),
            }],
            max_tokens=8096,
        )
        result = self._parse_json(response)
        if not result:
            result = {
                "existing_body": [],
                "contradictions": [],
                "gaps": [],
                "recommended_depth_areas": [],
                "overall_landscape": response[:800],
            }
        state.scout_report = result
        return state
