import re
from datetime import datetime
from html import unescape
from urllib.parse import quote

KOREAN_RE = re.compile(r"[\uac00-\ud7a3]")
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


def has_korean(text: str) -> bool:
    return bool(KOREAN_RE.search(text or ""))


def clean_html(text: str) -> str:
    return unescape(TAG_RE.sub("", text or "")).strip()


def normalize_key(*parts: str) -> str:
    raw = " ".join([p.strip().lower() for p in parts if p])
    return SPACE_RE.sub(" ", raw)


def parse_post_date(value: str):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y%m%d").date()
    except ValueError:
        return None


def recency_score(post_date: str, today=None) -> float:
    today = today or datetime.utcnow().date()
    parsed = parse_post_date(post_date)
    if not parsed:
        return 0.0

    age_days = max((today - parsed).days, 0)
    if age_days <= 14:
        return 2.0
    if age_days <= 30:
        return 1.5
    if age_days <= 90:
        return 1.0
    if age_days <= 180:
        return 0.5
    return 0.1


def keyword_popularity_boost(text: str) -> float:
    t = (text or "").lower()
    boost = 0.0
    keywords = [
        "인기",
        "핫플",
        "웨이팅",
        "줄서",
        "예약 필수",
        "must-visit",
        "viral",
        "best",
        "top",
    ]
    for kw in keywords:
        if kw in t:
            boost += 0.4
    return min(boost, 2.0)


def naver_search_map_link(place_name: str, city_ko: str = "") -> str:
    q = quote(f"{city_ko} {place_name}".strip())
    return f"https://map.naver.com/p/search/{q}"
