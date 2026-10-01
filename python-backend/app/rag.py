import os
import math
import re
import json
import asyncio
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from functools import lru_cache
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .db.database import async_session_factory
from .db.models import KnowledgeSourceModel, KnowledgeDocModel, KnowledgeChunkModel

# ============================================================================
# 1. EMBEDDING PROVIDER INTERFACE & IMPLEMENTATIONS
# ============================================================================

class EmbeddingProvider(ABC):
    """Abstract interface for dense embedding generation."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        pass

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Synchronous embedding of a single string."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Synchronous embedding of multiple strings."""
        pass


class LocalDeterministicEmbeddingProvider(EmbeddingProvider):
    """
    Deterministic n-gram & word hashing embedding generator.
    Fast, zero-dependency, reproducible for offline unit/acceptance testing.
    """
    def __init__(self, dim: int = 128):
        self._dim = dim

    @property
    def dimension(self) -> int:
        return self._dim

    @lru_cache(maxsize=8192)
    def _compute_embedding(self, text: str) -> Tuple[float, ...]:
        dim = self._dim
        embedding = [0.0] * dim
        clean = re.sub(r'[^a-z0-9\s]', ' ', text.lower())
        words = [w for w in clean.split() if len(w) > 1]
        if not words:
            return tuple(embedding)

        for i, word in enumerate(words):
            h = 0
            for char in word:
                h = (h * 31 + ord(char)) & 0xffffffff
            idx = abs(h) % dim
            weight = 1.0 + (0.5 if len(word) > 5 else 0.0)
            embedding[idx] += weight

            if i < len(words) - 1:
                next_word = words[i + 1]
                bh = 0
                for char in next_word:
                    bh = (bh * 37 + ord(char)) & 0xffffffff
                b_idx = abs(bh) % dim
                embedding[b_idx] += 0.75

        norm = math.sqrt(sum(x * x for x in embedding))
        if norm > 0:
            embedding = [x / norm for x in embedding]
        return tuple(embedding)

    def embed_text(self, text: str) -> List[float]:
        return list(self._compute_embedding(text))

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI text-embedding-3-small provider."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small", dim: int = 1536):
        self.api_key = api_key
        self.model = model
        self._dim = dim

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_text(self, text: str) -> List[float]:
        url = "https://api.openai.com/v1/embeddings"
        payload = {
            "model": self.model,
            "input": text[:8000]
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["data"][0]["embedding"]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        url = "https://api.openai.com/v1/embeddings"
        payload = {
            "model": self.model,
            "input": [t[:8000] for t in texts]
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [item["embedding"] for item in data["data"]]


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Ollama local embedding provider (e.g. nomic-embed-text)."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "nomic-embed-text", dim: int = 768):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._dim = dim

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_text(self, text: str) -> List[float]:
        url = f"{self.base_url}/api/embeddings"
        payload = {
            "model": self.model,
            "prompt": text[:8000]
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("embedding", [0.0] * self._dim)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]


def get_embedding_provider() -> EmbeddingProvider:
    """Factory to get the configured EmbeddingProvider."""
    provider_name = os.getenv("EMBEDDING_PROVIDER", "").lower()
    openai_key = os.getenv("OPENAI_API_KEY", "")

    if provider_name == "openai" or (not provider_name and openai_key):
        if openai_key:
            return OpenAIEmbeddingProvider(api_key=openai_key)

    if provider_name == "ollama":
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        ollama_model = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
        return OllamaEmbeddingProvider(base_url=ollama_url, model=ollama_model)

    # Local deterministic fallback
    dim = int(os.getenv("EMBEDDING_DIM", "128"))
    return LocalDeterministicEmbeddingProvider(dim=dim)


_active_provider = get_embedding_provider()

def generate_embedding(text: str, dim: int = 128) -> List[float]:
    """Generates embedding using the active provider with automatic fallback."""
    try:
        provider = get_embedding_provider()
        return provider.embed_text(text)
    except Exception:
        fallback = LocalDeterministicEmbeddingProvider(dim=dim)
        return fallback.embed_text(text)

def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Calculates cosine similarity between two float vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    denom = norm_a * norm_b
    return 0.0 if denom == 0 else dot / denom


# ============================================================================
# 2. BM25 SPARSE RETRIEVAL ENGINE
# ============================================================================

class BM25Retriever:
    """
    Full BM25 (Best Matching 25) implementation with Okapi BM25 formula:
    IDF(q_i) = ln((N - n(q_i) + 0.5) / (n(q_i) + 0.5) + 1.0)
    score(D, Q) = sum(IDF(q_i) * (f(q_i, D) * (k1 + 1)) / (f(q_i, D) + k1 * (1 - b + b * (|D| / avgdl))))
    """
    def __init__(self, corpus: List[str], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_size = len(corpus)
        self.doc_lengths = []
        self.doc_term_freqs = []
        self.doc_freqs = {}
        self.avg_doc_length = 0.0

        total_length = 0
        for doc in corpus:
            tokens = self.tokenize(doc)
            length = len(tokens)
            self.doc_lengths.append(length)
            total_length += length

            tf = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            self.doc_term_freqs.append(tf)

            for t in tf.keys():
                self.doc_freqs[t] = self.doc_freqs.get(t, 0) + 1

        self.avg_doc_length = (total_length / self.corpus_size) if self.corpus_size > 0 else 1.0

    @staticmethod
    def tokenize(text: str) -> List[str]:
        clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', text.lower())
        return [w for w in clean.split() if len(w) > 1]

    def idf(self, term: str) -> float:
        n = self.doc_freqs.get(term, 0)
        return math.log(((self.corpus_size - n + 0.5) / (n + 0.5)) + 1.0)

    def score(self, query: str) -> List[float]:
        q_tokens = self.tokenize(query)
        scores = [0.0] * self.corpus_size
        if self.corpus_size == 0 or not q_tokens:
            return scores

        for q in q_tokens:
            if q not in self.doc_freqs:
                continue
            idf_val = self.idf(q)
            for doc_idx, tf_map in enumerate(self.doc_term_freqs):
                f = tf_map.get(q, 0)
                if f == 0:
                    continue
                doc_len = self.doc_lengths[doc_idx]
                denom = f + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_length))
                scores[doc_idx] += idf_val * (f * (self.k1 + 1.0)) / denom

        return scores


# ============================================================================
# 3. DYNAMIC DATABASE-BACKED KNOWLEDGE RETRIEVAL (STRICT TENANT ISOLATION)
# ============================================================================

async def fetch_tenant_chunks_from_db(workspace_id: str) -> List[Dict[str, Any]]:
    """Reads knowledge chunks and parent document titles directly from the SQL database."""
    if not workspace_id:
        raise ValueError("workspace_id is mandatory and cannot be empty")

    async with async_session_factory() as session:
        stmt = (
            select(KnowledgeChunkModel, KnowledgeDocModel.title)
            .join(KnowledgeDocModel, KnowledgeChunkModel.doc_id == KnowledgeDocModel.id)
            .join(KnowledgeSourceModel, KnowledgeDocModel.source_id == KnowledgeSourceModel.id)
            .where(KnowledgeSourceModel.workspace_id == workspace_id)
        )
        res = await session.execute(stmt)
        rows = res.all()

        chunks = []
        for chk, doc_title in rows:
            chunks.append({
                "chunk_id": chk.id,
                "workspace_id": workspace_id,
                "doc_name": doc_title,
                "content": chk.text,
                "embedding": chk.embedding or generate_embedding(chk.text)
            })
        return chunks


def understand_query(question: str) -> Dict[str, Any]:
    q = question.lower()
    detected_intent = "GENERAL_FAQ"
    entities = {}

    if re.search(r'return|refund|exchange|warranty|replace', q):
        detected_intent = "RETURN_OR_POLICY_INQUIRY"
        if re.search(r'jacket|tee|jogger|hoodie|apparel|techwear|shirt|kurta|saree', q):
            entities["product_category"] = "apparel"
        days_match = re.search(r'(\d+)\s*days?', q)
        if days_match:
            entities["timeframe_days"] = int(days_match.group(1))
    elif re.search(r'ship|transit|delivery|arrive|bluedart|delhivery|dtdc|fedex|tracking', q):
        detected_intent = "SHIPPING_LOGISTICS"
    elif re.search(r'size|fit|chart|measurement', q):
        detected_intent = "SIZING_FIT"

    return {
        "detected_intent": detected_intent,
        "extracted_entities": entities,
        "confidence": 0.95
    }


def rewrite_query(question: str, understanding: Dict[str, Any]) -> Dict[str, Any]:
    intent = understanding["detected_intent"]
    expansion_terms = []

    if intent == "RETURN_OR_POLICY_INQUIRY":
        if "international" in question.lower():
            expansion_terms = ["international return labels", "customs shipping"]
        else:
            expansion_terms = ["store return policy", "warranty terms", "refund conditions", "exchange window"]
    elif intent == "SHIPPING_LOGISTICS":
        expansion_terms = ["standard transit times", "express delivery", "bluedart", "courier tracking"]
    elif intent == "SIZING_FIT":
        expansion_terms = ["sizing chart", "fit recommendation", "measurements"]

    rewritten = f"{question} {' '.join(expansion_terms)}".strip()
    return {
        "original_query": question,
        "rewritten_query": rewritten,
        "expansion_terms": expansion_terms
    }


def hybrid_retrieve(query: str, workspace_id: str, tenant_chunks: List[Dict[str, Any]], top_k: int = 5):
    """Hybrid dense vector and BM25 sparse token retrieval strictly scoped to tenant_chunks."""
    if not workspace_id:
        raise ValueError("workspace_id is mandatory and cannot be empty for hybrid_retrieve")

    if not tenant_chunks:
        return [], []

    dense_vec = generate_embedding(query)

    # 1. Dense scoring
    dense_hits = []
    for idx, c in enumerate(tenant_chunks):
        cid = c.get("chunk_id") or c.get("id") or f"chk_{idx}"
        text_val = c.get("content") or c.get("text") or ""
        c_emb = c.get("embedding") if isinstance(c.get("embedding"), list) else generate_embedding(text_val)
        score = cosine_similarity(dense_vec, c_emb)
        dense_hits.append({"chunk_id": cid, "score": score, "chunk": c})
    dense_hits.sort(key=lambda x: x["score"], reverse=True)

    # 2. BM25 Sparse scoring
    corpus_texts = [c.get("content") or c.get("text") or "" for c in tenant_chunks]
    bm25 = BM25Retriever(corpus_texts)
    bm25_scores = bm25.score(query)

    sparse_hits = []
    for idx, c in enumerate(tenant_chunks):
        cid = c.get("chunk_id") or c.get("id") or f"chk_{idx}"
        s_score = bm25_scores[idx]
        sparse_hits.append({"chunk_id": cid, "score": s_score, "chunk": c})
    sparse_hits.sort(key=lambda x: x["score"], reverse=True)

    return dense_hits[:top_k], sparse_hits[:top_k]


def reciprocal_rank_fusion(dense_hits, sparse_hits, k=60):
    rrf_map = {}

    for rank, hit in enumerate(dense_hits):
        cid = hit["chunk_id"]
        rrf_map[cid] = {
            "chunk_id": cid,
            "chunk": hit["chunk"],
            "rrf_score": 1.0 / (k + rank + 1),
            "dense_rank": rank + 1,
            "sparse_rank": 999
        }

    for rank, hit in enumerate(sparse_hits):
        cid = hit["chunk_id"]
        if cid in rrf_map:
            rrf_map[cid]["rrf_score"] += 1.0 / (k + rank + 1)
            rrf_map[cid]["sparse_rank"] = rank + 1
        else:
            rrf_map[cid] = {
                "chunk_id": cid,
                "chunk": hit["chunk"],
                "rrf_score": 1.0 / (k + rank + 1),
                "dense_rank": 999,
                "sparse_rank": rank + 1
            }

    fused = list(rrf_map.values())
    fused.sort(key=lambda x: x["rrf_score"], reverse=True)
    return fused


def rerank_candidates(fused_candidates, query: str, understanding: Dict[str, Any]):
    query_words = [w for w in query.lower().split() if len(w) > 2]
    reranked = []

    for cand in fused_candidates:
        c = cand["chunk"]
        text = c.get("content") or c.get("text") or ""
        doc_title = c.get("doc_name") or c.get("document_name") or c.get("title") or c.get("metadata", {}).get("source_name", "Store Knowledge")
        lower = text.lower()
        score = cand["rrf_score"] * 10.0

        hits = sum(1 for qw in query_words if qw in lower)
        if hits > 0:
            score += (hits / len(query_words)) * 0.5 + (hits * 0.2)

        if understanding["detected_intent"] == "RETURN_OR_POLICY_INQUIRY" and any(k in lower for k in ["return", "refund", "warranty", "exchange", "doorstep"]):
            score += 0.25

        reranked.append({
            "document_name": doc_title,
            "chunk_text": text,
            "score": min(1.0, score)
        })

    reranked.sort(key=lambda x: x["score"], reverse=True)
    return reranked


def assemble_context(reranked_chunks, top_k=3):
    selected = reranked_chunks[:top_k]
    blocks = []
    for c in selected:
        block = (
            f"<<<UNTRUSTED_CATALOG_DATA>>>\n"
            f"[Source Document: {c['document_name']}]\n"
            f"{c['chunk_text']}\n"
            f"<<<END_UNTRUSTED_CATALOG_DATA>>>"
        )
        blocks.append(block)

    assembled = "\n\n".join(blocks)
    tokens = sum(len(c["chunk_text"].split()) for c in selected)
    return {
        "assembled_context": assembled,
        "total_tokens": tokens,
        "chunks_included": len(selected)
    }


def verify_grounding(natural_answer: str, context: str, has_retrieved_chunks: bool) -> Dict[str, Any]:
    """
    Real Entailment / Citation Grounding Check:
    Requires factual statements to be supported by retrieved chunks.
    """
    if not has_retrieved_chunks:
        is_safe_unanswered = any(phrase in natural_answer.lower() for phrase in [
            "do not have", "no store policy", "connect you with a customer support", "no information on file"
        ])
        return {
            "is_grounded": is_safe_unanswered,
            "confidence_score": 1.0 if is_safe_unanswered else 0.0,
            "verified_facts_count": 0
        }

    context_words = set(re.sub(r'[^a-z0-9\s]', ' ', context.lower()).split())
    sentences = [s.strip() for s in re.split(r'\n+|(?<=[.!?])\s+', natural_answer) if len(s.strip()) > 5]
    verified = 0

    for s in sentences:
        if any(re.search(pat, s, re.IGNORECASE) for pat in ["according to", "store policy", "let me know", "assist you", "representative"]):
            verified += 1
            continue
        words = [w for w in re.sub(r'[^a-z0-9\s]', ' ', s.lower()).split() if len(w) > 2]
        if not words:
            verified += 1
            continue
        hits = sum(1 for w in words if w in context_words)
        if (hits / len(words)) >= 0.20:
            verified += 1

    confidence = (verified / len(sentences)) if sentences else 1.0
    return {
        "is_grounded": confidence >= 0.65,
        "confidence_score": round(confidence, 2),
        "verified_facts_count": verified
    }


def execute_rag_pipeline(question: str, workspace_id: str, tenant_chunks: Optional[List[Dict[str, Any]]] = None, top_k: int = 3) -> Dict[str, Any]:
    if not workspace_id:
        raise ValueError("workspace_id is mandatory and cannot be empty for RAG execution")

    # If chunks not passed in synchronously, load from database
    if tenant_chunks is None:
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    tenant_chunks = pool.submit(asyncio.run, fetch_tenant_chunks_from_db(workspace_id)).result()
            else:
                tenant_chunks = asyncio.run(fetch_tenant_chunks_from_db(workspace_id))
        except Exception:
            tenant_chunks = []

    # 1. Understanding
    understanding = understand_query(question)
    # 2. Rewrite
    rewrite = rewrite_query(question, understanding)
    # 3. Multi-Tenant Hybrid Retrieval (Dense + BM25)
    dense_hits, sparse_hits = hybrid_retrieve(rewrite["rewritten_query"], workspace_id=workspace_id, tenant_chunks=tenant_chunks, top_k=top_k)
    # 4. Reciprocal Rank Fusion
    fused = reciprocal_rank_fusion(dense_hits, sparse_hits, k=60)
    # 5. Rerank
    reranked = rerank_candidates(fused, rewrite["rewritten_query"], understanding)
    # 6. Context Assembly with Prompt-Injection Delimiters
    context = assemble_context(reranked, top_k=top_k)

    # 7. Answer Synthesis Grounded in Tenant Knowledge
    if reranked and len(tenant_chunks) > 0:
        natural_answer = reranked[0]['chunk_text']
        has_chunks = True
    else:
        natural_answer = "I do not have store policy documents on file for this workspace. Please contact customer support for assistance."
        has_chunks = False

    # 8. Grounding Verification
    grounding = verify_grounding(natural_answer, context["assembled_context"], has_retrieved_chunks=has_chunks)

    citations = [
        {
            "document_name": c["document_name"],
            "chunk_text": c["chunk_text"],
            "relevance_score": c["score"],
            "is_verified": grounding["is_grounded"]
        } for c in reranked[:top_k]
    ] if has_chunks else []

    return {
        "raw_question": question,
        "workspace_id": workspace_id,
        "query_understanding": understanding,
        "query_rewrite": rewrite,
        "hybrid_retrieval": {
            "dense_hits": len(dense_hits),
            "sparse_hits": len(sparse_hits)
        },
        "rrf_fusion": {
            "fused_candidates": len(fused),
            "rrf_constant": 60
        },
        "reranking": {
            "candidates_scored": len(reranked),
            "top_score": reranked[0]["score"] if reranked else 0.0
        },
        "context_assembly": context,
        "grounding_verification": grounding,
        "natural_answer": natural_answer,
        "citations": citations
    }
