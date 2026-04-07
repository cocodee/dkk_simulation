"""Task-oriented environment wrapper for RJ2506 tire loading."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .config import TireLoadingConfig
from .task_flow import TaskFlow, TaskPhase


@dataclass(frozen=True)
class StepResult:
    observation: dict[str, object]
    reward: float
    terminated: bool
    truncated: bool
    info: dict[str, object]


class Backend(Protocol):
    def reset(self) -> dict[str, object]: ...
    def execute(self, action: str, phase: TaskPhase) -> dict[str, object]: ...
    def observation(self, phase: TaskPhase) -> dict[str, object]: ...


class MockBackend:
    """Fallback backend used for tests and dry runs."""

    def __init__(self) -> None:
        self.object_stable = False

    def reset(self) -> dict[str, object]:
        self.object_stable = False
        return {"backend": "mock", "reset": True}

    def execute(self, action: str, phase: TaskPhase) -> dict[str, object]:
        self.object_stable = phase == TaskPhase.RETREAT
        return {
            "succeeded": True,
            "object_stable": self.object_stable,
            "action": action,
            "phase": phase.value,
        }

    def observation(self, phase: TaskPhase) -> dict[str, object]:
        return {
            "state": {
                "task_phase": phase.value,
                "base_pose": [0.0, 0.0, 0.0],
                "tire_on_conveyor": self.object_stable,
            },
            "images": {},
        }


class RJ2506TireLoadingEnv:
    """Minimal environment wrapper that exposes reset/step style APIs."""

    def __init__(self, config: TireLoadingConfig, backend: Backend | None = None) -> None:
        self.config = config
        self.backend = backend or MockBackend()
        self.task_flow = TaskFlow(
            max_failures=config.task.max_failures,
            success_hold_steps=config.task.success_hold_steps,
        )
        self.step_count = 0

    def reset(self, seed: int | None = None, options: dict[str, object] | None = None) -> dict[str, object]:
        del seed, options
        self.step_count = 0
        self.task_flow.reset()
        self.backend.reset()
        return self.get_observation()

    def get_observation(self) -> dict[str, object]:
        observation = self.backend.observation(self.task_flow.phase)
        observation["task_phase"] = self.task_flow.phase.value
        observation["action_mask"] = self.get_action_mask()
        return observation

    def get_action_mask(self) -> dict[str, bool]:
        return self.task_flow.action_mask()

    def is_success(self) -> bool:
        return self.task_flow.phase == TaskPhase.DONE

    def is_failure(self) -> bool:
        return self.task_flow.phase == TaskPhase.FAILED

    def step(self, action: str) -> StepResult:
        self.step_count += 1
        report = self.backend.execute(action, self.task_flow.phase)
        state = self.task_flow.advance(
            action=action,
            succeeded=bool(report.get("succeeded", False)),
            object_stable=bool(report.get("object_stable", False)),
        )

        reward = 1.0 if report.get("succeeded", False) else -1.0
        if state.phase == TaskPhase.DONE:
            reward += 10.0
        if state.phase == TaskPhase.FAILED:
            reward -= 10.0

        truncated = self.step_count >= self.config.task.max_steps and not (
            self.is_success() or self.is_failure()
        )
        observation = self.get_observation()
        info = {
            "expected_action": self.task_flow.expected_action(),
            "failure_count": self.task_flow.state.failure_count,
            "completed_cycles": self.task_flow.state.completed_cycles,
            "backend_report": report,
        }
        return StepResult(
            observation=observation,
            reward=reward,
            terminated=self.is_success() or self.is_failure(),
            truncated=truncated,
            info=info,
        )

