from __future__ import annotations

import logging
import random
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)

INVALID_FILENAME_CHARS_PATTERN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
WHITESPACE_PATTERN = re.compile(r"\s+")
ATOM_NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


@dataclass(frozen=True)
class CrawlConfig:
    api_url: str
    user_agent: str
    pdf_dir: Path
    prefetch_cap: int
    rate_limit_seconds: float
    jitter_range: Tuple[float, float]
    max_retries: int
    retry_backoff: Tuple[float, ...]
    api_timeout: Tuple[float, float]
    min_pdf_size_bytes: int
    max_filename_length: int


class RateLimiter:
    """Simple rate limiter shared across API and PDF download calls."""

    def __init__(self, min_interval: float, jitter: Tuple[float, float]) -> None:
        self.min_interval = float(min_interval)
        self.jitter = jitter
        self._last_call = 0.0

    def wait(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        jitter = random.uniform(*self.jitter)
        time.sleep(jitter)
        self._last_call = time.monotonic()


def sanitize_component(value: str) -> str:
    value = value.strip()
    value = INVALID_FILENAME_CHARS_PATTERN.sub("", value)
    value = WHITESPACE_PATTERN.sub("-", value)
    value = re.sub(r"-+", "-", value)
    value = value.strip("-._")
    return value or "unknown"


def slugify_title(title: str, max_words: int = 8) -> str:
    cleaned = re.sub(r"[\t\r\n]+", " ", title)
    cleaned = cleaned.lower()
    cleaned = re.sub(r"[^\w\s-]", " ", cleaned, flags=re.UNICODE)
    parts = [part for part in cleaned.split() if part][:max_words]
    slug = "-".join(parts) if parts else "untitled"
    return sanitize_component(slug)


def enforce_filename_length(base_name: str, *, limit: int) -> str:
    if len(base_name) <= limit - 4:  # subtract ".pdf"
        return base_name
    ellipsis = "…"
    allowed = limit - 4 - len(ellipsis)
    if allowed <= 0:  # pragma: no cover - extreme safeguard
        return ellipsis
    truncated = base_name[:allowed].rstrip("-._") or base_name[:allowed]
    return truncated + ellipsis


def build_filename(
    *,
    year: int,
    arxiv_id_with_version: str,
    first_author: str,
    title: str,
    limit: int,
) -> str:
    base_name = f"{year}-{sanitize_component(arxiv_id_with_version)}-"
    base_name += f"{sanitize_component(first_author)}-{slugify_title(title)}"
    return enforce_filename_length(base_name, limit=limit) + ".pdf"


def extract_arxiv_ids(identifier: str) -> Tuple[str, str]:
    match = re.search(r"(\d{4}\.\d{4,5})(v\d+)?", identifier)
    if not match:
        raise ValueError(f"无法解析 arXiv ID: {identifier}")
    base_id = match.group(1)
    version = match.group(2) or "v1"
    return base_id, f"{base_id}{version}"


def find_existing_versions(pdf_dir: Path, base_id: str) -> Iterable[Path]:
    pattern = f"*-{base_id}v*.pdf"
    return pdf_dir.glob(pattern)


class ArxivCrawler:
    def __init__(self, config: CrawlConfig):
        self.config = config
        self.rate_limiter = RateLimiter(config.rate_limit_seconds, config.jitter_range)

    def request_with_retries(
        self,
        session: requests.Session,
        method: str,
        url: str,
        *,
        stream: bool = False,
        acceptable_status: Iterable[int] = (200,),
        **kwargs,
    ) -> requests.Response:
        last_error: Optional[Exception] = None
        for attempt in range(self.config.max_retries):
            try:
                self.rate_limiter.wait()
                response = session.request(
                    method,
                    url,
                    timeout=self.config.api_timeout,
                    stream=stream,
                    **kwargs,
                )
            except requests.RequestException as exc:  # pragma: no cover - network failure
                last_error = exc
            else:
                if response.status_code in acceptable_status:
                    return response
                if response.status_code not in {429, 500, 502, 503, 504}:
                    response.raise_for_status()
                last_error = requests.HTTPError(f"Unexpected status {response.status_code}")
                response.close()
            backoff = self.config.retry_backoff[min(attempt, len(self.config.retry_backoff) - 1)]
            time.sleep(backoff)
        if last_error:
            raise last_error
        raise RuntimeError(f"请求 {url} 失败")

    def fetch_arxiv_entries(self, session: requests.Session, keywords: str, max_results: int) -> List[Dict[str, object]]:
        params = {
            "search_query": f"all:{keywords}",
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        query_url = f"{self.config.api_url}?{urlencode(params)}"
        logger.info("请求 arXiv API: %s", query_url)
        response = self.request_with_retries(session, "GET", query_url)
        try:
            text = response.text
        finally:
            response.close()
        return parse_atom_feed(text)

    def download_pdf(self, session: requests.Session, pdf_url: str, destination: Path) -> requests.Response:
        logger.info("下载 PDF: %s -> %s", pdf_url, destination)
        return self.request_with_retries(session, "GET", pdf_url, stream=True)

    def process_entry(self, session: requests.Session, entry: Dict[str, object]) -> Dict[str, object]:
        base_id: str = entry["base_id"]  # type: ignore[assignment]
        id_with_version: str = entry["id_with_version"]  # type: ignore[assignment]
        published: datetime = entry["published"]  # type: ignore[assignment]
        authors: List[str] = entry["authors"]  # type: ignore[assignment]
        pdf_url: str = entry["pdf_url"]  # type: ignore[assignment]

        first_author = authors[0] if authors else "unknown"
        filename = build_filename(
            year=published.year,
            arxiv_id_with_version=id_with_version,
            first_author=first_author,
            title=entry["title"],  # type: ignore[arg-type]
            limit=self.config.max_filename_length,
        )
        file_path = self.config.pdf_dir / filename
        relative_path = str(Path("pdf_files") / filename)

        if file_path.exists():
            if file_path.stat().st_size > self.config.min_pdf_size_bytes:
                logger.info("跳过已存在文件: %s", file_path)
                return {
                    "title": entry["title"],
                    "arxiv_id": base_id,
                    "id_with_version": id_with_version,
                    "status": "already_exists",
                    "file_name": filename,
                    "relative_path": relative_path,
                    "reason": None,
                }
            logger.warning("删除不完整文件，准备重新下载: %s", file_path)
            file_path.unlink(missing_ok=True)

        existing_versions = [p for p in find_existing_versions(self.config.pdf_dir, base_id) if p.name != filename]
        temp_path = file_path.with_suffix(".part")

        try:
            response = self.download_pdf(session, pdf_url, file_path)
            try:
                content_type = response.headers.get("Content-Type", "").lower()
                if "pdf" not in content_type:
                    raise ValueError(f"返回类型异常: {content_type}")
                with temp_path.open("wb") as handle:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            handle.write(chunk)
            finally:
                response.close()
            if not temp_path.exists() or temp_path.stat().st_size <= self.config.min_pdf_size_bytes:
                raise ValueError("下载的文件大小异常")
            temp_path.replace(file_path)
            for old_path in existing_versions:
                if old_path.exists() and old_path != file_path:
                    logger.info("删除旧版本: %s", old_path)
                    old_path.unlink()
            status = "replaced_old_version" if existing_versions else "downloaded"
            return {
                "title": entry["title"],
                "arxiv_id": base_id,
                "id_with_version": id_with_version,
                "status": status,
                "file_name": filename,
                "relative_path": relative_path,
                "reason": None,
            }
        except Exception as exc:  # pragma: no cover - network dependent
            logger.exception("下载或写入 PDF 失败: %s", pdf_url)
            temp_path.unlink(missing_ok=True)
            return {
                "title": entry["title"],
                "arxiv_id": base_id,
                "id_with_version": id_with_version,
                "status": "failed",
                "file_name": None,
                "relative_path": None,
                "reason": str(exc),
            }

    def summarize_results(self, results: List[Dict[str, object]]) -> Dict[str, int]:
        summary = {
            "total": len(results),
            "downloaded": 0,
            "already_exists": 0,
            "replaced_old_version": 0,
            "failed": 0,
        }
        for item in results:
            status = item.get("status")
            if status in summary:
                summary[status] += 1
        return summary

    def crawl(self, *, keywords: str, year_range: tuple[int, int], max_num: int) -> Dict[str, object]:
        self.config.pdf_dir.mkdir(parents=True, exist_ok=True)
        prefetch_count = min(self.config.prefetch_cap, max_num * 3 if max_num > 0 else 1)
        session = requests.Session()
        session.headers.update({"User-Agent": self.config.user_agent})

        try:
            try:
                entries = self.fetch_arxiv_entries(session, keywords, prefetch_count)
            except Exception as exc:
                logger.exception("arXiv API 请求失败")
                return {
                    "success": False,
                    "error": f"arXiv API 调用失败: {exc}",
                }

            filtered_entries = [
                entry for entry in entries if year_range[0] <= entry["published"].year <= year_range[1]
            ]
            selected_entries = filtered_entries[:max_num]

            results: List[Dict[str, object]] = []
            for entry in selected_entries:
                result = self.process_entry(session, entry)
                results.append(result)

            summary = self.summarize_results(results)
            response_payload = {
                "success": True,
                "results": results,
                "summary": summary,
                "requested": {
                    "keywords": keywords,
                    "year_range": f"{year_range[0]}-{year_range[1]}",
                    "max_num": max_num,
                    "prefetch_count": prefetch_count,
                    "total_found": len(filtered_entries),
                },
                "storage": {
                    "pdf_dir": str(self.config.pdf_dir),
                },
            }
            return response_payload
        finally:
            session.close()


def parse_atom_feed(xml_text: str) -> List[Dict[str, object]]:
    root = ET.fromstring(xml_text)
    entries: List[Dict[str, object]] = []
    for entry_elem in root.findall("atom:entry", ATOM_NAMESPACES):
        identifier = entry_elem.findtext("atom:id", default="", namespaces=ATOM_NAMESPACES)
        if not identifier:
            continue
        try:
            base_id, id_with_version = extract_arxiv_ids(identifier)
        except ValueError:
            logger.warning("跳过无法解析ID的条目: %s", identifier)
            continue
        title = entry_elem.findtext("atom:title", default="", namespaces=ATOM_NAMESPACES).strip()
        published_text = entry_elem.findtext("atom:published", default="", namespaces=ATOM_NAMESPACES)
        updated_text = entry_elem.findtext("atom:updated", default="", namespaces=ATOM_NAMESPACES)
        try:
            published_dt = datetime.fromisoformat(published_text.replace("Z", "+00:00"))
        except ValueError:
            logger.warning("跳过无效发布时间的条目: %s", published_text)
            continue
        try:
            updated_dt = datetime.fromisoformat(updated_text.replace("Z", "+00:00"))
        except ValueError:
            updated_dt = published_dt
        authors = [
            author_elem.findtext("atom:name", default="", namespaces=ATOM_NAMESPACES).strip()
            for author_elem in entry_elem.findall("atom:author", ATOM_NAMESPACES)
        ]
        pdf_url = None
        for link_elem in entry_elem.findall("atom:link", ATOM_NAMESPACES):
            if link_elem.get("type") == "application/pdf":
                pdf_url = link_elem.get("href")
                break
        if not pdf_url:
            pdf_url = f"https://arxiv.org/pdf/{id_with_version}.pdf"
        entries.append(
            {
                "base_id": base_id,
                "id_with_version": id_with_version,
                "title": title,
                "authors": authors,
                "published": published_dt,
                "updated": updated_dt,
                "pdf_url": pdf_url,
            }
        )
    return entries


def build_crawl_config(app_config: Mapping[str, object], *, pdf_dir: Path | None = None) -> CrawlConfig:
    return CrawlConfig(
        api_url=str(app_config["ARXIV_API_URL"]),
        user_agent=str(app_config["USER_AGENT"]),
        pdf_dir=Path(pdf_dir) if pdf_dir else Path(app_config["PDF_DIR"]),
        prefetch_cap=int(app_config["PRE_FETCH_CAP"]),
        rate_limit_seconds=float(app_config["RATE_LIMIT_SECONDS"]),
        jitter_range=tuple(app_config["JITTER_RANGE"]),
        max_retries=int(app_config["MAX_RETRIES"]),
        retry_backoff=tuple(app_config["RETRY_BACKOFF"]),
        api_timeout=tuple(app_config["API_TIMEOUT"]),
        min_pdf_size_bytes=int(app_config["MIN_PDF_SIZE_BYTES"]),
        max_filename_length=int(app_config["MAX_FILENAME_LENGTH"]),
    )


def crawl_papers(
    *,
    keywords: str,
    year_range: tuple[int, int],
    max_num: int,
    app_config: Mapping[str, object],
    pdf_dir: Path | None = None,
) -> Dict[str, object]:
    crawl_config = build_crawl_config(app_config, pdf_dir=pdf_dir)
    crawler = ArxivCrawler(crawl_config)
    return crawler.crawl(keywords=keywords, year_range=year_range, max_num=max_num)


def crawl_with_keyword_list(
    *,
    keyword_list: Sequence[str],
    year_range: tuple[int, int],
    max_num: int,
    app_config: Mapping[str, object],
    pdf_dir: Path | None = None,
) -> Dict[str, object]:
    keyword_list = [keyword.strip() for keyword in keyword_list if keyword.strip()]
    if not keyword_list:
        return {
            "success": False,
            "error": "未提供有效关键词",
            "results": [],
            "summary": {"total": 0, "downloaded": 0, "already_exists": 0, "replaced_old_version": 0, "failed": 0},
            "generated_keywords": [],
        }

    crawl_config = build_crawl_config(app_config, pdf_dir=pdf_dir)
    crawler = ArxivCrawler(crawl_config)

    aggregated_results: List[Dict[str, object]] = []
    seen_ids: Set[str] = set()
    failures: List[str] = []

    for keyword in keyword_list:
        remaining = max(max_num - len(aggregated_results), 0) if max_num else 0
        if max_num and remaining <= 0:
            break
        response = crawler.crawl(
            keywords=keyword,
            year_range=year_range,
            max_num=remaining or max_num,
        )
        if not response.get("success"):
            failure_reason = response.get("error") or "关键字检索失败"
            failures.append(f"{keyword}: {failure_reason}")
            continue
        for item in response.get("results", []):
            unique_id = str(item.get("id_with_version") or item.get("file_name") or item.get("title"))
            if unique_id in seen_ids:
                continue
            seen_ids.add(unique_id)
            aggregated_results.append(item)
        if max_num and len(aggregated_results) >= max_num:
            break

    summary = crawler.summarize_results(aggregated_results)
    storage = {"pdf_dir": str(crawler.config.pdf_dir)}

    success = bool(aggregated_results)
    error_message = "; ".join(failures) if failures else None

    return {
        "success": success,
        "error": error_message,
        "results": aggregated_results,
        "summary": summary,
        "generated_keywords": list(keyword_list),
        "storage": storage,
    }
