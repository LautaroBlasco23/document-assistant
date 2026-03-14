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


def test_chunk_size_within_max():
    long_text = " ".join(f"word{i}" for i in range(1000))
    doc = _make_doc([[long_text]])
    splitter = ChapterAwareSplitter(max_tokens=100, overlap_tokens=20)
    chunks = splitter.split(doc)
    for c in chunks:
        assert c.token_count <= 100


def test_overlap_present():
    # Create text long enough for multiple chunks with overlap
    words = [f"word{i}" for i in range(300)]
    text = " ".join(words)
    doc = _make_doc([[text]])
    splitter = ChapterAwareSplitter(max_tokens=100, overlap_tokens=20)
    chunks = splitter.split(doc)

    assert len(chunks) >= 2
    # Last words of chunk[0] should appear at start of chunk[1]
    c0_words = chunks[0].text.split()
    c1_words = chunks[1].text.split()
    overlap_words = c0_words[-20:]
    assert c1_words[:20] == overlap_words


def test_chapter_boundary_not_crossed():
    ch1_text = " ".join(f"alpha{i}" for i in range(200))
    ch2_text = " ".join(f"beta{i}" for i in range(200))
    doc = _make_doc([[ch1_text], [ch2_text]])
    splitter = ChapterAwareSplitter(max_tokens=100, overlap_tokens=20)
    chunks = splitter.split(doc)

    for c in chunks:
        # A chunk should contain only alpha OR only beta words
        has_alpha = "alpha0" in c.text or "alpha" in c.text
        has_beta = "beta0" in c.text or "beta" in c.text
        assert not (has_alpha and has_beta), "Chunk crosses chapter boundary!"


def test_empty_document():
    doc = _make_doc([])
    splitter = ChapterAwareSplitter()
    assert splitter.split(doc) == []


def test_metadata_populated():
    doc = _make_doc([["word " * 50]])
    splitter = ChapterAwareSplitter(max_tokens=30, overlap_tokens=5)
    chunks = splitter.split(doc)
    for c in chunks:
        assert c.metadata is not None
        assert c.metadata.chapter_index == 0
        assert c.id != ""
