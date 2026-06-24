# backend/tests/test_nl2sql_limits.py
"""NL2SQL 行数限制 (TOP 注入) + chart spec 工具的单元测试。"""

import pytest
from app.agents.tools import (
    _ensure_top_limit,
    _cache_thread_data,
    _get_thread_data,
    reset_tool_state,
    _thread_last_data,
)


# ─────────────────────────────────────────────────────────
# _ensure_top_limit
# ─────────────────────────────────────────────────────────


class TestEnsureTopLimit:
    def test_inject_when_no_top(self):
        assert _ensure_top_limit("SELECT [a] FROM [t]", 100) == "SELECT TOP 100 [a] FROM [t]"

    def test_keep_when_top_within_limit(self):
        assert _ensure_top_limit("SELECT TOP 10 [a] FROM [t]", 100) == "SELECT TOP 10 [a] FROM [t]"

    def test_clamp_when_top_exceeds_limit(self):
        assert _ensure_top_limit("SELECT TOP 500 [a] FROM [t]", 100) == "SELECT TOP 100 [a] FROM [t]"

    def test_distinct_keyword(self):
        assert _ensure_top_limit("SELECT DISTINCT [a] FROM [t]", 50) == "SELECT DISTINCT TOP 50 [a] FROM [t]"

    def test_lowercase_sql(self):
        assert _ensure_top_limit("select top 200 [a] from [t]", 50) == "select top 50 [a] from [t]"

    def test_leading_whitespace(self):
        assert _ensure_top_limit("  SELECT [a] FROM [t]", 50) == "  SELECT TOP 50 [a] FROM [t]"

    def test_top_equal_to_limit(self):
        """TOP N == max_rows 应保留不动。"""
        assert _ensure_top_limit("SELECT TOP 100 [a] FROM [t]", 100) == "SELECT TOP 100 [a] FROM [t]"

    def test_complex_select_with_join(self):
        """复杂 SELECT 也能注入。"""
        sql = "SELECT [a], [b] FROM [t1] JOIN [t2] ON [t1].id = [t2].id"
        got = _ensure_top_limit(sql, 100)
        assert got.startswith("SELECT TOP 100 ")
        assert "JOIN" in got


# ─────────────────────────────────────────────────────────
# Thread data 缓存(供 make_chart 使用)
# ─────────────────────────────────────────────────────────


class TestThreadCache:
    def setup_method(self):
        # 每个测试前清空
        _thread_last_data.clear()

    def test_cache_and_retrieve(self):
        data = [{"a": 1}, {"a": 2}]
        cols = [{"name": "a", "type": "numeric"}]
        _cache_thread_data("tid1", data, cols)

        got = _get_thread_data("tid1")
        assert got is not None
        assert got["data"] == data
        assert got["columns"] == cols

    def test_unknown_thread(self):
        assert _get_thread_data("nonexistent") is None

    def test_none_thread_id_noop(self):
        """thread_id=None 时不应缓存(不报错)。"""
        _cache_thread_data(None, [{"a": 1}], [{"name": "a", "type": "numeric"}])
        assert _get_thread_data(None) is None

    def test_lru_eviction(self):
        """超过 20 个 thread 时按插入顺序淘汰。"""
        for i in range(25):
            _cache_thread_data(f"t{i}", [{"x": i}], [{"name": "x", "type": "numeric"}])
        # 应只保留最后 20 个
        assert len(_thread_last_data) == 20
        # 最早的几个应被淘汰
        assert _get_thread_data("t0") is None
        assert _get_thread_data("t4") is None
        # 最近的还在
        assert _get_thread_data("t24") is not None

    def test_update_moves_to_end(self):
        """更新已存在的 thread 应刷新位置(不被淘汰)。"""
        for i in range(5):
            _cache_thread_data(f"t{i}", [{"v": i}], [{"name": "v", "type": "numeric"}])
        # 重新写 t0
        _cache_thread_data("t0", [{"v": 100}], [{"name": "v", "type": "numeric"}])
        # 再写 19 个，把 t1..t4 挤掉
        for i in range(19):
            _cache_thread_data(f"new{i}", [{"v": i}], [{"name": "v", "type": "numeric"}])
        # t0 应仍在（因为重写过）
        assert _get_thread_data("t0") is not None
        assert _get_thread_data("t0")["data"] == [{"v": 100}]


# ─────────────────────────────────────────────────────────
# reset_tool_state
# ─────────────────────────────────────────────────────────


def test_reset_tool_state_sets_thread_id():
    from app.agents import tools as tools_mod
    reset_tool_state("my-thread")
    assert tools_mod._current_thread_id == "my-thread"
    assert tools_mod._current_sources == []
    assert tools_mod._current_kg_minigraph is None


def test_reset_tool_state_none():
    from app.agents import tools as tools_mod
    reset_tool_state(None)
    assert tools_mod._current_thread_id is None
