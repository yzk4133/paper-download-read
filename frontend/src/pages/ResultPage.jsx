import { Card, Space, Button, Typography } from "antd";
import { useNavigate } from "react-router-dom";
import ResultTable from "../components/ResultPreview/ResultTable";
import ExcelExport from "../components/ResultPreview/ExcelExport";
import { useAppContext } from "../context/AppContext";

const { Text } = Typography;

function ResultPage() {
  const navigate = useNavigate();
  const { storage } = useAppContext();
  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Card bordered={false}>
        <Space align="center" wrap>
          <Button onClick={() => navigate("/")}>返回重新检索</Button>
          <Text type="secondary">PDF 保存：{storage.pdfDir || "默认配置"}</Text>
          <Text type="secondary">Excel 输出：{storage.excelDir || "默认配置"}</Text>
        </Space>
      </Card>
      <Card title="解析结果" bordered={false}>
        <ResultTable />
      </Card>
      <Card title="导出工具" bordered={false}>
        <ExcelExport />
      </Card>
    </Space>
  );
}

export default ResultPage;
