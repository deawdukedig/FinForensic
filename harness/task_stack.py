"""
Task Call-Stack Engine.
Manages the persistent hierarchical call-stack in stack.json with atomic file operations and Strict Mode tracking.
"""

from __future__ import annotations
import json
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import uuid

from harness.schemas import TaskFrame, TaskStatus, SystemState, StrictLevel, VerificationReceipt


class TaskStackManager:
    """Manages the task stack backed by stack.json."""

    def __init__(
        self,
        file_path: str = "stack.json",
        session_id: Optional[str] = None,
        strict_level: StrictLevel = StrictLevel.STRICT,
    ):
        self.file_path = Path(file_path).resolve()
        self.session_id = session_id or f"sess-{uuid.uuid4().hex[:8]}"
        self.current_state = SystemState.IDLE
        self.strict_level = strict_level
        self.stack: List[TaskFrame] = []
        self.history: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}
        self.created_at = time.time()
        self.updated_at = time.time()

        if self.file_path.exists():
            self.load()

    def is_empty(self) -> bool:
        return len(self.stack) == 0

    def peek(self) -> Optional[TaskFrame]:
        """Returns the Top of Stack without removing it."""
        if not self.stack:
            return None
        return self.stack[-1]

    def push(self, task: TaskFrame) -> None:
        """Pushes a new task frame to the top of the stack."""
        self.stack.append(task)
        self.updated_at = time.time()
        self.save()

    def pop(
        self,
        completion_summary: str = "",
        verification_receipt: Optional[VerificationReceipt] = None,
    ) -> Optional[TaskFrame]:
        """Pops the top task from the stack, attaches verification receipt, and moves it to history."""
        if not self.stack:
            return None

        popped = self.stack.pop()
        popped.status = TaskStatus.COMPLETED
        popped.updated_at = time.time()
        if verification_receipt:
            popped.verification_receipt = verification_receipt

        history_record = popped.to_dict()
        history_record["completed_at"] = time.time()
        history_record["completion_summary"] = completion_summary
        if verification_receipt:
            history_record["verification_receipt"] = verification_receipt.to_dict()

        self.history.append(history_record)
        self.updated_at = time.time()
        self.save()
        return popped

    def update_top(
        self,
        status: Optional[TaskStatus] = None,
        artifacts: Optional[List[str]] = None,
        allowed_files: Optional[List[str]] = None,
        assigned_agent: Optional[str] = None,
        tokens_used: int = 0,
        increment_retry: bool = False,
    ) -> Optional[TaskFrame]:
        """Updates the current top task frame."""
        top = self.peek()
        if not top:
            return None

        if status is not None:
            top.status = status
        if artifacts is not None:
            existing = set(top.artifacts)
            for art in artifacts:
                if art not in existing:
                    top.artifacts.append(art)
                    existing.add(art)
        if allowed_files is not None:
            existing_allowed = set(top.allowed_files)
            for af in allowed_files:
                if af not in existing_allowed:
                    top.allowed_files.append(af)
                    existing_allowed.add(af)
        if assigned_agent is not None:
            top.assigned_agent = assigned_agent
        if tokens_used > 0:
            top.budget.add_tokens(tokens_used)
        if increment_retry:
            top.budget.record_retry()

        top.updated_at = time.time()
        self.updated_at = time.time()
        self.save()
        return top

    def set_system_state(self, state: SystemState) -> None:
        self.current_state = state
        self.updated_at = time.time()
        self.save()

    def set_strict_level(self, level: StrictLevel) -> None:
        self.strict_level = level
        self.updated_at = time.time()
        self.save()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "current_state": self.current_state.value if isinstance(self.current_state, SystemState) else str(self.current_state),
            "strict_level": self.strict_level.value if isinstance(self.strict_level, StrictLevel) else str(self.strict_level),
            "stack_depth": len(self.stack),
            "stack": [task.to_dict() for task in self.stack],
            "history": self.history,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def save(self) -> None:
        """Atomic write to stack.json via temporary file."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.file_path.with_suffix(".json.tmp")
        data = self.to_dict()

        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        os.replace(tmp_path, self.file_path)

    def load(self) -> None:
        """Loads stack state from stack.json."""
        if not self.file_path.exists():
            return

        with open(self.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.session_id = data.get("session_id", self.session_id)
        raw_state = data.get("current_state", SystemState.IDLE.value)
        try:
            self.current_state = SystemState(raw_state)
        except ValueError:
            self.current_state = SystemState.IDLE

        raw_strict = data.get("strict_level", StrictLevel.STRICT.value)
        try:
            self.strict_level = StrictLevel(raw_strict)
        except ValueError:
            self.strict_level = StrictLevel.STRICT

        self.metadata = data.get("metadata", {})
        self.created_at = data.get("created_at", time.time())
        self.updated_at = data.get("updated_at", time.time())
        self.history = data.get("history", [])

        self.stack = []
        for item in data.get("stack", []):
            self.stack.append(TaskFrame.from_dict(item))
