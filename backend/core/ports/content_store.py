from abc import ABC, abstractmethod

from core.model.document_metadata import DocumentMetadata
from core.model.exam import ExamResult
from core.model.generated_content import Flashcard, Summary


class ContentStore(ABC):
    """Port for persisting AI-generated content."""

    # --- Summaries ---

    @abstractmethod
    def get_summary(self, document_hash: str, chapter_index: int) -> Summary | None:
        """Get summary for a specific chapter. Returns None if not found."""

    @abstractmethod
    def get_summaries(self, document_hash: str) -> list[Summary]:
        """Get all summaries for a document."""

    @abstractmethod
    def save_summary(self, summary: Summary) -> None:
        """Upsert a summary (replace if exists for same document_hash + chapter_index)."""

    # --- Flashcards ---

    @abstractmethod
    def get_flashcards(
        self,
        document_hash: str,
        chapter_index: int | None = None,
        status: str | None = "approved",
    ) -> list[Flashcard]:
        """Get flashcards. If chapter_index is None, return all for the document.
        If status is None, return all regardless of status. Default returns only approved cards."""

    @abstractmethod
    def save_flashcards(self, flashcards: list[Flashcard]) -> None:
        """Save flashcards. Deletes existing for the same (document_hash, chapter_index) first."""

    @abstractmethod
    def approve_flashcards(self, flashcard_ids: list[str]) -> int:
        """Bulk-update flashcard status to 'approved'. Returns count of updated rows."""

    @abstractmethod
    def delete_flashcards_by_ids(self, flashcard_ids: list[str]) -> int:
        """Hard-delete flashcards by their IDs. Returns count of deleted rows."""

    @abstractmethod
    def approve_all_flashcards(
        self, document_hash: str, chapter_index: int | None = None
    ) -> int:
        """Approve all pending flashcards for a document (optionally filtered by chapter).
        Returns count of updated rows."""

    # --- Metadata ---

    @abstractmethod
    def get_metadata(self, document_hash: str) -> DocumentMetadata | None:
        """Get the user-provided metadata for a document. Returns None if not set."""

    @abstractmethod
    def save_metadata(self, document_hash: str, metadata: DocumentMetadata) -> None:
        """Upsert the user-provided metadata for a document."""

    # --- Cleanup ---

    @abstractmethod
    def delete_by_document(self, document_hash: str) -> None:
        """Delete all generated content for a document (used when document is deleted)."""

    @abstractmethod
    def delete_summary(self, document_hash: str, chapter_index: int) -> None:
        """Delete the summary for a specific chapter."""

    @abstractmethod
    def delete_chapter(self, document_hash: str, chapter_index: int) -> None:
        """Delete all generated content for a specific chapter (summaries + flashcards)."""

    # --- Exam results ---

    @abstractmethod
    def save_exam_result(self, result: ExamResult) -> None:
        """Persist a completed exam session."""

    @abstractmethod
    def get_exam_results(self, document_hash: str, chapter_index: int) -> list[ExamResult]:
        """Get all exam results for a chapter, ordered by completed_at DESC."""

    @abstractmethod
    def get_chapter_level(self, document_hash: str, chapter_index: int) -> int:
        """Return 0 (none), 1 (Completed), 2 (Gold), or 3 (Platinum).
        Count total passed=true exams. Cap at 3. Failed exams do not reduce the level."""

    @abstractmethod
    def reset_exam_progress(self, document_hash: str, chapter_index: int) -> None:
        """Delete all exam results for a chapter (called on flashcard regeneration)."""

    # --- Custom documents ---

    @abstractmethod
    def save_custom_document(self, document_hash: str, title: str, content: str) -> None:
        """Persist raw text content for a custom document."""

    @abstractmethod
    def get_custom_document(self, document_hash: str) -> tuple[str, str] | None:
        """Get (title, content) for a custom document. Returns None if not found."""

    @abstractmethod
    def append_custom_document(self, document_hash: str, new_content: str) -> str:
        """Append text to a custom document. Returns the updated full content.
        Raises ValueError if document_hash not found."""

    @abstractmethod
    def delete_custom_document(self, document_hash: str) -> None:
        """Delete a custom document's raw content."""
