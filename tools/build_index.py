#!/usr/bin/env python
"""
build_index.py — wiki/ 각 페이지의 프론트매터에서 index.md 를 '생성'한다.

봇이 index.md 에 매일 append 해서 중복·깨진 행이 쌓이는 문제를 해결한다.
각 페이지의 frontmatter(type/name/ticker/sector/category/updated)만 읽어
타입별 표를 **updated 내림차순(최신 위)**으로 정렬·중복제거해 다시 쓴다.
결정적(deterministic)이라 재실행해도 동일 결과.

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
    # 프론트매터 YAML 따옴표 제거
    return (s or "").strip().strip("'\"").strip()


def inner_link(s):
    # '[["반도체"]]' -> "반도체"
    return clean(s.replace("[[", "").replace("]]", "")) if s else ""


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    stocks, sectors, themes, macro, analysts = [], [], [], [], []
    for path in glob.glob("wiki/**/*.md", recursive=True):
        fm = parse_frontmatter(path)
        t = fm.get("type", "")
        name = fm.get("name") or os.path.splitext(os.path.basename(path))[0]
        upd = fm.get("updated", "") or fm.get("created", "")
        if t == "stock":
            stocks.append({"name": name, "ticker": clean(fm.get("ticker", "-")) or "-",
                           "sector": inner_link(fm.get("sector", "")), "updated": upd})
        elif t == "sector":
            sectors.append({"name": name, "updated": upd})
        elif t == "theme":
            themes.append({"name": name, "updated": upd})
        elif t == "macro":
            macro.append({"name": name, "category": fm.get("category", ""), "updated": upd})
        elif t == "analyst":
            analysts.append({"name": name, "aff": fm.get("affiliation", ""), "updated": upd})

    by_date = lambda rows: sorted(rows, key=lambda r: (r["updated"] or "", r["name"]), reverse=True)
    # 섹터별 소속 종목(파생)
    sect_members = {}
    for s in stocks:
        sect_members.setdefault(s["sector"], []).append(s["name"])

    out = ["# 리서치 위키 — 인덱스", "",
           "> 이 페이지는 `tools/build_index.py`가 각 페이지 프론트매터에서 자동 생성합니다. "
           "표는 **최근 업데이트 내림차순**(최신 위) 정렬. 직접 편집하지 마세요.", ""]

    out += ["## 종목 (wiki/stocks/)", "",
            "| 종목명 | 티커 | 섹터 | 최근 업데이트 |", "|--------|------|------|---------------|"]
    for r in by_date(stocks):
        sec = f"[[{r['sector']}]]" if r["sector"] else "—"
        out.append(f"| [[{r['name']}]] | {r['ticker']} | {sec} | {r['updated'] or '—'} |")

    out += ["", "## 섹터 (wiki/sectors/)", "",
            "| 섹터 | 주요 종목 | 최근 업데이트 |", "|------|-----------|---------------|"]
    for r in by_date(sectors):
        members = ", ".join(f"[[{m}]]" for m in sect_members.get(r["name"], [])[:6]) or "—"
        out.append(f"| [[{r['name']}]] | {members} | {r['updated'] or '—'} |")

    out += ["", "## 거시 (wiki/macro/)", "",
            "| 지표 | 분류 | 최근 업데이트 |", "|------|------|---------------|"]
    for r in by_date(macro):
        out.append(f"| [[{r['name']}]] | {r['category'] or '—'} | {r['updated'] or '—'} |")

    out += ["", "## 테마 (wiki/themes/)", "",
            "| 테마 | 최근 업데이트 |", "|------|---------------|"]
    for r in by_date(themes):
        out.append(f"| [[{r['name']}]] | {r['updated'] or '—'} |")

    out += ["", "## 애널리스트 / 논객 (wiki/analysts/)", "",
            "| 이름 | 소속 | 최근 업데이트 |", "|------|------|---------------|"]
    for r in by_date(analysts):
        out.append(f"| [[{r['name']}]] | {r['aff'] or '—'} | {r['updated'] or '—'} |")

    open("index.md", "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    print(f"[OK] index.md 생성 — 종목 {len(stocks)} · 섹터 {len(sectors)} · 거시 {len(macro)} · 테마 {len(themes)} · 애널 {len(analysts)} (최신순 정렬)")


if __name__ == "__main__":
    main()
