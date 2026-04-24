"""Chat endpoint for AI-assisted document Q&A."""

from fastapi import APIRouter
from pydantic import BaseModel

from api.auth import CurrentUser
from api.deps import ServicesDep
from application.agents.document_chat import DocumentChatAgent

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    context: str | None = None


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
    agent = DocumentChatAgent(services.llm)
    raw_messages = [{"role": m.role, "content": m.content} for m in body.messages]
    reply = agent.answer(raw_messages, context=body.context)
    return ChatResponse(reply=reply)
