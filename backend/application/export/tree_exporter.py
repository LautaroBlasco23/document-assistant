"""Export a knowledge tree as an in-memory zip archive."""
from __future__ import annotations

import re
import zipfile
from io import BytesIO
from uuid import UUID

from core.model.knowledge_tree import Flashcard, KnowledgeDocument
from core.model.question import Question, QuestionType


def slugify(name: str, max_len: int = 80) -> str:
    s = name.lower().strip()
    s = re.sub(r'[\s/\\:*?"<>|]+', '_', s)
    s = re.sub(r'_+', '_', s)
    s = s.strip('_')
    return s[:max_len] or 'untitled'


def _dedup(name: str, seen: set[str]) -> str:
    candidate = name
    i = 2
    while candidate in seen:
        dot = name.rfind('.')
        if dot > 0:
            candidate = f"{name[:dot]}_{i}{name[dot:]}"
        else:
            candidate = f"{name}_{i}"
        i += 1
    seen.add(candidate)
    return candidate


def format_document(doc: KnowledgeDocument) -> str:
    lines = [f"# {doc.title}", ""]
    if doc.original_content is not None:
        lines += [
            "## Current Version (AI-improved)", "",
            doc.content, "",
            "## Original Version", "",
            doc.original_content,
        ]
    else:
        lines.append(doc.content)
    return "\n".join(lines)


def format_flashcards(cards: list[Flashcard]) -> str:
    if not cards:
        return "(no flashcards)"
    return "\n---\n".join(f"Q: {c.front}\nA: {c.back}" for c in cards)


def _fmt_true_false(q: Question) -> str:
    d = q.question_data
    answer = "True" if d.get("answer") else "False"
    lines = [f"Q: {d.get('statement', '')}", f"A: {answer}"]
    if d.get("explanation"):
        lines.append(f"Explanation: {d['explanation']}")
    return "\n".join(lines)


def _fmt_multiple_choice(q: Question) -> str:
    d = q.question_data
    lines = [f"Q: {d.get('question', '')}"]
    for opt in d.get("options", []):
        marker = ">" if opt.get("is_correct") else " "
        lines.append(f"  {marker} {opt.get('label', '')}: {opt.get('text', '')}")
    if d.get("explanation"):
        lines.append(f"Explanation: {d['explanation']}")
    return "\n".join(lines)


def _fmt_matching(q: Question) -> str:
    d = q.question_data
    lines = [f"Q: {d.get('question', '')}"]
    for pair in d.get("pairs", []):
        lines.append(f"  {pair.get('left', '')} → {pair.get('right', '')}")
    return "\n".join(lines)


def _fmt_checkbox(q: Question) -> str:
    d = q.question_data
    lines = [f"Q: {d.get('question', '')}"]
    for opt in d.get("options", []):
        marker = "[x]" if opt.get("is_correct") else "[ ]"
        lines.append(f"  {marker} {opt.get('text', '')}")
    if d.get("explanation"):
        lines.append(f"Explanation: {d['explanation']}")
    return "\n".join(lines)


_FORMATTERS: dict[str, object] = {
    "true_false": _fmt_true_false,
    "multiple_choice": _fmt_multiple_choice,
    "matching": _fmt_matching,
    "checkbox": _fmt_checkbox,
}


def format_questions(questions: list[Question], qtype: QuestionType) -> str:
    typed = [q for q in questions if q.question_type == qtype]
    if not typed:
        return f"(no {qtype.replace('_', ' ')} questions)"
    fmt = _FORMATTERS[qtype]
    return "\n\n---\n\n".join(fmt(q) for q in typed)  # type: ignore[operator]


def _readme(tree, chapters, all_docs) -> str:
    return "\n".join([
        f"Title: {tree.title}",
        f"Description: {tree.description or '(none)'}",
        f"Created: {tree.created_at.isoformat()}",
        f"Chapters: {len(chapters)}",
        f"Documents: {len(all_docs)}",
    ])


def export_tree(tree_id: UUID, services) -> bytes:
    tree = services.kt_tree_store.get_tree(tree_id)
    if tree is None:
        raise ValueError(f"Tree {tree_id} not found")

    chapters = services.kt_chapter_store.list_chapters(tree_id)
    all_docs = services.kt_doc_store.list_documents(tree_id, None)

    root = f"{slugify(tree.title)}/"
    buf = BytesIO()

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{root}README.txt", _readme(tree, chapters, all_docs))

        tree_level_docs = [d for d in all_docs if d.chapter_id is None]
        if tree_level_docs:
            seen: set[str] = set()
            for doc in tree_level_docs:
                fname = _dedup(f"{slugify(doc.title)}.txt", seen)
                zf.writestr(f"{root}documents/{fname}", format_document(doc))

        for ch in chapters:
            ch_folder = f"{root}{ch.number:02d} - {slugify(ch.title)}/"
            ch_docs = [d for d in all_docs if d.chapter_id == ch.id]

            if ch_docs:
                seen = set()
                for doc in ch_docs:
                    fname = _dedup(f"{slugify(doc.title)}.txt", seen)
                    zf.writestr(f"{ch_folder}documents/{fname}", format_document(doc))

            cards = services.kt_flashcard_store.list_flashcards(tree_id, ch.id)
            if cards:
                zf.writestr(f"{ch_folder}flashcards.txt", format_flashcards(cards))

            questions = services.kt_question_store.get_questions(tree_id, ch.id)
            for qtype in ("true_false", "multiple_choice", "matching", "checkbox"):
                typed = [q for q in questions if q.question_type == qtype]
                if typed:
                    zf.writestr(
                        f"{ch_folder}questions/{qtype}.txt",
                        format_questions(typed, qtype),  # type: ignore[arg-type]
                    )

    return buf.getvalue()
