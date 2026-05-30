from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod

import openai

from state.research_state import ResearchState


class BaseAgent(ABC):
    model: str = "gpt-4o"
    use_thinking: bool = True  # kept for compatibility; ignored by OpenAI backend
    name: str = "BaseAgent"

    def _call_claude(
        self,
        client: openai.OpenAI,
        system: str,
        messages: list[dict],
        max_tokens: int = 8096,
        tools: list[dict] | None = None,
    ) -> str:
        """Calls the OpenAI Chat Completions API. Named _call_claude for drop-in compatibility."""
        kwargs: dict = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system}, *messages],
        }
        if tools:
            kwargs["tools"] = [{"type": "function", "function": t} for t in tools]

        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    def _parse_json(self, text: str) -> dict:
        match = re.search(r"```json\n(.*?)```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return {}

    @abstractmethod
    def execute(self, state: ResearchState, client: openai.OpenAI) -> ResearchState:
        pass
