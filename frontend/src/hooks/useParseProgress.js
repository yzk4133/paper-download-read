import { useEffect } from "react";
import api from "../services/api";
import { useAppContext } from "../context/AppContext";

export default function useParseProgress(interval = 5000) {
  const { setProgress, setParseState } = useAppContext();

  useEffect(() => {
    let timer;
    const fetchProgress = async () => {
      try {
        const { data } = await api.get("/parse/progress");
        if (data) {
          setParseState((prev) => ({
            status: data.status || "idle",
            message: data.message || "等待解析",
            updatedAt: data.updated_at || null,
            sourceDir: data.source_dir || (prev ? prev.sourceDir : null),
          }));
          if (typeof data.current === "number" && typeof data.total === "number") {
            setProgress({ current: data.current, total: data.total });
          }
        }
      } catch (error) {
        // 忽略轮询异常
      }
    };

    fetchProgress();
    timer = setInterval(fetchProgress, interval);
    return () => {
      if (timer) {
        clearInterval(timer);
      }
    };
  }, [interval, setProgress, setParseState]);
}
