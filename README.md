# BaoStock 调研 Demo

[BaoStock](http://baostock.com/) 是一个免费、开源的 Python 证券数据接口库，提供 A 股历史 K 线、证券基本信息、指数成分股、财务报表、宏观利率等数据。本仓库是一个调研 demo：`demo.py` 可运行，演示常用 API 及真实的返回值结构；本文件是配套的调研报告。

---

## 1. 安装与登录

```bash
pip install baostock
```

所有数据查询前必须调用 `login()`，结束使用后调用 `logout()`。默认是匿名登录：

```python
import baostock as bs

lg = bs.login()        # 默认参数 user_id='anonymous', password='123456'
print(lg.error_code)   # '0' 表示成功
print(lg.error_msg)    # 'success'
# ... 查询数据 ...
bs.logout()
```

---

## 2. 返回值结构（核心知识点）

BaoStock 的返回对象**统一**用下面这套属性，是所有 `query_*` 函数与 `login()/logout()` 的通用结构：

| 属性 | 类型 | 含义 |
|------|------|------|
| `error_code` | `str` | `'0'` 表示成功，非 `'0'` 表示失败 |
| `error_msg` | `str` | 错误信息描述，成功时为 `'success'` |
| `fields` | `list[str]` | 查询结果各列的字段名（**仅 query 类返回**） |
| `data` | `list[list[str]]` | 查询结果的行数据，**每行是一个由字符串组成的列表** |
| `rows` | `int` | 总行数（**仅 query 类返回**，属性存在但 `dir()` 不可见） |

> **注意点：** 所有数值在 `data` 里都是**字符串**（如 `'6.6300'`、`'22066700'`），需要自行转换类型。

---

## 3. 完整 API 目录

以下为 `baostock` 包的公开函数全集（含签名）。按功能分类：

### 3.1 连接类

| 函数 | 签名 | 说明 |
|------|------|------|
| `login` | `login(user_id='anonymous', password='123456')` | 登录，返回含 `error_code/error_msg` 的对象 |
| `logout` | `logout(user_id='anonymous')` | 登出 |
| `set_API_key` | `set_API_key(apiKey='')` | 设置 API key |

### 3.2 行情 / K 线（核心）

| 函数 | 签名 | 说明 |
|------|------|------|
| `query_history_k_data_plus` | `(code, fields, start_date=None, end_date=None, frequency='d', adjustflag='3')` | 历史 K 线，最常用 |
| `query_adjust_factor` | `(code, start_date=None, end_date=None)` | 复权因子 |
| `query_daily_adjust_factor` | `(date=None)` | 全市场每日复权因子 |
| `query_daily_history_k_AStock` | `(date='')` | 全 A 股某日行情 |
| `query_daily_history_k_ETF` | `(date='')` | ETF 某日行情 |

### 3.3 证券信息

| 函数 | 签名 | 说明 |
|------|------|------|
| `query_stock_basic` | `(code='', code_name='')` | 证券基本信息（名称、上市/退市日期、类型、状态） |
| `query_all_stock` | `(day=None)` | 指定日期可交易的全部股票 |
| `query_stock_industry` | `(code='', date='')` | 股票所属行业 |

### 3.4 指数成分股

| 函数 | 签名 | 说明 |
|------|------|------|
| `query_hs300_stocks` | `(date='')` | 沪深 300 成分股 |
| `query_sz50_stocks` | `(date='')` | 上证 50 成分股 |
| `query_zz500_stocks` | `(date='')` | 中证 500 成分股 |

### 3.5 财务数据（按季度）

| 函数 | 签名 | 说明 |
|------|------|------|
| `query_profit_data` | `(code, year=None, quarter=None)` | 利润表 |
| `query_operation_data` | `(code, year=None, quarter=None)` | 营运能力 |
| `query_growth_data` | `(code, year=None, quarter=None)` | 成长能力 |
| `query_balance_data` | `(code, year=None, quarter=None)` | 资产负债 |
| `query_cash_flow_data` | `(code, year=None, quarter=None)` | 现金流 |
| `query_dupont_data` | `(code, year=None, quarter=None)` | 杜邦分析 |

### 3.6 业绩报告与分红

| 函数 | 签名 | 说明 |
|------|------|------|
| `query_forecast_report` | `(code, start_date=None, end_date=None)` | 业绩预告 |
| `query_performance_express_report` | `(code, start_date=None, end_date=None)` | 业绩快报 |
| `query_dividend_data` | `(code, year=None, yearType='report')` | 分红送配 |

### 3.7 宏观利率

| 函数 | 签名 | 说明 |
|------|------|------|
| `query_deposit_rate_data` | `(start_date='', end_date='')` | 存款利率 |
| `query_loan_rate_data` | `(start_date='', end_date='')` | 贷款利率 |
| `query_money_supply_data_month` | `(start_date='', end_date='')` | 月度货币供应量 |
| `query_money_supply_data_year` | `(start_date='', end_date='')` | 年度货币供应量 |
| `query_required_reserve_ratio_data` | `(start_date='', end_date='', yearType='0')` | 存款准备金率 |

### 3.8 交易日历

| 函数 | 签名 | 说明 |
|------|------|------|
| `query_trade_dates` | `(start_date=None, end_date=None)` | 交易日历（含是否交易日标记） |

---

## 4. 各 API 返回值详解与真实输出

`demo.py` 的真实运行输出如下（跑于一次实际登录，返回均为 `error_code='0'`）：

### 4.1 `query_history_k_data_plus` — 历史 K 线

最核心的接口。`frequency` 可取 `'d'/'w'/'m'/'5'/'15'/'30'/'60'`（日/周/月/5 分钟…），`adjustflag` 为复权方式（`'1'` 后复权、`'2'` 前复权、`'3'` 不复权）。`fields` 自由指定列。

```text
[query_history_k_data_plus 日K线]
  fields = ['date', 'code', 'open', 'high', 'low', 'close', 'volume']
  rows   = 4
    ['2024-01-02', 'sh.600000', '6.6300', '6.6500', '6.6000', '6.6000', '22066700']
    ['2024-01-03', 'sh.600000', '6.5900', '6.6500', '6.5900', '6.6400', '18203654']
    ['2024-01-04', 'sh.600000', '6.6400', '6.6700', '6.5500', '6.6200', '28885978']
```

### 4.2 `query_stock_basic` — 证券基本信息

```text
[query_stock_basic 证券基本信息]
  fields = ['code', 'code_name', 'ipoDate', 'outDate', 'type', 'status']
  rows   = 1
    ['sh.600000', '浦发银行', '1999-11-10', '', '1', '1']
```

字段：`type` 股票类型、`status` 上市状态。浦发银行退市日期 `outDate` 为空（在上市）。

### 4.3 `query_hs300_stocks` — 沪深 300 成分股

```text
[query_hs300_stocks 沪深300成分]
  fields = ['updateDate', 'code', 'code_name']
  rows   = 300
    ['2024-01-01', 'sh.600000', '浦发银行']
    ['2024-01-01', 'sh.600009', '上海机场']
    ['2024-01-01', 'sh.600010', '包钢股份']
```

### 4.4 `query_profit_data` — 季度利润表

财务类接口都要传 `year` + `quarter`（1~4）。`netProfit` 为净利润，`epsTTM` 为滚动每股收益等。

```text
[query_profit_data 季度利润表]
  fields = ['code', 'pubDate', 'statDate', 'roeAvg', 'npMargin', 'gpMargin',
            'netProfit', 'epsTTM', 'MBRevenue', 'totalShare', 'liqaShare']
  rows   = 1
    ['sh.600000', '2024-04-30', '2023-12-31', '0.051598', '0.215811', '',
     '37429000000.000000', '1.250401', '329633000000.000000', '29352176848.00', '29352176848.00']
```

### 4.5 `query_forecast_report` — 业绩预告

**返回 0 行**也是一种真实结果（该股票在该区间无业绩预告记录），`error_code` 仍为 `'0'`，因此**判断成功与否要看 `error_code`，不要只看行数**：

```text
[query_forecast_report 业绩预告]
  fields = ['code', 'profitForcastExpPubDate', 'profitForcastExpStatDate',
            'profitForcastType', 'profitForcastAbstract',
            'profitForcastChgPctUp', 'profitForcastChgPctDwn']
  rows   = 0
```

### 4.6 `query_deposit_rate_data` — 存款利率（宏观）

```text
[query_deposit_rate_data 存款利率]
  fields = ['pubDate', 'demandDepositRate', 'fixedDepositRate3Month',
            'fixedDepositRate6Month', 'fixedDepositRate1Year', 'fixedDepositRate2Year',
            'fixedDepositRate3Year', 'fixedDepositRate5Year', 'installmentFixedDepositRate1Year',
            'installmentFixedDepositRate3Year', 'installmentFixedDepositRate5Year']
  rows   = 2
    ['2015-03-01', '0.350000', '2.100000', '2.300000', '2.500000', '3.100000',
     '3.750000', '', '2.100000', '2.300000', '']
    ['2015-05-11', '0.350000', '1.850000', '2.050000', '2.250000', '2.850000',
     '3.500000', '', '1.850000', '2.050000', '']
```

### 4.7 `query_trade_dates` — 交易日历

`is_trading_day` 字段为 `'1'` 表示交易日、`'0'` 表示非交易日：

```text
[query_trade_dates 交易日历]
  fields = ['calendar_date', 'is_trading_day']
  rows   = 10
    ['2024-01-01', '0']
    ['2024-01-02', '1']
    ['2024-01-03', '1']
```

---

## 5. 实践注意事项

1. **必须登录**：未 `login()` 就查询会失败。
2. **依赖网络**：数据来自 baostock 服务器，偶尔连接失败，重试即可。
3. **返回值为字符串**：数值字段需手动 `float()` / `int()` 转换。
4. **成功判断看 `error_code`**：`error_code == '0'` 才算成功，`rows == 0` 只是"该条件下无数据"，并非错误。
5. **时间格式**：日期用 `YYYY-MM-DD` 字符串；财务接口用 `year` + `quarter`。
6. **股票代码格式**：带交易所前缀，如 `sh.600000`（沪）、`sz.000001`（深）。
7. **`rows` 是隐藏属性**：通过 `rs.rows` 可访问，但不在 `dir(rs)` 中列出。

---

## 6. 数据更新与数据范围说明

### 6.1 每日最新数据更新时间

| 时间 | 入库数据 |
|------|----------|
| 当前交易日 17:30 | 完成日 K 线数据入库 |
| 当前交易日 18:00 | 完成复权因子数据入库 |
| 当前交易日 20:00 | 完成分钟 K 线数据入库 |
| 第二自然日 1:30 | 完成前交易日“其它财务报告数据”入库 |
| 周六 17:30 | 完成周 K 线数据入库 |
| 每月 1 号 17:30 | 完成上月月 K 线数据入库 |

**每周数据更新时间：**

- 每周一下午，完成上证 50 成份股、沪深 300 成份股、中证 500 成份股信息数据入库。

### 6.2 数据范围说明

**股票数据**

- 日、周、月 K 线数据，时间范围：1990-12-19 至今。
- 5、15、30、60 分钟 K 线数据，时间范围（近 5 年）：2020-01-03 至今。

**ETF 数据**

- 日、周、月 K 线数据，时间范围：2026-01-05 至今。
- 5、15、30、60 分钟 K 线数据，时间范围：2026-01-05 至今。

**指数数据**

- 日、周、月 K 线已经包含指数（不提供分钟 K 线数据）：综合指数，规模指数，一级行业指数，二级行业指数，策略指数，成长指数，价值指数，主题指数，基金指数，债券指数。
- 时间范围：2006-01-01 至今。

---

## 7. 快速开始

```bash
# 创建虚拟环境并安装
python3 -m venv .venv
.venv/bin/pip install baostock

# 运行 demo（真实联网取数）
.venv/bin/python demo.py
```
