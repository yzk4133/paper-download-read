import api from "./api";

export async function triggerParse(records = [], options = {}) {
  try {
    const payload = {};
    if (Array.isArray(records) && records.length > 0) {
      payload.records = records;
    }
    if (options.sourceDir) {
      payload.source = options.sourceDir;
    }
    const { data } = await api.post("/parse/start", payload);
    return data;
  } catch (error) {
    return { success: false, message: error.message };
  }
}
