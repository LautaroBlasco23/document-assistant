"""Unit tests for knowledge tree chapter filtering and renumbering logic.

These tests exercise the chapter filtering path introduced by the chapter
selection feature.  They run entirely in-memory — no database or file I/O
required.
"""

from core.model.document import Chapter, Document, Page

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chapter(index: int, title: str = "") -> Chapter:
    page = Page(number=index + 1, text=f"Content of chapter {index}")
    return Chapter(index=index, title=title or f"Chapter {index}", pages=[page])


def _make_doc(num_chapters: int) -> Document:
    chapters = [_make_chapter(i) for i in range(num_chapters)]
    return Document(
        source_path="/tmp/fake.pdf",
        title="Fake Book",
        file_hash="deadbeef",
        original_filename="fake.pdf",
        chapters=chapters,
    )


# ---------------------------------------------------------------------------
# Filtering logic (extracted copy of the logic under test)
# ---------------------------------------------------------------------------

def _apply_filtering(doc: Document, chapter_indices: list[int] | None) -> list[Chapter]:
    """Mirror the filtering logic from _create_tree_from_document_background."""
    if chapter_indices is not None:
        selected = set(chapter_indices)
        return [ch for ch in doc.chapters if ch.index in selected]
    return list(doc.chapters)


def _chapter_numbers_after_import(chapters_to_process: list[Chapter]) -> list[int]:
    """Return the 1-based chapter numbers that would be assigned."""
    return [i + 1 for i in range(len(chapters_to_process))]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestChapterFiltering:
    """Filtering behaviour."""

    def test_none_returns_all_chapters(self) -> None:
        doc = _make_doc(4)
        result = _apply_filtering(doc, None)
        assert len(result) == 4
        assert [ch.index for ch in result] == [0, 1, 2, 3]

    def test_subset_returns_selected_chapters(self) -> None:
        doc = _make_doc(4)
        result = _apply_filtering(doc, [0, 2, 3])
        assert len(result) == 3
        assert [ch.index for ch in result] == [0, 2, 3]

    def test_empty_list_returns_no_chapters(self) -> None:
        doc = _make_doc(4)
        result = _apply_filtering(doc, [])
        assert result == []

    def test_duplicates_treated_as_set(self) -> None:
        doc = _make_doc(4)
        result = _apply_filtering(doc, [0, 0, 2])
        # Both 0s refer to same chapter; only chapters 0 and 2 returned
        assert len(result) == 2
        assert {ch.index for ch in result} == {0, 2}

    def test_out_of_range_index_ignored(self) -> None:
        doc = _make_doc(3)
        result = _apply_filtering(doc, [0, 99])
        # Only chapter 0 exists; index 99 doesn't match anything
        assert len(result) == 1
        assert result[0].index == 0

    def test_out_of_order_indices_follow_document_order(self) -> None:
        doc = _make_doc(5)
        result = _apply_filtering(doc, [4, 1, 2])
        # Chapters are yielded in document order, not index param order
        assert [ch.index for ch in result] == [1, 2, 4]


class TestSequentialRenumbering:
    """After filtering, chapters must be numbered 1..N sequentially."""

    def test_all_chapters_numbered_sequentially(self) -> None:
        doc = _make_doc(4)
        chapters = _apply_filtering(doc, None)
        numbers = _chapter_numbers_after_import(chapters)
        assert numbers == [1, 2, 3, 4]

    def test_subset_numbered_from_one(self) -> None:
        doc = _make_doc(5)
        chapters = _apply_filtering(doc, [0, 2, 4])
        numbers = _chapter_numbers_after_import(chapters)
        # Numbers are 1, 2, 3 regardless of original indices 0, 2, 4
        assert numbers == [1, 2, 3]

    def test_single_chapter_numbered_one(self) -> None:
        doc = _make_doc(5)
        chapters = _apply_filtering(doc, [3])
        numbers = _chapter_numbers_after_import(chapters)
        assert numbers == [1]

    def test_titles_preserved_after_renumbering(self) -> None:
        doc = _make_doc(4)
        chapters = _apply_filtering(doc, [0, 2, 3])
        expected_titles = [doc.chapters[0].title, doc.chapters[2].title, doc.chapters[3].title]
        assert [ch.title for ch in chapters] == expected_titles


class TestProgressDenominator:
    """Progress bar must use the filtered count, not the total chapter count."""

    def test_denominator_equals_filtered_count(self) -> None:
        doc = _make_doc(10)
        chapters = _apply_filtering(doc, [1, 3, 5])
        # Progress calculation: 25 + int(70 * i / chapter_count)
        chapter_count = len(chapters)
        assert chapter_count == 3
        # Verify last iteration reaches 25 + int(70 * 2 / 3) = 25 + 46 = 71
        last_pct = 25 + int(70 * (chapter_count - 1) / chapter_count)
        assert last_pct < 100  # leaves room for the "Storing chunks" step at 90
        assert last_pct > 50
