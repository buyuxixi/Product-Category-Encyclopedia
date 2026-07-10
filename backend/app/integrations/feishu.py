from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.config import get_settings


TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
CREATE_DOCUMENT_URL = "https://open.feishu.cn/open-apis/docx/v1/documents"
CONVERT_BLOCKS_URL = "https://open.feishu.cn/open-apis/docx/v1/documents/blocks/convert"


@dataclass(frozen=True)
class PublicationResult:
    external_doc_id: str
    external_url: str | None


class Publisher(Protocol):
    name: str

    def publish(self, *, version_id: int, title: str, content: str) -> PublicationResult: ...


class LocalPreviewPublisher:
    name = "local"

    def publish(self, *, version_id: int, title: str, content: str) -> PublicationResult:
        return PublicationResult(external_doc_id=f"local-preview-{version_id}", external_url=None)


def _safe_json(response: httpx.Response, operation: str) -> dict[str, Any]:
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") not in (0, None):
        raise RuntimeError(f"Feishu {operation} failed")
    return payload


def _remove_read_only_fields(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _remove_read_only_fields(child)
            for key, child in value.items()
            if key not in {"block_id", "parent_id", "children", "merge_info"}
        }
    if isinstance(value, list):
        return [_remove_read_only_fields(item) for item in value]
    return value


class FeishuPublisher:
    name = "feishu"

    def publish(self, *, version_id: int, title: str, content: str) -> PublicationResult:
        del version_id
        settings = get_settings()
        if not settings.feishu_app_id or not settings.feishu_app_secret:
            raise RuntimeError("Feishu publishing requires FEISHU_APP_ID and FEISHU_APP_SECRET")

        with httpx.Client(timeout=15.0) as client:
            token_payload = _safe_json(
                client.post(
                    TOKEN_URL,
                    json={
                        "app_id": settings.feishu_app_id,
                        "app_secret": settings.feishu_app_secret,
                    },
                    headers={"Content-Type": "application/json"},
                ),
                "tenant token",
            )
            token = str(token_payload.get("tenant_access_token") or "")
            if not token:
                raise RuntimeError("Feishu tenant token response was invalid")
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            }
            create_body: dict[str, str] = {"title": title}
            if settings.feishu_parent_folder_token:
                create_body["folder_token"] = settings.feishu_parent_folder_token
            document_payload = _safe_json(
                client.post(CREATE_DOCUMENT_URL, json=create_body, headers=headers),
                "document creation",
            )
            document = document_payload.get("data", {}).get("document", {})
            document_id = str(document.get("document_id") or "")
            if not document_id:
                raise RuntimeError("Feishu document creation response was invalid")

            converted_payload = _safe_json(
                client.post(
                    CONVERT_BLOCKS_URL,
                    json={"content_type": "markdown", "content": content},
                    headers=headers,
                ),
                "Markdown conversion",
            )
            converted_data = converted_payload.get("data", {})
            blocks = converted_data.get("blocks") or converted_data.get("descendants") or []
            if not isinstance(blocks, list) or not blocks:
                raise RuntimeError("Feishu Markdown conversion returned no blocks")
            if len(blocks) > 1000:
                raise RuntimeError("Feishu publication contains too many document blocks")
            children_ids = [str(block.get("block_id")) for block in blocks if block.get("block_id")]
            descendants = [_remove_read_only_fields(block) for block in blocks]
            if len(children_ids) != len(descendants):
                raise RuntimeError("Feishu Markdown conversion returned invalid block ids")
            _safe_json(
                client.post(
                    f"{CREATE_DOCUMENT_URL}/{document_id}/blocks/{document_id}/descendant",
                    params={"document_revision_id": -1},
                    json={
                        "index": 0,
                        "children_id": children_ids,
                        "descendants": descendants,
                    },
                    headers=headers,
                ),
                "document content insertion",
            )

        return PublicationResult(
            external_doc_id=document_id,
            external_url=f"https://feishu.cn/docx/{document_id}",
        )


def get_publisher(name: str) -> Publisher:
    if name == "local":
        return LocalPreviewPublisher()
    if name == "feishu":
        return FeishuPublisher()
    raise ValueError("Unsupported publication provider")
