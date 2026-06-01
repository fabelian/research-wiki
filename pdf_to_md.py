#!/usr/bin/env python3
"""
pdf_to_md.py — 리서치 PDF를 위키 ingest용 마크다운으로 변환

사용법:
    python3 pdf_to_md.py                  # raw/reports/*.pdf 전부 변환
    python3 pdf_to_md.py 파일.pdf          # 특정 파일만

동작:
    raw/reports/ 의 각 PDF에 대해
      - 텍스트 추출
      - 파일명에서 날짜·증권사 추정 (YYYY-MM-DD_증권사_... 규칙이면 자동 인식)
      - raw/reports_md/ 에 같은 이름의 .md 생성 (frontmatter + 원문 텍스트)
    이후 Claude Code에서 "ingest raw/reports_md/파일.md" 하면
    LLM이 목표주가·투자의견·핵심포인트를 구조화해 위키에 반영.

주의: 메타데이터(TP·투자의견)는 일부러 자동 파싱하지 않음.
    한국 증권사 PDF는 레이아웃이 제각각이라 규칙 파싱이 오히려 오류를 냄.
    원문 텍스트를 그대로 넘기고, 구조화는 ingest 단계에서 LLM이 처리하는 게 정확함.
"""

import sys, re
from pathlib import Path
from datetime import date

try:
    import pdfplumber
except ImportError:
    sys.exit("pdfplumber 필요: pip install pdfplumber --break-system-packages")

BASE = Path(__file__).resolve().parent
SRC = BASE / "raw" / "reports"
OUT = BASE / "raw" / "reports_md"
OUT.mkdir(parents=True, exist_ok=True)

# 파일명 패턴: 2026-05-07_미래에셋_SK하이닉스.pdf
NAME_RE = re.compile(r"(\d{4}-\d{2}-\d{2})[_\-\s]+([^_\-\s]+)")

def parse_name(stem: str):
    m = NAME_RE.match(stem)
    if m:
        return m.group(1), m.group(2)
    return "", ""

def extract_text(pdf_path: Path) -> str:
    chunks = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            t = page.extract_text() or ""
            if t.strip():
                chunks.append(f"--- p.{i} ---\n{t.strip()}")
    return "\n\n".join(chunks)

def convert(pdf_path: Path):
    stem = pdf_path.stem
    rdate, broker = parse_name(stem)
    try:
        text = extract_text(pdf_path)
    except Exception as e:
        print(f"  ✗ {pdf_path.name}: 추출 실패 ({e})")
        return
    if not text.strip():
        print(f"  ⚠ {pdf_path.name}: 텍스트 없음 (스캔 PDF일 수 있음 — OCR 필요)")
        text = "(텍스트 추출 실패 — 스캔본일 가능성. 원본 PDF 참조)"

    fm = (
        "---\n"
        "type: raw_report\n"
        f"source_pdf: {pdf_path.name}\n"
        f"report_date: {rdate or 'UNKNOWN'}\n"
        f"broker: {broker or 'UNKNOWN'}\n"
        "ticker: 000660\n"
        "name: SK하이닉스\n"
        f"converted: {date.today().isoformat()}\n"
        "ingested: false\n"
        "---\n\n"
    )
    body = f"# {stem}\n\n> 변환된 원문. ingest 시 LLM이 투자의견·목표주가·핵심포인트를 구조화.\n\n{text}\n"
    out_path = OUT / f"{stem}.md"
    out_path.write_text(fm + body, encoding="utf-8")
    flag = "" if rdate and broker else "  (파일명에서 날짜/증권사 인식 실패 — frontmatter 수동 보정 권장)"
    print(f"  ✓ {pdf_path.name} → reports_md/{out_path.name}{flag}")

def main():
    args = sys.argv[1:]
    if args:
        pdfs = [SRC / a if not Path(a).is_absolute() else Path(a) for a in args]
    else:
        pdfs = sorted(SRC.glob("*.pdf"))
    if not pdfs:
        print(f"PDF 없음: {SRC}/ 에 PDF를 넣으세요.")
        print("권장 파일명: YYYY-MM-DD_증권사_SK하이닉스.pdf")
        return
    print(f"{len(pdfs)}개 PDF 변환 시작...")
    for p in pdfs:
        if p.exists():
            convert(p)
        else:
            print(f"  ✗ {p}: 없음")
    print(f"\n완료. 다음: Claude Code에서 reports_md/*.md 를 ingest 하세요.")

if __name__ == "__main__":
    main()
