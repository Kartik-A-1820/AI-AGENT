import json
import re
from collections import Counter
from typing import Any

from assistant_state import load_knowledge_graph, now_iso, save_knowledge_graph
from async_utils import retry_async
from llm_config import create_llm


MAX_EVIDENCE_PER_ITEM = 4
MAX_NODES = 400
MAX_EDGES = 900
STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "and",
    "are",
    "because",
    "before",
    "can",
    "could",
    "for",
    "from",
    "have",
    "how",
    "into",
    "need",
    "not",
    "that",
    "the",
    "this",
    "use",
    "using",
    "was",
    "what",
    "when",
    "with",
    "you",
    "your",
}


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized[:80] or "unknown"


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_-]{2,}", text.lower())
        if token not in STOPWORDS
    }


def _is_displayable_text(value: str) -> bool:
    text = str(value)
    if not text:
        return False
    return all(ord(char) < 128 for char in text)


def _trim_evidence(items: list[str]) -> list[str]:
    compact = []
    for item in items:
        clean = re.sub(r"\s+", " ", str(item)).strip()
        if clean and clean not in compact:
            compact.append(clean[:260])
    return compact[-MAX_EVIDENCE_PER_ITEM:]


def _coerce_confidence(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.7


def _upsert_node(graph: dict[str, Any], name: str, node_type: str = "concept", evidence: str = "") -> str:
    clean_name = re.sub(r"\s+", " ", str(name)).strip()
    if not clean_name:
        return ""
    node_id = _slug(clean_name)
    nodes = graph.setdefault("nodes", {})
    node = nodes.get(
        node_id,
        {
            "id": node_id,
            "name": clean_name[:120],
            "type": node_type or "concept",
            "salience": 0,
            "first_seen": now_iso(),
            "last_seen": "",
            "evidence": [],
        },
    )
    existing_type = node.get("type") or "concept"
    node["name"] = node.get("name") or clean_name[:120]
    node["type"] = existing_type if node_type == "concept" and existing_type != "concept" else (node_type or existing_type)
    node["salience"] = int(node.get("salience", 0)) + 1
    node["last_seen"] = now_iso()
    if evidence:
        node["evidence"] = _trim_evidence([*node.get("evidence", []), evidence])
    nodes[node_id] = node
    return node_id


def add_graph_fact(
    subject: str,
    relation: str,
    object_value: str,
    subject_type: str = "concept",
    object_type: str = "concept",
    evidence: str = "",
    confidence: float = 0.8,
) -> dict[str, Any]:
    """Store one local knowledge graph fact and return the updated edge."""
    graph = load_knowledge_graph()
    source_id = _upsert_node(graph, subject, subject_type, evidence)
    target_id = _upsert_node(graph, object_value, object_type, evidence)
    clean_relation = re.sub(r"[^a-zA-Z0-9_ -]+", "", relation).strip().lower().replace(" ", "_")
    if not source_id or not target_id or not clean_relation:
        raise ValueError("subject, relation, and object_value are required")

    edges = graph.setdefault("edges", [])
    for edge in edges:
        if edge.get("source") == source_id and edge.get("target") == target_id and edge.get("relation") == clean_relation:
            edge["confidence"] = max(_coerce_confidence(edge.get("confidence")), _coerce_confidence(confidence))
            edge["last_seen"] = now_iso()
            edge["evidence"] = _trim_evidence([*edge.get("evidence", []), evidence])
            save_knowledge_graph(_prune_graph(graph))
            return edge

    edge = {
        "source": source_id,
        "target": target_id,
        "relation": clean_relation,
        "confidence": _coerce_confidence(confidence),
        "first_seen": now_iso(),
        "last_seen": now_iso(),
        "evidence": _trim_evidence([evidence]),
    }
    edges.append(edge)
    save_knowledge_graph(_prune_graph(graph))
    return edge


def _prune_graph(graph: dict[str, Any]) -> dict[str, Any]:
    nodes = graph.get("nodes", {})
    if len(nodes) > MAX_NODES:
        keep = {
            node_id
            for node_id, _node in sorted(
                nodes.items(),
                key=lambda item: (int(item[1].get("salience", 0)), item[1].get("last_seen", "")),
                reverse=True,
            )[:MAX_NODES]
        }
        graph["nodes"] = {node_id: node for node_id, node in nodes.items() if node_id in keep}
        graph["edges"] = [
            edge
            for edge in graph.get("edges", [])
            if edge.get("source") in keep and edge.get("target") in keep
        ]
    if len(graph.get("edges", [])) > MAX_EDGES:
        graph["edges"] = sorted(
            graph["edges"],
            key=lambda edge: (_coerce_confidence(edge.get("confidence")), edge.get("last_seen", "")),
            reverse=True,
        )[:MAX_EDGES]
    return graph


def query_graph(query: str, limit: int = 8) -> dict[str, Any]:
    graph = load_knowledge_graph()
    query_tokens = _tokens(query)
    nodes = graph.get("nodes", {})
    node_scores: Counter[str] = Counter()

    for node_id, node in nodes.items():
        haystack = " ".join([node.get("name", ""), node.get("type", ""), *node.get("evidence", [])])
        overlap = query_tokens & _tokens(haystack)
        if overlap:
            node_scores[node_id] += len(overlap) * 3 + int(node.get("salience", 0))

    for edge in graph.get("edges", []):
        source = nodes.get(edge.get("source"), {})
        target = nodes.get(edge.get("target"), {})
        haystack = " ".join(
            [
                source.get("name", ""),
                edge.get("relation", ""),
                target.get("name", ""),
                *edge.get("evidence", []),
            ]
        )
        overlap = query_tokens & _tokens(haystack)
        if overlap:
            score = len(overlap) * 4 + int(10 * _coerce_confidence(edge.get("confidence")))
            node_scores[edge.get("source", "")] += score
            node_scores[edge.get("target", "")] += score

    ranked_node_ids = [node_id for node_id, _score in node_scores.most_common(max(limit, 1))]
    if not ranked_node_ids and nodes:
        ranked_node_ids = [
            node_id
            for node_id, _node in sorted(
                nodes.items(),
                key=lambda item: (int(item[1].get("salience", 0)), item[1].get("last_seen", "")),
                reverse=True,
            )[: max(limit, 1)]
        ]
    selected = set(ranked_node_ids)
    edges = [
        edge
        for edge in graph.get("edges", [])
        if edge.get("source") in selected or edge.get("target") in selected
    ][: max(limit * 2, 1)]
    return {
        "nodes": [nodes[node_id] for node_id in ranked_node_ids if node_id in nodes],
        "edges": edges,
        "updated_at": graph.get("updated_at", ""),
    }


def format_graph_context(query: str, limit: int = 8, max_chars: int = 1800) -> str:
    result = query_graph(query, limit=limit)
    nodes = {node["id"]: node for node in result["nodes"]}
    if not nodes:
        return "No relevant local knowledge graph context yet."

    all_nodes = load_knowledge_graph().get("nodes", {})
    lines = ["Relevant local knowledge graph context:"]
    for node in result["nodes"]:
        if not _is_displayable_text(node.get("name", "")):
            continue
        evidence = "; ".join(item for item in node.get("evidence", [])[-2:] if _is_displayable_text(item))
        detail = f" - {node.get('name')} ({node.get('type', 'concept')})"
        if evidence:
            detail += f": {evidence}"
        lines.append(detail)

    for edge in result["edges"]:
        source = nodes.get(edge.get("source")) or all_nodes.get(edge.get("source"), {})
        target = nodes.get(edge.get("target")) or all_nodes.get(edge.get("target"), {})
        if source and target and _is_displayable_text(source.get("name", "")) and _is_displayable_text(target.get("name", "")):
            lines.append(
                f" - {source.get('name')} {edge.get('relation')} {target.get('name')} "
                f"(confidence {edge.get('confidence', 0.7)})"
            )

    text = "\n".join(lines)
    return text[:max_chars]


def _extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, flags=re.DOTALL)
    if fenced:
        stripped = fenced.group(1)
    else:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            stripped = stripped[start : end + 1]
    return json.loads(stripped)


def _fallback_extract(text: str) -> dict[str, Any]:
    candidates = []
    for match in re.finditer(r"\b([A-Z][A-Za-z0-9_-]*(?:\s+[A-Z][A-Za-z0-9_-]*){0,3})\b", text):
        name = match.group(1).strip()
        if len(name) > 2 and name.lower() not in STOPWORDS:
            candidates.append(name)
    unique = list(dict.fromkeys(candidates))[:8]
    return {
        "nodes": [{"name": name, "type": "concept", "evidence": text[:240]} for name in unique],
        "edges": [],
    }


async def extract_graph_updates_async(user_input: str, assistant_response: str) -> dict[str, Any]:
    transcript = f"User:\n{user_input}\n\nAssistant:\n{assistant_response}"
    instruction = """
Extract durable memory for a local personal assistant knowledge graph.
Only include stable user preferences, projects, people, tools, recurring facts, decisions, and useful context.
Ignore transient wording, secrets, API keys, one-time command output, and unsafe disk-management details.
Use English labels and relations, even if the transcript contains mixed-language text.
Return strict JSON with:
{
  "nodes": [{"name": "...", "type": "person|project|preference|tool|service|task|concept", "evidence": "..."}],
  "edges": [{"source": "...", "relation": "prefers|uses|works_on|related_to|decided|needs|avoids", "target": "...", "confidence": 0.0-1.0, "evidence": "..."}]
}
Keep it small: at most 8 nodes and 10 edges.
"""
    try:
        llm = create_llm()
        response = await retry_async(
            lambda: llm.ainvoke(f"{instruction}\n\nTranscript:\n{transcript[:6000]}"),
            attempts=2,
            base_delay=1,
        )
        payload = _extract_json_object(str(response.content))
    except Exception:
        payload = _fallback_extract(transcript)
    return payload


def apply_graph_updates(payload: dict[str, Any]) -> int:
    graph = load_knowledge_graph()
    count = 0
    for node in payload.get("nodes", [])[:12]:
        if isinstance(node, dict) and node.get("name"):
            _upsert_node(graph, node["name"], node.get("type", "concept"), node.get("evidence", ""))
            count += 1

    for edge in payload.get("edges", [])[:16]:
        if not isinstance(edge, dict):
            continue
        try:
            source_id = _upsert_node(graph, edge.get("source", ""), "concept", edge.get("evidence", ""))
            target_id = _upsert_node(graph, edge.get("target", ""), "concept", edge.get("evidence", ""))
            relation = re.sub(r"[^a-zA-Z0-9_ -]+", "", str(edge.get("relation", "related_to"))).strip()
            if source_id and target_id and relation:
                graph.setdefault("edges", []).append(
                    {
                        "source": source_id,
                        "target": target_id,
                        "relation": relation.lower().replace(" ", "_"),
                        "confidence": _coerce_confidence(edge.get("confidence")),
                        "first_seen": now_iso(),
                        "last_seen": now_iso(),
                        "evidence": _trim_evidence([edge.get("evidence", "")]),
                    }
                )
                count += 1
        except (TypeError, ValueError):
            continue

    graph = _dedupe_edges(_prune_graph(graph))
    save_knowledge_graph(graph)
    return count


def _dedupe_edges(graph: dict[str, Any]) -> dict[str, Any]:
    deduped = {}
    for edge in graph.get("edges", []):
        key = (edge.get("source"), edge.get("relation"), edge.get("target"))
        existing = deduped.get(key)
        if not existing:
            deduped[key] = edge
            continue
        existing["confidence"] = max(
            _coerce_confidence(existing.get("confidence")),
            _coerce_confidence(edge.get("confidence")),
        )
        existing["last_seen"] = max(str(existing.get("last_seen", "")), str(edge.get("last_seen", "")))
        existing["evidence"] = _trim_evidence([*existing.get("evidence", []), *edge.get("evidence", [])])
    graph["edges"] = list(deduped.values())
    return graph


async def update_graph_from_interaction_async(user_input: str, assistant_response: str) -> int:
    payload = await extract_graph_updates_async(user_input, assistant_response)
    return apply_graph_updates(payload)
