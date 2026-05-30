from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import anthropic
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agents.base import BaseAgent
from agents.proposal.alignment import AlignmentAgent
from agents.proposal.proposal_reviewer import ProposalReviewer
from agents.proposal.scout import ScoutAgent
from agents.research.topic_researcher import TopicResearcher
from agents.research.topic_reviewer import TopicReviewer
from agents.audit.fact_check import FactCheckAudit
from agents.audit.consistency import ConsistencyAudit
from agents.audit.benchmark import BenchmarkAudit
from agents.structure.structure_editorial import StructureEditorial
from agents.writing.section_writer import SectionWriter
from agents.writing.synthesis import SynthesisAgent
from agents.qa.fact_check_qa import FactCheckQA
from agents.qa.citation_auditor import CitationAuditor
from agents.qa.coherence_checker import CoherenceChecker
from agents.production.graph_generation import GraphGeneration
from agents.production.latex_formatter import LaTeXFormatter
from agents.production.appendix_assembler import AppendixAssembler
from agents.production.writing_review import WritingReview
from agents.production.layout_review import LayoutReview
from gates.gate_evaluator import GateEvaluator, MAX_CYCLES
from state.research_state import ResearchState, TopicOutput

console = Console()

_TOPIC_DECOMPOSE_SYSTEM = """\
You are the Director Agent. Given an approved research outline, decompose it into discrete \
research topics — one per key knowledge area that needs deep investigation.

Return ONLY a valid JSON array:
[
  {
    "id": "T-01",
    "title": "<topic title>",
    "description": "<what needs to be researched>",
    "section_ids": ["S-01", "S-02"],
    "domain": "<primary academic domain>"
  }
]

Each topic should be independently researchable. Aim for 3-8 topics total.
"""


class Director:
    """Orchestrates the full 7-phase research pipeline."""

    name = "Director"
    model = "claude-opus-4-7"

    def run(self, state: ResearchState, client: anthropic.Anthropic, state_path: Path) -> ResearchState:
        phases = [
            (0, self._run_phase_0),
            (1, self._run_phase_1),
            (2, self._run_phase_2),
            (3, self._run_phase_3),
            (4, self._run_phase_4),
            (5, self._run_phase_5),
            (6, self._run_phase_6),
        ]
        for phase_num, runner in phases:
            key = f"phase_{phase_num}"
            if getattr(state.phase_status, key) == "complete":
                console.print(f"[dim]Phase {phase_num} already complete — skipping[/]")
                continue
            console.rule(f"[bold blue]Phase {phase_num}[/]")
            state = runner(state, client)
            state.save(state_path)
            if getattr(state.phase_status, key) != "complete":
                console.print(f"[bold red]Phase {phase_num} did not complete. Pipeline halted.[/]")
                break
        return state

    # ──────────────────────────────────────────────────────────────────
    # Phase 0: Proposal Review
    # ──────────────────────────────────────────────────────────────────

    def _run_phase_0(self, state: ResearchState, client: anthropic.Anthropic) -> ResearchState:
        state.phase_status.phase_0 = "active"

        console.print("[cyan]Running Proposal Reviewer…[/]")
        state = ProposalReviewer().execute(state, client)

        console.print("[cyan]Running Scout Agent…[/]")
        state = ScoutAgent().execute(state, client)

        console.print("[cyan]Running Alignment Agent…[/]")
        state = AlignmentAgent().execute(state, client)

        approved, feedback = self._human_checkpoint_0(state)
        if not approved:
            if feedback:
                state.memo_text += f"\n\n[Revision notes from HC-0]: {feedback}"
            state.phase_status.phase_0 = "failed"
            return state

        state.phase_status.phase_0 = "complete"
        return state

    # ──────────────────────────────────────────────────────────────────
    # Phase 1: Research Lab
    # ──────────────────────────────────────────────────────────────────

    def _run_phase_1(self, state: ResearchState, client: anthropic.Anthropic) -> ResearchState:
        state.phase_status.phase_1 = "active"

        topics = self._decompose_into_topics(state, client)
        state.topic_tree = {"topics": topics}
        console.print(f"[cyan]Research Lab: {len(topics)} topics assigned[/]")

        def research_topic(topic: dict) -> TopicOutput:
            topic_id = topic["id"]
            researcher = TopicResearcher(topic_id=topic_id, topic=topic)
            reviewer = TopicReviewer(topic_id=topic_id)
            # Build a lightweight per-topic context slice
            topic_state = state.model_copy(deep=True)
            for cycle in range(MAX_CYCLES):
                topic_state = researcher.execute(topic_state, client)
                result = reviewer.check(topic_state, client)
                output = topic_state.get_topic(topic_id)
                if output and result.get("passed"):
                    output.status = "viable"
                    return output
                if output:
                    output.cycle_count = cycle + 1
            # Max cycles exceeded
            output = topic_state.get_topic(topic_id) or TopicOutput(topic_id=topic_id)
            output.status = "escalated"
            state.log_escalation(f"TopicResearcher-{topic_id}", "max cycles exceeded", "phase_1")
            return output

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(research_topic, t): t for t in topics}
            for future in as_completed(futures):
                output = future.result()
                existing = state.get_topic(output.topic_id)
                if existing:
                    idx = state.topic_outputs.index(existing)
                    state.topic_outputs[idx] = output
                else:
                    state.topic_outputs.append(output)
                console.print(f"  Topic {output.topic_id}: [{'green' if output.status == 'viable' else 'red'}]{output.status}[/]")

        gate = GateEvaluator.check_gate_1(state)
        if not gate.passed:
            console.print(f"[red]Gate 1 failed: {gate.reason}[/]")
            # Surgical routing: mark only failed topics for retry
            for tid in gate.failed_items:
                t = state.get_topic(tid)
                if t:
                    t.status = "failed"
            state.phase_status.phase_1 = "failed"
            return state

        state.phase_status.phase_1 = "complete"
        console.print(f"[green]Gate 1 passed: {gate.reason}[/]")
        return state

    # ──────────────────────────────────────────────────────────────────
    # Phase 2: Benchmark Audit
    # ──────────────────────────────────────────────────────────────────

    def _run_phase_2(self, state: ResearchState, client: anthropic.Anthropic) -> ResearchState:
        state.phase_status.phase_2 = "active"

        console.print("[cyan]Running Fact-Check Audit…[/]")
        state = FactCheckAudit().execute(state, client)
        console.print("[cyan]Running Consistency Audit…[/]")
        state = ConsistencyAudit().execute(state, client)
        console.print("[cyan]Running Benchmark Audit…[/]")
        state = BenchmarkAudit().execute(state, client)

        gate = GateEvaluator.check_gate_2(state)
        if not gate.passed:
            console.print(f"[red]Gate 2 failed: {gate.reason}[/]")
            state.phase_status.phase_2 = "failed"
            return state

        approved, feedback = self._human_checkpoint_1(state)
        if not approved:
            state.phase_status.phase_2 = "failed"
            return state

        state.phase_status.phase_2 = "complete"
        return state

    # ──────────────────────────────────────────────────────────────────
    # Phase 3: Structure
    # ──────────────────────────────────────────────────────────────────

    def _run_phase_3(self, state: ResearchState, client: anthropic.Anthropic) -> ResearchState:
        state.phase_status.phase_3 = "active"
        console.print("[cyan]Running Structure & Editorial Agent…[/]")
        state = StructureEditorial().execute(state, client)

        gate = GateEvaluator.check_gate_3(state)
        if not gate.passed:
            console.print(f"[red]Gate 3 failed: {gate.reason}[/]")
            state.phase_status.phase_3 = "failed"
            return state

        state.phase_status.phase_3 = "complete"
        console.print(f"[green]Gate 3 passed: {gate.reason}[/]")
        return state

    # ──────────────────────────────────────────────────────────────────
    # Phase 4: Writing
    # ──────────────────────────────────────────────────────────────────

    def _run_phase_4(self, state: ResearchState, client: anthropic.Anthropic) -> ResearchState:
        state.phase_status.phase_4 = "active"

        sections_to_write = [s for s in state.sections if s.status in ("pending", "contaminated")]
        console.print(f"[cyan]Writing {len(sections_to_write)} section(s) in parallel…[/]")

        def write_section(section_id: str) -> ResearchState:
            s = SectionWriter(section_id=section_id)
            return s.execute(state.model_copy(deep=True), client)

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(write_section, s.section_id): s for s in sections_to_write}
            for future in as_completed(futures):
                result = future.result()
                for updated in result.sections:
                    existing = state.get_section(updated.section_id)
                    if existing and updated.section_id in [s.section_id for s in sections_to_write]:
                        idx = state.sections.index(existing)
                        state.sections[idx] = updated

        console.print("[cyan]Running Synthesis Agent…[/]")
        state = SynthesisAgent().execute(state, client)

        gate = GateEvaluator.check_gate_4(state)
        if not gate.passed:
            console.print(f"[red]Gate 4 failed: {gate.reason}[/]")
            state.phase_status.phase_4 = "failed"
            return state

        state.phase_status.phase_4 = "complete"
        console.print(f"[green]Gate 4 passed: {gate.reason}[/]")
        return state

    # ──────────────────────────────────────────────────────────────────
    # Phase 5: QA / Audit
    # ──────────────────────────────────────────────────────────────────

    def _run_phase_5(self, state: ResearchState, client: anthropic.Anthropic) -> ResearchState:
        state.phase_status.phase_5 = "active"
        state.audit_findings.clear()

        console.print("[cyan]QA running in parallel: Fact-Check / Citation Auditor / Coherence Checker…[/]")

        def run_qa(agent: BaseAgent) -> ResearchState:
            return agent.execute(state.model_copy(deep=True), client)

        qa_agents = [FactCheckQA(), CitationAuditor(), CoherenceChecker()]
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(run_qa, a) for a in qa_agents]
            for future in as_completed(futures):
                result = future.result()
                state.audit_findings.extend(result.audit_findings)

        gate = GateEvaluator.check_gate_5(state)
        if not gate.passed:
            console.print(f"[red]Gate 5 failed: {gate.reason}[/]")
            # Cascade router: contaminate only affected sections
            for finding in state.audit_findings:
                if finding.severity == "critical" and finding.topic_id:
                    contaminated = state.contaminate_sections_from_topic(finding.topic_id)
                    if contaminated:
                        console.print(f"  Contaminated sections: {contaminated}")
            state.phase_status.phase_5 = "failed"
            return state

        state.phase_status.phase_5 = "complete"
        console.print(f"[green]Gate 5 passed: {gate.reason}[/]")
        return state

    # ──────────────────────────────────────────────────────────────────
    # Phase 6: Production
    # ──────────────────────────────────────────────────────────────────

    def _run_phase_6(self, state: ResearchState, client: anthropic.Anthropic) -> ResearchState:
        state.phase_status.phase_6 = "active"

        console.print("[cyan]Production running in parallel: Graphs / Formatter / Appendix…[/]")

        def run_prod(agent: BaseAgent) -> ResearchState:
            return agent.execute(state.model_copy(deep=True), client)

        prod_agents = [GraphGeneration(), LaTeXFormatter(), AppendixAssembler()]
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(run_prod, a) for a in prod_agents]
            for future in as_completed(futures):
                result = future.result()
                state.figures.extend(result.figures)
                state.appendix.extend(result.appendix)

        console.print("[cyan]Final review: Writing Review / Layout Review…[/]")

        def run_review(agent: BaseAgent) -> ResearchState:
            return agent.execute(state.model_copy(deep=True), client)

        review_agents = [WritingReview(), LayoutReview()]
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run_review, a) for a in review_agents]
            for future in as_completed(futures):
                result = future.result()
                state.human_checkpoints.update(result.human_checkpoints)

        gate = GateEvaluator.check_gate_6(state)
        if not gate.passed:
            console.print(f"[red]Gate 6 failed: {gate.reason}[/]")
            state.phase_status.phase_6 = "failed"
            return state

        state.phase_status.phase_6 = "complete"
        console.print(f"[green]Gate 6 passed — pipeline complete.[/]")
        return state

    # ──────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────

    def _decompose_into_topics(self, state: ResearchState, client: anthropic.Anthropic) -> list[dict]:
        kwargs: dict = {
            "model": self.model,
            "max_tokens": 4096,
            "thinking": {"type": "adaptive"},
            "system": _TOPIC_DECOMPOSE_SYSTEM,
            "messages": [{
                "role": "user",
                "content": (
                    f"Refined outline:\n{json.dumps(state.refined_outline, indent=2)}\n\n"
                    f"Scout recommended depth areas: {state.scout_report.get('recommended_depth_areas', [])}"
                ),
            }],
        }
        response = client.messages.create(**kwargs)
        text = next((b.text for b in response.content if hasattr(b, "type") and b.type == "text"), "[]")
        import re
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return [{"id": "T-01", "title": "Core Research", "description": "Full topic", "section_ids": [], "domain": "general"}]

    def _human_checkpoint_0(self, state: ResearchState) -> tuple[bool, str]:
        table = Table(title="Refined Outline", show_header=True, header_style="bold magenta")
        table.add_column("Section")
        table.add_column("Objective")
        for s in state.refined_outline.get("sections", []):
            table.add_row(s.get("title", ""), s.get("objective", ""))

        console.print(Panel(
            f"[bold]{state.refined_outline.get('title', 'Untitled')}[/]\n\n"
            f"{state.refined_outline.get('abstract_direction', '')}\n\n"
            f"Research questions: {state.refined_outline.get('research_questions', [])}",
            title="[bold orange1]HC-0: Outline Approval[/]",
            border_style="orange1",
        ))
        console.print(table)

        contradictions = state.scout_report.get("contradictions", [])
        if contradictions:
            console.print(f"\n[yellow]Scout flagged {len(contradictions)} contradiction(s) — resolved in outline.[/]")

        while True:
            choice = input("\n[HC-0] Approve outline? (yes / no / revise): ").strip().lower()
            if choice in ("yes", "y"):
                state.human_checkpoints["HC-0"] = {
                    "decision": "approved",
                    "timestamp": datetime.utcnow().isoformat(),
                }
                return True, ""
            if choice in ("no", "n"):
                state.human_checkpoints["HC-0"] = {"decision": "rejected"}
                return False, ""
            if choice == "revise":
                notes = input("Revision notes: ").strip()
                state.human_checkpoints["HC-0"] = {"decision": "revise", "feedback": notes}
                return False, notes
            console.print("[red]Enter yes, no, or revise[/]")

    def _human_checkpoint_1(self, state: ResearchState) -> tuple[bool, str]:
        criticals = [f for f in state.audit_findings if f.severity == "critical"]
        warnings = [f for f in state.audit_findings if f.severity == "warning"]
        minors = [f for f in state.audit_findings if f.severity == "minor"]

        table = Table(title="Audit Summary (ranked Critical → Minor)", show_header=True, header_style="bold red")
        table.add_column("Severity")
        table.add_column("Finding")
        table.add_column("Dimension")
        for f in criticals + warnings + minors:
            color = {"critical": "red", "warning": "yellow", "minor": "dim"}.get(f.severity, "white")
            table.add_row(f"[{color}]{f.severity}[/]", f.description[:80], f.dream_dimension or "")

        console.print(Panel(
            f"Critical: {len(criticals)}  |  Warning: {len(warnings)}  |  Minor: {len(minors)}\n\n"
            f"DREAM scores — "
            f"Presentation: {state.dream_scores.presentation_quality:.1f}  "
            f"Compliance: {state.dream_scores.task_compliance:.1f}  "
            f"Depth: {state.dream_scores.analytical_depth:.1f}  "
            f"Sources: {state.dream_scores.source_quality:.1f}",
            title="[bold orange1]HC-1: Audit Summary Approval[/]",
            border_style="orange1",
        ))
        console.print(table)

        while True:
            choice = input("\n[HC-1] Approve audit summary and proceed to writing? (yes / no / revise): ").strip().lower()
            if choice in ("yes", "y"):
                state.human_checkpoints["HC-1"] = {
                    "decision": "approved",
                    "timestamp": datetime.utcnow().isoformat(),
                }
                return True, ""
            if choice in ("no", "n"):
                state.human_checkpoints["HC-1"] = {"decision": "rejected"}
                return False, ""
            if choice == "revise":
                notes = input("Revision notes: ").strip()
                state.human_checkpoints["HC-1"] = {"decision": "revise", "feedback": notes}
                return False, notes
            console.print("[red]Enter yes, no, or revise[/]")
