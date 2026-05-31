from __future__ import annotations

from pathlib import Path

import openai
from rich.console import Console

from agents.base import BaseAgent
from agents.ingestion.file_parser import SUPPORTED, parse_file
from state.research_state import RawInput, ResearchState

console = Console()

_SYSTEM = """\
You are the Input Receiver Agent in an agentic research organization. You have been given the \
parsed contents of all research materials a user has provided — Excel models, unfinished drafts, \
notes, charts, PDFs, and any other documents.

Your job is to read ALL of this material and synthesize it into a single, coherent research memo \
that captures:

1. The core research question or thesis the user is pursuing
2. The key data points, models, and quantitative evidence already assembled
3. The existing structure or narrative the user has started building
4. Important observations, hypotheses, or arguments from the notes
5. Gaps or open questions visible in the materials
6. The intended audience and level of rigor

Write this as a structured research memo (not a bullet list dump). Use full sentences. \
Preserve specific numbers, model outputs, and technical details from the source materials — \
these are the evidence base for the paper.

The memo should be detailed enough that a researcher with no prior context could pick it up \
and understand exactly what the paper is trying to do and what evidence exists for it.
"""

_CONSOLIDATION_SYSTEM = """\
You are synthesizing multiple parsed research documents into one cohesive research memo. \
The documents may include Excel model outputs, rough drafts, handwritten notes, charts, \
and other materials in various states of completeness.

Return a single flowing research memo. Include:
- Stated or implied research thesis
- Key quantitative data and model outputs (preserve exact numbers)
- Existing arguments and evidence
- Structural intent (what the user was building toward)
- Open questions and gaps to address

Write in clear, formal prose. The memo becomes the foundation for a full research pipeline.
"""


class InputReceiverAgent(BaseAgent):
    name = "InputReceiverAgent"
    model = "gpt-4o"
    use_thinking = True

    def execute(self, state: ResearchState, client: openai.OpenAI) -> ResearchState:
        input_folder = Path(state.input_folder)
        if not input_folder.exists():
            console.print(f"[red]Input folder not found: {input_folder}[/]")
            return state

        # Discover and parse all supported files
        files = sorted([
            f for f in input_folder.iterdir()
            if f.is_file() and f.suffix.lower() in SUPPORTED
        ])

        if not files:
            console.print(f"[yellow]No supported files found in {input_folder}[/]")
            return state

        console.print(f"[cyan]Input Receiver: found {len(files)} file(s)[/]")

        for file_path in files:
            console.print(f"  Parsing [dim]{file_path.name}[/]…")
            try:
                content, metadata = parse_file(file_path, client)
                state.raw_inputs.append(RawInput(
                    file_name=file_path.name,
                    file_type=file_path.suffix.lower().lstrip("."),
                    content=content,
                    metadata=metadata,
                ))
            except Exception as e:
                console.print(f"  [red]Failed to parse {file_path.name}: {e}[/]")
                state.raw_inputs.append(RawInput(
                    file_name=file_path.name,
                    file_type=file_path.suffix.lower().lstrip("."),
                    content=f"[Parse error: {e}]",
                    metadata={},
                ))

        # Build consolidated input block for the LLM
        consolidated = self._build_consolidated_block(state.raw_inputs)

        console.print("[cyan]  Synthesizing research memo from all inputs…[/]")

        # If inputs are large, chunk them
        memo = self._synthesize_memo(client, consolidated)
        state.synthesized_memo = memo
        state.memo_text = memo  # this is what the downstream agents read

        return state

    def _build_consolidated_block(self, raw_inputs: list[RawInput]) -> str:
        parts: list[str] = []
        for inp in raw_inputs:
            header = f"{'='*60}\nFILE: {inp.file_name}  ({inp.file_type.upper()})\n{'='*60}"
            # Truncate very large files to avoid token overflow (keep first 8k chars)
            content = inp.content if len(inp.content) <= 8000 else inp.content[:8000] + "\n[... truncated ...]"
            parts.append(f"{header}\n{content}")
        return "\n\n".join(parts)

    def _synthesize_memo(self, client: openai.OpenAI, consolidated: str) -> str:
        # If the consolidated block is very large, split into two passes
        MAX_CHARS = 60_000

        if len(consolidated) <= MAX_CHARS:
            return self._call_claude(
                client=client,
                system=_SYSTEM,
                messages=[{
                    "role": "user",
                    "content": f"Here are all the research materials provided:\n\n{consolidated}",
                }],
                max_tokens=4096,
            )

        # Two-pass synthesis for large input sets
        midpoint = len(consolidated) // 2
        split = consolidated.rfind("\n", midpoint - 2000, midpoint + 2000)
        chunk_a = consolidated[:split]
        chunk_b = consolidated[split:]

        summary_a = self._call_claude(
            client=client,
            system=_CONSOLIDATION_SYSTEM,
            messages=[{"role": "user", "content": f"Research materials (part 1 of 2):\n\n{chunk_a}"}],
            max_tokens=2048,
        )
        summary_b = self._call_claude(
            client=client,
            system=_CONSOLIDATION_SYSTEM,
            messages=[{"role": "user", "content": f"Research materials (part 2 of 2):\n\n{chunk_b}"}],
            max_tokens=2048,
        )

        # Final merge
        return self._call_claude(
            client=client,
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": (
                    f"Partial summaries of research materials:\n\n"
                    f"[Part 1]\n{summary_a}\n\n[Part 2]\n{summary_b}\n\n"
                    f"Synthesize these into a single unified research memo."
                ),
            }],
            max_tokens=4096,
        )
