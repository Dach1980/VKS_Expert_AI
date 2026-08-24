"""
VKS Expert AI — Semantic Domain Models v0.8.

В этом модуле находятся основные модели данных semantic layer.

Важно:
    Модели не выполняют анализ PDF.
    Они описывают результат анализа и позволяют постепенно
    отказаться от передачи неструктурированных dict между модулями.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


# =====================================================================
# GEOMETRY
# =====================================================================

@dataclass
class Geometry:
    width: float = 0.0
    height: float = 0.0
    area: float = 0.0
    center: List[float] = field(
        default_factory=lambda: [0.0, 0.0]
    )
    horizontal_region: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PageGeometry:
    width: float = 0.0
    height: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =====================================================================
# IDENTITY
# =====================================================================

@dataclass
class ElementIdentity:
    parser_index: Optional[int] = None
    source_index: Optional[int] = None
    xref: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =====================================================================
# ELEMENT
# =====================================================================

@dataclass
class SemanticElement:
    parser_index: Optional[int] = None
    source_index: Optional[int] = None
    xref: Optional[int] = None

    type: Optional[str] = None
    bbox: Optional[List[float]] = None

    semantic_role: Optional[str] = None

    text_normalized: Optional[str] = None

    geometry: Optional[Geometry] = None

    classification_reason: Optional[str] = None
    classification_confidence: Optional[float] = None

    raw: Dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> Dict[str, Any]:
        result = dict(self.raw)

        result["identity"] = {
            "parser_index": self.parser_index,
            "source_index": self.source_index,
            "xref": self.xref,
        }

        if self.parser_index is not None:
            result["parser_index"] = self.parser_index

        if self.source_index is not None:
            result["source_index"] = self.source_index

        if self.xref is not None:
            result["xref"] = self.xref

        if self.type is not None:
            result["type"] = self.type

        if self.bbox is not None:
            result["bbox"] = self.bbox

        if self.semantic_role is not None:
            result["semantic_role"] = self.semantic_role

        if self.text_normalized is not None:
            result["text_normalized"] = self.text_normalized

        if self.geometry is not None:
            result["geometry"] = self.geometry.to_dict()

        if self.classification_reason is not None:
            result[
                "classification_reason"
            ] = self.classification_reason

        if self.classification_confidence is not None:
            result[
                "classification_confidence"
            ] = self.classification_confidence

        return result


# =====================================================================
# FORMULA CANDIDATE
# =====================================================================

@dataclass
class FormulaCandidate:
    formula_id: str
    parser_index: int
    source_index: Optional[int]
    xref: Optional[int]

    bbox: Optional[List[float]]

    role: str
    detection_reason: Optional[str]

    confidence: float

    area: float = 0.0
    width: float = 0.0
    height: float = 0.0

    horizontal_region: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =====================================================================
# FORMULA GROUP
# =====================================================================

@dataclass
class FormulaGroup:
    group_id: int

    members: int
    composite: bool

    parser_indices: List[int] = field(
        default_factory=list
    )

    source_indices: List[int] = field(
        default_factory=list
    )

    xrefs: List[int] = field(
        default_factory=list
    )

    bbox: Optional[List[float]] = None

    formula_ids: List[str] = field(
        default_factory=list
    )

    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =====================================================================
# FORMULA NUMBER
# =====================================================================

@dataclass
class FormulaNumber:
    number: int

    number_parser_index: Optional[int]
    number_source_index: Optional[int]
    number_xref: Optional[int]

    number_container_bbox: Optional[List[float]]
    number_estimated_bbox: Optional[List[float]]

    text: str

    prefix: str
    suffix: str

    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =====================================================================
# FORMULA RELATION
# =====================================================================

@dataclass
class FormulaRelation:
    group_id: int
    number: int

    number_parser_index: Optional[int]
    number_source_index: Optional[int]
    number_xref: Optional[int]

    score: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =====================================================================
# FORMULA RECORD
# =====================================================================

@dataclass
class FormulaRecord:
    group_id: int

    formula_ids: List[str]
    parser_indices: List[int]
    source_indices: List[int]
    xrefs: List[int]

    bbox: Optional[List[float]]

    members: int
    composite: bool

    confidence: float

    number: Optional[int] = None

    number_parser_index: Optional[int] = None
    number_source_index: Optional[int] = None
    number_xref: Optional[int] = None

    number_bbox: Optional[List[float]] = None
    number_estimated_bbox: Optional[List[float]] = None

    link_score: float = 0.0

    previous_text: Optional[str] = None
    previous_text_parser_index: Optional[int] = None

    next_text: Optional[str] = None
    next_text_parser_index: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =====================================================================
# PAGE
# =====================================================================

@dataclass
class SemanticPage:
    page_number: int

    page_geometry: PageGeometry

    elements_count: int

    elements: List[Dict[str, Any]] = field(
        default_factory=list
    )

    formula_candidates: List[Dict[str, Any]] = field(
        default_factory=list
    )

    formula_groups: List[Dict[str, Any]] = field(
        default_factory=list
    )

    formula_numbers: List[Dict[str, Any]] = field(
        default_factory=list
    )

    formulas: List[Dict[str, Any]] = field(
        default_factory=list
    )

    formula_relations: List[Dict[str, Any]] = field(
        default_factory=list
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "page_geometry": (
                self.page_geometry.to_dict()
            ),
            "elements_count": self.elements_count,
            "elements": self.elements,
            "formula_candidates": (
                self.formula_candidates
            ),
            "formula_groups": self.formula_groups,
            "formula_numbers": self.formula_numbers,
            "formulas": self.formulas,
            "formula_relations": (
                self.formula_relations
            ),
        }


# =====================================================================
# STATISTICS
# =====================================================================

@dataclass
class SemanticStatistics:
    pages: int = 0
    elements: int = 0
    images: int = 0
    symbols: int = 0
    formula_fragments: int = 0
    diagram_candidates: int = 0
    formula_candidates: int = 0
    formula_groups: int = 0
    composite_groups: int = 0
    formula_numbers: int = 0
    formula_relations: int = 0
    formulas_without_number: int = 0
    validation_errors: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =====================================================================
# DOCUMENT
# =====================================================================

@dataclass
class SemanticDocument:
    parser_name: str
    parser_version: str

    source: str

    statistics: Dict[str, Any]

    pages: List[Dict[str, Any]]

    validation_valid: bool

    validation_errors: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parser": {
                "name": self.parser_name,
                "version": self.parser_version,
            },
            "source": self.source,
            "statistics": self.statistics,
            "pages": self.pages,
            "validation": {
                "valid": self.validation_valid,
                "errors": self.validation_errors,
            },
        }
    