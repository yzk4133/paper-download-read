from __future__ import annotations

"""Large-language-model helpers for keyword generation and structured summaries."""

import json
import logging
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Iterable, List, Optional, Sequence

from dotenv import load_dotenv

try:  # pragma: no cover - optional dependency
    from langchain_openai import ChatOpenAI
except ImportError:  # pragma: no cover - handled gracefully at runtime
    ChatOpenAI = None  # type: ignore


load_dotenv()

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
_FIELD_CHAR_LIMIT = int(os.getenv("PARSE_FIELD_CHAR_LIMIT", "50"))
_DEFAULT_KEYWORD_COUNT = int(os.getenv("SUGGEST_KEYWORD_COUNT", "5"))


@dataclass(frozen=True)
class SectionPattern:
    name: str
    keywords: Iterable[str]
    max_sentences: int = 3


SECTION_PATTERNS: Sequence[SectionPattern] = (
    SectionPattern("innovation", ("innovation", "novel", "contribution", "breakthrough"), 2),
    SectionPattern("method", ("method", "approach", "architecture", "experiment"), 2),
    SectionPattern("conclusion", ("conclusion", "result", "finding", "future"), 2),
)

SENTENCE_PATTERN = re.compile(r"(?<=[.!?。！？])\s+")
WHITESPACE_PATTERN = re.compile(r"\s+")
JSON_BLOCK_PATTERN = re.compile(r"\{[\s\S]*\}")


def _truncate(value: str, limit: int = _FIELD_CHAR_LIMIT) -> str:
    if not value:
        return ""
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def _split_paragraphs(text: str) -> List[str]:
    raw = re.split(r"\n{2,}", text)
    return [paragraph.strip() for paragraph in raw if paragraph.strip()]


def _find_paragraph(paragraphs: Sequence[str], keywords: Iterable[str]) -> str:
    best = ""
    best_score = 0
    for paragraph in paragraphs:
        lowered = paragraph.lower()
        score = sum(1 for keyword in keywords if keyword in lowered)
        if score > best_score:
            best = paragraph
            best_score = score
            if score >= 2:
                break
    return best


def _take_sentences(text: str, *, limit: int) -> str:
    if not text:
        return ""
    sentences = SENTENCE_PATTERN.split(text)
    cleaned = [WHITESPACE_PATTERN.sub(" ", sentence.strip()) for sentence in sentences if sentence.strip()]
    combined = " ".join(cleaned[:limit])
    return _truncate(combined, 240)


def _heuristic_summary(text: str) -> Dict[str, str]:
    cleaned = text.strip()
    if not cleaned:
        return {
            "innovation": "未能从 PDF 提取文本内容。",
            "method": "",
            "conclusion": "",
            "summary": "",
        }

    paragraphs = _split_paragraphs(cleaned) or [cleaned]
    summary = _take_sentences(paragraphs[0], limit=2)

    result: Dict[str, str] = {}
    for pattern in SECTION_PATTERNS:
        paragraph = _find_paragraph(paragraphs, pattern.keywords)
        content = _take_sentences(paragraph or summary, limit=pattern.max_sentences)
        result[pattern.name] = _truncate(content)
    result["summary"] = _truncate(summary)
    return result


def _extract_json_block(text: str) -> Optional[str]:
    if not text:
        return None
    match = JSON_BLOCK_PATTERN.search(text)
    if match:
        return match.group(0)
    return None


def _load_json_fields(raw_text: str) -> Optional[Dict[str, str]]:
    block = _extract_json_block(raw_text) or raw_text
    try:
        parsed = json.loads(block)
    except json.JSONDecodeError:
        logger.debug("无法解析 LLM 返回的 JSON，返回原始文本", exc_info=True)
        return None
    if not isinstance(parsed, dict):
        return None
    return {str(key): str(value) for key, value in parsed.items() if isinstance(value, (str, int, float))}


def _get_llm_config() -> Dict[str, object]:
    api_key = os.getenv("TONGYI_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("TONGYI_BASE_URL") or os.getenv("OPENAI_BASE_URL") or _DEFAULT_BASE_URL
    model = os.getenv("TONGYI_LLM_MODEL") or os.getenv("OPENAI_LLM_MODEL") or "qwen-turbo"
    temperature = float(os.getenv("TONGYI_LLM_TEMPERATURE") or os.getenv("TEMPERATURE") or 0)
    max_tokens = int(os.getenv("TONGYI_LLM_MAX_TOKENS") or os.getenv("MAX_TOKENS") or 512)
    return {
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }


@lru_cache(maxsize=1)
def _build_llm() -> Optional[object]:
    if ChatOpenAI is None:
        logger.warning("未安装 langchain-openai，解析将退回启发式逻辑。")
        return None

    config = _get_llm_config()
    api_key = config["api_key"]
    if not api_key:
        logger.warning("未配置 TONGYI_API_KEY，解析将退回启发式逻辑。")
        return None

    try:
        return ChatOpenAI(
            model=str(config["model"]),
            api_key=str(api_key),
            base_url=str(config["base_url"]),
            temperature=float(config["temperature"]),
            max_tokens=int(config["max_tokens"]),
        )
    except Exception:  # pragma: no cover - depends on external SDK
        logger.exception("初始化通义千问 LLM 失败，将使用启发式解析。")
        return None


def _normalize_sections(fields: Dict[str, str]) -> Dict[str, str]:
    normalized = {
        "innovation": _truncate(fields.get("innovation") or fields.get("创新点") or ""),
        "method": _truncate(fields.get("method") or fields.get("方法") or fields.get("试验方法") or ""),
        "conclusion": _truncate(fields.get("conclusion") or fields.get("结论") or ""),
    }
    for key in normalized:
        if not normalized[key]:
            normalized[key] = ""
    return normalized


SUMMARY_PROMPT = (
    "你是一名科研助手，请阅读给定论文文本，提取‘创新点’、‘试验方法’、‘结论’三项摘要。"
    "每个字段不超过 200 个汉字，如果信息缺失请输出‘暂无信息’。"
    "请严格返回 JSON 对象，键包含 innovation, method, conclusion，值为字符串。"
)


def analyze_paper(text: str) -> Dict[str, str]:
    cleaned = text.strip()
    if not cleaned:
        return {
            "innovation": "未能从 PDF 提取文本内容。",
            "method": "",
            "conclusion": "",
            "summary": "",
        }

    llm = _build_llm()
    if llm is None:
        return _heuristic_summary(cleaned)

    try:
        prompt = (
            f"{SUMMARY_PROMPT}\n\n"
            "论文正文如下：\n"
            "---\n"
            f"{cleaned[:8000]}\n"
            "---"
        )
        response = llm.invoke(prompt)
        raw_text = getattr(response, "content", "") or ""
        fields = _load_json_fields(raw_text)
        if not fields:
            logger.warning("LLM 返回非结构化内容，使用启发式备选。")
            return _heuristic_summary(cleaned)
        normalized = _normalize_sections(fields)
        # 回退缺失字段
        for key, fallback_pattern in (
            ("innovation", SECTION_PATTERNS[0]),
            ("method", SECTION_PATTERNS[1]),
            ("conclusion", SECTION_PATTERNS[2]),
        ):
            if not normalized.get(key):
                paragraph = _find_paragraph(_split_paragraphs(cleaned), fallback_pattern.keywords)
                normalized[key] = _truncate(_take_sentences(paragraph, limit=fallback_pattern.max_sentences)) or "暂无信息"
        normalized["summary"] = normalized.get("conclusion") or normalized.get("method") or normalized.get("innovation")
        return normalized
    except Exception:  # pragma: no cover - network / SDK failure
        logger.exception("调用通义千问失败，使用启发式解析。")
        return _heuristic_summary(cleaned)


KEYWORD_PROMPT_TEMPLATE = (
    "请基于以下研究需求生成 {count} 个英文检索关键词，每个关键词 1-3 个单词。"
    "输出 JSON 数组，例如 [\"keyword1\", \"keyword2\"...]。"
    "如果很难满足数量，请尽量输出可行的关键词。"
)


def suggest_keywords(description: str, *, count: int | None = None) -> List[str]:
    cleaned = (description or "").strip()
    if not cleaned:
        return []
    desired_count = max(1, count or _DEFAULT_KEYWORD_COUNT)
    llm = _build_llm()
    if llm is None:
        return suggest_keywords_without_llm(cleaned, limit=desired_count)

    try:
        prompt = KEYWORD_PROMPT_TEMPLATE.format(count=desired_count) + f"\n\n需求描述：\n{cleaned}"
        response = llm.invoke(prompt)
        raw_text = getattr(response, "content", "") or ""
        block = _extract_json_block(raw_text) or raw_text
        keywords = json.loads(block)
        if isinstance(keywords, list):
            result: List[str] = []
            for item in keywords:
                if not isinstance(item, str):
                    continue
                token = item.strip()
                if token and token.lower() not in {k.lower() for k in result}:
                    result.append(token)
                if len(result) >= desired_count:
                    break
            return result
    except Exception:  # pragma: no cover - network / SDK failure
        logger.exception("调用通义千问生成关键词失败，使用启发式备选。")
    return suggest_keywords_without_llm(cleaned, limit=desired_count)


def suggest_keywords_without_llm(description: str, *, limit: int) -> List[str]:
    tokens = re.split(r"[^A-Za-z0-9+#]+", description)
    keywords: List[str] = []
    for token in tokens:
        cleaned = token.strip().lower()
        if len(cleaned) < 3:
            continue
        if cleaned not in keywords:
            keywords.append(cleaned)
        if len(keywords) >= limit:
            break
    return keywords[:limit]
