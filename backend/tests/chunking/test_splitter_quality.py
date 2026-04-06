"""Quality tests for the paragraph-aware ChapterAwareSplitter."""

from core.model.document import Chapter, Document, Page
from infrastructure.chunking.splitter import ChapterAwareSplitter


def _make_doc(pages_per_chapter: list[list[str]]) -> Document:
    chapters = []
    for ci, page_texts in enumerate(pages_per_chapter):
        pages = [Page(number=i + 1, text=t) for i, t in enumerate(page_texts)]
        chapters.append(Chapter(index=ci, title=f"Ch {ci}", pages=pages))
    return Document(
        source_path="test.pdf",
        title="Test",
        file_hash="abc",
        chapters=chapters,
    )


def test_chunk_text_does_not_contain_page_marker():
    page1 = "First page paragraph one.\n\nFirst page paragraph two."
    page2 = "Second page paragraph one.\n\nSecond page paragraph two."
    doc = _make_doc([[page1, page2]])
    splitter = ChapterAwareSplitter(max_tokens=20, overlap_tokens=5)
    chunks = splitter.split(doc)
    assert chunks, "Expected at least one chunk"
    for chunk in chunks:
        assert "---PAGE---" not in chunk.text


def test_chunk_boundaries_fall_on_paragraph_breaks():
    # 6 short paragraphs, ~5 words each; max_tokens=12 fits ~2 paragraphs per chunk
    paras = [f"Paragraph {i} has five words." for i in range(6)]
    page_text = "\n\n".join(paras)
    doc = _make_doc([[page_text]])
    splitter = ChapterAwareSplitter(max_tokens=12, overlap_tokens=0)
    chunks = splitter.split(doc)

    assert len(chunks) >= 2
    # Each chunk text should start with the first word of some original paragraph
    para_first_words = {p.split()[0] for p in paras}
    for chunk in chunks:
        first_word = chunk.text.split()[0]
        assert first_word in para_first_words, (
            f"Chunk starts with '{first_word}' which is not a paragraph-start word"
        )


def test_chunk_overlap_respects_paragraphs():
    # Build paragraphs so that the overlap paragraph from chunk N appears in chunk N+1
    paras = [f"Para {i}: " + " ".join(f"word{i}x{j}" for j in range(8)) for i in range(6)]
    page_text = "\n\n".join(paras)
    # max_tokens=20 fits ~2 paragraphs (9 words each); overlap=10 seeds ~1 paragraph
    doc = _make_doc([[page_text]])
    splitter = ChapterAwareSplitter(max_tokens=20, overlap_tokens=10)
    chunks = splitter.split(doc)

    assert len(chunks) >= 2
    # The overlapping chunk should contain a full paragraph from the previous chunk
    for i in range(1, len(chunks)):
        prev_text = chunks[i - 1].text
        curr_text = chunks[i].text
        # Find any paragraph that appears (as substring) in both chunks
        prev_paras = [p.strip() for p in prev_text.split("\n\n") if p.strip()]
        shared = [p for p in prev_paras if p in curr_text]
        assert shared, (
            f"Chunk {i} shares no full paragraph with chunk {i-1}; "
            f"overlap should contain whole paragraphs"
        )


def test_long_paragraph_falls_back_to_word_window():
    # Single paragraph with ~600 words; max_tokens=200 -> must produce multiple chunks
    long_para = " ".join(f"word{i}" for i in range(600))
    doc = _make_doc([[long_para]])
    splitter = ChapterAwareSplitter(max_tokens=200, overlap_tokens=50)
    chunks = splitter.split(doc)

    assert len(chunks) >= 3

    # Concatenating the non-overlapping portions should recover original word order.
    # Collect unique words in order (skip overlap region).
    seen: set[str] = set()
    all_words: list[str] = []
    for chunk in chunks:
        for w in chunk.text.split():
            if w not in seen:
                seen.add(w)
                all_words.append(w)

    original_words = long_para.split()
    # All original words should appear
    assert set(all_words) == set(original_words)


def test_page_number_tracking_preserved():
    # Page 1 has some paragraphs; page 2 has other paragraphs.
    # Chunks derived from page 2 text should have page_number == 2.
    page1 = "Alpha paragraph one.\n\nAlpha paragraph two."
    page2 = "Beta paragraph one.\n\nBeta paragraph two."
    doc = _make_doc([[page1, page2]])
    # Small max_tokens so each paragraph becomes its own chunk
    splitter = ChapterAwareSplitter(max_tokens=5, overlap_tokens=0)
    chunks = splitter.split(doc)

    beta_chunks = [c for c in chunks if "Beta" in c.text]
    assert beta_chunks, "Expected at least one chunk from page 2"
    for c in beta_chunks:
        assert c.metadata.page_number == 2, (
            f"Expected page_number=2 for Beta chunk, got {c.metadata.page_number}"
        )


def test_empty_chapter_returns_no_chunks():
    doc = _make_doc([[""]])
    splitter = ChapterAwareSplitter()
    chunks = splitter.split(doc)
    assert chunks == []
