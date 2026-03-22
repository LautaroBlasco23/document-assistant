from abc import ABC, abstractmethod

from core.model.generated_content import Flashcard, QAPair, Summary


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

    # --- QA Pairs ---

    @abstractmethod
    def get_qa_pairs(
        self, document_hash: str, chapter_index: int | None = None
    ) -> list[QAPair]:
        """Get Q&A pairs. If chapter_index is None, return all for the document."""

    @abstractmethod
    def save_qa_pairs(self, pairs: list[QAPair]) -> None:
        """Save Q&A pairs. Deletes existing for the same (document_hash, chapter_index) first."""

    # --- Flashcards ---

    @abstractmethod
    def get_flashcards(
        self, document_hash: str, chapter_index: int | None = None
    ) -> list[Flashcard]:
        """Get flashcards. If chapter_index is None, return all for the document."""

    @abstractmethod
    def save_flashcards(self, flashcards: list[Flashcard]) -> None:
        """Save flashcards. Deletes existing for the same (document_hash, chapter_index) first."""

    # --- Cleanup ---

    @abstractmethod
    def delete_by_document(self, document_hash: str) -> None:
        """Delete all generated content for a document (used when document is deleted)."""
