import logging
import random
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlencode

import requests
from flask import Flask, jsonify, render_template, request
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ARXIV_API_URL = "https://export.arxiv.org/api/query"
USER_AGENT = "ArXivMiniDownloader/1.0 (local)"
DOWNLOAD_DIR = Path(__file__).resolve().parent / "pdf_files"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
DEFAULT_MAX_NUM = 5
MAX_ALLOWED_NUM = 10
PRE_FETCH_CAP = 100
RATE_LIMIT_SECONDS = 1.0
JITTER_RANGE = (0.1, 0.3)
MAX_RETRIES = 3
RETRY_BACKOFF = [0.5, 1.0, 2.0]
API_TIMEOUT = (10, 30)
MIN_PDF_SIZE_BYTES = 10 * 1024
MAX_FILENAME_LENGTH = 120
ELLIPSIS = "…"

INVALID_FILENAME_CHARS_PATTERN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
WHITESPACE_PATTERN = re.compile(r"\s+")
YEAR_RANGE_PATTERN = re.compile(r"^\s*(\d{4})\s*-\s*(\d{4})\s*$")
ATOM_NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------
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


def ensure_directories() -> None:
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)


def get_default_year_range() -> Tuple[int, int]:
    current_year = datetime.now().year
    return current_year - 1, current_year


def parse_year_range(raw_value: Optional[str]) -> Tuple[int, int]:
    if not raw_value:
        return get_default_year_range()
    match = YEAR_RANGE_PATTERN.match(raw_value)
    if not match:
        raise ValueError("年份范围格式应为YYYY-YYYY")
    start_year, end_year = map(int, match.groups())
    if start_year > end_year:
        raise ValueError("年份范围起始值不能大于结束值")
    return start_year, end_year


def clamp_max_num(raw_value: Optional[str]) -> int:
    if not raw_value:
        return DEFAULT_MAX_NUM
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        raise ValueError("最大数量必须是整数")
    return max(1, min(MAX_ALLOWED_NUM, value))


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
    parts = [part for part in cleaned.split() if part]
    parts = parts[:max_words]
    slug = "-".join(parts) if parts else "untitled"
    return sanitize_component(slug)


def build_filename(year: int, arxiv_id_with_version: str, first_author: str, title: str) -> str:
    year_part = str(year)
    id_part = sanitize_component(arxiv_id_with_version)
    author_part = sanitize_component(first_author)
    title_part = slugify_title(title)
    base_name = f"{year_part}-{id_part}-{author_part}-{title_part}"
    return enforce_filename_length(base_name) + ".pdf"


def enforce_filename_length(base_name: str) -> str:
    if len(base_name) <= MAX_FILENAME_LENGTH - 4:  # subtract ".pdf"
        return base_name
    allowed = MAX_FILENAME_LENGTH - 4 - len(ELLIPSIS)
    if allowed <= 0:
        return ELLIPSIS
    truncated = base_name[:allowed].rstrip("-._")
    if not truncated:
        truncated = base_name[:allowed]
    return truncated + ELLIPSIS


def extract_arxiv_ids(identifier: str) -> Tuple[str, str]:
    match = re.search(r"(\d{4}\.\d{4,5})(v\d+)?", identifier)
    if not match:
        raise ValueError(f"无法解析 arXiv ID: {identifier}")
    base_id = match.group(1)
    version = match.group(2) or "v1"
    return base_id, f"{base_id}{version}"


def find_existing_versions(base_id: str) -> Iterable[Path]:
    pattern = f"*-{base_id}v*.pdf"
    return DOWNLOAD_DIR.glob(pattern)


rate_limiter = RateLimiter(RATE_LIMIT_SECONDS, JITTER_RANGE)


def request_with_retries(session: requests.Session, method: str, url: str, *, stream: bool = False,
                         acceptable_status: Iterable[int] = (200,), **kwargs) -> requests.Response:
    last_error: Optional[Exception] = None
    for attempt in range(MAX_RETRIES):
        try:
            rate_limiter.wait()
            response = session.request(method, url, timeout=API_TIMEOUT, stream=stream, **kwargs)
        except requests.RequestException as exc:
            last_error = exc
        else:
            if response.status_code in acceptable_status:
                return response
            if response.status_code not in {429, 500, 502, 503, 504}:
                response.raise_for_status()
            last_error = requests.HTTPError(f"Unexpected status {response.status_code}")
            response.close()
        backoff = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
        time.sleep(backoff)
    if last_error:
        raise last_error
    raise RuntimeError(f"请求 {url} 失败")


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
            logging.warning("跳过无法解析ID的条目: %s", identifier)
            continue
        title = entry_elem.findtext("atom:title", default="", namespaces=ATOM_NAMESPACES).strip()
        published_text = entry_elem.findtext("atom:published", default="", namespaces=ATOM_NAMESPACES)
        updated_text = entry_elem.findtext("atom:updated", default="", namespaces=ATOM_NAMESPACES)
        try:
            published_dt = datetime.fromisoformat(published_text.replace("Z", "+00:00"))
        except ValueError:
            logging.warning("跳过无效发布时间的条目: %s", published_text)
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


def fetch_arxiv_entries(session: requests.Session, keywords: str, max_results: int) -> List[Dict[str, object]]:
    params = {
        "search_query": f"all:{keywords}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    query_url = f"{ARXIV_API_URL}?{urlencode(params)}"
    logging.info("请求 arXiv API: %s", query_url)
    response = request_with_retries(session, "GET", query_url)
    try:
        text = response.text
    finally:
        response.close()
    return parse_atom_feed(text)


def download_pdf(session: requests.Session, pdf_url: str, destination: Path) -> requests.Response:
    logging.info("下载 PDF: %s -> %s", pdf_url, destination)
    response = request_with_retries(session, "GET", pdf_url, stream=True)
    return response


def process_entry(session: requests.Session, entry: Dict[str, object]) -> Dict[str, object]:
    base_id: str = entry["base_id"]  # type: ignore[assignment]
    id_with_version: str = entry["id_with_version"]  # type: ignore[assignment]
    published: datetime = entry["published"]  # type: ignore[assignment]
    authors: List[str] = entry["authors"]  # type: ignore[assignment]
    pdf_url: str = entry["pdf_url"]  # type: ignore[assignment]

    first_author = authors[0] if authors else "unknown"
    filename = build_filename(published.year, id_with_version, first_author, entry["title"])
    file_path = DOWNLOAD_DIR / filename
    relative_path = str(Path("pdf_files") / filename)

    if file_path.exists():
        if file_path.stat().st_size > MIN_PDF_SIZE_BYTES:
            logging.info("跳过已存在文件: %s", file_path)
            return {
                "title": entry["title"],
                "arxiv_id": base_id,
                "id_with_version": id_with_version,
                "status": "already_exists",
                "file_name": filename,
                "relative_path": relative_path,
                "reason": None,
            }
        logging.warning("删除不完整文件，准备重新下载: %s", file_path)
        file_path.unlink(missing_ok=True)

    existing_versions = [p for p in find_existing_versions(base_id) if p.name != filename]

    temp_path = file_path.with_suffix(".part")
    try:
        response = download_pdf(session, pdf_url, file_path)
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
        if not temp_path.exists() or temp_path.stat().st_size <= MIN_PDF_SIZE_BYTES:
            raise ValueError("下载的文件大小异常")
        temp_path.replace(file_path)
        for old_path in existing_versions:
            if old_path.exists() and old_path != file_path:
                logging.info("删除旧版本: %s", old_path)
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
    except Exception as exc:
        logging.exception("下载或写入 PDF 失败: %s", pdf_url)
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


# ---------------------------------------------------------------------------
# Flask application
# ---------------------------------------------------------------------------
ensure_directories()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

app = Flask(__name__, template_folder=str(TEMPLATES_DIR))


def summarize_results(results: List[Dict[str, object]]) -> Dict[str, int]:
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


@app.route("/")
def index():
    start_year, end_year = get_default_year_range()
    default_year_range = f"{start_year}-{end_year}"
    return render_template(
        "index.html",
        default_year_range=default_year_range,
        default_max_num=DEFAULT_MAX_NUM,
        max_allowed_num=MAX_ALLOWED_NUM,
    )


@app.route("/api/search", methods=["POST"])
def api_search():
    payload = request.get_json(silent=True) or request.form
    keywords = (payload.get("keywords") or "").strip()
    year_range_raw = (payload.get("year_range") or "").strip()
    max_num_raw = payload.get("max_num")

    if not keywords:
        return jsonify({"success": False, "error": "关键词不能为空"}), 400

    try:
        start_year, end_year = parse_year_range(year_range_raw)
        max_num = clamp_max_num(max_num_raw)
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    prefetch_count = min(PRE_FETCH_CAP, max_num * 3 if max_num > 0 else 1)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    try:
        try:
            entries = fetch_arxiv_entries(session, keywords, prefetch_count)
        except Exception as exc:
            logging.exception("arXiv API 请求失败")
            return jsonify({"success": False, "error": f"arXiv API 调用失败: {exc}"}), 502

        filtered_entries = [
            entry for entry in entries
            if start_year <= entry["published"].year <= end_year
        ]
        selected_entries = filtered_entries[:max_num]

        results: List[Dict[str, object]] = []
        for entry in selected_entries:
            result = process_entry(session, entry)
            results.append(result)

        summary = summarize_results(results)
        response_payload = {
            "success": True,
            "results": results,
            "summary": summary,
            "requested": {
                "keywords": keywords,
                "year_range": f"{start_year}-{end_year}",
                "max_num": max_num,
                "prefetch_count": prefetch_count,
                "total_found": len(filtered_entries),
            },
        }
        return jsonify(response_payload)
    finally:
        session.close()


if __name__ == "__main__":
    app.run(debug=False)
