#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""BaoStock 调研 demo —— 展示常用 API 及返回值结构。

运行方式:
    .venv/bin/python demo.py

依赖:
    pip install baostock
"""
import sys

try:
    import baostock as bs
except ImportError as e:
    sys.exit("未安装 baostock，请先运行: pip install baostock")

# 打印查询结果：统一展示 error_code / error_msg / fields / 前 N 行
def show(title, rs, max_rows=3):
    print("=" * 70)
    print(f"[{title}]")
    print(f"  error_code = {rs.error_code!r}")
    print(f"  error_msg  = {rs.error_msg!r}")
    if not hasattr(rs, "fields"):
        print()
        return
    print(f"  fields     = {rs.fields}")
    data = rs.data if hasattr(rs, "data") else []
    total = rs.rows if hasattr(rs, "rows") else len(data)
    print(f"  rows       = {total}")
    for row in data[:max_rows]:
        print(f"    {row}")
    print()

def main():
    print(">>> 开始登录 BaoStock ...")
    lg = bs.login()
    print(f"login -> error_code={lg.error_code!r}, error_msg={lg.error_msg!r}")
    if lg.error_code != "0":
        print("登录失败，无法继续。请检查网络后重试。")
        return
    try:
        # ---- 1. 历史 K 线（核心 API）----
        rs = bs.query_history_k_data_plus(
            "sh.600000",
            "date,code,open,high,low,close,volume",
            start_date="2024-01-02",
            end_date="2024-01-05",
            frequency="d",
            adjustflag="3",
        )
        show("query_history_k_data_plus 日K线", rs)

        # ---- 1b. 全市场 ETF 日 K 线 ----
        rs = bs.query_daily_history_k_ETF(date="2026-02-04")
        show("query_daily_history_k_ETF 全市场ETF日K线", rs)

        # ---- 2. 证券基本信息 ----
        rs = bs.query_stock_basic(code="sh.600000")
        show("query_stock_basic 证券基本信息", rs)

        # ---- 3. 指数成分股 ----
        rs = bs.query_hs300_stocks(date="2024-01-05")
        show("query_hs300_stocks 沪深300成分", rs)

        # ---- 4. 财务数据（季度利润表）----
        rs = bs.query_profit_data(code="sh.600000", year=2023, quarter=4)
        show("query_profit_data 季度利润表", rs)

        # ---- 5. 业绩预告 ----
        rs = bs.query_forecast_report("sh.600000", start_date="2023-10-01", end_date="2024-01-05")
        show("query_forecast_report 业绩预告", rs)

        # ---- 6. 宏观利率（存款利率）----
        rs = bs.query_deposit_rate_data(start_date="2015-01-01", end_date="2015-06-01")
        show("query_deposit_rate_data 存款利率", rs)

        # ---- 7. 交易日历 ----
        rs = bs.query_trade_dates(start_date="2024-01-01", end_date="2024-01-10")
        show("query_trade_dates 交易日历", rs)

    finally:
        bs.logout()
        print(">>> 已登出")

if __name__ == "__main__":
    main()
