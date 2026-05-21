"""
시민 목소리 수집기
- 네이버 뉴스 검색 API → 기사 제목/요약을 시민 반응으로 변환
- 유튜브 Data API → 관련 영상 댓글 수집
- 결과: data/citizen_voice/citizen_voice_YYYYMMDD.xlsx
"""

import os, requests, re
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

NAVER_CLIENT_ID     = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
YOUTUBE_API_KEY     = os.getenv("YOUTUBE_API_KEY")

DATA_DIR = Path(__file__).parent / "data" / "citizen_voice"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── 검색 키워드 (생활 민생 중심) ─────────────────────────
NAVER_QUERIES = [
    "휘발유 가격 올랐다 생활",
    "장바구니 물가 힘들다",
    "도시가스 요금 인상 서민",
    "배달비 올라 소상공인 어렵다",
    "전기요금 인상 가계 부담",
    "마트 물가 식료품 상승",
    "자영업자 운영비 힘들다",
    "대중교통비 유류비 부담",
]

YOUTUBE_QUERIES = [
    # 민생 생활
    "장바구니 물가 요즘 너무 올랐다",
    "휘발유 기름값 주유소 비싸다",
    "배달비 올랐다 자영업 힘들다",
    "전기요금 도시가스 인상 가계부담",
    "물가 상승 서민 생활 힘들다",
    "외식비 마트 식료품 가격",
    "소상공인 자영업 요즘 장사",
    # 미이란 전쟁
    "이란 미국 전쟁 한국 영향",
    "이란 전쟁 유가 물가",
    "미국 이란 협상 결과",
    "이란 핵 전쟁 위기",
    # 중동 전쟁
    "중동 전쟁 한국 경제 영향",
    "중동 유가 상승 서민",
    "호르무즈 봉쇄 유가 한국",
    "중동 전쟁 민생 타격",
]

# ── 전쟁/이란 관련 키워드 (전쟁 댓글도 포함) ────────────
WAR_KEYWORDS = [
    "이란", "중동", "전쟁", "호르무즈", "유가", "원유", "봉쇄",
    "트럼프", "미사일", "협상", "제재", "핵",
]

# ── 민생 관련 키워드 ──────────────────────────────────────
LIFE_KEYWORDS = [
    "물가", "가격", "요금", "비용", "생활", "서민", "가계", "월급",
    "장바구니", "마트", "식료품", "배달", "주유", "기름", "가스",
    "전기", "난방", "월세", "소상공인", "자영업", "임금", "알바",
    "치킨", "커피", "외식", "지출", "부담", "힘들", "올랐",
]

def is_life_related(text: str) -> bool:
    """민생 OR 전쟁 관련 댓글 통과"""
    life_hit = sum(1 for kw in LIFE_KEYWORDS if kw in text)
    war_hit  = sum(1 for kw in WAR_KEYWORDS if kw in text)
    return life_hit >= 1 or war_hit >= 1

TAG_MAP = {
    "휘발유": "유류비", "유가": "유류비", "기름값": "유류비", "주유": "유류비",
    "배달비": "소상공인", "자영업": "소상공인", "소상공인": "소상공인", "식당": "소상공인",
    "도시가스": "에너지", "전기요금": "에너지", "에너지": "에너지", "난방비": "에너지",
    "물가": "물가", "장바구니": "물가", "마트": "물가", "식료품": "물가",
    "정책": "정책", "지원금": "정책", "바우처": "정책", "보조금": "정책",
}

def auto_tag(text: str) -> str:
    for kw, tag in TAG_MAP.items():
        if kw in text:
            return tag
    return "민생"


# ── 네이버 뉴스 수집 ─────────────────────────────────────
def collect_naver_news(date_str: str) -> list[dict]:
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        print("[!] 네이버 API 키 없음 — 건너뜀")
        return []

    results = []
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }

    for query in NAVER_QUERIES:
        try:
            r = requests.get(
                "https://openapi.naver.com/v1/search/news.json",
                headers=headers,
                params={"query": query, "display": 5, "sort": "date"},
                timeout=10,
            )
            if r.status_code != 200:
                print(f"  네이버 오류 [{query}]: {r.status_code}")
                continue

            for item in r.json().get("items", []):
                title   = re.sub(r"<[^>]+>", "", item.get("title", "")).strip()
                desc    = re.sub(r"<[^>]+>", "", item.get("description", "")).strip()
                pub_str = item.get("pubDate", "")
                try:
                    pub_date = datetime.strptime(pub_str, "%a, %d %b %Y %H:%M:%S %z").date()
                except Exception:
                    pub_date = datetime.strptime(date_str, "%Y%m%d").date()

                comment = desc[:120] if desc else title
                if not is_life_related(title + " " + comment):
                    continue

                results.append({
                    "channel":      "naver",
                    "source_title": title[:60],
                    "comment":      comment,
                    "like_count":   0,          # 네이버 뉴스는 공감수 API 미제공
                    "posted_date":  pub_date,
                    "tag":          auto_tag(title + desc),
                    "source_url":   item.get("link", ""),
                    "bold_phrase":  "",
                })

        except Exception as e:
            print(f"  네이버 수집 실패 [{query}]: {e}")

    print(f"[OK] 네이버 뉴스 {len(results)}건 수집")
    return results


# ── 네이버 블로그 수집 ───────────────────────────────────
BLOG_QUERIES = [
    "이란 전쟁 우리 생활 영향",
    "중동 전쟁 물가 실생활",
    "휘발유 가격 요즘 힘들다",
    "장바구니 물가 마트 가격 올랐다",
    "배달비 외식비 부담 요즘",
    "도시가스 전기요금 가계 부담",
]

def collect_naver_blog(date_str: str) -> list[dict]:
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        print("[!] 네이버 API 키 없음 — 건너뜀")
        return []

    results = []
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }

    for query in BLOG_QUERIES:
        try:
            r = requests.get(
                "https://openapi.naver.com/v1/search/blog.json",
                headers=headers,
                params={"query": query, "display": 5, "sort": "date"},
                timeout=10,
            )
            if r.status_code != 200:
                print(f"  블로그 오류 [{query}]: {r.status_code}")
                continue

            for item in r.json().get("items", []):
                title   = re.sub(r"<[^>]+>", "", item.get("title", "")).strip()
                desc    = re.sub(r"<[^>]+>", "", item.get("description", "")).strip()
                pub_str = item.get("postdate", "")
                try:
                    pub_date = datetime.strptime(pub_str, "%Y%m%d").date()
                except Exception:
                    pub_date = datetime.strptime(date_str, "%Y%m%d").date()

                comment = desc[:150] if desc else title
                if not is_life_related(title + " " + comment):
                    continue

                results.append({
                    "channel":      "blog",
                    "source_title": title[:60],
                    "comment":      comment,
                    "like_count":   0,
                    "posted_date":  pub_date,
                    "tag":          auto_tag(title + desc),
                    "source_url":   item.get("link", ""),
                    "bold_phrase":  "",
                })

        except Exception as e:
            print(f"  블로그 수집 실패 [{query}]: {e}")

    print(f"[OK] 네이버 블로그 {len(results)}건 수집")
    return results


# ── 네이버 카페 수집 ─────────────────────────────────────
CAFE_QUERIES = [
    "이란 전쟁 물가 우리 생활",
    "휘발유 기름값 요즘 너무해",
    "장바구니 물가 진짜 힘들다",
    "배달비 외식 포기 요즘",
    "전기 가스 요금 인상 어떻게",
    "중동 전쟁 서민 타격",
]

def collect_naver_cafe(date_str: str) -> list[dict]:
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        print("[!] 네이버 API 키 없음 — 건너뜀")
        return []

    results = []
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }

    for query in CAFE_QUERIES:
        try:
            r = requests.get(
                "https://openapi.naver.com/v1/search/cafearticle.json",
                headers=headers,
                params={"query": query, "display": 5, "sort": "date"},
                timeout=10,
            )
            if r.status_code != 200:
                print(f"  카페 오류 [{query}]: {r.status_code}")
                continue

            for item in r.json().get("items", []):
                title   = re.sub(r"<[^>]+>", "", item.get("title", "")).strip()
                desc    = re.sub(r"<[^>]+>", "", item.get("description", "")).strip()
                pub_str = item.get("postdate", "")
                try:
                    pub_date = datetime.strptime(pub_str, "%Y%m%d").date()
                except Exception:
                    pub_date = datetime.strptime(date_str, "%Y%m%d").date()

                comment = desc[:150] if desc else title
                if not is_life_related(title + " " + comment):
                    continue

                results.append({
                    "channel":      "cafe",
                    "source_title": title[:60],
                    "comment":      comment,
                    "like_count":   0,
                    "posted_date":  pub_date,
                    "tag":          auto_tag(title + desc),
                    "source_url":   item.get("link", ""),
                    "bold_phrase":  "",
                })

        except Exception as e:
            print(f"  카페 수집 실패 [{query}]: {e}")

    print(f"[OK] 네이버 카페 {len(results)}건 수집")
    return results


# ── 유튜브 댓글 수집 ─────────────────────────────────────
def collect_youtube_comments(date_str: str) -> list[dict]:
    if not YOUTUBE_API_KEY:
        print("[!] 유튜브 API 키 없음 — 건너뜀")
        return []

    results = []
    base_date = datetime.strptime(date_str, "%Y%m%d")
    published_after = (base_date - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00Z")

    for query in YOUTUBE_QUERIES:
        try:
            # 영상 검색
            sr = requests.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "key": YOUTUBE_API_KEY,
                    "q": query,
                    "part": "snippet",
                    "type": "video",
                    "maxResults": 5,
                    "order": "relevance",
                    "publishedAfter": published_after,
                    "relevanceLanguage": "ko",
                    "regionCode": "KR",
                },
                timeout=10,
            )
            if sr.status_code != 200:
                print(f"  유튜브 검색 오류 [{query}]: {sr.status_code}")
                continue

            for vid in sr.json().get("items", []):
                vid_id    = vid["id"]["videoId"]
                vid_title = vid["snippet"]["title"]

                # 댓글 수집
                cr = requests.get(
                    "https://www.googleapis.com/youtube/v3/commentThreads",
                    params={
                        "key": YOUTUBE_API_KEY,
                        "videoId": vid_id,
                        "part": "snippet",
                        "maxResults": 20,
                        "order": "relevance",
                    },
                    timeout=10,
                )
                if cr.status_code != 200:
                    continue

                for ct in cr.json().get("items", []):
                    top = ct["snippet"]["topLevelComment"]["snippet"]
                    comment_text = top.get("textDisplay", "").strip()
                    like_count   = int(top.get("likeCount", 0))
                    pub_at       = top.get("publishedAt", "")[:10]

                    try:
                        pub_date = datetime.strptime(pub_at, "%Y-%m-%d").date()
                    except Exception:
                        pub_date = base_date.date()

                    if not comment_text or len(comment_text) < 10:
                        continue

                    if not is_life_related(comment_text):
                        continue

                    results.append({
                        "channel":      "youtube",
                        "source_title": vid_title[:60],
                        "comment":      comment_text[:200],
                        "like_count":   like_count,
                        "posted_date":  pub_date,
                        "tag":          auto_tag(vid_title + comment_text),
                        "source_url":   f"https://youtu.be/{vid_id}",
                        "bold_phrase":  "",
                    })

        except Exception as e:
            print(f"  유튜브 수집 실패 [{query}]: {e}")

    print(f"[OK] 유튜브 댓글 {len(results)}건 수집")
    return results


# ── 저장 ─────────────────────────────────────────────────
def save_xlsx(rows: list[dict], date_str: str):
    if not rows:
        print("[!] 수집 결과 없음 — 파일 저장 안 함")
        return

    df = pd.DataFrame(rows)
    df["posted_date"] = pd.to_datetime(df["posted_date"])
    df = df.sort_values(["like_count", "posted_date"], ascending=[False, False])
    df = df.drop_duplicates(subset=["comment"]).reset_index(drop=True)

    out_path = DATA_DIR / f"citizen_voice_{date_str}.xlsx"
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="data", index=False)

    print(f"[저장] 저장 완료: {out_path}  ({len(df)}건)")


# ── 메인 ─────────────────────────────────────────────────
def run(date_str: str = None):
    if date_str is None:
        date_str = datetime.today().strftime("%Y%m%d")

    print(f"\n{'='*50}")
    print(f"  시민 목소리 수집 시작 - {date_str}")
    print(f"{'='*50}")

    rows = []
    rows += collect_youtube_comments(date_str)
    save_xlsx(rows, date_str)

    print(f"\n완료! 총 {len(rows)}건\n")


if __name__ == "__main__":
    import sys
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    run(date_arg)
