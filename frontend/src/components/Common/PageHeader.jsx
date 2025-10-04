import { Button, Space, Typography } from "antd";
import { useNavigate } from "react-router-dom";

const { Title } = Typography;

function PageHeader({ title, extra }) {
  const navigate = useNavigate();

  return (
    <Space align="center" style={{ width: "100%", justifyContent: "space-between" }}>
      <Space>
        <Button type="link" onClick={() => navigate(-1)}>
          返回
        </Button>
        <Title level={3} style={{ margin: 0 }}>
          {title}
        </Title>
      </Space>
      {extra}
    </Space>
  );
}

export default PageHeader;
