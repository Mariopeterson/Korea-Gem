from app import build_mock_response, discover_places, to_bool


def test_to_bool_truthy_and_falsey():
    assert to_bool("1") is True
    assert to_bool("true") is True
    assert to_bool("0") is False
    assert to_bool("no") is False


def test_build_mock_response_shape():
    result = build_mock_response("best cafes", city="seoul", categories=["cafes"], limit=3)
    assert result["mode"] == "mock"
    assert result["count"] == 3
    assert len(result["items"]) == 3
    assert result["items"][0]["place_name_en"]


def test_discover_places_with_mock_mode():
    result = discover_places("bars", city="busan", categories=["bars"], limit=2, use_mock=True)
    assert result["mode"] == "mock"
    assert result["city"] == "busan"
    assert result["count"] == 2
