import json
import os
import urllib.parse
import urllib.request
from collections import Counter
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from core import (
    clean_html,
    has_korean,
    keyword_popularity_boost,
    naver_search_map_link,
    normalize_key,
    recency_score,
)

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
NAVER_BLOG_SEARCH_URL = "https://openapi.naver.com/v1/search/blog.json"
NAVER_LOCAL_SEARCH_URL = "https://openapi.naver.com/v1/search/local.json"

CITY_MAP = {
    "seoul": "서울",
    "busan": "부산",
}

CATEGORY_MAP = {
    "restaurants": "맛집",
    "cafes": "카페",
    "bars": "바",
    "activities": "놀거리",
    "gyms": "헬스장",
}

MOCK_SPOTS = {
    "seoul": [
        {"place_ko": "몽탄", "place_en": "Mongtan", "neighborhood_ko": "용산구", "neighborhood_en": "Yongsan-gu"},
        {"place_ko": "밀토스트", "place_en": "Mil Toast", "neighborhood_ko": "종로구", "neighborhood_en": "Jongno-gu"},
        {"place_ko": "사운즈 한남", "place_en": "Sounds Hannam", "neighborhood_ko": "용산구 한남동", "neighborhood_en": "Hannam-dong, Yongsan-gu"},
        {"place_ko": "클럽 FF", "place_en": "Club FF", "neighborhood_ko": "마포구 홍대", "neighborhood_en": "Hongdae, Mapo-gu"},
        {"place_ko": "피크닉 서울", "place_en": "Piknic Seoul", "neighborhood_ko": "중구", "neighborhood_en": "Jung-gu"},
    ],
    "busan": [
        {"place_ko": "톤쇼우", "place_en": "Tonshou", "neighborhood_ko": "해운대구", "neighborhood_en": "Haeundae-gu"},
        {"place_ko": "제이엠커피", "place_en": "JM Coffee", "neighborhood_ko": "수영구", "neighborhood_en": "Suyeong-gu"},
        {"place_ko": "해리단길", "place_en": "Haeridan-gil", "neighborhood_ko": "해운대구", "neighborhood_en": "Haeundae-gu"},
        {"place_ko": "삼진어묵 본점", "place_en": "Samjin Eomuk HQ", "neighborhood_ko": "영도구", "neighborhood_en": "Yeongdo-gu"},
        {"place_ko": "송정 서핑비치", "place_en": "Songjeong Surf Beach", "neighborhood_ko": "해운대구", "neighborhood_en": "Haeundae-gu"},
    ],
}


class Translator:
    def __init__(self):
        self.cache = {}

    def translate(self, text: str, source: str = "auto", target: str = "ko") -> str:
        if not text:
            return ""

        key = (text, source, target)
        if key in self.cache:
            return self.cache[key]

        params = urllib.parse.urlencode(
            {
                "client": "gtx",
                "sl": source,
                "tl": target,
                "dt": "t",
                "q": text,
            }
        )
        url = f"https://translate.googleapis.com/translate_a/single?{params}"

        with urllib.request.urlopen(url, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))

        translated = "".join(chunk[0] for chunk in payload[0] if chunk and chunk[0]).strip()
        result = translated or text
        self.cache[key] = result
        return result


translator = Translator()


def to_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def build_mock_response(query_en: str, city: str, categories: list[str], limit: int, reason: str = "") -> dict:
    city_key = city if city in MOCK_SPOTS else "seoul"
    city_ko = CITY_MAP.get(city_key, city_key)
    category_labels = [CATEGORY_MAP.get(c, c) for c in categories if c]
    seeds = MOCK_SPOTS[city_key]

    items = []
    bounded_limit = max(1, min(limit, 50))
    for i in range(bounded_limit):
        seed = seeds[i % len(seeds)]
        score = round(6.8 - (i * 0.28), 2)
        if score < 3.1:
            score = 3.1
        items.append(
            {
                "title_ko": f"{city_ko} {seed['place_ko']} 추천",
                "title_en": f"{seed['place_en']} in {city_key.title()}",
                "description_en": (
                    f"Offline mock result for '{query_en}'. Best-match place for "
                    f"{', '.join(categories) if categories else 'local discovery'} in {city_key.title()}."
                ),
                "place_name_ko": seed["place_ko"],
                "place_name_en": seed["place_en"],
                "neighborhood_ko": seed["neighborhood_ko"],
                "neighborhood_en": seed["neighborhood_en"],
                "blog_link": "https://search.naver.com/search.naver?where=blog&query="
                + urllib.parse.quote(f"{city_ko} {seed['place_ko']}") ,
                "map_link": naver_search_map_link(seed["place_ko"], city_ko=city_ko),
                "post_date": "20260214",
                "mention_count": max(1, 8 - i),
                "popularity_score": score,
                "source_query_ko": f"{city_ko} {query_en} {' '.join(category_labels)}".strip(),
            }
        )

    return {
        "input_query_en": query_en,
        "city": city_key,
        "city_ko": city_ko,
        "categories": categories,
        "queries_ko": [f"{city_ko} {query_en}"],
        "count": len(items),
        "items": items,
        "ranking_notes": "Offline mock mode: deterministic sample ranking for UI testing.",
        "mode": "mock",
        "mock_reason": reason or "Mock mode was requested or auto-fallback was enabled.",
    }


def naver_headers() -> dict:
    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise RuntimeError(
            "Missing NAVER_CLIENT_ID / NAVER_CLIENT_SECRET. "
            "Create a Naver Developers app and set environment variables."
        )

    return {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }


def call_naver_api(url: str, params: dict) -> dict:
    req = urllib.request.Request(
        f"{url}?{urllib.parse.urlencode(params)}",
        headers=naver_headers(),
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def translate_to_korean(query: str) -> str:
    if has_korean(query):
        return query
    return translator.translate(query, source="auto", target="ko")


def translate_to_english(text: str) -> str:
    if not text:
        return ""
    if not has_korean(text):
        return text
    return translator.translate(text, source="auto", target="en")


def get_local_place(place_query_ko: str):
    try:
        data = call_naver_api(
            NAVER_LOCAL_SEARCH_URL,
            {
                "query": place_query_ko,
                "display": 1,
                "sort": "comment",
            },
        )
        if data.get("items"):
            item = data["items"][0]
            return {
                "name_ko": clean_html(item.get("title", "")),
                "category_ko": item.get("category", ""),
                "address_ko": item.get("roadAddress", "") or item.get("address", ""),
                "map_link": naver_search_map_link(clean_html(item.get("title", ""))),
            }
    except Exception:
        return None
    return None


def extract_place_name(title_ko: str, city_ko: str = "") -> str:
    cleaned = title_ko.replace(city_ko, "").strip()
    tokens = [t for t in cleaned.replace("|", " ").split() if t]
    if not tokens:
        return ""

    noise = {"맛집", "카페", "바", "술집", "추천", "후기", "서울", "부산", "헬스장", "놀거리"}
    for token in tokens:
        if token not in noise and len(token) >= 2:
            return token
    return tokens[0]


def build_korean_queries(query_en: str, city: str, categories: list[str]) -> list[str]:
    city_ko = CITY_MAP.get(city, city)
    translated_query = translate_to_korean(query_en)
    category_terms = [CATEGORY_MAP.get(c, c) for c in categories if c]

    base = f"{city_ko} {translated_query}".strip()
    queries = [base]

    for category in category_terms:
        queries.append(f"{base} {category}".strip())

    seen = set()
    unique_queries = []
    for q in queries:
        nk = normalize_key(q)
        if nk not in seen:
            seen.add(nk)
            unique_queries.append(q)
    return unique_queries


def discover_places(query_en: str, city: str = "seoul", categories=None, limit: int = 20, use_mock: bool = False):
    categories = categories or ["restaurants", "cafes", "bars", "activities", "gyms"]

    if use_mock:
        return build_mock_response(query_en, city=city, categories=categories, limit=limit)

    city_ko = CITY_MAP.get(city, city)
    queries_ko = build_korean_queries(query_en, city, categories)

    raw_posts = []
    for q in queries_ko:
        data = call_naver_api(
            NAVER_BLOG_SEARCH_URL,
            {
                "query": q,
                "display": 30,
                "sort": "sim",
            },
        )
        for item in data.get("items", []):
            title_ko = clean_html(item.get("title", ""))
            desc_ko = clean_html(item.get("description", ""))
            place_name_ko = extract_place_name(title_ko, city_ko=city_ko)
            raw_posts.append(
                {
                    "query_ko": q,
                    "title_ko": title_ko,
                    "description_ko": desc_ko,
                    "link": item.get("link", ""),
                    "blogger_name": clean_html(item.get("bloggername", "")),
                    "post_date": item.get("postdate", ""),
                    "place_name_ko": place_name_ko,
                }
            )

    dedup_posts = {}
    for post in raw_posts:
        key = normalize_key(post.get("link", ""))
        if key and key not in dedup_posts:
            dedup_posts[key] = post

    posts = list(dedup_posts.values())

    place_counter = Counter(
        normalize_key(p.get("place_name_ko", ""), city_ko) for p in posts if p.get("place_name_ko")
    )

    scored = []
    for post in posts:
        place_key = normalize_key(post.get("place_name_ko", ""), city_ko)
        mention_count = place_counter.get(place_key, 1)
        text_blob = f"{post.get('title_ko', '')} {post.get('description_ko', '')}"

        popularity_score = (
            (mention_count * 1.7)
            + recency_score(post.get("post_date", ""))
            + keyword_popularity_boost(text_blob)
        )

        local = get_local_place(f"{city_ko} {post.get('place_name_ko', '')}".strip()) if post.get("place_name_ko") else None

        scored.append(
            {
                **post,
                "city_ko": city_ko,
                "mention_count": mention_count,
                "popularity_score": round(popularity_score, 2),
                "local": local,
            }
        )

    scored.sort(key=lambda x: x["popularity_score"], reverse=True)

    final_items = []
    for item in scored[: max(1, min(limit, 50))]:
        local = item.get("local") or {}
        place_ko = local.get("name_ko") or item.get("place_name_ko", "")
        place_en = translate_to_english(place_ko) if place_ko else ""
        neighborhood_ko = local.get("address_ko", "")
        neighborhood_en = translate_to_english(neighborhood_ko) if neighborhood_ko else ""

        final_items.append(
            {
                "title_ko": item.get("title_ko", ""),
                "title_en": translate_to_english(item.get("title_ko", "")),
                "description_en": translate_to_english(item.get("description_ko", "")),
                "place_name_ko": place_ko,
                "place_name_en": place_en,
                "neighborhood_ko": neighborhood_ko,
                "neighborhood_en": neighborhood_en,
                "blog_link": item.get("link", ""),
                "map_link": local.get("map_link") or naver_search_map_link(place_ko, city_ko=city_ko),
                "post_date": item.get("post_date", ""),
                "mention_count": item.get("mention_count", 1),
                "popularity_score": item.get("popularity_score", 0),
                "source_query_ko": item.get("query_ko", ""),
            }
        )

    return {
        "input_query_en": query_en,
        "city": city,
        "city_ko": city_ko,
        "categories": categories,
        "queries_ko": queries_ko,
        "count": len(final_items),
        "items": final_items,
        "ranking_notes": "Popularity is a proxy score: repeated place mentions + recency + hot-keyword signals.",
        "mode": "live",
    }


class AppHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/api/search":
            self.handle_api_search(parsed)
            return

        if parsed.path == "/":
            self.path = "/index.html"

        return super().do_GET()

    def translate_path(self, path):
        path = urllib.parse.urlparse(path).path
        clean_path = path.lstrip("/")
        return str(STATIC_DIR / clean_path)

    def handle_api_search(self, parsed):
        params = urllib.parse.parse_qs(parsed.query)
        query = params.get("q", [""])[0].strip()
        city = params.get("city", ["seoul"])[0].strip().lower()
        categories = [
            c.strip()
            for c in params.get("categories", ["restaurants,cafes,bars,activities,gyms"])[0].split(",")
            if c.strip()
        ]
        limit = int(params.get("limit", ["20"])[0])
        use_mock = to_bool(params.get("mock", ["0"])[0], default=False) or to_bool(
            os.getenv("OFFLINE_MOCK_MODE", "0"), default=False
        )
        auto_fallback = to_bool(params.get("fallback", ["1"])[0], default=True)

        if not query:
            self.respond_json(400, {"error": "Please provide a query using ?q="})
            return

        try:
            result = discover_places(query, city=city, categories=categories, limit=limit, use_mock=use_mock)
            self.respond_json(200, result)
        except Exception as exc:
            if auto_fallback:
                result = build_mock_response(
                    query_en=query,
                    city=city,
                    categories=categories,
                    limit=limit,
                    reason=f"Auto-fallback triggered due to: {exc}",
                )
                self.respond_json(200, result)
                return
            self.respond_json(500, {"error": str(exc)})

    def respond_json(self, code: int, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run():
    host = "0.0.0.0"
    port = int(os.getenv("PORT", "5000"))
    httpd = ThreadingHTTPServer((host, port), AppHandler)
    print(f"Server running at http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    run()
