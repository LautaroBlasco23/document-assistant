from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class ChunkMetadata:
    source_file: str
    chapter_index: int
    page_number: int
    start_char: int
    end_char: int


@dataclass
class Chunk:
    id: str = field(default_factory=lambda: str(uuid4()))
    text: str = ""
    token_count: int = 0
    metadata: ChunkMetadata | None = None
