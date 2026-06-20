"""
Pytest 配置和 fixtures

根因：asyncpg 连接绑定到创建时的事件循环。
每次 asyncio.run() 创建新的事件循环，必须重置 PersistenceService 单例。
"""

import asyncio
import pytest


@pytest.fixture(autouse=True)
def reset_persistence_singleton():
    """每个测试前重置 PersistenceService 单例，确保新的事件循环能创建新的引擎"""
    from app.services.persistence import PersistenceService
    PersistenceService._instance = None
    PersistenceService._settings = None
    PersistenceService._engine = None
    PersistenceService._async_session = None
    yield
