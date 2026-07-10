from __future__ import annotations

import json

from sqlalchemy import select
from starlette.responses import Response

from app.config import get_settings
from app.models import AuthSession, User
from app.security import authenticate_local, create_session, hash_password, sync_configured_users, verify_password


def test_password_hash_is_not_reversible_and_verifies():
    encoded = hash_password("correct horse battery staple")

    assert encoded != "correct horse battery staple"
    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("wrong", encoded)


def test_configured_local_users_are_seeded_and_can_login(db, monkeypatch):
    monkeypatch.setenv(
        "AUTH_USERS_JSON",
        json.dumps(
            [
                {
                    "username": "reviewer",
                    "password": "reviewer-password",
                    "role": "reviewer",
                    "display_name": "审核员",
                }
            ]
        ),
    )
    monkeypatch.setenv("AUTH_MODE", "local")
    get_settings.cache_clear()

    sync_configured_users(db)
    user = db.scalar(select(User).where(User.username == "reviewer"))
    assert user is not None
    assert authenticate_local(db, "reviewer", "reviewer-password") is user
    assert authenticate_local(db, "reviewer", "wrong") is None


def test_session_creation_stores_only_token_hash(db, monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "local")
    get_settings.cache_clear()
    user = User(
        username="admin",
        display_name="管理员",
        role="admin",
        password_hash=hash_password("password"),
        external_provider="local",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    response = Response()
    create_session(db, user, response)
    session = db.scalar(select(AuthSession).where(AuthSession.user_id == user.id))

    assert session is not None
    assert session.token_hash not in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]
