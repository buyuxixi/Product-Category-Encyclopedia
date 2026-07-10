from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import User
from app.security import VALID_ROLES


AUTHORIZE_URL = "https://accounts.feishu.cn/open-apis/authen/v1/authorize"
TOKEN_URL = "https://open.feishu.cn/open-apis/authen/v2/oauth/token"
USER_INFO_URL = "https://open.feishu.cn/open-apis/authen/v1/user_info"
STATE_TTL_SECONDS = 600


@dataclass(frozen=True)
class FeishuIdentity:
    open_id: str
    name: str


def _state_secret() -> bytes:
    secret = get_settings().feishu_app_secret
    if not secret:
        raise RuntimeError("FEISHU_APP_SECRET is not configured")
    return secret.encode("utf-8")


def create_state() -> str:
    timestamp = str(int(time.time()))
    nonce = secrets.token_urlsafe(24)
    payload = f"{timestamp}.{nonce}"
    signature = hmac.new(_state_secret(), payload.encode("utf-8"), hashlib.sha256).digest()
    encoded = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
    return f"{payload}.{encoded}"


def verify_state(state: str) -> bool:
    try:
        timestamp, nonce, signature = state.split(".", 2)
        if not nonce or abs(int(time.time()) - int(timestamp)) > STATE_TTL_SECONDS:
            return False
        payload = f"{timestamp}.{nonce}"
        expected = hmac.new(_state_secret(), payload.encode("utf-8"), hashlib.sha256).digest()
        actual = base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))
        return hmac.compare_digest(actual, expected)
    except (TypeError, ValueError):
        return False


def authorization_url() -> str:
    settings = get_settings()
    if not settings.feishu_app_id or not settings.feishu_app_secret or not settings.feishu_redirect_uri:
        raise RuntimeError("Feishu OAuth requires app id, app secret and redirect URI")
    params = {
        "client_id": settings.feishu_app_id,
        "redirect_uri": settings.feishu_redirect_uri,
        "response_type": "code",
        "state": create_state(),
    }
    if settings.feishu_scope:
        params["scope"] = settings.feishu_scope
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def _response_data(response: httpx.Response, operation: str) -> dict:
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") not in (0, None):
        raise RuntimeError(f"Feishu {operation} failed")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise RuntimeError(f"Feishu {operation} returned invalid data")
    return data


def exchange_code(code: str) -> FeishuIdentity:
    settings = get_settings()
    if not settings.feishu_app_id or not settings.feishu_app_secret or not settings.feishu_redirect_uri:
        raise RuntimeError("Feishu OAuth is not configured")
    with httpx.Client(timeout=10.0) as client:
        token_response = client.post(
            TOKEN_URL,
            json={
                "grant_type": "authorization_code",
                "client_id": settings.feishu_app_id,
                "client_secret": settings.feishu_app_secret,
                "code": code,
                "redirect_uri": settings.feishu_redirect_uri,
            },
            headers={"Content-Type": "application/json"},
        )
        token_data = _response_data(token_response, "token exchange")
        access_token = str(token_data.get("access_token") or "")
        if not access_token:
            raise RuntimeError("Feishu token exchange returned no access token")
        user_response = client.get(
            USER_INFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user_data = _response_data(user_response, "user info")
    open_id = str(user_data.get("open_id") or user_data.get("union_id") or "").strip()
    name = str(user_data.get("name") or user_data.get("en_name") or open_id).strip()
    if not open_id:
        raise RuntimeError("Feishu user info returned no stable user id")
    return FeishuIdentity(open_id=open_id, name=name[:160])


def _role_for(identity: FeishuIdentity) -> str:
    settings = get_settings()
    role = settings.feishu_default_role
    try:
        role_map = json.loads(settings.feishu_role_map_json or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError("FEISHU_ROLE_MAP_JSON must be valid JSON") from exc
    if isinstance(role_map, dict):
        role = str(role_map.get(identity.open_id) or role)
    if role not in VALID_ROLES:
        raise RuntimeError("FEISHU_DEFAULT_ROLE or role map contains an invalid role")
    if settings.feishu_allowed_open_ids and identity.open_id not in settings.feishu_allowed_open_ids:
        raise PermissionError("该飞书账号不在系统允许的成员范围内")
    return role


def upsert_user(db: Session, identity: FeishuIdentity) -> User:
    external_id = f"feishu:{identity.open_id}"
    user = db.scalar(select(User).where(User.external_id == external_id))
    if user is None:
        user = User(
            username=external_id,
            display_name=identity.name,
            role=_role_for(identity),
            password_hash=None,
            external_provider="feishu",
            external_id=external_id,
            is_active=True,
        )
        db.add(user)
    else:
        user.display_name = identity.name
        user.role = _role_for(identity)
        user.is_active = True
    db.commit()
    db.refresh(user)
    return user
