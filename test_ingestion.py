"""
Test script: runs ingestion phase only (no human checkpoints).
Shows synthesized memo + preliminary outline so you can verify
the pipeline correctly captured your input materials.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import openai
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from agents.ingestion.input_receiver import InputReceiverAgent
from agents.ingestion.preliminary_outline import PreliminaryOutlineAgent
from state.research_state import ResearchState

load_dotenv()
console = Console()


def main():
    input_folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("input/Orbital Data Center")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        console.print("[red]OPENAI_API_KEY not set[/]")
        sys.exit(1)

    client = openai.OpenAI(api_key=api_key)
    state = ResearchState(input_folder=str(input_folder.resolve()))

    RUNS_DIR = Path("runs")
    state_path = RUNS_DIR / state.run_id / "state.json"
    RUNS_DIR.mkdir(exist_ok=True)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    console.rule(f"[bold green]Ingestion Test — Run {state.run_id}[/]")
    console.print(f"Input: [italic]{input_folder}[/]\n")

    # ── Step 1: Input Receiver ──────────────────────────────────────────
    console.rule("[cyan]Step 1: Input Receiver[/]")
    state = InputReceiverAgent().execute(state, client)

    console.print(f"\n[green]✓ Parsed {len(state.raw_inputs)} file(s)[/]")
    for inp in state.raw_inputs:
        console.print(f"  • {inp.file_name} ({inp.file_type}) — {len(inp.content):,} chars extracted")

    console.print(Panel(
        state.synthesized_memo,
        title="[bold]Synthesized Research Memo[/]",
        border_style="blue",
    ))

    # ── Step 2: Preliminary Outline ─────────────────────────────────────
    console.rule("[cyan]Step 2: Preliminary Outline[/]")
    state = PreliminaryOutlineAgent().execute(state, client)

    outline = state.preliminary_outline
    console.print(f"\n[bold]Title:[/] {outline.get('title', '—')}")
    console.print(f"[bold]Thesis:[/] {outline.get('thesis', '—')}\n")

    console.print("[bold]Research Questions:[/]")
    for rq in outline.get("research_questions", []):
        console.print(f"  • {rq}")

    console.print("\n[bold]Proposed Sections:[/]")
    for s in outline.get("sections", []):
        completeness = s.get("completeness", "?")
        color = {"rich": "green", "partial": "yellow", "gap": "red"}.get(completeness, "white")
        console.print(
            f"  [{s['section_id']}] {s['title']} "
            f"[{color}]({completeness})[/] — {s.get('estimated_pages', '?')}p"
        )
        if s.get("existing_material"):
            console.print(f"       {s['existing_material'][:100]}")

    if outline.get("data_assets"):
        console.print("\n[bold]Data Assets Identified:[/]")
        for asset in outline.get("data_assets", []):
            console.print(f"  • [{asset.get('file', '?')}] {asset.get('key_value', '')} → {asset.get('used_in_section', '?')}")

    if outline.get("gaps_identified"):
        console.print("\n[bold yellow]Gaps to fill in research:[/]")
        for gap in outline.get("gaps_identified", []):
            console.print(f"  ! {gap}")

    # ── Save state ──────────────────────────────────────────────────────
    state.phase_status.ingestion = "complete"
    state.save(state_path)

    console.rule("[bold green]Ingestion test complete[/]")
    console.print(f"\nRun ID: [bold]{state.run_id}[/]")
    console.print(f"State saved: [dim]{state_path}[/]")
    console.print(
        f"\nTo run the full pipeline from here:\n"
        f"  [bold]python main.py resume {state.run_id}[/]"
    )


if __name__ == "__main__":
    main()
