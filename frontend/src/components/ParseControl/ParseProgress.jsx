import { Progress, Typography } from "antd";
import dayjs from "dayjs";
import { useAppContext } from "../../context/AppContext";
import useParseProgress from "../../hooks/useParseProgress";

const { Text } = Typography;

function ParseProgress() {
  const { progress, parseState } = useAppContext();
  useParseProgress();
  const percent = progress.total ? Math.round((progress.current / progress.total) * 100) : 0;
  const updatedLabel = parseState.updatedAt ? dayjs(parseState.updatedAt).format("YYYY-MM-DD HH:mm:ss") : "暂无更新";

  return (
    <div>
      <Text strong>{parseState.message}</Text>
      <div style={{ marginTop: 4 }}>
        <Text type="secondary">
          {progress.total
            ? `进度：${progress.current}/${progress.total} 篇（${percent}%）`
            : "尚未开始解析"}
        </Text>
      </div>
      <div style={{ marginTop: 4 }}>
        <Text type="secondary">解析目录：{parseState.sourceDir || "默认目录"}</Text>
      </div>
      <div style={{ marginTop: 4 }}>
        <Text type="secondary">最近更新：{updatedLabel}</Text>
      </div>
      <Progress percent={percent} style={{ marginTop: 12 }} />
    </div>
  );
}

export default ParseProgress;
