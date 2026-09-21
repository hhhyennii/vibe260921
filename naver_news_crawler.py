"""
네이버 뉴스 검색 결과 크롤러
- 네이버 검색 결과 페이지(search.naver.com)의 뉴스 카드에서
  언론사/제목/요약/게시시각/원문 링크/네이버뉴스 링크를 바로 추출해 CSV로 저장한다.
- 카드의 CSS 클래스(sds-comps-*)는 빌드마다 해시값이 바뀔 수 있어 신뢰하지 않고,
  각 기사마다 고유한 data-nlog-params의 "gdid" 값을 기준으로 관련 태그들을 묶어서 파싱한다.
"""

import csv
import json
import re
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

FIELDNAMES = ["press", "title", "summary", "time", "naver_url", "original_url"]
HEADER_LABELS = {
    "press": "언론사",
    "title": "제목",
    "summary": "요약",
    "time": "게시시각",
    "naver_url": "네이버뉴스 링크",
    "original_url": "원문 링크",
}


def build_search_url(query):
    return f"https://search.naver.com/search.naver?where=nexearch&sm=top_hty&fbm=0&ie=utf8&query={quote(query)}"


def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()


def visible_text(tag):
    """태그의 실제 표시 텍스트를 가져온다.
    검색어 강조 태그(<mark>)로 끊긴 텍스트도 이어붙이고, 썸네일 전용 링크나
    '새 창 열림' 같은 스크린리더용 텍스트는 제외한다."""
    span = tag.select_one("span.sds-comps-text-ellipsis")
    if span:
        # get_text(strip=True)는 <mark> 경계의 공백까지 지워버리므로
        # 원문 그대로 이어붙인 뒤 공백만 별도로 정리한다.
        return clean_text(span.get_text())
    for s in tag.stripped_strings:
        if s != "새 창 열림":
            return clean_text(s)
    return ""


def find_press_text(nav_anchor):
    """네이버뉴스 링크(.nav)의 상위 Profile 영역에서 언론사명을 찾는다.
    1차 기사는 언론사명이 링크(a)로, 관련기사는 일반 텍스트(span)로 되어 있어
    링크 유무와 상관없이 동작하도록 Profile 컨테이너 기준으로 찾는다."""
    profile = nav_anchor.find_parent(attrs={"data-sds-comp": "Profile"})
    if not profile:
        return ""
    title_el = profile.select_one(".sds-comps-profile-info-title-text")
    return visible_text(title_el) if title_el else ""


def get_gdid(tag):
    """data-nlog-params 속성에서 기사 고유 식별자(gdid)를 추출한다."""
    raw = tag.get("data-nlog-params")
    if not raw:
        return None
    try:
        return json.loads(raw).get("gdid")
    except (ValueError, TypeError):
        return None


def find_time_text(nav_anchor):
    """네이버뉴스 링크(.nav) 옆에 있는 상대 시간 텍스트(예: '7시간 전')를 찾는다."""
    subtexts_container = nav_anchor.find_parent(class_="sds-comps-profile-info-subtexts")
    if not subtexts_container:
        return ""
    for subtext in subtexts_container.select(".sds-comps-profile-info-subtext"):
        if not subtext.find("a"):
            return subtext.get_text(strip=True)
    return ""


def parse_news_list(html):
    """검색 결과 HTML에서 뉴스 카드 목록을 파싱한다."""
    soup = BeautifulSoup(html, "html.parser")
    articles = {}

    for a in soup.select("a[data-nlog-area][data-nlog-params]"):
        area = a.get("data-nlog-area", "")
        gdid = get_gdid(a)
        if not gdid:
            continue

        item = articles.setdefault(gdid, {})

        if area.endswith(".tit"):
            item["title"] = visible_text(a)
            item["original_url"] = a.get("href", "")
        elif area.endswith(".body"):
            item["summary"] = visible_text(a)
        elif area.endswith(".prof"):
            press = visible_text(a)
            if press:
                item["press"] = press
        elif area.endswith(".nav"):
            item["naver_url"] = a.get("href", "")
            item["time"] = find_time_text(a)
            if not item.get("press"):
                press = find_press_text(a)
                if press:
                    item["press"] = press

    # 제목이 파싱된 항목만 유효한 기사로 간주 (이미지/저장 버튼 등에 달린 gdid 제외)
    results = [item for item in articles.values() if item.get("title")]
    for item in results:
        for field in FIELDNAMES:
            item.setdefault(field, "")
    return results


def fetch_article_body(url):
    """네이버뉴스 기사 페이지(n.news.naver.com)에서 제목/날짜/본문 전체를 가져온다."""
    res = requests.get(url, headers=HEADERS, timeout=10)
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "html.parser")
    title_el = soup.select_one("#title_area")
    date_el = soup.select_one(".media_end_head_info_datestamp_time")
    body_el = soup.select_one("#dic_area")

    return {
        "title": clean_text(title_el.get_text()) if title_el else "",
        "date": clean_text(date_el.get_text()) if date_el else "",
        "content": body_el.get_text("\n", strip=True) if body_el else "본문을 가져오지 못했습니다.",
    }


def crawl(query):
    session = requests.Session()
    search_url = build_search_url(query)

    res = session.get(search_url, headers=HEADERS, timeout=10)
    res.raise_for_status()

    articles = parse_news_list(res.text)
    print(f"검색어 '{query}'에서 기사 {len(articles)}건 수집")
    for i, article in enumerate(articles, 1):
        print(f"[{i}/{len(articles)}] {article['press']} - {article['title']}")

    return articles


def save_to_csv(articles, filename):
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(articles)
    print(f"\n총 {len(articles)}건을 '{filename}'에 저장했습니다.")


def save_to_excel(articles, filename):
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    ws.title = "뉴스"

    ws.append([HEADER_LABELS[field] for field in FIELDNAMES])
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for article in articles:
        ws.append([article.get(field, "") for field in FIELDNAMES])

    link_columns = {FIELDNAMES.index("naver_url") + 1, FIELDNAMES.index("original_url") + 1}
    for row in range(2, ws.max_row + 1):
        for col in link_columns:
            cell = ws.cell(row=row, column=col)
            if cell.value:
                cell.hyperlink = cell.value
                cell.font = Font(color="0563C1", underline="single")

    widths = {"press": 14, "title": 45, "summary": 60, "time": 12, "naver_url": 42, "original_url": 42}
    for i, field in enumerate(FIELDNAMES, start=1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = widths.get(field, 20)

    wb.save(filename)
    print(f"\n총 {len(articles)}건을 '{filename}'에 저장했습니다.")


if __name__ == "__main__":
    QUERY = "반도체"
    articles = crawl(QUERY)
    save_to_csv(articles, f"naver_news_{QUERY}.csv")
