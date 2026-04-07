"""Task phases and transitions for the tire loading loop."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TaskPhase(str, Enum):
    IDLE = "IDLE"
    NAVIGATE_TO_PICK = "NAVIGATE_TO_PICK"
    PRE_GRASP_ALIGN = "PRE_GRASP_ALIGN"
    DUAL_ARM_GRASP = "DUAL_ARM_GRASP"
    LIFT = "LIFT"
    TRANSPORT_TO_CONVEYOR = "TRANSPORT_TO_CONVEYOR"
    PLACE_ON_CONVEYOR = "PLACE_ON_CONVEYOR"
    RELEASE = "RELEASE"
    RETREAT = "RETREAT"
    DONE = "DONE"
    FAILED = "FAILED"


PHASE_ACTIONS: dict[TaskPhase, str | None] = {
    TaskPhase.IDLE: "start_cycle",
    TaskPhase.NAVIGATE_TO_PICK: "navigate_to_pick",
    TaskPhase.PRE_GRASP_ALIGN: "pre_grasp_align",
    TaskPhase.DUAL_ARM_GRASP: "dual_arm_grasp",
    TaskPhase.LIFT: "lift",
    TaskPhase.TRANSPORT_TO_CONVEYOR: "transport_to_conveyor",
    TaskPhase.PLACE_ON_CONVEYOR: "place_on_conveyor",
    TaskPhase.RELEASE: "release",
    TaskPhase.RETREAT: "retreat",
    TaskPhase.DONE: None,
    TaskPhase.FAILED: None,
}

NEXT_PHASE: dict[TaskPhase, TaskPhase] = {
    TaskPhase.IDLE: TaskPhase.NAVIGATE_TO_PICK,
    TaskPhase.NAVIGATE_TO_PICK: TaskPhase.PRE_GRASP_ALIGN,
    TaskPhase.PRE_GRASP_ALIGN: TaskPhase.DUAL_ARM_GRASP,
    TaskPhase.DUAL_ARM_GRASP: TaskPhase.LIFT,
    TaskPhase.LIFT: TaskPhase.TRANSPORT_TO_CONVEYOR,
    TaskPhase.TRANSPORT_TO_CONVEYOR: TaskPhase.PLACE_ON_CONVEYOR,
    TaskPhase.PLACE_ON_CONVEYOR: TaskPhase.RELEASE,
    TaskPhase.RELEASE: TaskPhase.RETREAT,
    TaskPhase.RETREAT: TaskPhase.DONE,
}


@dataclass
class TaskFlowState:
    phase: TaskPhase = TaskPhase.IDLE
    completed_cycles: int = 0
    failure_count: int = 0
    success_hold_counter: int = 0
    history: list[TaskPhase] = field(default_factory=lambda: [TaskPhase.IDLE])


class TaskFlow:
    """Tracks the state machine for a single loading cycle."""

    def __init__(self, max_failures: int, success_hold_steps: int) -> None:
        self.max_failures = max_failures
        self.success_hold_steps = success_hold_steps
        self.state = TaskFlowState()

    @property
    def phase(self) -> TaskPhase:
        return self.state.phase

    def reset(self) -> TaskFlowState:
        self.state = TaskFlowState()
        return self.state

    def expected_action(self) -> str | None:
        return PHASE_ACTIONS[self.state.phase]

    def action_mask(self) -> dict[str, bool]:
        expected = self.expected_action()
        return {
            action: action == expected
            for action in [value for value in PHASE_ACTIONS.values() if value is not None]
        }

    def advance(self, action: str, succeeded: bool, object_stable: bool = False) -> TaskFlowState:
        expected = self.expected_action()
        if self.state.phase in {TaskPhase.DONE, TaskPhase.FAILED}:
            return self.state

        if action != expected or not succeeded:
            self.state.failure_count += 1
            if self.state.failure_count >= self.max_failures:
                self.state.phase = TaskPhase.FAILED
                self.state.history.append(self.state.phase)
            return self.state

        if self.state.phase == TaskPhase.RETREAT:
            self.state.success_hold_counter += 1 if object_stable else 0
            if self.state.success_hold_counter < self.success_hold_steps:
                return self.state
            self.state.phase = TaskPhase.DONE
            self.state.completed_cycles += 1
            self.state.history.append(self.state.phase)
            return self.state

        self.state.phase = NEXT_PHASE[self.state.phase]
        self.state.history.append(self.state.phase)
        return self.state

