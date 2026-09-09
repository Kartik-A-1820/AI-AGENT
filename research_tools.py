import asyncio
import base64
import html
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote_plus, unquote, urlparse, parse_qs

import requests
from langchain.tools import tool
from pydantic import BaseModel, Field

from async_utils import format_exception, retry_async, retry_blocking
from file_tools import AGENT_DIR
from llm_config import create_llm


RESEARCH_DIR = Path(AGENT_DIR) / "research"
USER_AGENT = "AI-AGENT research assistant/1.0"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value.lower()).strip("-")
    return slug[:70] or "research-topic"


def _strip_tags(markup: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", markup)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _clean_result_url(url: str) -> str:
    parsed = urlparse(url)
    wrapped = parse_qs(parsed.query).get("u")
    if wrapped:
        value = wrapped[0]
        if value.startswith("a1"):
            padded = value[2:] + "=" * (-len(value[2:]) % 4)
            try:
                return base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
            except Exception:
                return url
        return unquote(value)
    return url


def _search_duckduckgo(query: str, max_results: int) -> list[dict[str, str]]:
    url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
    response.raise_for_status()
    results: list[dict[str, str]] = []
    pattern = re.compile(
        r'<a rel="nofollow" class="result__a" href="(?P<href>.*?)".*?>(?P<title>.*?)</a>.*?'
        r'<a class="result__snippet".*?>(?P<snippet>.*?)</a>',
        re.I | re.S,
    )
    for match in pattern.finditer(response.text):
        href = html.unescape(match.group("href"))
        if "uddg=" in href:
            href = _clean_result_url(unquote(parse_qs(urlparse(href).query).get("uddg", [href])[0]))
        results.append(
            {
                "title": _strip_tags(match.group("title")),
                "url": href,
                "snippet": _strip_tags(match.group("snippet")),
            }
        )
        if len(results) >= max_results:
            break
    return results


def _search_bing(query: str, max_results: int) -> list[dict[str, str]]:
    url = f"https://www.bing.com/search?q={quote_plus(query)}"
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    response.raise_for_status()
    results: list[dict[str, str]] = []
    pattern = re.compile(r'<h2.*?><a[^>]+href="(?P<href>.*?)"[^>]*>(?P<title>.*?)</a></h2>', re.I | re.S)
    for match in pattern.finditer(response.text):
        href = html.unescape(match.group("href"))
        href = _clean_result_url(href)
        tail = response.text[match.end(): match.end() + 1600]
        snippet_match = re.search(r"<p.*?>(.*?)</p>", tail, re.I | re.S)
        snippet = _strip_tags(snippet_match.group(1)) if snippet_match else ""
        results.append(
            {
                "title": _strip_tags(match.group("title")),
                "url": href,
                "snippet": snippet,
            }
        )
        if len(results) >= max_results:
            break
    return results


async def _search_tavily(query: str, max_results: int) -> list[dict[str, str]]:
    from tavily import TavilyClient

    def run() -> list[dict[str, str]]:
        client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        response = client.search(query=query, max_results=max_results, search_depth="advanced")
        return [
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", ""),
            }
            for item in response.get("results", [])
        ]

    return await retry_blocking(run, attempts=2)


async def _search_web(query: str, max_results: int) -> list[dict[str, str]]:
    if os.getenv("TAVILY_API_KEY"):
        return await _search_tavily(query, max_results)
    results = await retry_blocking(_search_duckduckgo, query, max_results, attempts=2)
    if results:
        return results
    return await retry_blocking(_search_bing, query, max_results, attempts=2)


def _fetch_url_text(url: str, max_chars: int) -> str:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=25)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    if "text" not in content_type and "html" not in content_type and "json" not in content_type:
        return ""
    return _strip_tags(response.text)[:max_chars]


class ResearchTopicInput(BaseModel):
    topic: str = Field(..., description="Topic or question to research.")
    depth: Literal["quick", "standard", "deep"] = Field("standard", description="Research depth.")
    max_sources: int = Field(8, description="Maximum sources to search and cite.")
    output_name: str | None = Field(None, description="Optional folder/file slug for saved research.")


@tool(args_schema=ResearchTopicInput)
async def research_topic(
    topic: str,
    depth: str = "standard",
    max_sources: int = 8,
    output_name: str | None = None,
) -> str:
    """Research a topic, synthesize cited findings, and save a Markdown brief."""
    try:
        max_sources = max(3, min(max_sources, 15))
        if depth == "quick":
            max_sources = min(max_sources, 5)
            max_chars = 2500
        elif depth == "deep":
            max_chars = 7000
        else:
            max_chars = 4500

        results = await _search_web(topic, max_sources)
        if not results:
            return "Research failed: no search results were returned."

        async def fetch_one(item: dict[str, str]) -> dict[str, str]:
            try:
                text = await retry_blocking(_fetch_url_text, item["url"], max_chars, attempts=2)
            except Exception:
                text = ""
            return {**item, "text": text}

        fetched = await asyncio.gather(*(fetch_one(item) for item in results))
        source_blocks = "\n\n".join(
            f"[{idx}] {item['title']}\nURL: {item['url']}\nSnippet: {item['snippet']}\nExtract: {item['text'][:max_chars]}"
            for idx, item in enumerate(fetched, start=1)
        )
        llm = create_llm()
        prompt = (
            "Create a useful research brief for an everyday user. Cite sources inline as [1], [2], etc. "
            "Include: executive answer, key findings, contradictions or uncertainty, recommended next actions, "
            "and a source list. Do not invent facts beyond the provided sources.\n\n"
            f"Topic: {topic}\nDepth: {depth}\n\nSources:\n{source_blocks}"
        )
        response = await retry_async(lambda: llm.ainvoke(prompt), attempts=2, base_delay=2)
        content = getattr(response, "content", str(response))

        slug = _slugify(output_name or topic)
        folder = RESEARCH_DIR / slug
        folder.mkdir(parents=True, exist_ok=True)
        payload = {
            "topic": topic,
            "depth": depth,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "sources": fetched,
        }
        (folder / "sources.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        brief_path = folder / "brief.md"
        brief_path.write_text(content, encoding="utf-8")
        return f"Research brief saved to {brief_path}\n\n{content}"
    except Exception as exc:
        return f"Research failed after retries: {format_exception(exc)}"
