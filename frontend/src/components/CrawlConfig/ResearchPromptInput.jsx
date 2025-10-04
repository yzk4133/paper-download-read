import { Form, Input } from "antd";

function ResearchPromptInput({ name }) {
  return (
    <Form.Item
      name={name}
      label="研究需求描述"
      rules={[{ required: true, message: "请描述希望检索的研究主题" }]}
      tooltip="输入一段话，大模型将自动生成检索关键词"
    >
      <Input.TextArea rows={4} placeholder="例如：我想查看近两年深度学习在医学影像诊断中的最新进展" allowClear />
    </Form.Item>
  );
}

export default ResearchPromptInput;
