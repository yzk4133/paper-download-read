import { Layout } from "antd";
import { AppRoutes } from "./routes";
import { AppProvider } from "./context/AppContext";
import ParseNavigationGuard from "./components/Common/ParseNavigationGuard";

const { Header, Content } = Layout;

function App() {
  return (
    <AppProvider>
      <Layout style={{ minHeight: "100vh" }}>
        <Header style={{ color: "#fff", fontSize: 20 }}>
          arXiv 文献解析平台
        </Header>
        <Content style={{ padding: "24px" }}>
          <ParseNavigationGuard />
          <AppRoutes />
        </Content>
      </Layout>
    </AppProvider>
  );
}

export default App;
