from core.model.chunk import Chunk, ChunkMetadata
from core.model.document import Chapter, Document, Page


def test_document_creation():
    page = Page(number=1, text="Hello world")
    chapter = Chapter(index=0, title="Intro", pages=[page])
    doc = Document(source_path="test.pdf", title="Test", file_hash="abc123", chapters=[chapter])

    assert doc.title == "Test"
    assert len(doc.chapters) == 1
    assert doc.chapters[0].pages[0].text == "Hello world"


def test_chunk_creation():
    meta = ChunkMetadata(
        source_file="test.pdf",
        chapter_index=0,
        page_number=1,
        start_char=0,
        end_char=100,
    )
    chunk = Chunk(text="Some text", token_count=3, metadata=meta)

    assert chunk.text == "Some text"
    assert chunk.metadata.source_file == "test.pdf"
    assert len(chunk.id) > 0  # UUID generated
