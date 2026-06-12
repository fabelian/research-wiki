#!/usr/bin/env python
"""
build_index.py — wiki/ 각 페이지의 프론트매터에서 index.md 를 '생성'한다.

봇이 index.md 에 매일 append 해서 중복·깨진 행이 쌓이는 문제를 해결한다.
각 페이지의 frontmatter(type/name/ticker/sector/category/updated)만 읽어
타입별 표를 **updated 내림차순(최신 위)**으로 정렬·중복제거해 다시 쓴다.
링크는 항상 파일 stem 으로 걸어(표시는 name) 깨지지 않게 한다.

사용: python tools/build_index.py
"""
import glob
import os
import sys


def parse_frontmatter(path):
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except Exception:
        return {}
    if not lines or lines[0].strip() != "---":
        return {}
    fm = {}
    for ln in lines[1:]:
        if ln.strip() == "---":
            break
        if ":" in ln:
            k, v = ln.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm


def clean(s):
    return (s or "").strip().strip("'\"").strip()


def inner_link(s):
    return clean(s.replace("[[", "").replace("]]", "")) if s else ""


def link(stem, name):
    name = clean(name)
    return f"[[{stem}|{name}]]" if name and name != stem else f"[[{stem}]]"


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    stocks, sectors, themes, macro, analysts, issues = [], [], [], [], [], []
    for path in glob.glob("wiki/**/*.md", recursive=True):
        fm = parse_frontmatter(path)
        t = fm.get("type", "")
        stem = os.path.splitext(os.path.basename(path))[0]
        name = clean(fm.get("name")) or stem
        upd = clean(fm.get("updated")) or clean(fm.get("created"))
        rec = {"stem": stem, "name": name, "updated": upd}
        if t == "stock":
            rec.update(ticker=clean(fm.get("ticker", "-")) or "-", sector=inner_link(fm.get("sector", "")))
            stocks.append(rec)
        elif t == "sector":
            sectors.append(rec)
        elif t == "theme":
            themes.append(rec)
        elif t == "macro":
            rec["category"] = clean(fm.get("category", "")); macro.append(rec)
        elif t == "analyst":
            rec["aff"] = clean(fm.get("affiliation", "")); analysts.append(rec)
        elif t == "issue":
            rec["status"] = clean(fm.get("status", "")); issues.append(rec)

    by_date = lambda rows: sorted(rows, key=lambda r: (r["updated"] or "", r["name"]), reverse=True)
    # 섹터별 소속 종목(파생, stem 기준)
    sect_members = {}
    for s in stocks:
        sect_members.setdefault(s["sector"], []).append(s["stem"])

    out = ["# 리서치 위키 — 인덱스", "",
           "> 🕸️ **[관계 그래프 뷰어 열기](graph.html)** — 종목·섹터·테마·이슈를 노드 타입·관계종류·신뢰도로 "
           "필터·채색하는 인터랙티브 그래프(시간 슬라이더 포함).", "",
           "> 이 페이지는 `tools/build_index.py`가 각 페이지 프론트매터에서 자동 생성합니다. "
           "표는 **최근 업데이트 내림차순**(최신 위) 정렬. 직접 편집하지 마세요.", ""]

    out += ["## 종목 (wiki/stocks/)", "",
            "| 종목명 | 티커 | 섹터 | 최근 업데이트 |", "|--------|------|------|---------------|"]
    for r in by_date(stocks):
        sec = f"[[{r['sector']}]]" if r["sector"] else "—"
        out.append(f"| {link(r['stem'], r['name'])} | {r['ticker']} | {sec} | {r['updated'] or '—'} |")

    out += ["", "## 섹터 (wiki/sectors/)", "",
            "| 섹터 | 주요 종목 | 최근 업데이트 |", "|------|-----------|---------------|"]
    for r in by_date(sectors):
        members = ", ".join(f"[[{m}]]" for m in sect_members.get(r["stem"], [])[:6]) or "—"
        out.append(f"| {link(r['stem'], r['name'])} | {members} | {r['updated'] or '—'} |")

    out += ["", "## 거시 (wiki/macro/)", "",
            "| 지표 | 분류 | 최근 업데이트 |", "|------|------|---------------|"]
    for r in by_date(macro):
        out.append(f"| {link(r['stem'], r['name'])} | {r['category'] or '—'} | {r['updated'] or '—'} |")

    out += ["", "## 테마 (wiki/themes/)", "",
            "| 테마 | 최근 업데이트 |", "|------|---------------|"]
    for r in by_date(themes):
        out.append(f"| {link(r['stem'], r['name'])} | {r['updated'] or '—'} |")

    out += ["", "## 애널리스트 / 논객 (wiki/analysts/)", "",
            "| 이름 | 소속 | 최근 업데이트 |", "|------|------|---------------|"]
    for r in by_date(analysts):
        out.append(f"| {link(r['stem'], r['name'])} | {r['aff'] or '—'} | {r['updated'] or '—'} |")

    out += ["", "## 이슈/이벤트 (wiki/issues/)", "",
            "| 이슈 | 상태 | 최근 업데이트 |", "|------|------|---------------|"]
    for r in by_date(issues):
        out.append(f"| {link(r['stem'], r['name'])} | {r['status'] or '—'} | {r['updated'] or '—'} |")

    open("index.md", "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    print(f"[OK] index.md 생성 — 종목 {len(stocks)} · 섹터 {len(sectors)} · 거시 {len(macro)} · 테마 {len(themes)} · 애널 {len(analysts)} · 이슈 {len(issues)} (최신순, stem 링크)")


if __name__ == "__main__":
    main()
