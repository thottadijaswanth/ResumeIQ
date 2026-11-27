import json
import re
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


def sanitize_error_message(message: str, secrets: tuple[Optional[str], ...] = ()) -> str:
    """Redact potential API keys or Bearer tokens from log/error strings."""
    cleaned = message
    for secret in secrets:
        if secret and len(secret) > 4:
            cleaned = cleaned.replace(secret, "***REDACTED***")
    cleaned = re.sub(r"Bearer\s+[A-Za-z0-9\-_\.]+", "Bearer ***REDACTED***", cleaned)
    cleaned = re.sub(r"sk-[A-Za-z0-9\-_]{8,}", "sk-***REDACTED***", cleaned)
    return cleaned


def extract_json_payload(raw_text: str) -> Any:
    """
    Safely parse JSON from LLM output, stripping reasoning tags, markdown code fences,
    or surrounding prose when a valid JSON object or array is embedded.
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("Empty response from AI provider.")

    # Strip <think>...</think> blocks emitted by reasoning models (e.g., Qwen3 / DeepSeek-R1)
    text = re.sub(r"<think>[\s\S]*?</think>", "", raw_text, flags=re.IGNORECASE).strip()
    if not text:
        raise ValueError("Empty response from AI provider.")

    # Fast path: valid JSON directly
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip ```json ... ``` or ``` ... ``` markdown fences
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if fence_match:
        candidate = fence_match.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            text = candidate

    # Locate outermost JSON object or array
    obj_start = text.find("{")
    arr_start = text.find("[")
    starts = [idx for idx in (obj_start, arr_start) if idx != -1]
    if not starts:
        raise ValueError("No JSON object or array found in AI response.")

    start_idx = min(starts)
    open_char = text[start_idx]
    close_char = "}" if open_char == "{" else "]"
    end_idx = text.rfind(close_char)
    if end_idx == -1 or end_idx <= start_idx:
        raise ValueError("Unterminated JSON structure in AI response.")

    candidate = text[start_idx : end_idx + 1]
    return json.loads(candidate)


def validate_structured_payload(payload: Any, schema_model: Type[T]) -> T:
    """Validate parsed JSON payload against a Pydantic V2 schema model."""
    try:
        return schema_model.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"Schema validation failed for {schema_model.__name__}: {exc}") from exc


def schema_dict_for_model(schema_model: Type[BaseModel]) -> Dict[str, Any]:
    """
    Generate a compact JSON structure template for LLM prompt guidance.
    Dramatically smaller than raw Pydantic JSON Schema (especially on local CPUs)
    while preserving exact field names and nested item shapes.
    """
    raw_schema = schema_model.model_json_schema()
    defs = raw_schema.get("$defs") or {}

    def _simplify(node: Dict[str, Any], depth: int = 0) -> Any:
        if depth > 4:
            return "..."
        if "$ref" in node:
            ref_name = node["$ref"].split("/")[-1]
            return _simplify(defs.get(ref_name, {}), depth + 1)
        if "anyOf" in node:
            non_null = [opt for opt in node["anyOf"] if opt.get("type") != "null"]
            if non_null:
                return _simplify(non_null[0], depth + 1)
            return None
        node_type = node.get("type")
        if node_type == "object" or "properties" in node:
            props = node.get("properties") or {}
            if not props:
                return {}
            return {k: _simplify(v, depth + 1) for k, v in props.items()}
        if node_type == "array":
            items = node.get("items") or {}
            return [_simplify(items, depth + 1)]
        if node_type == "string":
            return ""
        if node_type in ("number", "integer"):
            return 0
        if node_type == "boolean":
            return False
        return None

    simplified = _simplify(raw_schema)
    return simplified if isinstance(simplified, dict) else raw_schema
