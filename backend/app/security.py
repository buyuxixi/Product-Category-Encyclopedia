from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import AuditEvent, AuthSession, User


VALID_ROLES = {"admin", "data", "researcher", "reviewer"}
PASSWORD_ITERATIONS = 310_000


@dataclass(frozen=True)
class Actor:
    id: int
    name: str
    role: str
    provider: str


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )
    return "pbkdf2_sha256${}${}${}".format(
        PASSWORD_ITERATIONS, salt.hex(), digest.hex()
    )


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (TypeError, ValueError):
        return False


def configured_local_users() -> list[dict[str, str]]:
    raw = get_settings().auth_users_json.strip()
    if not raw:
        return []
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("AUTH_USERS_JSON must be valid JSON") from exc
    if not isinstance(payload, list):
        raise RuntimeError("AUTH_USERS_JSON must be a JSON array")
    users: list[dict[str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            raise RuntimeError("Each AUTH_USERS_JSON item must be an object")
        username = str(item.get("username") or "").strip()
        password = str(item.get("password") or "")
        role = str(item.get("role") or "").strip()
        display_name = str(item.get("display_name") or username).strip()
        if not username or not password or role not in VALID_ROLES:
            raise RuntimeError("Each local auth user needs username, password and valid role")
        users.append(
            {
                "username": username[:160],
                "password": password,
                "role": role,
                "display_name": display_name[:160],
            }
        )
    return users


def sync_configured_users(db: Session) -> None:
    if get_settings().auth_mode != "local":
        return
    for item in configured_local_users():
        user = db.scalar(select(User).where(User.username == item["username"]))
        if user is None:
            db.add(
                User(
                    username=item["username"],
                    display_name=item["display_name"],
                    role=item["role"],
                    password_hash=hash_password(item["password"]),
                    external_provider="local",
                    is_active=True,
                )
            )
        else:
            user.display_name = item["display_name"]
            user.role = item["role"]
            user.is_active = True
    db.commit()


def authenticate_local(db: Session, username: str, password: str) -> User | None:
    user = db.scalar(
        select(User).where(User.username == username.strip(), User.external_provider == "local")
    )
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        return None
    return user


def actor_from_user(user: User) -> Actor:
    return Actor(id=user.id, name=user.display_name, role=user.role, provider=user.external_provider)


def create_session(db: Session, user: User, response: Response) -> None:
    raw_token = secrets.token_urlsafe(48)
    now = datetime.now(UTC)
    session = AuthSession(
        token_hash=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
        user_id=user.id,
        expires_at=now + timedelta(hours=get_settings().session_ttl_hours),
    )
    db.add(session)
    db.add(
        AuditEvent(
            actor=user.display_name,
            action="login",
            entity_type="user",
            entity_id=str(user.id),
            metadata_json={"provider": user.external_provider},
        )
    )
    db.commit()
    response.set_cookie(
        key=get_settings().session_cookie_name,
        value=raw_token,
        max_age=get_settings().session_ttl_hours * 3600,
        httponly=True,
        secure=get_settings().cookie_secure,
        samesite="lax",
        path="/",
    )


def revoke_session(db: Session, token: str | None) -> None:
    if not token:
        return
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash))
    if session is not None and session.revoked_at is None:
        session.revoked_at = datetime.now(UTC)
        db.commit()


def get_actor(
    request: Request,
    db: Session = Depends(get_db),
) -> Actor:
    settings = get_settings()
    if settings.auth_mode not in {"local", "feishu"}:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured. Set AUTH_MODE=local or AUTH_MODE=feishu.",
        )
    session_token = request.cookies.get(settings.session_cookie_name)
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")

    token_hash = hashlib.sha256(session_token.encode("utf-8")).hexdigest()
    session = db.scalar(
        select(AuthSession).where(
            AuthSession.token_hash == token_hash,
            AuthSession.revoked_at.is_(None),
        )
    )
    if session is None or _utc(session.expires_at) <= datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已过期，请重新登录")
    user = db.get(User, session.user_id)
    if user is None or not user.is_active or user.role not in VALID_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前账号不可用")
    return actor_from_user(user)


def ensure_role(actor: Actor, *roles: str) -> None:
    if actor.role not in set(roles):
        raise HTTPException(status_code=403, detail="当前账号没有执行此操作的权限")
