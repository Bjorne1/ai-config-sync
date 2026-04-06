from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .workflow_handlers import (
    AgentSkillsClaudeHandler,
    AgentSkillsCodexHandler,
    SuperpowersClaudeHandler,
    SuperpowersCodexHandler,
    WorkflowHandler,
)


def _superpowers_handler_factory(tool_id: str) -> WorkflowHandler:
    if tool_id == "claude":
        return SuperpowersClaudeHandler()
    if tool_id == "codex":
        return SuperpowersCodexHandler()
    raise ValueError(f"superpowers does not support tool: {tool_id}")


def _agent_skills_handler_factory(tool_id: str) -> WorkflowHandler:
    if tool_id == "claude":
        return AgentSkillsClaudeHandler()
    if tool_id == "codex":
        return AgentSkillsCodexHandler()
    raise ValueError(f"agent-skills does not support tool: {tool_id}")


@dataclass(frozen=True)
class WorkflowDefinition:
    workflow_id: str
    label: str
    description: str
    repo_url: str
    supported_tools: tuple[str, ...]
    handler_factory: Callable[[str], WorkflowHandler]


WORKFLOW_REGISTRY: dict[str, WorkflowDefinition] = {
    "superpowers": WorkflowDefinition(
        workflow_id="superpowers",
        label="Superpowers",
        description="AI coding workflow skills library (brainstorming, TDD, debugging, etc.)",
        repo_url="https://github.com/obra/superpowers",
        supported_tools=("claude", "codex"),
        handler_factory=_superpowers_handler_factory,
    ),
    "agent-skills": WorkflowDefinition(
        workflow_id="agent-skills",
        label="Agent Skills",
        description="Production-grade engineering workflows (spec, plan, build, test, review, ship)",
        repo_url="https://github.com/addyosmani/agent-skills",
        supported_tools=("claude", "codex"),
        handler_factory=_agent_skills_handler_factory,
    ),
}
