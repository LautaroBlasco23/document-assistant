import logging
from dataclasses import dataclass
from pathlib import Path

import ebooklib
from ebooklib import epub
from lxml import etree

from core.model.document import Chapter, Document, Page
from infrastructure.config import EpubConfig
from infrastructure.ingest.normalizer import normalize

logger = logging.getLogger(__name__)


@dataclass
class ChapterPreview:
    """Lightweight chapter metadata without full page text."""

    index: int
    title: str
    page_start: int  # 1-based (EPUB has no page concept, use index + 1)
    page_end: int


def _get_metadata(book: epub.EpubBook, name: str) -> str:
    items = book.get_metadata("DC", name)
    if items:
        value = items[0]
        return value[0] if isinstance(value, tuple) else str(value)
    return ""


_XHTML = "http://www.w3.org/1999/xhtml"

_BLOCK_TAGS = {
    f"{{{_XHTML}}}{t}"
    for t in ("p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "td", "th")
}


def _extract_text(root: etree._Element) -> str:
    """Walk the element tree and concatenate text with newlines at block boundaries."""
    parts: list[str] = []

    def _walk(el: etree._Element) -> None:
        if el.tag in _BLOCK_TAGS:
            text = "".join(el.itertext()).strip()
            if text:
                parts.append(text)
        else:
            for child in el:
                _walk(child)

    _walk(root)
    return "\n".join(parts)


def _extract_title_only(item: epub.EpubItem) -> str:
    """Extract title from an EPUB item without loading full text."""
    try:
        content = item.get_content()
        root = etree.fromstring(content)
    except Exception:
        return ""

    title = ""
    title_el = root.find(".//{http://www.w3.org/1999/xhtml}title")
    if title_el is not None and title_el.text:
        title = title_el.text.strip()

    if not title:
        for tag in ("h1", "h2"):
            el = root.find(f".//{{{_XHTML}}}{tag}")
            if el is not None:
                title = "".join(el.itertext()).strip()
                break

    return title


def _parse_item(item: epub.EpubItem) -> tuple[str, str]:
    """Return (title, plain_text) for an EPUB spine item."""
    try:
        content = item.get_content()
        root = etree.fromstring(content)
    except Exception:
        return "", ""

    # Extract title from <title> or first <h1>/<h2>
    title = ""
    title_el = root.find(".//{http://www.w3.org/1999/xhtml}title")
    if title_el is not None and title_el.text:
        title = title_el.text.strip()

    if not title:
        for tag in ("h1", "h2"):
            el = root.find(f".//{{{_XHTML}}}{tag}")
            if el is not None:
                title = "".join(el.itertext()).strip()
                break

    text = _extract_text(root)
    return title, text


def _collect_toc_entries(
    toc_nodes: list,
    depth: int,
    target_depth: int,
    result: dict[str, tuple[str, str]],
) -> None:
    """
    Recursively walk the ebooklib ToC tree and collect hrefs at target_depth.

    toc_nodes: list of either epub.Link or tuple(epub.Section, [children])
    depth: current depth (1 = top level)
    target_depth: the depth to treat as chapter boundaries
    result: mapping from filename (href without fragment) to (chapter title, original_href)
    """
    for node in toc_nodes:
        if isinstance(node, epub.Link):
            if depth == target_depth:
                filename = node.href.split("#")[0]
                if filename and filename not in result:
                    result[filename] = (node.title or "", node.href)
        elif isinstance(node, tuple) and len(node) == 2:
            section, children = node
            if depth == target_depth:
                # The section itself is a chapter boundary
                href = getattr(section, "href", "") or ""
                filename = href.split("#")[0]
                if filename and filename not in result:
                    result[filename] = (section.title or "", href)
            else:
                # Recurse into children to find deeper entries
                _collect_toc_entries(children, depth + 1, target_depth, result)


def _build_toc_groups(
    book: epub.EpubBook,
    spine_items: list[epub.EpubItem],
    depth: int,
) -> list[tuple[str, str, list[epub.EpubItem]]]:
    """
    Returns a list of (chapter_title, toc_href, [spine_items]) groups.

    Uses book.toc to group spine items under their top-level chapter.
    toc_href is the original TOC href (may include fragment) for EPUB navigation.
    Falls back to one-item-per-group if toc is empty.
    """
    toc = book.toc
    if not toc:
        logger.debug("EPUB has no ToC; falling back to one spine item per chapter")
        groups = []
        for item in spine_items:
            title = _extract_title_only(item)
            groups.append((title, "", [item]))
        return groups

    # Build href -> (chapter title, original_href) mapping from ToC at the requested depth
    toc_map: dict[str, tuple[str, str]] = {}
    _collect_toc_entries(list(toc), depth=1, target_depth=depth, result=toc_map)

    if not toc_map:
        # ToC exists but the requested depth has no entries — fall back
        logger.debug(
            "EPUB ToC has no entries at depth %d; falling back to one spine item per chapter",
            depth,
        )
        groups = []
        for item in spine_items:
            title = _extract_title_only(item)
            groups.append((title, "", [item]))
        return groups

    # Map each spine item to its chapter group
    # A spine item belongs to the chapter whose ToC href matches the item's file_name.
    # Items not found in the ToC are appended to the previous group (or a default group).
    groups: list[tuple[str, str, list[epub.EpubItem]]] = []
    current_title: str | None = None
    current_href: str = ""
    current_items: list[epub.EpubItem] = []

    for item in spine_items:
        file_name = item.file_name
        # Normalize: strip leading path prefix variants that might differ
        # ebooklib may store "OEBPS/chapter01.xhtml" while ToC has "chapter01.xhtml"
        bare_name = file_name.split("/")[-1] if "/" in file_name else file_name

        matched_title: str | None = None
        matched_href: str = ""
        if file_name in toc_map:
            matched_title, matched_href = toc_map[file_name]
        elif bare_name in toc_map:
            matched_title, matched_href = toc_map[bare_name]

        if matched_title is not None:
            # This item starts a new chapter group
            if current_items:
                groups.append((current_title or "", current_href, current_items))
            current_title = matched_title
            current_href = matched_href
            current_items = [item]
        else:
            # Belongs to the current group (or starts an unnamed first group)
            if current_items or current_title is not None:
                current_items.append(item)
            else:
                # Before first ToC entry; start a preamble group
                current_title = None
                current_href = ""
                current_items = [item]

    if current_items:
        groups.append((current_title or "", current_href, current_items))

    logger.debug(
        "ToC grouping: %d spine items -> %d groups (depth=%d)",
        len(spine_items),
        len(groups),
        depth,
    )
    return groups


def _apply_min_words_merge(
    groups: list[tuple[str, str, list[epub.EpubItem]]],
    texts: list[str],
    min_words: int,
) -> list[tuple[str, str, str]]:
    """
    Merge groups whose text is shorter than min_words into the previous group.

    groups: list of (title, toc_href, [items]) — same order as texts
    texts: pre-extracted concatenated text for each group
    min_words: minimum word count; groups below this are merged into the previous group

    Returns list of (title, toc_href, merged_text).
    The merged group keeps the previous group's title and toc_href.
    """
    if not groups:
        return []

    result: list[tuple[str, str, str]] = []

    for (title, toc_href, _items), text in zip(groups, texts):
        word_count = len(text.split())
        if word_count < min_words and result:
            # Merge into the previous group (keep previous title and href)
            prev_title, prev_href, prev_text = result[-1]
            result[-1] = (prev_title, prev_href, prev_text + "\n\n" + text)
            logger.debug(
                "Merged short group '%s' (%d words) into '%s'",
                title,
                word_count,
                prev_title,
            )
        else:
            result.append((title, toc_href, text))

    return result


def load_epub(
    path: Path,
    file_hash: str,
    original_filename: str = "",
    epub_config: EpubConfig | None = None,
) -> Document:
    """Extract a Document from an EPUB file."""
    cfg = epub_config or EpubConfig()

    book = epub.read_epub(str(path))

    display_name = original_filename or path.name
    title = _get_metadata(book, "title") or Path(display_name).stem
    author = _get_metadata(book, "creator") or ""

    spine_items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))

    groups = _build_toc_groups(book, spine_items, depth=cfg.chapter_depth)

    # Extract text for each group (concatenate spine item texts with separator)
    group_texts: list[str] = []
    for _group_title, _toc_href, items in groups:
        parts = []
        for item in items:
            _, raw_text = _parse_item(item)
            if raw_text.strip():
                parts.append(raw_text)
        group_texts.append("\n\n".join(parts))

    # Apply min_chapter_words merging
    merged = _apply_min_words_merge(groups, group_texts, cfg.min_chapter_words)

    chapters: list[Chapter] = []
    for idx, (chapter_title, toc_href, text) in enumerate(merged):
        if not text.strip():
            continue

        normalized = normalize([text])
        page = Page(number=1, text=normalized[0])
        chapters.append(
            Chapter(
                index=idx,
                title=chapter_title or f"Chapter {idx + 1}",
                pages=[page],
                toc_href=toc_href,
            )
        )

    # Re-index sequentially (some items may have been skipped)
    for i, ch in enumerate(chapters):
        ch.index = i

    logger.info(
        "Loaded EPUB %s: %d spine items -> %d chapters (depth=%d, min_words=%d)",
        display_name,
        len(spine_items),
        len(chapters),
        cfg.chapter_depth,
        cfg.min_chapter_words,
    )
    return Document(
        source_path=str(path),
        title=title,
        file_hash=file_hash,
        original_filename=original_filename or path.name,
        chapters=chapters,
        metadata={"author": author},
    )


def preview_epub(
    path: Path,
    file_hash: str,
    epub_config: EpubConfig | None = None,
) -> tuple[Document | None, list[ChapterPreview]]:
    """Extract chapter structure from an EPUB without loading full page text.

    Returns (doc, chapters) where doc has no populated chapters (just metadata).
    chapters is the list of ChapterPreview objects.
    """
    cfg = epub_config or EpubConfig()

    book = epub.read_epub(str(path))

    title = _get_metadata(book, "title") or path.stem
    author = _get_metadata(book, "creator") or ""

    spine_items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
    groups = _build_toc_groups(book, spine_items, depth=cfg.chapter_depth)

    # For preview we need to apply min_chapter_words as well so the count matches load_epub.
    # We do a lightweight text extraction just for word counting.
    group_texts: list[str] = []
    for _group_title, _toc_href, items in groups:
        parts = []
        for item in items:
            _, raw_text = _parse_item(item)
            if raw_text.strip():
                parts.append(raw_text)
        group_texts.append("\n\n".join(parts))

    merged = _apply_min_words_merge(groups, group_texts, cfg.min_chapter_words)

    chapters: list[ChapterPreview] = []
    idx = 0
    for chapter_title, _toc_href, text in merged:
        if not text.strip():
            continue
        chapters.append(
            ChapterPreview(
                index=idx,
                title=chapter_title or f"Chapter {idx + 1}",
                page_start=idx + 1,
                page_end=idx + 1,
            )
        )
        idx += 1

    result_doc = Document(
        source_path=str(path),
        title=title,
        file_hash=file_hash,
        original_filename=path.name,
        chapters=[],  # Not populated - use full load for that
        metadata={"author": author},
    )

    logger.info(
        "Preview EPUB %s: %d spine items -> %d chapters (depth=%d, min_words=%d)",
        path.name,
        len(spine_items),
        len(chapters),
        cfg.chapter_depth,
        cfg.min_chapter_words,
    )
    return result_doc, chapters
