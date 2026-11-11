"""Проверки поведения по api.yaml (написаны руками вместо сгенерированных заготовок)."""
import os
import time
import uuid

import jwt
import pytest
from fastapi.testclient import TestClient

from habit_tracker.impl.habits_api_impl import DB

BASE = "/api/v1/habits"


def auth(user: str) -> dict:
    token = jwt.encode({"sub": user, "exp": int(time.time()) + 600},
                       os.getenv("JWT_SECRET", "dev-secret"), algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def clean_db():
    DB.clear()


def create(client: TestClient, user="alice", title="Пить воду", **extra):
    body = {"title": title, "frequency": "DAILY", **extra}
    return client.post(BASE, json=body, headers=auth(user))


# ── 401: «не знаю, кто ты» ────────────────────────────────────────────────────
def test_no_token_is_401(client: TestClient):
    r = client.get(BASE)
    assert r.status_code == 401
    assert r.json()["code"] == "unauthorized"
    assert r.headers["www-authenticate"] == "Bearer"


def test_bad_token_is_401(client: TestClient):
    assert client.get(BASE, headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_expired_token_is_401(client: TestClient):
    token = jwt.encode({"sub": "alice", "exp": int(time.time()) - 10}, "dev-secret", algorithm="HS256")
    assert client.get(BASE, headers={"Authorization": f"Bearer {token}"}).status_code == 401


# ── POST ─────────────────────────────────────────────────────────────────────
def test_create_returns_201_location_and_only_schema_fields(client: TestClient):
    r = create(client, description="Два литра")
    assert r.status_code == 201
    body = r.json()
    assert r.headers["location"] == f"/api/v1/habits/{body['id']}"
    assert set(body) == {"id", "title", "description", "frequency", "targetPerPeriod",
                         "archived", "currentStreak", "createdAt"}      # ни ownerId, ни rowVersion
    assert body["targetPerPeriod"] == 1 and body["archived"] is False


def test_create_validation_is_400_with_field_errors(client: TestClient):
    r = client.post(BASE, json={"title": "", "frequency": "DAILY"}, headers=auth("alice"))
    assert r.status_code == 400
    assert r.json()["code"] == "validation_failed"
    assert r.json()["fieldErrors"][0]["field"] == "title"


def test_create_duplicate_title_is_409(client: TestClient):
    assert create(client).status_code == 201
    r = create(client, title="пить воду")
    assert r.status_code == 409 and r.json()["code"] == "habit_already_exists"


# ── GET список ───────────────────────────────────────────────────────────────
def test_list_shows_only_my_habits(client: TestClient):
    create(client, "alice", "Бегать")
    create(client, "bob", "Читать")
    r = client.get(BASE, headers=auth("alice"))
    assert r.status_code == 200
    assert [h["title"] for h in r.json()["items"]] == ["Бегать"]
    assert r.json()["total"] == 1


def test_list_filters_and_pagination(client: TestClient):
    for t in ("A", "B", "C"):
        create(client, title=t)
    habit_b = client.get(BASE, headers=auth("alice")).json()["items"][1]["id"]
    client.patch(f"{BASE}/{habit_b}", json={"archived": True}, headers=auth("alice"))
    active = client.get(BASE, headers=auth("alice")).json()
    assert [h["title"] for h in active["items"]] == ["A", "C"]            # status=active по умолчанию
    arch = client.get(BASE, params={"status": "archived"}, headers=auth("alice")).json()
    assert [h["title"] for h in arch["items"]] == ["B"]
    page = client.get(BASE, params={"status": "all", "limit": 1, "offset": 1}, headers=auth("alice")).json()
    assert page["total"] == 3 and [h["title"] for h in page["items"]] == ["B"]


def test_list_bad_params_are_400(client: TestClient):
    assert client.get(BASE, params={"limit": 0}, headers=auth("alice")).status_code == 400
    assert client.get(BASE, params={"status": "weird"}, headers=auth("alice")).status_code == 400


# ── GET одной: 403 против 404 ────────────────────────────────────────────────
def test_get_one_ok_forbidden_not_found(client: TestClient):
    hid = create(client, "alice").json()["id"]
    assert client.get(f"{BASE}/{hid}", headers=auth("alice")).status_code == 200
    r = client.get(f"{BASE}/{hid}", headers=auth("bob"))        # знаю, кто ты, но чужое
    assert r.status_code == 403 and r.json()["code"] == "forbidden"
    r = client.get(f"{BASE}/{uuid.uuid4()}", headers=auth("alice"))
    assert r.status_code == 404 and r.json()["code"] == "habit_not_found"


# ── PATCH ────────────────────────────────────────────────────────────────────
def test_patch_changes_only_given_fields(client: TestClient):
    hid = create(client, description="старое").json()["id"]
    r = client.patch(f"{BASE}/{hid}", json={"title": "Пить чай"}, headers=auth("alice"))
    assert r.status_code == 200
    assert r.json()["title"] == "Пить чай" and r.json()["description"] == "старое"


def test_patch_empty_body_is_400_and_foreign_is_403(client: TestClient):
    hid = create(client).json()["id"]
    assert client.patch(f"{BASE}/{hid}", json={}, headers=auth("alice")).status_code == 400
    assert client.patch(f"{BASE}/{hid}", json={"archived": True}, headers=auth("bob")).status_code == 403
    assert client.patch(f"{BASE}/{uuid.uuid4()}", json={"archived": True}, headers=auth("alice")).status_code == 404


# ── DELETE ───────────────────────────────────────────────────────────────────
def test_delete_204_then_404_and_foreign_403(client: TestClient):
    hid = create(client).json()["id"]
    assert client.delete(f"{BASE}/{hid}", headers=auth("bob")).status_code == 403
    r = client.delete(f"{BASE}/{hid}", headers=auth("alice"))
    assert r.status_code == 204 and r.content == b""
    assert client.get(f"{BASE}/{hid}", headers=auth("alice")).status_code == 404


# ── additionalProperties: false из спеки ─────────────────────────────────────
def test_extra_fields_are_rejected_with_400(client: TestClient):
    r = client.post(BASE, json={"title": "X", "frequency": "DAILY", "ownerId": "bob"}, headers=auth("alice"))
    assert r.status_code == 400 and r.json()["fieldErrors"][0]["field"] == "ownerId"
    hid = create(client, title="Y").json()["id"]
    r = client.patch(f"{BASE}/{hid}", json={"archived": True, "ownerId": "bob"}, headers=auth("alice"))
    assert r.status_code == 400
