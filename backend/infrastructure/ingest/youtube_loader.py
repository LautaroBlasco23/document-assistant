"""YouTube transcript fetcher via youtube-transcript-api + yt-dlp metadata."""

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_MAX_DURATION_SECONDS = 4 * 60 * 60  # 4 hours

_YT_ID_RE = re.compile(
    r"(?:youtube\.com/(?:watch\?v=|shorts/|embed/)|youtu\.be/)"
    r"([A-Za-z0-9_-]{11})"
)


class TranscriptUnavailable(Exception):
    """Raised when no captions are available for a video."""


class VideoUnavailable(Exception):
    """Raised when yt-dlp cannot reach/parse the video."""


@dataclass
class VideoMetadata:
    video_id: str
    title: str
    channel: str
    duration_seconds: int


def extract_video_id(url: str) -> str:
    """Parse video ID from various YouTube URL forms. Raises ValueError on failure."""
    m = _YT_ID_RE.search(url)
    if m:
        return m.group(1)
    raise ValueError(f"Cannot extract YouTube video ID from URL: {url!r}")


def fetch_metadata(video_id: str) -> VideoMetadata:
    """Fetch title, channel, duration via yt-dlp (no API key required)."""
    import yt_dlp  # noqa: PLC0415

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
    }
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        raise VideoUnavailable(f"yt-dlp could not fetch video {video_id}: {exc}") from exc

    title = info.get("title") or video_id
    channel = info.get("uploader") or info.get("channel") or "Unknown"
    duration = int(info.get("duration") or 0)

    if duration > _MAX_DURATION_SECONDS:
        raise VideoUnavailable(
            f"Video is {duration // 3600}h long — only videos up to 4 hours are supported."
        )

    return VideoMetadata(
        video_id=video_id,
        title=title,
        channel=channel,
        duration_seconds=duration,
    )


def fetch_transcript(video_id: str, languages: list[str] | None = None) -> str:
    """Fetch captions and return a normalized transcript string with timestamp markers.

    Raises TranscriptUnavailable when no captions exist.
    """
    from youtube_transcript_api import (  # noqa: PLC0415
        NoTranscriptFound,
        TranscriptsDisabled,
        YouTubeTranscriptApi,
    )

    langs = languages or ["en", "en-US", "en-GB", "a.en"]
    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        # Prefer manual captions over auto-generated
        try:
            transcript = transcript_list.find_manually_created_transcript(langs)
        except NoTranscriptFound:
            transcript = transcript_list.find_generated_transcript(langs)
        entries = transcript.fetch()
    except TranscriptsDisabled:
        raise TranscriptUnavailable("Transcripts are disabled for this video.")
    except NoTranscriptFound:
        raise TranscriptUnavailable(
            "No captions found in the requested languages. "
            "Try a video with English captions or auto-generated subtitles."
        )
    except Exception as exc:
        raise TranscriptUnavailable(f"Could not fetch transcript: {exc}") from exc

    return _normalize_transcript(entries)


def _normalize_transcript(entries) -> str:
    """Convert raw transcript entries into a readable string with timestamp markers."""
    lines: list[str] = []
    for entry in entries:
        # v1.x returns FetchedTranscriptSnippet objects; older versions returned dicts
        if hasattr(entry, "start"):
            start = entry.start
            text = (entry.text or "").strip()
        else:
            start = entry.get("start", 0)
            text = (entry.get("text") or "").strip()
        if not text:
            continue
        timestamp = _format_timestamp(start)
        lines.append(f"[{timestamp}] {text}")
    return "\n".join(lines)


def _format_timestamp(seconds: float) -> str:
    total = int(seconds)
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"
