"""
TripCraft Harness 容错执行引擎

统一工具执行框架：
- 可配置超时控制
- 指数退避重试（max 3 次）
- 熔断器（连续失败 N 次后半开恢复）
- 显式 ToolResult Schema（success/error/fallback/timeout 状态机）
- 分级降级：LLM 失败→模板引擎；API 超时→本地兜底数据；单 Agent 异常隔离
"""

from __future__ import annotations

import asyncio
import enum
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

from app.services.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# ToolResult Schema
# ---------------------------------------------------------------------------

class ToolStatus(enum.Enum):
    """工具执行状态机"""
    SUCCESS = "success"
    ERROR = "error"
    FALLBACK = "fallback"
    TIMEOUT = "timeout"
    CIRCUIT_OPEN = "circuit_open"  # 熔断器断开


@dataclass
class ToolResult:
    """统一的工具执行结果 Schema"""
    status: ToolStatus
    data: Any = None
    error: str | None = None
    duration_ms: float = 0.0
    attempts: int = 1
    source: str = "primary"  # primary / fallback / cache

    @property
    def success(self) -> bool:
        return self.status in (ToolStatus.SUCCESS, ToolStatus.FALLBACK)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "data": self.data,
            "error": self.error,
            "duration_ms": round(self.duration_ms, 2),
            "attempts": self.attempts,
            "source": self.source,
        }


# ---------------------------------------------------------------------------
# 熔断器 (Circuit Breaker)
# ---------------------------------------------------------------------------

class CircuitState(enum.Enum):
    CLOSED = "closed"       # 正常
    OPEN = "open"           # 断开（拒绝请求）
    HALF_OPEN = "half_open" # 半开（尝试恢复）


@dataclass
class CircuitBreaker:
    """熔断器实现"""
    failure_threshold: int = 5        # 连续失败次数触发断开
    recovery_timeout: float = 30.0    # 断开后半开等待时间（秒）
    success_threshold: int = 2        # 半开状态连续成功次数恢复闭合

    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _consecutive_failures: int = field(default=0, init=False)
    _consecutive_successes: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0.0, init=False)

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            # 检查是否到了半开时间
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._consecutive_successes = 0
        return self._state

    def record_success(self) -> None:
        """记录一次成功"""
        if self._state == CircuitState.HALF_OPEN:
            self._consecutive_successes += 1
            if self._consecutive_successes >= self.success_threshold:
                self._state = CircuitState.CLOSED
                self._consecutive_failures = 0
        else:
            self._consecutive_failures = 0

    def record_failure(self) -> None:
        """记录一次失败"""
        self._consecutive_failures += 1
        self._last_failure_time = time.time()
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            self._consecutive_successes = 0
        elif self._consecutive_failures >= self.failure_threshold:
            self._state = CircuitState.OPEN

    def can_execute(self) -> bool:
        """是否允许执行"""
        return self.state != CircuitState.OPEN


# ---------------------------------------------------------------------------
# ToolExecutor — 统一执行入口
# ---------------------------------------------------------------------------

@dataclass
class ExecutorConfig:
    """执行器配置"""
    timeout_seconds: float = 15.0
    max_retries: int = 3
    base_backoff_seconds: float = 1.0
    backoff_multiplier: float = 2.0
    circuit_breaker: CircuitBreaker | None = None


class ToolExecutor:
    """统一工具执行框架

    特性：
    - 可配置超时
    - 指数退避重试
    - 熔断器保护
    - 自动降级到 fallback 函数
    - 显式 ToolResult 状态机
    """

    def __init__(self, config: ExecutorConfig | None = None):
        self.config = config or ExecutorConfig()

    async def execute(
        self,
        func: Callable[..., Coroutine[Any, Any, Any]],
        *args: Any,
        fallback: Callable[..., Coroutine[Any, Any, Any]] | Callable[[], Any] | None = None,
        fallback_args: tuple[Any, ...] | None = None,
        tool_name: str = "unknown",
        **kwargs: Any,
    ) -> ToolResult:
        """统一执行入口

        Args:
            func: 主执行函数
            fallback: 降级函数
            fallback_args: 降级函数参数
            tool_name: 工具名称（用于日志）

        Returns:
            ToolResult
        """
        start = time.perf_counter()

        # 熔断器检查
        if self.config.circuit_breaker and not self.config.circuit_breaker.can_execute():
            logger.warning(f"[{tool_name}] Circuit breaker OPEN, skipping")
            duration = (time.perf_counter() - start) * 1000
            # 尝试降级
            if fallback:
                return await self._run_fallback(fallback, fallback_args, duration, ToolStatus.CIRCUIT_OPEN, tool_name)
            return ToolResult(
                status=ToolStatus.CIRCUIT_OPEN,
                error="Circuit breaker is open",
                duration_ms=duration,
                source="circuit_breaker",
            )

        last_error: str | None = None

        for attempt in range(1, self.config.max_retries + 1):
            try:
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.config.timeout_seconds,
                )
                duration = (time.perf_counter() - start) * 1000

                if self.config.circuit_breaker:
                    self.config.circuit_breaker.record_success()

                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=result,
                    duration_ms=duration,
                    attempts=attempt,
                    source="primary",
                )

            except asyncio.TimeoutError:
                last_error = f"Timeout after {self.config.timeout_seconds}s (attempt {attempt})"
                logger.warning(f"[{tool_name}] Attempt {attempt} timed out")
                if self.config.circuit_breaker:
                    self.config.circuit_breaker.record_failure()

            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                logger.warning(f"[{tool_name}] Attempt {attempt} failed: {last_error}")
                if self.config.circuit_breaker:
                    self.config.circuit_breaker.record_failure()

            # 指数退避（最后一次不等待）
            if attempt < self.config.max_retries:
                backoff = self.config.base_backoff_seconds * (self.config.backoff_multiplier ** (attempt - 1))
                await asyncio.sleep(backoff)

        # 全部重试失败 → 降级
        duration = (time.perf_counter() - start) * 1000
        if fallback:
            return await self._run_fallback(fallback, fallback_args, duration, ToolStatus.FALLBACK, tool_name)

        return ToolResult(
            status=ToolStatus.ERROR,
            error=f"All {self.config.max_retries} attempts failed. Last: {last_error}",
            duration_ms=duration,
            attempts=self.config.max_retries,
            source="failed",
        )

    async def _run_fallback(
        self,
        fallback: Callable[..., Coroutine[Any, Any, Any]] | Callable[[], Any],
        fallback_args: tuple[Any, ...] | None,
        duration: float,
        reason: ToolStatus,
        tool_name: str,
    ) -> ToolResult:
        """执行降级逻辑"""
        try:
            if asyncio.iscoroutinefunction(fallback):
                if fallback_args:
                    data = await fallback(*fallback_args)
                else:
                    data = await fallback()
            else:
                if fallback_args:
                    data = fallback(*fallback_args)
                else:
                    data = fallback()

            return ToolResult(
                status=ToolStatus.FALLBACK,
                data=data,
                duration_ms=duration,
                source="fallback",
            )
        except Exception as exc:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Fallback also failed: {exc}",
                duration_ms=duration,
                source="fallback_failed",
            )


# ---------------------------------------------------------------------------
# 预配置的执行器（系统级别复用）
# ---------------------------------------------------------------------------

# API 调用：2s 超时 + 2 次重试 + 熔断
api_executor = ToolExecutor(ExecutorConfig(
    timeout_seconds=8.0,
    max_retries=2,
    base_backoff_seconds=0.5,
    circuit_breaker=CircuitBreaker(failure_threshold=5, recovery_timeout=60.0),
))

# LLM 调用：15s 超时 + 1 次重试（LLM 侧自身有容错）
llm_executor = ToolExecutor(ExecutorConfig(
    timeout_seconds=30.0,
    max_retries=1,
    base_backoff_seconds=2.0,
))

# 缓存/本地查询：1s 超时不重试
cache_executor = ToolExecutor(ExecutorConfig(
    timeout_seconds=2.0,
    max_retries=0,
))
