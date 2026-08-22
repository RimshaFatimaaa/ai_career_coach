"""Selective RAG over curated career/resume/interview knowledge."""

from __future__ import annotations

import math
import re

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import KnowledgeDoc

settings = get_settings()


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


def ingest_knowledge(db: Session) -> int:
    if db.query(KnowledgeDoc).count():
        return 0
    root = settings.knowledge_dir
    if not root.exists():
        return 0
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
    q = db.query(KnowledgeDoc)
    if category:
        q = q.filter(KnowledgeDoc.category == category)
    docs = q.all()
    query_emb = (_embed_texts([query]) or [None])[0]
    tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
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
