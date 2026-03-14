from dataclasses import dataclass, field


@dataclass
class Page:
    number: int
    text: str


@dataclass
class Chapter:
    index: int
    title: str
    pages: list[Page] = field(default_factory=list)


@dataclass
class Document:
    source_path: str
    title: str
    file_hash: str
    chapters: list[Chapter] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
