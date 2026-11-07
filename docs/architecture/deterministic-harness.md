# Deterministic State Machine & Prompt on Demand Harness

This document outlines the architecture, data schemas, verification gates, and execution protocol for the `TeamAgents` harness.

---

## 🏛️ Architecture Overview

The system strictly decouples the **Deterministic Control Plane** from the **Probabilistic Data Plane**:

```
[Sub-Agent A: Coder]
       │
       ▼ (1. Structured Output: e.g. pop_task / request_review with Artifacts)
┌────────────────────────────────────────────────────────┐
│            Deterministic State Machine (Harness)        │
│  - Records persistent state in stack.json              │
│  - Executes Pre-Handoff Fast Gate (Syntax & Existence) │
│  - Enforces Deterministic State Transition Matrix      │
│  - Selects Next Agent deterministically                │
└────────────────────────────────────────────────────────┘
       │
       ▼ (2. Top of Stack + Relevant Unified Git Diff)
┌────────────────────────────────────────────────────────┐
│               Prompt on Demand Builder                 │
│  - Loads Agent B Template from .agents/skills/         │
│  - Injects latest context Just-In-Time (JIT)           │
│  - Inforces Zero-Test & Anti-Hallucination directives  │
└────────────────────────────────────────────────────────┘
       │
       ▼ (3. Clean Prompt with zero conversational bloat)
[Sub-Agent B: Reviewer / QA] (Probabilistic Reasoning)
```

---

## 📦 Components & Modules

| Module | File | Role |
| :--- | :--- | :--- |
| **Schemas** | [`harness/schemas.py`](file:///home/deaw/Projects/TeamAgents/harness/schemas.py) | Pydantic-style dataclasses for `TaskFrame`, `StructuredOutput`, `SystemState`, and `TaskBudget`. |
| **Stack Manager** | [`harness/task_stack.py`](file:///home/deaw/Projects/TeamAgents/harness/task_stack.py) | Atomic file manager for `stack.json`. Supports `push`, `pop`, `peek`, and hierarchical parent-child tracking. |
| **Sanitizer** | [`harness/sanitizer.py`](file:///home/deaw/Projects/TeamAgents/harness/sanitizer.py) | Deterministic JSON block extractor and syntax repairer (zero token consumption). |
| **Verifier Gate** | [`harness/verifier.py`](file:///home/deaw/Projects/TeamAgents/harness/verifier.py) | Ground-truth verification: checks physical existence of files and compiles Python/JSON syntax. |
| **Delta Extractor** | [`harness/git_diff.py`](file:///home/deaw/Projects/TeamAgents/harness/git_diff.py) | Unified git diff extractor for modified artifacts to prune tokens. |
| **JIT Prompt Builder** | [`harness/prompt_builder.py`](file:///home/deaw/Projects/TeamAgents/harness/prompt_builder.py) | Just-In-Time prompt assembler combining persona, task, diff, and output schema. |
| **State Machine** | [`harness/state_machine.py`](file:///home/deaw/Projects/TeamAgents/harness/state_machine.py) | FSM engine enforcing transitions, circuit breakers, and handoffs. |
| **CLI Tool** | [`harness/cli.py`](file:///home/deaw/Projects/TeamAgents/harness/cli.py) | Command-line management tool for initializing, advancing, and inspecting the harness. |

---

## 📋 Data Contract: `stack.json`

The persistent state is maintained in `stack.json` using atomic temporary file swaps:

```json
{
  "session_id": "sess-4df4fbba",
  "current_state": "CODING",
  "stack_depth": 2,
  "stack": [
    {
      "task_id": "ROOT-001",
      "parent_id": null,
      "title": "Build Auth System",
      "description": "User authentication module",
      "assigned_agent": "pm_agent",
      "status": "IN_PROGRESS",
      "artifacts": [],
      "budget": {
        "max_tokens": 15000,
        "used_tokens": 1200,
        "max_retries": 2,
        "current_retries": 0
      }
    },
    {
      "task_id": "SUBTASK-001",
      "parent_id": "ROOT-001",
      "title": "Implement JWT Route",
      "description": "Create route in src/auth.py",
      "assigned_agent": "backend_agent",
      "status": "PENDING",
      "artifacts": ["src/auth.py"],
      "budget": {
        "max_tokens": 15000,
        "used_tokens": 0,
        "max_retries": 2,
        "current_retries": 0
      }
    }
  ],
  "history": []
}
```

---

## ⚡ CLI Usage Guide

```bash
# 1. Initialize a new root task with Strict Mode and file boundary
python3 -m harness.cli --strict-level strict init --task-id ROOT-001 --title "Implement Payment API" --agent pm_agent --allowed-files docs/PRD.md

# 2. Check current active state, allowed files, and Top of Stack
python3 -m harness.cli status

# 3. Build Prompt on Demand (injects Strict Banner and constraints)
python3 -m harness.cli build-prompt

# 4. Advance state machine with agent's structured output (enforces boundaries & brevity)
python3 -m harness.cli transition --input '{"action": "pop_task", "status": "completed", "summary": "Done"}'

# 5. Verify current artifacts locally (zero tokens)
python3 -m harness.cli verify

# 6. Inspect full task stack, history, and verification receipts
python3 -m harness.cli inspect-stack
```

---

## 🚨 Strict / Opinionated Mode (The 4 Iron Rules)

When `--strict-level strict` (default) or `hardcore` is enabled, the harness mechanically enforces four rules:

### 1. 🛡️ Hyper-Disciplined Stack Hygiene
- **Rule**: Agents are strictly forbidden from modifying or creating files outside `allowed_files` on the active task frame.
- **Enforcement**: Harness inspects `git status --porcelain`. Any touched file outside `allowed_files` triggers an immediate transition rejection without invoking downstream agents.
- **Escape Hatch**: If a prerequisite file needs modification, the agent must use `action: push_task` to declare a subtask with its own dedicated `allowed_files`.

### 2. ⚛️ Atomic Decomposition
- **Rule**: Complex features must be broken down into atomic steps (interfaces -> schemas -> implementations).
- **Enforcement**: Harness checks blast radius via `git diff --numstat`. Modifications exceeding the line threshold (default: 200 lines) are blocked in hardcore mode or flagged for subtask decomposition.

### 3. 🧾 Mandatory Verification before Pop
- **Rule**: No task can be popped from the stack on assumptions or self-reports.
- **Enforcement**: `pop_task` requires deterministic ground truth verification passing with exit code `0`. A permanent `VerificationReceipt` (timestamp, exit code, files checked, SHA hash) is generated and archived in `stack.json`.

### 4. ✂️ Zero Fluff & Extreme Brevity
- **Rule**: Conversational pleasantries, apologies, and theoretical essays are banned to preserve the context window.
- **Enforcement**: `OutputSanitizer` automatically trims polite filler patterns and enforces a hard cap of 250 characters on `summary` and `review_feedback`.

