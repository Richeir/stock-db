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
    """main() 成功路径：登录成功后依次调用各 query_*，最终登出。"""
    called = []

    class FakeBS:
        def login(self):
            called.append("login")
            return FakeLogin()

        def logout(self):
            called.append("logout")

        def query_history_k_data_plus(self, *a, **kw):
            called.append("query_history_k_data_plus")
            return FakeResult(fields=["date", "close"], data=[["2024-01-02", "6.63"]])

        def query_daily_history_k_ETF(self, **kw):
            called.append("query_daily_history_k_ETF")
            return FakeResult(fields=["code"], data=[["sh.510010"]])

        def query_stock_basic(self, **kw):
            called.append("query_stock_basic")
            return FakeResult(fields=["code"], data=[["sh.600000"]])

        def query_hs300_stocks(self, **kw):
            called.append("query_hs300_stocks")
            return FakeResult(fields=["code"], data=[])

        def query_profit_data(self, **kw):
            called.append("query_profit_data")
            return FakeResult(fields=["code"], data=[])

        def query_forecast_report(self, *a, **kw):
            called.append("query_forecast_report")
            return FakeResult(fields=["code"], data=[])

        def query_deposit_rate_data(self, **kw):
            called.append("query_deposit_rate_data")
            return FakeResult(fields=["code"], data=[])

        def query_trade_dates(self, **kw):
            called.append("query_trade_dates")
            return FakeResult(fields=["code"], data=[])

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
    assert "已登出" in out


def test_main_login_failure_returns_early(monkeypatch, capsys):
    """登录失败：打印失败信息，不调用任何 query_*，并登出。"""
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
