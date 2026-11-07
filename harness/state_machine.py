"""
Deterministic State Machine (Harness Control Plane) with Strict Mode Enforcer.
Decides state transitions, validates gates, enforces stack hygiene boundaries, blast radius,
and mandatory verification receipts.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from harness.schemas import (
    AgentAction,
    SystemState,
    TaskFrame,
    TaskStatus,
    StructuredOutput,
    TaskBudget,
    StrictLevel,
    VerificationReceipt,
)
from harness.task_stack import TaskStackManager
from harness.verifier import DeterministicVerifier, VerificationResult
from harness.sanitizer import OutputSanitizer


@dataclass
class TransitionResult:
    success: bool
    previous_state: SystemState
    new_state: SystemState
    next_agent: Optional[str]
    message: str
    rejection_feedback: Optional[str] = None
    verification_result: Optional[VerificationResult] = None
    verification_receipt: Optional[VerificationReceipt] = None


class DeterministicStateMachine:
    """The central deterministic orchestrator enforcing Strict Mode."""

    def __init__(self, stack_manager: TaskStackManager, workspace_root: str = "."):
        self.stack = stack_manager
        self.verifier = DeterministicVerifier(workspace_root)
        self.workspace_root = workspace_root

    @property
    def current_state(self) -> SystemState:
        return self.stack.current_state

    @property
    def strict_level(self) -> StrictLevel:
        return self.stack.strict_level

    @staticmethod
    def state_for_agent(agent: Optional[str]) -> SystemState:
        """Maps an agent identifier to its canonical SystemState."""
        if agent == "pm_agent":
            return SystemState.PLANNING
        if agent in ("architect_agent", "forensic_architect"):
            return SystemState.ARCHITECTURE
        if agent == "reviewer_agent":
            return SystemState.REVIEWING
        if agent in ("qa_agent", "evidence_auditor", "compliance_auditor"):
            return SystemState.QA_VERIFICATION
        return SystemState.CODING

    def _collect_exempt_files(self, active_task_id: str) -> List[str]:
        """Collects authorized/verified files from other tasks in the stack and history."""
        exempt: List[str] = []
        for frame in self.stack.stack:
            if frame.task_id != active_task_id:
                exempt.extend(frame.allowed_files)
                exempt.extend(frame.artifacts)
        for hist in self.stack.history:
            exempt.extend(hist.get("allowed_files", []))
            exempt.extend(hist.get("artifacts", []))
        return exempt

    def step_with_raw_output(self, raw_output: str) -> TransitionResult:
        """Parses raw agent output, sanitizes brevity, and executes transition."""
        enforce_brevity = self.strict_level in (StrictLevel.STRICT, StrictLevel.HARDCORE)
        structured_out, error = OutputSanitizer.parse_structured_output(
            raw_output,
            enforce_brevity=enforce_brevity,
            max_summary_chars=250,
            max_feedback_chars=1000,
        )
        if error or not structured_out:
            top = self.stack.peek()
            curr_state = self.current_state
            if top:
                top.budget.record_retry()
                self.stack.save()
            return TransitionResult(
                success=False,
                previous_state=curr_state,
                new_state=curr_state,
                next_agent=top.assigned_agent if top else None,
                message="Structured Output parsing failed.",
                rejection_feedback=f"Output must be valid JSON: {error}",
            )

        return self.transition(structured_out)

    def transition(self, output: StructuredOutput) -> TransitionResult:
        """Executes a deterministic state transition based on StructuredOutput."""
        prev_state = self.current_state
        top = self.stack.peek()

        if not top and output.action != AgentAction.PUSH_TASK:
            return TransitionResult(
                success=False,
                previous_state=prev_state,
                new_state=SystemState.IDLE,
                next_agent=None,
                message="Cannot transition: Task stack is empty.",
            )

        action = output.action

        # Update tokens if provided in metrics
        tokens = int(output.metrics.get("tokens_estimated", 0)) if output.metrics else 0
        if top and tokens > 0:
            top.budget.add_tokens(tokens)

        # -------------------------------------------------------------------
        # Rule 1: Hyper-Disciplined Stack Hygiene (File Boundary Check)
        # -------------------------------------------------------------------
        if top and action in (
            AgentAction.PUSH_TASK,
            AgentAction.REQUEST_REVIEW,
            AgentAction.COMPLETE,
            AgentAction.POP_TASK,
        ):
            if top.allowed_files and self.strict_level in (StrictLevel.STRICT, StrictLevel.HARDCORE):
                exempt_files = self._collect_exempt_files(top.task_id)
                is_clean, unauth_files = self.verifier.check_file_boundaries(
                    top.allowed_files,
                    exempt_files=exempt_files,
                )
                if not is_clean:
                    top.budget.record_retry()
                    self.stack.save()
                    err_msg = (
                        f"Hyper-Disciplined Stack Hygiene Violation: Unauthorized file(s) touched: "
                        f"{', '.join(unauth_files)}. You may only touch files declared in 'allowed_files': "
                        f"{', '.join(top.allowed_files)}. Push a subtask if prerequisite files need changes."
                    )
                    return TransitionResult(
                        success=False,
                        previous_state=prev_state,
                        new_state=prev_state,
                        next_agent=top.assigned_agent,
                        message="Boundary check failed.",
                        rejection_feedback=err_msg,
                    )

        # -------------------------------------------------------------------
        # Rule 2: Atomic Decomposition (Blast Radius Check)
        # -------------------------------------------------------------------
        if top and action in (AgentAction.REQUEST_REVIEW, AgentAction.COMPLETE):
            is_design_agent = top.assigned_agent in ("pm_agent", "architect_agent")
            if not is_design_agent and self.strict_level in (StrictLevel.STRICT, StrictLevel.HARDCORE):
                target_scope = top.allowed_files or top.artifacts or None
                within_radius, blast_reason = self.verifier.check_blast_radius(
                    max_lines=top.max_lines_changed,
                    max_files=4,
                    target_files=target_scope,
                )
                if not within_radius:
                    if self.strict_level == StrictLevel.HARDCORE:
                        top.budget.record_retry()
                        self.stack.save()
                        return TransitionResult(
                            success=False,
                            previous_state=prev_state,
                            new_state=prev_state,
                            next_agent=top.assigned_agent,
                            message="Atomic Decomposition blast radius exceeded.",
                            rejection_feedback=f"Atomic Decomposition Violation: {blast_reason}",
                        )

        # -------------------------------------------------------------------
        # 1. Action: PUSH_TASK (Decompose task into subtasks)
        # -------------------------------------------------------------------
        if action == AgentAction.PUSH_TASK:
            if not output.subtasks:
                return TransitionResult(
                    success=False,
                    previous_state=prev_state,
                    new_state=prev_state,
                    next_agent=top.assigned_agent if top else None,
                    message="action='push_task' requires 'subtasks' list.",
                    rejection_feedback="Please provide at least one subtask in 'subtasks'.",
                )

            if top and output.artifacts:
                self.stack.update_top(status=TaskStatus.IN_PROGRESS, artifacts=output.artifacts)
                ver_res = self.verifier.verify_artifacts(top.artifacts)
                if not ver_res.passed:
                    top.budget.record_retry()
                    self.stack.save()
                    return TransitionResult(
                        success=False,
                        previous_state=prev_state,
                        new_state=prev_state,
                        next_agent=top.assigned_agent,
                        message="Artifact verification failed before pushing subtasks.",
                        rejection_feedback=ver_res.summary(),
                        verification_result=ver_res,
                    )

            parent_id = top.task_id if top else None
            pushed_tasks: List[TaskFrame] = []
            for sub_data in reversed(output.subtasks):
                task_id = str(sub_data.get("task_id", f"SUB-{len(self.stack.stack) + 1}"))
                allowed = sub_data.get("allowed_files", [])
                sub_frame = TaskFrame(
                    task_id=task_id,
                    parent_id=parent_id,
                    title=str(sub_data.get("title", "")),
                    description=str(sub_data.get("description", "")),
                    assigned_agent=str(sub_data.get("assigned_agent", "backend_agent")),
                    status=TaskStatus.PENDING,
                    allowed_files=list(allowed) if isinstance(allowed, list) else [],
                    max_lines_changed=int(sub_data.get("max_lines_changed", 200)),
                )
                self.stack.push(sub_frame)
                pushed_tasks.append(sub_frame)

            new_top = self.stack.peek()
            next_agent = new_top.assigned_agent if new_top else "backend_agent"
            new_state = self.state_for_agent(next_agent)

            self.stack.set_system_state(new_state)
            return TransitionResult(
                success=True,
                previous_state=prev_state,
                new_state=new_state,
                next_agent=next_agent,
                message=f"Pushed {len(output.subtasks)} subtask(s) to stack.",
            )

        # -------------------------------------------------------------------
        # 2. Action: REQUEST_REVIEW or COMPLETE from Coder / Implementer
        # -------------------------------------------------------------------
        elif action in (AgentAction.REQUEST_REVIEW, AgentAction.COMPLETE):
            assert top is not None

            # Record any new artifacts
            if output.artifacts:
                self.stack.update_top(artifacts=output.artifacts)

            # Fast Local Verification Gate
            ver_res = self.verifier.verify_artifacts(top.artifacts)

            if not ver_res.passed:
                top.budget.record_retry()
                if top.budget.is_exhausted():
                    self.stack.set_system_state(SystemState.ESCALATED)
                    return TransitionResult(
                        success=False,
                        previous_state=prev_state,
                        new_state=SystemState.ESCALATED,
                        next_agent=None,
                        message="Circuit breaker tripped: Max retries exceeded during pre-handoff verification.",
                        rejection_feedback=ver_res.summary(),
                        verification_result=ver_res,
                    )

                fallback_state = self.state_for_agent(top.assigned_agent)
                self.stack.set_system_state(fallback_state)
                return TransitionResult(
                    success=False,
                    previous_state=prev_state,
                    new_state=fallback_state,
                    next_agent=top.assigned_agent,
                    message="Pre-handoff verification failed. Handed back to implementer.",
                    rejection_feedback=ver_res.summary(),
                    verification_result=ver_res,
                )

            # Verification Passed -> Deterministically route to Reviewer
            self.stack.update_top(status=TaskStatus.WAITING_REVIEW)
            new_state = SystemState.REVIEWING
            next_agent = "reviewer_agent"
            self.stack.set_system_state(new_state)

            return TransitionResult(
                success=True,
                previous_state=prev_state,
                new_state=new_state,
                next_agent=next_agent,
                message="Pre-handoff verification passed. Handed off to Reviewer.",
                verification_result=ver_res,
                verification_receipt=ver_res.receipt,
            )

        # -------------------------------------------------------------------
        # 3. Action: SUBMIT_REVIEW from Reviewer
        # -------------------------------------------------------------------
        elif action == AgentAction.SUBMIT_REVIEW:
            assert top is not None

            if output.status == "changes_requested":
                top.budget.record_retry()
                if top.budget.is_exhausted():
                    self.stack.set_system_state(SystemState.ESCALATED)
                    return TransitionResult(
                        success=False,
                        previous_state=prev_state,
                        new_state=SystemState.ESCALATED,
                        next_agent=None,
                        message="Circuit breaker tripped: Max review iterations exceeded.",
                        rejection_feedback=output.review_feedback or "Max review iterations exceeded.",
                    )

                self.stack.update_top(status=TaskStatus.IN_PROGRESS)
                next_agent = top.assigned_agent
                new_state = self.state_for_agent(next_agent)
                self.stack.set_system_state(new_state)

                return TransitionResult(
                    success=True,
                    previous_state=prev_state,
                    new_state=new_state,
                    next_agent=next_agent,
                    message="Changes requested by Reviewer. Routed back to implementer.",
                    rejection_feedback=output.review_feedback,
                )

            elif output.status in ("approved", "completed"):
                new_state = SystemState.QA_VERIFICATION
                next_agent = "qa_agent"
                self.stack.update_top(status=TaskStatus.VERIFYING)
                self.stack.set_system_state(new_state)

                return TransitionResult(
                    success=True,
                    previous_state=prev_state,
                    new_state=new_state,
                    next_agent=next_agent,
                    message="Review approved. Transitioned to QA Verification Gate.",
                )

        # -------------------------------------------------------------------
        # 4. Action: POP_TASK (Rule 3: Mandatory Verification before Pop)
        # -------------------------------------------------------------------
        elif action == AgentAction.POP_TASK:
            assert top is not None

            if output.artifacts:
                self.stack.update_top(artifacts=output.artifacts)

            # Enforce Rule 3: Verification must pass before pop
            ver_res = None
            if top.artifacts:
                ver_res = self.verifier.verify_artifacts(top.artifacts)
                if not ver_res.passed:
                    top.budget.record_retry()
                    self.stack.save()
                    return TransitionResult(
                        success=False,
                        previous_state=prev_state,
                        new_state=prev_state,
                        next_agent=top.assigned_agent,
                        message="Mandatory Verification before Pop failed.",
                        rejection_feedback=f"Cannot pop task: {ver_res.summary()}",
                        verification_result=ver_res,
                    )

            receipt = ver_res.receipt if ver_res else VerificationReceipt(
                details=f"Task {top.task_id} completed without file artifacts."
            )

            popped = self.stack.pop(completion_summary=output.summary, verification_receipt=receipt)
            if self.stack.is_empty():
                new_state = SystemState.COMPLETED
                self.stack.set_system_state(new_state)
                return TransitionResult(
                    success=True,
                    previous_state=prev_state,
                    new_state=new_state,
                    next_agent=None,
                    message=f"Task {popped.task_id if popped else ''} popped. All tasks completed!",
                    verification_receipt=receipt,
                )
            else:
                new_top = self.stack.peek()
                next_agent = new_top.assigned_agent if new_top else "backend_agent"
                new_state = self.state_for_agent(next_agent)
                self.stack.set_system_state(new_state)
                return TransitionResult(
                    success=True,
                    previous_state=prev_state,
                    new_state=new_state,
                    next_agent=next_agent,
                    message=f"Task {popped.task_id if popped else ''} verified and popped. Resuming {new_top.task_id if new_top else ''}.",
                    verification_receipt=receipt,
                )

        # -------------------------------------------------------------------
        # 5. Action: FAIL
        # -------------------------------------------------------------------
        elif action == AgentAction.FAIL:
            assert top is not None
            top.status = TaskStatus.FAILED
            new_state = SystemState.ESCALATED
            self.stack.set_system_state(new_state)
            return TransitionResult(
                success=False,
                previous_state=prev_state,
                new_state=new_state,
                next_agent=None,
                message=f"Task failed: {output.summary}",
                rejection_feedback=output.summary,
            )

        return TransitionResult(
            success=False,
            previous_state=prev_state,
            new_state=prev_state,
            next_agent=top.assigned_agent if top else None,
            message=f"Unhandled action '{action.value}'.",
        )
