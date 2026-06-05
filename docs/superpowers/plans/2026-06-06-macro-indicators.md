# 거시지표 페이지 타입 추가 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 셀사이드 리서치 위키에 거시지표(macro) 페이지 타입을 추가해 환율·유가·VIX·CNN 공포탐욕지수·한국/미국 금리·한국 CDS를 스냅샷·셀사이드 전망·영향 매핑으로 누적한다.

**Architecture:** `wiki/macro/`에 지표별 1페이지(총 7개)를 마크다운으로 둔다. 데이터는 리포트 ingest 시점에 웹검색으로 스냅샷을 append하며, 같은 날짜 행은 건너뛰어 idempotent를 보장한다. `CLAUDE.md`(스키마 계약)와 `index.md`(네비)에 거시 타입을 반영하고, 기존 종목/섹터 페이지와 양방향 위키링크로 연결한다.

**Tech Stack:** Markdown + YAML frontmatter, Obsidian 스타일 위키링크 `[[ ]]`, git. 코드/테스트 프레임워크 없음 — 검증은 파일 구조 확인·git diff·grep·재실행 idempotency로 한다.

**참조 스펙:** `docs/superpowers/specs/2026-06-06-macro-indicators-design.md`

---

## File Structure

생성:
- `wiki/macro/원달러환율.md`, `wiki/macro/유가.md`, `wiki/macro/VIX.md`, `wiki/macro/공포탐욕지수.md`, `wiki/macro/한국금리.md`, `wiki/macro/미국금리.md`, `wiki/macro/한국CDS.md`

수정:
- `CLAUDE.md` — 3계층 구조 / 페이지 타입 / INGEST 워크플로
- `index.md` — 거시 섹션 추가
- `wiki/stocks/삼성전자.md`, `wiki/stocks/SK하이닉스.md`, `wiki/sectors/반도체.md` — 거시 위키링크(양방향)
- `log.md` — maintenance 기록 1행 append

---

## Task 1: 스냅샷 데이터 수집 (2026-06-06 기준)

이후 모든 페이지가 이 한 번의 수집 결과를 재사용한다(DRY).

**Files:** 없음(데이터 수집만). 결과는 작업 노트로 보관.

- [ ] **Step 1: 7개 지표의 2026-06-06(또는 최근 거래일) 값을 웹검색으로 수집**

WebSearch / WebFetch로 다음을 각각 조회하고, 값·기준일·출처 URL을 기록한다:
- 원달러 환율 (USD/KRW 종가)
- WTI · 브렌트 유가 (USD/bbl)
- VIX 종가 (pt)
- CNN Fear & Greed Index (0~100, 라벨)
- 한국: 기준금리(%), 국고채 3년/10년 금리(%)
- 미국: FFR 상단(%), 미 국채 2년/10년 금리(%)
- 한국 5년물 국가 CDS 스프레드 (bp)

- [ ] **Step 2: 수집 결과를 한 표로 정리(작업 노트)**

형식: `지표 | 값 | 기준일 | 출처URL`. 값을 못 구한 지표는 `N/A`로 두고 사유를 적는다(가짜 숫자 금지).

- [ ] **Step 3: 커밋 없음 (데이터 수집 단계)**

---

## Task 2: `원달러환율.md` 생성 (템플릿 기준 페이지)

이 페이지가 전망 섹션 포함형 macro 페이지의 표준 형태다.

**Files:**
- Create: `wiki/macro/원달러환율.md`

- [ ] **Step 1: 파일 생성 (아래 내용, `<>`는 Task 1 수집값으로 치환)**

```markdown
---
type: macro
name: 원달러환율
category: 환율
unit: KRW/USD
created: 2026-06-06
updated: 2026-06-06
---
# 원달러환율
USD/KRW 원달러 환율. 원화 약세(↑)는 [[삼성전자]]·[[SK하이닉스]] 등 수출주에 통상 우호적.
관련 섹터: [[반도체]]. 관련 금리: [[미국금리]]·[[한국금리]].

## 최신 스냅샷
- <값> 원 (<기준일>, 출처: <출처URL>)

## 스냅샷 히스토리
| 날짜 | 종가(KRW/USD) | 출처 |
|------|---------------|------|
| <기준일> | <값> | <출처URL> |

## 셀사이드 전망
| 증권사 | 날짜 | 전망레벨 | 기간 | 출처 |
|--------|------|----------|------|------|
| (추가 예정) | | | | |

## 영향 관계
- 원화약세(USD/KRW↑) → [[삼성전자]]·[[SK하이닉스]] 수출 채산성 개선
- 원화강세(↓) → 수입 원가 부담 완화, 외국인 수급 우호

## 관련 출처 링크
- <출처URL>
```

- [ ] **Step 2: 구조 검증**

Grep으로 프론트매터와 섹션 헤더 확인:
Run: `rg -n "^type: macro|^## (최신 스냅샷|스냅샷 히스토리|셀사이드 전망|영향 관계|관련 출처)" wiki/macro/원달러환율.md`
Expected: `type: macro` 1건 + `##` 헤더 5건 출력.

- [ ] **Step 3: 커밋**

```bash
git add wiki/macro/원달러환율.md
git commit -m "feat(macro): add 원달러환율 page"
```

---

## Task 3: `유가.md` 생성 (복수 시리즈 + 전망)

**Files:**
- Create: `wiki/macro/유가.md`

- [ ] **Step 1: 파일 생성 (`<>`는 Task 1 수집값으로 치환)**

```markdown
---
type: macro
name: 유가
category: 원자재
unit: USD/bbl
created: 2026-06-06
updated: 2026-06-06
---
# 유가
WTI · 브렌트 국제 유가. 유가 상승은 정유·항공 등 수송비 구조에 영향. 인플레이션·[[미국금리]] 경로와 연관.

## 최신 스냅샷
- WTI <값> / 브렌트 <값> USD/bbl (<기준일>, 출처: <출처URL>)

## 스냅샷 히스토리
| 날짜 | WTI(USD/bbl) | 브렌트(USD/bbl) | 출처 |
|------|--------------|------------------|------|
| <기준일> | <값> | <값> | <출처URL> |

## 셀사이드 전망
| 증권사 | 날짜 | 전망레벨 | 기간 | 출처 |
|--------|------|----------|------|------|
| (추가 예정) | | | | |

## 영향 관계
- 유가↑ → 정유 정제마진/항공 연료비 영향, 인플레 압력 → [[미국금리]] 경로 변화
- 유가↓ → 수입물가 완화

## 관련 출처 링크
- <출처URL>
```

- [ ] **Step 2: 구조 검증**

Run: `rg -n "^type: macro" wiki/macro/유가.md`
Expected: 1건 출력.

- [ ] **Step 3: 커밋**

```bash
git add wiki/macro/유가.md
git commit -m "feat(macro): add 유가 page"
```

---

## Task 4: `한국금리.md` 생성 (복수 시리즈 + 전망)

**Files:**
- Create: `wiki/macro/한국금리.md`

- [ ] **Step 1: 파일 생성 (`<>`는 Task 1 수집값으로 치환)**

```markdown
---
type: macro
name: 한국금리
category: 금리
unit: "%"
created: 2026-06-06
updated: 2026-06-06
---
# 한국금리
한국은행 기준금리 + 국고채 3년/10년 금리. [[원달러환율]]·외국인 수급과 연관.

## 최신 스냅샷
- 기준금리 <값>% / 국고3년 <값>% / 국고10년 <값>% (<기준일>, 출처: <출처URL>)

## 스냅샷 히스토리
| 날짜 | 기준금리(%) | 국고3년(%) | 국고10년(%) | 출처 |
|------|-------------|------------|-------------|------|
| <기준일> | <값> | <값> | <값> | <출처URL> |

## 셀사이드 전망
| 증권사 | 날짜 | 전망레벨 | 기간 | 출처 |
|--------|------|----------|------|------|
| (추가 예정) | | | | |

## 영향 관계
- 금리↑ → 성장주 밸류에이션 부담, [[원달러환율]] 방어 요인
- 미-한 금리차 확대 → 원화 약세 압력([[미국금리]] 참조)

## 관련 출처 링크
- <출처URL>
```

- [ ] **Step 2: 구조 검증**

Run: `rg -n "^type: macro" wiki/macro/한국금리.md`
Expected: 1건 출력.

- [ ] **Step 3: 커밋**

```bash
git add wiki/macro/한국금리.md
git commit -m "feat(macro): add 한국금리 page"
```

---

## Task 5: `미국금리.md` 생성 (복수 시리즈 + 전망)

**Files:**
- Create: `wiki/macro/미국금리.md`

- [ ] **Step 1: 파일 생성 (`<>`는 Task 1 수집값으로 치환)**

```markdown
---
type: macro
name: 미국금리
category: 금리
unit: "%"
created: 2026-06-06
updated: 2026-06-06
---
# 미국금리
미 연준 FFR + 미 국채 2년/10년 금리. 글로벌 위험선호·[[원달러환율]]의 핵심 변수.

## 최신 스냅샷
- FFR(상단) <값>% / 미국채2년 <값>% / 미국채10년 <값>% (<기준일>, 출처: <출처URL>)

## 스냅샷 히스토리
| 날짜 | FFR상단(%) | 미국채2년(%) | 미국채10년(%) | 출처 |
|------|-----------|--------------|----------------|------|
| <기준일> | <값> | <값> | <값> | <출처URL> |

## 셀사이드 전망
| 증권사 | 날짜 | 전망레벨 | 기간 | 출처 |
|--------|------|----------|------|------|
| (추가 예정) | | | | |

## 영향 관계
- 미 금리↑ → 글로벌 위험회피, 원화 약세([[원달러환율]]↑), 성장주 압박
- 장단기 역전 → 경기침체 시그널 해석

## 관련 출처 링크
- <출처URL>
```

- [ ] **Step 2: 구조 검증**

Run: `rg -n "^type: macro" wiki/macro/미국금리.md`
Expected: 1건 출력.

- [ ] **Step 3: 커밋**

```bash
git add wiki/macro/미국금리.md
git commit -m "feat(macro): add 미국금리 page"
```

---

## Task 6: `한국CDS.md` 생성 (단일 시리즈 + 전망)

**Files:**
- Create: `wiki/macro/한국CDS.md`

- [ ] **Step 1: 파일 생성 (`<>`는 Task 1 수집값으로 치환)**

```markdown
---
type: macro
name: 한국CDS
category: 신용
unit: bp
created: 2026-06-06
updated: 2026-06-06
---
# 한국CDS
한국 5년물 국가 CDS 스프레드. 국가 신용위험·외국인 수급 심리의 척도. [[VIX]]와 동반 움직임 잦음.

## 최신 스냅샷
- <값> bp (<기준일>, 출처: <출처URL>)

## 스냅샷 히스토리
| 날짜 | CDS 5Y(bp) | 출처 |
|------|------------|------|
| <기준일> | <값> | <출처URL> |

## 셀사이드 전망
| 증권사 | 날짜 | 전망레벨 | 기간 | 출처 |
|--------|------|----------|------|------|
| (추가 예정) | | | | |

## 영향 관계
- CDS↑ → 국가 신용위험 인식 확대, 외국인 자금 이탈·원화 약세([[원달러환율]]↑)
- [[VIX]] 급등 국면과 동조하는 경향

## 관련 출처 링크
- <출처URL>
```

- [ ] **Step 2: 구조 검증**

Run: `rg -n "^type: macro" wiki/macro/한국CDS.md`
Expected: 1건 출력.

- [ ] **Step 3: 커밋**

```bash
git add wiki/macro/한국CDS.md
git commit -m "feat(macro): add 한국CDS page"
```

---

## Task 7: `VIX.md` 생성 (전망 섹션 없음)

**Files:**
- Create: `wiki/macro/VIX.md`

- [ ] **Step 1: 파일 생성 (`<>`는 Task 1 수집값으로 치환) — "셀사이드 전망" 섹션 없음**

```markdown
---
type: macro
name: VIX
category: 변동성
unit: pt
created: 2026-06-06
updated: 2026-06-06
---
# VIX
S&P500 변동성 지수(공포지수). 위험선호/회피 국면 판단. [[한국CDS]]·[[공포탐욕지수]]와 연계 해석.

## 최신 스냅샷
- <값> pt (<기준일>, 출처: <출처URL>)

## 스냅샷 히스토리
| 날짜 | VIX(pt) | 출처 |
|------|---------|------|
| <기준일> | <값> | <출처URL> |

## 영향 관계
- VIX↑(통상 >20) → 위험회피, 신흥국·성장주 변동성 확대, [[한국CDS]] 동반 상승 경향
- VIX↓ → 위험선호 국면, 외국인 수급 우호

## 관련 출처 링크
- <출처URL>
```

- [ ] **Step 2: 전망 섹션이 없음을 검증**

Run: `rg -n "셀사이드 전망" wiki/macro/VIX.md`
Expected: 출력 없음(0건).

- [ ] **Step 3: 커밋**

```bash
git add wiki/macro/VIX.md
git commit -m "feat(macro): add VIX page"
```

---

## Task 8: `공포탐욕지수.md` 생성 (전망 섹션 없음)

**Files:**
- Create: `wiki/macro/공포탐욕지수.md`

- [ ] **Step 1: 파일 생성 (`<>`는 Task 1 수집값으로 치환) — "셀사이드 전망" 섹션 없음**

```markdown
---
type: macro
name: 공포탐욕지수
category: 변동성
unit: 0~100
created: 2026-06-06
updated: 2026-06-06
---
# 공포탐욕지수
CNN Fear & Greed Index (0=극단적 공포, 100=극단적 탐욕). 시장 심리 척도. [[VIX]]와 역방향 해석.

## 최신 스냅샷
- <값> (<라벨>, <기준일>, 출처: <출처URL>)

## 스냅샷 히스토리
| 날짜 | 지수(0~100) | 라벨 | 출처 |
|------|-------------|------|------|
| <기준일> | <값> | <라벨> | <출처URL> |

## 영향 관계
- 극단적 탐욕(>75) → 과열 경계 신호
- 극단적 공포(<25) → [[VIX]] 급등 동반, 단기 반등 기대 심리

## 관련 출처 링크
- <출처URL>
```

- [ ] **Step 2: 전망 섹션이 없음을 검증**

Run: `rg -n "셀사이드 전망" wiki/macro/공포탐욕지수.md`
Expected: 출력 없음(0건).

- [ ] **Step 3: 커밋**

```bash
git add wiki/macro/공포탐욕지수.md
git commit -m "feat(macro): add 공포탐욕지수 page"
```

---

## Task 9: `index.md`에 거시 섹션 추가

**Files:**
- Modify: `index.md` (테마 섹션 뒤에 추가)

- [ ] **Step 1: 파일 끝에 거시 섹션 추가 (`<>`는 Task 1 수집값으로 치환)**

`index.md` 의 테마 표 다음 줄 이후에 아래 블록을 추가:

```markdown

## 거시 (wiki/macro/)
| 지표 | 최신값 | 최근 업데이트 |
|------|--------|---------------|
| [[원달러환율]] | <값> 원 | 2026-06-06 |
| [[유가]] | WTI <값> / 브렌트 <값> | 2026-06-06 |
| [[VIX]] | <값> pt | 2026-06-06 |
| [[공포탐욕지수]] | <값> (<라벨>) | 2026-06-06 |
| [[한국금리]] | 기준 <값>% / 국고10년 <값>% | 2026-06-06 |
| [[미국금리]] | FFR <값>% / 미국채10년 <값>% | 2026-06-06 |
| [[한국CDS]] | <값> bp | 2026-06-06 |
```

- [ ] **Step 2: 검증**

Run: `rg -n "## 거시 \(wiki/macro/\)" index.md`
Expected: 1건 출력.

- [ ] **Step 3: 커밋**

```bash
git add index.md
git commit -m "docs(index): add 거시 section"
```

---

## Task 10: `CLAUDE.md` 스키마 갱신

**Files:**
- Modify: `CLAUDE.md` (3계층 구조 / 페이지 타입 / INGEST 워크플로)

- [ ] **Step 1: 3계층 구조 절에 macro 디렉토리 추가**

`CLAUDE.md` 의 `- \`wiki/\` — LLM이 소유하는 마크다운...` 항목 바로 아래 들여쓰기 목록에, 기존 index.md/log.md 줄과 같은 위치 흐름을 유지하며 다음을 추가(파일 본문에서 `wiki/` 설명 직후, `CLAUDE.md` 줄 앞):

```markdown
  - `wiki/macro/` — 거시지표 페이지 (환율·유가·VIX·공포탐욕·금리·CDS)
```

- [ ] **Step 2: "페이지 타입" 절에 거시 페이지 항목 추가**

`### 테마 페이지 (wiki/themes/)` 항목 다음에 아래 섹션을 추가:

```markdown
### 거시 페이지 (wiki/macro/)
type: macro. 거시경제 지표를 지표별 1페이지로 누적.
필수 프론트매터:
\`\`\`
type: macro
name: 원달러환율
category: 환율        # 환율/금리/원자재/변동성/신용
unit: KRW/USD
created: YYYY-MM-DD
updated: YYYY-MM-DD
\`\`\`
본문 섹션: 최신 스냅샷 / 스냅샷 히스토리(날짜·값·출처, append-only) / 셀사이드 전망(증권사·날짜·전망레벨·기간·출처 — 환율·유가·금리·CDS만, VIX·공포탐욕지수는 생략) / 영향 관계(관련 [[종목]]·[[섹터]] 위키링크) / 관련 출처 링크
대상 지표: [[원달러환율]], [[유가]], [[VIX]], [[공포탐욕지수]], [[한국금리]], [[미국금리]], [[한국CDS]]
```

(주의: 위 블록을 실제 파일에 쓸 때 `\`\`\`` 는 백틱 3개로 작성.)

- [ ] **Step 3: INGEST 워크플로에 거시 스냅샷 단계 추가**

`### INGEST (소스 추가)` 의 6단계 목록에서, 기존 6번(`index.md와 log.md를 갱신한다.`)을 7번으로 밀고 새 6번을 삽입:

```markdown
6. **거시 스냅샷**: 리포트 기준일의 거시지표 7종을 웹검색해 각 `wiki/macro/` 페이지 스냅샷 히스토리에 1행 append한다. **같은 날짜 행이 이미 있으면 건너뛴다(idempotent).** 최신 스냅샷 줄과 `updated`도 갱신한다.
```

- [ ] **Step 4: 검증**

Run: `rg -n "wiki/macro/|type: macro|거시 스냅샷" CLAUDE.md`
Expected: 3계층(1), 페이지 타입 frontmatter(1), INGEST 단계(1) 등 macro 관련 줄들이 출력.

- [ ] **Step 5: 커밋**

```bash
git add CLAUDE.md
git commit -m "docs(schema): add macro page type and INGEST snapshot step"
```

---

## Task 11: 기존 종목/섹터 페이지에 거시 양방향 링크

**Files:**
- Modify: `wiki/stocks/삼성전자.md`, `wiki/stocks/SK하이닉스.md`, `wiki/sectors/반도체.md`

- [ ] **Step 1: 각 페이지 본문에 거시 링크 1줄 추가**

`wiki/sectors/반도체.md` 의 `관련 테마:` 줄 아래에 추가:
```markdown
관련 거시: [[원달러환율]](수출 채산성), [[미국금리]]·[[VIX]](수급·위험선호)
```

`wiki/stocks/삼성전자.md` 와 `wiki/stocks/SK하이닉스.md` 각각, 본문 적절한 위치(투자포인트/리스크 인근)에 추가:
```markdown
거시 민감도: [[원달러환율]] 약세 시 수출 채산성 개선 / [[미국금리]]·[[VIX]] 변동에 외국인 수급 연동
```

- [ ] **Step 2: 링크 검증**

Run: `rg -n "\[\[원달러환율\]\]" wiki/stocks/삼성전자.md wiki/stocks/SK하이닉스.md wiki/sectors/반도체.md`
Expected: 3개 파일 각 1건 이상 출력.

- [ ] **Step 3: 커밋**

```bash
git add wiki/stocks/삼성전자.md wiki/stocks/SK하이닉스.md wiki/sectors/반도체.md
git commit -m "docs(wiki): cross-link 종목/섹터 to macro pages"
```

---

## Task 12: `log.md` 기록 + idempotency 확인

**Files:**
- Modify: `log.md`

- [ ] **Step 1: log.md 끝에 maintenance 1행 append**

```markdown
- 2026-06-06 maintenance: 거시지표(macro) 페이지 타입 신설 — wiki/macro/ 7개 지표 생성, CLAUDE.md 스키마·index.md 반영, 종목/섹터 양방향 링크.
```

- [ ] **Step 2: 전체 macro 페이지 수와 프론트매터 일관성 확인**

Run: `rg -l "^type: macro" wiki/macro/ | wc -l`
Expected: `7`

- [ ] **Step 3: idempotency 점검 (스냅샷 중복 방지 규칙 동작 확인)**

같은 날짜(2026-06-06)로 임의 페이지(예: `wiki/macro/VIX.md`)의 스냅샷 히스토리에 행을 다시 추가하려 할 때, INGEST 규칙상 "같은 날짜 행이 있으면 건너뜀"이 적용되는지 수동 확인.
Run: `rg -n "2026-06-06" wiki/macro/VIX.md`
Expected: 스냅샷 히스토리 내 2026-06-06 행이 **1건만** 존재.

- [ ] **Step 4: 커밋**

```bash
git add log.md
git commit -m "chore(log): record macro page-type rollout"
```

---

## Self-Review (작성자 점검 결과)

- **Spec 커버리지:** §2 구조→Task2-8 / §3 프론트매터→각 페이지 Step1 + Task10 / §4 본문 섹션→각 페이지(전망 유무 분기 Task7·8) / §5 데이터 흐름→Task1 수집 + Task10 INGEST 단계 + Task12 idempotency / §6 인덱스·연결→Task9·11 / §7 CLAUDE.md→Task10 / §8 범위밖→계획에 미포함(준수) / §9 완료기준→Task12 검증. 누락 없음.
- **Placeholder 점검:** `<값>`/`<출처URL>` 은 런타임 웹검색으로 채우는 실데이터 지시이며 Task1에서 수집을 강제(가짜 숫자 금지 명시). 계획상 미정(TBD)·"적절히 처리" 류 모호 지시 없음.
- **타입 일관성:** `type: macro`, frontmatter 키(name/category/unit/created/updated), 섹션명("최신 스냅샷/스냅샷 히스토리/셀사이드 전망/영향 관계/관련 출처 링크")이 전 Task에서 동일. 전망 섹션 제외 대상(VIX·공포탐욕지수)이 스펙과 일치.
