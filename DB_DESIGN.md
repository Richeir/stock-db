# BaoStock K 线数据存储设计（SQLite）

本文件描述将 BaoStock 的股票 / ETF 日、周、月 K 线数据落库为 SQLite 的数据库设计。

## 1. 设计目标与原则

- **产品分表**：股票与 ETF **不混在同一张表**，各自独立。
- **频率分表**：日 / 周 / 月 K 各建一张表，避免混合存储造成字段与粒度混乱。
- **复权策略**：每张 K 线表同时保存 **前复权（`adjustflag='2'`）** 与 **不复权原始价（`'3'`）** 两档。
  - 前复权：符合画图 / 趋势分析需求。
  - 不复权：原始成交价"永久真实"，当某股发生新的分红送股、前复权历史价漂移时，可结合复权因子表重算最新前复权，不必整段重拉。
- **幂等写入**：以 `UNIQUE(code, date, adjustflag)` 为主键约束，重复抓取用 `INSERT OR REPLACE` / `INSERT OR IGNORE` 去重。
- **约定**：
  - `code` 带交易所前缀原文存储（如 `sh.600000`、`sh.510010`）。
  - 数值列从 BaoStock 返回的 `str` 转换为 `REAL` 入库。
  - 日期用 `TEXT` 存储，格式 `YYYY-MM-DD`（字典序即时间序）。

## 2. 数据范围与频率说明

| 频率 | 股票范围 | ETF 范围 | 字段集 |
|------|----------|----------|--------|
| 日 K | 1990-12-19 至今 | 2026-01-05 至今 | 完整字段（含 `preclose/tradestatus/isST`） |
| 周 K | 1990-12-19 至今 | 2026-01-05 至今 | 精简字段 |
| 月 K | 1990-12-19 至今 | 2026-01-05 至今 | 精简字段 |

## 3. 表清单

共 **8 张表**：6 张 K 线数据表 + 2 张辅助表。

```
stock_kline_daily     股票 日 K
stock_kline_weekly    股票 周 K
stock_kline_monthly   股票 月 K
etf_kline_daily       ETF 日 K
etf_kline_weekly      ETF 周 K
etf_kline_monthly     ETF 月 K
adjust_factor         复权因子（辅助）
security_basic        证券基本信息（辅助）
```

## 4. K 线表结构（6 张）

### 4.1 股票日 K `stock_kline_daily`

| 列名 | 类型 | 说明 |
|------|------|------|
| `date` | `TEXT` | 交易日 `YYYY-MM-DD` |
| `code` | `TEXT` | 带交易所前缀代码，如 `sh.600000` |
| `open` | `REAL` | 开盘价 |
| `high` | `REAL` | 最高价 |
| `low` | `REAL` | 最低价 |
| `close` | `REAL` | 收盘价 |
| `preclose` | `REAL` | 前收盘价 |
| `volume` | `REAL` | 成交量（股） |
| `amount` | `REAL` | 成交额（元） |
| `adjustflag` | `TEXT` | 复权方式，`'2'` 前复权 / `'3'` 不复权 |
| `turn` | `REAL` | 换手率（%） |
| `tradestatus` | `TEXT` | 交易状态，`'1'` 正常交易 |
| `pctChg` | `REAL` | 涨跌幅（%） |
| `isST` | `TEXT` | 是否 ST，`'1'` 是 / `'0'` 否 |

```sql
CREATE TABLE IF NOT EXISTS stock_kline_daily (
    date        TEXT NOT NULL,
    code        TEXT NOT NULL,
    open        REAL,
    high        REAL,
    low         REAL,
    close       REAL,
    preclose    REAL,
    volume      REAL,
    amount      REAL,
    adjustflag  TEXT NOT NULL CHECK (adjustflag IN ('2', '3')),
    turn        REAL,
    tradestatus TEXT,
    pctChg      REAL,
    isST        TEXT,
    PRIMARY KEY (code, date, adjustflag)
);
CREATE INDEX IF NOT EXISTS idx_stock_daily_date ON stock_kline_daily(date);
CREATE INDEX IF NOT EXISTS idx_stock_daily_codedate ON stock_kline_daily(code, date);
```

### 4.2 股票周 K `stock_kline_weekly`

BaoStock 周 K **不返回** `preclose`、`tradestatus`、`isST`，故省略这三列：

```sql
CREATE TABLE IF NOT EXISTS stock_kline_weekly (
    date        TEXT NOT NULL,
    code        TEXT NOT NULL,
    open        REAL,
    high        REAL,
    low         REAL,
    close       REAL,
    volume      REAL,
    amount      REAL,
    adjustflag  TEXT NOT NULL CHECK (adjustflag IN ('2', '3')),
    turn        REAL,
    pctChg      REAL,
    PRIMARY KEY (code, date, adjustflag)
);
CREATE INDEX IF NOT EXISTS idx_stock_weekly_date ON stock_kline_weekly(date);
CREATE INDEX IF NOT EXISTS idx_stock_weekly_codedate ON stock_kline_weekly(code, date);
```

### 4.3 股票月 K `stock_kline_monthly`

```sql
CREATE TABLE IF NOT EXISTS stock_kline_monthly (
    date        TEXT NOT NULL,
    code        TEXT NOT NULL,
    open        REAL,
    high        REAL,
    low         REAL,
    close       REAL,
    volume      REAL,
    amount      REAL,
    adjustflag  TEXT NOT NULL CHECK (adjustflag IN ('2', '3')),
    turn        REAL,
    pctChg      REAL,
    PRIMARY KEY (code, date, adjustflag)
);
CREATE INDEX IF NOT EXISTS idx_stock_monthly_date ON stock_kline_monthly(date);
CREATE INDEX IF NOT EXISTS idx_stock_monthly_codedate ON stock_kline_monthly(code, date);
```

### 4.4 ETF 日 K `etf_kline_daily`

ETF 日 K 除标准字段外，BaoStock 还返回 **估值指标** `peTTM`、`pbMRQ`、`psTTM`、`pcfNcfTTM`（对多数 ETF 为空字符串）：

```sql
CREATE TABLE IF NOT EXISTS etf_kline_daily (
    date        TEXT NOT NULL,
    code        TEXT NOT NULL,
    open        REAL,
    high        REAL,
    low         REAL,
    close       REAL,
    preclose    REAL,
    volume      REAL,
    amount      REAL,
    adjustflag  TEXT NOT NULL CHECK (adjustflag IN ('2', '3')),
    turn        REAL,
    tradestatus TEXT,
    pctChg      REAL,
    isST        TEXT,
    peTTM       REAL,
    pbMRQ       REAL,
    psTTM       REAL,
    pcfNcfTTM   REAL,
    PRIMARY KEY (code, date, adjustflag)
);
CREATE INDEX IF NOT EXISTS idx_etf_daily_date ON etf_kline_daily(date);
CREATE INDEX IF NOT EXISTS idx_etf_daily_codedate ON etf_kline_daily(code, date);
```

### 4.5 ETF 周 K `etf_kline_weekly`

```sql
CREATE TABLE IF NOT EXISTS etf_kline_weekly (
    date        TEXT NOT NULL,
    code        TEXT NOT NULL,
    open        REAL,
    high        REAL,
    low         REAL,
    close       REAL,
    volume      REAL,
    amount      REAL,
    adjustflag  TEXT NOT NULL CHECK (adjustflag IN ('2', '3')),
    turn        REAL,
    pctChg      REAL,
    PRIMARY KEY (code, date, adjustflag)
);
CREATE INDEX IF NOT EXISTS idx_etf_weekly_date ON etf_kline_weekly(date);
CREATE INDEX IF NOT EXISTS idx_etf_weekly_codedate ON etf_kline_weekly(code, date);
```

### 4.6 ETF 月 K `etf_kline_monthly`

```sql
CREATE TABLE IF NOT EXISTS etf_kline_monthly (
    date        TEXT NOT NULL,
    code        TEXT NOT NULL,
    open        REAL,
    high        REAL,
    low         REAL,
    close       REAL,
    volume      REAL,
    amount      REAL,
    adjustflag  TEXT NOT NULL CHECK (adjustflag IN ('2', '3')),
    turn        REAL,
    pctChg      REAL,
    PRIMARY KEY (code, date, adjustflag)
);
CREATE INDEX IF NOT EXISTS idx_etf_monthly_date ON etf_kline_monthly(date);
CREATE INDEX IF NOT EXISTS idx_etf_monthly_codedate ON etf_kline_monthly(code, date);
```

## 5. 辅助表

### 5.1 复权因子 `adjust_factor`

存储 `query_adjust_factor` 返回的复权因子，用于在"不复权原始价"基础上现算前/后复权价。当某股发生新除权导致前复权历史价漂移时，用它低成本重算：

```sql
CREATE TABLE IF NOT EXISTS adjust_factor (
    code             TEXT NOT NULL,
    date             TEXT NOT NULL,   -- 除权日期
    foreAdjustFactor REAL,            -- 前复权因子
    backAdjustFactor REAL,            -- 后复权因子
    PRIMARY KEY (code, date)
);
```

> 因子实际含义请以 BaoStock 返回为准（不同 `query_adjust_factor` 调用口径可能返回前复权/后复权因子之一）。重算前复权价的基本思路：`前复权价 ≈ 原始价 × 前复权因子`，具体公式按 BaoStock 文档核对。

### 5.2 证券基本信息 `security_basic`

记录股票 / ETF 的元数据，与 K 线表通过 `code` 关联：

```sql
CREATE TABLE IF NOT EXISTS security_basic (
    code     TEXT PRIMARY KEY,   -- 如 sh.600000 / sh.510010
    code_name TEXT,              -- 证券名称
    type      TEXT,              -- 证券类型（股票/指数/ETF 等）
    ipoDate   TEXT,              -- 上市日期 YYYY-MM-DD
    outDate   TEXT,              -- 退市日期（在上市为空）
    status    TEXT               -- 上市状态
);
```

## 6. 常用查询示例

```sql
-- 某只股票的前复权日 K（最近 N 天）
SELECT date, open, high, low, close, volume, amount, pctChg
FROM stock_kline_daily
WHERE code = 'sh.600000' AND adjustflag = '2'
ORDER BY date DESC
LIMIT 100;

-- 全市场某交易日所有股票的未复权收盘
SELECT code, close
FROM stock_kline_daily
WHERE date = '2024-01-05' AND adjustflag = '3';

-- 某只 ETF 前复权月 K 全量
SELECT date, open, high, low, close, volume, amount
FROM etf_kline_monthly
WHERE code = 'sh.510010' AND adjustflag = '2'
ORDER BY date;

-- 幂等写入一条日 K（重复则覆盖）
INSERT OR REPLACE INTO stock_kline_daily
  (date, code, open, high, low, close, preclose, volume, amount,
   adjustflag, turn, tradestatus, pctChg, isST)
VALUES
  ('2024-01-05', 'sh.600000', 6.65, 6.67, 6.55, 6.62, 6.64, 28885978, 0,
   '2', 0.0752, '1', -0.3021, '0');
```

## 7. 写入流程建议

1. `login()` → 遍历标的列表（`security_basic` 或 `query_all_stock`）。
2. 对每个标的按 日/周/月 和 前复权(`adjustflag='2'`)/不复权(`'3'`) 分别调用 `query_history_k_data_plus`。
3. 将返回 `data` 中的 `str` 数值转 `float`，空串转 `NULL`，`INSERT OR REPLACE` 入库。
4. `commit()` 后可对 `UNIQUE(code, date, adjustflag)` 冲突做 `INSERT OR IGNORE` 增量更新。
5. 结束后 `logout()`。
