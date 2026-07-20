"""
TripCraft Harness 容错执行引擎测试
"""

from __future__ import annotations

import asyncio

import pytest

from app.services.harness import (
    CircuitBreaker,
    CircuitState,
    ExecutorConfig,
    ToolExecutor,
    ToolResult,
    ToolStatus,
)


# ==========================================================================
# 1. ToolResult Schema
# ==========================================================================

class TestToolResult:
    def test_success_status(self):
        r = ToolResult(status=ToolStatus.SUCCESS, data="ok")
        assert r.success is True

    def test_fallback_status(self):
        r = ToolResult(status=ToolStatus.FALLBACK, data="fallback_data")
        assert r.success is True

    def test_error_status(self):
        r = ToolResult(status=ToolStatus.ERROR, error="failed")
        assert r.success is False

    def test_timeout_status(self):
        r = ToolResult(status=ToolStatus.TIMEOUT, error="timeout")
        assert r.success is False

    def test_to_dict(self):
        r = ToolResult(status=ToolStatus.SUCCESS, data=[1, 2], duration_ms=12.5, attempts=2)
        d = r.to_dict()
        assert d["status"] == "success"
        assert d["data"] == [1, 2]
        assert d["attempts"] == 2


# ==========================================================================
# 2. 熔断器
# ==========================================================================

class TestCircuitBreaker:
    def test_initial_state_closed(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.can_execute() is False

    def test_half_open_after_recovery_timeout(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.01)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        # 等待恢复超时
        import time
        time.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.can_execute() is True

    def test_closes_after_successes_in_half_open(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01, success_threshold=2)
        cb.record_failure()
        import time
        time.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.HALF_OPEN  # 还需要一次
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_reopens_on_failure_in_half_open(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
        cb.record_failure()
        import time
        time.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_success_resets_failure_count(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb._consecutive_failures == 0
        assert cb.state == CircuitState.CLOSED


# ==========================================================================
# 3. ToolExecutor — 成功场景
# ==========================================================================

class TestToolExecutorSuccess:
    @pytest.mark.asyncio
    async def test_successful_call(self):
        async def add(a, b):
            return a + b

        executor = ToolExecutor()
        result = await executor.execute(add, 2, 3, tool_name="add")

        assert result.status == ToolStatus.SUCCESS
        assert result.data == 5
        assert result.attempts == 1
        assert result.source == "primary"

    @pytest.mark.asyncio
    async def test_success_after_retry(self):
        call_count = 0

        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RuntimeError("transient error")
            return "ok"

        executor = ToolExecutor(ExecutorConfig(max_retries=3, base_backoff_seconds=0.01))
        result = await executor.execute(flaky, tool_name="flaky")

        assert result.status == ToolStatus.SUCCESS
        assert result.data == "ok"
        assert result.attempts == 2


# ==========================================================================
# 4. ToolExecutor — 降级场景
# ==========================================================================

class TestToolExecutorFallback:
    @pytest.mark.asyncio
    async def test_fallback_on_failure(self):
        async def always_fail():
            raise RuntimeError("API down")

        executor = ToolExecutor(ExecutorConfig(max_retries=1, base_backoff_seconds=0.01))
        result = await executor.execute(
            always_fail,
            fallback=lambda: "fallback_data",
            tool_name="failing_api",
        )

        assert result.status == ToolStatus.FALLBACK
        assert result.data == "fallback_data"
        assert result.source == "fallback"

    @pytest.mark.asyncio
    async def test_fallback_on_timeout(self):
        async def slow():
            await asyncio.sleep(10)
            return "never"

        executor = ToolExecutor(ExecutorConfig(timeout_seconds=0.05, max_retries=0))
        result = await executor.execute(
            slow,
            fallback=lambda: "fast_fallback",
            tool_name="slow_api",
        )

        assert result.status == ToolStatus.FALLBACK
        assert result.data == "fast_fallback"

    @pytest.mark.asyncio
    async def test_error_when_no_fallback(self):
        async def always_fail():
            raise RuntimeError("API down")

        executor = ToolExecutor(ExecutorConfig(max_retries=1, base_backoff_seconds=0.01))
        result = await executor.execute(always_fail, tool_name="no_fallback")

        assert result.status == ToolStatus.ERROR
        assert result.error is not None
        assert result.success is False


# ==========================================================================
# 5. ToolExecutor — 熔断器集成
# ==========================================================================

class TestToolExecutorCircuitBreaker:
    @pytest.mark.asyncio
    async def test_circuit_opens_after_failures(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=10.0)
        executor = ToolExecutor(ExecutorConfig(max_retries=1, base_backoff_seconds=0.01, circuit_breaker=cb))

        async def fail():
            raise RuntimeError("down")

        # 第一次调用 → 失败，熔断器记录 (1/2)
        r1 = await executor.execute(fail, tool_name="cb_test")
        assert r1.status == ToolStatus.ERROR

        # 第二次调用 → 失败，熔断器断开 (2/2)
        r2 = await executor.execute(fail, tool_name="cb_test")
        assert r2.status == ToolStatus.ERROR
        assert cb.state == CircuitState.OPEN

        # 第三次调用 → 熔断器断开，走 fallback
        r3 = await executor.execute(fail, fallback=lambda: "fb", tool_name="cb_test")
        assert r3.status == ToolStatus.FALLBACK
        assert r3.data == "fb"  # fallback 被执行

        # 无 fallback 时 → CIRCUIT_OPEN
        r4 = await executor.execute(fail, tool_name="cb_test")
        assert r4.status == ToolStatus.CIRCUIT_OPEN


# ==========================================================================
# 6. 指数退避
# ==========================================================================

class TestExponentialBackoff:
    @pytest.mark.asyncio
    async def test_backoff_timing(self):
        """验证重试间有退避延迟"""
        call_times: list[float] = []

        async def track_calls():
            call_times.append(asyncio.get_event_loop().time())
            raise RuntimeError("fail")

        executor = ToolExecutor(ExecutorConfig(
            max_retries=3,
            base_backoff_seconds=0.05,
            backoff_multiplier=2.0,
        ))
        await executor.execute(track_calls, tool_name="timing")

        assert len(call_times) == 3
        # 第一次和第二次之间 ~0.05s
        gap1 = call_times[1] - call_times[0]
        # 第二次和第三次之间 ~0.10s
        gap2 = call_times[2] - call_times[1]
        assert gap1 >= 0.04  # 允许少量误差
        assert gap2 >= 0.08
        assert gap2 > gap1  # 指数增长
