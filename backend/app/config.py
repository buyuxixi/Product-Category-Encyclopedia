from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    database_url: str
    auth_mode: str
    feishu_app_id: str | None
    feishu_app_secret: str | None
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
    # 选品Agent LLM配置
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    crawler_enabled: bool
    crawler_scripts_dir: str
    crawler_api_base: str
    crawler_password_file: str
    crawler_http_proxy: str
    crawler_https_proxy: str


@lru_cache
def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv(
            "DATABASE_URL",
            "mysql+pymysql://encyclopedia:encyclopedia_dev@localhost:3308/"
            "category_encyclopedia?charset=utf8mb4",
        ),
        auth_mode=os.getenv("AUTH_MODE", "local").strip().lower(),
        feishu_app_id=os.getenv("FEISHU_APP_ID") or None,
        feishu_app_secret=os.getenv("FEISHU_APP_SECRET") or None,
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
        llm_api_key=os.getenv("LLM_API_KEY", ""),
        llm_base_url=os.getenv(
            "LLM_BASE_URL",
            "https://llm-4ky3t9l8il29a1dv.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
        ),
        llm_model=os.getenv("LLM_MODEL", "qwen-plus"),
        crawler_enabled=os.getenv("CRAWLER_ENABLED", "false").lower() in {"1", "true", "yes"},
        crawler_scripts_dir=os.getenv(
            "CRAWLER_SCRIPTS_DIR",
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "crawler"),
        ).strip(),
        crawler_api_base=os.getenv("CRAWLER_API_BASE", "http://backend:8000/api/v1").strip(),
        crawler_password_file=os.getenv(
            "CRAWLER_PASSWORD_FILE",
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".crawler_password"),
        ).strip(),
        crawler_http_proxy=os.getenv("CRAWLER_HTTP_PROXY", "").strip(),
        crawler_https_proxy=os.getenv("CRAWLER_HTTPS_PROXY", "").strip(),
    )
