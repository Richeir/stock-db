"""离线测试 demo.py —— mock baostock，验证 API 调用流程与输出，不依赖网络。"""
import demo


class FakeResult:
    """模拟 BaoStock 返回对象：error_code / error_msg / fields / data / rows。

    fields/data/rows 仅在显式传入时才设置，模拟 login 返回对象（无这些属性）。
    """

    def __init__(self, error_code="0", error_msg="success", fields=None, data=None, rows=None):
        self.error_code = error_code
        self.error_msg = error_msg
        if fields is not None:
            self.fields = fields
        if data is not None:
            self.data = data
        if rows is not None:
            self.rows = rows


class FakeLogin:
    """模拟 login() 返回对象（仅含 error_code / error_msg）。"""

    def __init__(self, error_code="0", error_msg="success"):
        self.error_code = error_code
        self.error_msg = error_msg


def _result_from_show(capsys, **kw):
    rs = FakeResult(**kw)
    demo.show("测试", rs, max_rows=1)
    return capsys.readouterr().out


def test_show_login_style_object(capsys):
    """无 fields/data 的对象（如 login 返回值）：只打印 error_code / error_msg。"""
    out = _result_from_show(capsys, error_code="0", error_msg="success")
    assert "error_code = '0'" in out
    assert "error_msg  = 'success'" in out
    assert "fields" not in out


def test_show_query_object_prints_fields_and_rows(capsys):
    """query 返回对象：打印 fields、rows 与前若干行数据。"""
    out = _result_from_show(capsys,
                            fields=["date", "code", "close"],
                            data=[["2024-01-02", "sh.600000", "6.6300"],
                                  ["2024-01-03", "sh.600000", "6.6500"]],
                            rows=2)
    assert "fields     = ['date', 'code', 'close']" in out
    assert "rows       = 2" in out
    assert "2024-01-02" in out
    assert "['2024-01-02', 'sh.600000', '6.6300']" in out


def test_show_limits_rows(capsys):
    """max_rows 限制打印行数，但 rows 显示完整总数。"""
    data = [[f"2024-01-0{i}", "sh.600000", "1"] for i in range(1, 6)]
    out = _result_from_show(capsys, fields=["date", "code", "x"], data=data, rows=5)
    assert "rows       = 5" in out
    assert data[0][0] in out   # 只打印第一行
    assert data[4][0] not in out  # 超出的行不打印


def test_main_success_path(monkeypatch, capsys):
    """main() 成功路径：登录成功后依次调用各 query_* 且传入正确参数，最终登出。"""
    called = []
    detail = []  # 记录 (函数名, 位置参数, 关键字参数)

    class FakeBS:
        def _r(self, name, *a, **kw):
            called.append(name)
            detail.append((name, a, kw))
            return FakeResult(fields=["date", "close"], data=[["2024-01-02", "6.63"]])

        def login(self):
            called.append("login")
            return FakeLogin()

        def logout(self):
            called.append("logout")

        def query_history_k_data_plus(self, *a, **kw):
            return self._r("query_history_k_data_plus", *a, **kw)

        def query_daily_history_k_ETF(self, **kw):
            return self._r("query_daily_history_k_ETF", **kw)

        def query_stock_basic(self, **kw):
            return self._r("query_stock_basic", **kw)

        def query_hs300_stocks(self, **kw):
            return self._r("query_hs300_stocks", **kw)

        def query_profit_data(self, **kw):
            return self._r("query_profit_data", **kw)

        def query_forecast_report(self, *a, **kw):
            return self._r("query_forecast_report", *a, **kw)

        def query_deposit_rate_data(self, **kw):
            return self._r("query_deposit_rate_data", **kw)

        def query_trade_dates(self, **kw):
            return self._r("query_trade_dates", **kw)

    monkeypatch.setattr(demo, "bs", FakeBS())
    demo.main()
    out = capsys.readouterr().out

    assert called == ["login"] + [
        "query_history_k_data_plus",
        "query_daily_history_k_ETF",
        "query_stock_basic",
        "query_hs300_stocks",
        "query_profit_data",
        "query_forecast_report",
        "query_deposit_rate_data",
        "query_trade_dates",
    ] + ["logout"]

    # 关键参数断言：K 线接口的 code / 字段 / 频率 / 复权方式
    name, args, kw = detail[0]
    assert name == "query_history_k_data_plus"
    assert args[0] == "sh.600000"
    assert "date,code,open,high,low,close,volume" in args[1]
    assert kw["start_date"] == "2024-01-02" and kw["end_date"] == "2024-01-05"
    assert kw["frequency"] == "d" and kw["adjustflag"] == "3"

    # ETF 日 K / 财务 / 宏观 / 交易日历的日期参数
    by_name = {n: kw for n, _, kw in detail}
    assert by_name["query_daily_history_k_ETF"]["date"] == "2026-02-04"
    assert by_name["query_profit_data"]["year"] == 2023
    assert by_name["query_profit_data"]["quarter"] == 4
    assert by_name["query_deposit_rate_data"]["start_date"] == "2015-01-01"
    assert by_name["query_trade_dates"]["start_date"] == "2024-01-01"

    assert "已登出" in out


def test_main_login_failure_returns_early(monkeypatch, capsys):
    """登录失败：打印失败信息，不调用任何 query_*（login 失败前即 return，故不登出）。"""
    called = []

    class FakeBS:
        def login(self):
            called.append("login")
            return FakeLogin(error_code="-1", error_msg="登录失败")

        def logout(self):
            called.append("logout")

    monkeypatch.setattr(demo, "bs", FakeBS())
    demo.main()
    out = capsys.readouterr().out

    assert called == ["login"]  # 登录失败在 try/finally 之前 return，不登出
    assert "登录失败" in out
    assert "query_" not in out
