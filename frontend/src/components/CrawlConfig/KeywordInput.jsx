import { Form, Input } from "antd";

function KeywordInput({ name }) {
  return (
    <Form.Item
      name={name}
      label="附加关键词（可选）"
      tooltip="如需固定某些关键词，可在此处输入，多个关键词以逗号或空格分隔"
    >
      <Input placeholder="例如：transformer, multi-modal" allowClear />
    </Form.Item>
  );
}

export default KeywordInput;
