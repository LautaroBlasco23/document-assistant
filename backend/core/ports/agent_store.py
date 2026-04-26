from abc import ABC, abstractmethod
from uuid import UUID

from core.model.agent import Agent


class AgentRepository(ABC):
    @abstractmethod
    def list_by_user(self, user_id: UUID) -> list[Agent]:
        """List all agents for a user."""

    @abstractmethod
    def get_by_id(self, agent_id: UUID) -> Agent | None:
        """Get an agent by ID."""

    @abstractmethod
    def get_default(self, user_id: UUID) -> Agent | None:
        """Get the default agent for a user."""

    @abstractmethod
    def create(self, agent: Agent) -> Agent:
        """Create a new agent. Raises ValueError on duplicate name."""

    @abstractmethod
    def update(self, agent: Agent) -> Agent:
        """Update an existing agent."""

    @abstractmethod
    def delete(self, agent_id: UUID) -> None:
        """Delete an agent (cannot delete the default agent)."""
