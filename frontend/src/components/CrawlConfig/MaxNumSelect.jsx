import { Form, InputNumber } from "antd";

function MaxNumSelect({ name }) {
  return (
    <Form.Item
      name={name}
      label="最大下载数量"
      rules={[{ required: true, message: "请选择下载数量" }]}
    >
      <InputNumber min={1} max={10} style={{ width: "100%" }} />
    </Form.Item>
  );
}

export default MaxNumSelect;
