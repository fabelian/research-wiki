# VKOSPI 거시 페이지 + 매크로 대시보드 — 설계

- 날짜: 2026-06-10
- 대상 저장소: `_repo`(fabelian/research-wiki, 위키 콘텐츠) + `_app`(봇)
- 상태: 승인됨(브레인스토밍)

## 목적
1. 한국 변동성지수 **VKOSPI**를 거시 지표로 추가(현재 VIX 페이지 곳곳에 산재만 됨).
2. 8개 거시지표의 **일별 값을 한눈에 보는 매크로 대시보드 표**를 자동 생성해 추가.

## 배경/제약
- 거시 페이지는 `## 스냅샷 히스토리` 표(날짜·값·출처)를 가지며 **auto-ingest 봇이 매일 append만** 함 → 표가 지저분(중복 날짜, `21.35~21.51` 범위, 값 칸 주석, `N/A`).
- 손으로 만든 대시보드는 즉시 낡으므로 **생성 도구 자동화**로 결정.
- 동일 저장소가 디스크에 2벌 존재(외곽 `research-wiki` = 낡음, 내부 `_repo` = 최신 #722). **작업은 `_repo`에서 수행.** 봇은 `_app`.

## 결정 사항(확정)
- 대시보드 형태: **날짜×지표 매트릭스, 최근 14일**(행=날짜 내림차순, 열=8지표 고정순).
- 8지표 열 순서: 원달러환율 · 유가 · VIX · VKOSPI · 공포탐욕지수 · 한국CDS · 한국금리 · 미국금리.
- 위치: 신규 페이지 `_repo/wiki/macro/대시보드.md`.
- 값 추출: 같은 날짜 여러 행이면 **파일 마지막(최신 append) 행**, 그 셀에서 **첫 숫자 토큰**. 빈칸은 `-`.
- VKOSPI 시딩: **웹검색으로 최근 ~14일치 실제 값**을 채움(VIX.md 산재 값만 쓰지 않음).
- VKOSPI 봇 자동화까지 포함(_app `seed_macro.py` 수정 + 운영 시 seed 실행).

## 구성 요소

### A. `_repo/wiki/macro/VKOSPI.md` (신규)
- 프론트매터: `type: macro / name: VKOSPI / category: 변동성 / unit: pt / created: 2026-06-10 / updated: 2026-06-10`.
- 본문(거시 스키마): `최신 스냅샷 / 스냅샷 히스토리 / 영향 관계 / 관련 출처`. **셀사이드 전망 생략**(VIX·공포탐욕지수와 동일, 변동성지수).
- 스냅샷 히스토리: 웹검색으로 최근 ~14거래일 VKOSPI 종가를 날짜·값·출처와 함께 채움. 못 구한 날은 `N/A`(가짜 숫자 금지).
- 위키링크: [[VIX]] · [[공포탐욕지수]] · [[한국CDS]] 연결. VIX.md에서 VKOSPI를 [[VKOSPI]]로 연결(역링크).

### B. `_repo/CLAUDE.md` (스키마 갱신)
- 거시 "대상 지표" 줄에 `[[VKOSPI]]` 추가(7→8종).
- "셀사이드 전망 생략" 대상(VIX·공포탐욕지수)에 VKOSPI 명시.

### C. `_repo/tools/build_macro_dashboard.py` (신규 도구)
- 입력: 8개 거시 페이지의 `## 스냅샷 히스토리` 표.
- 파싱 규칙:
  - 헤딩 `## 스냅샷 히스토리` 다음의 마크다운 표 행을 읽어 col0=날짜, col1=값.
  - 날짜: `YYYY-MM-DD` 단일 날짜만 채택. 범위(`2026-06-05~06`)·모호 행은 스킵.
  - 값: 셀에서 첫 숫자 토큰 추출(부호·소수점·콤마 허용; `21.35~21.51 (장중…)`→`21.35`). 숫자 없으면 그 행 스킵.
  - 같은 (지표, 날짜) 중복 시 **파일에서 더 아래(나중 append) 행**이 승리.
- 출력: `_repo/wiki/macro/대시보드.md` 덮어쓰기.
  - 프론트매터: `type: macro / name: 대시보드 / category: 종합 / unit: - / updated: <KST 오늘>`(created는 최초 1회 보존).
  - 상단 주석: "이 페이지는 tools/build_macro_dashboard.py가 자동 생성합니다. 직접 편집 금지."
  - 본문: 최근 14개 날짜(내림차순) × 8지표 매트릭스. 누락 셀 `-`.
- idempotent. 페이지 매핑(지표명→파일)은 도구 내 상수로 고정.

### D. `_repo/.github/workflows/index.yml` (자동화)
- 기존 매일 스텝에서 `build_index.py` **앞에** `python tools/build_macro_dashboard.py` 실행 추가(대시보드 `updated`가 인덱스에 반영되도록).

### E. `_app/scripts/seed_macro.py` (봇)
- `MACRO_INDICATORS`에 추가: `("MACRO-VKOSPI", "VKOSPI", ["VKOSPI", "브이코스피", "코스피200 변동성"])`.
- alias는 VIX의 `변동성지수`·`공포지수`와 겹치지 않는 변별 토큰만(오분류 방지).

## 테스트/검증
- `_repo/tools/test_build_macro_dashboard.py`: 파서 단위 테스트(범위 날짜 스킵 / 주석 셀 첫 숫자 / 중복 날짜 마지막 행 / N/A·빈셀 / 콤마·소수). 위험 지점이 파싱이라 필수.
- 로컬 `python tools/build_macro_dashboard.py` 실행해 `대시보드.md` 산출 확인.
- 생성물 + VKOSPI.md + CLAUDE.md가 Quartz 빌드를 깨지 않는지 프론트매터 펜스 확인(과거 compact가 펜스 누락시킨 사례 있음).

## 운영(배포) 스텝 — 코드 외
- ⚠️ `_app` 머지·배포 후 prod DB에 `python -m scripts.seed_macro` 1회 실행해야 VKOSPI Watchlist 행 생성 → 봇이 매일 채움(idempotent). abeliansw가 Railway에서 실행. *(Railway 재배포 확인 필요 — 과거 미재배포 이슈 있었음.)*

## 커밋/PR
- `_repo`: VKOSPI.md + CLAUDE.md + tools(도구+테스트) + index.yml + 대시보드.md 묶음.
- `_app`: seed_macro.py 별도 커밋(별도 저장소).

## 비목표(YAGNI)
- 대시보드의 색상/차트/스파크라인 등 시각 요소(마크다운 표만).
- 스냅샷 히스토리 표 자체의 정제·중복 제거(COMPACT 영역, 별도).
- 30일/지표×날짜 전치 등 대안 레이아웃(확정: 날짜×지표 14일).
