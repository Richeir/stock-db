# AGENTS.md — BaoStock Demo 项目约定

本文件是 Pi 的上下文文件，启动时会自动加载，帮助后续所有会话遵循本项目约定。

## 项目概览

一个 BaoStock（Python 免费证券数据接口库）调研 demo：

- `demo.py` — 可运行的示例脚本，登录后按类别查询数据并打印返回值。
- `README.md` — 调研报告，含完整 API 目录、返回值结构、真实输出示例。

## 常用命令

```bash
# 运行 demo（需要联网，会真实登录 BaoStock）
.venv/bin/python demo.py

# 安装依赖
.venv/bin/pip install baostock
```

## 环境约定

- 使用项目内虚拟环境，**必须用 `.venv/bin/python`**（不是系统 `python3`）。
- Python 版本：3.11（`.venv/bin/python`）。
- `.venv/`、`__pycache__/` 已在 `.gitignore` 中排除，不要提交。

## BaoStock 关键知识点（编码/文档时务必遵循）

- **必须登录**：任何 `query_*` 前要先 `bs.login()`，结束 `bs.logout()`。默认匿名登录。
- **返回值统一结构**：所有查询对象含 `error_code`（`'0'`=成功）、`error_msg`、`fields`（列名列表）、`data`（行列表）。
- **`rows` 是隐藏属性**：`rs.rows` 可访问但不在 `dir(rs)` 中。
- **返回值为字符串**：`data` 里的数值（如 `'6.6300'`）都是 `str`，需要时手动 `float()`/`int()` 转换。
- **成功看 `error_code`，不看行数**：`rows == 0` 只是该条件下无数据，不是错误。
- **股票代码带交易所前缀**：如 `sh.600000`（沪）、`sz.000001`（深）。
- **日期格式**：`YYYY-MM-DD` 字符串；财务接口用 `year` + `quarter`（1~4）。
- **依赖网络**：数据来自远程服务器，可能偶发连接失败，脚本应做容错。

## 沟通偏好

- 使用简体中文回复用户；代码、命令、文件名、API 名称保留英文原文。
