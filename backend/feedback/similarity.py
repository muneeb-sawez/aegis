"""AEGIS Incident Similarity Engine (backend/feedback/similarity.py) — M8.

Embeds incident descriptions using sentence-transformers (all-MiniLM-L6-v2, CPU)
and returns top-k most similar past incidents via cosine similarity in numpy.

Design rules:
  - Model is loaded lazily and cached at module level (avoids reload cost).
  - Falls back to keyword overlap if sentence-transformers is unavailable.
  - Cosine similarity computed in pure numpy (no sklearn dependency).
  - All incidents passed in come from GraphRepository.get_all_incidents_with_descriptions().
  - Never logs raw incident descriptions (PII risk); log IDs only.
"""

from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# ── Model cache ───────────────────────────────────────────────────────────────
_MODEL = None
_MODEL_NAME = "all-MiniLM-L6-v2"


def _get_model():
    """Lazily load the sentence-transformer model (CPU only, Phase 1)."""
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    try:
        from sentence_transformers import SentenceTransformer
        logger.info("SIMILARITY_MODEL_LOAD model=%r", _MODEL_NAME)
        _MODEL = SentenceTransformer(_MODEL_NAME, device="cpu")
        logger.info("SIMILARITY_MODEL_READY model=%r", _MODEL_NAME)
    except ImportError:
        logger.warning(
            "SIMILARITY_MODEL_UNAVAILABLE — sentence-transformers not installed; "
            "falling back to keyword overlap similarity."
        )
        _MODEL = None
    return _MODEL


# ── Cosine similarity (pure numpy) ───────────────────────────────────────────

def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two 1-D vectors. Returns 0.0 if either is zero."""
    norm_a = float(np.linalg.norm(a))
    norm_b = float(np.linalg.norm(b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _cosine_matrix(query: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Batch cosine similarity between query (D,) and matrix (N, D). Returns (N,)."""
    norms = np.linalg.norm(matrix, axis=1)              # (N,)
    norms = np.where(norms == 0, 1e-10, norms)          # avoid divide-by-zero
    query_norm = float(np.linalg.norm(query)) or 1e-10
    return (matrix @ query) / (norms * query_norm)


# ── Keyword fallback ─────────────────────────────────────────────────────────

def _keyword_similarity(text_a: str, text_b: str) -> float:
    """Simple Jaccard overlap as fallback when model is unavailable."""
    tokens_a = set(text_a.lower().split())
    tokens_b = set(text_b.lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


# ── Public API ────────────────────────────────────────────────────────────────

def find_similar_incidents(
    query_description: str,
    all_incidents: list[dict[str, Any]],
    top_k: int = 3,
    exclude_id: str = "",
) -> list[dict[str, Any]]:
    """Return the top_k most similar past incidents to the query description.

    Args:
        query_description: Free-text description of the current incident.
        all_incidents: List of incident dicts from GraphRepository
                       (must have 'id', 'description', 'service_id').
        top_k: Number of similar incidents to return (default 3).
        exclude_id: Incident ID to exclude (e.g. the current incident itself).

    Returns:
        List of up to top_k dicts: each incident dict augmented with
        {"similarity_score": float (0..1)}, sorted descending by similarity.
    """
    # Filter out the current incident
    candidates = [inc for inc in all_incidents if inc.get("id") != exclude_id]

    if not candidates:
        return []

    model = _get_model()

    if model is not None:
        # ── Embedding path ────────────────────────────────────────────────────
        try:
            descriptions = [inc.get("description", "") for inc in candidates]
            # Encode query and corpus together for efficiency
            all_texts = [query_description] + descriptions
            embeddings = model.encode(all_texts, convert_to_numpy=True, show_progress_bar=False)
            query_vec = embeddings[0]                    # (D,)
            corpus_matrix = embeddings[1:]               # (N, D)
            scores = _cosine_matrix(query_vec, corpus_matrix)   # (N,)

            # Build ranked results
            ranked_indices = np.argsort(scores)[::-1][:top_k]
            results = []
            for idx in ranked_indices:
                entry = dict(candidates[int(idx)])
                entry["similarity_score"] = round(float(scores[idx]), 4)
                results.append(entry)
            logger.debug(
                "SIMILARITY_DONE query_len=%d candidates=%d top_k=%d model=transformer",
                len(query_description),
                len(candidates),
                top_k,
            )
            return results
        except Exception as exc:
            logger.warning("SIMILARITY_EMBED_ERROR %s — falling back to keyword.", exc)

    # ── Keyword fallback path ─────────────────────────────────────────────────
    scored = []
    for inc in candidates:
        score = _keyword_similarity(query_description, inc.get("description", ""))
        entry = dict(inc)
        entry["similarity_score"] = round(score, 4)
        scored.append(entry)

    scored.sort(key=lambda x: x["similarity_score"], reverse=True)
    logger.debug(
        "SIMILARITY_DONE query_len=%d candidates=%d top_k=%d model=keyword_fallback",
        len(query_description),
        len(candidates),
        top_k,
    )
    return scored[:top_k]
