from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import openai
from dotenv import load_dotenv
from rich.console import Console
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from agents.director.director import Director
from agents.ingestion.file_parser import SUPPORTED
from state.research_state import ResearchState

load_dotenv()
console = Console()

INPUT_DIR = Path("input")
OUTPUT_DIR = Path("output")
RUNS_DIR = Path("runs")

MEMO_EXTENSIONS = {".md", ".txt"}


def _make_client() -> openai.OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        console.print("[bold red]OPENAI_API_KEY not set. Add it to .env[/]")
        sys.exit(1)
    return openai.OpenAI(api_key=api_key)


def _finish(state: ResearchState, state_path: Path) -> None:
    if state.phase_status.phase_6 == "complete":
        latex_block = next((a for a in state.appendix if a.get("type") == "latex_source"), None)
        if latex_block:
            OUTPUT_DIR.mkdir(exist_ok=True)
            out_tex = OUTPUT_DIR / f"{state.run_id}.tex"
            out_tex.write_text(latex_block["content"])
            console.print(f"\n[bold green]✓ Output: {out_tex}[/]")
        console.print(f"[bold green]✓ Run {state.run_id} complete.[/]")
    else:
        console.print(f"\n[yellow]Pipeline halted. State saved to {state_path}[/]")
        console.print(f"Resume with: python main.py resume {state.run_id}")


def run_folder(folder: Path) -> None:
    """Run the full pipeline starting from a folder of raw research materials."""
    client = _make_client()

    supported_files = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in SUPPORTED]
    memo_files = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in MEMO_EXTENSIONS]

    # If the folder contains only a single memo file and nothing else, treat as memo run
    if not supported_files and memo_files:
        run_memo(memo_files[0])
        return

    state = ResearchState(input_folder=str(folder.resolve()))
    state_path = RUNS_DIR / state.run_id / "state.json"
    RUNS_DIR.mkdir(exist_ok=True)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    console.rule(f"[bold green]Research Org — Run {state.run_id}[/]")
    console.print(f"Input folder: [italic]{folder}[/] ({len(supported_files)} file(s))")
    console.print(f"State: [dim]{state_path}[/]\n")

    director = Director()
    state = director.run(state, client, state_path)
    _finish(state, state_path)


def run_memo(memo_path: Path) -> None:
    """Run the pipeline from a single memo file (skips ingestion phase)."""
    client = _make_client()

    memo_text = memo_path.read_text(encoding="utf-8")
    state = ResearchState(
        memo_text=memo_text,
        memo_path=str(memo_path),
    )
    # Mark ingestion complete so Director skips it
    state.phase_status.ingestion = "complete"

    state_path = RUNS_DIR / state.run_id / "state.json"
    RUNS_DIR.mkdir(exist_ok=True)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    console.rule(f"[bold green]Research Org — Run {state.run_id}[/]")
    console.print(f"Memo: [italic]{memo_path}[/]")
    console.print(f"State: [dim]{state_path}[/]\n")

    director = Director()
    state = director.run(state, client, state_path)
    _finish(state, state_path)


def resume_pipeline(run_id: str) -> None:
    state_path = RUNS_DIR / run_id / "state.json"
    if not state_path.exists():
        console.print(f"[red]No state found for run {run_id}[/]")
        sys.exit(1)

    client = _make_client()
    state = ResearchState.load(state_path)
    console.rule(f"[bold yellow]Resuming Run {run_id}[/]")

    director = Director()
    state = director.run(state, client, state_path)
    _finish(state, state_path)


class InputFolderHandler(FileSystemEventHandler):
    """Watches for new folders dropped into input/."""

    def on_created(self, event):
        path = Path(event.src_path)
        time.sleep(1)  # allow file writes to settle

        if event.is_directory:
            console.print(f"\n[cyan]New input folder detected: {path.name}[/]")
            run_folder(path)
        elif path.suffix.lower() in MEMO_EXTENSIONS:
            console.print(f"\n[cyan]New memo detected: {path.name}[/]")
            run_memo(path)


def watch_mode() -> None:
    INPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    console.print(f"[bold]Watching [cyan]{INPUT_DIR}/[/] for new input folders or memo files…[/]")
    console.print("• Drop a [bold]folder[/] of materials (Excel, PDF, Word, images, notes) to trigger ingestion pipeline")
    console.print("• Drop a [bold].md or .txt[/] file to run from a memo directly")
    console.print("Ctrl+C to stop.\n")

    observer = Observer()
    observer.schedule(InputFolderHandler(), str(INPUT_DIR), recursive=False)
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
        target = Path(args[1])
        if target.is_dir():
            run_folder(target)
        else:
            run_memo(target)
        return

    if args[0] == "resume" and len(args) == 2:
        resume_pipeline(args[1])
        return

    console.print("[bold]Usage:[/]")
    console.print("  python main.py                            # watch input/ for folders/memos")
    console.print("  python main.py run <folder/>              # run from a folder of materials")
    console.print("  python main.py run <memo.md>              # run from a single memo file")
    console.print("  python main.py resume <run-id>            # resume a halted run")
    console.print()
    console.print("[bold]Supported input file types:[/]")
    console.print(f"  {', '.join(sorted(SUPPORTED))}")


if __name__ == "__main__":
    main()
