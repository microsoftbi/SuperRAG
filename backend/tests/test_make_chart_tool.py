# backend/tests/test_make_chart_tool.py
"""make_chart 工具的端到端单元测试。

策略：直接调用 build_nl2sql_tools() 得到工具列表，
取出 make_chart 工具，预置 thread 缓存数据后调用其 .invoke()，
验证 _current_sources 里收集到的 chart spec。
"""

import json
import pytest

from app.agents import tools as tools_mod
from app.agents.tools import (
    build_nl2sql_tools,
    reset_tool_state,
    _cache_thread_data,
    get_collected_sources,
)


THREAD_ID = "test-thread"


@pytest.fixture
def make_chart_tool():
    """从 build_nl2sql_tools 取出 make_chart 工具。"""
    tools = build_nl2sql_tools()
    by_name = {t.name: t for t in tools}
    return by_name["make_chart"]


@pytest.fixture
def preload_data():
    """预置一组销售数据,模拟刚执行完 query_database。"""
    reset_tool_state(THREAD_ID)
    data = [
        {"区域": "华东", "销售额": 1000, "客户数": 50},
        {"区域": "华南", "销售额": 800, "客户数": 35},
        {"区域": "华北", "销售额": 600, "客户数": 28},
    ]
    cols = [
        {"name": "区域", "type": "text"},
        {"name": "销售额", "type": "numeric"},
        {"name": "客户数", "type": "numeric"},
    ]
    _cache_thread_data(THREAD_ID, data, cols)
    return data, cols


def _get_chart_specs():
    return [s["spec"] for s in get_collected_sources() if s.get("type") == "chart"]


# ─────────────────────────────────────────────────────────
# 正常路径
# ─────────────────────────────────────────────────────────


def test_make_chart_bar(make_chart_tool, preload_data):
    result = make_chart_tool.invoke({
        "chart_type": "bar",
        "x_field": "区域",
        "y_fields": "销售额",
        "title": "各区域销售",
    })
    assert "已生成图表" in result

    specs = _get_chart_specs()
    assert len(specs) == 1
    spec = specs[0]
    assert spec["type"] == "bar"
    assert spec["title"] == "各区域销售"
    assert spec["x"] == "区域"
    assert spec["y"] == ["销售额"]
    assert len(spec["data"]) == 3


def test_make_chart_multiple_y(make_chart_tool, preload_data):
    """多个 Y 字段(柱图)应保留全部。"""
    make_chart_tool.invoke({
        "chart_type": "stacked_bar",
        "x_field": "区域",
        "y_fields": "销售额, 客户数",  # 逗号分隔
    })
    spec = _get_chart_specs()[0]
    assert spec["y"] == ["销售额", "客户数"]
    assert spec["type"] == "stacked_bar"


def test_make_chart_pie_single_y_only(make_chart_tool, preload_data):
    """饼图传多个 Y 字段时,只保留第一个。"""
    make_chart_tool.invoke({
        "chart_type": "pie",
        "x_field": "区域",
        "y_fields": "销售额,客户数",
    })
    spec = _get_chart_specs()[0]
    assert spec["type"] == "pie"
    assert spec["y"] == ["销售额"]


def test_make_chart_default_title(make_chart_tool, preload_data):
    """不传 title 时应自动生成。"""
    make_chart_tool.invoke({
        "chart_type": "bar",
        "x_field": "区域",
        "y_fields": "销售额",
    })
    spec = _get_chart_specs()[0]
    assert "销售额" in spec["title"] and "区域" in spec["title"]


# ─────────────────────────────────────────────────────────
# 校验失败
# ─────────────────────────────────────────────────────────


def test_make_chart_no_data():
    """没有缓存数据 → 返回警告。"""
    reset_tool_state("empty-thread")
    tools = build_nl2sql_tools()
    chart = next(t for t in tools if t.name == "make_chart")
    result = chart.invoke({
        "chart_type": "bar", "x_field": "x", "y_fields": "y",
    })
    assert "没有可用的查询结果" in result
    assert not _get_chart_specs()


def test_make_chart_invalid_type(make_chart_tool, preload_data):
    result = make_chart_tool.invoke({
        "chart_type": "unknown_type",
        "x_field": "区域", "y_fields": "销售额",
    })
    assert "不支持的图表类型" in result
    assert not _get_chart_specs()


def test_make_chart_invalid_x_field(make_chart_tool, preload_data):
    result = make_chart_tool.invoke({
        "chart_type": "bar",
        "x_field": "不存在的列", "y_fields": "销售额",
    })
    assert "不在结果列中" in result
    assert not _get_chart_specs()


def test_make_chart_invalid_y_field(make_chart_tool, preload_data):
    result = make_chart_tool.invoke({
        "chart_type": "bar",
        "x_field": "区域", "y_fields": "销售额, 不存在",
    })
    assert "不存在" in result
    assert not _get_chart_specs()


def test_make_chart_empty_y(make_chart_tool, preload_data):
    result = make_chart_tool.invoke({
        "chart_type": "bar",
        "x_field": "区域", "y_fields": "",
    })
    assert "不能为空" in result
    assert not _get_chart_specs()


# ─────────────────────────────────────────────────────────
# 数据序列化(Decimal/datetime 等)
# ─────────────────────────────────────────────────────────


def test_make_chart_spec_is_json_serializable(make_chart_tool):
    """chart spec 应该是纯 JSON 友好的(没有 Decimal/datetime 等)。"""
    from decimal import Decimal
    from datetime import datetime

    reset_tool_state(THREAD_ID)
    data = [
        {"日期": datetime(2026, 1, 1), "金额": Decimal("123.45")},
        {"日期": datetime(2026, 2, 1), "金额": Decimal("234.56")},
    ]
    cols = [
        {"name": "日期", "type": "text"},
        {"name": "金额", "type": "numeric"},
    ]
    _cache_thread_data(THREAD_ID, data, cols)

    make_chart_tool.invoke({
        "chart_type": "line", "x_field": "日期", "y_fields": "金额",
    })
    spec = _get_chart_specs()[0]
    # 应该能直接 json.dumps，不会抛 TypeError
    payload = json.dumps(spec, ensure_ascii=False)
    assert "123.45" in payload
    assert "2026" in payload
