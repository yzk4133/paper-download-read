import { Form, Input } from "antd";

function YearRangeInput({ name }) {
  return (
    <Form.Item
      name={name}
      label="年份范围"
      extra="格式：YYYY-YYYY，留空使用最近两年"
      rules={[
        {
          validator: (_, value) => {
            if (!value) return Promise.resolve();
            const match = value.match(/^\s*(\d{4})\s*-\s*(\d{4})\s*$/);
            if (!match) {
              return Promise.reject(new Error("年份范围格式应为 YYYY-YYYY"));
            }
            const start = parseInt(match[1], 10);
            const end = parseInt(match[2], 10);
            if (start > end) {
              return Promise.reject(new Error("起始年份不能大于结束年份"));
            }
            return Promise.resolve();
          },
        },
      ]}
    >
      <Input placeholder="2023-2024" allowClear />
    </Form.Item>
  );
}

export default YearRangeInput;
