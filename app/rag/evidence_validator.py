"""
VKS Expert AI

Evidence Validator v1.6

Prioritizes direct normative requirements over generic semantic matches.
"""

from dataclasses import dataclass
from typing import List
import re


@dataclass
class EvidenceResult:
    confidence: float
    accepted: List[dict]
    rejected: List[dict]
    sufficient: bool


class EvidenceValidator:
    """Validate retrieved evidence with an explicit normative-evidence priority."""

    def __init__(self, min_score: float = 0.55, min_confidence: float = 0.55, min_relevance: float = 0.10, min_query_relevance: float = 0.05, min_faiss_score: float = 0.20):
        self.min_score = min_score
        self.min_confidence = min_confidence
        self.min_relevance = min_relevance
        self.min_query_relevance = min_query_relevance
        self.min_faiss_score = min_faiss_score

    DOMAIN_KEYWORDS = {
        "internal_water_supply": ["водоснабж", "водопровод", "хвс", "гвс", "расход воды", "секундный расход", "расчетный расход", "максимальный расчетный расход", "давление", "напор", "трубопровод", "стояк", "водоразбор", "водоразборный", "система холодного водоснабжения", "система горячего водоснабжения"],
        "sewerage": ["канализа", "сток", "водоотведение", "гидравлический затвор", "канализационный стояк", "расчетный расход стоков"],
        "fire_water": ["пожар", "внутренний пожарный водопровод", "спринклер", "расход пожарный", "пожаротушение", "пожарный кран"],
    }

    TOPIC_KEYWORDS = {
        "hydraulic_calculation": ["расход", "напор", "давление", "гидравличес", "диаметр", "потери", "формула", "скорость", "водоразбор", "расчет", "расчетный"],
        "pipe_selection": ["диаметр", "труба", "материал", "скорость", "трубопровод"],
        "normative_requirement": ["требования", "должен", "следует", "нормы", "предусматривать", "допускается", "не допускается", "принимать", "предусматривается"],
    }

    STOP_WORDS = {"как", "какой", "какая", "какие", "какое", "что", "где", "когда", "для", "при", "по", "на", "в", "во", "из", "и", "или", "а", "о", "об", "с", "со", "к", "у", "от", "до", "за", "не", "же", "ли", "это"}

    DIRECT_NORMATIVE_PATTERNS = (
        r"следует\s+(?:принимать|предусматривать|определять|устанавливать)",
        r"долж(?:ен|на|но|ны)",
        r"не\s+допускается",
        r"допускается",
        r"принимают",
        r"принимается",
        r"не\s+менее",
        r"не\s+более",
        r"не\s+должен",
    )

    QUERY_ANCHORS = ("диаметр", "труб", "трубопровод", "условный проход", "водопровод", "водоснабжен", "ду", "dn")

    def validate(self, results: List[dict], intent=None, top_k: int = 5, query: str = "") -> EvidenceResult:
        accepted_candidates, rejected = [], []
        normative_query = self._is_normative_query(query, intent)

        for item in results:
            if not isinstance(item, dict):
                continue
            text, formula, continuation = self._extract_content(item)
            searchable_text = self._normalize(" ".join(part for part in (text, formula, continuation) if part))
            score = self._safe_float(item.get("score", 0.0))
            relevance = self._calculate_relevance(searchable_text, intent)
            query_relevance = self._calculate_query_relevance(searchable_text, query)
            direct_normative = self._direct_normative_evidence(searchable_text, query, normative_query)
            has_formula = bool(formula.strip())
            is_formula_context = item.get("type") == "formula_context"
            formula_bonus = 0.10 if is_formula_context and has_formula else (0.05 if has_formula else 0.0)
            completeness = self._calculate_completeness(text, formula, continuation, item)
            direct_bonus = 0.20 if direct_normative else 0.0
            final_score = min(score * 0.55 + relevance * 0.15 + query_relevance * 0.15 + completeness * 0.05 + formula_bonus + direct_bonus, 1.0)

            faiss_ok = score >= self.min_faiss_score
            query_gate = max(self.min_query_relevance, 0.10) if normative_query and not direct_normative else self.min_query_relevance
            if normative_query and not direct_normative:
                # For normative questions, subject/query relevance is a hard gate.
                # Generic engineering relevance must never compensate for a weak
                # match to the actual question concept.
                has_relevance = query_relevance >= query_gate
            else:
                has_relevance = relevance >= self.min_relevance or query_relevance >= self.min_query_relevance

            reasons = []
            if not faiss_ok:
                reasons.append("faiss_score_below_threshold")
            if normative_query and not direct_normative and query_relevance < query_gate:
                reasons.append("normative_query_relevance_below_threshold_for_non_direct_evidence")
            elif not normative_query and not has_relevance:
                reasons.append("no_direct_relevance")
            elif normative_query and direct_normative is False and not has_relevance:
                reasons.append("no_query_relevance")
            if final_score < self.min_score:
                reasons.append("evidence_score_below_threshold")

            accepted_flag = faiss_ok and has_relevance and final_score >= self.min_score
            # A direct normative clause is deliberately allowed to pass the
            # stricter query-relevance gate: it is the highest-value evidence.
            if normative_query and direct_normative:
                accepted_flag = faiss_ok and final_score >= self.min_score

            item["evidence_score"] = round(final_score, 3)
            item["relevance_score"] = round(relevance, 3)
            item["query_relevance_score"] = round(query_relevance, 3)
            item["faiss_score"] = round(score, 3)
            item["formula_bonus"] = round(formula_bonus, 3)
            item["direct_normative_bonus"] = round(direct_bonus, 3)
            item["direct_normative_evidence"] = direct_normative
            item["completeness_score"] = round(completeness, 3)
            item["direct_relevance"] = has_relevance
            item["has_formula"] = has_formula
            item["validation_reasons"] = ["accepted"] if accepted_flag else reasons
            item["score_breakdown"] = {"faiss": round(score * 0.55, 3), "engineering_relevance": round(relevance * 0.15, 3), "query_relevance": round(query_relevance * 0.15, 3), "completeness": round(completeness * 0.05, 3), "formula_bonus": round(formula_bonus, 3), "direct_normative_bonus": round(direct_bonus, 3)}
            (accepted_candidates if accepted_flag else rejected).append(item)

        accepted = sorted(accepted_candidates, key=lambda x: (bool(x.get("direct_normative_evidence")), x.get("evidence_score", 0.0)), reverse=True)[:top_k]
        confidence = self._calculate_confidence(accepted)
        sufficient = bool(accepted) and confidence >= self.min_confidence

        print()
        print("===== EVIDENCE VALIDATION v1.6 =====")
        print("Input:", len(results))
        print("Accepted:", len(accepted))
        print("Rejected:", len(rejected))
        print("Confidence:", round(confidence, 3))
        print("Sufficient:", sufficient)
        for i, item in enumerate(accepted, 1):
            print()
            print(f"ACCEPTED #{i}")
            print("Document:", item.get("document"))
            print("Page:", item.get("page"))
            print("Type:", item.get("type"))
            print("FAISS:", item.get("faiss_score"))
            print("Relevance:", item.get("relevance_score"))
            print("Query relevance:", item.get("query_relevance_score"))
            print("Direct normative:", item.get("direct_normative_evidence"))
            print("Completeness:", item.get("completeness_score"))
            print("Evidence:", item.get("evidence_score"))
            print("Formula:", item.get("has_formula"))
        if rejected:
            print()
            print("REJECTED DIAGNOSTICS:")
            for i, item in enumerate(rejected, 1):
                print(f"#{i}", "page=", item.get("page"), "score=", item.get("evidence_score"), "reasons=", item.get("validation_reasons"))
        print("====================================")

        return EvidenceResult(confidence=round(confidence, 3), accepted=accepted, rejected=rejected, sufficient=sufficient)

    def _extract_content(self, item: dict):
        content = item.get("content", {})
        text = formula = continuation = ""
        if isinstance(content, dict):
            text = str(content.get("text", "") or "")
            formula = str(content.get("formula", "") or "")
            continuation = str(content.get("after", "") or "")
        else:
            text = str(content or "")
        if not text:
            text = str(item.get("text", "") or "")
        return text, formula, continuation

    def _calculate_completeness(self, text: str, formula: str, continuation: str, item: dict) -> float:
        score = 0.0
        if text.strip():
            score += 0.40
        if formula.strip():
            score += 0.30
        if continuation.strip():
            score += 0.20
        if item.get("page") is not None:
            score += 0.10
        return min(score, 1.0)

    def _calculate_confidence(self, accepted: List[dict]) -> float:
        if not accepted:
            return 0.0
        scores = [float(item.get("evidence_score", 0.0)) for item in accepted]
        base = sum(scores) / len(scores)
        documents = {str(item.get("document", "")) for item in accepted if item.get("document")}
        pages = {(str(item.get("document", "")), item.get("page")) for item in accepted}
        diversity_bonus = (0.03 if len(documents) >= 2 else 0.0) + (0.02 if len(pages) >= 2 else 0.0)
        return min(base + diversity_bonus, 1.0)

    def _normalize(self, text: str) -> str:
        text = str(text).lower().replace("ё", "е")
        text = re.sub(r"[^а-яa-z0-9\s]", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _query_tokens(self, query: str) -> List[str]:
        tokens = self._normalize(query).split()
        return [token for token in tokens if token not in self.STOP_WORDS and len(token) >= 3]

    def _calculate_query_relevance(self, text: str, query: str) -> float:
        if not query:
            return 0.0
        normalized_text = self._normalize(text)
        normalized_query = self._normalize(query)
        important_phrases = ["максимальный расчетный расход воды", "расчетный расход воды", "расчетном участке сети", "максимальный расход воды", "расчетный участок сети", "гидравлический расчет", "внутренняя система водоснабжения", "внутренние системы водоснабжения", "диаметр труб", "диаметр трубы", "условный проход", "минимальный диаметр", "принимать диаметр"]
        phrase_hits = sum(1 for phrase in important_phrases if phrase in normalized_query and phrase in normalized_text)
        tokens = self._query_tokens(query)
        if not tokens:
            return 0.0
        hits = 0
        for token in tokens:
            if token in normalized_text:
                hits += 1
            elif len(token) >= 6 and token[:6] in normalized_text:
                hits += 1
        token_score = hits / len(tokens)
        phrase_score = min(phrase_hits * 0.35, 0.70)
        return min(token_score * 0.30 + phrase_score, 1.0)

    def _calculate_relevance(self, text: str, intent) -> float:
        if intent is None:
            return 0.5
        score = 0.0
        system = getattr(intent, "system", "")
        system_hits = sum(1 for word in self.DOMAIN_KEYWORDS.get(system, []) if self._normalize(word) in text)
        if system_hits:
            score += min(system_hits * 0.15, 0.55)
        topic = getattr(intent, "topic", "")
        topic_hits = sum(1 for word in self.TOPIC_KEYWORDS.get(topic, []) if self._normalize(word) in text)
        if topic_hits:
            score += min(topic_hits * 0.15, 0.45)
        return min(score, 1.0)

    def _is_normative_query(self, query: str, intent) -> bool:
        normalized = self._normalize(query)
        if any(marker in normalized for marker in ("согласно", "требован", "норм", "следует", "должен", "допускается", "принимать")):
            return True
        return getattr(intent, "topic", "") == "normative_requirement"

    def _direct_normative_evidence(self, text: str, query: str, normative_query: bool) -> bool:
        if not normative_query:
            return False
        normalized_query = self._normalize(query)
        query_uses_diameter = any(term in normalized_query for term in ("диаметр", "диаметру", "диаметры", "диаметр труб", "диаметр трубы"))

        # For concept-specific normative questions, generic engineering words
        # are not sufficient. A clause about pipes, for example, is not direct
        # evidence for a question about diameter unless the diameter concept is
        # itself present in the same local normative clause.
        if query_uses_diameter:
            anchors = ("диаметр", "условный проход", "dn", "ду")
        else:
            anchors = [anchor for anchor in self.QUERY_ANCHORS if anchor in normalized_query]
        if not anchors:
            return False

        for anchor in anchors:
            for anchor_match in re.finditer(re.escape(anchor), text):
                start = max(0, anchor_match.start() - 120)
                end = min(len(text), anchor_match.end() + 160)
                window = text[start:end]
                if any(re.search(pattern, window) for pattern in self.DIRECT_NORMATIVE_PATTERNS):
                    return True
        return False

    def _safe_float(self, value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
