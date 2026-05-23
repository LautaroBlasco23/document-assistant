import copy
import logging
import re
from dataclasses import dataclass
from pathlib import Path

import ebooklib
from ebooklib import epub
from lxml import etree

from core.model.document import Chapter, Document, ImageRef, Page
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


_IMG_PLACEHOLDER = "__IMG__{}__"


def _extract_text_with_images(root: etree._Element) -> tuple[str, list[ImageRef]]:
    """Extract text with __IMG__name__ placeholders in document order.

    Returns (text_with_placeholders, list_of_image_refs).
    """
    root = copy.deepcopy(root)
    images: list[ImageRef] = []

    for img_el in list(root.iter(f"{{{_XHTML}}}img")):
        src = img_el.get("src", "") or ""
        alt = img_el.get("alt", "") or ""
        name = src.split("/")[-1] if "/" in src else src
        if name:
            images.append(ImageRef(name=name, alt=alt))
            parent = img_el.getparent()
            if parent is not None:
                placeholder = etree.Element(f"{{{_XHTML}}}p")
                placeholder.text = _IMG_PLACEHOLDER.format(name)
                placeholder.tail = img_el.tail
                parent.replace(img_el, placeholder)

    return _extract_text(root), images


def _extract_markdown(root: etree._Element) -> str:
    """Convert XHTML element tree to markdown text.

    Handles headings, paragraphs, lists, blockquotes, inline formatting,
    horizontal rules, and tables. Image placeholders (__IMG__name__) are
    expected to have been inserted already by _extract_markdown_with_images.
    """
    lines: list[str] = []

    def _inline(el: etree._Element) -> str:
        """Convert inline children of an element to markdown text."""
        parts: list[str] = []
        if el.text:
            parts.append(el.text)
        for child in el:
            tag = child.tag
            inner = _inline(child)
            tail = child.tail or ""
            if tag in (f"{{{_XHTML}}}strong", f"{{{_XHTML}}}b"):
                parts.append(f"**{inner.strip()}**")
            elif tag in (f"{{{_XHTML}}}em", f"{{{_XHTML}}}i"):
                parts.append(f"*{inner.strip()}*")
            elif tag == f"{{{_XHTML}}}code":
                parts.append(f"`{inner.strip()}`")
            elif tag == f"{{{_XHTML}}}a":
                href = child.get("href", "")
                parts.append(f"[{inner.strip()}]({href})" if href else inner)
            elif tag == f"{{{_XHTML}}}br":
                parts.append("  \n")
            elif tag == f"{{{_XHTML}}}img":
                src = child.get("src", "")
                name = src.split("/")[-1] if "/" in src else src
                parts.append(f"__IMG__{name}__")
            else:
                parts.append(inner)
            if tail:
                parts.append(tail)
        return "".join(parts)

    def _walk(el: etree._Element, depth: int = 0, ordered: bool = False, idx: int = 1) -> None:
        tag = el.tag
        if not isinstance(tag, str):
            return

        # Container / structural tags — recurse into children
        if tag in (
            f"{{{_XHTML}}}html", f"{{{_XHTML}}}body", f"{{{_XHTML}}}div",
            f"{{{_XHTML}}}section", f"{{{_XHTML}}}article", f"{{{_XHTML}}}header",
            f"{{{_XHTML}}}main", f"{{{_XHTML}}}nav", f"{{{_XHTML}}}footer",
            f"{{{_XHTML}}}aside", f"{{{_XHTML}}}figure", f"{{{_XHTML}}}figcaption",
        ):
            for child in el:
                _walk(child, depth, ordered, idx)
            return

        # Skip head content (title, meta, etc.)
        if tag == f"{{{_XHTML}}}head":
            return

        # Paragraph
        if tag == f"{{{_XHTML}}}p":
            text = _inline(el).strip()
            if text:
                lines.append(text + "\n")
            return

        # Headings
        local = tag.split("}")[-1]
        if local.startswith("h") and len(local) == 2 and local[1].isdigit():
            level = int(local[1])
            text = _inline(el).strip()
            if text:
                lines.append(f"{'#' * level} {text}\n")
            return

        # Blockquote
        if tag == f"{{{_XHTML}}}blockquote":
            text = _inline(el).strip()
            for line in text.split("\n"):
                lines.append(f"> {line}")
            lines.append("\n")
            return

        # Unordered list
        if tag == f"{{{_XHTML}}}ul":
            for child in el:
                _walk(child, depth, False, 1)
            lines.append("\n")
            return

        # Ordered list
        if tag == f"{{{_XHTML}}}ol":
            i = 1
            for child in el:
                _walk(child, depth, True, i)
                i += 1
            lines.append("\n")
            return

        # List item
        if tag == f"{{{_XHTML}}}li":
            indent = "  " * depth
            prefix = f"{indent}{idx}. " if ordered else f"{indent}- "
            text = _inline(el).strip()
            lines.append(f"{prefix}{text}")
            for child in el:
                child_tag = child.tag
                if not isinstance(child_tag, str):
                    continue
                child_local = child_tag.split("}")[-1]
                if child_local in ("ul", "ol"):
                    _walk(child, depth + 1, child_local == "ol", 1)
            return

        # Horizontal rule
        if tag == f"{{{_XHTML}}}hr":
            lines.append("---\n")
            return

        # Table structure — recurse through container tags, emit pipe rows
        if tag in (
            f"{{{_XHTML}}}table", f"{{{_XHTML}}}thead",
            f"{{{_XHTML}}}tbody", f"{{{_XHTML}}}tfoot",
        ):
            for child in el:
                _walk(child, depth, ordered, idx)
            return

        if tag == f"{{{_XHTML}}}tr":
            cells = []
            for child in el:
                if child.tag in (f"{{{_XHTML}}}td", f"{{{_XHTML}}}th"):
                    cells.append(_inline(child).strip())
            if cells:
                lines.append("| " + " | ".join(cells) + " |\n")
            return

        # Fallback for unknown block-level elements: emit inline text
        text = _inline(el).strip()
        if text:
            lines.append(text + "\n")

    _walk(root)
    result = "".join(lines)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def _extract_markdown_with_images(root: etree._Element) -> tuple[str, list[ImageRef]]:
    """Extract markdown with __IMG__name__ placeholders in document order.

    Returns (markdown_text_with_placeholders, list_of_image_refs).
    """
    root = copy.deepcopy(root)
    images: list[ImageRef] = []

    for img_el in list(root.iter(f"{{{_XHTML}}}img")):
        src = img_el.get("src", "") or ""
        alt = img_el.get("alt", "") or ""
        name = src.split("/")[-1] if "/" in src else src
        if name:
            images.append(ImageRef(name=name, alt=alt))
            parent = img_el.getparent()
            if parent is not None:
                placeholder = etree.Element(f"{{{_XHTML}}}p")
                placeholder.text = _IMG_PLACEHOLDER.format(name)
                placeholder.tail = img_el.tail
                parent.replace(img_el, placeholder)

    return _extract_markdown(root), images


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


def _parse_item(
    item: epub.EpubItem,
    image_map: dict[str, bytes] | None = None,
) -> tuple[str, str, list[ImageRef]]:
    """Return (title, markdown_text, images) for an EPUB spine item."""
    try:
        content = item.get_content()
        root = etree.fromstring(content)
    except Exception:
        return "", "", []

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

    if image_map is not None:
        text, images = _extract_markdown_with_images(root)
    else:
        text = _extract_markdown(root)
        images = []

    return title, text, images


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


def _build_image_map(book: epub.EpubBook) -> dict[str, bytes]:
    """Build {bare_filename: image_bytes} map from EPUB image items."""
    image_map: dict[str, bytes] = {}
    for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
        name = item.file_name.split("/")[-1] if "/" in item.file_name else item.file_name
        if name and name not in image_map:
            image_map[name] = item.get_content()
    return image_map


def _merge_group_data_with_images(
    group_data: list[tuple[str, str, str, list[ImageRef]]],
    min_words: int,
) -> list[tuple[str, str, str, list[ImageRef]]]:
    """Merge groups whose text is shorter than min_words into the previous group.

    Each tuple: (title, toc_href, text, images).
    Merged group keeps the previous group's title and toc_href.
    """
    if not group_data:
        return []

    result: list[tuple[str, str, str, list[ImageRef]]] = []

    for title, toc_href, text, imgs in group_data:
        word_count = len(text.split())
        if word_count < min_words and result:
            prev_title, prev_href, prev_text, prev_imgs = result[-1]
            result[-1] = (prev_title, prev_href, prev_text + "\n\n" + text, prev_imgs + imgs)
        else:
            result.append((title, toc_href, text, imgs))

    return result


def load_epub(
    path: Path,
    file_hash: str,
    original_filename: str = "",
    epub_config: EpubConfig | None = None,
) -> tuple[Document, dict[str, bytes]]:
    """Extract a Document from an EPUB file.

    Returns (Document, {image_name: image_bytes}).
    """
    cfg = epub_config or EpubConfig()

    book = epub.read_epub(str(path))
    image_map = _build_image_map(book)

    display_name = original_filename or path.name
    title = _get_metadata(book, "title") or Path(display_name).stem
    author = _get_metadata(book, "creator") or ""

    spine_items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))

    groups = _build_toc_groups(book, spine_items, depth=cfg.chapter_depth)

    # Extract text and images for each group
    group_data: list[tuple[str, str, str, list[ImageRef]]] = []
    for _group_title, _toc_href, items in groups:
        parts: list[str] = []
        group_imgs: list[ImageRef] = []
        for item in items:
            _, raw_text, imgs = _parse_item(item, image_map)
            if raw_text.strip():
                parts.append(raw_text)
                group_imgs.extend(imgs)
        group_data.append((_group_title, _toc_href, "\n\n".join(parts), group_imgs))

    # Apply min_chapter_words merging with images
    merged = _merge_group_data_with_images(group_data, cfg.min_chapter_words)

    chapters: list[Chapter] = []
    for idx, (chapter_title, toc_href, text, imgs) in enumerate(merged):
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
                images=imgs,
            )
        )

    # Re-index sequentially (some items may have been skipped)
    for i, ch in enumerate(chapters):
        ch.index = i

    # Collect bytes for referenced images
    referenced_bytes: dict[str, bytes] = {}
    for ch in chapters:
        for img in ch.images:
            if img.name in image_map and img.name not in referenced_bytes:
                referenced_bytes[img.name] = image_map[img.name]

    logger.info(
        "Loaded EPUB %s: %d spine items -> %d chapters (depth=%d, min_words=%d, images=%d)",
        display_name,
        len(spine_items),
        len(chapters),
        cfg.chapter_depth,
        cfg.min_chapter_words,
        len(referenced_bytes),
    )
    return (
        Document(
            source_path=str(path),
            title=title,
            file_hash=file_hash,
            original_filename=original_filename or path.name,
            chapters=chapters,
            metadata={"author": author},
        ),
        referenced_bytes,
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
            _, raw_text, _ = _parse_item(item)
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
