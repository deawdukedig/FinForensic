"""
Data schemas and contracts for the Deterministic State Machine.
Defines Structured Output contracts, Task Frames, Strict Mode definitions, and State definitions.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
import json
import time
from typing import Any, Dict, List, Optional


class StrictLevel(str, Enum):
    LENIENT = "lenient"
    STRICT = "strict"
    HARDCORE = "hardcore"


class AgentAction(str, Enum):
    PUSH_TASK = "push_task"
    POP_TASK = "pop_task"
    REQUEST_REVIEW = "request_review"
    SUBMIT_REVIEW = "submit_review"
    COMPLETE = "complete"
    FAIL = "fail"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_REVIEW = "WAITING_REVIEW"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    ESCALATED = "ESCALATED"


class SystemState(str, Enum):
    IDLE = "IDLE"
    PLANNING = "PLANNING"
    ARCHITECTURE = "ARCHITECTURE"
    CODING = "CODING"
    PRE_HANDOFF_VERIFICATION = "PRE_HANDOFF_VERIFICATION"
    REVIEWING = "REVIEWING"
    QA_VERIFICATION = "QA_VERIFICATION"
    BLOCKED = "BLOCKED"
    ESCALATED = "ESCALATED"
    COMPLETED = "COMPLETED"


@dataclass
class VerificationReceipt:
    timestamp: float = field(default_factory=time.time)
    gate_type: str = "LIGHTWEIGHT_STATIC"
    verified_files: List[str] = field(default_factory=list)
    exit_code: int = 0
    status: str = "PASSED"
    details: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> VerificationReceipt:
        return cls(
            timestamp=float(data.get("timestamp", time.time())),
            gate_type=str(data.get("gate_type", "LIGHTWEIGHT_STATIC")),
            verified_files=list(data.get("verified_files", [])),
            exit_code=int(data.get("exit_code", 0)),
            status=str(data.get("status", "PASSED")),
            details=str(data.get("details", "")),
        )


@dataclass
class TaskBudget:
    max_tokens: int = 15000
    used_tokens: int = 0
    max_retries: int = 2
    current_retries: int = 0

    def is_exhausted(self) -> bool:
        return self.current_retries >= self.max_retries or (
            self.max_tokens > 0 and self.used_tokens >= self.max_tokens
        )

    def record_retry(self) -> None:
        self.current_retries += 1

    def add_tokens(self, tokens: int) -> None:
        self.used_tokens += max(0, tokens)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TaskBudget:
        return cls(
            max_tokens=data.get("max_tokens", 15000),
            used_tokens=data.get("used_tokens", 0),
            max_retries=data.get("max_retries", 2),
            current_retries=data.get("current_retries", 0),
        )


@dataclass
class TaskFrame:
    task_id: str
    parent_id: Optional[str] = None
    title: str = ""
    description: str = ""
    assigned_agent: str = "backend_agent"
    status: TaskStatus = TaskStatus.PENDING
    artifacts: List[str] = field(default_factory=list)
    allowed_files: List[str] = field(default_factory=list)
    max_lines_changed: int = 200
    budget: TaskBudget = field(default_factory=TaskBudget)
    verification_receipt: Optional[VerificationReceipt] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "parent_id": self.parent_id,
            "title": self.title,
            "description": self.description,
            "assigned_agent": self.assigned_agent,
            "status": self.status.value if isinstance(self.status, TaskStatus) else str(self.status),
            "artifacts": list(self.artifacts),
            "allowed_files": list(self.allowed_files),
            "max_lines_changed": self.max_lines_changed,
            "budget": self.budget.to_dict(),
            "verification_receipt": self.verification_receipt.to_dict() if self.verification_receipt else None,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TaskFrame:
        raw_status = data.get("status", TaskStatus.PENDING.value)
        try:
            status = TaskStatus(raw_status)
        except ValueError:
            status = TaskStatus.PENDING

        budget_data = data.get("budget", {})
        budget = TaskBudget.from_dict(budget_data) if isinstance(budget_data, dict) else TaskBudget()

        receipt_data = data.get("verification_receipt")
        receipt = VerificationReceipt.from_dict(receipt_data) if receipt_data else None

        return cls(
            task_id=str(data.get("task_id", "")),
            parent_id=data.get("parent_id"),
            title=str(data.get("title", "")),
            description=str(data.get("description", "")),
            assigned_agent=str(data.get("assigned_agent", "backend_agent")),
            status=status,
            artifacts=list(data.get("artifacts", [])),
            allowed_files=list(data.get("allowed_files", [])),
            max_lines_changed=int(data.get("max_lines_changed", 200)),
            budget=budget,
            verification_receipt=receipt,
            metadata=dict(data.get("metadata", {})),
            created_at=float(data.get("created_at", time.time())),
            updated_at=float(data.get("updated_at", time.time())),
        )


@dataclass
class StructuredOutput:
    action: AgentAction
    status: str
    summary: str
    artifacts: List[str] = field(default_factory=list)
    subtasks: Optional[List[Dict[str, Any]]] = None
    review_feedback: Optional[str] = None
    next_agent_hint: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action.value if isinstance(self.action, AgentAction) else str(self.action),
            "status": self.status,
            "summary": self.summary,
            "artifacts": list(self.artifacts),
            "subtasks": self.subtasks,
            "review_feedback": self.review_feedback,
            "next_agent_hint": self.next_agent_hint,
            "metrics": dict(self.metrics),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StructuredOutput:
        raw_action = data.get("action", AgentAction.COMPLETE.value).lower()
        try:
            action = AgentAction(raw_action)
        except ValueError:
            if "pop" in raw_action:
                action = AgentAction.POP_TASK
            elif "push" in raw_action:
                action = AgentAction.PUSH_TASK
            elif "review" in raw_action and "request" in raw_action:
                action = AgentAction.REQUEST_REVIEW
            elif "review" in raw_action:
                action = AgentAction.SUBMIT_REVIEW
            elif "fail" in raw_action:
                action = AgentAction.FAIL
            else:
                action = AgentAction.COMPLETE

        summary_text = str(data.get("summary", "")).strip()

        return cls(
            action=action,
            status=str(data.get("status", "completed")),
            summary=summary_text,
            artifacts=list(data.get("artifacts", [])),
            subtasks=data.get("subtasks"),
            review_feedback=data.get("review_feedback"),
            next_agent_hint=data.get("next_agent_hint"),
            metrics=dict(data.get("metrics", {})),
        )
