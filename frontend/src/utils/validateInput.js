const YEAR_RANGE_PATTERN = /^\s*(\d{4})\s*-\s*(\d{4})\s*$/;

export function normalizeCrawlPayload(values) {
  const payload = { ...values };

  const queryText = (payload.query_text || "").trim();
  const keywordsRaw = (payload.keywords || "").replace(/；/g, ",").trim();
  if (!queryText && !keywordsRaw) {
    throw new Error("请至少填写研究描述或附加关键词");
  }

  if (queryText) {
    payload.query_text = queryText;
  } else {
    delete payload.query_text;
  }

  if (keywordsRaw) {
    payload.keywords = keywordsRaw;
  } else {
    delete payload.keywords;
  }

  if (payload.keyword_count !== undefined) {
    const count = Number(payload.keyword_count || 5);
    payload.keyword_count = Math.min(Math.max(Number.isNaN(count) ? 5 : count, 1), 10);
  }

  if (payload.pdf_dir) {
    payload.pdf_dir = payload.pdf_dir.trim();
    if (!payload.pdf_dir) {
      delete payload.pdf_dir;
    }
  }

  if (payload.year_range) {
    const match = payload.year_range.match(YEAR_RANGE_PATTERN);
    if (!match) {
      throw new Error("年份范围格式应为 YYYY-YYYY");
    }
    const start = parseInt(match[1], 10);
    const end = parseInt(match[2], 10);
    if (start > end) {
      throw new Error("起始年份不能大于结束年份");
    }
  }

  const maxNum = Number(payload.max_num || 5);
  payload.max_num = Math.min(Math.max(maxNum, 1), 10);

  return payload;
}
