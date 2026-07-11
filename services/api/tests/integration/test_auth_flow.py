"""Integration test: a complete authentication journey end to end."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_full_journey(api_client: AsyncClient) -> None:
    # 1. Register a new organization + admin user.
    reg = await api_client.post(
        "/v1/auth/register",
        json={
            "email": "journey@corp.com",
            "password": "journey-strong-pass-1",
            "organization_name": "Journey Corp",
        },
    )
    assert reg.status_code == 201
    tokens = reg.json()["tokens"]

    # 2. Use the access token to read the current user and organization.
    auth = {"Authorization": f"Bearer {tokens['access_token']}"}
    me = await api_client.get("/v1/users/me", headers=auth)
    assert me.status_code == 200
    assert me.json()["email"] == "journey@corp.com"

    org = await api_client.get("/v1/organizations/me", headers=auth)
    assert org.status_code == 200
    assert org.json()["name"] == "Journey Corp"

    # 3. Rotate the refresh token.
    refreshed = await api_client.post(
        "/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refreshed.status_code == 200
    new_tokens = refreshed.json()

    # 4. The new access token still works.
    new_auth = {"Authorization": f"Bearer {new_tokens['access_token']}"}
    me2 = await api_client.get("/v1/users/me", headers=new_auth)
    assert me2.status_code == 200

    # 5. Logout revokes the (new) refresh token.
    logout = await api_client.post(
        "/v1/auth/logout", json={"refresh_token": new_tokens["refresh_token"]}
    )
    assert logout.status_code == 204

    # 6. The revoked refresh token can no longer be rotated.
    replay = await api_client.post(
        "/v1/auth/refresh", json={"refresh_token": new_tokens["refresh_token"]}
    )
    assert replay.status_code == 401


async def test_register_validation_error(client: AsyncClient) -> None:
    # Password too short -> 400 validation error (no DB needed).
    resp = await client.post(
        "/v1/auth/register",
        json={
            "email": "bad@corp.com",
            "password": "short",
            "organization_name": "Bad Corp",
        },
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["field_errors"]


async def test_register_invalid_email(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/auth/register",
        json={
            "email": "not-an-email",
            "password": "a-strong-password-123",
            "organization_name": "X",
        },
    )
    assert resp.status_code == 400
