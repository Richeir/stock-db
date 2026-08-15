#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""BaoStock 数据 SQLite 存储层。

对应 DB_DESIGN.md 中的表设计，提供建表、幂等写入与常用查询封装。
本模块不依赖 baostock，纯 SQLite 操作，可离线测试。

典型用法::

    conn = db.connect("baostock.db")
    db.init_db(conn)
    db.upsert(conn, "stock_kline_daily", rows)   # rows: list[dict]
    klines = db.get_kline(conn, "sh.600000", adjustflag="2")
    conn.close()
"""
import os
import sqlite3

DB_PATH = os.environ.get("BAOSTOCK_DB", "baostock.db")

# 每张表：columns 为 (列名, SQL类型) 列表；pk 为主键列；indexes 为索引 DDL。
# 列名与类型严格对齐 DB_DESIGN.md。
TABLES = {
    "stock_info": {
        "columns": [
            ("code", "TEXT"), ("code_name", "TEXT"), ("market", "TEXT"),
            ("type", "TEXT"), ("ipoDate", "TEXT"), ("outDate", "TEXT"),
            ("status", "TEXT"), ("updateDate", "TEXT"), ("industry", "TEXT"),
            ("industryClassification", "TEXT"), ("last_trade_date", "TEXT"),
            ("last_close", "REAL"), ("last_pct_chg", "REAL"),
            ("last_amount", "REAL"), ("pe_ttm", "REAL"),
        ],
        "pk": ["code"],
        "indexes": [],
    },
    "etf_info": {
        "columns": [
            ("code", "TEXT"), ("code_name", "TEXT"), ("market", "TEXT"),
            ("type", "TEXT"), ("ipoDate", "TEXT"), ("outDate", "TEXT"),
            ("status", "TEXT"), ("last_trade_date", "TEXT"),
            ("last_close", "REAL"), ("last_pct_chg", "REAL"),
            ("fund_scale", "REAL"),
        ],
        "pk": ["code"],
        "indexes": [],
    },
    "stock_kline_daily": {
        "columns": [
            ("date", "TEXT"), ("code", "TEXT"), ("open", "REAL"),
            ("high", "REAL"), ("low", "REAL"), ("close", "REAL"),
            ("preclose", "REAL"), ("volume", "REAL"), ("amount", "REAL"),
            ("adjustflag", "TEXT"), ("turn", "REAL"), ("tradestatus", "TEXT"),
            ("pctChg", "REAL"), ("isST", "TEXT"),
        ],
        "pk": ["code", "date", "adjustflag"],
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_stock_daily_date ON stock_kline_daily(date)",
            "CREATE INDEX IF NOT EXISTS idx_stock_daily_codedate ON stock_kline_daily(code, date)",
        ],
    },
    "stock_kline_weekly": {
        "columns": [
            ("date", "TEXT"), ("code", "TEXT"), ("open", "REAL"),
            ("high", "REAL"), ("low", "REAL"), ("close", "REAL"),
            ("volume", "REAL"), ("amount", "REAL"), ("adjustflag", "TEXT"),
            ("turn", "REAL"), ("pctChg", "REAL"),
        ],
        "pk": ["code", "date", "adjustflag"],
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_stock_weekly_date ON stock_kline_weekly(date)",
            "CREATE INDEX IF NOT EXISTS idx_stock_weekly_codedate ON stock_kline_weekly(code, date)",
        ],
    },
    "stock_kline_monthly": {
        "columns": [
            ("date", "TEXT"), ("code", "TEXT"), ("open", "REAL"),
            ("high", "REAL"), ("low", "REAL"), ("close", "REAL"),
            ("volume", "REAL"), ("amount", "REAL"), ("adjustflag", "TEXT"),
            ("turn", "REAL"), ("pctChg", "REAL"),
        ],
        "pk": ["code", "date", "adjustflag"],
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_stock_monthly_date ON stock_kline_monthly(date)",
            "CREATE INDEX IF NOT EXISTS idx_stock_monthly_codedate ON stock_kline_monthly(code, date)",
        ],
    },
    "etf_kline_daily": {
        "columns": [
            ("date", "TEXT"), ("code", "TEXT"), ("open", "REAL"),
            ("high", "REAL"), ("low", "REAL"), ("close", "REAL"),
            ("preclose", "REAL"), ("volume", "REAL"), ("amount", "REAL"),
            ("adjustflag", "TEXT"), ("turn", "REAL"), ("tradestatus", "TEXT"),
            ("pctChg", "REAL"), ("isST", "TEXT"), ("peTTM", "REAL"),
            ("pbMRQ", "REAL"), ("psTTM", "REAL"), ("pcfNcfTTM", "REAL"),
        ],
        "pk": ["code", "date", "adjustflag"],
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_etf_daily_date ON etf_kline_daily(date)",
            "CREATE INDEX IF NOT EXISTS idx_etf_daily_codedate ON etf_kline_daily(code, date)",
        ],
    },
    "etf_kline_weekly": {
        "columns": [
            ("date", "TEXT"), ("code", "TEXT"), ("open", "REAL"),
            ("high", "REAL"), ("low", "REAL"), ("close", "REAL"),
            ("volume", "REAL"), ("amount", "REAL"), ("adjustflag", "TEXT"),
            ("turn", "REAL"), ("pctChg", "REAL"),
        ],
        "pk": ["code", "date", "adjustflag"],
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_etf_weekly_date ON etf_kline_weekly(date)",
            "CREATE INDEX IF NOT EXISTS idx_etf_weekly_codedate ON etf_kline_weekly(code, date)",
        ],
    },
    "etf_kline_monthly": {
        "columns": [
            ("date", "TEXT"), ("code", "TEXT"), ("open", "REAL"),
            ("high", "REAL"), ("low", "REAL"), ("close", "REAL"),
            ("volume", "REAL"), ("amount", "REAL"), ("adjustflag", "TEXT"),
            ("turn", "REAL"), ("pctChg", "REAL"),
        ],
        "pk": ["code", "date", "adjustflag"],
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_etf_monthly_date ON etf_kline_monthly(date)",
            "CREATE INDEX IF NOT EXISTS idx_etf_monthly_codedate ON etf_kline_monthly(code, date)",
        ],
    },
    "stock_analysis": {
        "columns": [
            ("code", "TEXT"), ("date", "TEXT"), ("score", "REAL"),
            ("signal", "TEXT"), ("rating", "TEXT"), ("is_worth_buying", "INTEGER"),
            ("hold_days", "INTEGER"), ("ma5", "REAL"), ("ma20", "REAL"),
            ("ma60", "REAL"), ("trend", "TEXT"), ("momentum_20", "REAL"),
            ("volatility_20", "REAL"), ("volume_ratio", "REAL"),
            ("note", "TEXT"), ("llm_analysis", "TEXT"),
        ],
        "pk": ["code", "date"],
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_stock_analysis_date ON stock_analysis(date)",
        ],
    },
    "etf_analysis": {
        "columns": [
            ("code", "TEXT"), ("date", "TEXT"), ("score", "REAL"),
            ("signal", "TEXT"), ("rating", "TEXT"), ("is_worth_buying", "INTEGER"),
            ("hold_days", "INTEGER"), ("ma5", "REAL"), ("ma20", "REAL"),
            ("ma60", "REAL"), ("trend", "TEXT"), ("momentum_20", "REAL"),
            ("volatility_20", "REAL"), ("volume_ratio", "REAL"),
            ("note", "TEXT"), ("llm_analysis", "TEXT"),
        ],
        "pk": ["code", "date"],
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_etf_analysis_date ON etf_analysis(date)",
        ],
    },
    "adjust_factor": {
        "columns": [
            ("code", "TEXT"), ("date", "TEXT"), ("foreAdjustFactor", "REAL"),
            ("backAdjustFactor", "REAL"),
        ],
        "pk": ["code", "date"],
        "indexes": [],
    },
}


# ---------- 基础工具 ----------

def connect(db_path=DB_PATH):
    """打开 SQLite 连接，row_factory 设为 Row（查询结果可转 dict）。"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _create_sql(name):
    meta = TABLES[name]
    pk = set(meta["pk"])
    parts = []
    for col, typ in meta["columns"]:
        notnull = " NOT NULL" if col in pk else ""
        parts.append(f"  {col} {typ}{notnull}")
    parts.append(f"  PRIMARY KEY ({', '.join(meta['pk'])})")
    return f"CREATE TABLE IF NOT EXISTS {name} (\n" + ",\n".join(parts) + "\n)"


def init_db(conn):
    """按 TABLES 定义建全部表与索引（幂等，可重复调用）。"""
    for name in TABLES:
        conn.execute(_create_sql(name))
        for idx in TABLES[name]["indexes"]:
            conn.execute(idx)
    conn.commit()


# ---------- 类型转换（BaoStock 返回 str，空串→NULL） ----------

def _to_float(v):
    if v is None:
        return None
    s = str(v).strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _to_int(v):
    if v is None:
        return None
    s = str(v).strip()
    if s == "":
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def _to_text(v):
    if v is None:
        return None
    s = str(v).strip()
    return s if s != "" else None


# ---------- 写入 ----------

def upsert(conn, table, rows):
    """幂等写入：主键冲突时覆盖整行（INSERT OR REPLACE）。

    rows 为 list[dict]，键名与表列对齐；缺失列自动填 NULL，多余键忽略。
    返回写入行数。table 必须是 TABLES 中预定义的表名（防 SQL 注入）。
    """
    if table not in TABLES:
        raise ValueError(f"未知表: {table!r}（合法表名见 db.TABLES）")
    meta = TABLES[table]
    cols = [c for c, _ in meta["columns"]]
    typmap = dict(meta["columns"])
    col_sql = ", ".join(cols)
    placeholders = ", ".join("?" for _ in cols)
    sql = f"INSERT OR REPLACE INTO {table} ({col_sql}) VALUES ({placeholders})"

    values = []
    for r in rows:
        row = []
        for c in cols:
            raw = r.get(c)
            t = typmap[c]
            if t == "REAL":
                row.append(_to_float(raw))
            elif t == "INTEGER":
                row.append(_to_int(raw))
            else:
                row.append(_to_text(raw))
        values.append(tuple(row))

    if values:
        conn.executemany(sql, values)
    return len(values)


# ---------- 查询封装 ----------

def _fetch(conn, sql, params=()):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def get_kline(conn, code, table="stock_kline_daily", adjustflag="2",
              start=None, end=None, limit=None):
    """按 code / 复权方式查询 K 线，日期升序；start/end/limit 为可选过滤。"""
    if table not in TABLES:
        raise ValueError(f"未知表: {table!r}")
    cols = [c for c, _ in TABLES[table]["columns"]]
    sql = f"SELECT {', '.join(cols)} FROM {table} WHERE code=? AND adjustflag=?"
    params = [code, adjustflag]
    if start:
        sql += " AND date>=?"
        params.append(start)
    if end:
        sql += " AND date<=?"
        params.append(end)
    sql += " ORDER BY date"
    if limit:
        sql += " LIMIT ?"
        params.append(int(limit))
    return _fetch(conn, sql, params)


def get_stock_info(conn, code=None):
    sql = "SELECT * FROM stock_info"
    params = [code] if code else []
    if code:
        sql += " WHERE code=?"
    return _fetch(conn, sql, params)


def get_etf_info(conn, code=None):
    sql = "SELECT * FROM etf_info"
    params = [code] if code else []
    if code:
        sql += " WHERE code=?"
    return _fetch(conn, sql, params)


def get_analysis(conn, table="stock_analysis", code=None, latest_only=False):
    """查询分析结果；latest_only=True 时每只 code 只返回最新一条。"""
    if table not in TABLES or "analysis" not in table:
        raise ValueError(f"非分析表: {table!r}")
    if latest_only:
        sql = (
            f"SELECT a.* FROM {table} a "
            f"JOIN (SELECT code, MAX(date) AS md FROM {table} GROUP BY code) m "
            f"ON a.code = m.code AND a.date = m.md"
        )
        params = []
        if code:
            sql += " WHERE a.code=?"
            params.append(code)
        return _fetch(conn, sql, params)
    sql = f"SELECT * FROM {table}"
    params = []
    if code:
        sql += " WHERE code=?"
        params.append(code)
    sql += " ORDER BY code, date"
    return _fetch(conn, sql, params)


def count_stats(conn):
    """首页统计：收录数量 / 已分析数量 / 已分析次数（对应 DB_DESIGN §8）。"""
    return _fetch(
        conn,
        """
        SELECT
          (SELECT COUNT(*) FROM stock_info)  AS stock_cnt,
          (SELECT COUNT(*) FROM etf_info)   AS etf_cnt,
          (SELECT COUNT(DISTINCT code) FROM stock_analysis)
            + (SELECT COUNT(DISTINCT code) FROM etf_analysis) AS analyzed_cnt,
          (SELECT COUNT(*) FROM stock_analysis)
            + (SELECT COUNT(*) FROM etf_analysis)             AS analyzed_times
        """,
    )[0]


def backfill_stock_last_quote(conn):
    """用不复权日 K 回填 stock_info 的行情字段（每个 code 取日期最大一行）。

    注：pe_ttm 不在回填列中 —— stock_kline_daily 表（DB_DESIGN §5.1）未定义
    peTTM 列，故该列保持 NULL，需另行按需抓取填充。
    """
    conn.execute(
        """
        UPDATE stock_info
        SET last_trade_date = k.date,
            last_close      = k.close,
            last_pct_chg    = k.pctChg,
            last_amount     = k.amount
        FROM (
            SELECT code, date, close, pctChg, amount,
                   ROW_NUMBER() OVER (PARTITION BY code ORDER BY date DESC) AS rn
            FROM stock_kline_daily
            WHERE adjustflag = '3'
        ) AS k
        WHERE stock_info.code = k.code AND k.rn = 1
        """
    )
    conn.commit()
    return conn.total_changes


def get_etf_quote_crosscheck(conn):
    """用不复权 ETF 日 K 交叉校验 etf_info 的收盘价与涨跌幅。"""
    return _fetch(
        conn,
        """
        SELECT e.code, e.last_trade_date, e.last_close, e.last_pct_chg,
               k.close AS kline_close, k.pctChg AS kline_pct_chg
        FROM etf_info e
        JOIN etf_kline_daily k
          ON k.code = e.code
         AND k.date = e.last_trade_date
         AND k.adjustflag = '3'
        """
    )


def list_etf_missing_scale(conn):
    """列出已有最后收盘价但 fund_scale 仍为 NULL 的 ETF（供 LLM 循环补齐）。"""
    return _fetch(
        conn,
        """
        SELECT code, code_name, last_trade_date, last_close, fund_scale
        FROM etf_info
        WHERE last_close IS NOT NULL AND fund_scale IS NULL
        """
    )
