import base64
import re
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import requests
from langchain.tools import tool
from pydantic import BaseModel, Field

from async_utils import format_exception, retry_blocking
from file_tools import AGENT_DIR
from llm_config import OMNIROUTE_API_KEY, OMNIROUTE_BASE_URL


MEDIA_DIR = Path(AGENT_DIR) / "media"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov"}


def _safe_filename(filename: str, default_ext: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", filename.strip())[:120]
    if not name:
        name = "generation"
    if not Path(name).suffix:
        name += default_ext
    return name


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if OMNIROUTE_API_KEY:
        headers["Authorization"] = f"Bearer {OMNIROUTE_API_KEY}"
    return headers


def _post_omniroute(path: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    url = f"{OMNIROUTE_BASE_URL.rstrip('/')}{path}"
    response = requests.post(url, headers=_headers(), json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json()


def _get_omniroute_models() -> list[dict[str, Any]]:
    response = requests.get(f"{OMNIROUTE_BASE_URL.rstrip('/')}/models", headers=_headers(), timeout=15)
    response.raise_for_status()
    data = response.json().get("data", [])
    return data if isinstance(data, list) else []


def _save_media_item(item: dict[str, Any], filename: str, default_ext: str, timeout: int) -> str:
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_filename(filename, default_ext)
    path = MEDIA_DIR / safe_name

    if item.get("b64_json"):
        path.write_bytes(base64.b64decode(item["b64_json"]))
        return str(path)

    url = item.get("url") or item.get("video_url")
    if url:
        parsed_ext = Path(urlparse(url).path).suffix.lower()
        if parsed_ext and parsed_ext != path.suffix.lower():
            path = path.with_suffix(parsed_ext)
        media = requests.get(url, timeout=timeout)
        media.raise_for_status()
        path.write_bytes(media.content)
        return str(path)

    raise ValueError(f"No downloadable media payload found. Keys: {', '.join(item.keys())}")


class ListMediaModelsInput(BaseModel):
    kind: Literal["image", "video", "all"] = Field("all", description="Which media model type to list.")
    max_results: int = Field(30, description="Maximum number of models to return.")


@tool(args_schema=ListMediaModelsInput)
async def list_omniroute_media_models(kind: str = "all", max_results: int = 30) -> str:
    """List Omniroute media-generation routes available on the local endpoint."""
    try:
        models = await retry_blocking(_get_omniroute_models, attempts=2)
        rows = []
        for model in models:
            outputs = model.get("output_modalities") or []
            if kind != "all" and kind not in outputs:
                continue
            if kind == "all" and not ({"image", "video"} & set(outputs)):
                continue
            rows.append(
                f"{model.get('id')} | owner={model.get('owned_by')} | output={','.join(outputs)}"
            )
            if len(rows) >= max_results:
                break
        return "\n".join(rows) if rows else "No Omniroute media models were found."
    except Exception as exc:
        return f"Failed to list Omniroute media models: {format_exception(exc)}"


class GenerateOmniImageInput(BaseModel):
    prompt: str = Field(..., description="Detailed prompt for the image.")
    filename: str = Field("output.png", description="Filename to save under the assistant media folder.")
    model: str = Field("aihorde/Z-Image-Turbo", description="Omniroute image model route.")
    size: str = Field("1024x1024", description="Requested image size.")
    timeout_seconds: int = Field(240, description="Request timeout for slow free/community routes.")


@tool(args_schema=GenerateOmniImageInput)
async def generate_omniroute_image(
    prompt: str,
    filename: str = "output.png",
    model: str = "aihorde/Z-Image-Turbo",
    size: str = "1024x1024",
    timeout_seconds: int = 240,
) -> str:
    """Generate an image through Omniroute and save it under the D-drive assistant workspace."""
    payload = {"model": model, "prompt": prompt, "n": 1, "size": size}
    try:
        result = await retry_blocking(
            _post_omniroute,
            "/images/generations",
            payload,
            timeout_seconds,
            attempts=3,
            base_delay=3,
            max_delay=20,
        )
        items = result.get("data") or []
        if not items:
            return f"Omniroute image generation returned no image. Raw keys: {', '.join(result.keys())}"
        path = await retry_blocking(_save_media_item, items[0], filename, ".png", 60, attempts=2)
        return f"Saved image to {path}"
    except Exception as exc:
        return f"Failed to generate Omniroute image after retries: {format_exception(exc)}"


class GenerateOmniVideoInput(BaseModel):
    prompt: str = Field(..., description="Detailed prompt for the video.")
    filename: str = Field("output.mp4", description="Filename to save under the assistant media folder.")
    model: str = Field("veo-free/seedance", description="Omniroute video model route.")
    timeout_seconds: int = Field(600, description="Request timeout for slow free/community video routes.")


@tool(args_schema=GenerateOmniVideoInput)
async def generate_omniroute_video(
    prompt: str,
    filename: str = "output.mp4",
    model: str = "veo-free/seedance",
    timeout_seconds: int = 600,
) -> str:
    """Generate a short video through Omniroute and save it under the D-drive assistant workspace."""
    payload = {"model": model, "prompt": prompt}
    try:
        result = await retry_blocking(
            _post_omniroute,
            "/videos/generations",
            payload,
            timeout_seconds,
            attempts=2,
            base_delay=5,
            max_delay=30,
        )
        items = result.get("data") or []
        if not items:
            return f"Omniroute video generation returned no video. Raw keys: {', '.join(result.keys())}"
        path = await retry_blocking(_save_media_item, items[0], filename, ".mp4", 120, attempts=2)
        return f"Saved video to {path}"
    except Exception as exc:
        return f"Failed to generate Omniroute video after retries: {format_exception(exc)}"
