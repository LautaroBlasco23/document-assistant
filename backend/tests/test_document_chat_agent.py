"""
Subject: application/agents/document_chat.py — DocumentChatAgent
Scope:   Answering user questions with/without document context, multi-turn history, LLM errors
Out of scope:
  - JSON parsing or retry logic          → test_base_agent.py
  - flashcard / question generation      → test_flashcard_generator_agent.py,
                                           test_question_generator_agent.py
Setup:   LLM collaborator is a unittest.mock.MagicMock(spec=LLM).
"""

from unittest.mock import MagicMock

from application.agents.document_chat import DocumentChatAgent
from core.ports.llm import LLM

# ---------------------------------------------------------------------------
# answer() with context
# ---------------------------------------------------------------------------

# Includes document context in the user message Background section (not system prompt).
def test_answer_with_context():
    llm = MagicMock(spec=LLM)
    llm.chat.return_value = "The answer is 42."
    agent = DocumentChatAgent(llm)

    messages = [{"role": "user", "content": "What is the meaning of life?"}]
    result = agent.answer(messages, context="Document about life")

    assert result == "The answer is 42."
    call_args = llm.chat.call_args[0]
    system, user = call_args[0], call_args[1]
    assert "Document about life" in user
    assert "What is the meaning of life?" in user
    assert "Document about life" not in system


# ---------------------------------------------------------------------------
# answer() with empty context
# ---------------------------------------------------------------------------

# Omits the context section from the system prompt when no context is provided.
def test_answer_without_context():
    llm = MagicMock(spec=LLM)
    llm.chat.return_value = "I don't know."
    agent = DocumentChatAgent(llm)

    messages = [{"role": "user", "content": "Hello?"}]
    result = agent.answer(messages, context=None)

    assert result == "I don't know."
    system = llm.chat.call_args[0][0]
    assert "Here is the document context" not in system


# ---------------------------------------------------------------------------
# answer() multi-turn conversation
# ---------------------------------------------------------------------------

# Formats prior messages as a history block prefixed to the latest question.
def test_answer_multi_turn():
    llm = MagicMock(spec=LLM)
    llm.chat.return_value = "Sure thing."
    agent = DocumentChatAgent(llm)

    messages = [
        {"role": "user", "content": "First question"},
        {"role": "assistant", "content": "First answer"},
        {"role": "user", "content": "Follow-up"},
    ]
    result = agent.answer(messages, context="Ctx")

    assert result == "Sure thing."
    user_msg = llm.chat.call_args[0][1]
    assert "Conversation so far" in user_msg
    assert "User: First question" in user_msg
    assert "Assistant: First answer" in user_msg
    assert "Latest question" in user_msg
    assert "Follow-up" in user_msg


# ---------------------------------------------------------------------------
# answer() error propagation
# ---------------------------------------------------------------------------

# Returns a friendly error message instead of crashing when the LLM call raises.
def test_answer_propagates_llm_error():
    llm = MagicMock(spec=LLM)
    llm.chat.side_effect = RuntimeError("LLM exploded")
    agent = DocumentChatAgent(llm)

    messages = [{"role": "user", "content": "Oops"}]
    result = agent.answer(messages, context="Ctx")

    assert "Sorry, I encountered an error" in result


# ---------------------------------------------------------------------------
# answer() empty messages
# ---------------------------------------------------------------------------

# Handles an empty messages list by sending an empty string as the user message.
def test_answer_empty_messages():
    llm = MagicMock(spec=LLM)
    llm.chat.return_value = "Empty."
    agent = DocumentChatAgent(llm)

    result = agent.answer([], context="Ctx")

    assert result == "Empty."
    user_msg = llm.chat.call_args[0][1]
    assert "Latest question" in user_msg
    assert "Ctx" in user_msg
