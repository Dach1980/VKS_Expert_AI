"""Project Expert AI — transparent RAG diagnostics for the Knowledge Base page.

This module intentionally does not generate an answer. It exposes the stages that
matter when debugging retrieval: classification, enhanced query, raw FAISS
results, evidence validation, and the final verified context.
"""
from __future__ import annotations

from app.rag.rag_pipeline import RAGPipeline


class RAGDiagnostics:
    """Run the existing RAG stages without calling the LLM."""

    def __init__(self, pipeline: RAGPipeline):
        self.pipeline = pipeline

    def run(self, question: str, top_k: int = 5) -> dict:
        question = str(question or "").strip()
        if not question:
            return {
                "question": "",
                "enhanced_query": "",
                "retrieved": [],
                "accepted": [],
                "rejected": [],
                "context": "",
                "evidence_confidence": 0.0,
                "evidence_sufficient": False,
                "diagnostics": {"error": "Вопрос не задан."},
            }

        intent = self.pipeline.classifier.classify(question)
        enhanced_query = self.pipeline._build_enhanced_query(question, intent)
        retrieved = self.pipeline.retriever.search(enhanced_query, top_k=top_k) or []
        evidence = self.pipeline.validator.validate(
            retrieved,
            intent=intent,
            query=question,
            top_k=top_k,
        )
        accepted = self.pipeline._prepare_validated_results(evidence.accepted)
        context = ""
        if accepted:
            context = str(self.pipeline.context_builder.build(accepted) or "").strip()

        return {
            "question": question,
            "intent": self._safe_intent(intent),
            "enhanced_query": enhanced_query,
            "retrieved": [self._public_result(item) for item in retrieved],
            "accepted": [self._public_result(item) for item in accepted],
            "rejected": [self._public_rejection(item) for item in evidence.rejected],
            "context": context,
            "evidence_confidence": float(evidence.confidence),
            "evidence_sufficient": bool(evidence.sufficient),
            "diagnostics": {
                "retrieved_count": len(retrieved),
                "accepted_count": len(evidence.accepted),
                "rejected_count": len(evidence.rejected),
                "context_length": len(context),
            },
        }

    @staticmethod
    def _safe_intent(intent) -> dict:
        if intent is None:
            return {}
        if hasattr(intent, "__dict__"):
            return dict(intent.__dict__)
        return {"value": str(intent)}

    @staticmethod
    def _public_result(item: dict) -> dict:
        content = item.get("content", "")
        if isinstance(content, dict):
            content = dict(content)
        return {
            "document": item.get("document"),
            "version": item.get("version"),
            "page": item.get("page", 0),
            "type": item.get("type", "text"),
            "source": item.get("source"),
            "score": float(item.get("score", 0.0) or 0.0),
            "content": content,
            "metadata": item.get("metadata", {}),
            "chunk_id": item.get("chunk_id"),
        }

    @staticmethod
    def _public_rejection(item: dict) -> dict:
        if not isinstance(item, dict):
            return {"value": str(item)}
        result = dict(item)
        if "item" in result and isinstance(result["item"], dict):
            result["item"] = RAGDiagnostics._public_result(result["item"])
        return result
