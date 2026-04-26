"""Chat endpoint for AI-assisted document Q&A."""

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.auth import CurrentUser
from api.deps import ServicesDep
from application.agents.document_chat import DocumentChatAgent
from core.ports.llm import GenerationParams
from infrastructure.llm.factory import create_llm_with_model

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    context: str | None = None
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    model: str | None = None
    agent_id: str | None = None


class ChatResponse(BaseModel):
    reply: str


def _resolve_agent_llm(
    services: ServicesDep,
    model: str | None,
    agent_id: str | None,
    fallback_llm,
):
    """Resolve agent, returning (llm, agent_prompt | None)."""
    if agent_id:
        try:
            agent_uid = UUID(agent_id)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid agent_id")
        agent = services.agent_store.get_by_id(agent_uid)
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        return create_llm_with_model(services.config, agent.model), agent.prompt
    if model:
        return create_llm_with_model(services.config, model), None
    return fallback_llm, None


def _resolve_agent_params(
    services: ServicesDep,
    body_temperature: float | None,
    body_top_p: float | None,
    body_max_tokens: int | None,
    agent_id: str | None,
) -> GenerationParams:
    """Resolve generation params from agent config or request body."""
    if agent_id:
        try:
            agent_uid = UUID(agent_id)
        except ValueError:
            return GenerationParams(
                temperature=body_temperature,
                top_p=body_top_p,
                max_tokens=body_max_tokens,
            )
        agent = services.agent_store.get_by_id(agent_uid)
        if agent:
            return GenerationParams(
                temperature=body_temperature if body_temperature is not None else agent.temperature,
                top_p=body_top_p if body_top_p is not None else agent.top_p,
                max_tokens=body_max_tokens if body_max_tokens is not None else agent.max_tokens,
            )
    return GenerationParams(
        temperature=body_temperature,
        top_p=body_top_p,
        max_tokens=body_max_tokens,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    _user: CurrentUser,
    services: ServicesDep,
) -> ChatResponse:
    """Chat with an AI assistant about a document.

    The frontend provides the document context and conversation history.
    The assistant answers questions based on that context.
    """
    llm, agent_prompt = _resolve_agent_llm(services, body.model, body.agent_id, services.llm)
    agent = DocumentChatAgent(llm)
    raw_messages = [{"role": m.role, "content": m.content} for m in body.messages]
    params = _resolve_agent_params(
        services,
        body.temperature,
        body.top_p,
        body.max_tokens,
        body.agent_id,
    )
    reply = agent.answer(
        raw_messages,
        context=body.context,
        params=params,
        agent_prompt=agent_prompt or None,
    )
    return ChatResponse(reply=reply)
