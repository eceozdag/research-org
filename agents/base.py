from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod

import anthropic

from state.research_state import ResearchState


class BaseAgent(ABC):
    model: str = "claude-opus-4-7"
    use_thinking: bool = True
    name: str = "BaseAgent"

    def _call_claude(
        self,
        client: anthropic.Anthropic,
        system: str,
        messages: list[dict],
        max_tokens: int = 8096,
        tools: list[dict] | None = None,
    ) -> str:
        kwargs: dict = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
        }
        if self.use_thinking:
            kwargs["thinking"] = {"type": "adaptive"}
        if tools:
            kwargs["tools"] = tools

        response = client.messages.create(**kwargs)

        for block in response.content:
            if hasattr(block, "type") and block.type == "text":
                return block.text
        return ""

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
    def execute(self, state: ResearchState, client: anthropic.Anthropic) -> ResearchState:
        pass
