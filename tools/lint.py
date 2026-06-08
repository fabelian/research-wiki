#!/usr/bin/env python
"""
lint.py — 위키 헬스체크(읽기 전용 보고). CLAUDE.md LINT 워크플로의 기계적 점검 부분.

점검: 깨진 위키링크 / 고아 페이지(인입 링크 없음) / 데이터 공백(N/A·미확인 등) /
      프론트매터 누락 / 명명 불일치 후보.
출력은 보고만 — 파일을 수정하지 않는다.
"""
import glob
import os
import re

WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]*)?\]\]")


def stem(path):
    return os.path.splitext(os.path.basename(path))[0]


def main():
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    pages = glob.glob("wiki/**/*.md", recursive=True) + glob.glob("raw/**/*.md", recursive=True)
    # 유효 링크 타깃: 파일 stem + (있으면) frontmatter name + 전체 경로(확장자 제거)
    valid = set()
    name_of = {}
    fm_missing = []
    for p in pages:
        s = stem(p)
        valid.add(s)
        rel = p.replace("\\", "/")[:-3]  # raw/social/xxx
        valid.add(rel)
        lines = open(p, encoding="utf-8").read().splitlines()
        fm = {}
        if lines and lines[0].strip() == "---":
            for ln in lines[1:]:
                if ln.strip() == "---":
                    break
                if ":" in ln:
                    k, v = ln.split(":", 1); fm[k.strip()] = v.strip()
        if fm.get("name"):
            valid.add(fm["name"].strip().strip("'\""))
            name_of[s] = fm["name"].strip().strip("'\"")
        if p.startswith("wiki") and not fm.get("type"):
            fm_missing.append(p)

    # 모든 링크 수집 (wiki + index.md + log.md)
    link_targets = {}  # target -> set(source files)
    scan = pages + ["index.md", "log.md"]
    for p in scan:
        if not os.path.exists(p):
            continue
        txt = open(p, encoding="utf-8").read()
        for m in WIKILINK.finditer(txt):
            t = m.group(1).strip().strip("'\"")
            link_targets.setdefault(t, set()).add(p.replace("\\", "/"))

    # 깨진 링크: 타깃이 valid에 없음 (raw 경로/별칭 고려)
    broken = {}
    for t, srcs in link_targets.items():
        cand = {t, t.replace("\\", "/")}
        if cand & valid:
            continue
        broken[t] = srcs

    # 고아 페이지: wiki/ 페이지 중 어떤 링크로도 참조되지 않음 (자기 자신 제외)
    referenced = set(link_targets.keys())
    orphans = []
    for p in glob.glob("wiki/**/*.md", recursive=True):
        s = stem(p)
        nm = name_of.get(s)
        if s not in referenced and (nm is None or nm not in referenced):
            orphans.append(p.replace("\\", "/"))

    # 데이터 공백
    gap_pat = re.compile(r"N/A|미확인|미확보|미확정|조사\s*필요|TBD|YYYY-MM-DD")
    gaps = []
    for p in glob.glob("wiki/**/*.md", recursive=True):
        for i, ln in enumerate(open(p, encoding="utf-8"), 1):
            if gap_pat.search(ln):
                gaps.append((p.replace("\\", "/"), i, ln.strip()[:90]))

    # 보고
    print("=" * 60)
    print("WIKI LINT 리포트")
    print("=" * 60)
    print(f"\n[1] 깨진 위키링크 (대상 페이지 없음): {len(broken)}건")
    for t in sorted(broken):
        srcs = ", ".join(sorted(os.path.basename(s) for s in broken[t])[:4])
        print(f"  - [[{t}]]  ← {srcs}")
    print(f"\n[2] 고아 페이지 (인입 링크 0): {len(orphans)}건")
    for o in sorted(orphans):
        print(f"  - {o}")
    print(f"\n[3] 프론트매터 type 누락: {len(fm_missing)}건")
    for f in sorted(fm_missing):
        print(f"  - {f}")
    print(f"\n[4] 데이터 공백(N/A·미확인 등): {len(gaps)}건")
    for f, i, ln in gaps[:40]:
        print(f"  - {f}:{i}  {ln}")
    if len(gaps) > 40:
        print(f"  ... 외 {len(gaps)-40}건")


if __name__ == "__main__":
    main()
