#!/usr/bin/env python
"""graph_query.py — graph.sqlite에 대한 1~N hop 이웃 질의(재귀 CTE).

GRAPH_LAYER.md Phase 1. LLM/에이전트가 INGEST/QUERY 때 호출해 컨텍스트를 좁힌다.
graph.sqlite가 없으면 build_graph로 즉석 빌드한다.

예:
  python tools/graph_query.py --neighbors "SK하이닉스"
  python tools/graph_query.py --neighbors "엔비디아" --rel SUPPLIES_TO --hops 2 --min-conf 0.5
  python tools/graph_query.py --neighbors "HBM" --both --hops 2
"""
import argparse
import os
import sqlite3
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "graph.sqlite")


def ensure_db(path):
    """graph.sqlite가 없으면 build_graph로 생성."""
    if os.path.exists(path):
        return
    sys.path.insert(0, os.path.join(BASE, "tools"))
    import build_graph
    build_graph.main()


def resolve_node(con, term):
    """term을 노드 id로 해석: id 정확일치 > name 정확일치 > id/name 부분일치(유일할 때)."""
    row = con.execute("SELECT id FROM nodes WHERE id=?", (term,)).fetchone()
    if row:
        return row[0]
    row = con.execute("SELECT id FROM nodes WHERE name=?", (term,)).fetchone()
    if row:
        return row[0]
    like = f"%{term}%"
    rows = con.execute("SELECT id FROM nodes WHERE id LIKE ? OR name LIKE ?", (like, like)).fetchall()
    if len(rows) == 1:
        return rows[0][0]
    if len(rows) > 1:
        cands = ", ".join(r[0] for r in rows[:10])
        raise SystemExit(f"'{term}' 모호 — 후보: {cands}")
    raise SystemExit(f"'{term}' 노드를 찾을 수 없음.")


def query(con, start, rel, hops, min_conf, both):
    """재귀 CTE로 start에서 hops 이내 도달 노드(min hop)."""
    # 방향: 기본 src→dst. --both면 양방향(dst→src도 따라감).
    step = "SELECT e.dst, r.hop+1 FROM edges e JOIN reach r ON e.src=r.id WHERE {cond}"
    if both:
        step += " UNION SELECT e.src, r.hop+1 FROM edges e JOIN reach r ON e.dst=r.id WHERE {cond}"
    cond = ("r.hop < :hops"
            " AND (:rel IS NULL OR e.rel=:rel)"
            " AND (:minc IS NULL OR (e.confidence IS NOT NULL AND e.confidence >= :minc))")
    sql = (
        "WITH RECURSIVE reach(id, hop) AS ("
        "  SELECT :start, 0"
        "  UNION " + step.format(cond=cond) +
        ") SELECT id, MIN(hop) AS hop FROM reach WHERE id != :start GROUP BY id ORDER BY hop, id"
    )
    params = {"start": start, "hops": hops, "rel": rel, "minc": min_conf}
    return con.execute(sql, params).fetchall()


def direct_edges(con, start, rel, min_conf, both):
    """1-hop 직접 엣지(rel·confidence·claim_type 포함) 상세."""
    clauses = ["src=:s"]
    if both:
        clauses = ["(src=:s OR dst=:s)"]
    where = clauses[0]
    if rel:
        where += " AND rel=:rel"
    if min_conf is not None:
        where += " AND confidence IS NOT NULL AND confidence >= :minc"
    sql = (f"SELECT CASE WHEN src=:s THEN dst ELSE src END AS other, rel, confidence, claim_type "
           f"FROM edges WHERE {where} ORDER BY rel, other")
    return con.execute(sql, {"s": start, "rel": rel, "minc": min_conf}).fetchall()


def main(argv=None):
    ap = argparse.ArgumentParser(description="graph.sqlite 이웃 질의")
    ap.add_argument("--neighbors", required=True, help="시작 노드(종목/섹터/테마/이슈 이름 또는 stem)")
    ap.add_argument("--rel", default=None, help="관계종류 필터 (예: SUPPLIES_TO)")
    ap.add_argument("--hops", type=int, default=2, help="최대 hop (기본 2)")
    ap.add_argument("--min-conf", type=float, default=None, dest="min_conf",
                    help="이 신뢰도 이상 엣지만(미지정 시 confidence null 포함)")
    ap.add_argument("--both", action="store_true", help="양방향(무향)으로 탐색")
    ap.add_argument("--db", default=DB, help="graph.sqlite 경로")
    args = ap.parse_args(argv)

    ensure_db(args.db)
    con = sqlite3.connect(args.db)
    try:
        start = resolve_node(con, args.neighbors)
        node = con.execute("SELECT type,name,ticker FROM nodes WHERE id=?", (start,)).fetchone()
        flt = []
        if args.rel:
            flt.append(f"rel={args.rel}")
        if args.min_conf is not None:
            flt.append(f"min-conf={args.min_conf}")
        if args.both:
            flt.append("both")
        head = f"# {start}  [{node[0]}{' · ' + node[2] if node[2] else ''}]"
        if flt:
            head += "  (" + ", ".join(flt) + ")"
        print(head)

        direct = direct_edges(con, start, args.rel, args.min_conf, args.both)
        print(f"\n## 직접 연결 (1-hop) — {len(direct)}건")
        if direct:
            for other, rel, conf, claim in direct:
                tail = f" conf={conf}" if conf is not None else ""
                tail += f" ⚠️{claim}" if claim in ("추정", "루머") else ""
                print(f"  {rel:16} → {other}{tail}")
        else:
            print("  (없음)")

        if args.hops > 1:
            reach = query(con, start, args.rel, args.hops, args.min_conf, args.both)
            far = [(i, h) for (i, h) in reach if h > 1]
            print(f"\n## 추가 도달 (2~{args.hops} hop) — {len(far)}건")
            for i, h in far:
                print(f"  {h}-hop  {i}")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
