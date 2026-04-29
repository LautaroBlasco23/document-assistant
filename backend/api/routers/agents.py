"""Agent management endpoints."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.auth import CurrentUser
from api.deps import ServicesDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])

_KNOWN_PROVIDERS = frozenset({"groq", "openrouter", "huggingface", "nvidia", "gemini", "ollama"})


class AgentOut(BaseModel):
    id: str
    name: str
    prompt: str
    model: str
    provider: str
    temperature: float
    top_p: float
    max_tokens: int
    is_default: bool
    created_at: str


class CreateAgentRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    prompt: str = ""
    model: str
    provider: str
    temperature: float = Field(default=0.7, ge=0, le=2)
    top_p: float = Field(default=1.0, ge=0, le=1)
    max_tokens: int = Field(default=1024, ge=1, le=32768)


class UpdateAgentRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    prompt: str | None = None
    model: str | None = None
    provider: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    top_p: float | None = Field(default=None, ge=0, le=1)
    max_tokens: int | None = Field(default=None, ge=1, le=32768)


def _agent_out(agent) -> AgentOut:
    return AgentOut(
        id=str(agent.id),
        name=agent.name,
        prompt=agent.prompt or "",
        model=agent.model,
        provider=agent.provider,
        temperature=agent.temperature,
        top_p=agent.top_p,
        max_tokens=agent.max_tokens,
        is_default=agent.is_default,
        created_at=agent.created_at.isoformat(),
    )


@router.get("", response_model=list[AgentOut])
async def list_agents(
    current_user: CurrentUser,
    services: ServicesDep,
) -> list[AgentOut]:
    """List all agents for the current user, ensuring a default exists."""
    # Ensure default agent exists
    provider = services.config.llm_provider
    if provider == "groq":
        current_model = services.config.groq.model
    elif provider == "nvidia":
        current_model = services.config.nvidia.model
    elif provider == "gemini":
        current_model = services.config.gemini.model
    elif provider == "openrouter":
        current_model = services.config.openrouter.model
    elif provider == "huggingface":
        current_model = services.config.huggingface.model
    else:
        current_model = services.config.ollama.generation_model
    services.agent_store.ensure_default(current_user.id, current_model)
    agents = services.agent_store.list_by_user(current_user.id)
    return [_agent_out(a) for a in agents]


@router.post("", response_model=AgentOut, status_code=201)
async def create_agent(
    req: CreateAgentRequest,
    current_user: CurrentUser,
    services: ServicesDep,
) -> AgentOut:
    """Create a new agent for the current user."""
    from core.model.agent import Agent

    if req.provider not in _KNOWN_PROVIDERS:
        raise HTTPException(status_code=422, detail=f"Unknown provider: {req.provider}")

    agent = Agent(
        user_id=current_user.id,
        name=req.name,
        prompt=req.prompt or "",
        model=req.model,
        provider=req.provider,
        temperature=req.temperature,
        top_p=req.top_p,
        max_tokens=req.max_tokens,
        is_default=False,
    )
    try:
        created = services.agent_store.create(agent)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return _agent_out(created)


@router.put("/{agent_id}", response_model=AgentOut)
async def update_agent(
    agent_id: str,
    req: UpdateAgentRequest,
    current_user: CurrentUser,
    services: ServicesDep,
) -> AgentOut:
    """Update an existing agent."""
    from uuid import UUID as _UUID
    try:
        uid = _UUID(agent_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid agent ID")

    agent = services.agent_store.get_by_id(uid)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your agent")

    if req.name is not None:
        agent.name = req.name
    if req.prompt is not None:
        agent.prompt = req.prompt
    if req.model is not None:
        agent.model = req.model
    if req.provider is not None:
        if req.provider not in _KNOWN_PROVIDERS:
            raise HTTPException(status_code=422, detail=f"Unknown provider: {req.provider}")
        agent.provider = req.provider
    if req.temperature is not None:
        agent.temperature = req.temperature
    if req.top_p is not None:
        agent.top_p = req.top_p
    if req.max_tokens is not None:
        agent.max_tokens = req.max_tokens

    try:
        updated = services.agent_store.update(agent)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return _agent_out(updated)


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: str,
    current_user: CurrentUser,
    services: ServicesDep,
) -> None:
    """Delete an agent. Cannot delete the default agent."""
    from uuid import UUID as _UUID
    try:
        uid = _UUID(agent_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid agent ID")

    agent = services.agent_store.get_by_id(uid)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your agent")

    try:
        services.agent_store.delete(uid)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/default", response_model=AgentOut)
async def get_default_agent(
    current_user: CurrentUser,
    services: ServicesDep,
) -> AgentOut:
    """Get the default agent for the current user."""
    agent = services.agent_store.get_default(current_user.id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Default agent not found")
    return _agent_out(agent)
