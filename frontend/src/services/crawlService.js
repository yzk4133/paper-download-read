import api from "./api";
import { normalizeCrawlPayload } from "../utils/validateInput";

export async function submitCrawlJob(formValues) {
  const payload = normalizeCrawlPayload(formValues);
  const { data } = await api.post("/crawl/search", payload);
  return data;
}
