from __future__ import annotations

import re
from pathlib import Path
from typing import List

from flask import current_app, request  # type: ignore[import-not-found]
from flask_restx import Namespace, Resource, fields  # type: ignore[import-not-found]

from ..services.crawl_service import crawl_papers, crawl_with_keyword_list
from ..services.llm_service import suggest_keywords
from ..utils.validate_utils import clamp_max_num, parse_year_range, validate_keywords

api = Namespace("crawl", description="arXiv 爬取相关接口")

crawl_request_model = api.model(
    "CrawlRequest",
    {
        "keywords": fields.String(required=False, description="检索关键词，支持逗号或空格分隔"),
        "query_text": fields.String(required=False, description="研究需求描述，将使用大模型生成检索关键词"),
        "keyword_count": fields.Integer(required=False, description="大模型生成关键词数量，默认 5"),
        "pdf_dir": fields.String(required=False, description="自定义 PDF 保存目录"),
        "year_range": fields.String(
            required=False,
            description="年份范围，格式 YYYY-YYYY，默认为最近两年",
        ),
        "max_num": fields.Integer(
            required=False,
            min=1,
            max=lambda: current_app.config.get("MAX_ALLOWED_NUM", 10),
            description="最大下载数量，默认 5",
        ),
    },
)

crawl_response_model = api.model(
    "CrawlResponse",
    {
        "success": fields.Boolean(description="是否执行成功"),
        "error": fields.String(description="失败原因"),
        "summary": fields.Raw(description="结果摘要"),
        "results": fields.List(fields.Raw, description="每篇论文的处理结果"),
        "requested": fields.Raw(description="请求的原始参数"),
        "generated_keywords": fields.List(fields.String, description="实际使用的检索关键词"),
        "storage": fields.Raw(description="当前任务使用的文件存储目录"),
    },
)


@api.route("/search")
class CrawlSearch(Resource):
    """触发 arXiv 爬取并下载 PDF 文件。"""

    @api.expect(crawl_request_model, validate=True)
    @api.marshal_with(crawl_response_model)
    def post(self):
        payload = request.get_json(force=True, silent=False)

        config = current_app.config
        try:
            year_range = parse_year_range(payload.get("year_range"))
            max_num = clamp_max_num(
                payload.get("max_num"),
                default=config["DEFAULT_MAX_NUM"],
                maximum=config["MAX_ALLOWED_NUM"],
            )
        except ValueError as exc:
            api.abort(400, str(exc))

        manual_keywords = payload.get("keywords")
        query_text = payload.get("query_text")
        keyword_count = payload.get("keyword_count")
        pdf_dir_value = payload.get("pdf_dir")

        try:
            keyword_list = _prepare_keywords(manual_keywords, query_text, keyword_count)
        except ValueError as exc:
            api.abort(400, str(exc))
        if not keyword_list:
            api.abort(400, "请提供检索关键词或研究需求描述")

        pdf_dir = Path(pdf_dir_value).expanduser().resolve() if pdf_dir_value else None

        if len(keyword_list) == 1 and not query_text:
            # 兼容旧逻辑：单一关键词直接走原实现
            keywords = keyword_list[0]
            result = crawl_papers(
                keywords=keywords,
                year_range=year_range,
                max_num=max_num,
                app_config=config,
                pdf_dir=pdf_dir,
            )
            result.setdefault("generated_keywords", keyword_list)
            result.setdefault("requested", {})
            result["requested"].update(
                {
                    "keywords": keyword_list,
                    "year_range": f"{year_range[0]}-{year_range[1]}",
                    "max_num": max_num,
                }
            )
        else:
            result = crawl_with_keyword_list(
                keyword_list=keyword_list,
                year_range=year_range,
                max_num=max_num,
                app_config=config,
                pdf_dir=pdf_dir,
            )
            result.setdefault("requested", {})
            result["requested"].update(
                {
                    "year_range": f"{year_range[0]}-{year_range[1]}",
                    "max_num": max_num,
                    "query_text": query_text,
                }
            )
            result.setdefault("generated_keywords", keyword_list)
            result["requested"]["keywords"] = keyword_list

        if pdf_dir:
            result.setdefault("storage", {})
            result["storage"]["pdf_dir"] = str(pdf_dir)

        status_code = 200 if result.get("success") else 502
        return result, status_code


def _prepare_keywords(manual_keywords, query_text, keyword_count) -> List[str]:
    keyword_list: List[str] = []

    desired_count = None
    if keyword_count is not None:
        try:
            desired_count = max(1, int(keyword_count))
        except (TypeError, ValueError) as exc:  # pragma: no cover - validation
            raise ValueError("keyword_count 必须为整数") from exc

    if query_text:
        generated = suggest_keywords(str(query_text), count=desired_count)
        keyword_list.extend(generated)

    if manual_keywords:
        if isinstance(manual_keywords, str):
            normalized = manual_keywords.replace("；", ",").replace("，", ",")
            parts = re.split(r"[,\s]+", normalized)
        elif isinstance(manual_keywords, (list, tuple)):
            parts = [str(item) for item in manual_keywords]
        else:
            raise ValueError("keywords 字段格式不正确")

        for part in parts:
            trimmed = part.strip()
            if not trimmed:
                continue
            trimmed = validate_keywords(trimmed)
            keyword_list.append(trimmed)

    deduped: list[str] = []
    seen = set()
    for keyword in keyword_list:
        lowered = keyword.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(keyword)
    return deduped
