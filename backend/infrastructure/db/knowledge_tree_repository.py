"""PostgreSQL implementations for Knowledge Tree stores."""

import json
import logging
import threading
from datetime import datetime, timezone
from uuid import UUID

import psycopg
from psycopg.pq import TransactionStatus

from core.model.knowledge_tree import (
    Flashcard,
    KnowledgeChapter,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeTree,
)
from core.model.question import Question, QuestionType
from infrastructure.db.postgres import PostgresPool

logger = logging.getLogger(__name__)


def _ensure_naive(dt: datetime) -> datetime:
    """Strip timezone info from a datetime returned from PostgreSQL (TIMESTAMPTZ)."""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


class _BaseKnowledgeRepo:
    """Shared connection + lock helpers for all Knowledge Tree repos."""

    def __init__(self, pool: PostgresPool) -> None:
        self._pool = pool
        self._lock = threading.Lock()

    def _conn(self) -> psycopg.Connection:
        conn = self._pool.connection()
        if conn.info.transaction_status == TransactionStatus.INERROR:
            conn.rollback()
        return conn


class PostgresKnowledgeTreeStore(_BaseKnowledgeRepo):
    """CRUD for knowledge_trees table."""

    def list_trees_for_user(self, user_id: UUID) -> list[KnowledgeTree]:
        conn = self._conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, title, description, created_at"
                " FROM knowledge_trees WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,)
            )
            rows = cur.fetchall()
        return [
            KnowledgeTree(
                id=row["id"],
                user_id=row["user_id"],
                title=row["title"],
                description=row["description"],
                created_at=_ensure_naive(row["created_at"]),
            )
            for row in rows
        ]

    def create_tree(self, title: str, description: str | None, user_id: UUID) -> KnowledgeTree:
        with self._lock:
            conn = self._conn()
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO knowledge_trees (user_id, title, description)"
                        " VALUES (%s, %s, %s)"
                        " RETURNING id, user_id, title, description, created_at",
                        (user_id, title, description),
                    )
                    row = cur.fetchone()
        return KnowledgeTree(
            id=row["id"],
            user_id=row["user_id"],
            title=row["title"],
            description=row["description"],
            created_at=_ensure_naive(row["created_at"]),
        )

    def get_tree(self, id: UUID) -> KnowledgeTree | None:
        conn = self._conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, title, description, created_at FROM knowledge_trees WHERE id = %s",
                (id,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return KnowledgeTree(
            id=row["id"],
            user_id=row["user_id"],
            title=row["title"],
            description=row["description"],
            created_at=_ensure_naive(row["created_at"]),
        )

    def update_tree(self, id: UUID, title: str, description: str | None) -> KnowledgeTree:
        with self._lock:
            conn = self._conn()
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE knowledge_trees"
                        " SET title = %s, description = %s"
                        " WHERE id = %s"
                        " RETURNING id, user_id, title, description, created_at",
                        (title, description, id),
                    )
                    row = cur.fetchone()
        if row is None:
            raise ValueError(f"Knowledge tree not found: {id}")
        logger.debug("Updated knowledge tree id=%s", id)
        return KnowledgeTree(
            id=row["id"],
            user_id=row["user_id"],
            title=row["title"],
            description=row["description"],
            created_at=_ensure_naive(row["created_at"]),
        )

    def delete_tree(self, id: UUID) -> None:
        with self._lock:
            conn = self._conn()
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM knowledge_trees WHERE id = %s", (id,))
        logger.debug("Deleted knowledge tree id=%s", id)


class PostgresKnowledgeChapterStore(_BaseKnowledgeRepo):
    """CRUD for knowledge_chapters table."""

    def list_chapters(self, tree_id: UUID) -> list[KnowledgeChapter]:
        conn = self._conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, tree_id, number, title, created_at"
                " FROM knowledge_chapters WHERE tree_id = %s ORDER BY number",
                (tree_id,),
            )
            rows = cur.fetchall()
        return [
            KnowledgeChapter(
                id=row["id"],
                tree_id=row["tree_id"],
                number=row["number"],
                title=row["title"],
                created_at=_ensure_naive(row["created_at"]),
            )
            for row in rows
        ]

    def create_chapter(self, tree_id: UUID, title: str) -> KnowledgeChapter:
        with self._lock:
            conn = self._conn()
            with conn.transaction():
                with conn.cursor() as cur:
                    # Auto-assign next number
                    cur.execute(
                        "SELECT COALESCE(MAX(number), 0) + 1 AS next_number"
                        " FROM knowledge_chapters WHERE tree_id = %s",
                        (tree_id,),
                    )
                    next_number = cur.fetchone()["next_number"]
                    cur.execute(
                        "INSERT INTO knowledge_chapters (tree_id, number, title)"
                        " VALUES (%s, %s, %s)"
                        " RETURNING id, tree_id, number, title, created_at",
                        (tree_id, next_number, title),
                    )
                    row = cur.fetchone()
        return KnowledgeChapter(
            id=row["id"],
            tree_id=row["tree_id"],
            number=row["number"],
            title=row["title"],
            created_at=_ensure_naive(row["created_at"]),
        )

    def update_chapter(self, tree_id: UUID, number: int, title: str) -> KnowledgeChapter:
        with self._lock:
            conn = self._conn()
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE knowledge_chapters"
                        " SET title = %s"
                        " WHERE tree_id = %s AND number = %s"
                        " RETURNING id, tree_id, number, title, created_at",
                        (title, tree_id, number),
                    )
                    row = cur.fetchone()
        if row is None:
            raise ValueError(f"Knowledge chapter not found: tree={tree_id} number={number}")
        logger.debug("Updated knowledge chapter tree=%s number=%d", tree_id, number)
        return KnowledgeChapter(
            id=row["id"],
            tree_id=row["tree_id"],
            number=row["number"],
            title=row["title"],
            created_at=_ensure_naive(row["created_at"]),
        )

    def delete_chapter(self, tree_id: UUID, number: int) -> None:
        with self._lock:
            conn = self._conn()
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM knowledge_chapters WHERE tree_id = %s AND number = %s",
                        (tree_id, number),
                    )
        logger.debug("Deleted knowledge chapter tree=%s number=%d", tree_id, number)


class PostgresKnowledgeDocumentStore(_BaseKnowledgeRepo):
    """CRUD for knowledge_documents table."""

    def list_documents(self, tree_id: UUID, chapter_id: UUID | None) -> list[KnowledgeDocument]:
        conn = self._conn()
        with conn.cursor() as cur:
            if chapter_id is not None:
                cur.execute(
                    "SELECT d.id, d.tree_id, d.chapter_id, d.title, d.content, d.is_main,"
                    " d.created_at, d.updated_at, d.source_file_path, d.source_file_name,"
                    " d.page_start, d.page_end, c.number AS chapter_number"
                    " FROM knowledge_documents d"
                    " LEFT JOIN knowledge_chapters c ON c.id = d.chapter_id"
                    " WHERE d.tree_id = %s AND d.chapter_id = %s"
                    " ORDER BY d.created_at",
                    (tree_id, chapter_id),
                )
            else:
                cur.execute(
                    "SELECT d.id, d.tree_id, d.chapter_id, d.title, d.content, d.is_main,"
                    " d.created_at, d.updated_at, d.source_file_path, d.source_file_name,"
                    " d.page_start, d.page_end, c.number AS chapter_number"
                    " FROM knowledge_documents d"
                    " LEFT JOIN knowledge_chapters c ON c.id = d.chapter_id"
                    " WHERE d.tree_id = %s"
                    " ORDER BY c.number NULLS LAST, d.created_at",
                    (tree_id,),
                )
            rows = cur.fetchall()
        return [_row_to_doc(row) for row in rows]

    def create_document(
        self,
        tree_id: UUID,
        chapter_id: UUID | None,
        title: str,
        content: str,
        is_main: bool,
        source_file_path: str | None = None,
        source_file_name: str | None = None,
        page_start: int | None = None,
        page_end: int | None = None,
    ) -> KnowledgeDocument:
        with self._lock:
            conn = self._conn()
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO knowledge_documents"
                        " (tree_id, chapter_id, title, content, is_main,"
                        " source_file_path, source_file_name, page_start, page_end)"
                        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                        " RETURNING id, tree_id, chapter_id, title, content,"
                        " is_main, created_at, updated_at,"
                        " source_file_path, source_file_name, page_start, page_end",
                        (
                            tree_id,
                            chapter_id,
                            title,
                            content,
                            is_main,
                            source_file_path,
                            source_file_name,
                            page_start,
                            page_end,
                        ),
                    )
                    row = cur.fetchone()
        logger.debug("Created knowledge document tree=%s title=%s", tree_id, title)
        return _row_to_doc(row)

    def get_document(self, id: UUID) -> KnowledgeDocument | None:
        conn = self._conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT d.id, d.tree_id, d.chapter_id, d.title, d.content, d.is_main,"
                " d.created_at, d.updated_at, d.source_file_path, d.source_file_name,"
                " d.page_start, d.page_end, c.number AS chapter_number"
                " FROM knowledge_documents d"
                " LEFT JOIN knowledge_chapters c ON c.id = d.chapter_id"
                " WHERE d.id = %s",
                (id,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return _row_to_doc(row)

    def update_document(self, id: UUID, title: str, content: str) -> KnowledgeDocument:
        with self._lock:
            conn = self._conn()
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE knowledge_documents"
                        " SET title = %s, content = %s, updated_at = NOW()"
                        " WHERE id = %s"
                        " RETURNING id, tree_id, chapter_id, title, content,"
                        " is_main, created_at, updated_at,"
                        " source_file_path, source_file_name, page_start, page_end",
                        (title, content, id),
                    )
                    row = cur.fetchone()
        if row is None:
            raise ValueError(f"Knowledge document not found: {id}")
        logger.debug("Updated knowledge document id=%s", id)
        return _row_to_doc(row)

    def update_document_source_file(self, id: UUID, path: str | None, name: str | None) -> None:
        with self._lock:
            conn = self._conn()
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE knowledge_documents"
                        " SET source_file_path = %s, source_file_name = %s"
                        " WHERE id = %s",
                        (path, name, id),
                    )

    def delete_document(self, id: UUID) -> None:
        with self._lock:
            conn = self._conn()
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM knowledge_documents WHERE id = %s", (id,))
        logger.debug("Deleted knowledge document id=%s", id)


class PostgresKnowledgeContentStore(_BaseKnowledgeRepo):
    """CRUD for knowledge_content table."""

    def save_chunks(self, chunks: list[KnowledgeChunk]) -> None:
        if not chunks:
            return
        with self._lock:
            conn = self._conn()
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.executemany(
                        "INSERT INTO knowledge_content"
                        " (id, tree_id, chapter_id, doc_id, chunk_index, text, token_count)"
                        " VALUES (%s, %s, %s, %s, %s, %s, %s)"
                        " ON CONFLICT (doc_id, chunk_index) DO NOTHING",
                        [
                            (
                                chunk.id,
                                chunk.tree_id,
                                chunk.chapter_id,
                                chunk.doc_id,
                                chunk.chunk_index,
                                chunk.text,
                                chunk.token_count,
                            )
                            for chunk in chunks
                        ],
                    )
        logger.debug("Saved %d knowledge content chunks", len(chunks))

    def get_chunks(self, tree_id: UUID, chapter_number: int) -> list[KnowledgeChunk]:
        """Fetch chunks for a tree chapter identified by 1-based chapter number."""
        conn = self._conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT kc.id, kc.tree_id, kc.chapter_id, kc.doc_id,"
                "       kc.chunk_index, kc.text, kc.token_count"
                " FROM knowledge_content kc"
                " JOIN knowledge_chapters ch ON ch.id = kc.chapter_id"
                " WHERE kc.tree_id = %s AND ch.number = %s"
                " ORDER BY kc.doc_id, kc.chunk_index",
                (tree_id, chapter_number),
            )
            rows = cur.fetchall()
        return [
            KnowledgeChunk(
                id=row["id"],
                tree_id=row["tree_id"],
                chapter_id=row["chapter_id"],
                doc_id=row["doc_id"],
                chunk_index=row["chunk_index"],
                text=row["text"],
                token_count=row["token_count"],
            )
            for row in rows
        ]


class PostgresKnowledgeQuestionStore(_BaseKnowledgeRepo):
    """CRUD for knowledge_tree_questions table."""

    def save_questions(self, questions: list[Question]) -> None:
        if not questions:
            return
        with self._lock:
            conn = self._conn()
            with conn.transaction():
                with conn.cursor() as cur:
                    for q in questions:
                        cur.execute(
                            "INSERT INTO knowledge_tree_questions"
                            " (id, tree_id, chapter_id, question_type, question_data, created_at)"
                            " VALUES (%s, %s, %s, %s, %s::jsonb, %s)"
                            " ON CONFLICT (id) DO NOTHING",
                            (
                                q.id,
                                q.tree_id,
                                q.chapter_id,
                                q.question_type,
                                json.dumps(q.question_data),
                                q.created_at,
                            ),
                        )
        logger.debug(
            "Saved %d questions for tree=%s", len(questions), str(questions[0].tree_id)[:12]
        )

    def get_questions(
        self,
        tree_id: UUID,
        chapter_id: UUID,
        question_type: QuestionType | None = None,
    ) -> list[Question]:
        conn = self._conn()
        with conn.cursor() as cur:
            if question_type is not None:
                cur.execute(
                    "SELECT id, tree_id, chapter_id, question_type, question_data, created_at"
                    " FROM knowledge_tree_questions"
                    " WHERE tree_id = %s AND chapter_id = %s AND question_type = %s"
                    " ORDER BY created_at ASC, id ASC",
                    (tree_id, chapter_id, question_type),
                )
            else:
                cur.execute(
                    "SELECT id, tree_id, chapter_id, question_type, question_data, created_at"
                    " FROM knowledge_tree_questions"
                    " WHERE tree_id = %s AND chapter_id = %s"
                    " ORDER BY created_at ASC, id ASC",
                    (tree_id, chapter_id),
                )
            rows = cur.fetchall()
        return [
            Question(
                id=row["id"],
                tree_id=row["tree_id"],
                chapter_id=row["chapter_id"],
                question_type=row["question_type"],
                question_data=row["question_data"],
                created_at=_ensure_naive(row["created_at"]),
            )
            for row in rows
        ]

    def delete_question(self, question_id: UUID) -> None:
        with self._lock:
            conn = self._conn()
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM knowledge_tree_questions WHERE id = %s",
                        (question_id,),
                    )
        logger.debug("Deleted question id=%s", str(question_id))


class PostgresFlashcardStore(_BaseKnowledgeRepo):
    """CRUD for flashcards table."""

    def save_flashcard(self, flashcard: Flashcard) -> None:
        with self._lock:
            conn = self._conn()
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO flashcards"
                        " (id, tree_id, chapter_id, doc_id, front, back, source_text, created_at)"
                        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
                        " ON CONFLICT (id) DO NOTHING",
                        (
                            flashcard.id,
                            flashcard.tree_id,
                            flashcard.chapter_id,
                            flashcard.doc_id,
                            flashcard.front,
                            flashcard.back,
                            flashcard.source_text,
                            flashcard.created_at,
                        ),
                    )
        logger.debug("Saved flashcard id=%s", str(flashcard.id)[:12])

    def list_flashcards(self, tree_id: UUID, chapter_id: UUID) -> list[Flashcard]:
        conn = self._conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, tree_id, chapter_id, doc_id, front, back, source_text, created_at"
                " FROM flashcards"
                " WHERE tree_id = %s AND chapter_id = %s"
                " ORDER BY created_at ASC, id ASC",
                (tree_id, chapter_id),
            )
            rows = cur.fetchall()
        return [
            Flashcard(
                id=row["id"],
                tree_id=row["tree_id"],
                chapter_id=row["chapter_id"],
                doc_id=row["doc_id"],
                front=row["front"],
                back=row["back"],
                source_text=row["source_text"],
                created_at=_ensure_naive(row["created_at"]),
            )
            for row in rows
        ]

    def delete_flashcard(self, id: UUID) -> None:
        with self._lock:
            conn = self._conn()
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM flashcards WHERE id = %s", (id,))
        logger.debug("Deleted flashcard id=%s", str(id))


def _row_to_doc(row: dict) -> KnowledgeDocument:
    return KnowledgeDocument(
        id=row["id"],
        tree_id=row["tree_id"],
        chapter_id=row["chapter_id"],
        title=row["title"],
        content=row["content"],
        is_main=row["is_main"],
        created_at=_ensure_naive(row["created_at"]),
        updated_at=_ensure_naive(row["updated_at"]),
        source_file_path=row.get("source_file_path"),
        source_file_name=row.get("source_file_name"),
        chapter_number=row.get("chapter_number"),
        page_start=row.get("page_start"),
        page_end=row.get("page_end"),
    )
