from __future__ import annotations

from dataclasses import dataclass, field

from state.research_state import ResearchState

MAX_CYCLES = 5


@dataclass
class GateResult:
    passed: bool
    reason: str
    failed_items: list[str] = field(default_factory=list)


class GateEvaluator:

    @staticmethod
    def check_gate_1(state: ResearchState) -> GateResult:
        """All topics must reach viable status."""
        failed = [
            t.topic_id for t in state.topic_outputs
            if t.status not in ("viable",)
        ]
        if not state.topic_outputs:
            return GateResult(False, "No topic outputs produced", [])
        if failed:
            return GateResult(False, f"{len(failed)} topic(s) did not reach viability", failed)
        return GateResult(True, "All topics viable")

    @staticmethod
    def check_gate_2(state: ResearchState) -> GateResult:
        """No unresolved critical audit findings."""
        criticals = [
            f.finding_id for f in state.audit_findings
            if f.severity == "critical"
        ]
        if criticals:
            return GateResult(False, f"{len(criticals)} critical finding(s) require resolution", criticals)
        return GateResult(True, "Benchmark audit cleared")

    @staticmethod
    def check_gate_3(state: ResearchState) -> GateResult:
        """Section map must be locked with at least one section."""
        sections = state.section_map.get("sections", [])
        if not sections:
            return GateResult(False, "Section map is empty", [])
        return GateResult(True, f"Structure locked: {len(sections)} sections")

    @staticmethod
    def check_gate_4(state: ResearchState) -> GateResult:
        """All sections must have draft content."""
        incomplete = [
            s.section_id for s in state.sections
            if s.status == "pending" or not s.content.strip()
        ]
        if incomplete:
            return GateResult(False, f"{len(incomplete)} section(s) not drafted", incomplete)
        return GateResult(True, "All sections drafted")

    @staticmethod
    def check_gate_5(state: ResearchState) -> GateResult:
        """No critical QA findings; contaminated sections must be empty."""
        criticals = [
            f.finding_id for f in state.audit_findings
            if f.severity == "critical"
        ]
        contaminated = [
            s.section_id for s in state.sections
            if s.status == "contaminated"
        ]
        if criticals:
            return GateResult(False, f"{len(criticals)} critical QA finding(s)", criticals)
        if contaminated:
            return GateResult(False, f"{len(contaminated)} contaminated section(s)", contaminated)
        return GateResult(True, "QA cleared")

    @staticmethod
    def check_gate_6(state: ResearchState) -> GateResult:
        """Final review by both Writing Review and Layout Review agents must pass."""
        wr = state.human_checkpoints.get("writing_review", {})
        lr = state.human_checkpoints.get("layout_review", {})
        failed = []
        if wr.get("decision") != "approved":
            failed.append("writing_review")
        if lr.get("decision") != "approved":
            failed.append("layout_review")
        if failed:
            return GateResult(False, "Final review agents have not signed off", failed)
        return GateResult(True, "Final review passed")
