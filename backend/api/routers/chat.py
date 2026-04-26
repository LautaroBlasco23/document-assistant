"""Chat endpoint for AI-assisted document Q&A."""

from fastapi import APIRouter
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
    llm = create_llm_with_model(services.config, body.model) if body.model else services.llm
    agent = DocumentChatAgent(llm)
    raw_messages = [{"role": m.role, "content": m.content} for m in body.messages]
    params = GenerationParams(
        temperature=body.temperature,
        top_p=body.top_p,
        max_tokens=body.max_tokens,
    )
    reply = agent.answer(raw_messages, context=body.context, params=params)
    return ChatResponse(reply=reply)
