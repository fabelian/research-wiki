"""매크로 대시보드 생성 — 각 wiki/macro/<지표>.md의 `## 스냅샷 히스토리` 표를
파싱해 '날짜×지표' 최근 14일 매트릭스를 wiki/macro/대시보드.md로 렌더링.

규칙: 날짜는 단일 YYYY-MM-DD만(범위 스킵). 값은 셀의 첫 숫자 토큰.
같은 (지표,날짜) 중복이면 파일에서 더 아래(나중 append) 행이 승리. idempotent.

    python tools/build_macro_dashboard.py
"""
import os
import re
from datetime import datetime, timedelta, timezone

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
NUM_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?")
DAYS = 14

# 열 순서(고정): 표시명 → 파일명
INDICATORS = [
    ("환율", "원달러환율.md"),
    ("유가", "유가.md"),
    ("VIX", "VIX.md"),
    ("VKOSPI", "VKOSPI.md"),
    ("공탐", "공포탐욕지수.md"),
    ("한국CDS", "한국CDS.md"),
    ("한국금리", "한국금리.md"),
    ("미국금리", "미국금리.md"),
]

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MACRO_DIR = os.path.join(REPO_ROOT, "wiki", "macro")
OUT_PATH = os.path.join(MACRO_DIR, "대시보드.md")


def first_number(cell):
    """셀에서 첫 숫자 토큰을 콤마 제거해 반환. 없으면 None."""
    m = NUM_RE.search(cell)
    if not m:
        return None
    return m.group(0).replace(",", "")


def parse_snapshots(text):
    """페이지 본문에서 모든 `## 스냅샷 히스토리` 섹션의 (날짜→값) 사전.
    파일 위쪽→아래쪽 순서로 채우므로 같은 날짜는 마지막(최신 append) 행이 승리."""
    result = {}
    in_section = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("## "):
            in_section = s.startswith("## 스냅샷 히스토리")
            continue
        if not in_section or not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 2:
            continue
        date_cell, value_cell = cells[0], cells[1]
        if not DATE_RE.match(date_cell):  # 헤더 '날짜'·구분선·범위 날짜 스킵
            continue
        val = first_number(value_cell)
        if val is None:
            continue
        result[date_cell] = val
    return result


def build_table(data, days=DAYS):
    """data: {표시명: {날짜: 값}} → 마크다운 표 문자열(날짜 내림차순, 최근 days개)."""
    headers = list(data.keys())
    all_dates = sorted({d for ind in data.values() for d in ind}, reverse=True)[:days]
    out = ["| 날짜 | " + " | ".join(headers) + " |"]
    out.append("|------|" + "------|" * len(headers))
    for d in all_dates:
        row = [d] + [data[h].get(d, "-") for h in headers]
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def read_created(path):
    """기존 대시보드의 created 보존(없으면 None)."""
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("created:"):
                return line.split(":", 1)[1].strip()
    return None


def render_page(table, today, created):
    return "\n".join([
        "---",
        "type: macro",
        "name: 대시보드",
        "category: 종합",
        'unit: "-"',
        f"created: {created or today}",
        f"updated: {today}",
        "---",
        "# 매크로 대시보드",
        "",
        "> 이 페이지는 `tools/build_macro_dashboard.py`가 각 거시 페이지의 "
        "`## 스냅샷 히스토리`에서 자동 생성합니다. 최근 14일 · **직접 편집 금지**.",
        "> 값 규칙: 같은 날짜 여러 행이면 최신 행의 첫 숫자, 빈 셀은 `-`.",
        "",
        table,
        "",
    ])


def main():
    data = {}
    for name, fname in INDICATORS:
        path = os.path.join(MACRO_DIR, fname)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                data[name] = parse_snapshots(f.read())
        else:
            data[name] = {}
    today = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d")
    table = build_table(data)
    page = render_page(table, today, read_created(OUT_PATH))
    with open(OUT_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(page)
    print(f"[OK] {OUT_PATH} 생성 — 지표 {len(INDICATORS)} · 날짜 {min(DAYS, len({d for ind in data.values() for d in ind}))}")


if __name__ == "__main__":
    main()
