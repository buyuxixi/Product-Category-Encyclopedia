from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_url: str
    auth_mode: str
    import_roots: tuple[Path, ...]
    publication_provider: str
    feishu_app_id: str | None
    feishu_app_secret: str | None
    feishu_parent_folder_token: str | None
    feishu_redirect_uri: str | None
    feishu_scope: str
    feishu_frontend_url: str
    feishu_default_role: str
    feishu_role_map_json: str
    feishu_allowed_open_ids: tuple[str, ...]
    auth_users_json: str
    session_cookie_name: str
    session_ttl_hours: int
    cookie_secure: bool
    allowed_origins: tuple[str, ...]


@lru_cache
def get_settings() -> Settings:
    roots = tuple(
        Path(item.strip()).expanduser().resolve()
        for item in os.getenv("IMPORT_ROOTS", "/imports").split(",")
        if item.strip()
    )
    return Settings(
        database_url=os.getenv(
            "DATABASE_URL",
            "mysql+pymysql://encyclopedia:encyclopedia_dev@localhost:3308/"
            "category_encyclopedia?charset=utf8mb4",
        ),
        auth_mode=os.getenv("AUTH_MODE", "local").strip().lower(),
        import_roots=roots,
        publication_provider=os.getenv("PUBLICATION_PROVIDER", "local"),
        feishu_app_id=os.getenv("FEISHU_APP_ID") or None,
        feishu_app_secret=os.getenv("FEISHU_APP_SECRET") or None,
        feishu_parent_folder_token=os.getenv("FEISHU_PARENT_FOLDER_TOKEN") or None,
        feishu_redirect_uri=os.getenv("FEISHU_REDIRECT_URI") or None,
        feishu_scope=os.getenv("FEISHU_SCOPE", "").strip(),
        feishu_frontend_url=os.getenv("FEISHU_FRONTEND_URL", "/"),
        feishu_default_role=os.getenv("FEISHU_DEFAULT_ROLE", "researcher").strip(),
        feishu_role_map_json=os.getenv("FEISHU_ROLE_MAP_JSON", ""),
        feishu_allowed_open_ids=tuple(
            item.strip()
            for item in os.getenv("FEISHU_ALLOWED_OPEN_IDS", "").split(",")
            if item.strip()
        ),
        auth_users_json=os.getenv("AUTH_USERS_JSON", ""),
        session_cookie_name=os.getenv("SESSION_COOKIE_NAME", "encyclopedia_session"),
        session_ttl_hours=max(1, int(os.getenv("SESSION_TTL_HOURS", "12"))),
        cookie_secure=os.getenv("COOKIE_SECURE", "false").lower() in {"1", "true", "yes"},
        allowed_origins=tuple(
            item.strip()
            for item in os.getenv(
                "ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
            ).split(",")
            if item.strip()
        ),
    )
