import { useEffect } from "react";
import { Card, Form, Space, Button, message, Input, Divider, Tag, Typography, InputNumber } from "antd";
import { useNavigate } from "react-router-dom";
import ResearchPromptInput from "../components/CrawlConfig/ResearchPromptInput";
import KeywordInput from "../components/CrawlConfig/KeywordInput";
import YearRangeInput from "../components/CrawlConfig/YearRangeInput";
import MaxNumSelect from "../components/CrawlConfig/MaxNumSelect";
import ParseButton from "../components/ParseControl/ParseButton";
import ParseProgress from "../components/ParseControl/ParseProgress";
import { submitCrawlJob } from "../services/crawlService";
import { useAppContext } from "../context/AppContext";
import { fetchStorageInfo } from "../services/systemService";

const layout = {
  labelCol: { span: 6 },
  wrapperCol: { span: 18 },
};

const { Text } = Typography;

function HomePage() {
  const [form] = Form.useForm();
  const navigate = useNavigate();
  const { setResults, setProgress, setParseState, setExcelInfo, storage, setStorage, keywordPlan, setKeywordPlan } = useAppContext();

  useEffect(() => {
    async function loadStorageDefaults() {
      try {
        const info = await fetchStorageInfo();
        const nextStorage = {
          pdfDir: info.pdf_dir || storage.pdfDir,
          excelDir: info.excel_dir || storage.excelDir,
        };
        setStorage(nextStorage);
        form.setFieldsValue({
          pdf_dir: nextStorage.pdfDir,
          excel_dir: nextStorage.excelDir,
        });
      } catch (error) {
        // 忽略初始化失败
      }
    }

    if (!storage.pdfDir || !storage.excelDir) {
      loadStorageDefaults();
    } else {
      form.setFieldsValue({
        pdf_dir: storage.pdfDir,
        excel_dir: storage.excelDir,
      });
    }
  }, [form, setStorage, storage.pdfDir, storage.excelDir]);

  const handleSubmit = async (values) => {
    try {
      const payload = await submitCrawlJob(values);
      if (!payload.success) {
        message.error(payload.error || "爬取失败");
        return;
      }
      setResults(payload.results || []);
      const total = payload.summary?.total ?? 0;
      const downloaded = payload.summary?.downloaded ?? 0;
      setProgress({ current: downloaded, total });
      const generatedKeywords = payload.generated_keywords || payload.requested?.keywords || [];
      setKeywordPlan(generatedKeywords);

  const pdfDir = (payload.storage?.pdf_dir || values.pdf_dir || storage.pdfDir || "").trim();
  const excelDir = (values.excel_dir || storage.excelDir || "").trim();
      setStorage({ pdfDir, excelDir });

      const hasDownloadable = downloaded > 0;
      setParseState({
        status: hasDownloadable ? "ready" : "idle",
        message: hasDownloadable ? `爬取完成，可解析 ${downloaded} 篇论文` : "爬取完成，但暂无可解析论文",
        updatedAt: new Date().toISOString(),
        sourceDir: pdfDir || null,
      });
      setExcelInfo({
        status: "idle",
        message: "Excel 尚未生成",
        file: null,
        path: excelDir || null,
        updatedAt: null,
      });
      if (generatedKeywords.length) {
        message.success(`关键词已生成（${generatedKeywords.length} 个），点击解析继续`);
      } else {
        message.success(hasDownloadable ? "爬取完成，点击解析以继续" : "爬取完成，但没有可解析的下载记录");
      }
      if (payload.error) {
        message.warning(`部分关键词检索失败：${payload.error}`);
      }
    } catch (error) {
      message.error(error.message || "请求失败");
    }
  };

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Card title="爬取配置" bordered={false}>
        <Form
          {...layout}
          layout="vertical"
          form={form}
          initialValues={{
            query_text: "深度学习在医学影像诊断的最新应用",
            keywords: "",
            year_range: "",
            max_num: 5,
            keyword_count: 5,
            pdf_dir: storage.pdfDir,
            excel_dir: storage.excelDir,
          }}
          onValuesChange={(changed, allValues) => {
            if (Object.prototype.hasOwnProperty.call(changed, "pdf_dir")) {
              const nextPdf = (changed.pdf_dir || "").trim();
              setStorage((prev) => ({ ...prev, pdfDir: nextPdf }));
            }
            if (Object.prototype.hasOwnProperty.call(changed, "excel_dir")) {
              const nextExcel = (changed.excel_dir || "").trim();
              setStorage((prev) => ({ ...prev, excelDir: nextExcel }));
              setExcelInfo((prev) => ({
                ...prev,
                path: nextExcel || (prev ? prev.path : null),
              }));
            }
          }}
          onFinish={handleSubmit}
        >
          <ResearchPromptInput name="query_text" />
          <KeywordInput name="keywords" />
          <Form.Item name="keyword_count" label="生成关键词数量" tooltip="将请求大模型生成若干检索关键词">
            <InputNumber min={1} max={10} style={{ width: "100%" }} />
          </Form.Item>
          <YearRangeInput name="year_range" />
          <MaxNumSelect name="max_num" />
          <Form.Item name="pdf_dir" label="PDF 保存目录" tooltip="默认为后端配置，可自定义到本地任意文件夹">
            <Input placeholder="例如：D:/Research/papers" allowClear />
          </Form.Item>
          <Form.Item name="excel_dir" label="Excel 输出目录" tooltip="默认为后端配置，可自定义输出位置">
            <Input placeholder="例如：D:/Research/reports" allowClear />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">
              开始爬取
            </Button>
            <Button style={{ marginLeft: 12 }} onClick={() => navigate("/results")}>查看结果</Button>
          </Form.Item>
        </Form>
        {keywordPlan?.length ? (
          <>
            <Divider orientation="left">本次检索关键词</Divider>
            <Space wrap>
              {keywordPlan.map((item) => (
                <Tag key={item}>{item}</Tag>
              ))}
            </Space>
          </>
        ) : null}
        <Divider orientation="left">当前保存路径</Divider>
        <Space direction="vertical">
          <Text type="secondary">PDF：{storage.pdfDir || "默认配置"}</Text>
          <Text type="secondary">Excel：{storage.excelDir || "默认配置"}</Text>
        </Space>
      </Card>
      <Card title="解析控制" bordered={false}>
        <Space direction="vertical" size="middle" style={{ width: "100%" }}>
          <ParseButton />
          <ParseProgress />
        </Space>
      </Card>
    </Space>
  );
}

export default HomePage;
