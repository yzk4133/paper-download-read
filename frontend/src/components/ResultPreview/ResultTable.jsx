import { Table, Tag, Tooltip } from "antd";
import { useMemo } from "react";
import { useAppContext } from "../../context/AppContext";

const STATUS_MAP = {
  downloaded: { color: "green", text: "已下载" },
  already_exists: { color: "blue", text: "已存在" },
  replaced_old_version: { color: "purple", text: "替换旧版" },
  failed: { color: "red", text: "失败" },
};

const PARSE_STATUS_MAP = {
  succeeded: { color: "green", text: "解析成功" },
  failed: { color: "red", text: "解析失败" },
  running: { color: "blue", text: "解析中" },
};

function ResultTable() {
  const { results } = useAppContext();

  const dataSource = useMemo(
    () =>
      results.map((item, index) => ({
        key: item.id_with_version || index,
        ...item,
      })),
    [results]
  );

  const columns = [
    {
      title: "PDF 文件",
      dataIndex: "file_name",
      key: "file_name",
      render: (value, record) => value || record.title,
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      filters: Object.entries(STATUS_MAP).map(([value, meta]) => ({ text: meta.text, value })),
      onFilter: (value, record) => record.status === value,
      render: (value) => {
        const meta = STATUS_MAP[value] || { color: "default", text: value };
        return <Tag color={meta.color}>{meta.text}</Tag>;
      },
    },
    {
      title: "解析状态",
      dataIndex: "parse_status",
      key: "parse_status",
      filters: [
        { text: "解析成功", value: "succeeded" },
        { text: "解析失败", value: "failed" },
      ],
      onFilter: (value, record) => record.parse_status === value,
      render: (value, record) => {
        if (!value) {
          return <Tag>未解析</Tag>;
        }
        const meta = PARSE_STATUS_MAP[value] || { color: "default", text: value };
        const tag = <Tag color={meta.color}>{meta.text}</Tag>;
        return record.parse_error ? (
          <Tooltip title={record.parse_error}>{tag}</Tooltip>
        ) : (
          tag
        );
      },
    },
    {
      title: "创新点",
      dataIndex: "innovation",
      key: "innovation",
      render: (value) => value || "尚未解析",
    },
    {
      title: "实验方法",
      dataIndex: "method",
      key: "method",
      render: (value) => value || "尚未解析",
    },
    {
      title: "结论",
      dataIndex: "conclusion",
      key: "conclusion",
      render: (value) => value || "尚未解析",
    },
  ];

  return <Table columns={columns} dataSource={dataSource} pagination={{ pageSize: 5 }} />;
}

export default ResultTable;
