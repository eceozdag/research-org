from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field


class RawInput(BaseModel):
    file_name: str
    file_type: str  # xlsx, pdf, docx, md, txt, csv, image
    content: str    # extracted text / description
    metadata: dict = Field(default_factory=dict)


class SourceEntry(BaseModel):
    source_id: str
    url: str
    retrieved_by: str
    retrieved_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    content_hash: str = ""
    raw_excerpt: str = ""


class TopicNote(BaseModel):
    topic_id: str
    subtopic: str = ""
    partial_answer: str = ""
    confidence: float = 0.0
    conflicting_sources: list[str] = Field(default_factory=list)
    conflict_resolution: Literal["pending", "resolved", "escalated"] = "pending"


class Claim(BaseModel):
    claim_id: str
    text: str
    source_id: str
    sentence_offset: int = 0
    confidence: float = 1.0


class Section(BaseModel):
    section_id: str
    title: str
    content: str = ""
    status: Literal["pending", "draft", "qa_cleared", "contaminated"] = "pending"
    claims: list[Claim] = Field(default_factory=list)


class TopicOutput(BaseModel):
    topic_id: str
    title: str = ""
    status: Literal["pending", "viable", "failed", "escalated"] = "pending"
    cycle_count: int = 0
    content: str = ""
    experiments: dict = Field(default_factory=dict)
    viability_record: dict = Field(default_factory=dict)
    subqueries: list[str] = Field(default_factory=list)


class AuditFinding(BaseModel):
    finding_id: str
    severity: Literal["critical", "warning", "minor"]
    description: str
    topic_id: Optional[str] = None
    section_id: Optional[str] = None
    source_id: Optional[str] = None
    dream_dimension: Optional[str] = None


class DreamScores(BaseModel):
    presentation_quality: float = 0.0
    task_compliance: float = 0.0
    analytical_depth: float = 0.0
    source_quality: float = 0.0


class PhaseStatus(BaseModel):
    ingestion: Literal["pending", "active", "complete", "failed"] = "pending"
    phase_0: Literal["pending", "active", "complete", "failed"] = "pending"
    phase_1: Literal["pending", "active", "complete", "failed"] = "pending"
    phase_2: Literal["pending", "active", "complete", "failed"] = "pending"
    phase_3: Literal["pending", "active", "complete", "failed"] = "pending"
    phase_4: Literal["pending", "active", "complete", "failed"] = "pending"
    phase_5: Literal["pending", "active", "complete", "failed"] = "pending"
    phase_6: Literal["pending", "active", "complete", "failed"] = "pending"


class ResearchState(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    input_folder: str = ""           # path to folder of raw materials
    memo_text: str = ""              # final memo (synthesized or user-provided)
    memo_path: str = ""
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    # Ingestion phase
    raw_inputs: list[RawInput] = Field(default_factory=list)
    synthesized_memo: str = ""
    preliminary_outline: dict = Field(default_factory=dict)

    # Phase 0
    proposal_review: dict = Field(default_factory=dict)
    scout_report: dict = Field(default_factory=dict)
    refined_outline: dict = Field(default_factory=dict)

    # Phase 1
    topic_tree: dict = Field(default_factory=dict)
    source_registry: list[SourceEntry] = Field(default_factory=list)
    topic_notes: list[TopicNote] = Field(default_factory=list)
    topic_outputs: list[TopicOutput] = Field(default_factory=list)

    # Phase 2
    claim_provenance_map: dict = Field(default_factory=dict)
    benchmark_report: dict = Field(default_factory=dict)
    audit_summary: dict = Field(default_factory=dict)
    dream_scores: DreamScores = Field(default_factory=DreamScores)
    audit_findings: list[AuditFinding] = Field(default_factory=list)

    # Phases 3–6
    section_map: dict = Field(default_factory=dict)
    sections: list[Section] = Field(default_factory=list)
    figures: list[dict] = Field(default_factory=list)
    appendix: list[dict] = Field(default_factory=list)

    phase_status: PhaseStatus = Field(default_factory=PhaseStatus)
    escalation_log: list[dict] = Field(default_factory=list)
    context_health: dict = Field(default_factory=dict)
    human_checkpoints: dict = Field(default_factory=dict)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, path: Path) -> ResearchState:
        return cls.model_validate_json(path.read_text())

    def add_source(self, url: str, retrieved_by: str, raw_excerpt: str = "") -> str:
        source_id = f"SR-{len(self.source_registry) + 1:03d}"
        self.source_registry.append(SourceEntry(
            source_id=source_id,
            url=url,
            retrieved_by=retrieved_by,
            content_hash=hashlib.md5(raw_excerpt.encode()).hexdigest(),
            raw_excerpt=raw_excerpt,
        ))
        return source_id

    def log_escalation(self, agent: str, reason: str, phase: str) -> None:
        self.escalation_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "agent": agent,
            "phase": phase,
            "reason": reason,
        })

    def get_topic(self, topic_id: str) -> Optional[TopicOutput]:
        return next((t for t in self.topic_outputs if t.topic_id == topic_id), None)

    def get_section(self, section_id: str) -> Optional[Section]:
        return next((s for s in self.sections if s.section_id == section_id), None)

    def contaminate_sections_from_topic(self, topic_id: str) -> list[str]:
        contaminated = []
        for section in self.sections:
            if any(c.source_id.startswith(topic_id) for c in section.claims):
                section.status = "contaminated"
                contaminated.append(section.section_id)
        return contaminated
