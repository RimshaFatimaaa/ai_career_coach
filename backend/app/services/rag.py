"""Selective RAG over curated career/resume/interview knowledge."""

from __future__ import annotations

import hashlib
import math
import re

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import KnowledgeDoc

settings = get_settings()

# Marker row holding the fingerprint of the ingested markdown. Kept in the same
# table so deployments do not need a schema migration; excluded from retrieval.
META_CATEGORY = "__meta__"
FINGERPRINT_TITLE = "knowledge_fingerprint"
MAX_CANDIDATES = 400


def chunk_text(text: str, size: int = 900, overlap: int = 120) -> list[str]:
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        piece = " ".join(words[i : i + size])
        if piece.strip():
            chunks.append(piece)
        i += size - overlap
    return chunks or [text]


def _embed_texts(texts: list[str]) -> list[list[float] | None]:
    key = settings.embedding_key
    if not key:
        return [None] * len(texts)
    try:
        from openai import OpenAI

        client = OpenAI(api_key=key, base_url=settings.embedding_base_url, timeout=20.0)
        resp = client.embeddings.create(model=settings.embedding_model, input=texts)
        by_index = {item.index: item.embedding for item in resp.data}
        return [by_index.get(i) for i in range(len(texts))]
    except Exception:
        return [None] * len(texts)


def knowledge_fingerprint(root) -> str:
    parts = []
    for path in sorted(root.glob("*.md")):
        stat = path.stat()
        parts.append(f"{path.name}:{stat.st_size}:{int(stat.st_mtime)}")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def ingest_knowledge(db: Session) -> int:
    """Load `knowledge/*.md` into the doc table, re-ingesting when files change.

    The previous version skipped whenever any row existed, so edits to the
    markdown never reached the coach without manually clearing the table.
    """
    root = settings.knowledge_dir
    if not root.exists():
        return 0
    fingerprint = knowledge_fingerprint(root)
    marker = (
        db.query(KnowledgeDoc)
        .filter_by(category=META_CATEGORY, title=FINGERPRINT_TITLE)
        .first()
    )
    if marker and marker.content == fingerprint:
        return 0
    if marker or db.query(KnowledgeDoc).count():
        db.query(KnowledgeDoc).delete()
        db.commit()
    docs: list[KnowledgeDoc] = []
    chunks: list[str] = []
    for path in sorted(root.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        header, _, body = raw.partition("\n\n")
        meta = _parse_meta(header)
        for i, chunk in enumerate(chunk_text(body or raw)):
            docs.append(
                KnowledgeDoc(
                    title=meta.get("title", path.stem),
                    source=meta.get("source", path.name),
                    category=meta.get("category", "general"),
                    topic=meta.get("topic", path.stem),
                    target_role=meta.get("target_role", "any"),
                    experience_level=meta.get("experience_level", "any"),
                    content=chunk,
                    chunk_index=i,
                )
            )
            chunks.append(chunk)
    embeddings = _embed_texts(chunks) if chunks else []
    for doc, emb in zip(docs, embeddings):
        doc.embedding = emb
        db.add(doc)
    db.add(
        KnowledgeDoc(
            title=FINGERPRINT_TITLE,
            source="internal",
            category=META_CATEGORY,
            topic=FINGERPRINT_TITLE,
            content=fingerprint,
        )
    )
    db.commit()
    return len(docs)


def _parse_meta(header: str) -> dict[str, str]:
    meta = {}
    for line in header.splitlines():
        if ":" in line and not line.startswith("#"):
            k, v = line.split(":", 1)
            meta[k.strip().lower().replace(" ", "_")] = v.strip()
        elif line.startswith("# "):
            meta["title"] = line[2:].strip()
    return meta


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def retrieve(db: Session, query: str, k: int = 4, category: str | None = None) -> list[dict]:
    base = db.query(KnowledgeDoc).filter(KnowledgeDoc.category != META_CATEGORY)
    if category:
        base = base.filter(KnowledgeDoc.category == category)
    tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
    # Push the first pass into SQL so a chat message does not pull the whole
    # corpus into Python on every turn.
    terms = sorted((t for t in tokens if len(t) >= 4), key=len, reverse=True)[:6]
    docs = []
    if terms:
        docs = (
            base.filter(or_(*[KnowledgeDoc.content.ilike(f"%{t}%") for t in terms]))
            .limit(MAX_CANDIDATES)
            .all()
        )
    if not docs:
        docs = base.limit(MAX_CANDIDATES).all()
    query_emb = (_embed_texts([query]) or [None])[0]
    scored = []
    for doc in docs:
        hay = set(re.findall(r"[a-z0-9]+", (doc.title + " " + doc.content).lower()))
        lexical = len(tokens & hay)
        semantic = 0.0
        if query_emb and isinstance(doc.embedding, list):
            semantic = _cosine(query_emb, doc.embedding)
        score = lexical + semantic * 8
        if score > 0:
            scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "title": d.title,
            "source": d.source,
            "category": d.category,
            "content": d.content[:800],
        }
        for _, d in scored[:k]
    ]


def format_context(hits: list[dict]) -> str:
    if not hits:
        return ""
    parts = []
    for h in hits:
        parts.append(f"[{h['title']} — {h['source']}]\n{h['content']}")
    return "\n\n".join(parts)
