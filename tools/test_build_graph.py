import os
import sqlite3
import tempfile

import build_graph as g


def test_norm_target_strips_alias_and_anchor():
    assert g._norm_target("[[엔비디아|엔비디아(NVIDIA)]]") == "엔비디아"
    assert g._norm_target("SK하이닉스#실적") == "SK하이닉스"
    assert g._norm_target("[[삼성전자]]") == "삼성전자"


def test_extract_links_excludes_raw_and_strips_alias():
    text = "본문 [[엔비디아|엔비디아(NVIDIA)]] 참고 [[raw/social/2026-06-09_x|캡처]] 그리고 [[HBM]]."
    assert g.extract_links(text) == ["엔비디아", "HBM"]


def test_infer_rel():
    assert g.infer_rel("stock", "theme") == "BELONGS_TO_THEME"
    assert g.infer_rel("stock", "macro") == "AFFECTS"
    assert g.infer_rel("macro", "stock") == "AFFECTS"
    assert g.infer_rel("stock", "stock") == "MENTIONS"


def test_parse_frontmatter_flat_only():
    text = "\n".join([
        "---", "type: stock", "ticker: '005930'", "name: 삼성전자",
        "sector: \"[[반도체]]\"", "updated: 2026-06-10", "---", "# 삼성전자", "본문 [[HBM]]",
    ])
    flat, edges = g.parse_frontmatter(text)
    assert flat["type"] == "stock"
    assert flat["name"] == "삼성전자"
    assert edges == []  # edges: 없음


def test_parse_frontmatter_no_frontmatter():
    assert g.parse_frontmatter("# 그냥 제목\n본문") == ({}, [])


def test_build_graph_prose_edges_and_missing_node():
    pages = [
        {"stem": "삼성전자", "type": "stock", "name": "삼성전자", "ticker": "005930",
         "updated": "2026-06-10", "links": ["HBM", "엔비디아"], "edges": []},
        {"stem": "HBM", "type": "theme", "name": "HBM", "ticker": None,
         "updated": "2026-06-09", "links": [], "edges": []},
    ]
    nodes, edges = g.build_graph(pages)
    # 노드: 삼성전자, HBM, 그리고 페이지 없는 엔비디아 → _missing
    assert nodes["엔비디아"]["type"] == "_missing"
    rels = {(e["src"], e["rel"], e["dst"]) for e in edges}
    assert ("삼성전자", "BELONGS_TO_THEME", "HBM") in rels      # 대상이 theme
    assert ("삼성전자", "MENTIONS", "엔비디아") in rels          # 대상 미생성 → 기본 MENTIONS
    assert all(e["confidence"] is None for e in edges)          # prose는 confidence null


def test_build_graph_structured_edges_take_precedence_and_dedup():
    pages = [
        {"stem": "SK하이닉스", "type": "stock", "name": "SK하이닉스", "ticker": "000660",
         "updated": "2026-06-10", "links": ["엔비디아"],  # prose도 같은 타깃
         "edges": [{"rel": "SUPPLIES_TO", "target": "엔비디아", "confidence": 0.8,
                    "claim_type": "보도", "source": "raw/x", "date": "2026-06-09"}]},
        {"stem": "엔비디아", "type": "stock", "name": "엔비디아", "ticker": None,
         "updated": "2026-06-10", "links": [], "edges": []},
    ]
    nodes, edges = g.build_graph(pages)
    supplies = [e for e in edges if e["rel"] == "SUPPLIES_TO"]
    assert len(supplies) == 1 and supplies[0]["confidence"] == 0.8
    # 구조화 엣지 우선 → 같은 타깃(엔비디아) prose MENTIONS는 억제(중복 방지)
    assert not any(e["rel"] == "MENTIONS" and e["dst"] == "엔비디아" for e in edges)


def test_write_sqlite_roundtrip_and_schema():
    nodes = {"a": {"id": "a", "type": "stock", "name": "A", "ticker": "1", "updated": "2026-06-10"},
             "b": {"id": "b", "type": "theme", "name": "B", "ticker": None, "updated": None}}
    edges = [{"src": "a", "rel": "BELONGS_TO_THEME", "dst": "b",
              "confidence": None, "claim_type": None, "source": None, "date": None}]
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "graph.sqlite")
        g.write_sqlite(nodes, edges, p)
        con = sqlite3.connect(p)
        try:
            assert con.execute("SELECT count(*) FROM nodes").fetchone()[0] == 2
            row = con.execute("SELECT src,rel,dst FROM edges").fetchone()
            assert row == ("a", "BELONGS_TO_THEME", "b")
            # 인덱스 존재
            idxs = {r[1] for r in con.execute("PRAGMA index_list(edges)")}
            assert "idx_edges_src" in idxs and "idx_edges_dst" in idxs
        finally:
            con.close()


def test_write_sqlite_idempotent_overwrite():
    nodes = {"a": {"id": "a", "type": "stock", "name": "A", "ticker": None, "updated": None}}
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "graph.sqlite")
        g.write_sqlite(nodes, [], p)
        g.write_sqlite(nodes, [], p)  # 재실행 안전(파일 제거 후 재생성)
        con = sqlite3.connect(p)
        try:
            assert con.execute("SELECT count(*) FROM nodes").fetchone()[0] == 1
        finally:
            con.close()
