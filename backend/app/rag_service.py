import json
import math
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.pipeline import FeatureUnion

from app.config import settings


BACKEND_DIR = Path(__file__).resolve().parents[1]
KNOWLEDGE_PATH = BACKEND_DIR / "data" / "knowledge_base.json"


@dataclass(frozen=True)
class KnowledgeChunk:
    id: str
    title: str
    content: str

    @property
    def searchable_text(self) -> str:
        return f"{self.title}. {self.content}"


@dataclass(frozen=True)
class RagResult:
    query: str
    chunks: list[KnowledgeChunk]
    scores: list[float]

    @property
    def primary_source(self) -> str | None:
        return self.chunks[0].title if self.chunks else None

    @property
    def source_titles(self) -> list[str]:
        seen: set[str] = set()
        titles: list[str] = []
        for chunk in self.chunks:
            if chunk.title not in seen:
                seen.add(chunk.title)
                titles.append(chunk.title)
        return titles

    @property
    def best_score(self) -> float | None:
        if not self.scores:
            return None
        return round(float(max(self.scores)), 4)

    def context_text(self) -> str:
        return "\n".join(
            f"[{index}] {chunk.title}: {chunk.content}"
            for index, chunk in enumerate(self.chunks, start=1)
        )


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _load_chunks() -> list[KnowledgeChunk]:
    try:
        raw_items = json.loads(KNOWLEDGE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        raw_items = []

    chunks: list[KnowledgeChunk] = []
    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            continue

        title = str(item.get("title") or f"Knowledge {index + 1}").strip()
        content = str(item.get("content") or "").strip()
        if not content:
            continue

        chunks.append(
            KnowledgeChunk(
                id=str(item.get("id") or f"chunk_{index + 1}"),
                title=title,
                content=content,
            )
        )

    return chunks


@lru_cache(maxsize=1)
def _rag_index():
    chunks = _load_chunks()
    documents = [chunk.searchable_text for chunk in chunks]

    if not documents:
        return chunks, None, None

    vectorizer = FeatureUnion(
        [
            (
                "word",
                TfidfVectorizer(
                    preprocessor=_normalize,
                    ngram_range=(1, 3),
                    sublinear_tf=True,
                ),
            ),
            (
                "char",
                TfidfVectorizer(
                    preprocessor=_normalize,
                    analyzer="char_wb",
                    ngram_range=(3, 5),
                    sublinear_tf=True,
                ),
            ),
        ]
    )
    matrix = vectorizer.fit_transform(documents)
    return chunks, vectorizer, matrix


def _keyword_overlap(query: str, document: str) -> float:
    query_terms = {term for term in _normalize(query).split() if len(term) > 2}
    if not query_terms:
        return 0.0

    doc_terms = set(_normalize(document).split())
    return len(query_terms & doc_terms) / math.sqrt(len(query_terms))


def _mmr_order(
    similarity_scores: list[float],
    doc_similarity,
    candidate_indices: list[int],
    top_k: int,
) -> list[int]:
    selected: list[int] = []
    remaining = candidate_indices[:]
    relevance_weight = max(0.0, min(1.0, settings.rag_mmr_lambda))

    while remaining and len(selected) < top_k:
        best_index = remaining[0]
        best_score = float("-inf")

        for index in remaining:
            redundancy = 0.0
            if selected:
                redundancy = max(float(doc_similarity[index, chosen]) for chosen in selected)

            mmr_score = relevance_weight * similarity_scores[index] - (
                1 - relevance_weight
            ) * redundancy
            if mmr_score > best_score:
                best_score = mmr_score
                best_index = index

        selected.append(best_index)
        remaining.remove(best_index)

    return selected


def retrieve_knowledge(query: str) -> RagResult | None:
    chunks, vectorizer, matrix = _rag_index()
    if not chunks or vectorizer is None or matrix is None:
        return None

    query_vector = vectorizer.transform([query])
    vector_scores = cosine_similarity(query_vector, matrix)[0]

    combined_scores: list[float] = []
    for index, chunk in enumerate(chunks):
        overlap = _keyword_overlap(query, chunk.searchable_text)
        combined_scores.append((0.86 * float(vector_scores[index])) + (0.14 * overlap))

    candidate_indices = [
        index
        for index, score in enumerate(combined_scores)
        if score >= settings.rag_score_threshold
    ]
    if not candidate_indices:
        return None

    candidate_indices.sort(key=lambda index: combined_scores[index], reverse=True)
    doc_similarity = cosine_similarity(matrix)
    selected_indices = _mmr_order(
        similarity_scores=combined_scores,
        doc_similarity=doc_similarity,
        candidate_indices=candidate_indices,
        top_k=settings.rag_top_k,
    )

    return RagResult(
        query=query,
        chunks=[chunks[index] for index in selected_indices],
        scores=[combined_scores[index] for index in selected_indices],
    )
