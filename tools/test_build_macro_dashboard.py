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
    assert rows[0].startswith("| 2026-06-20 ")
    assert rows[-1].startswith("| 2026-06-07 ")
