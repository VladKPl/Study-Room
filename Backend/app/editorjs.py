import json
from typing import Any
from urllib.parse import urlparse

from fastapi import HTTPException, status

ALLOWED_EDITORJS_BLOCK_TYPES = {
    "paragraph",
    "header",
    "list",
    "checklist",
    "quote",
    "delimiter",
    "warning",
    "table",
    "code",
    "linkTool",
    "embed",
    "image",
    "attaches",
    "raw",
}

EDITORJS_MAX_BLOCKS = 300
EDITORJS_MAX_JSON_BYTES = 300_000
URL_FIELD_NAMES = {"url", "link", "href", "src"}


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _reject_invalid_url_field(field_name: str, path: str, value: str) -> None:
    if not _is_http_url(value):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name}: {path} must use http or https URL",
        )


def _validate_url_fields(field_name: str, value: Any, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, nested_value in value.items():
            nested_path = f"{path}.{key}"
            if key in URL_FIELD_NAMES and isinstance(nested_value, str) and nested_value.strip():
                _reject_invalid_url_field(field_name, nested_path, nested_value.strip())
            _validate_url_fields(field_name, nested_value, nested_path)
        return

    if isinstance(value, list):
        for index, nested_value in enumerate(value):
            _validate_url_fields(field_name, nested_value, f"{path}[{index}]")


def _validate_editorjs_document(field_name: str, document: dict[str, Any]) -> dict[str, Any]:
    blocks = document.get("blocks")
    if not isinstance(blocks, list):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} must contain 'blocks' list",
        )
    if len(blocks) > EDITORJS_MAX_BLOCKS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} exceeds {EDITORJS_MAX_BLOCKS} blocks",
        )

    normalized_blocks: list[dict[str, Any]] = []
    for index, block in enumerate(blocks):
        if not isinstance(block, dict):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"{field_name}.blocks[{index}] must be object",
            )
        block_type = block.get("type")
        if block_type not in ALLOWED_EDITORJS_BLOCK_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"{field_name}.blocks[{index}].type '{block_type}' is not allowed",
            )
        data = block.get("data")
        if not isinstance(data, dict):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"{field_name}.blocks[{index}].data must be object",
            )
        _validate_url_fields(field_name, data, f"blocks[{index}].data")
        normalized_blocks.append(
            {
                "id": block.get("id"),
                "type": block_type,
                "data": data,
            }
        )

    normalized: dict[str, Any] = {
        "time": document.get("time"),
        "version": document.get("version"),
        "blocks": normalized_blocks,
    }
    return normalized


def normalize_editorjs_payload_for_storage(field_name: str, value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return None
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return value
        if isinstance(parsed, dict) and isinstance(parsed.get("blocks"), list):
            normalized = _validate_editorjs_document(field_name, parsed)
            serialized = json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))
            if len(serialized.encode("utf-8")) > EDITORJS_MAX_JSON_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"{field_name} payload is too large",
                )
            return serialized
        return value

    if isinstance(value, dict):
        normalized = _validate_editorjs_document(field_name, value)
        serialized = json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))
        if len(serialized.encode("utf-8")) > EDITORJS_MAX_JSON_BYTES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"{field_name} payload is too large",
            )
        return serialized

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=f"{field_name} must be string or Editor.js object",
    )


def parse_editorjs_payload_for_response(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped:
        return value
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return value
    if isinstance(parsed, dict) and isinstance(parsed.get("blocks"), list):
        return parsed
    return value
