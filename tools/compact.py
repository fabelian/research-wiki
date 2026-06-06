#!/usr/bin/env python
"""
compact.py — 비대해진 위키 페이지를 강력 모델(DeepSeek V4 Pro, OpenRouter 경유)로 정기 압축한다.

봇이 매일 append만 해서 페이지에 중복이 쌓인다. 이 스크립트는 임계 줄수를 넘는
wiki/ 페이지를 Claude로 재작성해 중복 병합·표준형태로 정제한다.
원본은 raw/ 에 불변 보존되므로 위키는 과감히 압축해도 정보 손실이 없다.

표준 형태:
  프론트매터(updated 갱신) → # 제목 → ## 📌 최신 요약 → 핵심/쟁점 →
  상충하는 견해(보존) → 타임라인(압축) → 출처

사용법:
    OPENROUTER_API_KEY=... python tools/compact.py           # 임계(기본 150줄) 초과 전부
    python tools/compact.py --threshold 120
    python tools/compact.py wiki/stocks/삼성전자.md           # 특정 파일만
    python tools/compact.py --dry-run                         # 호출 없이 대상만 출력

모델: 기본 deepseek/deepseek-v4-pro (OpenRouter). COMPACT_MODEL 환경변수로 변경 가능.
의존성: openai  (pip install -r tools/requirements.txt) — OpenRouter는 OpenAI 호환 API.
"""
import argparse
import glob
import os
import sys
from datetime import date

MODEL = os.environ.get("COMPACT_MODEL", "deepseek/deepseek-v4-pro")

SYSTEM = """\
너는 셀사이드 리서치 위키의 페이지를 '압축·정제'하는 편집자다. 입력으로 마크다운 페이지 1개 전체를 받고,
중복을 병합하고 표준 형태로 재작성한 마크다운 1개를 출력한다.

[배경] 자동 봇이 매일 같은 사건을 반복 append해서 페이지에 거의 동일한 섹션이 여러 개 쌓여 있다.
원본 출처는 별도 raw/ 에 불변 보존되므로, 위키 페이지는 과감히 압축해도 된다.

[표준 형태] (해당 항목이 있을 때만)
1) YAML 프론트매터 — type/ticker/name/sector/created 등 기존 키는 유지. `updated`만 {today} 로 갱신. (SK하이닉스처럼 프론트매터가 2개면 1개로 병합)
2) `# 제목` + 1~2줄 소개([[위키링크]] 유지)
3) `## 📌 최신 요약 ({today})` — 핵심 takeaway 4~6개 불릿(현재가/목표가 분포·최신 이벤트·핵심 리스크)
4) 종목이면 `## 투자의견 컨센서스 추이` 목표주가/투자의견 히스토리 '표' — 동일 행 중복 제거, 최신순 정렬, 구별되는 (날짜·증권사·투자의견·목표주가·비고) 행은 모두 보존
5) `## 핵심 투자포인트`(또는 테마/섹터면 핵심 동향) — 중복 제거 불릿
6) `## ⚠️ 리스크` — 중복 제거 불릿
7) `## 상충하는 견해` — 상충/이견은 절대 삭제 금지. 중복만 합치고 날짜·출처 유지
8) `## 주요 이벤트`(또는 타임라인) — 반복 서술을 사건당 1개 한 줄로 압축(날짜+출처)
9) `## 관련 출처/링크`
10) 🐦SNS 라벨 블록이 있으면 라벨과 함께 보존

[절대 규칙]
- 구별되는 사실·숫자·목표주가·날짜·애널리스트·증권사·출처는 최소 1회 반드시 보존. 중복만 제거.
- 상충/이견 견해 삭제 금지(날짜와 함께 통합). 폐기된 건 "(obsolete)"로 표기하되 삭제하지 않음.
- 모든 [[위키링크]] 보존. 출처·날짜 표기 유지(짧게 줄여도 됨).
- 사실을 새로 지어내지 말 것. 불확실하면 원문 표현 유지.
- 분량은 대폭 줄이되(목표 -50~75%) 정보 손실은 0이어야 한다.

[출력 형식] 재작성된 마크다운 '본문만' 출력한다. 코드펜스(```)로 감싸지 말 것. 설명·머리말·꼬리말 금지.
""".replace("{today}", date.today().isoformat())


def find_targets(args):
    if args.paths:
        return args.paths
    files = glob.glob("wiki/**/*.md", recursive=True)
    out = []
    for f in files:
        # macro 페이지는 스냅샷 시계열 구조라 자동 압축 제외(별도 규칙 필요)
        if "macro" in f.replace("\\", "/").split("/"):
            continue
        try:
            n = sum(1 for _ in open(f, encoding="utf-8"))
        except Exception:
            continue
        if n > args.threshold:
            out.append((n, f))
    out.sort(reverse=True)
    return [f for _, f in out]


def compact_one(client, path):
    src = open(path, encoding="utf-8").read()
    before = src.count("\n") + 1
    resp = client.chat.completions.create(
        model=MODEL,
        max_tokens=32000,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": src},
        ],
    )
    text = (resp.choices[0].message.content or "").strip()
    # 혹시 코드펜스로 감싸 나오면 제거
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()
    # 안전장치: 프론트매터로 시작 + 원본보다 길지 않을 때만 채택
    if not text.startswith("---"):
        print(f"[SKIP] {path}: 출력이 프론트매터로 시작하지 않음(안전상 미적용)")
        return None
    after = text.count("\n") + 1
    if after >= before:
        print(f"[SKIP] {path}: 압축 효과 없음({before}→{after})")
        return None
    open(path, "w", encoding="utf-8", newline="\n").write(text + "\n")
    print(f"[OK]   {path}: {before} → {after}줄")
    return (before, after)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", help="대상 파일(미지정 시 임계 초과 전부)")
    ap.add_argument("--threshold", type=int, default=int(os.environ.get("COMPACT_THRESHOLD", "150")))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    targets = find_targets(a)
    if not targets:
        print("압축 대상 없음(임계 이하).")
        return
    print(f"대상 {len(targets)}개 (임계 {a.threshold}줄): " + ", ".join(os.path.basename(t) for t in targets))
    if a.dry_run:
        return

    try:
        from openai import OpenAI
    except ImportError:
        sys.exit("[ERR] pip install -r tools/requirements.txt 필요(openai)")
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        sys.exit("[ERR] OPENROUTER_API_KEY 환경변수 필요")
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

    tot_b = tot_a = 0
    done = errors = 0
    for p in targets:
        try:
            r = compact_one(client, p)
            if r:
                tot_b += r[0]; tot_a += r[1]; done += 1
        except Exception as e:
            errors += 1
            print(f"[ERR]  {p}: {type(e).__name__}: {str(e)[:200]}")
    if done:
        print(f"=== {done}개 압축: {tot_b} → {tot_a}줄 ({100*(tot_b-tot_a)//max(tot_b,1)}% 감축) ===")
    # 에러가 있으면 CI가 빨간색(실패)으로 보이도록 비정상 종료(키/모델 오설정 가시화)
    if errors:
        sys.exit(f"[FAIL] {errors}개 페이지 처리 실패 — 위 오류 확인(API 키/모델 슬러그 등)")


if __name__ == "__main__":
    main()
