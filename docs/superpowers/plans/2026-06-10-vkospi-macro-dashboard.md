# VKOSPI 거시 페이지 + 매크로 대시보드 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** VKOSPI를 거시 지표로 추가하고, 8개 거시지표의 최근 14일 값을 한눈에 보는 매크로 대시보드를 자동 생성한다.

**Architecture:** `_repo`(위키 콘텐츠)에 VKOSPI 페이지·생성도구·대시보드를 추가하고 매일 워크플로에 연결. `_app`(봇)의 seed 목록에 VKOSPI를 더해 자동 수집까지 잇는다. 대시보드는 각 거시 페이지의 `## 스냅샷 히스토리` 표를 파싱해 날짜×지표 매트릭스로 렌더링한다.

**Tech Stack:** Python 3.12(표준 라이브러리만), Markdown, GitHub Actions, pytest.

**작업 위치:** 모든 `_repo` 작업은 `C:\Users\MYCOM\Documents\Claude\Projects\research-wiki\_repo`(브랜치 `feat/vkospi-macro-dashboard`)에서, `_app` 작업은 `...\_app`에서. 명령은 해당 폴더 기준 상대경로로 표기.

---

## 파일 구조

- Create: `_repo/wiki/macro/VKOSPI.md` — VKOSPI 거시 페이지(웹검색 시딩)
- Modify: `_repo/CLAUDE.md:54-55` — 스키마 대상지표 8종·셀사이드 전망 생략 목록
- Create: `_repo/tools/build_macro_dashboard.py` — 대시보드 생성 도구
- Create: `_repo/tools/test_build_macro_dashboard.py` — 파서 단위 테스트
- Create: `_repo/wiki/macro/대시보드.md` — 도구 산출물(생성)
- Modify: `_repo/.github/workflows/index.yml` — 매일 대시보드 재생성 스텝
- Modify: `_app/scripts/seed_macro.py` — VKOSPI 봇 타깃 1행

---

## Task 1: 대시보드 생성 도구 (TDD)

**Files:**
- Create: `tools/build_macro_dashboard.py`
- Test: `tools/test_build_macro_dashboard.py`

도구가 위험 지점(지저분한 표 파싱)이므로 테스트 먼저.

- [ ] **Step 1: 실패하는 테스트 작성** — `tools/test_build_macro_dashboard.py`

```python
import build_macro_dashboard as m


def test_first_number_plain():
    assert m.first_number("21.35") == "21.35"


def test_first_number_range_takes_first():
    assert m.first_number("21.35~21.51 (장중 고점 21.51)") == "21.35"


def test_first_number_with_comma_and_unit():
    assert m.first_number("1,512.10원") == "1512.10"


def test_first_number_with_annotation():
    assert m.first_number("76.63(+4.34%)") == "76.63"


def test_first_number_none():
    assert m.first_number("N/A") is None
    assert m.first_number("") is None


def test_parse_snapshots_basic():
    text = "\n".join([
        "## 스냅샷 히스토리",
        "| 날짜 | VIX(pt) | 출처 |",
        "|------|---------|------|",
        "| 2026-06-05 | 15.40 | src |",
        "| 2026-06-06 | 21.35~21.51 (급등) | src |",
    ])
    assert m.parse_snapshots(text) == {"2026-06-05": "15.40", "2026-06-06": "21.35"}


def test_parse_snapshots_skips_range_dates():
    text = "\n".join([
        "## 스냅샷 히스토리",
        "| 날짜 | 값 | 출처 |",
        "| 2026-06-05~06 | 21.35 | src |",
        "| 2026-06-07 | 21.51 | src |",
    ])
    assert m.parse_snapshots(text) == {"2026-06-07": "21.51"}


def test_parse_snapshots_last_row_wins_for_duplicate_date():
    text = "\n".join([
        "## 스냅샷 히스토리",
        "| 날짜 | 값 | 출처 |",
        "| 2026-06-08 | 19.35 | 프리마켓 |",
        "| 2026-06-08 | 21.51 | 종가 |",
    ])
    assert m.parse_snapshots(text) == {"2026-06-08": "21.51"}


def test_parse_snapshots_multiple_sections_merge():
    text = "\n".join([
        "## 스냅샷 히스토리",
        "| 날짜 | 값 | 출처 |",
        "| 2026-06-01 | 10 | a |",
        "## 영향 관계",
        "| 무시 | 999 | x |",
        "## 스냅샷 히스토리",
        "| 날짜 | 값 | 출처 |",
        "| 2026-06-02 | 20 | b |",
    ])
    assert m.parse_snapshots(text) == {"2026-06-01": "10", "2026-06-02": "20"}


def test_build_table_shape_and_missing_cells():
    data = {
        "환율": {"2026-06-09": "1512", "2026-06-08": "1520"},
        "VIX": {"2026-06-09": "21.5"},
    }
    out = m.build_table(data, days=14)
    lines = out.splitlines()
    assert lines[0] == "| 날짜 | 환율 | VIX |"
    assert lines[1] == "|------|------|------|"
    assert lines[2] == "| 2026-06-09 | 1512 | 21.5 |"
    assert lines[3] == "| 2026-06-08 | 1520 | - |"


def test_build_table_limits_days_desc():
    data = {"X": {f"2026-06-{d:02d}": str(d) for d in range(1, 21)}}
    out = m.build_table(data, days=14)
    rows = [l for l in out.splitlines() if l.startswith("| 2026-")]
    assert len(rows) == 14
    assert rows[0].startswith("| 2026-06-20 ")   # 최신이 위
    assert rows[-1].startswith("| 2026-06-07 ")
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd tools && python -m pytest test_build_macro_dashboard.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'build_macro_dashboard'`

- [ ] **Step 3: 도구 구현** — `tools/build_macro_dashboard.py`

```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd tools && python -m pytest test_build_macro_dashboard.py -v`
Expected: PASS (11 passed)

- [ ] **Step 5: 커밋**

```bash
git add tools/build_macro_dashboard.py tools/test_build_macro_dashboard.py
git commit -m "feat(tools): 매크로 대시보드 생성 도구 + 파서 테스트"
```

---

## Task 2: VKOSPI 거시 페이지 (웹검색 시딩)

**Files:**
- Create: `wiki/macro/VKOSPI.md`

웹검색이 필요한 데이터 수집 태스크. 아래 골격을 그대로 쓰고 `스냅샷 히스토리` 표만 실제 값으로 채운다.

- [ ] **Step 1: 최근 ~14거래일 VKOSPI 종가 웹검색**

검색 쿼리 예: `"VKOSPI 종가 2026-06"`, `"코스피200 변동성지수 VKOSPI 6월"`, KRX/네이버금융/연합인포맥스. 기존 [[VIX]] 페이지에 이미 있는 앵커값을 출처와 함께 활용: 2026-06-06 "70 돌파", 2026-06-08 "76.63 (+4.34%, 서킷브레이커)". 값을 못 구한 거래일은 `N/A`로 두고 사유 표기(가짜 숫자 금지).

- [ ] **Step 2: 파일 작성** — `wiki/macro/VKOSPI.md`

골격(프론트매터·섹션 고정, 표 행은 Step 1 결과로 채움):

```markdown
---
type: macro
name: VKOSPI
category: 변동성
unit: pt
created: 2026-06-10
updated: 2026-06-10
---
# VKOSPI
코스피200 변동성지수(한국판 공포지수). 국내 위험회피 강도 판단. [[VIX]]·[[공포탐욕지수]]·[[한국CDS]]와 연계 해석. 셀사이드 전망은 다루지 않는다(변동성지수, 스키마상 생략 대상).

## 최신 스냅샷
- <최신값> pt (<날짜>, 출처: <URL>)

## 스냅샷 히스토리
| 날짜 | VKOSPI(pt) | 출처 |
|------|-----------|------|
| 2026-06-08 | 76.63 (+4.34%, 서킷브레이커 발동) | https://www.edaily.co.kr/news/newspath.asp?newsid=03965526645479752 |
| 2026-06-06 | 70 (70 돌파, '검은 월요일' 경계) | https://www.digitaltoday.co.kr/news/articleView.html?idxno=672547 |
<...웹검색으로 확보한 최근 14거래일 행을 날짜·값·출처와 함께 추가...>

## 영향 관계
- VKOSPI↑ → 국내 위험회피, 외국인 코스피 순매도·[[한국CDS]] 동반 상승 경향
- VKOSPI↓ → 위험선호, 외국인 수급 우호
- [[VIX]]와 통상 동행하나 국내 고유 충격(수급·정책)에 더 민감

## 관련 출처 링크
- https://finance.naver.com/sise/sise_index.naver?code=VKOSPI
```

- [ ] **Step 3: 역링크 추가** — `wiki/macro/VIX.md`에서 VKOSPI 첫 등장 텍스트를 `[[VKOSPI]]`로 연결(본문 산문 1곳; 스냅샷 히스토리 표 셀은 건드리지 않음).

- [ ] **Step 4: 프론트매터 펜스 확인**

Run: `cd .. && python -c "import io; t=open('wiki/macro/VKOSPI.md',encoding='utf-8').read(); assert t.startswith('---'); assert t.count('---')>=2; print('frontmatter OK')"`
Expected: `frontmatter OK`

- [ ] **Step 5: 커밋**

```bash
git add wiki/macro/VKOSPI.md wiki/macro/VIX.md
git commit -m "feat(macro): VKOSPI 거시 페이지 추가(웹검색 시딩) + VIX 역링크"
```

---

## Task 3: 스키마 갱신 (CLAUDE.md)

**Files:**
- Modify: `CLAUDE.md:54-55`

- [ ] **Step 1: 셀사이드 전망 생략 목록에 VKOSPI 추가** — 54행

찾기:
```
스냅샷 히스토리(날짜·값·출처, append-only) / 셀사이드 전망(증권사·날짜·전망레벨·기간·출처 — 환율·유가·금리·CDS만, VIX·공포탐욕지수는 생략)
```
바꾸기:
```
스냅샷 히스토리(날짜·값·출처, append-only) / 셀사이드 전망(증권사·날짜·전망레벨·기간·출처 — 환율·유가·금리·CDS만, VIX·VKOSPI·공포탐욕지수는 생략)
```

- [ ] **Step 2: 대상 지표 8종으로** — 55행

찾기:
```
대상 지표: [[원달러환율]], [[유가]], [[VIX]], [[공포탐욕지수]], [[한국금리]], [[미국금리]], [[한국CDS]]
```
바꾸기:
```
대상 지표: [[원달러환율]], [[유가]], [[VIX]], [[VKOSPI]], [[공포탐욕지수]], [[한국금리]], [[미국금리]], [[한국CDS]]
```

- [ ] **Step 3: 커밋**

```bash
git add CLAUDE.md
git commit -m "docs(schema): 거시 대상지표에 VKOSPI 추가(8종)"
```

---

## Task 4: 대시보드 생성·검증

**Files:**
- Create(생성물): `wiki/macro/대시보드.md`

- [ ] **Step 1: 도구 실행**

Run: `python tools/build_macro_dashboard.py`
Expected: `[OK] .../wiki/macro/대시보드.md 생성 — 지표 8 · 날짜 14`

- [ ] **Step 2: 산출물 점검** — `wiki/macro/대시보드.md`를 열어 확인:
  - 프론트매터가 `---`로 열고 닫힘(Quartz 빌드 안전).
  - 헤더 행 `| 날짜 | 환율 | 유가 | VIX | VKOSPI | 공탐 | 한국CDS | 한국금리 | 미국금리 |`.
  - 14개 날짜 행, 최신이 위. VKOSPI 열에 Task 2 값이 보임. 빈 셀은 `-`.

- [ ] **Step 3: 재실행 idempotent 확인**

Run: `python tools/build_macro_dashboard.py && git diff --stat wiki/macro/대시보드.md`
Expected: 같은 날 재실행 시 내용 동일(diff 없음 또는 updated만).

- [ ] **Step 4: 커밋**

```bash
git add wiki/macro/대시보드.md
git commit -m "feat(macro): 매크로 대시보드 페이지 생성(최근 14일×8지표)"
```

---

## Task 5: 매일 워크플로 연결 (index.yml)

**Files:**
- Modify: `.github/workflows/index.yml`

- [ ] **Step 1: build_index 앞에 대시보드 스텝 추가**

찾기:
```yaml
      - name: Fix links + frontmatter (명명정규화·쓰레기링크 해제·type 보강)
        run: python tools/fix_wiki.py
      - name: Rebuild index.md (frontmatter → 최신순 정렬)
        run: python tools/build_index.py
```
바꾸기:
```yaml
      - name: Fix links + frontmatter (명명정규화·쓰레기링크 해제·type 보강)
        run: python tools/fix_wiki.py
      - name: Rebuild 매크로 대시보드 (스냅샷 → 날짜×지표 14일)
        run: python tools/build_macro_dashboard.py
      - name: Rebuild index.md (frontmatter → 최신순 정렬)
        run: python tools/build_index.py
```

(커밋 스텝은 이미 `wiki/`를 add하므로 `대시보드.md`도 자동 포함 — 수정 불필요.)

- [ ] **Step 2: YAML 유효성 확인**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/index.yml',encoding='utf-8')); print('yaml OK')"`
Expected: `yaml OK` (pyyaml 없으면 `pip install pyyaml` 후 실행)

- [ ] **Step 3: 커밋**

```bash
git add .github/workflows/index.yml
git commit -m "ci(index): 매일 매크로 대시보드 재생성 스텝 추가"
```

---

## Task 6: 봇 타깃에 VKOSPI 추가 (_app)

**Files:**
- Modify: `_app/scripts/seed_macro.py`

작업 폴더 전환: `C:\Users\MYCOM\Documents\Claude\Projects\research-wiki\_app`.

- [ ] **Step 1: MACRO_INDICATORS에 VKOSPI 1행 추가**

찾기:
```python
    ("MACRO-VIX", "VIX", ["VIX", "변동성지수", "공포지수"]),
    ("MACRO-FNG", "공포탐욕지수", ["공포탐욕지수", "탐욕지수", "Fear and Greed"]),
```
바꾸기:
```python
    ("MACRO-VIX", "VIX", ["VIX", "변동성지수", "공포지수"]),
    ("MACRO-VKOSPI", "VKOSPI", ["VKOSPI", "브이코스피", "코스피200 변동성"]),
    ("MACRO-FNG", "공포탐욕지수", ["공포탐욕지수", "탐욕지수", "Fear and Greed"]),
```

(alias는 VIX의 `변동성지수`·`공포지수`와 겹치지 않는 변별 토큰만 — 오분류 방지.)

- [ ] **Step 2: 문법 확인**

Run: `python -c "import ast; ast.parse(open('scripts/seed_macro.py',encoding='utf-8').read()); print('syntax OK')"`
Expected: `syntax OK`

- [ ] **Step 3: 커밋** (별도 저장소)

```bash
git -C "C:\Users\MYCOM\Documents\Claude\Projects\research-wiki\_app" add scripts/seed_macro.py
git -C "C:\Users\MYCOM\Documents\Claude\Projects\research-wiki\_app" commit -m "feat(macro): VKOSPI를 봇 거시 수집 타깃에 추가"
```

---

## Task 7: 운영 메모(코드 외) — 배포 후 seed 실행

코드가 아니라 사람이 실행하는 단계. 계획서에 기록만 하고 자동 실행하지 않는다.

- [ ] `_app` 머지·Railway 재배포 확인 후, prod DB에 1회:
  `DATABASE_URL=<prod> python -m scripts.seed_macro`
  → `MACRO-VKOSPI` Watchlist 행 생성(idempotent). 이후 봇이 매일 VKOSPI 뉴스를 수집해 `wiki/macro/VKOSPI.md` 갱신, 대시보드가 자동 반영. *(과거 Railway 미재배포로 구코드 동작한 이력 있으니 배포 반영 확인 필수 — 메모리 `verify-bot-follows-schema-rules` 참조.)*

---

## 자기검토 메모(작성자 확인 완료)
- **Spec 커버리지:** A(VKOSPI)=Task2, B(스키마)=Task3, C(도구)=Task1, D(워크플로)=Task5, E(봇)=Task6, 대시보드 산출=Task4, 운영 seed=Task7. 누락 없음.
- **다중 `## 스냅샷 히스토리` 섹션**(원달러환율.md 2회) → `parse_snapshots`가 섹션 토글로 모두 병합(`test_parse_snapshots_multiple_sections_merge`).
- **타입 일관성:** `first_number`/`parse_snapshots`/`build_table`/`render_page`/`read_created`/`main` 시그니처가 테스트·도구·호출부에서 일치.
- **알려진 한계(의도적):** 값 셀에 다른 지표 숫자가 먼저 오면(예: VIX.md의 "반도체 VIX: 57.97") 그 숫자를 취함 — 합의된 단순 규칙(첫 숫자). 스냅샷 표 정제는 COMPACT 영역(비목표).
