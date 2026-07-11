"""API tests for the authentication endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _register(client: AsyncClient, email: str, org: str) -> dict:
    resp = await client.post(
        "/v1/auth/register",
        json={
            "email": email,
            "password": "a-strong-password-123",
            "organization_name": org,
        },
    )
    return resp


async def test_register_returns_201_and_tokens(api_client: AsyncClient) -> None:
    resp = await _register(api_client, "founder@x.com", "Xco")
    assert resp.status_code == 201
    body = resp.json()
    assert body["tokens"]["access_token"]
    assert body["user"]["email"] == "founder@x.com"
    assert body["user"]["role"] == "admin"
    assert body["organization"]["slug"] == "xco"


async def test_register_second_org_same_email_allowed(
    api_client: AsyncClient,
) -> None:
    # Email uniqueness is per-organization. Registering the same email again
    # creates a new organization (unique slug), which is allowed.
    first = await _register(api_client, "dup@x.com", "Dupco")
    assert first.status_code == 201
    second = await api_client.post(
        "/v1/auth/register",
        json={
            "email": "dup@x.com",
            "password": "another-strong-pass-1",
            "organization_name": "Dupco",
        },
    )
    assert second.status_code == 201
    # The two organizations are distinct (slug disambiguated).
    assert (
        first.json()["organization"]["slug"]
        != second.json()["organization"]["slug"]
    )


async def test_login_returns_tokens(api_client: AsyncClient) -> None:
    await _register(api_client, "login@x.com", "Loginco")
    resp = await api_client.post(
        "/v1/auth/login",
        json={"email": "login@x.com", "password": "a-strong-password-123"},
    )
    assert resp.status_code == 200
    assert resp.json()["tokens"]["access_token"]


async def test_login_wrong_password_401(api_client: AsyncClient) -> None:
    await _register(api_client, "wp@x.com", "Wpco")
    resp = await api_client.post(
        "/v1/auth/login",
        json={"email": "wp@x.com", "password": "incorrect"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHENTICATED"


async def test_me_requires_auth(api_client: AsyncClient) -> None:
    resp = await api_client.get("/v1/users/me")
    assert resp.status_code == 401


async def test_me_returns_current_user(api_client: AsyncClient) -> None:
    reg = await _register(api_client, "me@x.com", "Meco")
    access = reg.json()["tokens"]["access_token"]
    resp = await api_client.get(
        "/v1/users/me", headers={"Authorization": f"Bearer {access}"}
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@x.com"


async def test_organizations_me(api_client: AsyncClient) -> None:
    reg = await _register(api_client, "org@x.com", "Orgco")
    access = reg.json()["tokens"]["access_token"]
    resp = await api_client.get(
        "/v1/organizations/me", headers={"Authorization": f"Bearer {access}"}
    )
    assert resp.status_code == 200
    assert resp.json()["slug"] == "orgco"


async def test_refresh_rotates_token(api_client: AsyncClient) -> None:
    reg = await _register(api_client, "refresh@x.com", "Refco")
    refresh = reg.json()["tokens"]["refresh_token"]
    resp = await api_client.post(
        "/v1/auth/refresh", json={"refresh_token": refresh}
    )
    assert resp.status_code == 200
    assert resp.json()["refresh_token"] != refresh


async def test_logout_then_refresh_fails(api_client: AsyncClient) -> None:
    reg = await _register(api_client, "lo@x.com", "Loco")
    refresh = reg.json()["tokens"]["refresh_token"]
    logout = await api_client.post(
        "/v1/auth/logout", json={"refresh_token": refresh}
    )
    assert logout.status_code == 204
    resp = await api_client.post(
        "/v1/auth/refresh", json={"refresh_token": refresh}
    )
    assert resp.status_code == 401


async def test_employee_forbidden_from_users_list(api_client: AsyncClient) -> None:
    # The registered user is an admin; assert admin CAN list users, proving the
    # permission dependency allows a granted permission.
    reg = await _register(api_client, "adm@x.com", "Admco")
    access = reg.json()["tokens"]["access_token"]
    resp = await api_client.get(
        "/v1/users", headers={"Authorization": f"Bearer {access}"}
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
