"""
Configuration for VKS Expert AI Semantic PDF Parser.
"""

from pathlib import Path


VERSION = "0.8"

PARSER_NAME = "VKS Expert AI Semantic PDF Parser"


PROJECT_ROOT = Path(__file__).resolve().parents[2]


DEFAULT_SOURCE = (
    PROJECT_ROOT
    / "knowledge"
    / "parsed"
    / "SP_30.13330.2020.elements.json"
)

DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "knowledge"
    / "parsed"
    / "SP_30.13330.2020.semantic.json"
)


DEBUG_PAGE = 12


# =====================================================================
# IMAGE CLASSIFICATION
# =====================================================================

SYMBOL_MAX_AREA = 1200.0

FORMULA_FRAGMENT_MIN_AREA = 180.0
FORMULA_FRAGMENT_MAX_AREA = 5000.0

FORMULA_CANDIDATE_MIN_AREA = 500.0

DIAGRAM_MIN_AREA = 5000.0

SMALL_MATH_MAX_WIDTH = 120.0
SMALL_MATH_MAX_HEIGHT = 80.0


# =====================================================================
# FORMULA GROUPING
# =====================================================================

FORMULA_GROUP_MAX_X_GAP = 45.0
FORMULA_GROUP_MAX_Y_GAP = 18.0
FORMULA_GROUP_CENTER_Y_TOLERANCE = 24.0

FORMULA_GROUP_HEIGHT_RATIO = 3.5


# =====================================================================
# FORMULA NUMBER
# =====================================================================

FORMULA_NUMBER_Y_TOLERANCE = 45.0
FORMULA_NUMBER_MAX_X_DISTANCE = 220.0

FORMULA_NUMBER_MIN_LINK_SCORE = 50.0
