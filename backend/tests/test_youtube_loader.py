"""Unit tests for infrastructure.ingest.youtube_loader."""

import pytest
from unittest.mock import MagicMock, patch

from infrastructure.ingest.youtube_loader import (
    TranscriptUnavailable,
    VideoUnavailable,
    _format_timestamp,
    _normalize_transcript,
    extract_video_id,
    fetch_transcript,
)


class TestExtractVideoId:
    def test_standard_watch_url(self):
        assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_short_url(self):
        assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_shorts_url(self):
        assert extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_embed_url(self):
        assert extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_url_with_extra_params(self):
        assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s") == "dQw4w9WgXcQ"

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError):
            extract_video_id("https://vimeo.com/12345")

    def test_plain_string_raises(self):
        with pytest.raises(ValueError):
            extract_video_id("not-a-url")


class TestFormatTimestamp:
    def test_seconds_only(self):
        assert _format_timestamp(45) == "00:45"

    def test_minutes_and_seconds(self):
        assert _format_timestamp(125) == "02:05"

    def test_hours(self):
        assert _format_timestamp(3661) == "01:01:01"

    def test_zero(self):
        assert _format_timestamp(0) == "00:00"

    def test_float_truncated(self):
        assert _format_timestamp(59.9) == "00:59"


class TestNormalizeTranscript:
    def test_basic(self):
        entries = [{"start": 0, "text": "Hello world"}, {"start": 62, "text": "Second line"}]
        result = _normalize_transcript(entries)
        assert result == "[00:00] Hello world\n[01:02] Second line"

    def test_empty_entries_skipped(self):
        entries = [{"start": 0, "text": ""}, {"start": 5, "text": "Hi"}]
        result = _normalize_transcript(entries)
        assert result == "[00:05] Hi"

    def test_strips_whitespace(self):
        entries = [{"start": 10, "text": "  trimmed  "}]
        result = _normalize_transcript(entries)
        assert "[00:10] trimmed" in result


def _make_snippet(text: str, start: float):
    s = MagicMock()
    s.text = text
    s.start = start
    return s


class TestFetchTranscript:
    @patch("youtube_transcript_api.YouTubeTranscriptApi")
    def test_prefers_manual_captions(self, MockApi):
        mock_transcript = MagicMock()
        mock_transcript.fetch.return_value = [_make_snippet("Manual caption", 0)]
        mock_list = MagicMock()
        mock_list.find_manually_created_transcript.return_value = mock_transcript
        MockApi.return_value.list.return_value = mock_list

        result = fetch_transcript("dQw4w9WgXcQ")
        assert "Manual caption" in result

    @patch("youtube_transcript_api.YouTubeTranscriptApi")
    def test_falls_back_to_generated(self, MockApi):
        from youtube_transcript_api import NoTranscriptFound

        mock_transcript = MagicMock()
        mock_transcript.fetch.return_value = [_make_snippet("Auto caption", 0)]
        mock_list = MagicMock()
        mock_list.find_manually_created_transcript.side_effect = NoTranscriptFound("vid", [], [])
        mock_list.find_generated_transcript.return_value = mock_transcript
        MockApi.return_value.list.return_value = mock_list

        result = fetch_transcript("dQw4w9WgXcQ")
        assert "Auto caption" in result

    @patch("youtube_transcript_api.YouTubeTranscriptApi")
    def test_raises_transcript_unavailable_when_disabled(self, MockApi):
        from youtube_transcript_api import TranscriptsDisabled

        MockApi.return_value.list.side_effect = TranscriptsDisabled("vid")

        with pytest.raises(TranscriptUnavailable):
            fetch_transcript("dQw4w9WgXcQ")

    @patch("youtube_transcript_api.YouTubeTranscriptApi")
    def test_raises_transcript_unavailable_when_not_found(self, MockApi):
        from youtube_transcript_api import NoTranscriptFound

        mock_list = MagicMock()
        mock_list.find_manually_created_transcript.side_effect = NoTranscriptFound("vid", [], [])
        mock_list.find_generated_transcript.side_effect = NoTranscriptFound("vid", [], [])
        MockApi.return_value.list.return_value = mock_list

        with pytest.raises(TranscriptUnavailable):
            fetch_transcript("dQw4w9WgXcQ")
