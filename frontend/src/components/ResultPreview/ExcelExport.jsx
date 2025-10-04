import { useState } from "react";
import { Button, message, Space, Typography } from "antd";
import { generateExcel, downloadExcel } from "../../services/excelService";
import { useAppContext } from "../../context/AppContext";
import useExcelStatus from "../../hooks/useExcelStatus";

const { Text } = Typography;

function ExcelExport() {
  const [loading, setLoading] = useState(false);
  const { results, excelInfo, setExcelInfo, storage } = useAppContext();
  useExcelStatus();

  const handleGenerate = async () => {
    if (!results?.length) {
      message.warning("暂无解析结果，无法生成 Excel。");
      return;
    }
    setLoading(true);
    setExcelInfo({ status: "running", message: "正在生成 Excel 报告", file: null, path: storage.excelDir || null, updatedAt: new Date().toISOString() });
    try {
      const response = await generateExcel(results, { outputDir: storage.excelDir });
      if (!response.success) {
        setExcelInfo({ status: "failed", message: response.message || "生成失败", file: null, path: storage.excelDir || null, updatedAt: new Date().toISOString() });
        message.warning(response.message || "Excel 功能尚未启用");
      } else {
        setExcelInfo({ status: "completed", message: response.message || "Excel 已生成", file: response.file, path: response.path || storage.excelDir || null, updatedAt: new Date().toISOString() });
        message.success(response.message || "Excel 已生成");
      }
    } catch (error) {
      setExcelInfo({ status: "failed", message: error.message || "生成失败", file: null, path: storage.excelDir || null, updatedAt: new Date().toISOString() });
      message.error(error.message || "生成失败");
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (!excelInfo.file) {
      message.warning("请先生成 Excel 文件。");
      return;
    }
    downloadExcel(excelInfo.file);
  };

  return (
    <Space direction="vertical" size="small" style={{ width: "100%" }}>
      <Space>
        <Button onClick={handleGenerate} loading={loading || excelInfo.status === "running"} type="primary">
        生成 Excel
        </Button>
        <Button onClick={handleDownload} disabled={!excelInfo.file}>
          下载 Excel
        </Button>
      </Space>
      <Text type="secondary">状态：{excelInfo.message || "尚未生成 Excel"}</Text>
      {excelInfo.file ? <Text type="secondary">最新文件：{excelInfo.file}</Text> : null}
      <Text type="secondary">输出目录：{excelInfo.path || storage.excelDir || "默认目录"}</Text>
    </Space>
  );
}

export default ExcelExport;
