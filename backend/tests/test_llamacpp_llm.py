"""
Unit tests for LlamaCppLLM adapter.

Subject: infrastructure/llm/llamacpp_llm.py — LlamaCppLLM
Scope:   generate(), chat(), streaming, retry logic, health check, config fields.
Out of scope:
  - Actual llama-server behavior     → integration tests
Setup:   Mocked requests.post responses.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from infrastructure.config import LlamaCppConfig
from infrastructure.llm.llamacpp_llm import LlamaCppLLM, _health_cache

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(**kwargs) -> LlamaCppConfig:
    defaults = {
        "base_url": "http://localhost:8080/v1",
        "model": "local-model",
        "timeout": 30,
        "connect_timeout": 5,
        "max_retries": 3,
        "max_retries_chat": 2,  # >1 so tests can verify retries work
        "streaming": False,  # disable streaming for simpler non-streaming tests
    }
    defaults.update(kwargs)
    return LlamaCppConfig(**defaults)


def _mock_response(content: str, status_code: int = 200) -> MagicMock:
    """Create a mock requests.Response for a non-streaming call."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.json.return_value = {
        "choices": [{"message": {"content": content}}]
    }
    resp.raise_for_status = MagicMock()
    return resp


def _mock_streaming_response(chunks: list[str]) -> MagicMock:
    """Create a mock streaming requests.Response.

    Args:
        chunks: List of content strings to stream.
    """
    import json
    resp = MagicMock(spec=requests.Response)
    resp.status_code = 200

    lines = []
    for chunk in chunks:
        line = f'data: {json.dumps({"choices": [{"delta": {"content": chunk}}]})}'
        lines.append(line)
    lines.append("data: [DONE]")
    lines.append("")

    resp.iter_lines.return_value = iter(lines)
    resp.raise_for_status = MagicMock()
    resp.close = MagicMock()
    return resp


@pytest.fixture(autouse=True)
def _clear_health_cache():
    """Clear the health cache before each test."""
    _health_cache.clear()
    yield
    _health_cache.clear()


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


def test_llamacpp_strips_trailing_slash():
    """The base URL must have trailing slashes stripped."""
    config = _make_config(base_url="http://localhost:8080/v1/")
    llm = LlamaCppLLM(config)

    assert llm._base_url == "http://localhost:8080/v1"


def test_llamacpp_stores_model():
    """The model name must be stored from config."""
    config = _make_config(model="my-gguf-model")
    llm = LlamaCppLLM(config)

    assert llm._model == "my-gguf-model"


def test_llamacpp_stores_new_config_fields():
    """New config fields must be stored correctly."""
    config = _make_config(
        connect_timeout=15,
        max_retries=5,
        max_retries_chat=2,
        streaming=True,
    )
    llm = LlamaCppLLM(config)

    assert llm._connect_timeout == 15
    assert llm._max_retries == 5
    assert llm._max_retries_chat == 2
    assert llm._streaming is True


# ---------------------------------------------------------------------------
# generate() — non-streaming
# ---------------------------------------------------------------------------


def test_generate_returns_content():
    """generate() must return the response content."""
    config = _make_config()
    llm = LlamaCppLLM(config)

    mock_resp = _mock_response("hello from llama")

    with patch("requests.post", return_value=mock_resp):
        result = llm.generate("some prompt")

    assert result == "hello from llama"


def test_generate_sends_model():
    """generate() must send the configured model name."""
    config = _make_config(model="my-model")
    llm = LlamaCppLLM(config)

    mock_resp = _mock_response("ok")

    with patch("requests.post", return_value=mock_resp) as mock_post:
        llm.generate("test prompt")

    payload = mock_post.call_args[1]["json"]
    assert payload["model"] == "my-model"


def test_generate_applies_params():
    """generate() must apply temperature, top_p, and max_tokens when provided."""
    config = _make_config()
    llm = LlamaCppLLM(config)

    mock_resp = _mock_response("ok")

    with patch("requests.post", return_value=mock_resp) as mock_post:
        from core.ports.llm import GenerationParams
        llm.generate("prompt", params=GenerationParams(temperature=0.5, top_p=0.9, max_tokens=512))

    payload = mock_post.call_args[1]["json"]
    assert payload["temperature"] == 0.5
    assert payload["top_p"] == 0.9
    assert payload["max_tokens"] == 512


def test_generate_no_auth_header():
    """generate() must not send an Authorization header."""
    config = _make_config()
    llm = LlamaCppLLM(config)

    mock_resp = _mock_response("ok")

    with patch("requests.post", return_value=mock_resp) as mock_post:
        llm.generate("prompt")

    headers = mock_post.call_args[1]["headers"]
    assert "Authorization" not in headers


# ---------------------------------------------------------------------------
# chat() — non-streaming
# ---------------------------------------------------------------------------


def test_chat_returns_content():
    """chat() must return the response content."""
    config = _make_config()
    llm = LlamaCppLLM(config)

    mock_resp = _mock_response("chat response")

    with patch("requests.post", return_value=mock_resp):
        result = llm.chat(system="You are helpful", user="Hello")

    assert result == "chat response"


def test_chat_sends_system_and_user():
    """chat() must send both system and user messages."""
    config = _make_config()
    llm = LlamaCppLLM(config)

    mock_resp = _mock_response("ok")

    with patch("requests.post", return_value=mock_resp) as mock_post:
        llm.chat(system="Be concise", user="What is 2+2?")

    payload = mock_post.call_args[1]["json"]
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][1]["role"] == "user"


def test_chat_json_format_appends_instruction():
    """When format='json', chat() must append JSON-only instruction to system."""
    config = _make_config()
    llm = LlamaCppLLM(config)

    mock_resp = _mock_response("{}")

    with patch("requests.post", return_value=mock_resp) as mock_post:
        llm.chat(system="Extract data", user="text", format="json")

    payload = mock_post.call_args[1]["json"]
    assert "valid JSON only" in payload["messages"][0]["content"]


def test_chat_applies_params():
    """chat() must apply generation params."""
    config = _make_config()
    llm = LlamaCppLLM(config)

    mock_resp = _mock_response("ok")

    with patch("requests.post", return_value=mock_resp) as mock_post:
        from core.ports.llm import GenerationParams
        llm.chat("sys", "user", params=GenerationParams(temperature=0.3))

    payload = mock_post.call_args[1]["json"]
    assert payload["temperature"] == 0.3


# ---------------------------------------------------------------------------
# Streaming
# ---------------------------------------------------------------------------


def test_streaming_chat_returns_content():
    """Streaming chat() must accumulate and return all chunks."""
    config = _make_config(streaming=True)
    llm = LlamaCppLLM(config)

    mock_resp = _mock_streaming_response(["Hello", " ", "world"])

    with patch("requests.post", return_value=mock_resp):
        result = llm.chat(system="You are helpful", user="Hello")

    assert result == "Hello world"


def test_streaming_generate_returns_content():
    """Streaming generate() must accumulate and return all chunks."""
    config = _make_config(streaming=True)
    llm = LlamaCppLLM(config)

    mock_resp = _mock_streaming_response(["hello", " llama"])

    with patch("requests.post", return_value=mock_resp):
        result = llm.generate("some prompt")

    assert result == "hello llama"


def test_streaming_sends_stream_true():
    """Streaming requests must set stream=True in payload."""
    config = _make_config(streaming=True)
    llm = LlamaCppLLM(config)

    mock_resp = _mock_streaming_response(["ok"])

    with patch("requests.post", return_value=mock_resp) as mock_post:
        llm.chat(system="sys", user="user")

    payload = mock_post.call_args[1]["json"]
    assert payload["stream"] is True


def test_streaming_uses_per_chunk_timeout():
    """Streaming must use per-chunk timeout instead of total timeout."""
    config = _make_config(streaming=True, timeout=300, connect_timeout=10)
    llm = LlamaCppLLM(config)

    mock_resp = _mock_streaming_response(["ok"])

    with patch("requests.post", return_value=mock_resp) as mock_post:
        llm.chat(system="sys", user="user")

    # Check timeout parameter: should be (connect_timeout, per_chunk_timeout)
    timeout = mock_post.call_args[1]["timeout"]
    assert timeout == (10, 30)  # 30 is _STREAM_CHUNK_TIMEOUT


def test_streaming_closes_response():
    """Streaming must close the response even on success."""
    config = _make_config(streaming=True)
    llm = LlamaCppLLM(config)

    mock_resp = _mock_streaming_response(["ok"])

    with patch("requests.post", return_value=mock_resp):
        llm.chat(system="sys", user="user")

    mock_resp.close.assert_called_once()


def test_streaming_updates_task_progress():
    """Streaming must update task progress every 50 tokens."""
    config = _make_config(streaming=True)
    llm = LlamaCppLLM(config)

    # Generate enough chunks to trigger progress update
    chunks = [f"token{i} " for i in range(60)]
    mock_resp = _mock_streaming_response(chunks)

    task = MagicMock()
    task.progress = ""

    with patch("requests.post", return_value=mock_resp):
        with patch("infrastructure.llm.llamacpp_llm._current_task") as mock_ctx:
            mock_ctx.get.return_value = task
            llm.chat(system="sys", user="user")

    # Progress should have been updated at token 50
    assert task.progress == "Generated ~60 tokens"


# ---------------------------------------------------------------------------
# Retry logic — ConnectionError
# ---------------------------------------------------------------------------


def test_connection_error_retries_with_backoff():
    """ConnectionError must be retried with exponential backoff."""
    config = _make_config(max_retries=3, max_retries_chat=3, streaming=False)
    llm = LlamaCppLLM(config)

    with patch("requests.post") as mock_post:
        mock_post.side_effect = [
            requests.ConnectionError("refused"),
            requests.ConnectionError("refused"),
            _mock_response("ok"),
        ]

        with patch("infrastructure.llm.llamacpp_llm.time.sleep") as mock_sleep:
            result = llm.generate("prompt")

    assert result == "ok"
    assert mock_post.call_count == 3
    # Check exponential backoff: 2s, 4s
    sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
    assert sleep_calls == [2, 4]


def test_connection_error_raises_after_max_retries():
    """ConnectionError must raise after exhausting retries."""
    config = _make_config(max_retries=2, streaming=False)
    llm = LlamaCppLLM(config)

    with patch("requests.post") as mock_post:
        mock_post.side_effect = requests.ConnectionError("refused")

        with patch("infrastructure.llm.llamacpp_llm.time.sleep"):
            with pytest.raises(requests.ConnectionError):
                llm.generate("prompt")

    assert mock_post.call_count == 2


def test_chat_uses_fewer_retries_for_sync():
    """Synchronous chat() must use max_retries_chat instead of max_retries."""
    config = _make_config(max_retries=3, max_retries_chat=1, streaming=False)
    llm = LlamaCppLLM(config)

    with patch("requests.post") as mock_post:
        mock_post.side_effect = requests.ConnectionError("refused")

        with patch("infrastructure.llm.llamacpp_llm.time.sleep"):
            with pytest.raises(requests.ConnectionError):
                llm.chat(system="sys", user="user")

    # Should only retry once (max_retries_chat=1), not 3 times
    assert mock_post.call_count == 1


# ---------------------------------------------------------------------------
# Retry logic — ReadTimeout
# ---------------------------------------------------------------------------


def test_read_timeout_retries():
    """ReadTimeout must be retried, unlike the old code that only retried ConnectionError."""
    config = _make_config(max_retries=2, streaming=False)
    llm = LlamaCppLLM(config)

    with patch("requests.post") as mock_post:
        mock_post.side_effect = [
            requests.ReadTimeout("read timed out"),
            _mock_response("ok"),
        ]

        with patch("infrastructure.llm.llamacpp_llm.time.sleep"):
            result = llm.generate("prompt")

    assert result == "ok"
    assert mock_post.call_count == 2


# ---------------------------------------------------------------------------
# Retry logic — HTTP 5xx
# ---------------------------------------------------------------------------


def test_http_5xx_retries():
    """HTTP 5xx errors must be retried."""
    config = _make_config(max_retries=2, streaming=False)
    llm = LlamaCppLLM(config)

    resp_500 = MagicMock(spec=requests.Response)
    resp_500.status_code = 500
    http_err = requests.HTTPError(response=resp_500)

    with patch("requests.post") as mock_post:
        mock_post.side_effect = [
            http_err,
            _mock_response("ok"),
        ]

        with patch("infrastructure.llm.llamacpp_llm.time.sleep"):
            result = llm.generate("prompt")

    assert result == "ok"
    assert mock_post.call_count == 2


def test_http_4xx_does_not_retry():
    """HTTP 4xx errors must NOT be retried (client errors)."""
    config = _make_config(max_retries=3, streaming=False)
    llm = LlamaCppLLM(config)

    resp_400 = MagicMock(spec=requests.Response)
    resp_400.status_code = 400
    http_err = requests.HTTPError(response=resp_400)

    with patch("requests.post") as mock_post:
        mock_post.side_effect = http_err

        with pytest.raises(requests.HTTPError):
            llm.generate("prompt")

    # Should NOT retry on 4xx
    assert mock_post.call_count == 1


# ---------------------------------------------------------------------------
# Streaming retry logic
# ---------------------------------------------------------------------------


def test_streaming_retries_on_connection_error():
    """Streaming must retry on ConnectionError."""
    config = _make_config(streaming=True, max_retries=2)
    llm = LlamaCppLLM(config)

    mock_resp = _mock_streaming_response(["ok"])

    with patch("requests.post") as mock_post:
        mock_post.side_effect = [
            requests.ConnectionError("refused"),
            mock_resp,
        ]

        with patch("infrastructure.llm.llamacpp_llm.time.sleep"):
            result = llm.chat(system="sys", user="user")

    assert result == "ok"
    assert mock_post.call_count == 2


def test_streaming_retries_on_read_timeout():
    """Streaming must retry on ReadTimeout."""
    config = _make_config(streaming=True, max_retries=2)
    llm = LlamaCppLLM(config)

    mock_resp = _mock_streaming_response(["ok"])

    with patch("requests.post") as mock_post:
        mock_post.side_effect = [
            requests.ReadTimeout("timeout"),
            mock_resp,
        ]

        with patch("infrastructure.llm.llamacpp_llm.time.sleep"):
            result = llm.chat(system="sys", user="user")

    assert result == "ok"
    assert mock_post.call_count == 2


def test_streaming_retries_on_chunked_encoding_error():
    """Streaming must retry on ChunkedEncodingError."""
    config = _make_config(streaming=True, max_retries=2)
    llm = LlamaCppLLM(config)

    mock_resp = _mock_streaming_response(["ok"])

    with patch("requests.post") as mock_post:
        mock_post.side_effect = [
            requests.exceptions.ChunkedEncodingError("chunked error"),
            mock_resp,
        ]

        with patch("infrastructure.llm.llamacpp_llm.time.sleep"):
            result = llm.chat(system="sys", user="user")

    assert result == "ok"
    assert mock_post.call_count == 2


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


def test_is_healthy_returns_true():
    """Health check must return True when server responds 200."""
    config = _make_config()
    llm = LlamaCppLLM(config)

    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.status_code = 200

    with patch("requests.get", return_value=mock_resp):
        assert llm.is_healthy() is True


def test_is_healthy_returns_false_on_error():
    """Health check must return False when server is unreachable."""
    config = _make_config()
    llm = LlamaCppLLM(config)

    with patch("requests.get", side_effect=requests.ConnectionError("refused")):
        assert llm.is_healthy() is False


def test_is_healthy_returns_false_on_non_200():
    """Health check must return False on non-200 status."""
    config = _make_config()
    llm = LlamaCppLLM(config)

    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.status_code = 503

    with patch("requests.get", return_value=mock_resp):
        assert llm.is_healthy() is False


def test_is_healthy_caches_result():
    """Health check results must be cached for a short period."""
    config = _make_config(base_url="http://localhost:8080/v1")
    llm = LlamaCppLLM(config)

    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.status_code = 200

    with patch("requests.get", return_value=mock_resp) as mock_get:
        # First call
        assert llm.is_healthy() is True
        # Second call (cached)
        assert llm.is_healthy() is True
        # Only one GET request should have been made
        assert mock_get.call_count == 1


# ---------------------------------------------------------------------------
# Timeout configuration
# ---------------------------------------------------------------------------


def test_non_streaming_uses_split_timeout():
    """Non-streaming must use (connect_timeout, read_timeout)."""
    config = _make_config(connect_timeout=10, timeout=300, streaming=False)
    llm = LlamaCppLLM(config)

    mock_resp = _mock_response("ok")

    with patch("requests.post", return_value=mock_resp) as mock_post:
        llm.generate("prompt")

    timeout = mock_post.call_args[1]["timeout"]
    assert timeout == (10, 300)
