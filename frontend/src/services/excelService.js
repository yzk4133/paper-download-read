import api from "./api";

export async function generateExcel(records, options = {}) {
  try {
    const payload = { records };
    if (options.outputDir) {
      payload.output_dir = options.outputDir;
    }
    const { data } = await api.post("/excel/generate", payload);
    return data;
  } catch (error) {
    return { success: false, message: error.message };
  }
}

export function downloadExcel(fileName) {
  const link = document.createElement("a");
  link.href = `${import.meta.env.VITE_API_BASE_URL}/excel/download`;
  link.target = "_blank";
  link.rel = "noopener";
  if (fileName) {
    link.download = fileName;
  }
  link.click();
}
