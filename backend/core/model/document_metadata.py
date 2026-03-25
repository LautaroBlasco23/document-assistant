from dataclasses import dataclass


@dataclass
class DocumentMetadata:
    description: str = ""
    document_type: str = ""  # One of: book, paper, documentation, article, notes, other
    file_extension: str = ""  # e.g., 'pdf', 'epub'
