import { Spin } from "antd";

function Loading({ tip = "加载中..." }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "24px" }}>
      <Spin tip={tip} size="large" />
    </div>
  );
}

export default Loading;
