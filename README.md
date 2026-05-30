# Agentic Research Organization

A multi-agent pipeline that converts a rough research memo into a publication-grade scientific white paper — complete with Vancouver-style citations, custom figures, appendix, and LaTeX/Prism-compatible output.

---

## How It Works

A sloppy prose memo drops into a watch folder. The Director Agent orchestrates 21 fixed agents (plus dynamically spawned domain experts) through 7 sequential phases, 6 hard QA gates, and 2 human checkpoints. Nothing moves forward until the gate signs off.

```mermaid
flowchart TD
    INPUT([📄 Research Memo\nWatch Folder]) --> P0

    subgraph P0["Phase 0 — Proposal Review"]
        PR[Proposal Reviewer] --> SC[Scout Agent]
        SC --> AL[Alignment Agent]
    end

    P0 --> HC0{{"🧑 HC-0\nOutline Approval"}}
    HC0 -->|Approved| P1
    HC0 -->|Revise| AL

    subgraph P1["Phase 1 — Research Lab"]
        direction TB
        DIR[Director Agent] --> TR1[Topic Researcher\n+ Domain Expert]
        DIR --> TR2[Topic Researcher\n+ Domain Expert]
        DIR --> TR3[Topic Researcher\n+ Domain Expert]
        TR1 --> REV1[Topic Reviewer]
        TR2 --> REV2[Topic Reviewer]
        TR3 --> REV3[Topic Reviewer]
    end

    P1 --> G1{{"⛔ Gate 1\nViability"}}
    G1 -->|Pass| P2
    G1 -->|Fail| P1

    subgraph P2["Phase 2 — Benchmark Audit"]
        FC1[Fact-Check Agent] --> CON[Consistency Agent]
        CON --> BEN[Benchmark Agent]
    end

    P2 --> G2{{"⛔ Gate 2\nAudit"}}
    G2 --> HC1{{"🧑 HC-1\nAudit Summary\nApproval"}}
    HC1 -->|Approved| P3
    HC1 -->|Revise| P1

    subgraph P3["Phase 3 — Structure"]
        SE[Structure &\nEditorial Agent]
    end

    P3 --> G3{{"⛔ Gate 3\nOutline Lock"}}
    G3 -->|Pass| P4

    subgraph P4["Phase 4 — Writing  (parallel)"]
        SW1[Section Writer 1]
        SW2[Section Writer 2]
        SW3[Section Writer N]
        SYN[Synthesis Agent]
        SW1 & SW2 & SW3 --> SYN
    end

    P4 --> G4{{"⛔ Gate 4\nDraft Complete"}}
    G4 -->|Pass| P5

    subgraph P5["Phase 5 — QA / Audit"]
        FACT[Fact-Check Agent] & CITE[Citation Auditor] & COH[Coherence Checker]
    end

    P5 --> G5{{"⛔ Gate 5\nQA Sign-off"}}
    G5 -->|Pass| P6
    G5 -->|Fail| P4

    subgraph P6["Phase 6 — Production  (parallel)"]
        GG[Graph Generation\nAgent]
        FMT[LaTeX / Prism\nFormatter]
        APP[Appendix\nAssembler]
        WR[Writing\nReview Agent]
        LR[Layout\nReview Agent]
        GG & FMT & APP --> WR & LR
    end

    P6 --> G6{{"⛔ Gate 6\nFinal Review"}}
    G6 -->|Pass| OUTPUT
    G6 -->|Fail| P6

    OUTPUT([📑 paper.tex / paper.pdf\nAPI Delivery])

    style HC0 fill:#f5a623,color:#000
    style HC1 fill:#f5a623,color:#000
    style G1 fill:#d0021b,color:#fff
    style G2 fill:#d0021b,color:#fff
    style G3 fill:#d0021b,color:#fff
    style G4 fill:#d0021b,color:#fff
    style G5 fill:#d0021b,color:#fff
    style G6 fill:#d0021b,color:#fff
    style INPUT fill:#417505,color:#fff
    style OUTPUT fill:#417505,color:#fff
```

---

## Phase Breakdown

### Phase 0 — Proposal Review

The system reads the memo before committing any research effort. Three agents validate it in sequence.

```mermaid
flowchart LR
    MEMO([Memo]) --> PR

    PR["**Proposal Reviewer**\nReads memo, scores:\n• Clarity\n• Scope feasibility\n• Missing context"] --> SC

    SC["**Scout Agent**\nInitial literature scan:\n• Existing body of research\n• Contradictions vs. memo claims\n• Gap identification"] --> AL

    AL["**Alignment Agent**\nRevises outline until:\n• Aligned with existing facts\n• Gaps addressed\n• Scope confirmed feasible"] --> OUTLINE([Draft Outline\n→ HC-0])
```

**Human Checkpoint 0** — Human approves or rejects the outline before any research begins. Rejection routes back to Alignment Agent.

---

### Phase 1 — Research Lab

The Director decomposes the approved outline into topics, spawns one Topic Researcher + Domain Expert per topic, and runs them in parallel. Each researcher runs three experiment types and must pass a viability check before their output is accepted.

```mermaid
flowchart TD
    OUTLINE([Approved Outline]) --> DIR

    DIR["**Director Agent**\nDecomposes outline → topic tree\nAssigns agents per topic\nMonitors cycle count"] --> SPAWN

    SPAWN["Topic assignment\n(parallel)"]

    SPAWN --> LOOP1
    SPAWN --> LOOP2
    SPAWN --> LOOP3

    subgraph LOOP1["Topic A"]
        TR_A["**Topic Researcher**\n+ Domain Expert\n─────────────────\n① Adversarial hypothesis test\n② Multi-source triangulation ≥3\n③ Quantitative replication\n─────────────────\nSubquery decomposition\nDual search: semantic + BM25\nConflict flags → topic_notes\nSelf-reflection before submit"]
        REV_A["**Topic Reviewer**\nViability check:\n• Evidential sufficiency\n• Methodological soundness\n• Novelty / contribution"]
        TR_A -->|Submit| REV_A
        REV_A -->|Fail, cycle ≤5| TR_A
        REV_A -->|Fail, cycle >5| ESC_A([Escalate\nto Human])
    end

    subgraph LOOP2["Topic B"]
        TR_B[Topic Researcher] --> REV_B[Topic Reviewer]
        REV_B -->|Fail| TR_B
    end

    subgraph LOOP3["Topic N"]
        TR_N[Topic Researcher] --> REV_N[Topic Reviewer]
        REV_N -->|Fail| TR_N
    end

    REV_A & REV_B & REV_N -->|Pass| G1{{"⛔ Gate 1\nAll topics viable?"}}
    G1 -->|Yes| BENCH([→ Phase 2])
    G1 -->|No| DIR
```

---

### Phase 2 — Benchmark Audit

Independent of the researchers who produced the content, three audit agents verify every claim against external benchmarks and each other.

```mermaid
flowchart LR
    IN([Topic Outputs\n+ SourceRegistry]) --> FC

    FC["**Fact-Check Agent**\nVerifies each claim:\n• 3-dim citation check\n  (Link Works / Relevant / Fact)\n• SourceRegistry match\n• Sentence-level tracing"] --> CO

    CO["**Consistency Agent**\nInternal consistency matrix:\n• Cross-topic contradiction check\n• Claim provenance map\n• Cascade contamination detection"] --> BE

    BE["**Benchmark Agent**\nExternal baseline comparison:\n• Quantitative data baselines\n• Prior versions / related papers\n• Novelty delta scoring"] --> AUDIT([Ranked Audit Summary\nCritical → Warning → Minor\n× 4 DREAM dimensions\n→ HC-1])
```

**Human Checkpoint 1** — Human reviews the ranked audit summary (most critical finding to least, scored on Presentation / Task Compliance / Analytical Depth / Source Quality). Approval unlocks writing. Rejection routes back to Phase 1 with targeted repair instructions.

---

### Phase 4 — Writing (Parallel)

Section Writers are read-only agents — no web search, no source retrieval. They compose from ResearchState only, attaching `source_id` + `sentence_offset` to every claim.

```mermaid
flowchart TD
    STRUCT([Locked Section Map]) --> SW

    SW["Section Writers\n(one per section, parallel)\n─────────────────────\nEach writer:\n• Reads assigned topic outputs\n• Writes section prose\n• Anchors every claim:\n  source_id + sentence_offset\n• Flags uncertain claims\n  with confidence score"]

    SW --> S1[Section 1\n+ claim anchors]
    SW --> S2[Section 2\n+ claim anchors]
    SW --> SN[Section N\n+ claim anchors]

    S1 & S2 & SN --> SYN

    SYN["**Synthesis Agent**\nMerges sections into coherent draft:\n• Cross-section flow\n• Removes duplicates\n• Validates internal references\n• Resolves cross-section conflicts"]

    SYN --> DRAFT([Full Draft → Gate 4])
```

---

### Phase 5 — QA / Audit

Three agents run in parallel against the full draft. Any Critical finding blocks Gate 5 and routes only the contaminated sections (not the whole paper) back to Phase 4.

```mermaid
flowchart LR
    DRAFT([Full Draft\n+ claim anchors\n+ SourceRegistry]) --> QA

    subgraph QA["QA — parallel"]
        FC2["**Fact-Check Agent**\nVerifies every claim anchor:\n• SourceRegistry match\n• 3-dim citation check\n• Table/figure data extraction\n• Cascade contamination trace"]
        CA["**Citation Auditor**\nVancouver [n] format\nSentence-level accuracy\nOrphan citation detection\nBroken link detection"]
        CC["**Coherence Checker**\nArgument flow\nTerminology consistency\nSection-to-section logic\nAbstract ↔ conclusion match"]
    end

    QA --> AUD([Audit Report\nCritical / Warning / Minor\n→ Gate 5])

    AUD -->|Critical| ROUTE["Cascade router:\nmark contaminated sections\nonly those sections\nreturn to Phase 4"]
    AUD -->|Clear| PROD([→ Phase 6])
```

---

### Phase 6 — Production (Parallel)

All production and final review agents run in parallel. Gate 6 requires both the Writing Review Agent and Layout Review Agent to sign off.

```mermaid
flowchart TD
    IN([QA-Cleared Draft\n+ Figures spec\n+ Appendix content]) --> PROD

    subgraph PROD["Production — parallel"]
        GG["**Graph Generation Agent**\nTime-series charts\nComparison tables / heatmaps\nSystem architecture diagrams\nGeospatial maps"]
        FMT["**LaTeX / Prism Formatter**\nSection typesetting\nVancouver bibliography\nFigure placement\nCross-reference linking"]
        APP["**Appendix Assembler**\nData tables\nMethodology details\nSupplementary figures\nRaw citation list"]
    end

    GG & FMT & APP --> REVIEW

    subgraph REVIEW["Final Review — parallel"]
        WR["**Writing Review Agent**\nCitation completeness\nProse quality\nClaim–citation alignment\nSection completeness"]
        LR["**Layout Review Agent**\nFigure numbering\nTable formatting\nPage structure\nLaTeX / Prism compliance"]
    end

    REVIEW --> G6{{"⛔ Gate 6\nBoth agents sign off?"}}
    G6 -->|Pass| OUT([paper.tex + paper.pdf\nAPI Delivery])
    G6 -->|Fail| PROD
```

---

## Agent Roster

| # | Agent | Division | Role |
|---|---|---|---|
| 1 | Director Agent | Command | Orchestrator — decomposes outline, assigns agents, routes failures, monitors cycle counts |
| 2 | Proposal Reviewer | Proposal | Scores memo clarity, scope feasibility, missing context |
| 3 | Scout Agent | Proposal | Initial literature scan — existing body of research, contradiction flags |
| 4 | Alignment Agent | Proposal | Revises outline until aligned with existing facts and confirmed feasible |
| 5 | Topic Researcher | Research Lab | Per-topic: subquery decomposition, dual search, 3 experiments, conflict notes |
| 6 | Domain Expert | Research Lab | Dynamically spawned per topic — specialist knowledge injection |
| 7 | Topic Reviewer | Research Lab | Per-topic viability check: evidential sufficiency, methodology, novelty |
| 8 | Fact-Check Agent (P2) | Benchmark Audit | External claim verification, SourceRegistry citation check |
| 9 | Consistency Agent | Benchmark Audit | Cross-topic contradiction, claim provenance mapping |
| 10 | Benchmark Agent | Benchmark Audit | Quantitative baseline comparison, prior-work delta scoring |
| 11 | Structure & Editorial | Structure | Locks section map, defines section assignments for writers |
| 12 | Section Writer (×N) | Writing | Per-section prose, read-only, sentence-level claim anchoring |
| 13 | Synthesis Agent | Writing | Merges parallel sections into coherent draft |
| 14 | Fact-Check Agent (P5) | QA | Draft claim verification, cascade contamination trace |
| 15 | Citation Auditor | QA | Vancouver [n] format, sentence-level accuracy, orphan detection |
| 16 | Coherence Checker | QA | Argument flow, terminology consistency, abstract ↔ conclusion match |
| 17 | Graph Generation Agent | Production | Time-series, heatmaps, architecture diagrams, geospatial maps |
| 18 | LaTeX/Prism Formatter | Production | Full typesetting, bibliography, figure placement, cross-references |
| 19 | Appendix Assembler | Production | Data tables, methodology details, supplementary figures |
| 20 | Writing Review Agent | Final Review | Citation completeness, prose quality, claim–citation alignment |
| 21 | Layout Review Agent | Final Review | Figure numbering, table formatting, LaTeX/Prism structural compliance |

Plus: dynamically spawned **Domain Experts** and **Topic Reviewers** — one pair per research topic.

---

## ResearchState Schema

All agents read and write through a single shared state object. No agent communicates with another agent directly.

```json
{
  "proposal_review": {
    "memo_text": "",
    "clarity_score": 0,
    "feasibility_score": 0,
    "missing_context": []
  },
  "scout_report": {
    "existing_body": [],
    "contradictions": [],
    "gaps": []
  },
  "refined_outline": {
    "sections": [],
    "approved_at": null,
    "approved_by": "human"
  },
  "topic_tree": {
    "topics": []
  },
  "source_registry": [
    {
      "source_id": "SR-001",
      "url": "",
      "retrieved_by": "",
      "retrieved_at": "",
      "content_hash": "",
      "raw_excerpt": ""
    }
  ],
  "topic_notes": [
    {
      "topic_id": "T-01",
      "subtopic": "",
      "partial_answer": "",
      "confidence": 0.0,
      "conflicting_sources": [],
      "conflict_resolution": "pending"
    }
  ],
  "topic_outputs": [
    {
      "topic_id": "T-01",
      "status": "pending | viable | failed | escalated",
      "cycle_count": 0,
      "content": "",
      "viability_record": {}
    }
  ],
  "claim_provenance_map": {
    "claim_id": {
      "topic_id": "",
      "source_id": "",
      "sentence_offset": 0,
      "confidence": 0.0
    }
  },
  "benchmark_report": {
    "findings": [],
    "dream_scores": {
      "presentation_quality": 0,
      "task_compliance": 0,
      "analytical_depth": 0,
      "source_quality": 0
    }
  },
  "audit_summary": {
    "critical": [],
    "warning": [],
    "minor": [],
    "approved_at": null,
    "approved_by": "human"
  },
  "section_map": {
    "sections": []
  },
  "sections": [
    {
      "section_id": "S-01",
      "title": "",
      "content": "",
      "status": "pending | draft | qa_cleared | contaminated",
      "claims": [
        {
          "claim_id": "C-001",
          "text": "",
          "source_id": "SR-001",
          "sentence_offset": 0,
          "confidence": 0.0
        }
      ]
    }
  ],
  "figures": [],
  "appendix": [],
  "phase_status": {
    "phase_0": "pending | active | complete | failed",
    "phase_1": "pending",
    "phase_2": "pending",
    "phase_3": "pending",
    "phase_4": "pending",
    "phase_5": "pending",
    "phase_6": "pending"
  },
  "escalation_log": [],
  "context_health": {
    "last_checked": null,
    "agents_over_80pct": []
  }
}
```

---

## Gate Conditions

| Gate | Condition to Pass | On Fail |
|---|---|---|
| HC-0 | Human approves refined outline | Routes back to Alignment Agent |
| Gate 1 | All topics pass viability (3 criteria) | Director routes only failing topics back to their Topic Researcher |
| Gate 2 | Benchmark Audit has zero Critical findings **or** all Criticals have approved resolutions | Routes failing topics back to Phase 1 |
| HC-1 | Human approves ranked audit summary | Director routes flagged topics back to Phase 1 with repair instructions |
| Gate 3 | Structural outline locked and complete | Routes back to Structure Agent |
| Gate 4 | All sections drafted with claim anchors | Routes incomplete sections back to Section Writers |
| Gate 5 | Zero Critical findings across all three QA agents | Cascade router returns only contaminated sections to Phase 4 |
| Gate 6 | Writing Review + Layout Review both sign off | Routes only failing components back to Production |

**Max revision cycles:** 5 per agent per phase before automatic escalation to human.

---

## Citation Standard

All citations use **Vancouver numbered inline style** `[n]`.

Citation Auditor runs a 3-dimensional check per citation:
1. **Link Works** — URL accessible, content matches expected source
2. **Relevant Content** — source topically supports the claim
3. **Fact Check** — source factually supports the exact claim text

Any citation not traceable to a `source_id` in the SourceRegistry is a Critical audit finding.

---

## Output

The pipeline delivers two files via API:
- `paper.tex` — LaTeX source, Vancouver bibliography, all figures embedded
- `paper.pdf` — compiled output

Both are compatible with **OpenAI Prism** (LaTeX-alternative scientific paper format).

---

## Stack

- **Runtime:** Claude Code subagents (Anthropic SDK, Python)
- **Orchestration:** Director Agent with shared ResearchState JSON
- **Input trigger:** Folder watch on `./input/` for `.md` / `.txt` memo files
- **Output delivery:** LaTeX/Prism file via platform API
- **Models:** Claude Opus 4.7 (Director, QA agents), Claude Sonnet 4.6 (Section Writers, production agents)

---

## Directory Structure

```
research-org/
├── README.md
├── state/
│   └── research_state_schema.json
├── agents/
│   ├── director/
│   ├── proposal/
│   │   ├── proposal_reviewer.py
│   │   ├── scout.py
│   │   └── alignment.py
│   ├── research/
│   │   ├── topic_researcher.py
│   │   ├── domain_expert.py
│   │   └── topic_reviewer.py
│   ├── audit/
│   │   ├── fact_check.py
│   │   ├── consistency.py
│   │   └── benchmark.py
│   ├── structure/
│   │   └── structure_editorial.py
│   ├── writing/
│   │   ├── section_writer.py
│   │   └── synthesis.py
│   ├── qa/
│   │   ├── fact_check_qa.py
│   │   ├── citation_auditor.py
│   │   └── coherence_checker.py
│   └── production/
│       ├── graph_generation.py
│       ├── latex_formatter.py
│       ├── appendix_assembler.py
│       ├── writing_review.py
│       └── layout_review.py
├── gates/
│   └── gate_evaluator.py
├── input/
│   └── .gitkeep
└── output/
    └── .gitkeep
```
