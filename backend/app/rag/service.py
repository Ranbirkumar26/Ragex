from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from app.config import Settings
from app.contracts import DecisionEnvelope, ExplanationEvidence, ExplanationResult
from app.data.repository import PolicyDocument, PricingRepository

TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


@dataclass(frozen=True)
class RetrievedChunk:
    doc_id: str
    title: str
    text: str
    score: float
    policy_ref: str


class Retriever(Protocol):
    def search(self, query: str, limit: int) -> list[RetrievedChunk]:
        raise NotImplementedError


class HashEmbeddingProvider:
    def __init__(self, model: str, dimensions: int) -> None:
        self.model = model
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        vector = np.zeros(self.dimensions, dtype=np.float32)
        for token in _tokens(text):
            index = hash(token) % self.dimensions
            vector[index] += 1.0
        norm = float(np.linalg.norm(vector))
        if norm == 0:
            return vector.tolist()
        return (vector / norm).tolist()


class PolicyRetriever:
    def __init__(self, repository: PricingRepository, settings: Settings) -> None:
        self._settings = settings
        self._embedder = HashEmbeddingProvider(settings.embedding_model, settings.embedding_dim)
        self._documents = repository.list_policy_documents()
        self._chunks = _chunk_documents(self._documents)
        self._chroma = self._build_chroma_or_none()

    def search(self, query: str, limit: int) -> list[RetrievedChunk]:
        if self._chroma is not None:
            return self._search_chroma(query, limit)
        return self._search_memory(query, limit)

    def _build_chroma_or_none(self) -> object | None:
        if self._settings.vector_backend != "chroma" or not self._chunks:
            return None

        try:
            import chromadb
        except Exception:
            return None

        try:
            client = chromadb.PersistentClient(path=str(self._settings.chroma_path))
            collection = client.get_or_create_collection(
                name="ragex_policy_corpus",
                metadata={
                    "embedding_model": self._settings.embedding_model,
                    "embedding_dim": self._settings.embedding_dim,
                },
            )
            ids = [f"{chunk.doc_id}:{index}" for index, chunk in enumerate(self._chunks)]
            collection.upsert(
                ids=ids,
                documents=[chunk.text for chunk in self._chunks],
                embeddings=[self._embedder.embed(chunk.text) for chunk in self._chunks],
                metadatas=[
                    {"doc_id": chunk.doc_id, "title": chunk.title, "policy_ref": chunk.policy_ref}
                    for chunk in self._chunks
                ],
            )
            return collection
        except Exception:
            return None

    def _search_chroma(self, query: str, limit: int) -> list[RetrievedChunk]:
        result = self._chroma.query(
            query_embeddings=[self._embedder.embed(query)],
            n_results=min(limit, len(self._chunks)),
            include=["documents", "metadatas", "distances"],
        )
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        query_tokens = set(_tokens(query))
        chunks: list[RetrievedChunk] = []
        for document, metadata, distance in zip(documents, metadatas, distances, strict=True):
            overlap = _overlap_score(query_tokens, set(_tokens(str(document))))
            score = max(overlap, 1 / (1 + float(distance)))
            if overlap == 0 or score < self._settings.rag_min_score:
                continue
            chunks.append(
                RetrievedChunk(
                    doc_id=str(metadata["doc_id"]),
                    title=str(metadata["title"]),
                    text=str(document),
                    score=round(float(score), 4),
                    policy_ref=str(metadata["policy_ref"]),
                )
            )
        return chunks

    def _search_memory(self, query: str, limit: int) -> list[RetrievedChunk]:
        query_tokens = set(_tokens(query))
        query_embedding = self._embedder.embed(query)
        ranked: list[RetrievedChunk] = []
        for chunk in self._chunks:
            overlap = _overlap_score(query_tokens, set(_tokens(chunk.text)))
            cosine = _cosine(query_embedding, self._embedder.embed(chunk.text))
            score = 0.75 * overlap + 0.25 * cosine
            if overlap == 0 or score < self._settings.rag_min_score:
                continue
            ranked.append(
                RetrievedChunk(
                    doc_id=chunk.doc_id,
                    title=chunk.title,
                    text=chunk.text,
                    score=round(float(score), 4),
                    policy_ref=chunk.policy_ref,
                )
            )
        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[:limit]


class ExplanationService:
    def __init__(self, retriever: Retriever, settings: Settings) -> None:
        self._retriever = retriever
        self._settings = settings

    def explain(self, decision: DecisionEnvelope) -> ExplanationResult:
        query = self._query_for_decision(decision)
        chunks = self._retriever.search(query, self._settings.rag_top_k)
        if not chunks:
            return ExplanationResult(
                status="refused",
                summary="This information is not found in the policy corpus.",
                evidence=[],
            )

        flags = ", ".join(flag.code for flag in decision.guardrail.flags) or "no guardrail flags"
        regret_phrase = ""
        if decision.regret.status == "scored":
            regret_phrase = f" Estimated regret is Rs {decision.regret.score_inr:,.2f}."
        summary = (
            f"Decision {decision.decision_id} has {flags}. "
            f"Policy evidence supports status {decision.guardrail.status}.{regret_phrase}"
        )
        return ExplanationResult(
            status="grounded",
            summary=summary,
            evidence=[
                ExplanationEvidence(
                    doc_id=chunk.doc_id,
                    title=chunk.title,
                    snippet=_snippet(chunk.text),
                    score=chunk.score,
                    policy_ref=chunk.policy_ref,
                )
                for chunk in chunks
            ],
        )

    def answer_question(self, question: str) -> ExplanationResult:
        chunks = self._retriever.search(question, self._settings.rag_top_k)
        if not chunks:
            return ExplanationResult(
                status="refused",
                summary="This information is not found in the policy corpus.",
                evidence=[],
            )

        return ExplanationResult(
            status="grounded",
            summary=f"Policy corpus contains relevant guidance in {chunks[0].title}.",
            evidence=[
                ExplanationEvidence(
                    doc_id=chunk.doc_id,
                    title=chunk.title,
                    snippet=_snippet(chunk.text),
                    score=chunk.score,
                    policy_ref=chunk.policy_ref,
                )
                for chunk in chunks
            ],
        )

    @staticmethod
    def _query_for_decision(decision: DecisionEnvelope) -> str:
        flag_terms = " ".join(
            " ".join(
                [
                    flag.code,
                    flag.code.replace("_", " "),
                    flag.code.replace("zscore", "z score"),
                    flag.message,
                    flag.policy_ref,
                ]
            )
            for flag in decision.guardrail.flags
        )
        if not flag_terms:
            flag_terms = "pricing policy guardrail pass"
        return (
            f"{flag_terms} price {decision.proposed_price_inr} "
            f"inventory {decision.context.inventory} demand {decision.context.demand_index} "
            f"competitor {decision.context.competitor_price_inr}"
        )


@dataclass(frozen=True)
class _Chunk:
    doc_id: str
    title: str
    text: str
    policy_ref: str


def _chunk_documents(documents: list[PolicyDocument]) -> list[_Chunk]:
    chunks: list[_Chunk] = []
    for document in documents:
        paragraphs = [item.strip() for item in document.content.split("\n\n") if item.strip()]
        for index, paragraph in enumerate(paragraphs):
            if paragraph.startswith("# "):
                continue
            chunks.append(
                _Chunk(
                    doc_id=document.doc_id,
                    title=document.title,
                    text=paragraph,
                    policy_ref=f"{document.doc_id}.{index}",
                )
            )
    return chunks


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text) if len(token) > 2]


def _overlap_score(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0
    return len(left & right) / math.sqrt(len(left) * len(right))


def _cosine(left: list[float], right: list[float]) -> float:
    left_arr = np.array(left, dtype=np.float32)
    right_arr = np.array(right, dtype=np.float32)
    denom = float(np.linalg.norm(left_arr) * np.linalg.norm(right_arr))
    if denom == 0:
        return 0
    return float(np.dot(left_arr, right_arr) / denom)


def _snippet(text: str, limit: int = 220) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 1].rstrip()}..."
