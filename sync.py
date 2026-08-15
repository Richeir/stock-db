#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""BaoStock 抓取 → SQLite 入库管道。

依赖 baostock（联网）。典型用法::

    .venv/bin/python sync.py                      # 默认示例同步
    .venv/bin/python sync.py --codes sh.600000    # 指定标的同步 K 线
    .venv/bin/python sync.py --etf-date 2026-02-04
    .venv/bin/python sync.py --init-only          # 只建表不联网

抓取前会自动 init_db，结束自动 logout。
"""
import argparse
import sys

import baostock as bs

import db

# 各频率 K 线的字段集（与 DB_DESIGN §5 的表列对应）
KLINE_FIELDS = {
    "d": ("date,code,open,high,low,close,preclose,volume,amount,"
          "adjustflag,turn,tradestatus,pctChg,isST"),
    "w": "date,code,open,high,low,close,volume,amount,adjustflag,turn,pctChg",
    "m": "date,code,open,high,low,close,volume,amount,adjustflag,turn,pctChg",
}
TABLE_BY_FREQ = {"d": "_kline_daily", "w": "_kline_weekly", "m": "_kline_monthly"}
ADJUSTFLAGS = ["2", "3"]  # '2' 前复权 / '3' 不复权


def _market(code):
    if code.startswith("sh."):
        return "SH"
    if code.startswith("sz."):
        return "SZ"
    return None


def login():
    lg = bs.login()
    if lg.error_code != "0":
        raise RuntimeError(f"BaoStock 登录失败: {lg.error_msg}")
    return lg


def sync_basic(conn):
    """抓取全市场证券基础信息，按 type 分表写入 stock_info/etf_info。"""
    rs = bs.query_stock_basic()
    if rs.error_code != "0":
        raise RuntimeError(f"query_stock_basic 失败: {rs.error_msg}")
    stock_rows, etf_rows = [], []
    for row in rs.data:
        rec = dict(zip(rs.fields, row))
        rec["market"] = _market(rec.get("code", ""))
        typ = rec.get("type")
        if typ == "1":
            stock_rows.append(rec)
        elif typ == "5":
            etf_rows.append(rec)
    n_stock = db.upsert(conn, "stock_info", stock_rows)
    n_etf = db.upsert(conn, "etf_info", etf_rows)
    conn.commit()
    return n_stock, n_etf


def sync_stock_kline(conn, code, start_date=None, end_date=None,
                     frequencies=("d", "w", "m"), adjustflags=ADJUSTFLAGS):
    """抓取单只股票在指定频率 × 复权方式下的 K 线入库。返回写入行数。"""
    total = 0
    for freq in frequencies:
        table = "stock" + TABLE_BY_FREQ[freq]
        for flag in adjustflags:
            rs = bs.query_history_k_data_plus(
                code, KLINE_FIELDS[freq],
                start_date=start_date or "", end_date=end_date or "",
                frequency=freq, adjustflag=flag,
            )
            if rs.error_code != "0":
                print(f"  {code} {freq} adjustflag={flag} 查询失败: {rs.error_msg}")
                continue
            rows = [dict(zip(rs.fields, r)) for r in rs.data]
            total += db.upsert(conn, table, rows)
    conn.commit()
    return total


def sync_etf_daily(conn, date):
    """抓取指定日期全市场 ETF 日 K（一次全量，不分页）。返回写入行数。"""
    rs = bs.query_daily_history_k_ETF(date=date)
    if rs.error_code != "0":
        raise RuntimeError(f"query_daily_history_k_ETF 失败: {rs.error_msg}")
    rows = [dict(zip(rs.fields, r)) for r in rs.data]
    n = db.upsert(conn, "etf_kline_daily", rows)
    conn.commit()
    return n


def main(argv=None):
    parser = argparse.ArgumentParser(description="BaoStock 数据入库管道")
    parser.add_argument("--db", default=db.DB_PATH, help="SQLite 文件路径")
    parser.add_argument("--init-only", action="store_true",
                        help="只建表不联网")
    parser.add_argument("--codes", nargs="*", default=["sh.600000"],
                        help="要同步 K 线的股票代码")
    parser.add_argument("--start", default="", help="K 线开始日期 YYYY-MM-DD")
    parser.add_argument("--end", default="", help="K 线结束日期 YYYY-MM-DD")
    parser.add_argument("--etf-date", default=None,
                        help="抓取该日期的全市场 ETF 日 K")
    args = parser.parse_args(argv)

    conn = db.connect(args.db)
    db.init_db(conn)
    if args.init_only:
        print(f"已建表于 {args.db}，共 {len(db.TABLES)} 张表")
        conn.close()
        return

    lg = login()
    try:
        n_stock, n_etf = sync_basic(conn)
        print(f"基础信息: 股票 {n_stock} 条 / ETF {n_etf} 条")

        for code in args.codes:
            n = sync_stock_kline(conn, code, args.start, args.end)
            print(f"K线 {code}: 写入 {n} 行")

        if args.etf_date:
            n = sync_etf_daily(conn, args.etf_date)
            print(f"全市场ETF日K {args.etf_date}: 写入 {n} 行")

        print(f"统计: {db.count_stats(conn)}")
    finally:
        bs.logout()
        conn.close()
        print(">>> 已登出")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001 —— 顶层脚本兜底
        sys.exit(f"错误: {e}")
