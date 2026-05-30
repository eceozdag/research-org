from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from rich.console import Console
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from agents.director.director import Director
from state.research_state import ResearchState

load_dotenv()
console = Console()

INPUT_DIR = Path("input")
OUTPUT_DIR = Path("output")
RUNS_DIR = Path("runs")

SUPPORTED_EXTENSIONS = {".md", ".txt"}


def run_pipeline(memo_path: Path) -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[bold red]ANTHROPIC_API_KEY not set. Add it to .env[/]")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    memo_text = memo_path.read_text(encoding="utf-8")

    state = ResearchState(memo_text=memo_text, memo_path=str(memo_path))

    state_path = RUNS_DIR / state.run_id / "state.json"
    RUNS_DIR.mkdir(exist_ok=True)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    console.rule(f"[bold green]Research Org — Run {state.run_id}[/]")
    console.print(f"Memo: [italic]{memo_path}[/]")
    console.print(f"State: [dim]{state_path}[/]\n")

    director = Director()
    state = director.run(state, client, state_path)

    # Write output
    if state.phase_status.phase_6 == "complete":
        latex_block = next((a for a in state.appendix if a.get("type") == "latex_source"), None)
        if latex_block:
            out_tex = OUTPUT_DIR / f"{state.run_id}.tex"
            out_tex.write_text(latex_block["content"])
            console.print(f"\n[bold green]✓ Output written: {out_tex}[/]")
        console.print(f"[bold green]✓ Run {state.run_id} complete.[/]")
    else:
        console.print(f"\n[yellow]Pipeline halted at phase: {state.phase_status}[/]")
        console.print(f"State saved to {state_path} — resume by rerunning with same run_id.")


def resume_pipeline(run_id: str) -> None:
    state_path = RUNS_DIR / run_id / "state.json"
    if not state_path.exists():
        console.print(f"[red]No state found for run {run_id}[/]")
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)

    state = ResearchState.load(state_path)
    console.rule(f"[bold yellow]Resuming Run {run_id}[/]")

    director = Director()
    state = director.run(state, client, state_path)

    if state.phase_status.phase_6 == "complete":
        latex_block = next((a for a in state.appendix if a.get("type") == "latex_source"), None)
        if latex_block:
            out_tex = OUTPUT_DIR / f"{run_id}.tex"
            out_tex.write_text(latex_block["content"])
            console.print(f"[bold green]✓ Output: {out_tex}[/]")


class MemoHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix in SUPPORTED_EXTENSIONS:
            console.print(f"\n[cyan]New memo detected: {path.name}[/]")
            time.sleep(0.5)  # brief wait for file write to complete
            run_pipeline(path)


def watch_mode() -> None:
    INPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    console.print(f"[bold]Watching [cyan]{INPUT_DIR}/[/] for new memos (.md, .txt)…[/]")
    console.print("Drop a memo file to start the pipeline. Ctrl+C to stop.\n")

    observer = Observer()
    observer.schedule(MemoHandler(), str(INPUT_DIR), recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    RUNS_DIR.mkdir(exist_ok=True)

    args = sys.argv[1:]

    if not args:
        watch_mode()
        return

    if args[0] == "run" and len(args) == 2:
        run_pipeline(Path(args[1]))
        return

    if args[0] == "resume" and len(args) == 2:
        resume_pipeline(args[1])
        return

    console.print("[bold]Usage:[/]")
    console.print("  python main.py                       # watch input/ folder")
    console.print("  python main.py run <memo.md>         # run a specific memo")
    console.print("  python main.py resume <run-id>       # resume a halted run")


if __name__ == "__main__":
    main()
