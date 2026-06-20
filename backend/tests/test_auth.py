"""
Tests for authentication service

每个测试使用唯一用户名，避免测试间数据冲突。
"""

import asyncio
import pytest
import httpx
from httpx import ASGITransport
from app.main import app
from app.services.auth import (
    create_access_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    """Test password hashing and verification"""

    def test_hash_password_returns_string(self):
        hashed = hash_password("testpassword")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_verify_password_correct(self):
        password = "mypassword123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        hashed = hash_password("correctpassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_different_passwords_different_hashes(self):
        hash1 = hash_password("password1")
        hash2 = hash_password("password2")
        assert hash1 != hash2


class TestTokenCreation:
    """Test JWT token creation and validation"""

    def test_create_token_returns_string(self):
        from app.core.config import get_settings
        settings = get_settings()
        token = create_access_token("user123", "testuser", settings)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_valid_token(self):
        from app.core.config import get_settings
        from app.services.auth import decode_token

        settings = get_settings()
        token = create_access_token("user123", "testuser", settings)
        payload = decode_token(token, settings)

        assert payload["sub"] == "user123"
        assert payload["username"] == "testuser"
        assert payload["type"] == "access"
        assert "exp" in payload

    def test_decode_invalid_token_fails(self):
        from app.core.config import get_settings
        from app.services.auth import decode_token
        from fastapi import HTTPException

        settings = get_settings()
        with pytest.raises(HTTPException) as exc_info:
            decode_token("invalid.token.here", settings)

        assert exc_info.value.status_code == 401


class TestAuthEndpoints:
    """Test authentication API endpoints"""

    def test_register_user(self):
        async def _test():
            transport = ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/auth/register",
                    json={
                        "username": "newuser_unique_001",
                        "password": "password123",
                        "email": "new@example.com",
                    },
                )
                assert response.status_code == 201
                data = response.json()
                assert data["username"] == "newuser_unique_001"
                assert "user_id" in data

        asyncio.run(_test())

    def test_register_duplicate_username(self):
        async def _test():
            transport = ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                await client.post(
                    "/api/v1/auth/register",
                    json={"username": "duplicate_unique_002", "password": "password123"},
                )
                response = await client.post(
                    "/api/v1/auth/register",
                    json={"username": "duplicate_unique_002", "password": "password456"},
                )
                assert response.status_code == 409

        asyncio.run(_test())

    def test_register_short_password(self):
        async def _test():
            transport = ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/auth/register",
                    json={"username": "shortpass_unique_003", "password": "123"},
                )
                assert response.status_code == 400

        asyncio.run(_test())

    def test_login_success(self):
        async def _test():
            transport = ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                await client.post(
                    "/api/v1/auth/register",
                    json={"username": "logintest_unique_004", "password": "password123"},
                )
                response = await client.post(
                    "/api/v1/auth/login",
                    json={"username": "logintest_unique_004", "password": "password123"},
                )
                assert response.status_code == 200
                data = response.json()
                assert "access_token" in data
                assert data["token_type"] == "bearer"

        asyncio.run(_test())

    def test_login_wrong_password(self):
        async def _test():
            transport = ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                await client.post(
                    "/api/v1/auth/register",
                    json={"username": "wrongpass_unique_005", "password": "password123"},
                )
                response = await client.post(
                    "/api/v1/auth/login",
                    json={"username": "wrongpass_unique_005", "password": "wrongpassword"},
                )
                assert response.status_code == 401

        asyncio.run(_test())

    def test_login_nonexistent_user(self):
        async def _test():
            transport = ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/auth/login",
                    json={"username": "nonexistent_unique_006", "password": "password123"},
                )
                assert response.status_code == 401

        asyncio.run(_test())

    def test_get_me_authenticated(self):
        async def _test():
            transport = ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                await client.post(
                    "/api/v1/auth/register",
                    json={"username": "metest_unique_007", "password": "password123"},
                )
                login_response = await client.post(
                    "/api/v1/auth/login",
                    json={"username": "metest_unique_007", "password": "password123"},
                )
                token = login_response.json()["access_token"]
                response = await client.get(
                    "/api/v1/auth/me",
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert response.status_code == 200
                data = response.json()
                assert data["username"] == "metest_unique_007"

        asyncio.run(_test())

    def test_get_me_unauthenticated(self):
        async def _test():
            transport = ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/auth/me")
                assert response.status_code == 401

        asyncio.run(_test())

    def test_get_optional_user(self):
        async def _test():
            transport = ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/auth/optional")
                assert response.status_code == 200
                data = response.json()
                assert data["username"] == "guest"

        asyncio.run(_test())
