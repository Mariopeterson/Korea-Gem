from datetime import date

from core import clean_html, has_korean, keyword_popularity_boost, normalize_key, recency_score


def test_has_korean_true():
    assert has_korean("홍대 맛집") is True


def test_has_korean_false():
    assert has_korean("best bbq in hongdae") is False


def test_clean_html():
    assert clean_html("<b>맛집</b> &amp; 카페") == "맛집 & 카페"


def test_normalize_key():
    assert normalize_key("  Seoul", "Hot  Place ") == "seoul hot place"


def test_recency_score_recent():
    assert recency_score("20260101", today=date(2026, 1, 10)) == 2.0


def test_keyword_popularity_boost_cap():
    text = "인기 핫플 웨이팅 예약 필수 must-visit viral best top"
    assert keyword_popularity_boost(text) == 2.0
