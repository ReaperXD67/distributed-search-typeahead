import pytest
from pydantic import ValidationError

from app.schemas import SearchRequest, normalize_query


def test_normalize_query() -> None:
    assert normalize_query("  IPHONE   Charger ") == "iphone charger"


def test_search_request_rejects_blank_query() -> None:
    with pytest.raises(ValidationError):
        SearchRequest(query="   ")


def test_search_request_normalizes_query() -> None:
    assert SearchRequest(query="  Java   Tutorial ").query == "java tutorial"
