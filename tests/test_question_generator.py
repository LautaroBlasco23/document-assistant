"""Unit tests for QuestionGeneratorAgent._parse and batching logic."""
import json
from unittest.mock import MagicMock

import pytest

from application.agents.question_generator import QuestionGeneratorAgent, _BATCH_SIZE
from core.model.chunk import Chunk


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chunk(text: str = "sample text") -> Chunk:
    return Chunk(text=text, token_count=len(text.split()))


def _make_agent(responses: list[str]) -> tuple[QuestionGeneratorAgent, MagicMock]:
    """Return an agent whose LLM mock returns responses in sequence."""
    llm = MagicMock()
    llm.chat.side_effect = responses
    return QuestionGeneratorAgent(llm), llm


# ---------------------------------------------------------------------------
# _parse: valid inputs
# ---------------------------------------------------------------------------

class TestParse:
    def test_pairs_wrapper(self):
        raw = json.dumps({"pairs": [{"question": "Q1", "answer": "A1"}]})
        result = QuestionGeneratorAgent._parse(raw)
        assert result == [{"question": "Q1", "answer": "A1"}]

    def test_bare_array(self):
        raw = json.dumps([{"question": "Q1", "answer": "A1"}])
        result = QuestionGeneratorAgent._parse(raw)
        assert result == [{"question": "Q1", "answer": "A1"}]

    def test_questions_alternate_key(self):
        raw = json.dumps({"questions": [{"question": "Q2", "answer": "A2"}]})
        result = QuestionGeneratorAgent._parse(raw)
        assert result == [{"question": "Q2", "answer": "A2"}]

    def test_multiple_pairs(self):
        pairs = [{"question": f"Q{i}", "answer": f"A{i}"} for i in range(5)]
        raw = json.dumps({"pairs": pairs})
        result = QuestionGeneratorAgent._parse(raw)
        assert len(result) == 5
        assert result[0] == {"question": "Q0", "answer": "A0"}

    def test_empty_pairs_array(self):
        raw = json.dumps({"pairs": []})
        result = QuestionGeneratorAgent._parse(raw)
        assert result == []

    def test_items_missing_question_key_filtered_out(self):
        raw = json.dumps({"pairs": [
            {"question": "Q1", "answer": "A1"},
            {"answer": "A2"},  # missing "question"
            {"question": "Q3", "answer": "A3"},
        ]})
        result = QuestionGeneratorAgent._parse(raw)
        assert len(result) == 2
        assert result[0]["question"] == "Q1"
        assert result[1]["question"] == "Q3"


# ---------------------------------------------------------------------------
# _parse: invalid / malformed inputs
# ---------------------------------------------------------------------------

class TestParseErrors:
    def test_plain_text_returns_empty(self):
        result = QuestionGeneratorAgent._parse("Here are your questions: ...")
        assert result == []

    def test_truncated_json_returns_empty(self):
        result = QuestionGeneratorAgent._parse('{"pairs": [{"question": "Q1"')
        assert result == []

    def test_empty_string_returns_empty(self):
        result = QuestionGeneratorAgent._parse("")
        assert result == []

    def test_non_list_data_returns_empty(self):
        # dict without "pairs" or "questions" key falls through to non-list check
        raw = json.dumps({"pairs": "not a list"})
        result = QuestionGeneratorAgent._parse(raw)
        assert result == []

    def test_json_number_returns_empty(self):
        result = QuestionGeneratorAgent._parse("42")
        assert result == []


# ---------------------------------------------------------------------------
# generate: batching behaviour
# ---------------------------------------------------------------------------

class TestGenerate:
    def test_12_chunks_produces_3_batches(self):
        n_chunks = 12
        expected_batches = n_chunks // _BATCH_SIZE  # 3
        single_pair = [{"question": "Q", "answer": "A"}]
        responses = [json.dumps({"pairs": single_pair})] * expected_batches
        agent, llm = _make_agent(responses)

        chunks = [_make_chunk(f"chunk text {i}") for i in range(n_chunks)]
        result = agent.generate(chunks)

        assert llm.chat.call_count == expected_batches
        assert len(result) == expected_batches  # 1 pair per batch

    def test_results_from_all_batches_combined(self):
        n_chunks = 8
        n_batches = n_chunks // _BATCH_SIZE  # 2
        batch_pairs = [
            {"pairs": [{"question": "Q1", "answer": "A1"}, {"question": "Q2", "answer": "A2"}]},
            {"pairs": [{"question": "Q3", "answer": "A3"}]},
        ]
        responses = [json.dumps(b) for b in batch_pairs]
        agent, llm = _make_agent(responses)

        chunks = [_make_chunk(f"chunk {i}") for i in range(n_chunks)]
        result = agent.generate(chunks)

        assert len(result) == 3
        questions = [r["question"] for r in result]
        assert questions == ["Q1", "Q2", "Q3"]

    def test_format_json_passed_to_chat(self):
        agent, llm = _make_agent([json.dumps({"pairs": []})])

        agent.generate([_make_chunk()])

        llm.chat.assert_called_once()
        _, kwargs = llm.chat.call_args
        # format="json" may be positional (index 2) or keyword
        call_args = llm.chat.call_args
        assert call_args[1].get("format") == "json" or (
            len(call_args[0]) >= 3 and call_args[0][2] == "json"
        )

    def test_fewer_chunks_than_batch_size_single_call(self):
        agent, llm = _make_agent([json.dumps({"pairs": [{"question": "Q", "answer": "A"}]})])
        chunks = [_make_chunk() for _ in range(2)]
        result = agent.generate(chunks)

        assert llm.chat.call_count == 1
        assert len(result) == 1

    def test_empty_chunks_returns_empty(self):
        agent, llm = _make_agent([])
        result = agent.generate([])

        assert result == []
        llm.chat.assert_not_called()
