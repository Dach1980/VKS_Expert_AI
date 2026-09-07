import pytest

from app.checking.scope import normalize_page_scope, parse_page_ranges


def test_parse_page_ranges_deduplicates_and_sorts():
    assert parse_page_ranges("1-3, 3-5, 5, 7", 10) == [1, 2, 3, 4, 5, 7]


def test_whole_document_returns_all_pages():
    assert normalize_page_scope(6, True) == [1, 2, 3, 4, 5, 6]


@pytest.mark.parametrize("value", ["0", "1-0", "1-7", "abc", "2-3-x", ""])
def test_invalid_ranges_are_rejected(value):
    with pytest.raises(ValueError):
        parse_page_ranges(value, 6)
