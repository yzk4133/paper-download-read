import { useMemo, useState } from "react";
import { Button, message } from "antd";
import { triggerParse } from "../../services/parseService";
import { useAppContext } from "../../context/AppContext";

function ParseButton() {
  const [loading, setLoading] = useState(false);
  const { results, setResults, setProgress, setParseState, storage } = useAppContext();
  const downloadableRecords = useMemo(() => results.filter((item) => item.status !== "failed"), [results]);
  const handleClick = async () => {
    if (!downloadableRecords.length) {
      message.warning("当前没有可解析的论文，请先执行爬取。");
      return;
    }

    setLoading(true);
    setParseState({ status: "running", message: "正在启动解析任务", updatedAt: new Date().toISOString(), sourceDir: storage.pdfDir || null });
    setProgress({ current: 0, total: downloadableRecords.length });

    try {
      const response = await triggerParse(downloadableRecords, { sourceDir: storage.pdfDir });
      if (!response.success) {
        setParseState({ status: "failed", message: response.message || "解析失败", updatedAt: new Date().toISOString(), sourceDir: storage.pdfDir || null });
        message.warning(response.message || "解析功能尚未启用");
      } else {
        const updatedByKey = new Map(
          (response.results || []).map((item) => [item.id_with_version || item.file_name || item.title, item])
        );
        const mergedResults = results.map((item) => updatedByKey.get(item.id_with_version || item.file_name || item.title) || item);
        setResults(mergedResults);
        const summary = response.summary || {};
        setProgress({ current: summary.parsed || 0, total: summary.total || downloadableRecords.length });
        setParseState({ status: response.status || "completed", message: response.message || "解析完成", updatedAt: new Date().toISOString(), sourceDir: (response.storage && response.storage.pdf_dir) || storage.pdfDir || null });
        message.success(response.message || "解析任务完成");
      }
    } catch (error) {
      setParseState({ status: "failed", message: error.message || "解析失败", updatedAt: new Date().toISOString(), sourceDir: storage.pdfDir || null });
      message.error(error.message || "解析启动失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Button type="primary" onClick={handleClick} loading={loading} block>
      开始解析
    </Button>
  );
}

export default ParseButton;
