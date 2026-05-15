"""Chat endpoint for AI-assisted document Q&A."""

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.auth import CurrentUser
from api.deps import ServicesDep
from application.agents.document_chat import DocumentChatAgent
from application.llm_resolver import resolve_llm_for_agent
from core.exceptions import ProviderNotConfigured
from core.ports.llm import GenerationParams

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
    agent_uid = None
    if body.agent_id:
        try:
            agent_uid = UUID(body.agent_id)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid agent_id")

    try:
        llm, agent_prompt, agent_params = resolve_llm_for_agent(
            _user.id,
            agent_uid,
            services,
            model_override=body.model,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ProviderNotConfigured as e:
        raise HTTPException(
            status_code=412,
            detail=f"Provider not configured: {e.provider}. Add an API key in Settings.",
        )

    def _param(value: float | None, fallback: float | None) -> float | None:
        return value if value is not None else fallback

    agent_defaults = agent_params or {}
    params = GenerationParams(
        temperature=_param(body.temperature, getattr(agent_defaults, "temperature", None)),
        top_p=_param(body.top_p, getattr(agent_defaults, "top_p", None)),
        max_tokens=_param(body.max_tokens, getattr(agent_defaults, "max_tokens", None)),
    )

    agent = DocumentChatAgent(llm)
    raw_messages = [{"role": m.role, "content": m.content} for m in body.messages]
    reply = agent.answer(
        raw_messages,
        context=body.context,
        params=params,
        agent_prompt=agent_prompt or None,
    )
    return ChatResponse(reply=reply)
