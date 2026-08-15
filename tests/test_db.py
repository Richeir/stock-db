import os
import sqlite3
import tempfile

import db


def make_conn():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = db.connect(path)
    db.init_db(conn)
    return conn, path


def test_all_tables_created():
    conn, _ = make_conn()
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert db.TABLES.keys() <= names
    assert len(db.TABLES) == 11


def test_unknown_table_rejected():
    conn, _ = make_conn()
    try:
        db.upsert(conn, "evil; DROP TABLE stock_info", [])
        raise AssertionError("should reject unknown table")
    except ValueError:
        pass


def test_kline_upsert_type_conversion_and_query():
    conn, _ = make_conn()
    rows = [{
        "date": "2024-01-02", "code": "sh.600000",
        "open": "6.6300", "high": "6.6500", "low": "6.6000", "close": "6.6000",
        "preclose": "", "volume": "22066700", "amount": "0",
        "adjustflag": "2", "turn": "", "tradestatus": "1",
        "pctChg": "-0.3021", "isST": "0",
    }]
    assert db.upsert(conn, "stock_kline_daily", rows) == 1
    conn.commit()

    got = db.get_kline(conn, "sh.600000", adjustflag="2")
    assert len(got) == 1
    r = got[0]
    assert r["open"] == 6.63        # str -> float
    assert r["volume"] == 22066700.0
    assert r["preclose"] is None    # 空串 -> NULL
    assert r["turn"] is None
    assert r["tradestatus"] == "1"  # TEXT 原样保留
    assert r["code"] == "sh.600000"

    # 幂等：主键冲突覆盖整行，不新增行
    db.upsert(conn, "stock_kline_daily",
              [dict(rows[0], close="6.9900")])
    conn.commit()
    got2 = db.get_kline(conn, "sh.600000", adjustflag="2")
    assert len(got2) == 1
    assert got2[0]["close"] == 6.99


def test_kline_filter_limit():
    conn, _ = make_conn()
    rows = []
    for i, d in enumerate(["2024-01-02", "2024-01-03", "2024-01-04"]):
        rows.append({"date": d, "code": "sz.000001", "open": "1",
                     "high": "1", "low": "1", "close": f"{i+1}.0",
                     "adjustflag": "3"})
    db.upsert(conn, "stock_kline_daily", rows)
    conn.commit()
    got = db.get_kline(conn, "sz.000001", table="stock_kline_daily",
                       adjustflag="3", start="2024-01-03", limit=1)
    assert len(got) == 1
    assert got[0]["date"] == "2024-01-03"


def test_info_and_analysis_roundtrip():
    conn, _ = make_conn()
    db.upsert(conn, "stock_info", [{
        "code": "sh.600000", "code_name": "浦发银行", "market": "SH",
        "type": "1", "ipoDate": "1999-11-10", "status": "1",
        "last_close": "6.62", "last_pct_chg": "-0.30",
    }])
    db.upsert(conn, "etf_info", [{
        "code": "sh.510010", "code_name": "xxETF", "market": "SH",
        "type": "5", "status": "1", "last_close": "0.918",
    }])
    db.upsert(conn, "stock_analysis", [
        {"code": "sh.600000", "date": "2024-01-05", "score": "70",
         "signal": "BUY", "rating": "A", "is_worth_buying": "1",
         "hold_days": "15"},
        {"code": "sh.600000", "date": "2024-01-12", "score": "55",
         "signal": "HOLD", "rating": "A", "is_worth_buying": "0"},
    ])
    conn.commit()

    assert getattr(conn, "execute") and True
    assert db.get_stock_info(conn, "sh.600000")[0]["market"] == "SH"
    assert db.get_etf_info(conn, "sh.510010")[0]["last_close"] == 0.918
    assert len(db.get_analysis(conn, "stock_analysis")) == 2
    latest = db.get_analysis(conn, "stock_analysis", latest_only=True)
    assert len(latest) == 1 and latest[0]["date"] == "2024-01-12"
    assert db.get_analysis(conn, "stock_analysis", latest_only=True)[0]["score"] == 55

    stats = db.count_stats(conn)
    assert stats["stock_cnt"] == 1
    assert stats["etf_cnt"] == 1
    assert stats["analyzed_cnt"] == 1
    assert stats["analyzed_times"] == 2


def test_backfill_stock_last_quote():
    conn, _ = make_conn()
    db.upsert(conn, "stock_info", [{"code": "sh.600000", "code_name": "x",
                                    "type": "1"}])
    db.upsert(conn, "stock_kline_daily", [
        {"date": "2024-01-02", "code": "sh.600000", "close": "6.50",
         "pctChg": "0.5", "amount": "100", "adjustflag": "3"},
        {"date": "2024-01-03", "code": "sh.600000", "close": "6.60",
         "pctChg": "1.2", "amount": "200", "adjustflag": "3"},
        # 前复权行应被忽略（WHERE adjustflag='3'）
        {"date": "2024-01-04", "code": "sh.600000", "close": "9.99",
         "pctChg": "9.9", "amount": "999", "adjustflag": "2"},
    ])
    conn.commit()
    db.backfill_stock_last_quote(conn)
    row = db.get_stock_info(conn, "sh.600000")[0]
    assert row["last_close"] == 6.60
    assert row["last_trade_date"] == "2024-01-03"
