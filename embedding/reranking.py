"""
reranker_pipeline.py
Two-stage retrieval + cross-encoder reranking module for e-commerce.

Env vars expected:
  QDRANT_URL (e.g. http://localhost:6333)
  QDRANT_API_KEY (optional)
  CROSS_ENCODER_MODEL (default 'cross-encoder/ms-marco-MiniLM-L-6-v2')
  ENABLE_RERANKING (true/false)
  SIMILARITY_THRESHOLD (float, default 0.25)
"""

import os
import math
from typing import List, Dict, Any, Tuple, Optional
from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from sentence_transformers import CrossEncoder


from FlagEmbedding import BGEM3FlagModel
model = BGEM3FlagModel('AITeamVN/Vietnamese_Embedding_v2', use_fp16=True)

# --- Config from env ---
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6334")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)
CROSS_ENCODER_MODEL = os.getenv("CROSS_ENCODER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
ENABLE_RERANKING = os.getenv("ENABLE_RERANKING", "true").lower() in ("1", "true", "yes")
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.25"))

# --- Setup clients ---
qclient = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

# load cross-encoder once (lazy)
_cross_encoder: Optional[CrossEncoder] = None
def get_cross_encoder() -> CrossEncoder:
    global _cross_encoder
    if _cross_encoder is None:
        _cross_encoder = CrossEncoder(CROSS_ENCODER_MODEL, device="cpu")  # change device as needed
    return _cross_encoder

# Simple in-memory cache for reranker scores: {(query, doc_id): score}
_rerank_cache: Dict[Tuple[str, str], float] = {}

# --- Utility: get dense query vector ---
def embed_query(
    query_text: str,
    embedding_model=None
) -> List[float]:
    """
    Produce dense vector for query_text. Replace with your embedding call.
    If you use BGEM3FlagModel, pass the model instance via embedding_model and
    adapt this function to extract 'dense_vecs' from model.encode output.
    """
    if embedding_model is None:
        # Fallback: raise helpful error
        raise ValueError("Please provide an embedding_model (e.g. BGEM3FlagModel instance).")
    emb_out = embedding_model.encode(query_text, return_dense=True, return_sparse=False)
    # adapt access depending on actual model output structure
    if isinstance(emb_out, dict) and "dense_vecs" in emb_out:
        dense = emb_out["dense_vecs"][0]
    elif isinstance(emb_out, (list, tuple)):
        dense = emb_out[0]
    else:
        # Best-effort fallback
        dense = emb_out
    return dense

# --- Stage 1: initial retrieval from Qdrant ---
def qdrant_dense_search(collection_name: str, query_vector: List[float], top_k: int):
    """
    Compatible with Qdrant >= 1.9.x (multi-vector collection).
    Always query by 'dense_vector' field.
    """
    results = qclient.query_points(
        collection_name=collection_name,
        query=qmodels.Filter(should=[]),  # optional, no filter
        query_vector=qmodels.NamedVector(
            name="dense_vector",           # ✅ TÊN VECTOR field trong collection
            vector=query_vector
        ),
        limit=top_k,
        with_payload=True
    )
    return results.points




# --- Reranker scoring ---
def score_candidates_with_cross_encoder(
    query: str,
    candidates: List[Dict[str, Any]],
    doc_text_field: str = "text",
    batch_size: int = 32
) -> List[Tuple[Dict[str, Any], float]]:
    """
    candidates: list of dict-like objects that include unique 'id' or 'payload' and the text to score.
    doc_text_field: where to pick text from each candidate (payload['text'] or candidate['payload'][doc_text_field])
    Returns: list of (candidate, score)
    """
    cross = get_cross_encoder()

    # Prepare pairs (query, doc_text) and collect doc ids
    pairs = []
    ids = []
    # We'll produce list of doc_texts for model
    texts = []
    for cand in candidates:
        # doc id
        pid = getattr(cand, "id", None) or (cand.payload.get("product_id") if hasattr(cand, "payload") else cand.get("id"))
        ids.append(str(pid))
        # try payload text
        doc_text = None
        if hasattr(cand, "payload") and cand.payload:
            # safe access
            doc_payload = cand.payload
            if isinstance(doc_payload, dict):
                doc_text = doc_payload.get(doc_text_field) or doc_payload.get("text") or doc_payload.get("description") or " ".join(
                    str(doc_payload.get(k, "")) for k in ("name", "brand") if k in doc_payload
                )
        if doc_text is None:
            # fallback: cand could be dict
            if isinstance(cand, dict):
                doc_text = cand.get(doc_text_field) or cand.get("text") or cand.get("description") or ""
        if not doc_text:
            doc_text = ""  # ensure not None

        texts.append(doc_text)
    # Use caching: build batch of pairs to score
    results = []
    # We'll score in batches using CrossEncoder.predict with list of tuples
    pair_tuples = [(query, t) for t in texts]

    # check cache per (query, doc_text) tuple - but doc_text maybe large; we cache by (query, doc_id)
    to_score_indices = []
    to_score_inputs = []
    for i, pid in enumerate(ids):
        key = (query, pid)
        if key in _rerank_cache:
            continue
        to_score_indices.append(i)
        to_score_inputs.append(pair_tuples[i])

    # batch scoring
    if to_score_inputs:
        preds = cross.predict(to_score_inputs, batch_size=batch_size)
        # store preds into cache mapping
        for idx, p in enumerate(preds):
            doc_idx = to_score_indices[idx]
            pid = ids[doc_idx]
            _rerank_cache[(query, pid)] = float(p)

    # assemble final list
    for i, pid in enumerate(ids):
        score = _rerank_cache.get((query, pid))
        # If still None (shouldn't), compute quickly
        if score is None:
            score = float(cross.predict([pair_tuples[i]])[0])
            _rerank_cache[(query, pid)] = score
        results.append((candidates[i], score))

    return results

# --- Main pipeline function ---
def rerank_search(
    query_text: str,
    collection_name: str,
    embedding_model,
    top_n: int = 10,
    similarity_threshold: float = SIMILARITY_THRESHOLD,
    fetch_multiplier: int = 2,
    enable_reranking: bool = ENABLE_RERANKING,
) -> List[Dict[str, Any]]:
    """
    End-to-end: embed query -> search dense -> optionally rerank -> return top_n results.

    Returns list of dicts: { 'id', 'score', 'payload' } sorted by final score descending.
    """
    # 1) embed query
    dense_q = embed_query(query_text, embedding_model=embedding_model)

    # 2) initial retrieval: get top 2N
    initial_k = max(top_n * fetch_multiplier, top_n)
    raw_results = qdrant_dense_search(collection_name, dense_q, initial_k)

    # 3) optionally filter by similarity threshold (if Qdrant returned scores)
    if similarity_threshold is not None:
        filtered = [r for r in raw_results if (getattr(r, "score", None) is None or r.score >= similarity_threshold)]
    else:
        filtered = raw_results

    if not filtered:
        return []

    # Convert to list of candidate dict-like objects
    candidates = filtered  # ScoredPoint objects are handled by scoring function

    # 4) Reranking
    if enable_reranking:
        scored = score_candidates_with_cross_encoder(query_text, candidates, doc_text_field="text", batch_size=32)
        # scored is list of (candidate, score)
        # Sort by cross-encoder score descending
        scored_sorted = sorted(scored, key=lambda x: x[1], reverse=True)
        # Build return structure, include both initial vector score and reranker score
        out = []
        for cand, rerank_score in scored_sorted[:top_n]:
            out.append({
                "id": getattr(cand, "id", None) or cand.payload.get("product_id") if hasattr(cand, "payload") else cand.get("id"),
                "payload": cand.payload if hasattr(cand, "payload") else cand,
                "vector_score": getattr(cand, "score", None),
                "rerank_score": rerank_score
            })
        return out
    else:
        # just return top_n by vector score
        sorted_by_vector = sorted(filtered, key=lambda r: getattr(r, "score", 0), reverse=True)
        out = []
        for r in sorted_by_vector[:top_n]:
            out.append({
                "id": getattr(r, "id", None),
                "payload": r.payload,
                "vector_score": getattr(r, "score", None),
                "rerank_score": None
            })
        return out

# --- Example usage ---
if __name__ == "__main__":
    # Example placeholder embedding model. Replace with your actual BGEM3FlagModel instance.
    class DummyEmbeddingModel:
        def encode(self, text, return_dense=True, return_sparse=False):
            # naive dummy: return vector of zeros (replace with real model)
            return {"dense_vecs": [[0.0]*768]}

    embedding_model = DummyEmbeddingModel()

    # Query example
    query = "áo khoác da nam cao cấp"
    results = rerank_search(
        query_text=query,
        collection_name="products",
        embedding_model=embedding_model,
        top_n=5,
        similarity_threshold=0.2,
        fetch_multiplier=2,
        enable_reranking=True
    )

    for i, r in enumerate(results, 1):
        print(f"{i}. id={r['id']} vec_score={r['vector_score']} rerank_score={r['rerank_score']} payload_name={r['payload'].get('name') if isinstance(r['payload'], dict) else 'N/A'}")
